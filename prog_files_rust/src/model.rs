use std::collections::VecDeque;
use std::fmt;

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::params::{ParamsError, ScenarioConfig, SystemArchitecture};

pub const COMPLETION_TOL: f64 = 1e-12;

#[derive(Debug, Error)]
pub enum ModelError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),
}

type Result<T> = std::result::Result<T, ModelError>;

fn ensure_nonnegative_f64(name: &str, value: f64) -> Result<()> {
    if value < 0.0 {
        return Err(ModelError::Validation(format!(
            "Параметр '{name}' должен быть >= 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_f64(name: &str, value: f64) -> Result<()> {
    if value <= 0.0 {
        return Err(ModelError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_u32(name: &str, value: u32) -> Result<()> {
    if value == 0 {
        return Err(ModelError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RejectionReason {
    CapacityLimit,
    ServerLimit,
    ResourceLimit,
    None,
}

impl RejectionReason {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::CapacityLimit => "capacity_limit",
            Self::ServerLimit => "server_limit",
            Self::ResourceLimit => "resource_limit",
            Self::None => "none",
        }
    }
}

impl fmt::Display for RejectionReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct AdmissionDecision {
    pub accepted: bool,
    pub reason: RejectionReason,
}

impl AdmissionDecision {
    pub fn accepted() -> Self {
        Self {
            accepted: true,
            reason: RejectionReason::None,
        }
    }

    pub fn rejected(reason: RejectionReason) -> Self {
        Self {
            accepted: false,
            reason,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionPlacement {
    Active,
    Queued,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Job {
    pub job_id: u64,
    pub arrival_time: f64,
    pub queue_enter_time: Option<f64>,
    pub service_start_time: Option<f64>,
    pub resource_demand: u32,
    pub total_workload: f64,
    pub remaining_workload: f64,
}

impl Job {
    pub fn new(
        job_id: u64,
        arrival_time: f64,
        resource_demand: u32,
        total_workload: f64,
    ) -> Result<Self> {
        ensure_nonnegative_f64("arrival_time", arrival_time)?;
        ensure_positive_u32("resource_demand", resource_demand)?;
        ensure_positive_f64("total_workload", total_workload)?;

        Ok(Self {
            job_id,
            arrival_time,
            queue_enter_time: None,
            service_start_time: None,
            resource_demand,
            total_workload,
            remaining_workload: total_workload,
        })
    }

    pub fn with_remaining_workload(
        job_id: u64,
        arrival_time: f64,
        resource_demand: u32,
        total_workload: f64,
        remaining_workload: f64,
    ) -> Result<Self> {
        ensure_nonnegative_f64("arrival_time", arrival_time)?;
        ensure_positive_u32("resource_demand", resource_demand)?;
        ensure_positive_f64("total_workload", total_workload)?;
        ensure_nonnegative_f64("remaining_workload", remaining_workload)?;

        Ok(Self {
            job_id,
            arrival_time,
            queue_enter_time: None,
            service_start_time: None,
            resource_demand,
            total_workload,
            remaining_workload,
        })
    }

    pub fn progress(&mut self, dt: f64, service_speed: f64) -> Result<()> {
        ensure_nonnegative_f64("dt", dt)?;
        ensure_nonnegative_f64("service_speed", service_speed)?;

        self.progress_unchecked(dt, service_speed);
        Ok(())
    }

    pub fn progress_unchecked(&mut self, dt: f64, service_speed: f64) {
        debug_assert!(dt >= 0.0);
        debug_assert!(service_speed >= 0.0);
        if dt == 0.0 || service_speed == 0.0 {
            return;
        }

        self.remaining_workload = (self.remaining_workload - service_speed * dt).max(0.0);
    }

    pub fn is_completed(&self, tol: f64) -> bool {
        self.remaining_workload <= tol
    }

    pub fn time_to_completion(&self, service_speed: f64) -> Result<f64> {
        ensure_nonnegative_f64("service_speed", service_speed)?;
        Ok(self.time_to_completion_unchecked(service_speed))
    }

    pub fn time_to_completion_unchecked(&self, service_speed: f64) -> f64 {
        debug_assert!(service_speed >= 0.0);
        if self.is_completed(COMPLETION_TOL) {
            return 0.0;
        }
        if service_speed == 0.0 {
            return f64::INFINITY;
        }

        self.remaining_workload / service_speed
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemState {
    pub current_time: f64,
    pub active_jobs: Vec<Job>,
    pub waiting_queue: VecDeque<Job>,
    pub occupied_resource_total: u32,
    pub next_job_id: u64,
}

impl Default for SystemState {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemState {
    pub fn new() -> Self {
        Self {
            current_time: 0.0,
            active_jobs: Vec::new(),
            waiting_queue: VecDeque::new(),
            occupied_resource_total: 0,
            next_job_id: 1,
        }
    }

    pub fn num_active_jobs(&self) -> usize {
        self.active_jobs.len()
    }

    pub fn num_waiting_jobs(&self) -> usize {
        self.waiting_queue.len()
    }

    pub fn num_jobs_total(&self) -> usize {
        self.num_active_jobs() + self.num_waiting_jobs()
    }

    pub fn num_jobs(&self) -> usize {
        self.num_jobs_total()
    }

    pub fn occupied_resource(&self) -> u32 {
        self.occupied_resource_total
    }

    pub fn queue_capacity(&self, scenario: &ScenarioConfig) -> usize {
        scenario.queue_capacity()
    }

    pub fn has_free_server(&self, scenario: &ScenarioConfig) -> bool {
        self.num_active_jobs() < scenario.servers_n
    }

    pub fn current_arrival_rate(&self, scenario: &ScenarioConfig) -> f64 {
        scenario.arrival_rate_by_state[self.num_jobs_total()]
    }

    pub fn current_service_speed(&self, scenario: &ScenarioConfig) -> f64 {
        scenario.service_speed_by_state[self.num_jobs_total()]
    }

    pub fn can_admit_job(
        &self,
        resource_demand: u32,
        scenario: &ScenarioConfig,
    ) -> Result<AdmissionDecision> {
        ensure_positive_u32("resource_demand", resource_demand)?;
        Ok(self.can_admit_job_fast(resource_demand, scenario))
    }

    pub fn can_admit_job_fast(
        &self,
        resource_demand: u32,
        scenario: &ScenarioConfig,
    ) -> AdmissionDecision {
        debug_assert!(resource_demand > 0);
        if self.num_jobs_total() >= scenario.capacity_k {
            return AdmissionDecision::rejected(RejectionReason::CapacityLimit);
        }
        if self.occupied_resource() + resource_demand > scenario.total_resource_r {
            return AdmissionDecision::rejected(RejectionReason::ResourceLimit);
        }

        if scenario.system_architecture == SystemArchitecture::Loss
            && self.num_active_jobs() >= scenario.servers_n
        {
            return AdmissionDecision::rejected(RejectionReason::ServerLimit);
        }

        AdmissionDecision::accepted()
    }

    pub fn can_accept(
        &self,
        resource_demand: u32,
        scenario: &ScenarioConfig,
    ) -> Result<AdmissionDecision> {
        Ok(self.can_admit_job_fast(resource_demand, scenario))
    }

    pub fn create_job(
        &mut self,
        resource_demand: u32,
        workload: f64,
        arrival_time: Option<f64>,
    ) -> Result<Job> {
        ensure_positive_u32("resource_demand", resource_demand)?;
        ensure_positive_f64("workload", workload)?;

        let job = Job::new(
            self.next_job_id,
            arrival_time.unwrap_or(self.current_time),
            resource_demand,
            workload,
        )?;
        self.next_job_id += 1;
        Ok(job)
    }

    pub fn admit_or_enqueue(
        &mut self,
        mut job: Job,
        scenario: &ScenarioConfig,
    ) -> Result<AdmissionPlacement> {
        let decision = self.can_admit_job(job.resource_demand, scenario)?;
        if !decision.accepted {
            return Err(ModelError::Validation(format!(
                "Невозможно добавить job_id={}: отказ по причине {}",
                job.job_id, decision.reason
            )));
        }

        if self
            .active_jobs
            .iter()
            .any(|active| active.job_id == job.job_id)
            || self
                .waiting_queue
                .iter()
                .any(|queued| queued.job_id == job.job_id)
        {
            return Err(ModelError::Validation(format!(
                "Заявка job_id={} уже есть в системе",
                job.job_id
            )));
        }

        self.occupied_resource_total += job.resource_demand;

        if self.has_free_server(scenario) {
            job.service_start_time = Some(self.current_time);
            self.active_jobs.push(job);
            Ok(AdmissionPlacement::Active)
        } else {
            job.queue_enter_time = Some(self.current_time);
            self.waiting_queue.push_back(job);
            Ok(AdmissionPlacement::Queued)
        }
    }

    pub fn add_job(&mut self, job: Job, scenario: &ScenarioConfig) -> Result<()> {
        let _ = self.admit_or_enqueue(job, scenario)?;
        Ok(())
    }

    pub fn promote_from_queue(&mut self, scenario: &ScenarioConfig) -> Vec<u64> {
        let mut promoted: Vec<u64> = Vec::new();
        while self.has_free_server(scenario) {
            let Some(mut job) = self.waiting_queue.pop_front() else {
                break;
            };
            job.service_start_time = Some(self.current_time);
            promoted.push(job.job_id);
            self.active_jobs.push(job);
        }
        promoted
    }

    pub fn remove_job(&mut self, job_id: u64) -> Result<Job> {
        let index = self
            .active_jobs
            .iter()
            .position(|job| job.job_id == job_id)
            .ok_or_else(|| {
                ModelError::Validation(format!(
                    "Заявка job_id={} не найдена среди активных",
                    job_id
                ))
            })?;

        let removed = self.active_jobs.remove(index);
        self.occupied_resource_total = self
            .occupied_resource_total
            .checked_sub(removed.resource_demand)
            .ok_or_else(|| {
                ModelError::Validation(format!(
                    "Неконсистентное состояние ресурса при удалении job_id={}",
                    job_id
                ))
            })?;

        Ok(removed)
    }

    pub fn advance_time_and_service(&mut self, dt: f64, scenario: &ScenarioConfig) -> Result<()> {
        ensure_nonnegative_f64("dt", dt)?;
        self.advance_time_and_service_fast(dt, scenario);
        Ok(())
    }

    pub fn advance_time_and_service_fast(&mut self, dt: f64, scenario: &ScenarioConfig) {
        debug_assert!(dt >= 0.0);
        if dt == 0.0 {
            return;
        }

        let current_k = self.num_jobs_total();
        let service_speed = scenario.service_speed_by_state[current_k];

        for job in &mut self.active_jobs {
            job.progress_unchecked(dt, service_speed);
        }

        self.current_time += dt;
    }

    pub fn completion_offsets(&self, scenario: &ScenarioConfig) -> Result<Vec<(u64, f64)>> {
        if self.active_jobs.is_empty() {
            return Ok(Vec::new());
        }

        let service_speed = self.current_service_speed(scenario);
        let mut offsets = Vec::with_capacity(self.active_jobs.len());

        for job in &self.active_jobs {
            offsets.push((job.job_id, job.time_to_completion(service_speed)?));
        }

        Ok(offsets)
    }

    pub fn next_completion(&self, scenario: &ScenarioConfig) -> Result<(Option<u64>, f64)> {
        Ok(self.next_completion_fast(scenario))
    }

    pub fn next_completion_fast(&self, scenario: &ScenarioConfig) -> (Option<u64>, f64) {
        let mut best_job_id: Option<u64> = None;
        let mut best_dt = f64::INFINITY;
        let service_speed = self.current_service_speed(scenario);

        for job in &self.active_jobs {
            let job_id = job.job_id;
            let dt = job.time_to_completion_unchecked(service_speed);
            if dt < best_dt {
                best_dt = dt;
                best_job_id = Some(job_id);
            } else if (dt - best_dt).abs() <= COMPLETION_TOL {
                if let Some(current_best) = best_job_id {
                    if job_id < current_best {
                        best_job_id = Some(job_id);
                    }
                }
            }
        }

        (best_job_id, best_dt)
    }

    pub fn completed_jobs(&self, tol: f64) -> Vec<u64> {
        self.active_jobs
            .iter()
            .filter_map(|job| job.is_completed(tol).then_some(job.job_id))
            .collect()
    }

    pub fn short_summary(&self) -> String {
        format!(
            "SystemState(t={:.6}, active={}, waiting={}, k_total={}, occupied_resource={}, next_job_id={})",
            self.current_time,
            self.num_active_jobs(),
            self.num_waiting_jobs(),
            self.num_jobs_total(),
            self.occupied_resource(),
            self.next_job_id
        )
    }

    pub fn pretty_string(&self) -> String {
        let mut out = String::new();
        out.push_str(&format!("{}\n", "=".repeat(80)));
        out.push_str(&format!("{}\n", self.short_summary()));
        out.push_str(&format!("{}\n", "-".repeat(80)));

        if self.active_jobs.is_empty() {
            out.push_str("Активных заявок нет.\n");
        } else {
            out.push_str("Активные заявки:\n");
            for job in &self.active_jobs {
                out.push_str(&format!(
                    "  job_id={:>3} | arrival={:>8.4} | resource={:>2} | total_work={:>8.4} | remaining={:>8.4}\n",
                    job.job_id,
                    job.arrival_time,
                    job.resource_demand,
                    job.total_workload,
                    job.remaining_workload
                ));
            }
        }

        if self.waiting_queue.is_empty() {
            out.push_str("Очередь ожидания пуста.\n");
        } else {
            out.push_str("Очередь ожидания:\n");
            for job in &self.waiting_queue {
                out.push_str(&format!(
                    "  job_id={:>3} | arrival={:>8.4} | resource={:>2} | total_work={:>8.4} | remaining={:>8.4}\n",
                    job.job_id,
                    job.arrival_time,
                    job.resource_demand,
                    job.total_workload,
                    job.remaining_workload
                ));
            }
        }

        out.push_str(&format!("{}\n\n", "=".repeat(80)));
        out
    }

    pub fn pretty_print(&self) {
        print!("{}", self.pretty_string());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::params::{
        build_base_scenario_from_values, load_default_external_experiment_values,
        standard_workload_family_from_values, ArrivalProcessConfig,
    };

    #[test]
    fn job_progress_and_completion_work() {
        let mut job = Job::new(1, 0.0, 2, 1.5).unwrap();
        job.progress(0.5, 2.0).unwrap();
        assert!((job.remaining_workload - 0.5).abs() < 1e-12);
        assert!(!job.is_completed(1e-12));

        job.progress(0.25, 2.0).unwrap();
        assert!(job.is_completed(1e-12));
    }

    #[test]
    fn can_reject_for_resource_limit() {
        let mut values = load_default_external_experiment_values().unwrap();
        values.mean_workload = 1.0;
        values.system_architecture = SystemArchitecture::Loss;
        values.capacity_k = values.servers_n;
        let workloads = standard_workload_family_from_values(&values).unwrap();
        let scenario = build_base_scenario_from_values(
            &values,
            workloads.get("exponential").unwrap().clone(),
            ArrivalProcessConfig::Poisson,
            "_test_resource",
        )
        .unwrap();

        let state = SystemState::new();
        let decision = state
            .can_accept(scenario.total_resource_r + 1, &scenario)
            .unwrap();

        assert!(!decision.accepted);
        assert_eq!(decision.reason, RejectionReason::ResourceLimit);
    }
}
