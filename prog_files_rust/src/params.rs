use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub max_time: f64,
    pub warmup_time: f64,
    pub replications: usize,
    pub seed: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ResourceDistributionConfig {
    DiscreteUniform { min_units: u32, max_units: u32 },
    DiscreteCustom { values: Vec<u32>, probabilities: Vec<f64> },
}

impl ResourceDistributionConfig {
    pub fn validate(&self) -> Result<(), String> {
        match self {
            Self::DiscreteUniform { min_units, max_units } => {
                if min_units == max_units && *min_units == 0 {
                    return Err("resource bounds must be positive".to_string());
                }
                if min_units > max_units {
                    return Err("min_units must be <= max_units".to_string());
                }
            }
            Self::DiscreteCustom { values, probabilities } => {
                if values.is_empty() || values.len() != probabilities.len() {
                    return Err("values/probabilities must be non-empty and same length".to_string());
                }
                if values.iter().any(|v| *v == 0) {
                    return Err("resource values must be > 0".to_string());
                }
                let s = probabilities.iter().sum::<f64>();
                if (s - 1.0).abs() > 1e-8 {
                    return Err("probabilities must sum to 1".to_string());
                }
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WorkloadDistributionConfig {
    Deterministic { value: f64, label: String },
    Exponential { mean: f64, label: String },
    Erlang { mean: f64, order: usize, label: String },
    Hyperexponential2 { mean: f64, p: f64, rates: [f64; 2], label: String },
}

impl WorkloadDistributionConfig {
    pub fn mean(&self) -> f64 {
        match self {
            Self::Deterministic { value, .. } => *value,
            Self::Exponential { mean, .. } => *mean,
            Self::Erlang { mean, .. } => *mean,
            Self::Hyperexponential2 { mean, .. } => *mean,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ArrivalProcessConfig {
    Poisson,
    Erlang { order: usize },
    Hyperexponential2 { p: f64, rates: [f64; 2] },
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
    pub resource_distribution: ResourceDistributionConfig,
    pub workload_distribution: WorkloadDistributionConfig,
    pub arrival_process: ArrivalProcessConfig,
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
        self.resource_distribution.validate()?;
        if self.workload_distribution.mean() <= 0.0 {
            return Err("workload mean must be > 0".to_string());
        }
        Ok(())
    }
}

pub fn threshold_profile(
    capacity_k: usize,
    normal_value: f64,
    threshold_k: usize,
    reduced_value: f64,
    full_state_value: f64,
) -> Vec<f64> {
    let mut profile = Vec::with_capacity(capacity_k + 1);
    for k in 0..=capacity_k {
        if k < threshold_k {
            profile.push(normal_value);
        } else {
            profile.push(reduced_value);
        }
    }
    profile[capacity_k] = full_state_value;
    profile
}

pub fn linear_decreasing_profile(capacity_k: usize, start_value: f64, step: f64, floor: f64) -> Vec<f64> {
    (0..=capacity_k)
        .map(|k| (start_value - step * k as f64).max(floor))
        .collect()
}

pub fn build_base_resource_distribution() -> ResourceDistributionConfig {
    ResourceDistributionConfig::DiscreteCustom {
        values: vec![2, 4, 8, 12, 16],
        probabilities: vec![0.30, 0.30, 0.20, 0.15, 0.05],
    }
}

pub fn build_base_arrival_profile(capacity_k: usize) -> Vec<f64> {
    threshold_profile(capacity_k, 3.20, capacity_k.saturating_sub(4), 2.20, 0.0)
}

pub fn build_base_service_profile(capacity_k: usize) -> Vec<f64> {
    linear_decreasing_profile(capacity_k, 1.40, 0.07, 0.35)
}

pub fn standard_workload_family(mean: f64) -> BTreeMap<String, WorkloadDistributionConfig> {
    let mut family = BTreeMap::new();
    family.insert(
        "deterministic".to_string(),
        WorkloadDistributionConfig::Deterministic {
            value: mean,
            label: "Deterministic".to_string(),
        },
    );
    family.insert(
        "exponential".to_string(),
        WorkloadDistributionConfig::Exponential {
            mean,
            label: "Exponential".to_string(),
        },
    );
    family.insert(
        "erlang_2".to_string(),
        WorkloadDistributionConfig::Erlang {
            mean,
            order: 2,
            label: "Erlang(2)".to_string(),
        },
    );
    family.insert(
        "erlang_4".to_string(),
        WorkloadDistributionConfig::Erlang {
            mean,
            order: 4,
            label: "Erlang(4)".to_string(),
        },
    );
    family.insert(
        "erlang_8".to_string(),
        WorkloadDistributionConfig::Erlang {
            mean,
            order: 8,
            label: "Erlang(8)".to_string(),
        },
    );
    family.insert(
        "hyperexp_2".to_string(),
        WorkloadDistributionConfig::Hyperexponential2 {
            mean,
            p: 0.5,
            rates: [2.4 / mean, 0.6 / mean],
            label: "HyperExp(2)".to_string(),
        },
    );
    family.insert(
        "hyperexp_heavy".to_string(),
        WorkloadDistributionConfig::Hyperexponential2 {
            mean,
            p: 0.85,
            rates: [6.0 / mean, 0.25 / mean],
            label: "HyperExpHeavy".to_string(),
        },
    );
    family
}

pub fn build_base_scenario(mean_workload: f64) -> ScenarioConfig {
    let capacity_k = 20;
    ScenarioConfig {
        name: "base".to_string(),
        capacity_k,
        servers_n: 12,
        total_resource_r: 40,
        arrival_rate_by_state: build_base_arrival_profile(capacity_k),
        service_speed_by_state: build_base_service_profile(capacity_k),
        simulation: SimulationConfig {
            max_time: 100_000.0,
            warmup_time: 20_000.0,
            replications: 30,
            seed: 42,
        },
        resource_distribution: build_base_resource_distribution(),
        workload_distribution: WorkloadDistributionConfig::Exponential {
            mean: mean_workload,
            label: "Exponential".to_string(),
        },
        arrival_process: ArrivalProcessConfig::Poisson,
    }
}

pub fn build_sensitivity_scenarios(mean_workload: f64) -> Vec<ScenarioConfig> {
    let mut scenarios = Vec::new();
    for (name, wd) in standard_workload_family(mean_workload) {
        let mut s = build_base_scenario(mean_workload);
        s.name = format!("base_{name}");
        s.workload_distribution = wd;
        scenarios.push(s);
    }
    scenarios
}
