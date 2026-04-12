use super::{BackendError, Result, RunRequest, SimulationBackend};
use crate::params::{ArrivalProcessSpec, WorkloadDistributionSpec};
use crate::stats::RunSummary;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use cudarc::{
    driver::{CudaContext, LaunchConfig, PushKernelArg},
    nvrtc::Ptx,
};

const GPU_KERNEL_PTX_PATH: &str = "cuda/sim_kernel.ptx";

#[derive(Debug, Default, Clone, Copy)]
struct GpuTimingBreakdown {
    setup_context: Duration,
    kernel: Duration,
    dtoh: Duration,
    summary: Duration,
}

#[derive(Debug)]
struct GpuRuntime {
    ctx: Arc<CudaContext>,
    kernel: cudarc::driver::CudaFunction,
}

#[derive(Debug)]
pub struct GpuBackend {
    pub max_batch_size: usize,
    pub block_size: u32,
    pub save_pi_hat: bool,
    runtime: Mutex<Option<GpuRuntime>>,
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
            runtime: Mutex::new(None),
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

    fn get_or_init_runtime(
        &self,
    ) -> Result<(Arc<CudaContext>, cudarc::driver::CudaFunction, Duration)> {
        let started = Instant::now();
        let mut guard = self.runtime.lock().map_err(|_| {
            BackendError::Validation("Не удалось захватить lock runtime GPU backend".to_string())
        })?;

        if guard.is_none() {
            let ctx = CudaContext::new(0).map_err(|e| {
                BackendError::Validation(format!(
                    "Не удалось создать CUDA context на device 0: {:?}",
                    e
                ))
            })?;
            let kernel = self.compile_and_load_kernel(&ctx)?;
            *guard = Some(GpuRuntime { ctx, kernel });
        }

        let runtime = guard.as_ref().ok_or_else(|| {
            BackendError::Validation("GPU runtime не инициализирован".to_string())
        })?;

        Ok((
            runtime.ctx.clone(),
            runtime.kernel.clone(),
            started.elapsed(),
        ))
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
        let mut timings = GpuTimingBreakdown::default();
        requests
            .first()
            .ok_or_else(|| BackendError::Validation("Пустая группа GPU-запросов".to_string()))?;
        for request in requests {
            self.validate_request(request)?;
        }

        let num_runs = requests.len();
        let num_runs_u32 = num_runs as u32;
        let stream = ctx.default_stream();

        let mut arrival_rate_host = Vec::with_capacity(num_runs);
        let mut service_speed_host = Vec::with_capacity(num_runs);
        let mut max_time_host = Vec::with_capacity(num_runs);
        let mut warmup_time_host = Vec::with_capacity(num_runs);
        let mut servers_n_host = Vec::with_capacity(num_runs);
        let mut capacity_k_host = Vec::with_capacity(num_runs);
        let mut total_resource_r_host = Vec::with_capacity(num_runs);
        let mut arrival_mode_host = Vec::with_capacity(num_runs);
        let mut arrival_order_host = Vec::with_capacity(num_runs);
        let mut arrival_p_host = Vec::with_capacity(num_runs);
        let mut arrival_fast_mult_host = Vec::with_capacity(num_runs);
        let mut workload_mode_host = Vec::with_capacity(num_runs);
        let mut workload_order_host = Vec::with_capacity(num_runs);
        let mut workload_mean_host = Vec::with_capacity(num_runs);
        let mut workload_p_host = Vec::with_capacity(num_runs);
        let mut workload_fast_mult_host = Vec::with_capacity(num_runs);
        let mut resource_len_host = Vec::with_capacity(num_runs);
        let mut resource_values_host = Vec::with_capacity(num_runs * 8);
        let mut resource_cdf_host = Vec::with_capacity(num_runs * 8);

        for request in requests {
            let scenario = &request.scenario;
            let (arrival_mode, arrival_order, arrival_p, arrival_fast_mult) =
                Self::arrival_params(&scenario.arrival_spec);
            let (workload_mode, workload_order, workload_mean, workload_p, workload_fast_mult) =
                Self::workload_params(&scenario.workload_spec);
            let resource_values =
                Self::padded_resource_values(&scenario.resource_distribution.values);
            let resource_cdf =
                Self::cumulative_resource_cdf(&scenario.resource_distribution.probabilities);

            arrival_rate_host.push(scenario.arrival_rate);
            service_speed_host.push(scenario.service_speed);
            max_time_host.push(scenario.max_time);
            warmup_time_host.push(scenario.warmup_time);
            servers_n_host.push(scenario.servers_n as u32);
            capacity_k_host.push(scenario.capacity_k as u32);
            total_resource_r_host.push(scenario.total_resource_r);
            arrival_mode_host.push(arrival_mode);
            arrival_order_host.push(arrival_order);
            arrival_p_host.push(arrival_p);
            arrival_fast_mult_host.push(arrival_fast_mult);
            workload_mode_host.push(workload_mode);
            workload_order_host.push(workload_order);
            workload_mean_host.push(workload_mean);
            workload_p_host.push(workload_p);
            workload_fast_mult_host.push(workload_fast_mult);
            resource_len_host.push(scenario.resource_distribution.values.len() as u32);
            resource_values_host.extend_from_slice(&resource_values);
            resource_cdf_host.extend_from_slice(&resource_cdf);
        }

        let seed_host: Vec<u64> = requests.iter().map(|r| r.seed).collect();
        let seed_dev = stream.clone_htod(&seed_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy seed vector failed: {:?}", e))
        })?;
        let arrival_rate_dev = stream.clone_htod(&arrival_rate_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy arrival_rate failed: {:?}", e))
        })?;
        let service_speed_dev = stream.clone_htod(&service_speed_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy service_speed failed: {:?}", e))
        })?;
        let max_time_dev = stream.clone_htod(&max_time_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy max_time failed: {:?}", e))
        })?;
        let warmup_time_dev = stream.clone_htod(&warmup_time_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy warmup_time failed: {:?}", e))
        })?;
        let servers_n_dev = stream.clone_htod(&servers_n_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy servers_n failed: {:?}", e))
        })?;
        let capacity_k_dev = stream.clone_htod(&capacity_k_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy capacity_k failed: {:?}", e))
        })?;
        let total_resource_r_dev = stream.clone_htod(&total_resource_r_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy total_resource_r failed: {:?}", e))
        })?;
        let arrival_mode_dev = stream.clone_htod(&arrival_mode_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy arrival_mode failed: {:?}", e))
        })?;
        let arrival_order_dev = stream.clone_htod(&arrival_order_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy arrival_order failed: {:?}", e))
        })?;
        let arrival_p_dev = stream.clone_htod(&arrival_p_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy arrival_p failed: {:?}", e))
        })?;
        let arrival_fast_mult_dev = stream.clone_htod(&arrival_fast_mult_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy arrival_fast_mult failed: {:?}", e))
        })?;
        let workload_mode_dev = stream.clone_htod(&workload_mode_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy workload_mode failed: {:?}", e))
        })?;
        let workload_order_dev = stream.clone_htod(&workload_order_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy workload_order failed: {:?}", e))
        })?;
        let workload_mean_dev = stream.clone_htod(&workload_mean_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy workload_mean failed: {:?}", e))
        })?;
        let workload_p_dev = stream.clone_htod(&workload_p_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy workload_p failed: {:?}", e))
        })?;
        let workload_fast_mult_dev = stream.clone_htod(&workload_fast_mult_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy workload_fast_mult failed: {:?}", e))
        })?;
        let resource_len_dev = stream.clone_htod(&resource_len_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy resource_len failed: {:?}", e))
        })?;
        let resource_values_dev = stream.clone_htod(&resource_values_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy resource_values failed: {:?}", e))
        })?;
        let resource_cdf_dev = stream.clone_htod(&resource_cdf_host).map_err(|e| {
            BackendError::Validation(format!("alloc/copy resource_cdf failed: {:?}", e))
        })?;

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

        let state_stride = 129usize;
        let state_stride_u32 = state_stride as u32;
        let state_buffer_len = if self.save_pi_hat {
            state_stride * num_runs
        } else {
            1
        };
        let mut out_state_times = stream.alloc_zeros::<f64>(state_buffer_len).map_err(|e| {
            BackendError::Validation(format!("alloc out_state_times failed: {:?}", e))
        })?;

        let mut builder = stream.launch_builder(kernel);

        builder.arg(&num_runs_u32);
        builder.arg(&arrival_rate_dev);
        builder.arg(&service_speed_dev);
        builder.arg(&max_time_dev);
        builder.arg(&warmup_time_dev);
        builder.arg(&servers_n_dev);
        builder.arg(&capacity_k_dev);
        builder.arg(&total_resource_r_dev);
        builder.arg(&seed_dev);

        builder.arg(&arrival_mode_dev);
        builder.arg(&arrival_order_dev);
        builder.arg(&arrival_p_dev);
        builder.arg(&arrival_fast_mult_dev);

        builder.arg(&workload_mode_dev);
        builder.arg(&workload_order_dev);
        builder.arg(&workload_mean_dev);
        builder.arg(&workload_p_dev);
        builder.arg(&workload_fast_mult_dev);

        let collect_state_times_u32 = if self.save_pi_hat { 1_u32 } else { 0_u32 };
        builder.arg(&collect_state_times_u32);
        builder.arg(&state_stride_u32);
        builder.arg(&resource_len_dev);
        builder.arg(&resource_values_dev);
        builder.arg(&resource_cdf_dev);

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
            builder
                .launch(LaunchConfig {
                    grid_dim: ((num_runs_u32 + self.block_size - 1) / self.block_size, 1, 1),
                    block_dim: (self.block_size, 1, 1),
                    shared_mem_bytes: 0,
                })
                .map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось запустить simulate_loss_poisson_deterministic: {:?}",
                        e
                    ))
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

        let mut summaries = Vec::with_capacity(num_runs);
        let summary_started = Instant::now();

        for run_id in 0..num_runs {
            let request = &requests[run_id];
            let scenario = &request.scenario;
            let observed_time = scenario.max_time - scenario.warmup_time;
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
            let (pi_hat, mean_num_jobs) = if self.save_pi_hat {
                let state_offset = run_id * state_stride;
                let scenario_state_len = scenario.capacity_k + 1;
                let pi_hat: Vec<f64> = state_times[state_offset..state_offset + scenario_state_len]
                    .iter()
                    .map(|x| *x / observed_time)
                    .collect();
                let mean_num_jobs = pi_hat
                    .iter()
                    .enumerate()
                    .map(|(k, p)| k as f64 * *p)
                    .sum::<f64>();
                (pi_hat, mean_num_jobs)
            } else {
                // Для benchmark-режима без state_times используем оценку по формуле Литтла.
                (vec![1.0], throughput * mean_sojourn_time)
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

        let (ctx, kernel, setup_elapsed) = self.get_or_init_runtime()?;
        let mut total_timings = GpuTimingBreakdown {
            setup_context: setup_elapsed,
            ..GpuTimingBreakdown::default()
        };
        let mut out = Vec::with_capacity(requests.len());
        let mut chunk_start = 0usize;
        while chunk_start < requests.len() {
            let chunk_end = (chunk_start + self.max_batch_size).min(requests.len());
            let (summaries, timings) =
                self.run_group_on_gpu(&requests[chunk_start..chunk_end], &ctx, &kernel)?;
            out.extend(summaries);
            total_timings.kernel += timings.kernel;
            total_timings.dtoh += timings.dtoh;
            total_timings.summary += timings.summary;
            chunk_start = chunk_end;
        }

        eprintln!("GPU timing breakdown:");
        eprintln!("  setup/context: {:.2?}", total_timings.setup_context);
        eprintln!("  kernel:        {:.2?}", total_timings.kernel);
        eprintln!("  dtoh:          {:.2?}", total_timings.dtoh);
        eprintln!("  summary:       {:.2?}", total_timings.summary);
        eprintln!("GPU backend finished: {} run(s) executed.", out.len());

        Ok(out)
    }
}
