use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use rand_distr::{Distribution, Exp};
use serde::{Deserialize, Serialize};

use crate::model::{RejectionReason, SystemState};
use crate::params::ScenarioConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationRunResult {
    pub scenario_name: String,
    pub replication_index: usize,
    pub seed: u64,
    pub total_time: f64,
    pub warmup_time: f64,
    pub mean_num_jobs: f64,
    pub mean_occupied_resource: f64,
    pub accepted_arrivals: u64,
    pub rejected_arrivals: u64,
    pub rejected_capacity: u64,
    pub rejected_server: u64,
    pub rejected_resource: u64,
    pub completed_jobs: u64,
    pub throughput: f64,
    pub loss_probability: f64,
    pub pi_hat: Vec<f64>,
}

pub fn derive_seed(base_seed: u64, replication_index: usize) -> u64 {
    base_seed ^ (replication_index as u64 + 1).wrapping_mul(0x9E37_79B9_7F4A_7C15)
}

pub fn simulate_one_run(scenario: &ScenarioConfig, replication_index: usize, seed_override: Option<u64>) -> SimulationRunResult {
    let seed = seed_override.unwrap_or_else(|| derive_seed(scenario.simulation.seed, replication_index));
    let mut rng = StdRng::seed_from_u64(seed);
    let mut state = SystemState::new();

    let mut state_times = vec![0.0_f64; scenario.capacity_k + 1];
    let mut accepted_arrivals = 0_u64;
    let mut rejected_arrivals = 0_u64;
    let mut rejected_capacity = 0_u64;
    let mut rejected_server = 0_u64;
    let mut rejected_resource = 0_u64;
    let mut completed_jobs = 0_u64;

    let mut area_num_jobs = 0.0_f64;
    let mut area_resource = 0.0_f64;

    while state.current_time < scenario.simulation.max_time {
        let k = state.num_jobs().min(scenario.capacity_k);
        let arrival_rate = scenario.arrival_rate_by_state[k].max(0.0);
        let service_speed = scenario.service_speed_by_state[k].max(0.0);

        let arrival_dt = if arrival_rate > 0.0 {
            Exp::new(arrival_rate).unwrap().sample(&mut rng)
        } else {
            f64::INFINITY
        };

        let completion_dt = if state.active_jobs.is_empty() || service_speed <= 0.0 {
            f64::INFINITY
        } else {
            state
                .active_jobs
                .iter()
                .map(|j| j.remaining_workload / service_speed)
                .fold(f64::INFINITY, f64::min)
        };

        let dt = arrival_dt.min(completion_dt);
        if !dt.is_finite() || dt <= 0.0 {
            break;
        }

        let t0 = state.current_time;
        let t1 = (t0 + dt).min(scenario.simulation.max_time);
        let dt_effective = t1 - t0;

        if t1 > scenario.simulation.warmup_time {
            let left = t0.max(scenario.simulation.warmup_time);
            let observed_dt = (t1 - left).max(0.0);
            if observed_dt > 0.0 {
                area_num_jobs += state.num_jobs() as f64 * observed_dt;
                area_resource += state.occupied_resource_total as f64 * observed_dt;
                state_times[k] += observed_dt;
            }
        }

        let finished = state.advance_and_complete(dt_effective, service_speed);
        completed_jobs += finished as u64;

        if (arrival_dt - dt).abs() <= 1e-12 {
            let resource = rng.gen_range(1..=3) as u32;
            let workload = Exp::new(1.0 / scenario.mean_workload.max(1e-9)).unwrap().sample(&mut rng);
            match state.can_accept(resource, scenario) {
                Ok(()) => {
                    state.add_job(resource, workload.max(1e-9));
                    accepted_arrivals += 1;
                }
                Err(reason) => {
                    rejected_arrivals += 1;
                    match reason {
                        RejectionReason::Capacity => rejected_capacity += 1,
                        RejectionReason::Servers => rejected_server += 1,
                        RejectionReason::Resource => rejected_resource += 1,
                    }
                }
            }
        }
    }

    let observed_time = (scenario.simulation.max_time - scenario.simulation.warmup_time).max(1e-9);
    let total_arrivals = accepted_arrivals + rejected_arrivals;
    let throughput = completed_jobs as f64 / observed_time;
    let loss_probability = if total_arrivals == 0 {
        0.0
    } else {
        rejected_arrivals as f64 / total_arrivals as f64
    };

    let pi_hat = state_times.iter().map(|v| v / observed_time).collect::<Vec<_>>();

    SimulationRunResult {
        scenario_name: scenario.name.clone(),
        replication_index,
        seed,
        total_time: scenario.simulation.max_time,
        warmup_time: scenario.simulation.warmup_time,
        mean_num_jobs: area_num_jobs / observed_time,
        mean_occupied_resource: area_resource / observed_time,
        accepted_arrivals,
        rejected_arrivals,
        rejected_capacity,
        rejected_server,
        rejected_resource,
        completed_jobs,
        throughput,
        loss_probability,
        pi_hat,
    }
}
