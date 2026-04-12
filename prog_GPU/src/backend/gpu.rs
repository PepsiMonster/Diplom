use super::{BackendError, Result, RunRequest, SimulationBackend};
use crate::params::{ArrivalProcessSpec, WorkloadDistributionSpec};
use crate::stats::RunSummary;
use std::sync::Arc;
use std::time::{Duration, Instant};

use cudarc::{
    driver::{CudaContext, LaunchConfig, PushKernelArg},
    nvrtc::Ptx,
};

const GPU_KERNEL_PTX_PATH: &str = "cuda/sim_kernel.ptx";

#[derive(Debug, Clone)]
pub struct GpuBackend {
    pub max_batch_size: usize,
    pub block_size: u32,
    pub save_pi_hat: bool,
}

#[derive(Debug, Clone, Default)]
struct GpuTimingBreakdown {
    htod: Duration,
    kernel: Duration,
    dtoh: Duration,
    summary: Duration,
}

impl GpuBackend {
    pub fn new() -> Result<Self> {
        let block_size = std::env::var("SIM_GPU_BLOCK_SIZE")
            .ok()
            .and_then(|v| v.parse::<u32>().ok())
            .unwrap_or(128);
        if !matches!(block_size, 64 | 128 | 256) {
            return Err(BackendError::Validation(format!(
                "SIM_GPU_BLOCK_SIZE должен быть одним из [64, 128, 256], получено {block_size}"
            )));
        }

        let save_pi_hat = std::env::var("SIM_GPU_SAVE_PI_HAT")
            .map(|v| !matches!(v.to_ascii_lowercase().as_str(), "0" | "false" | "no"))
            .unwrap_or(true);

        Ok(Self {
            max_batch_size: 65_536,
            block_size,
            save_pi_hat,
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

        if let ArrivalProcessSpec::Erlang { order } = scenario.arrival_spec {
            if order == 0 {
                return Err(BackendError::Validation(
                    "arrival Erlang order должен быть > 0".to_string(),
                ));
            }
        }

        if let ArrivalProcessSpec::Hyperexponential2 {
            p,
            fast_rate_multiplier,
        } = scenario.arrival_spec
        {
            if !(0.0 < p && p < 1.0) {
                return Err(BackendError::Validation(format!(
                    "arrival HyperExp(2) требует p в (0,1), получено {p}"
                )));
            }
            if fast_rate_multiplier <= 0.0 {
                return Err(BackendError::Validation(format!(
                    "arrival HyperExp(2) требует fast_rate_multiplier > 0, получено {fast_rate_multiplier}"
                )));
            }
        }

        if let WorkloadDistributionSpec::Erlang { order, .. } = scenario.workload_spec {
            if order == 0 {
                return Err(BackendError::Validation(
                    "workload Erlang order должен быть > 0".to_string(),
                ));
            }
        }

        if let WorkloadDistributionSpec::Hyperexponential2 {
            p,
            fast_rate_multiplier,
            ..
        } = scenario.workload_spec
        {
            if !(0.0 < p && p < 1.0) {
                return Err(BackendError::Validation(format!(
                    "workload HyperExp(2) требует p в (0,1), получено {p}"
                )));
            }
            if fast_rate_multiplier <= 0.0 {
                return Err(BackendError::Validation(format!(
                    "workload HyperExp(2) требует fast_rate_multiplier > 0, получено {fast_rate_multiplier}"
                )));
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
        let ptx = Ptx::from_file(GPU_KERNEL_PTX_PATH);

        let module = ctx.load_module(ptx).map_err(|e| {
            BackendError::Validation(format!(
                "Не удалось загрузить PTX-модуль '{}' в CUDA context: {:?}",
                GPU_KERNEL_PTX_PATH, e
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

    fn arrival_params(spec: &ArrivalProcessSpec) -> (u32, u32, f64, f64) {
        match spec {
            ArrivalProcessSpec::Poisson => (0, 0, 0.5, 1.0),
            ArrivalProcessSpec::Erlang { order } => (1, *order as u32, 0.5, 1.0),
            ArrivalProcessSpec::Hyperexponential2 {
                p,
                fast_rate_multiplier,
            } => (2, 0, *p, *fast_rate_multiplier),
        }
    }

    fn workload_params(spec: &WorkloadDistributionSpec) -> (u32, u32, f64, f64, f64) {
        match spec {
            WorkloadDistributionSpec::Deterministic { mean, .. } => (0, 0, *mean, 0.5, 1.0),
            WorkloadDistributionSpec::Exponential { mean, .. } => (1, 0, *mean, 0.5, 1.0),
            WorkloadDistributionSpec::Erlang { mean, order, .. } => {
                (2, *order as u32, *mean, 0.5, 1.0)
            }
            WorkloadDistributionSpec::Hyperexponential2 {
                mean,
                p,
                fast_rate_multiplier,
                ..
            } => (3, 0, *mean, *p, *fast_rate_multiplier),
        }
    }

    fn run_group_on_gpu(
        &self,
        requests: &[RunRequest],
        ctx: &Arc<CudaContext>,
        kernel: &cudarc::driver::CudaFunction,
    ) -> Result<(Vec<RunSummary>, GpuTimingBreakdown)> {
        let first = requests
            .first()
            .ok_or_else(|| BackendError::Validation("Пустая группа GPU-запросов".to_string()))?;
        self.validate_request(first)?;
        let scenario = &first.scenario;
        for request in requests {
            self.validate_request(request)?;
            if request.scenario.scenario_key != scenario.scenario_key {
                return Err(BackendError::Validation(
                    "GPU batched launch ожидает группу одинаковых сценариев".to_string(),
                ));
            }
        }

        let num_runs = requests.len();
        let num_runs_u32 = num_runs as u32;
        let stream = ctx.default_stream();
        let mut timings = GpuTimingBreakdown::default();

        let resource_values = Self::padded_resource_values(&scenario.resource_distribution.values);
        let resource_cdf =
            Self::cumulative_resource_cdf(&scenario.resource_distribution.probabilities);

        let (arrival_mode, arrival_order, arrival_p, arrival_fast_mult) =
            Self::arrival_params(&scenario.arrival_spec);
        let (workload_mode, workload_order, workload_mean, workload_p, workload_fast_mult) =
            Self::workload_params(&scenario.workload_spec);

        let htod_started = Instant::now();
        let seed_host: Vec<u64> = requests.iter().map(|r| r.seed).collect();
        let seed_dev = stream.clone_htod(&seed_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy seed vector failed: {:?}", e))
        })?;
        timings.htod += htod_started.elapsed();

        let mut out_arrival_attempts = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_arrival_attempts failed: {:?}", e))
        })?;
        let mut out_accepted_arrivals = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_accepted_arrivals failed: {:?}", e))
        })?;
        let mut out_rejected_arrivals = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_arrivals failed: {:?}", e))
        })?;
        let mut out_rejected_capacity = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_capacity failed: {:?}", e))
        })?;
        let mut out_rejected_server = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_server failed: {:?}", e))
        })?;
        let mut out_rejected_resource = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_rejected_resource failed: {:?}", e))
        })?;
        let mut out_completed_jobs = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_completed_jobs failed: {:?}", e))
        })?;
        let mut out_completed_time_samples = stream.alloc_zeros::<u64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_completed_time_samples failed: {:?}", e))
        })?;

        let mut out_resource_time = stream.alloc_zeros::<f64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_resource_time failed: {:?}", e))
        })?;
        let mut out_service_time_sum = stream.alloc_zeros::<f64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_service_time_sum failed: {:?}", e))
        })?;
        let mut out_service_time_sq_sum = stream.alloc_zeros::<f64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_service_time_sq_sum failed: {:?}", e))
        })?;
        let mut out_sojourn_time_sum = stream.alloc_zeros::<f64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_sojourn_time_sum failed: {:?}", e))
        })?;
        let mut out_sojourn_time_sq_sum = stream.alloc_zeros::<f64>(num_runs).map_err(|e| {
            BackendError::Validation(format!("alloc out_sojourn_time_sq_sum failed: {:?}", e))
        })?;

        let state_stride = scenario.capacity_k + 1;
        let state_len = if self.save_pi_hat {
            state_stride * num_runs
        } else {
            1
        };
        let mut out_state_times = stream.alloc_zeros::<f64>(state_len).map_err(|e| {
            BackendError::Validation(format!("alloc out_state_times failed: {:?}", e))
        })?;

        let mut builder = stream.launch_builder(kernel);

        let servers_n_u32 = scenario.servers_n as u32;
        let capacity_k_u32 = scenario.capacity_k as u32;
        let resource_len_u32 = scenario.resource_distribution.values.len() as u32;
        let collect_state_times_u32 = if self.save_pi_hat { 1_u32 } else { 0_u32 };

        builder.arg(&num_runs_u32);
        builder.arg(&scenario.arrival_rate);
        builder.arg(&scenario.service_speed);
        builder.arg(&scenario.max_time);
        builder.arg(&scenario.warmup_time);
        builder.arg(&servers_n_u32);
        builder.arg(&capacity_k_u32);
        builder.arg(&scenario.total_resource_r);
        builder.arg(&seed_dev);

        builder.arg(&arrival_mode);
        builder.arg(&arrival_order);
        builder.arg(&arrival_p);
        builder.arg(&arrival_fast_mult);

        builder.arg(&workload_mode);
        builder.arg(&workload_order);
        builder.arg(&workload_mean);
        builder.arg(&workload_p);
        builder.arg(&workload_fast_mult);
        builder.arg(&collect_state_times_u32);

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

        let kernel_started = Instant::now();
        unsafe {
            let blocks = num_runs_u32.div_ceil(self.block_size);
            let launch_cfg = LaunchConfig {
                grid_dim: (blocks, 1, 1),
                block_dim: (self.block_size, 1, 1),
                shared_mem_bytes: 0,
            };
            builder.launch(launch_cfg).map_err(|e| {
                BackendError::Validation(format!(
                    "Не удалось запустить simulate_loss_poisson_deterministic: {:?}",
                    e
                ))
            })?;
            stream.synchronize().map_err(|e| {
                BackendError::Validation(format!("Ошибка синхронизации CUDA stream: {:?}", e))
            })?;
        }
        timings.kernel += kernel_started.elapsed();

        let dtoh_started = Instant::now();
        let arrival_attempts = stream.clone_dtoh(&out_arrival_attempts).map_err(|e| {
            BackendError::Validation(format!("dtoh arrival_attempts failed: {:?}", e))
        })?;
        let accepted_arrivals = stream.clone_dtoh(&out_accepted_arrivals).map_err(|e| {
            BackendError::Validation(format!("dtoh accepted_arrivals failed: {:?}", e))
        })?;
        let rejected_arrivals = stream.clone_dtoh(&out_rejected_arrivals).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_arrivals failed: {:?}", e))
        })?;
        let rejected_capacity = stream.clone_dtoh(&out_rejected_capacity).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_capacity failed: {:?}", e))
        })?;
        let rejected_server = stream.clone_dtoh(&out_rejected_server).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_server failed: {:?}", e))
        })?;
        let rejected_resource = stream.clone_dtoh(&out_rejected_resource).map_err(|e| {
            BackendError::Validation(format!("dtoh rejected_resource failed: {:?}", e))
        })?;
        let completed_jobs = stream.clone_dtoh(&out_completed_jobs).map_err(|e| {
            BackendError::Validation(format!("dtoh completed_jobs failed: {:?}", e))
        })?;
        let completed_time_samples =
            stream
                .clone_dtoh(&out_completed_time_samples)
                .map_err(|e| {
                    BackendError::Validation(format!("dtoh completed_time_samples failed: {:?}", e))
                })?;

        let resource_time = stream
            .clone_dtoh(&out_resource_time)
            .map_err(|e| BackendError::Validation(format!("dtoh resource_time failed: {:?}", e)))?;
        let service_time_sum = stream.clone_dtoh(&out_service_time_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh service_time_sum failed: {:?}", e))
        })?;
        let service_time_sq_sum = stream.clone_dtoh(&out_service_time_sq_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh service_time_sq_sum failed: {:?}", e))
        })?;
        let sojourn_time_sum = stream.clone_dtoh(&out_sojourn_time_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh sojourn_time_sum failed: {:?}", e))
        })?;
        let sojourn_time_sq_sum = stream.clone_dtoh(&out_sojourn_time_sq_sum).map_err(|e| {
            BackendError::Validation(format!("dtoh sojourn_time_sq_sum failed: {:?}", e))
        })?;

        let state_times = if self.save_pi_hat {
            stream.clone_dtoh(&out_state_times).map_err(|e| {
                BackendError::Validation(format!("dtoh state_times failed: {:?}", e))
            })?
        } else {
            Vec::new()
        };
        timings.dtoh += dtoh_started.elapsed();

        let observed_time = scenario.max_time - scenario.warmup_time;
        let mut summaries = Vec::with_capacity(num_runs);
        let summary_started = Instant::now();
        let fallback_pi_hat = if self.save_pi_hat {
            Vec::new()
        } else {
            let mut v = vec![0.0; state_stride];
            if !v.is_empty() {
                v[0] = 1.0;
            }
            v
        };

        for run_id in 0..num_runs {
            let state_offset = run_id * state_stride;
            let pi_hat: Vec<f64> = if self.save_pi_hat {
                state_times[state_offset..state_offset + state_stride]
                    .iter()
                    .map(|x| *x / observed_time)
                    .collect()
            } else {
                fallback_pi_hat.clone()
            };

            let mean_num_jobs = if self.save_pi_hat {
                pi_hat
                    .iter()
                    .enumerate()
                    .map(|(k, p)| k as f64 * *p)
                    .sum::<f64>()
            } else {
                0.0
            };

            let mean_occupied_resource = resource_time[run_id] / observed_time;
            let loss_probability = if arrival_attempts[run_id] > 0 {
                rejected_arrivals[run_id] as f64 / arrival_attempts[run_id] as f64
            } else {
                0.0
            };
            let throughput = completed_jobs[run_id] as f64 / observed_time;

            let n = completed_time_samples[run_id] as f64;
            let mean_service_time = if n > 0.0 {
                service_time_sum[run_id] / n
            } else {
                0.0
            };
            let mean_sojourn_time = if n > 0.0 {
                sojourn_time_sum[run_id] / n
            } else {
                0.0
            };

            let std_service_time = if n > 0.0 {
                ((service_time_sq_sum[run_id] / n) - mean_service_time * mean_service_time)
                    .max(0.0)
                    .sqrt()
            } else {
                0.0
            };

            let std_sojourn_time = if n > 0.0 {
                ((sojourn_time_sq_sum[run_id] / n) - mean_sojourn_time * mean_sojourn_time)
                    .max(0.0)
                    .sqrt()
            } else {
                0.0
            };

            let request = &requests[run_id];
            let summary = RunSummary {
                scenario_key: scenario.scenario_key.clone(),
                scenario_name: scenario.scenario_name.clone(),
                replication_index: request.replication_index,
                seed: request.seed,

                total_time: scenario.max_time,
                warmup_time: scenario.warmup_time,
                observed_time,

                arrival_attempts: arrival_attempts[run_id],
                accepted_arrivals: accepted_arrivals[run_id],
                rejected_arrivals: rejected_arrivals[run_id],
                rejected_capacity: rejected_capacity[run_id],
                rejected_server: rejected_server[run_id],
                rejected_resource: rejected_resource[run_id],
                completed_jobs: completed_jobs[run_id],
                completed_time_samples: completed_time_samples[run_id],

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
            summaries.push(summary);
        }
        timings.summary += summary_started.elapsed();

        Ok((summaries, timings))
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
        let mut timings = GpuTimingBreakdown::default();

        let mut out = Vec::with_capacity(requests.len());
        let mut group_start = 0usize;
        while group_start < requests.len() {
            let scenario_key = &requests[group_start].scenario.scenario_key;
            let mut group_end = group_start + 1;
            while group_end < requests.len()
                && requests[group_end].scenario.scenario_key == *scenario_key
                && group_end - group_start < self.max_batch_size
            {
                group_end += 1;
            }

            let (summaries, group_timings) =
                self.run_group_on_gpu(&requests[group_start..group_end], &ctx, &kernel)?;
            out.extend(summaries);
            timings.htod += group_timings.htod;
            timings.kernel += group_timings.kernel;
            timings.dtoh += group_timings.dtoh;
            timings.summary += group_timings.summary;
            group_start = group_end;
        }

        eprintln!(
            "GPU real test backend finished: {} run(s). block_size={}, save_pi_hat={}, htod={:.3}s, kernel={:.3}s, dtoh={:.3}s, summary={:.3}s",
            out.len(),
            self.block_size,
            self.save_pi_hat,
            timings.htod.as_secs_f64(),
            timings.kernel.as_secs_f64(),
            timings.dtoh.as_secs_f64(),
            timings.summary.as_secs_f64(),
        );

        Ok(out)
    }
}
