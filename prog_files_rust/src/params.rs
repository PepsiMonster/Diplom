use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub max_time: f64,
    pub warmup_time: f64,
    pub replications: usize,
    pub seed: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioConfig {
    pub name: String,
    pub capacity_k: usize,
    pub servers_n: usize,
    pub total_resource_r: u32,
    pub arrival_rate_by_state: Vec<f64>,
    pub service_speed_by_state: Vec<f64>,
    pub simulation: SimulationConfig,
    pub mean_workload: f64,
}

impl ScenarioConfig {
    pub fn validate(&self) -> Result<(), String> {
        if self.capacity_k == 0 {
            return Err("capacity_k must be > 0".to_string());
        }
        if self.servers_n == 0 {
            return Err("servers_n must be > 0".to_string());
        }
        if self.total_resource_r == 0 {
            return Err("total_resource_r must be > 0".to_string());
        }
        if self.arrival_rate_by_state.len() != self.capacity_k + 1 {
            return Err("arrival_rate_by_state length mismatch".to_string());
        }
        if self.service_speed_by_state.len() != self.capacity_k + 1 {
            return Err("service_speed_by_state length mismatch".to_string());
        }
        if self.simulation.warmup_time >= self.simulation.max_time {
            return Err("warmup_time must be < max_time".to_string());
        }
        if self.mean_workload <= 0.0 {
            return Err("mean_workload must be > 0".to_string());
        }
        Ok(())
    }
}

pub fn constant_profile(capacity_k: usize, value: f64, last_value: Option<f64>) -> Vec<f64> {
    let mut profile = vec![value; capacity_k + 1];
    if let Some(v) = last_value {
        profile[capacity_k] = v;
    }
    profile
}

pub fn linear_decreasing_profile(capacity_k: usize, start_value: f64, step: f64, floor: f64) -> Vec<f64> {
    (0..=capacity_k)
        .map(|k| (start_value - step * k as f64).max(floor))
        .collect()
}

pub fn build_base_scenario(mean_workload: f64) -> ScenarioConfig {
    let capacity_k = 10;
    ScenarioConfig {
        name: "base".to_string(),
        capacity_k,
        servers_n: 10,
        total_resource_r: 20,
        arrival_rate_by_state: constant_profile(capacity_k, 1.8, Some(0.0)),
        service_speed_by_state: linear_decreasing_profile(capacity_k, 1.2, 0.04, 0.6),
        simulation: SimulationConfig {
            max_time: 2_000.0,
            warmup_time: 200.0,
            replications: 10,
            seed: 42,
        },
        mean_workload,
    }
}
