use super::{BackendError, Result, RunRequest, SimulationBackend};
use crate::params::{ArrivalProcessSpec, WorkloadDistributionSpec};
use crate::stats::RunSummary;
use std::sync::Arc;

use cudarc::{
    driver::{CudaContext, LaunchConfig, PushKernelArg},
    nvrtc::compile_ptx,
};

const GPU_KERNEL_SRC: &str = r#"
#define MAX_CAPACITY 128
#define RESOURCE_CHOICES 8
#define INF_TIME 1.0e300

__device__ __forceinline__ unsigned long long xorshift64star(unsigned long long* state) {
    unsigned long long x = *state;
    if (x == 0ULL) {
        x = 0x9E3779B97F4A7C15ULL;
    }
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 2685821657736338717ULL;
}

__device__ __forceinline__ double uniform01(unsigned long long* state) {
    unsigned long long x = xorshift64star(state);
    double u = (double)((x >> 11) * (1.0 / 9007199254740992.0));
    if (u <= 1.0e-15) u = 1.0e-15;
    if (u >= 1.0) u = 1.0 - 1.0e-15;
    return u;
}

__device__ __forceinline__ double sample_exp(unsigned long long* state, double rate) {
    if (rate <= 0.0) return INF_TIME;
    double u = uniform01(state);
    return -log(u) / rate;
}

__device__ __forceinline__ double overlap_len(double a0, double a1, double b0, double b1) {
    double left = a0 > b0 ? a0 : b0;
    double right = a1 < b1 ? a1 : b1;
    double len = right - left;
    return len > 0.0 ? len : 0.0;
}

__device__ __forceinline__ unsigned int sample_resource(
    unsigned long long* state,
    unsigned int resource_len,
    unsigned int rv0, unsigned int rv1, unsigned int rv2, unsigned int rv3,
    unsigned int rv4, unsigned int rv5, unsigned int rv6, unsigned int rv7,
    double c0, double c1, double c2, double c3, double c4, double c5, double c6, double c7
) {
    double u = uniform01(state);

    unsigned int values[RESOURCE_CHOICES];
    double cdf[RESOURCE_CHOICES];

    values[0] = rv0; values[1] = rv1; values[2] = rv2; values[3] = rv3;
    values[4] = rv4; values[5] = rv5; values[6] = rv6; values[7] = rv7;

    cdf[0] = c0; cdf[1] = c1; cdf[2] = c2; cdf[3] = c3;
    cdf[4] = c4; cdf[5] = c5; cdf[6] = c6; cdf[7] = c7;

    for (unsigned int i = 0; i < resource_len; ++i) {
        if (u <= cdf[i]) {
            return values[i];
        }
    }

    return values[resource_len - 1];
}

extern "C" __global__ void simulate_loss_poisson_deterministic(
    double arrival_rate,
    double service_speed,
    double max_time,
    double warmup_time,
    double mean_workload,
    unsigned int servers_n,
    unsigned int capacity_k,
    unsigned int total_resource_r,
    unsigned long long seed,

    unsigned int resource_len,
    unsigned int rv0, unsigned int rv1, unsigned int rv2, unsigned int rv3,
    unsigned int rv4, unsigned int rv5, unsigned int rv6, unsigned int rv7,
    double c0, double c1, double c2, double c3, double c4, double c5, double c6, double c7,

    unsigned long long* out_arrival_attempts,
    unsigned long long* out_accepted_arrivals,
    unsigned long long* out_rejected_arrivals,
    unsigned long long* out_rejected_capacity,
    unsigned long long* out_rejected_server,
    unsigned long long* out_rejected_resource,
    unsigned long long* out_completed_jobs,
    unsigned long long* out_completed_time_samples,

    double* out_resource_time,
    double* out_service_time_sum,
    double* out_service_time_sq_sum,
    double* out_sojourn_time_sum,
    double* out_sojourn_time_sq_sum,

    double* out_state_times
) {
    if (blockIdx.x != 0 || threadIdx.x != 0) {
        return;
    }

    if (capacity_k > MAX_CAPACITY) {
        return;
    }

    for (unsigned int k = 0; k <= capacity_k; ++k) {
        out_state_times[k] = 0.0;
    }

    out_arrival_attempts[0] = 0ULL;
    out_accepted_arrivals[0] = 0ULL;
    out_rejected_arrivals[0] = 0ULL;
    out_rejected_capacity[0] = 0ULL;
    out_rejected_server[0] = 0ULL;
    out_rejected_resource[0] = 0ULL;
    out_completed_jobs[0] = 0ULL;
    out_completed_time_samples[0] = 0ULL;

    out_resource_time[0] = 0.0;
    out_service_time_sum[0] = 0.0;
    out_service_time_sq_sum[0] = 0.0;
    out_sojourn_time_sum[0] = 0.0;
    out_sojourn_time_sq_sum[0] = 0.0;

    unsigned long long rng_state = seed ^ 0xD1B54A32D192ED03ULL;

    double current_time = 0.0;
    double next_arrival_time = (arrival_rate > 0.0) ? sample_exp(&rng_state, arrival_rate) : INF_TIME;
    double service_time_const = mean_workload / service_speed;

    double departure_times[MAX_CAPACITY];
    double arrival_times[MAX_CAPACITY];
    unsigned int resource_demands[MAX_CAPACITY];

    unsigned int active_count = 0;
    unsigned int occupied_resource = 0;

    while (current_time < max_time) {
        double next_departure_time = INF_TIME;

        for (unsigned int i = 0; i < active_count; ++i) {
            if (departure_times[i] < next_departure_time) {
                next_departure_time = departure_times[i];
            }
        }

        double next_event_time = next_arrival_time;
        if (next_departure_time < next_event_time) {
            next_event_time = next_departure_time;
        }
        if (max_time < next_event_time) {
            next_event_time = max_time;
        }

        double overlap = overlap_len(current_time, next_event_time, warmup_time, max_time);
        if (overlap > 0.0) {
            out_state_times[active_count] += overlap;
            out_resource_time[0] += ((double)occupied_resource) * overlap;
        }

        current_time = next_event_time;
        if (current_time >= max_time - 1.0e-12) {
            break;
        }

        int arrival_happened = (next_arrival_time <= next_departure_time + 1.0e-12);

        if (arrival_happened) {
            if (current_time >= warmup_time && current_time <= max_time) {
                out_arrival_attempts[0] += 1ULL;
            }

            unsigned int demand = sample_resource(
                &rng_state,
                resource_len,
                rv0, rv1, rv2, rv3, rv4, rv5, rv6, rv7,
                c0, c1, c2, c3, c4, c5, c6, c7
            );

            int accepted = 0;

            if (active_count >= capacity_k) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[0] += 1ULL;
                    out_rejected_capacity[0] += 1ULL;
                }
            } else if (active_count >= servers_n) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[0] += 1ULL;
                    out_rejected_server[0] += 1ULL;
                }
            } else if (occupied_resource + demand > total_resource_r) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[0] += 1ULL;
                    out_rejected_resource[0] += 1ULL;
                }
            } else {
                accepted = 1;
            }

            if (accepted) {
                departure_times[active_count] = current_time + service_time_const;
                arrival_times[active_count] = current_time;
                resource_demands[active_count] = demand;
                active_count += 1;
                occupied_resource += demand;

                if (current_time >= warmup_time && current_time <= max_time) {
                    out_accepted_arrivals[0] += 1ULL;
                }
            }

            next_arrival_time = (arrival_rate > 0.0)
                ? current_time + sample_exp(&rng_state, arrival_rate)
                : INF_TIME;
        } else {
            unsigned int i = 0;
            while (i < active_count) {
                if (departure_times[i] <= current_time + 1.0e-12) {
                    double service_time = departure_times[i] - arrival_times[i];
                    double sojourn_time = service_time;

                    if (current_time >= warmup_time && current_time <= max_time) {
                        out_completed_jobs[0] += 1ULL;
                        out_completed_time_samples[0] += 1ULL;

                        out_service_time_sum[0] += service_time;
                        out_service_time_sq_sum[0] += service_time * service_time;

                        out_sojourn_time_sum[0] += sojourn_time;
                        out_sojourn_time_sq_sum[0] += sojourn_time * sojourn_time;
                    }

                    occupied_resource -= resource_demands[i];

                    unsigned int last = active_count - 1;
                    departure_times[i] = departure_times[last];
                    arrival_times[i] = arrival_times[last];
                    resource_demands[i] = resource_demands[last];
                    active_count -= 1;
                } else {
                    i += 1;
                }
            }
        }
    }
}
"#;

#[derive(Debug, Clone)]
pub struct GpuBackend {
    pub max_batch_size: usize,
}

impl GpuBackend {
    pub fn new() -> Result<Self> {
        Ok(Self {
            max_batch_size: 65_536,
        })
    }

    fn validate_request(&self, request: &RunRequest) -> Result<()> {
        let scenario = &request.scenario;

        if scenario.capacity_k > 128 {
            return Err(BackendError::Validation(format!(
                "Текущая GPU-версия поддерживает только capacity_k <= 128, получено {}",
                scenario.capacity_k
            )));
        }

        if scenario.resource_distribution.values.len() > 8 {
            return Err(BackendError::Validation(format!(
                "Текущая GPU-версия поддерживает не более 8 resource choices, получено {}",
                scenario.resource_distribution.values.len()
            )));
        }

        match scenario.arrival_spec {
            ArrivalProcessSpec::Poisson => {}
            _ => {
                return Err(BackendError::Validation(
                    "Текущая полноценная test-версия GPU backend пока поддерживает только arrival=poisson".to_string(),
                ));
            }
        }

        match scenario.workload_spec {
            WorkloadDistributionSpec::Deterministic { .. } => {}
            _ => {
                return Err(BackendError::Validation(
                    "Текущая полноценная test-версия GPU backend пока поддерживает только workload=deterministic".to_string(),
                ));
            }
        }

        if scenario.service_speed <= 0.0 {
            return Err(BackendError::Validation(format!(
                "service_speed должен быть > 0, получено {}",
                scenario.service_speed
            )));
        }

        if scenario.max_time <= scenario.warmup_time {
            return Err(BackendError::Validation(format!(
                "max_time должен быть > warmup_time, получено {} <= {}",
                scenario.max_time, scenario.warmup_time
            )));
        }

        Ok(())
    }

    fn compile_and_load_kernel(
        &self,
        ctx: &Arc<CudaContext>,
    ) -> Result<cudarc::driver::CudaFunction> {
        let ptx = compile_ptx(GPU_KERNEL_SRC).map_err(|e| {
            BackendError::Validation(format!(
                "Не удалось скомпилировать GPU simulation kernel через NVRTC: {:?}",
                e
            ))
        })?;

        let module = ctx.load_module(ptx).map_err(|e| {
            BackendError::Validation(format!(
                "Не удалось загрузить PTX-модуль GPU kernel в CUDA context: {:?}",
                e
            ))
        })?;

        module
            .load_function("simulate_loss_poisson_deterministic")
            .map_err(|e| {
                BackendError::Validation(format!(
                    "Не удалось загрузить функцию simulate_loss_poisson_deterministic: {:?}",
                    e
                ))
            })
    }

    fn cumulative_resource_cdf(probabilities: &[f64]) -> [f64; 8] {
        let mut cdf = [1.0_f64; 8];
        let mut acc = 0.0_f64;

        for (i, p) in probabilities.iter().enumerate() {
            acc += *p;
            cdf[i] = acc;
        }

        if !probabilities.is_empty() {
            cdf[probabilities.len() - 1] = 1.0;
        }

        cdf
    }

    fn padded_resource_values(values: &[u32]) -> [u32; 8] {
        let mut out = [0_u32; 8];
        for (i, v) in values.iter().enumerate() {
            out[i] = *v;
        }
        out
    }

    fn run_one_on_gpu(
        &self,
        request: &RunRequest,
        ctx: &Arc<CudaContext>,
        kernel: &cudarc::driver::CudaFunction,
    ) -> Result<RunSummary> {
        self.validate_request(request)?;
        let scenario = &request.scenario;
        let stream = ctx.default_stream();

        let resource_values = Self::padded_resource_values(&scenario.resource_distribution.values);
        let resource_cdf = Self::cumulative_resource_cdf(&scenario.resource_distribution.probabilities);

        let mean_workload = match scenario.workload_spec {
            WorkloadDistributionSpec::Deterministic { mean, .. } => mean,
            _ => unreachable!(),
        };

        let mut out_arrival_attempts = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_arrival_attempts failed: {:?}", e))
        })?;
        let mut out_accepted_arrivals = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_accepted_arrivals failed: {:?}", e))
        })?;
        let mut out_rejected_arrivals = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_arrivals failed: {:?}", e))
        })?;
        let mut out_rejected_capacity = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_capacity failed: {:?}", e))
        })?;
        let mut out_rejected_server = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_server failed: {:?}", e))
        })?;
        let mut out_rejected_resource = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_resource failed: {:?}", e))
        })?;
        let mut out_completed_jobs = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_completed_jobs failed: {:?}", e))
        })?;
        let mut out_completed_time_samples = stream.alloc_zeros::<u64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_completed_time_samples failed: {:?}", e))
        })?;

        let mut out_resource_time = stream.alloc_zeros::<f64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_resource_time failed: {:?}", e))
        })?;
        let mut out_service_time_sum = stream.alloc_zeros::<f64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_service_time_sum failed: {:?}", e))
        })?;
        let mut out_service_time_sq_sum = stream.alloc_zeros::<f64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_service_time_sq_sum failed: {:?}", e))
        })?;
        let mut out_sojourn_time_sum = stream.alloc_zeros::<f64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_sojourn_time_sum failed: {:?}", e))
        })?;
        let mut out_sojourn_time_sq_sum = stream.alloc_zeros::<f64>(1).map_err(|e| {
            BackendError::Validation(format!("alloc out_sojourn_time_sq_sum failed: {:?}", e))
        })?;

        let mut out_state_times =
            stream.alloc_zeros::<f64>(scenario.capacity_k + 1).map_err(|e| {
                BackendError::Validation(format!("alloc out_state_times failed: {:?}", e))
            })?;

        let mut builder = stream.launch_builder(kernel);

    let servers_n_u32 = scenario.servers_n as u32;
    let capacity_k_u32 = scenario.capacity_k as u32;
    let resource_len_u32 = scenario.resource_distribution.values.len() as u32;

    builder.arg(&scenario.arrival_rate);
    builder.arg(&scenario.service_speed);
    builder.arg(&scenario.max_time);
    builder.arg(&scenario.warmup_time);
    builder.arg(&mean_workload);
    builder.arg(&servers_n_u32);
    builder.arg(&capacity_k_u32);
    builder.arg(&scenario.total_resource_r);
    builder.arg(&request.seed);

    builder.arg(&resource_len_u32);

        builder.arg(&resource_values[0]);
        builder.arg(&resource_values[1]);
        builder.arg(&resource_values[2]);
        builder.arg(&resource_values[3]);
        builder.arg(&resource_values[4]);
        builder.arg(&resource_values[5]);
        builder.arg(&resource_values[6]);
        builder.arg(&resource_values[7]);

        builder.arg(&resource_cdf[0]);
        builder.arg(&resource_cdf[1]);
        builder.arg(&resource_cdf[2]);
        builder.arg(&resource_cdf[3]);
        builder.arg(&resource_cdf[4]);
        builder.arg(&resource_cdf[5]);
        builder.arg(&resource_cdf[6]);
        builder.arg(&resource_cdf[7]);

        builder.arg(&mut out_arrival_attempts);
        builder.arg(&mut out_accepted_arrivals);
        builder.arg(&mut out_rejected_arrivals);
        builder.arg(&mut out_rejected_capacity);
        builder.arg(&mut out_rejected_server);
        builder.arg(&mut out_rejected_resource);
        builder.arg(&mut out_completed_jobs);
        builder.arg(&mut out_completed_time_samples);

        builder.arg(&mut out_resource_time);
        builder.arg(&mut out_service_time_sum);
        builder.arg(&mut out_service_time_sq_sum);
        builder.arg(&mut out_sojourn_time_sum);
        builder.arg(&mut out_sojourn_time_sq_sum);

        builder.arg(&mut out_state_times);

        unsafe {
            builder
                .launch(LaunchConfig::for_num_elems(1))
                .map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось запустить simulate_loss_poisson_deterministic: {:?}",
                        e
                    ))
                })?;
        }

        let arrival_attempts = stream.clone_dtoh(&out_arrival_attempts).map_err(|e| {
            BackendError::Validation(format!("dtoh arrival_attempts failed: {:?}", e))
        })?[0];
        let accepted_arrivals = stream.clone_dtoh(&out_accepted_arrivals).map_err(|e| {
            BackendError::Validation(format!("dtoh accepted_arrivals failed: {:?}", e))
        })?[0];
        let rejected_arrivals = stream.clone_dtoh(&out_rejected_arrivals).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_arrivals failed: {:?}", e))
        })?[0];
        let rejected_capacity = stream.clone_dtoh(&out_rejected_capacity).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_capacity failed: {:?}", e))
        })?[0];
        let rejected_server = stream.clone_dtoh(&out_rejected_server).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_server failed: {:?}", e))
        })?[0];
        let rejected_resource = stream.clone_dtoh(&out_rejected_resource).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_resource failed: {:?}", e))
        })?[0];
        let completed_jobs = stream.clone_dtoh(&out_completed_jobs).map_err(|e| {
            BackendError::Validation(format!("dtoh completed_jobs failed: {:?}", e))
        })?[0];
        let completed_time_samples = stream.clone_dtoh(&out_completed_time_samples).map_err(|e| {
            BackendError::Validation(format!("dtoh completed_time_samples failed: {:?}", e))
        })?[0];

        let resource_time = stream.clone_dtoh(&out_resource_time).map_err(|e| {
            BackendError::Validation(format!("dtoh resource_time failed: {:?}", e))
        })?[0];
        let service_time_sum = stream.clone_dtoh(&out_service_time_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh service_time_sum failed: {:?}", e))
        })?[0];
        let service_time_sq_sum = stream.clone_dtoh(&out_service_time_sq_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh service_time_sq_sum failed: {:?}", e))
        })?[0];
        let sojourn_time_sum = stream.clone_dtoh(&out_sojourn_time_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh sojourn_time_sum failed: {:?}", e))
        })?[0];
        let sojourn_time_sq_sum = stream.clone_dtoh(&out_sojourn_time_sq_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh sojourn_time_sq_sum failed: {:?}", e))
        })?[0];

        let state_times = stream.clone_dtoh(&out_state_times).map_err(|e| {
            BackendError::Validation(format!("dtoh state_times failed: {:?}", e))
        })?;

        let observed_time = scenario.max_time - scenario.warmup_time;
        let pi_hat: Vec<f64> = state_times.iter().map(|x| *x / observed_time).collect();

        let mean_num_jobs = pi_hat
            .iter()
            .enumerate()
            .map(|(k, p)| k as f64 * *p)
            .sum::<f64>();

        let mean_occupied_resource = resource_time / observed_time;
        let loss_probability = if arrival_attempts > 0 {
            rejected_arrivals as f64 / arrival_attempts as f64
        } else {
            0.0
        };
        let throughput = completed_jobs as f64 / observed_time;

        let n = completed_time_samples as f64;
        let mean_service_time = if n > 0.0 { service_time_sum / n } else { 0.0 };
        let mean_sojourn_time = if n > 0.0 { sojourn_time_sum / n } else { 0.0 };

        let std_service_time = if n > 0.0 {
            ((service_time_sq_sum / n) - mean_service_time * mean_service_time)
                .max(0.0)
                .sqrt()
        } else {
            0.0
        };

        let std_sojourn_time = if n > 0.0 {
            ((sojourn_time_sq_sum / n) - mean_sojourn_time * mean_sojourn_time)
                .max(0.0)
                .sqrt()
        } else {
            0.0
        };

        let summary = RunSummary {
            scenario_key: scenario.scenario_key.clone(),
            scenario_name: scenario.scenario_name.clone(),
            replication_index: request.replication_index,
            seed: request.seed,

            total_time: scenario.max_time,
            warmup_time: scenario.warmup_time,
            observed_time,

            arrival_attempts,
            accepted_arrivals,
            rejected_arrivals,
            rejected_capacity,
            rejected_server,
            rejected_resource,
            completed_jobs,
            completed_time_samples,

            mean_num_jobs,
            mean_occupied_resource,
            loss_probability,
            throughput,

            mean_service_time,
            mean_sojourn_time,
            std_service_time,
            std_sojourn_time,

            pi_hat,
        };

        summary.validate()?;
        Ok(summary)
    }
}

impl SimulationBackend for GpuBackend {
    fn kind(&self) -> &'static str {
        "gpu"
    }

    fn execute_batch(&self, requests: &[RunRequest]) -> Result<Vec<RunSummary>> {
        if requests.is_empty() {
            return Ok(Vec::new());
        }

        if requests.len() > self.max_batch_size {
            return Err(BackendError::Validation(format!(
                "GPU backend получил batch размера {}, что больше max_batch_size={}",
                requests.len(),
                self.max_batch_size
            )));
        }

        let ctx = CudaContext::new(0).map_err(|e| {
            BackendError::Validation(format!(
                "Не удалось создать CUDA context на device 0: {:?}",
                e
            ))
        })?;

        let kernel = self.compile_and_load_kernel(&ctx)?;

        let mut out = Vec::with_capacity(requests.len());
        for request in requests {
            out.push(self.run_one_on_gpu(request, &ctx, &kernel)?);
        }

        eprintln!(
            "GPU real test backend finished: {} run(s) executed on CUDA device.",
            out.len()
        );

        Ok(out)
    }
}