use std::collections::BTreeMap;
use std::fmt;

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::params::{
    build_base_scenario_from_values, load_default_external_experiment_values, ParamsError,
    ScenarioConfig, standard_workload_family_from_values,
};

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Job {
    pub job_id: u64,
    pub arrival_time: f64,
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
            resource_demand,
            total_workload,
            remaining_workload,
        })
    }

    pub fn progress(&mut self, dt: f64, service_speed: f64) -> Result<()> {
        ensure_nonnegative_f64("dt", dt)?;
        ensure_nonnegative_f64("service_speed", service_speed)?;

        if dt == 0.0 || service_speed == 0.0 {
            return Ok(());
        }

        self.remaining_workload = (self.remaining_workload - service_speed * dt).max(0.0);
        Ok(())
    }

    pub fn is_completed(&self, tol: f64) -> bool {
        self.remaining_workload <= tol
    }

    pub fn time_to_completion(&self, service_speed: f64) -> Result<f64> {
        ensure_nonnegative_f64("service_speed", service_speed)?;

        if self.is_completed(COMPLETION_TOL) {
            return Ok(0.0);
        }
        if service_speed == 0.0 {
            return Ok(f64::INFINITY);
        }

        Ok(self.remaining_workload / service_speed)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemState {
    pub current_time: f64,
    pub active_jobs: BTreeMap<u64, Job>,
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
            active_jobs: BTreeMap::new(),
            occupied_resource_total: 0,
            next_job_id: 1,
        }
    }

    pub fn num_jobs(&self) -> usize {
        self.active_jobs.len()
    }

    pub fn occupied_resource(&self) -> u32 {
        self.occupied_resource_total
    }

    pub fn free_resource(&self, scenario: &ScenarioConfig) -> u32 {
        scenario
            .total_resource_r
            .saturating_sub(self.occupied_resource_total)
    }

    pub fn free_servers(&self, scenario: &ScenarioConfig) -> usize {
        scenario.servers_n.saturating_sub(self.num_jobs())
    }

    pub fn current_arrival_rate(&self, scenario: &ScenarioConfig) -> f64 {
        scenario.arrival_rate_by_state[self.num_jobs()]
    }

    pub fn current_service_speed(&self, scenario: &ScenarioConfig) -> f64 {
        scenario.service_speed_by_state[self.num_jobs()]
    }

    pub fn can_accept(
        &self,
        resource_demand: u32,
        scenario: &ScenarioConfig,
    ) -> Result<AdmissionDecision> {
        ensure_positive_u32("resource_demand", resource_demand)?;

        if self.num_jobs() >= scenario.capacity_k {
            return Ok(AdmissionDecision::rejected(RejectionReason::CapacityLimit));
        }
        if self.num_jobs() >= scenario.servers_n {
            return Ok(AdmissionDecision::rejected(RejectionReason::ServerLimit));
        }
        if self.occupied_resource() + resource_demand > scenario.total_resource_r {
            return Ok(AdmissionDecision::rejected(RejectionReason::ResourceLimit));
        }

        Ok(AdmissionDecision::accepted())
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

    pub fn add_job(&mut self, job: Job, scenario: &ScenarioConfig) -> Result<()> {
        let decision = self.can_accept(job.resource_demand, scenario)?;
        if !decision.accepted {
            return Err(ModelError::Validation(format!(
                "Невозможно добавить job_id={}: отказ по причине {}",
                job.job_id, decision.reason
            )));
        }

        if self.active_jobs.contains_key(&job.job_id) {
            return Err(ModelError::Validation(format!(
                "Заявка job_id={} уже есть в системе",
                job.job_id
            )));
        }

        self.occupied_resource_total += job.resource_demand;
        self.active_jobs.insert(job.job_id, job);
        Ok(())
    }

    pub fn remove_job(&mut self, job_id: u64) -> Result<Job> {
        let removed = self.active_jobs.remove(&job_id).ok_or_else(|| {
            ModelError::Validation(format!(
                "Заявка job_id={} не найдена среди активных",
                job_id
            ))
        })?;

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
        if dt == 0.0 {
            return Ok(());
        }

        let current_k = self.num_jobs();
        let service_speed = scenario.service_speed_by_state[current_k];

        for job in self.active_jobs.values_mut() {
            job.progress(dt, service_speed)?;
        }

        self.current_time += dt;
        Ok(())
    }

    pub fn completion_offsets(&self, scenario: &ScenarioConfig) -> Result<BTreeMap<u64, f64>> {
        if self.active_jobs.is_empty() {
            return Ok(BTreeMap::new());
        }

        let service_speed = self.current_service_speed(scenario);
        let mut offsets = BTreeMap::new();

        for (job_id, job) in &self.active_jobs {
            offsets.insert(*job_id, job.time_to_completion(service_speed)?);
        }

        Ok(offsets)
    }

    pub fn next_completion(&self, scenario: &ScenarioConfig) -> Result<(Option<u64>, f64)> {
        let offsets = self.completion_offsets(scenario)?;
        if offsets.is_empty() {
            return Ok((None, f64::INFINITY));
        }

        let mut best_job_id: Option<u64> = None;
        let mut best_dt = f64::INFINITY;

        for (job_id, dt) in offsets {
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

        Ok((best_job_id, best_dt))
    }

    pub fn completed_jobs(&self, tol: f64) -> Vec<u64> {
        self.active_jobs
            .iter()
            .filter_map(|(job_id, job)| job.is_completed(tol).then_some(*job_id))
            .collect()
    }

    pub fn short_summary(&self) -> String {
        format!(
            "SystemState(t={:.6}, k={}, occupied_resource={}, next_job_id={})",
            self.current_time,
            self.num_jobs(),
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
            for job in self.active_jobs.values() {
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

pub fn self_test() -> Result<()> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = 1.0;
    let workloads = standard_workload_family_from_values(&values)?;
    let workload = workloads
        .get("exponential")
        .cloned()
        .ok_or_else(|| ModelError::Validation("Не найден workload 'exponential'".to_string()))?;

    let scenario = build_base_scenario_from_values(&values, workload, "_model_self_test")?;

    println!("\nSELF-TEST model.rs\n");
    println!("Используемый сценарий:");
    println!("{}", scenario.short_description());
    println!();

    let mut state = SystemState::new();

    println!("Шаг 1. Пустое состояние.");
    state.pretty_print();

    println!("Шаг 2. Добавляем первую заявку.");
    let job_1 = state.create_job(2, 1.5, None)?;
    let decision_1 = state.can_accept(job_1.resource_demand, &scenario)?;
    println!(
        "Решение о допуске job_1: accepted={}, reason={}",
        decision_1.accepted, decision_1.reason
    );
    state.add_job(job_1, &scenario)?;
    state.pretty_print();

    println!("Шаг 3. Добавляем вторую заявку.");
    let job_2 = state.create_job(3, 0.8, None)?;
    let decision_2 = state.can_accept(job_2.resource_demand, &scenario)?;
    println!(
        "Решение о допуске job_2: accepted={}, reason={}",
        decision_2.accepted, decision_2.reason
    );
    state.add_job(job_2, &scenario)?;
    state.pretty_print();

    println!("Шаг 4. Вычисляем ближайшее завершение.");
    let (next_job_id, next_dt) = state.next_completion(&scenario)?;
    println!(
        "Ближайшее завершение: job_id={:?}, через dt={:.6}\n",
        next_job_id, next_dt
    );

    println!("Шаг 5. Продвигаем время до ближайшего завершения.");
    state.advance_time_and_service(next_dt, &scenario)?;
    state.pretty_print();

    let completed = state.completed_jobs(COMPLETION_TOL);
    println!(
        "Завершившиеся заявки после продвижения времени: {:?}\n",
        completed
    );

    println!("Шаг 6. Удаляем завершившиеся заявки.");
    for job_id in completed {
        let removed = state.remove_job(job_id)?;
        println!(
            "Удалена заявка job_id={}, время поступления={:.4}, остаток={:.6}",
            removed.job_id, removed.arrival_time, removed.remaining_workload
        );
    }
    state.pretty_print();

    println!("Шаг 7. Проверяем логику отказа по ресурсу.");
    let oversized_resource = scenario.total_resource_r + 1;
    let decision_3 = state.can_accept(oversized_resource, &scenario)?;
    println!(
        "Решение о допуске слишком большой заявки: accepted={}, reason={}",
        decision_3.accepted, decision_3.reason
    );
    println!();

    println!("SELF-TEST model.rs завершён успешно.");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn next_completion_uses_smallest_job_id_on_tie() {
        let mut values = load_default_external_experiment_values().unwrap();
        values.mean_workload = 1.0;
        let workloads = standard_workload_family_from_values(&values).unwrap();
        let scenario = build_base_scenario_from_values(
            &values,
            workloads.get("exponential").unwrap().clone(),
            "_test_tie",
        )
        .unwrap();

        let mut state = SystemState::new();
        let job1 = Job::with_remaining_workload(1, 0.0, 1, 1.0, 1.0).unwrap();
        let job2 = Job::with_remaining_workload(2, 0.0, 1, 1.0, 1.0).unwrap();

        state.add_job(job1, &scenario).unwrap();
        state.add_job(job2, &scenario).unwrap();

        let (job_id, dt) = state.next_completion(&scenario).unwrap();
        assert_eq!(job_id, Some(1));
        assert!(dt.is_finite());
    }

    #[test]
    fn can_reject_for_resource_limit() {
        let mut values = load_default_external_experiment_values().unwrap();
        values.mean_workload = 1.0;
        let workloads = standard_workload_family_from_values(&values).unwrap();
        let scenario = build_base_scenario_from_values(
            &values,
            workloads.get("exponential").unwrap().clone(),
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
