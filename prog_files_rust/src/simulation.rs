use std::collections::{BTreeMap, HashMap};
use std::f64::INFINITY;

use rand::distributions::{Distribution as RandDistribution, WeightedIndex};
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use rand_distr::{Exp, Gamma};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use thiserror::Error;

use crate::model::{AdmissionPlacement, ModelError, RejectionReason, SystemState, COMPLETION_TOL};
use crate::params::{
    ParamsError, ResourceDistributionConfig, ScenarioConfig, SystemArchitecture,
    WorkloadDistributionConfig,
};

#[derive(Debug, Error)]
pub enum SimulationError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Model(#[from] ModelError),

    #[error(transparent)]
    Params(#[from] ParamsError),
}

type Result<T> = std::result::Result<T, SimulationError>;

fn ensure_nonnegative_f64(name: &str, value: f64) -> Result<()> {
    if value < 0.0 {
        return Err(SimulationError::Validation(format!(
            "Параметр '{name}' должен быть >= 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_f64(name: &str, value: f64) -> Result<()> {
    if value <= 0.0 {
        return Err(SimulationError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_usize(name: &str, value: usize) -> Result<()> {
    if value == 0 {
        return Err(SimulationError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSnapshot {
    pub time: f64,
    pub num_jobs: usize,
    pub num_active_jobs: usize,
    pub num_waiting_jobs: usize,
    pub occupied_resource: u32,
    pub arrival_rate: f64,
    pub service_speed: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventRecord {
    pub time: f64,
    pub event_type: String,
    pub job_id: Option<u64>,
    pub num_jobs_before: usize,
    pub num_jobs_after: usize,
    pub occupied_resource_before: u32,
    pub occupied_resource_after: u32,
    pub details: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnimationLogMeta {
    pub system_architecture: String,
    pub servers_n: usize,
    pub capacity_k: usize,
    pub queue_capacity: usize,
    pub total_resource_r: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnimationJobRecord {
    pub job_id: u64,
    pub arrival_time: f64,
    pub resource_demand: u32,
    pub decision: String,
    pub queue_enter_time: Option<f64>,
    pub service_start_time: Option<f64>,
    pub service_end_time: Option<f64>,
    pub lane_id: Option<usize>,
    pub reject_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnimationLog {
    pub meta: AnimationLogMeta,
    pub jobs: Vec<AnimationJobRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationRunResult {
    pub scenario_name: String,
    pub replication_index: usize,
    pub seed: u64,
    pub total_time: f64,
    pub warmup_time: f64,
    pub observed_time: f64,
    pub state_times: Vec<f64>,
    pub pi_hat: Vec<f64>,
    pub mean_num_jobs: f64,
    pub mean_occupied_resource: f64,
    pub mean_queue_length: f64,
    pub mean_waiting_jobs: f64,
    pub arrival_attempts: u64,
    pub accepted_arrivals: u64,
    pub accepted_to_queue: u64,
    pub started_from_queue: u64,
    pub rejected_arrivals: u64,
    pub rejected_capacity: u64,
    pub rejected_server: u64,
    pub rejected_resource: u64,
    pub completed_jobs: u64,
    pub completed_time_samples: u64,
    pub loss_probability: f64,
    pub queueing_probability: f64,
    pub throughput: f64,
    pub mean_service_time: f64,
    pub mean_waiting_time: f64,
    pub mean_sojourn_time: f64,
    pub std_service_time: f64,
    pub std_waiting_time: f64,
    pub std_sojourn_time: f64,
    pub state_trace: Vec<StateSnapshot>,
    pub event_log: Vec<EventRecord>,
    pub animation_log: Option<AnimationLog>,
}

impl SimulationRunResult {
    pub fn flat_summary(&self) -> BTreeMap<String, Value> {
        let mut summary = BTreeMap::new();

        summary.insert("scenario_name".to_string(), json!(self.scenario_name));
        summary.insert(
            "replication_index".to_string(),
            json!(self.replication_index),
        );
        summary.insert("seed".to_string(), json!(self.seed));
        summary.insert("total_time".to_string(), json!(self.total_time));
        summary.insert("warmup_time".to_string(), json!(self.warmup_time));
        summary.insert("observed_time".to_string(), json!(self.observed_time));
        summary.insert("mean_num_jobs".to_string(), json!(self.mean_num_jobs));
        summary.insert(
            "mean_occupied_resource".to_string(),
            json!(self.mean_occupied_resource),
        );
        summary.insert(
            "mean_queue_length".to_string(),
            json!(self.mean_queue_length),
        );
        summary.insert(
            "mean_waiting_jobs".to_string(),
            json!(self.mean_waiting_jobs),
        );
        summary.insert("arrival_attempts".to_string(), json!(self.arrival_attempts));
        summary.insert(
            "accepted_arrivals".to_string(),
            json!(self.accepted_arrivals),
        );
        summary.insert(
            "accepted_to_queue".to_string(),
            json!(self.accepted_to_queue),
        );
        summary.insert(
            "started_from_queue".to_string(),
            json!(self.started_from_queue),
        );
        summary.insert(
            "rejected_arrivals".to_string(),
            json!(self.rejected_arrivals),
        );
        summary.insert(
            "rejected_capacity".to_string(),
            json!(self.rejected_capacity),
        );
        summary.insert("rejected_server".to_string(), json!(self.rejected_server));
        summary.insert(
            "rejected_resource".to_string(),
            json!(self.rejected_resource),
        );
        summary.insert("completed_jobs".to_string(), json!(self.completed_jobs));
        summary.insert(
            "completed_time_samples".to_string(),
            json!(self.completed_time_samples),
        );
        summary.insert("loss_probability".to_string(), json!(self.loss_probability));
        summary.insert(
            "queueing_probability".to_string(),
            json!(self.queueing_probability),
        );
        summary.insert("throughput".to_string(), json!(self.throughput));
        summary.insert(
            "mean_service_time".to_string(),
            json!(self.mean_service_time),
        );
        summary.insert(
            "mean_waiting_time".to_string(),
            json!(self.mean_waiting_time),
        );
        summary.insert(
            "mean_sojourn_time".to_string(),
            json!(self.mean_sojourn_time),
        );
        summary.insert("std_service_time".to_string(), json!(self.std_service_time));
        summary.insert("std_waiting_time".to_string(), json!(self.std_waiting_time));
        summary.insert("std_sojourn_time".to_string(), json!(self.std_sojourn_time));

        for (k, value) in self.pi_hat.iter().enumerate() {
            summary.insert(format!("pi_hat_{k}"), json!(value));
        }

        summary
    }
}

pub fn derive_run_seed(base_seed: u64, replication_index: usize) -> u64 {
    base_seed.wrapping_add(1_000_003u64.wrapping_mul(replication_index as u64))
}

pub fn interval_overlap_length(a0: f64, a1: f64, b0: f64, b1: f64) -> f64 {
    let left = a0.max(b0);
    let right = a1.min(b1);
    (right - left).max(0.0)
}

pub fn sample_resource_demand(
    rng: &mut StdRng,
    config: &ResourceDistributionConfig,
) -> Result<u32> {
    config.validate()?;

    match config {
        ResourceDistributionConfig::Deterministic {
            deterministic_value,
        } => Ok(*deterministic_value),
        ResourceDistributionConfig::DiscreteUniform {
            min_units,
            max_units,
        } => Ok(rng.gen_range(*min_units..=*max_units)),
        ResourceDistributionConfig::DiscreteCustom {
            values,
            probabilities,
        } => {
            let dist = WeightedIndex::new(probabilities).map_err(|e| {
                SimulationError::Validation(format!(
                    "Некорректные probabilities для discrete_custom: {e}"
                ))
            })?;
            let idx = dist.sample(rng);
            Ok(values[idx])
        }
    }
}

pub fn sample_workload(rng: &mut StdRng, config: &WorkloadDistributionConfig) -> Result<f64> {
    config.validate()?;

    match config {
        WorkloadDistributionConfig::Deterministic { mean, .. } => Ok(*mean),

        WorkloadDistributionConfig::Exponential { mean, .. } => {
            let rate = 1.0 / *mean;
            let dist = Exp::new(rate).map_err(|e| {
                SimulationError::Validation(format!(
                    "Не удалось создать Exp(rate={rate}) для workload: {e}"
                ))
            })?;
            Ok(dist.sample(rng))
        }

        WorkloadDistributionConfig::Erlang {
            mean, erlang_order, ..
        } => {
            let shape = *erlang_order as f64;
            let scale = *mean / shape;
            let dist = Gamma::new(shape, scale).map_err(|e| {
                SimulationError::Validation(format!(
                    "Не удалось создать Gamma(shape={shape}, scale={scale}) для Erlang: {e}"
                ))
            })?;
            Ok(dist.sample(rng))
        }

        WorkloadDistributionConfig::Hyperexponential2 {
            hyper_p,
            hyper_rates,
            ..
        } => {
            let branch_first = rng.gen_bool(*hyper_p);
            let rate = if branch_first {
                hyper_rates[0]
            } else {
                hyper_rates[1]
            };
            let dist = Exp::new(rate).map_err(|e| {
                SimulationError::Validation(format!(
                    "Не удалось создать Exp(rate={rate}) для HyperExp(2): {e}"
                ))
            })?;
            Ok(dist.sample(rng))
        }
    }
}

pub fn sample_next_arrival_delta(
    rng: &mut StdRng,
    state: &SystemState,
    scenario: &ScenarioConfig,
) -> Result<f64> {
    let current_rate = state.current_arrival_rate(scenario);
    if current_rate <= 0.0 {
        return Ok(INFINITY);
    }

    let dist = Exp::new(current_rate).map_err(|e| {
        SimulationError::Validation(format!(
            "Не удалось создать Exp(rate={current_rate}) для следующего поступления: {e}"
        ))
    })?;
    Ok(dist.sample(rng))
}

#[derive(Debug, Clone)]
pub struct StatisticsAccumulator {
    pub capacity_k: usize,
    pub total_time: f64,
    pub warmup_time: f64,
    pub state_times: Vec<f64>,
    pub resource_time_integral: f64,
    pub queue_time_integral: f64,
    pub arrival_attempts: u64,
    pub accepted_arrivals: u64,
    pub accepted_to_queue: u64,
    pub started_from_queue: u64,
    pub rejected_arrivals: u64,
    pub rejected_capacity: u64,
    pub rejected_server: u64,
    pub rejected_resource: u64,
    pub completed_jobs: u64,
    pub completed_service_time_sum: f64,
    pub completed_service_time_sq_sum: f64,
    pub completed_waiting_time_sum: f64,
    pub completed_waiting_time_sq_sum: f64,
    pub completed_sojourn_time_sum: f64,
    pub completed_sojourn_time_sq_sum: f64,
    pub completed_time_samples: u64,
}

impl StatisticsAccumulator {
    pub fn new(capacity_k: usize, total_time: f64, warmup_time: f64) -> Result<Self> {
        ensure_positive_usize("capacity_k", capacity_k)?;
        ensure_positive_f64("total_time", total_time)?;
        ensure_nonnegative_f64("warmup_time", warmup_time)?;

        Ok(Self {
            capacity_k,
            total_time,
            warmup_time,
            state_times: vec![0.0; capacity_k + 1],
            resource_time_integral: 0.0,
            queue_time_integral: 0.0,
            arrival_attempts: 0,
            accepted_arrivals: 0,
            accepted_to_queue: 0,
            started_from_queue: 0,
            rejected_arrivals: 0,
            rejected_capacity: 0,
            rejected_server: 0,
            rejected_resource: 0,
            completed_jobs: 0,
            completed_service_time_sum: 0.0,
            completed_service_time_sq_sum: 0.0,
            completed_waiting_time_sum: 0.0,
            completed_waiting_time_sq_sum: 0.0,
            completed_sojourn_time_sum: 0.0,
            completed_sojourn_time_sq_sum: 0.0,
            completed_time_samples: 0,
        })
    }

    pub fn observed_time(&self) -> f64 {
        self.total_time - self.warmup_time
    }

    pub fn is_in_observation_window(&self, time_point: f64) -> bool {
        self.warmup_time <= time_point && time_point <= self.total_time
    }

    pub fn observe_constant_interval(
        &mut self,
        t0: f64,
        t1: f64,
        num_jobs: usize,
        waiting_jobs: usize,
        occupied_resource: u32,
    ) -> Result<()> {
        if t1 < t0 {
            return Err(SimulationError::Validation(format!(
                "Ожидалось t1 >= t0, получено t0={t0}, t1={t1}"
            )));
        }
        if t1 == t0 {
            return Ok(());
        }
        if num_jobs > self.capacity_k {
            return Err(SimulationError::Validation(format!(
                "num_jobs={} превышает capacity_k={}",
                num_jobs, self.capacity_k
            )));
        }

        let overlap = interval_overlap_length(t0, t1, self.warmup_time, self.total_time);
        if overlap <= 0.0 {
            return Ok(());
        }

        self.state_times[num_jobs] += overlap;
        self.resource_time_integral += occupied_resource as f64 * overlap;
        self.queue_time_integral += waiting_jobs as f64 * overlap;
        Ok(())
    }

    pub fn register_arrival_attempt(&mut self, event_time: f64) {
        if self.is_in_observation_window(event_time) {
            self.arrival_attempts += 1;
        }
    }

    pub fn register_admission(&mut self, event_time: f64, queued: bool) {
        if self.is_in_observation_window(event_time) {
            self.accepted_arrivals += 1;
            if queued {
                self.accepted_to_queue += 1;
            }
        }
    }

    pub fn register_started_from_queue(&mut self, event_time: f64) {
        if self.is_in_observation_window(event_time) {
            self.started_from_queue += 1;
        }
    }

    pub fn register_rejection(&mut self, event_time: f64, reason: RejectionReason) {
        if !self.is_in_observation_window(event_time) {
            return;
        }

        self.rejected_arrivals += 1;
        match reason {
            RejectionReason::CapacityLimit => self.rejected_capacity += 1,
            RejectionReason::ServerLimit => self.rejected_server += 1,
            RejectionReason::ResourceLimit => self.rejected_resource += 1,
            RejectionReason::None => {}
        }
    }

    pub fn register_departure(&mut self, event_time: f64) {
        if self.is_in_observation_window(event_time) {
            self.completed_jobs += 1;
        }
    }

    pub fn register_completed_job_times(
        &mut self,
        departure_time: f64,
        arrival_time: f64,
        service_start_time: f64,
    ) {
        if !self.is_in_observation_window(departure_time) {
            return;
        }

        let service_time = (departure_time - service_start_time).max(0.0);
        let waiting_time = (service_start_time - arrival_time).max(0.0);
        let sojourn_time = (departure_time - arrival_time).max(0.0);

        self.completed_service_time_sum += service_time;
        self.completed_service_time_sq_sum += service_time * service_time;
        self.completed_waiting_time_sum += waiting_time;
        self.completed_waiting_time_sq_sum += waiting_time * waiting_time;
        self.completed_sojourn_time_sum += sojourn_time;
        self.completed_sojourn_time_sq_sum += sojourn_time * sojourn_time;
        self.completed_time_samples += 1;
    }

    pub fn build_result(
        self,
        scenario_name: String,
        replication_index: usize,
        seed: u64,
        state_trace: Vec<StateSnapshot>,
        event_log: Vec<EventRecord>,
        animation_log: Option<AnimationLog>,
    ) -> Result<SimulationRunResult> {
        let observed_time = self.observed_time();
        if observed_time <= 0.0 {
            return Err(SimulationError::Validation(format!(
                "observed_time должно быть > 0, получено: {observed_time}. Проверь max_time и warmup_time."
            )));
        }

        let pi_hat: Vec<f64> = self
            .state_times
            .iter()
            .map(|time_in_state| time_in_state / observed_time)
            .collect();

        let mean_num_jobs = pi_hat
            .iter()
            .enumerate()
            .map(|(k, p)| k as f64 * *p)
            .sum::<f64>();

        let mean_occupied_resource = self.resource_time_integral / observed_time;
        let mean_queue_length = self.queue_time_integral / observed_time;
        let mean_waiting_jobs = mean_queue_length;
        let loss_probability = if self.arrival_attempts > 0 {
            self.rejected_arrivals as f64 / self.arrival_attempts as f64
        } else {
            0.0
        };
        let queueing_probability = if self.accepted_arrivals > 0 {
            self.accepted_to_queue as f64 / self.accepted_arrivals as f64
        } else {
            0.0
        };
        let throughput = self.completed_jobs as f64 / observed_time;
        let n = self.completed_time_samples as f64;
        let safe_std = |sum: f64, sum_sq: f64| -> f64 {
            if n <= 0.0 {
                0.0
            } else {
                let mean = sum / n;
                let var = (sum_sq / n) - mean * mean;
                var.max(0.0).sqrt()
            }
        };
        let mean_service_time = if n > 0.0 {
            self.completed_service_time_sum / n
        } else {
            0.0
        };
        let mean_waiting_time = if n > 0.0 {
            self.completed_waiting_time_sum / n
        } else {
            0.0
        };
        let mean_sojourn_time = if n > 0.0 {
            self.completed_sojourn_time_sum / n
        } else {
            0.0
        };
        let std_service_time = safe_std(
            self.completed_service_time_sum,
            self.completed_service_time_sq_sum,
        );
        let std_waiting_time = safe_std(
            self.completed_waiting_time_sum,
            self.completed_waiting_time_sq_sum,
        );
        let std_sojourn_time = safe_std(
            self.completed_sojourn_time_sum,
            self.completed_sojourn_time_sq_sum,
        );

        Ok(SimulationRunResult {
            scenario_name,
            replication_index,
            seed,
            total_time: self.total_time,
            warmup_time: self.warmup_time,
            observed_time,
            state_times: self.state_times,
            pi_hat,
            mean_num_jobs,
            mean_occupied_resource,
            mean_queue_length,
            mean_waiting_jobs,
            arrival_attempts: self.arrival_attempts,
            accepted_arrivals: self.accepted_arrivals,
            accepted_to_queue: self.accepted_to_queue,
            started_from_queue: self.started_from_queue,
            rejected_arrivals: self.rejected_arrivals,
            rejected_capacity: self.rejected_capacity,
            rejected_server: self.rejected_server,
            rejected_resource: self.rejected_resource,
            completed_jobs: self.completed_jobs,
            completed_time_samples: self.completed_time_samples,
            loss_probability,
            queueing_probability,
            throughput,
            mean_service_time,
            mean_waiting_time,
            mean_sojourn_time,
            std_service_time,
            std_waiting_time,
            std_sojourn_time,
            state_trace,
            event_log,
            animation_log,
        })
    }
}

#[derive(Debug)]
pub struct SingleRunSimulator {
    pub scenario: ScenarioConfig,
    pub replication_index: usize,
    pub seed: u64,
    pub rng: StdRng,
    pub state: SystemState,
    pub stats: StatisticsAccumulator,
    pub state_trace: Vec<StateSnapshot>,
    pub event_log: Vec<EventRecord>,
    pub lane_by_job: HashMap<u64, usize>,
    pub animation_jobs: Vec<AnimationJobRecord>,
    pub animation_job_index: HashMap<u64, usize>,
    pub processed_job_count: usize,
}

impl SingleRunSimulator {
    pub fn new(
        scenario: ScenarioConfig,
        replication_index: usize,
        seed: Option<u64>,
    ) -> Result<Self> {
        scenario.validate()?;

        let actual_seed =
            seed.unwrap_or_else(|| derive_run_seed(scenario.simulation.seed, replication_index));

        let mut simulator = Self {
            stats: StatisticsAccumulator::new(
                scenario.capacity_k,
                scenario.simulation.max_time,
                scenario.simulation.warmup_time,
            )?,
            scenario,
            replication_index,
            seed: actual_seed,
            rng: StdRng::seed_from_u64(actual_seed),
            state: SystemState::new(),
            state_trace: Vec::new(),
            event_log: Vec::new(),
            lane_by_job: HashMap::new(),
            animation_jobs: Vec::new(),
            animation_job_index: HashMap::new(),
            processed_job_count: 0,
        };

        simulator.record_state_snapshot();
        Ok(simulator)
    }

    fn record_state_snapshot(&mut self) {
        if !self.scenario.simulation.record_state_trace {
            return;
        }

        self.state_trace.push(StateSnapshot {
            time: self.state.current_time,
            num_jobs: self.state.num_jobs(),
            num_active_jobs: self.state.num_active_jobs(),
            num_waiting_jobs: self.state.num_waiting_jobs(),
            occupied_resource: self.state.occupied_resource(),
            arrival_rate: self.state.current_arrival_rate(&self.scenario),
            service_speed: self.state.current_service_speed(&self.scenario),
        });
    }

    fn record_event(
        &mut self,
        event_type: impl Into<String>,
        job_id: Option<u64>,
        num_jobs_before: usize,
        num_jobs_after: usize,
        occupied_resource_before: u32,
        occupied_resource_after: u32,
        details: impl Into<String>,
    ) {
        if !self.scenario.simulation.save_event_log {
            return;
        }

        self.event_log.push(EventRecord {
            time: self.state.current_time,
            event_type: event_type.into(),
            job_id,
            num_jobs_before,
            num_jobs_after,
            occupied_resource_before,
            occupied_resource_after,
            details: details.into(),
        });
    }

    fn sample_new_job_parameters(&mut self) -> Result<(u32, f64)> {
        let resource_demand =
            sample_resource_demand(&mut self.rng, &self.scenario.resource_distribution)?;
        // Распределение W работы задается workload_distribution.
        // Далее фактическое время обслуживания формируется как T = W / sigma_k.
        let workload = sample_workload(&mut self.rng, &self.scenario.workload_distribution)?;
        Ok((resource_demand, workload))
    }

    fn should_record_animation_job(&self) -> bool {
        let limit = self.scenario.simulation.animation_log_max_jobs;
        limit > 0 && self.processed_job_count < limit
    }

    fn allocate_lane(&mut self, job_id: u64) -> Option<usize> {
        for lane in 0..self.scenario.servers_n {
            if !self.lane_by_job.values().any(|&v| v == lane) {
                self.lane_by_job.insert(job_id, lane);
                return Some(lane);
            }
        }
        None
    }

    fn update_animation_job<F>(&mut self, job_id: u64, mut f: F)
    where
        F: FnMut(&mut AnimationJobRecord),
    {
        if let Some(idx) = self.animation_job_index.get(&job_id).copied() {
            if let Some(job) = self.animation_jobs.get_mut(idx) {
                f(job);
            }
        }
    }

    fn process_arrival(&mut self) -> Result<()> {
        let num_jobs_before = self.state.num_jobs_total();
        let occupied_resource_before = self.state.occupied_resource();

        let (resource_demand, workload) = self.sample_new_job_parameters()?;
        self.stats.register_arrival_attempt(self.state.current_time);
        let job =
            self.state
                .create_job(resource_demand, workload, Some(self.state.current_time))?;
        let job_id = job.job_id;
        let should_record = self.should_record_animation_job();
        self.processed_job_count += 1;

        let decision = self.state.can_admit_job(resource_demand, &self.scenario)?;

        if !decision.accepted {
            self.stats
                .register_rejection(self.state.current_time, decision.reason);

            self.record_event(
                "arrival_rejected",
                None,
                num_jobs_before,
                self.state.num_jobs_total(),
                occupied_resource_before,
                self.state.occupied_resource(),
                format!(
                    "reason={}, resource_demand={}, workload={:.6}",
                    decision.reason.as_str(),
                    resource_demand,
                    workload
                ),
            );

            if should_record {
                let rec = AnimationJobRecord {
                    job_id,
                    arrival_time: self.state.current_time,
                    resource_demand,
                    decision: "rejected".to_string(),
                    queue_enter_time: None,
                    service_start_time: None,
                    service_end_time: None,
                    lane_id: None,
                    reject_reason: Some(decision.reason.as_str().to_string()),
                };
                self.animation_job_index
                    .insert(job_id, self.animation_jobs.len());
                self.animation_jobs.push(rec);
            }
            self.record_state_snapshot();
            return Ok(());
        }

        let placement = self.state.admit_or_enqueue(job, &self.scenario)?;
        let queued = matches!(placement, AdmissionPlacement::Queued);
        self.stats
            .register_admission(self.state.current_time, queued);

        if should_record {
            let lane_id = if queued {
                None
            } else {
                self.allocate_lane(job_id)
            };
            let rec = AnimationJobRecord {
                job_id,
                arrival_time: self.state.current_time,
                resource_demand,
                decision: if queued {
                    "queued".to_string()
                } else {
                    "accepted".to_string()
                },
                queue_enter_time: if queued {
                    Some(self.state.current_time)
                } else {
                    None
                },
                service_start_time: if queued {
                    None
                } else {
                    Some(self.state.current_time)
                },
                service_end_time: None,
                lane_id,
                reject_reason: None,
            };
            self.animation_job_index
                .insert(job_id, self.animation_jobs.len());
            self.animation_jobs.push(rec);
        } else if !queued {
            let _ = self.allocate_lane(job_id);
        }

        let event_type = if queued {
            "arrival_enqueued"
        } else {
            "arrival_accepted"
        };
        self.record_event(
            event_type,
            Some(job_id),
            num_jobs_before,
            self.state.num_jobs_total(),
            occupied_resource_before,
            self.state.occupied_resource(),
            format!(
                "resource_demand={}, workload={:.6}, queued={}",
                resource_demand, workload, queued
            ),
        );

        self.record_state_snapshot();
        Ok(())
    }

    fn process_departures(&mut self) -> Result<()> {
        let completed_ids = self.state.completed_jobs(COMPLETION_TOL);
        if completed_ids.is_empty() {
            return Ok(());
        }

        for job_id in completed_ids {
            let num_jobs_before = self.state.num_jobs_total();
            let occupied_resource_before = self.state.occupied_resource();
            let now = self.state.current_time;

            let removed_job = self.state.remove_job(job_id)?;
            self.lane_by_job.remove(&removed_job.job_id);
            self.stats.register_departure(self.state.current_time);
            let service_start_time = removed_job.service_start_time.ok_or_else(|| {
                SimulationError::Validation(format!(
                    "У завершившейся заявки job_id={} отсутствует service_start_time",
                    removed_job.job_id
                ))
            })?;
            self.stats.register_completed_job_times(
                self.state.current_time,
                removed_job.arrival_time,
                service_start_time,
            );
            self.update_animation_job(removed_job.job_id, |r| {
                r.service_end_time = Some(now);
            });

            self.record_event(
                "departure",
                Some(removed_job.job_id),
                num_jobs_before,
                self.state.num_jobs_total(),
                occupied_resource_before,
                self.state.occupied_resource(),
                format!(
                    "arrival_time={:.6}, total_workload={:.6}",
                    removed_job.arrival_time, removed_job.total_workload
                ),
            );

            let promoted_job_ids = self.state.promote_from_queue(&self.scenario);
            if !promoted_job_ids.is_empty() {
                for promoted_job_id in &promoted_job_ids {
                    self.stats
                        .register_started_from_queue(self.state.current_time);
                    let lane = self.allocate_lane(*promoted_job_id);
                    let now = self.state.current_time;
                    self.update_animation_job(*promoted_job_id, |r| {
                        r.service_start_time = Some(now);
                        r.lane_id = lane;
                    });
                }
                self.record_event(
                    "queue_promotion",
                    None,
                    self.state.num_jobs_total(),
                    self.state.num_jobs_total(),
                    self.state.occupied_resource(),
                    self.state.occupied_resource(),
                    format!("promoted_jobs={}", promoted_job_ids.len()),
                );
            }
        }

        self.record_state_snapshot();
        Ok(())
    }

    pub fn run(mut self) -> Result<SimulationRunResult> {
        let max_time = self.scenario.simulation.max_time;
        let eps = self.scenario.simulation.time_epsilon;

        while self.state.current_time < max_time - eps {
            let t0 = self.state.current_time;

            let arrival_dt = sample_next_arrival_delta(&mut self.rng, &self.state, &self.scenario)?;
            let (next_departure_job_id, departure_dt) =
                self.state.next_completion(&self.scenario)?;
            let next_event_dt = arrival_dt.min(departure_dt);

            if next_event_dt == INFINITY {
                let t1 = max_time;
                self.stats.observe_constant_interval(
                    t0,
                    t1,
                    self.state.num_jobs_total(),
                    self.state.num_waiting_jobs(),
                    self.state.occupied_resource(),
                )?;
                self.state
                    .advance_time_and_service(t1 - t0, &self.scenario)?;
                self.record_state_snapshot();
                break;
            }

            if next_event_dt <= eps {
                if departure_dt <= arrival_dt && next_departure_job_id.is_some() {
                    self.process_departures()?;
                    continue;
                }
                if arrival_dt < INFINITY {
                    self.process_arrival()?;
                    continue;
                }
                break;
            }

            if t0 + next_event_dt > max_time {
                let t1 = max_time;
                self.stats.observe_constant_interval(
                    t0,
                    t1,
                    self.state.num_jobs_total(),
                    self.state.num_waiting_jobs(),
                    self.state.occupied_resource(),
                )?;
                self.state
                    .advance_time_and_service(t1 - t0, &self.scenario)?;
                self.record_state_snapshot();
                break;
            }

            let t1 = t0 + next_event_dt;
            self.stats.observe_constant_interval(
                t0,
                t1,
                self.state.num_jobs_total(),
                self.state.num_waiting_jobs(),
                self.state.occupied_resource(),
            )?;

            self.state
                .advance_time_and_service(next_event_dt, &self.scenario)?;

            if departure_dt < arrival_dt - eps {
                self.process_departures()?;
            } else if arrival_dt < departure_dt - eps {
                self.process_arrival()?;
            } else {
                if next_departure_job_id.is_some() {
                    self.process_departures()?;
                }
                self.process_arrival()?;
            }
        }

        let animation_log = if self.scenario.simulation.animation_log_max_jobs > 0 {
            Some(AnimationLog {
                meta: AnimationLogMeta {
                    system_architecture: match self.scenario.system_architecture {
                        SystemArchitecture::Loss => "loss".to_string(),
                        SystemArchitecture::Buffer => "buffer".to_string(),
                    },
                    servers_n: self.scenario.servers_n,
                    capacity_k: self.scenario.capacity_k,
                    queue_capacity: self.scenario.queue_capacity(),
                    total_resource_r: self.scenario.total_resource_r,
                },
                jobs: self.animation_jobs,
            })
        } else {
            None
        };

        self.stats.build_result(
            self.scenario.name.clone(),
            self.replication_index,
            self.seed,
            self.state_trace,
            self.event_log,
            animation_log,
        )
    }
}

pub fn simulate_one_run(
    scenario: ScenarioConfig,
    replication_index: usize,
    seed: Option<u64>,
) -> Result<SimulationRunResult> {
    SingleRunSimulator::new(scenario, replication_index, seed)?.run()
}

pub fn print_run_summary(result: &SimulationRunResult) {
    println!("{}", "=".repeat(90));
    println!("РЕЗУЛЬТАТ ОДНОГО ПРОГОНА");
    println!("{}", "=".repeat(90));
    println!(
        "Сценарий:                          {}",
        result.scenario_name
    );
    println!(
        "Replication index:                 {}",
        result.replication_index
    );
    println!("Seed:                              {}", result.seed);
    println!("Полное время моделирования:        {}", result.total_time);
    println!("Warm-up:                           {}", result.warmup_time);
    println!(
        "Наблюдаемое время:                 {}",
        result.observed_time
    );
    println!("{}", "-".repeat(90));
    println!(
        "Среднее число заявок:              {:.6}",
        result.mean_num_jobs
    );
    println!(
        "Средний занятый ресурс:            {:.6}",
        result.mean_occupied_resource
    );
    println!(
        "Средняя длина очереди:             {:.6}",
        result.mean_queue_length
    );
    println!(
        "Среднее число ожидающих:           {:.6}",
        result.mean_waiting_jobs
    );
    println!(
        "Число попыток поступления:         {}",
        result.arrival_attempts
    );
    println!(
        "Число принятых заявок:             {}",
        result.accepted_arrivals
    );
    println!(
        "Из них поставлено в очередь:       {}",
        result.accepted_to_queue
    );
    println!(
        "Стартов обслуживания из очереди:   {}",
        result.started_from_queue
    );
    println!(
        "Число отказов:                     {}",
        result.rejected_arrivals
    );
    println!(
        "  из-за ёмкости K:                 {}",
        result.rejected_capacity
    );
    println!(
        "  из-за лимита приборов N:         {}",
        result.rejected_server
    );
    println!(
        "  из-за лимита ресурса R:          {}",
        result.rejected_resource
    );
    println!(
        "Число завершённых заявок:          {}",
        result.completed_jobs
    );
    println!(
        "Сэмплов job-time в окне:            {}",
        result.completed_time_samples
    );
    println!(
        "Вероятность отказа:                {:.6}",
        result.loss_probability
    );
    println!(
        "Вероятность попадания в очередь:   {:.6}",
        result.queueing_probability
    );
    println!(
        "Эффективная пропускная способность:{:.6}",
        result.throughput
    );
    println!(
        "Среднее время обслуживания:         {:.6}",
        result.mean_service_time
    );
    println!(
        "Среднее время ожидания:             {:.6}",
        result.mean_waiting_time
    );
    println!(
        "Среднее время пребывания:           {:.6}",
        result.mean_sojourn_time
    );
    println!(
        "Std времени обслуживания:           {:.6}",
        result.std_service_time
    );
    println!(
        "Std времени ожидания:               {:.6}",
        result.std_waiting_time
    );
    println!(
        "Std времени пребывания:             {:.6}",
        result.std_sojourn_time
    );
    println!("{}", "-".repeat(90));
    println!("Оценка стационарного распределения pi_hat(k):");
    for (k, value) in result.pi_hat.iter().enumerate() {
        println!("  k={:>2}: {:.6}", k, value);
    }
    println!("{}", "=".repeat(90));
    println!();
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::params::{
        build_base_scenario_from_values, load_default_external_experiment_values,
        standard_workload_family_from_values,
    };

    #[test]
    fn derive_seed_matches_python_formula() {
        assert_eq!(derive_run_seed(42, 0), 42);
        assert_eq!(derive_run_seed(42, 1), 42 + 1_000_003);
        assert_eq!(derive_run_seed(42, 2), 42 + 2 * 1_000_003);
    }

    #[test]
    fn overlap_length_works() {
        assert!((interval_overlap_length(0.0, 10.0, 2.0, 4.0) - 2.0).abs() < 1e-12);
        assert_eq!(interval_overlap_length(0.0, 1.0, 2.0, 3.0), 0.0);
    }

    #[test]
    fn smoke_run_exponential_base_scenario() {
        let mut values = load_default_external_experiment_values().unwrap();
        values.mean_workload = 1.0;
        let workloads = standard_workload_family_from_values(&values).unwrap();
        let mut scenario = build_base_scenario_from_values(
            &values,
            workloads.get("exponential").unwrap().clone(),
            "_smoke",
        )
        .unwrap();

        scenario.simulation.max_time = 50.0;
        scenario.simulation.warmup_time = 5.0;
        scenario.simulation.record_state_trace = true;
        scenario.simulation.save_event_log = true;

        let result = simulate_one_run(scenario, 0, Some(12345)).unwrap();

        assert!(result.observed_time > 0.0);
        assert_eq!(result.pi_hat.len(), 21);
        assert!(result.loss_probability >= 0.0);
        assert!(result.loss_probability <= 1.0);
    }
}
