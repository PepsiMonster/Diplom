use super::{BackendError, Result, RunRequest, SimulationBackend};
use crate::params::{ArrivalProcessSpec, ResourceDistributionSpec, WorkloadDistributionSpec};
use crate::stats::RunSummary;
use rand::distributions::{Distribution, WeightedIndex};
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use rand_distr::{Exp, Gamma};
use rayon::prelude::*;
use std::f64::INFINITY;

const COMPLETION_TOL: f64 = 1e-12;
const TIME_EPS: f64 = 1e-12;

#[derive(Debug, Clone, Default)]
pub struct CpuRefBackend;

impl CpuRefBackend {
    pub fn new() -> Self {
        Self
    }
}

impl SimulationBackend for CpuRefBackend {
    fn kind(&self) -> &'static str {
        "cpu_ref"
    }

    fn execute_batch(&self, requests: &[RunRequest]) -> Result<Vec<RunSummary>> {
        let results: Vec<Result<RunSummary>> = requests
            .par_iter()
            .map(simulate_one_run)
            .collect();

        results.into_iter().collect()
    }
}

#[derive(Debug, Clone)]
struct ActiveJob {
    arrival_time: f64,
    resource_demand: u32,
    remaining_workload: f64,
}

#[derive(Debug, Clone)]
struct ResourceSampler {
    values: Vec<u32>,
    dist: WeightedIndex<f64>,
}

impl ResourceSampler {
    fn new(spec: &ResourceDistributionSpec) -> Result<Self> {
        let dist = WeightedIndex::new(spec.probabilities.clone()).map_err(|e| {
            BackendError::Validation(format!(
                "Некорректные probabilities для resource distribution: {e}"
            ))
        })?;

        Ok(Self {
            values: spec.values.clone(),
            dist,
        })
    }

    fn sample(&self, rng: &mut StdRng) -> u32 {
        let idx = self.dist.sample(rng);
        self.values[idx]
    }
}

#[derive(Debug, Clone)]
enum WorkloadSampler {
    Deterministic { value: f64 },
    Exponential { dist: Exp<f64> },
    Erlang { dist: Gamma<f64> },
    Hyperexp2 {
        p: f64,
        fast: Exp<f64>,
        slow: Exp<f64>,
    },
}

impl WorkloadSampler {
    fn new(spec: &WorkloadDistributionSpec) -> Result<Self> {
        match spec {
            WorkloadDistributionSpec::Deterministic { mean, .. } => Ok(Self::Deterministic {
                value: *mean,
            }),

            WorkloadDistributionSpec::Exponential { mean, .. } => {
                let rate = 1.0 / *mean;
                let dist = Exp::new(rate).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать Exp(rate={rate}) для workload: {e}"
                    ))
                })?;
                Ok(Self::Exponential { dist })
            }

            WorkloadDistributionSpec::Erlang { mean, order, .. } => {
                if *order == 0 {
                    return Err(BackendError::Validation(
                        "Параметр workload Erlang order должен быть > 0".to_string(),
                    ));
                }

                let shape = *order as f64;
                let scale = *mean / shape;
                let dist = Gamma::new(shape, scale).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать Gamma(shape={shape}, scale={scale}) для workload Erlang: {e}"
                    ))
                })?;
                Ok(Self::Erlang { dist })
            }

            WorkloadDistributionSpec::Hyperexponential2 {
                mean,
                p,
                fast_rate_multiplier,
                ..
            } => {
                let rate_1 = fast_rate_multiplier / mean;
                let denominator = mean - p / rate_1;
                if denominator <= 0.0 {
                    return Err(BackendError::Validation(
                        "Некорректные параметры workload HyperExp(2): невозможно подобрать вторую интенсивность".to_string(),
                    ));
                }
                let rate_2 = (1.0 - p) / denominator;

                let fast = Exp::new(rate_1).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать fast Exp(rate={rate_1}) для workload HyperExp(2): {e}"
                    ))
                })?;
                let slow = Exp::new(rate_2).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать slow Exp(rate={rate_2}) для workload HyperExp(2): {e}"
                    ))
                })?;

                Ok(Self::Hyperexp2 {
                    p: *p,
                    fast,
                    slow,
                })
            }
        }
    }

    fn sample(&self, rng: &mut StdRng) -> f64 {
        match self {
            Self::Deterministic { value } => *value,
            Self::Exponential { dist } => dist.sample(rng),
            Self::Erlang { dist } => dist.sample(rng),
            Self::Hyperexp2 { p, fast, slow } => {
                if rng.gen_bool(*p) {
                    fast.sample(rng)
                } else {
                    slow.sample(rng)
                }
            }
        }
    }
}

#[derive(Debug, Clone)]
enum ArrivalSampler {
    Poisson { dist: Exp<f64> },
    Erlang { dist: Gamma<f64> },
    Hyperexp2 {
        p: f64,
        fast: Exp<f64>,
        slow: Exp<f64>,
    },
}

impl ArrivalSampler {
    fn new(spec: &ArrivalProcessSpec, arrival_rate: f64) -> Result<Self> {
        if arrival_rate < 0.0 || !arrival_rate.is_finite() {
            return Err(BackendError::Validation(format!(
                "arrival_rate должен быть конечным числом >= 0, получено: {arrival_rate}"
            )));
        }

        if arrival_rate == 0.0 {
            let dist = Exp::new(1.0).map_err(|e| {
                BackendError::Validation(format!(
                    "Не удалось создать служебный Exp(rate=1.0) для нулевого потока: {e}"
                ))
            })?;
            return Ok(Self::Poisson { dist });
        }

        match spec {
            ArrivalProcessSpec::Poisson => {
                let dist = Exp::new(arrival_rate).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать Exp(rate={arrival_rate}) для Poisson arrivals: {e}"
                    ))
                })?;
                Ok(Self::Poisson { dist })
            }

            ArrivalProcessSpec::Erlang { order } => {
                if *order == 0 {
                    return Err(BackendError::Validation(
                        "Параметр arrival Erlang order должен быть > 0".to_string(),
                    ));
                }

                let shape = *order as f64;
                let scale = 1.0 / (shape * arrival_rate);
                let dist = Gamma::new(shape, scale).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать Gamma(shape={shape}, scale={scale}) для Erlang arrivals: {e}"
                    ))
                })?;
                Ok(Self::Erlang { dist })
            }

            ArrivalProcessSpec::Hyperexponential2 {
                p,
                fast_rate_multiplier,
            } => {
                let rate_1 = fast_rate_multiplier * arrival_rate;
                let target_mean = 1.0 / arrival_rate;
                let denominator = target_mean - p / rate_1;
                if denominator <= 0.0 {
                    return Err(BackendError::Validation(
                        "Некорректные параметры arrival HyperExp(2): невозможно подобрать вторую интенсивность".to_string(),
                    ));
                }
                let rate_2 = (1.0 - p) / denominator;

                let fast = Exp::new(rate_1).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать fast Exp(rate={rate_1}) для arrival HyperExp(2): {e}"
                    ))
                })?;
                let slow = Exp::new(rate_2).map_err(|e| {
                    BackendError::Validation(format!(
                        "Не удалось создать slow Exp(rate={rate_2}) для arrival HyperExp(2): {e}"
                    ))
                })?;

                Ok(Self::Hyperexp2 {
                    p: *p,
                    fast,
                    slow,
                })
            }
        }
    }

    fn sample_delta(&self, rng: &mut StdRng, arrival_rate: f64) -> f64 {
        if arrival_rate == 0.0 {
            return INFINITY;
        }

        match self {
            Self::Poisson { dist } => dist.sample(rng),
            Self::Erlang { dist } => dist.sample(rng),
            Self::Hyperexp2 { p, fast, slow } => {
                if rng.gen_bool(*p) {
                    fast.sample(rng)
                } else {
                    slow.sample(rng)
                }
            }
        }
    }
}

#[derive(Debug, Clone, Default)]
struct TimeAccumulators {
    state_times: Vec<f64>,
    resource_time_integral: f64,

    arrival_attempts: u64,
    accepted_arrivals: u64,
    rejected_arrivals: u64,
    rejected_capacity: u64,
    rejected_server: u64,
    rejected_resource: u64,
    completed_jobs: u64,
    completed_time_samples: u64,

    completed_service_time_sum: f64,
    completed_service_time_sq_sum: f64,
    completed_sojourn_time_sum: f64,
    completed_sojourn_time_sq_sum: f64,
}

fn simulate_one_run(request: &RunRequest) -> Result<RunSummary> {
    let scenario = &request.scenario;

    if scenario.warmup_time >= scenario.max_time {
        return Err(BackendError::Validation(format!(
            "warmup_time должен быть строго меньше max_time, получено {} >= {}",
            scenario.warmup_time, scenario.max_time
        )));
    }

    let mut rng = StdRng::seed_from_u64(request.seed);

    let resource_sampler = ResourceSampler::new(&scenario.resource_distribution)?;
    let workload_sampler = WorkloadSampler::new(&scenario.workload_spec)?;
    let arrival_sampler = ArrivalSampler::new(&scenario.arrival_spec, scenario.arrival_rate)?;

    let mut acc = TimeAccumulators {
        state_times: vec![0.0; scenario.capacity_k + 1],
        ..Default::default()
    };

    let mut current_time = 0.0_f64;
    let mut occupied_resource_total: u32 = 0;
    let mut active_jobs: Vec<ActiveJob> = Vec::new();

    let mut next_arrival_time = if scenario.arrival_rate == 0.0 {
        INFINITY
    } else {
        arrival_sampler.sample_delta(&mut rng, scenario.arrival_rate)
    };

    while current_time < scenario.max_time {
        let next_completion_time = next_completion_time(&active_jobs, current_time, scenario.service_speed);

        let next_event_time = next_arrival_time
            .min(next_completion_time)
            .min(scenario.max_time);

        observe_interval(
            &mut acc,
            current_time,
            next_event_time,
            active_jobs.len(),
            occupied_resource_total,
            scenario.warmup_time,
            scenario.max_time,
            scenario.capacity_k,
        )?;

        let dt = next_event_time - current_time;
        if dt < -TIME_EPS {
            return Err(BackendError::Validation(format!(
                "Получен отрицательный шаг времени dt={dt}"
            )));
        }

        if dt > 0.0 {
            for job in &mut active_jobs {
                job.remaining_workload = (job.remaining_workload - scenario.service_speed * dt).max(0.0);
            }
        }

        current_time = next_event_time;

        if current_time >= scenario.max_time - TIME_EPS {
            break;
        }

        let arrival_happened = (next_arrival_time - current_time).abs() <= TIME_EPS
            && next_arrival_time <= next_completion_time + TIME_EPS;

        if arrival_happened {
            process_arrival(
                &mut rng,
                &mut acc,
                &mut active_jobs,
                &mut occupied_resource_total,
                current_time,
                scenario.capacity_k,
                scenario.servers_n,
                scenario.total_resource_r,
                &resource_sampler,
                &workload_sampler,
                scenario.warmup_time,
                scenario.max_time,
            );

            next_arrival_time = if scenario.arrival_rate == 0.0 {
                INFINITY
            } else {
                current_time + arrival_sampler.sample_delta(&mut rng, scenario.arrival_rate)
            };
        } else {
            process_completions(
                &mut acc,
                &mut active_jobs,
                &mut occupied_resource_total,
                current_time,
                scenario.warmup_time,
                scenario.max_time,
            );
        }
    }

    build_run_summary(request, acc)
}

fn build_run_summary(request: &RunRequest, acc: TimeAccumulators) -> Result<RunSummary> {
    let scenario = &request.scenario;
    let observed_time = scenario.max_time - scenario.warmup_time;
    if observed_time <= 0.0 {
        return Err(BackendError::Validation(format!(
            "observed_time должно быть > 0, получено: {observed_time}"
        )));
    }

    let pi_hat: Vec<f64> = acc
        .state_times
        .iter()
        .map(|time_in_state| time_in_state / observed_time)
        .collect();

    let mean_num_jobs = pi_hat
        .iter()
        .enumerate()
        .map(|(k, p)| k as f64 * *p)
        .sum::<f64>();

    let mean_occupied_resource = acc.resource_time_integral / observed_time;

    let loss_probability = if acc.arrival_attempts > 0 {
        acc.rejected_arrivals as f64 / acc.arrival_attempts as f64
    } else {
        0.0
    };

    let throughput = acc.completed_jobs as f64 / observed_time;

    let n = acc.completed_time_samples as f64;
    let mean_service_time = if n > 0.0 {
        acc.completed_service_time_sum / n
    } else {
        0.0
    };
    let mean_sojourn_time = if n > 0.0 {
        acc.completed_sojourn_time_sum / n
    } else {
        0.0
    };
    let std_service_time = if n > 0.0 {
        let var = (acc.completed_service_time_sq_sum / n) - mean_service_time * mean_service_time;
        var.max(0.0).sqrt()
    } else {
        0.0
    };
    let std_sojourn_time = if n > 0.0 {
        let var = (acc.completed_sojourn_time_sq_sum / n) - mean_sojourn_time * mean_sojourn_time;
        var.max(0.0).sqrt()
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

        arrival_attempts: acc.arrival_attempts,
        accepted_arrivals: acc.accepted_arrivals,
        rejected_arrivals: acc.rejected_arrivals,
        rejected_capacity: acc.rejected_capacity,
        rejected_server: acc.rejected_server,
        rejected_resource: acc.rejected_resource,
        completed_jobs: acc.completed_jobs,
        completed_time_samples: acc.completed_time_samples,

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

fn observe_interval(
    acc: &mut TimeAccumulators,
    t0: f64,
    t1: f64,
    num_jobs: usize,
    occupied_resource: u32,
    warmup_time: f64,
    max_time: f64,
    capacity_k: usize,
) -> Result<()> {
    if t1 < t0 {
        return Err(BackendError::Validation(format!(
            "Ожидалось t1 >= t0, получено t0={t0}, t1={t1}"
        )));
    }

    if num_jobs > capacity_k {
        return Err(BackendError::Validation(format!(
            "num_jobs={} превышает capacity_k={}",
            num_jobs, capacity_k
        )));
    }

    let overlap = interval_overlap_length(t0, t1, warmup_time, max_time);
    if overlap <= 0.0 {
        return Ok(());
    }

    acc.state_times[num_jobs] += overlap;
    acc.resource_time_integral += occupied_resource as f64 * overlap;
    Ok(())
}

fn process_arrival(
    rng: &mut StdRng,
    acc: &mut TimeAccumulators,
    active_jobs: &mut Vec<ActiveJob>,
    occupied_resource_total: &mut u32,
    event_time: f64,
    capacity_k: usize,
    servers_n: usize,
    total_resource_r: u32,
    resource_sampler: &ResourceSampler,
    workload_sampler: &WorkloadSampler,
    warmup_time: f64,
    max_time: f64,
) {
    if is_in_observation_window(event_time, warmup_time, max_time) {
        acc.arrival_attempts += 1;
    }

    let resource_demand = resource_sampler.sample(rng);
    let workload = workload_sampler.sample(rng);

    let rejection_reason = if active_jobs.len() >= capacity_k || active_jobs.len() >= servers_n {
        Some("capacity")
    } else if occupied_resource_total.saturating_add(resource_demand) > total_resource_r {
        Some("resource")
    } else {
        None
    };

    match rejection_reason {
        Some("capacity") => {
            if is_in_observation_window(event_time, warmup_time, max_time) {
                acc.rejected_arrivals += 1;
                acc.rejected_capacity += 1;
            }
        }
        Some("resource") => {
            if is_in_observation_window(event_time, warmup_time, max_time) {
                acc.rejected_arrivals += 1;
                acc.rejected_resource += 1;
            }
        }
        _ => {
            active_jobs.push(ActiveJob {
                arrival_time: event_time,
                resource_demand,
                remaining_workload: workload,
            });
            *occupied_resource_total += resource_demand;

            if is_in_observation_window(event_time, warmup_time, max_time) {
                acc.accepted_arrivals += 1;
            }
        }
    }
}

fn process_completions(
    acc: &mut TimeAccumulators,
    active_jobs: &mut Vec<ActiveJob>,
    occupied_resource_total: &mut u32,
    event_time: f64,
    warmup_time: f64,
    max_time: f64,
) {
    let mut idx = 0usize;

    while idx < active_jobs.len() {
        if active_jobs[idx].remaining_workload <= COMPLETION_TOL {
            let job = active_jobs.swap_remove(idx);
            *occupied_resource_total = occupied_resource_total.saturating_sub(job.resource_demand);

            if is_in_observation_window(event_time, warmup_time, max_time) {
                let service_time = (event_time - job.arrival_time).max(0.0);
                let sojourn_time = service_time;

                acc.completed_jobs += 1;
                acc.completed_time_samples += 1;

                acc.completed_service_time_sum += service_time;
                acc.completed_service_time_sq_sum += service_time * service_time;

                acc.completed_sojourn_time_sum += sojourn_time;
                acc.completed_sojourn_time_sq_sum += sojourn_time * sojourn_time;
            }
        } else {
            idx += 1;
        }
    }
}

fn next_completion_time(active_jobs: &[ActiveJob], current_time: f64, service_speed: f64) -> f64 {
    if active_jobs.is_empty() {
        return INFINITY;
    }

    let best_dt = active_jobs
        .iter()
        .map(|job| {
            if service_speed <= 0.0 {
                INFINITY
            } else {
                job.remaining_workload / service_speed
            }
        })
        .fold(INFINITY, f64::min);

    current_time + best_dt
}

fn interval_overlap_length(a0: f64, a1: f64, b0: f64, b1: f64) -> f64 {
    let left = a0.max(b0);
    let right = a1.min(b1);
    (right - left).max(0.0)
}

fn is_in_observation_window(time_point: f64, warmup_time: f64, max_time: f64) -> bool {
    warmup_time <= time_point && time_point <= max_time
}