use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::params::ScenarioConfig;
use crate::simulation::{simulate_one_run, SimulationRunResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricSummary {
    pub mean: f64,
    pub min: f64,
    pub max: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioExperimentResult {
    pub scenario_name: String,
    pub replications: usize,
    pub throughput: MetricSummary,
    pub loss_probability: MetricSummary,
    pub mean_num_jobs: MetricSummary,
    pub mean_occupied_resource: MetricSummary,
    pub runs: Vec<SimulationRunResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSuiteResult {
    pub suite_name: String,
    pub created_at: String,
    pub scenarios: Vec<ScenarioExperimentResult>,
}

fn summarize(values: &[f64]) -> MetricSummary {
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let min = values.iter().copied().fold(f64::INFINITY, f64::min);
    let max = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    MetricSummary { mean, min, max }
}

pub fn run_scenario_experiment(scenario: &ScenarioConfig) -> ScenarioExperimentResult {
    let runs = (0..scenario.simulation.replications)
        .into_par_iter()
        .map(|idx| simulate_one_run(scenario, idx, None))
        .collect::<Vec<_>>();

    let throughput = summarize(&runs.iter().map(|r| r.throughput).collect::<Vec<_>>());
    let loss_probability = summarize(&runs.iter().map(|r| r.loss_probability).collect::<Vec<_>>());
    let mean_num_jobs = summarize(&runs.iter().map(|r| r.mean_num_jobs).collect::<Vec<_>>());
    let mean_occupied_resource = summarize(&runs.iter().map(|r| r.mean_occupied_resource).collect::<Vec<_>>());

    ScenarioExperimentResult {
        scenario_name: scenario.name.clone(),
        replications: scenario.simulation.replications,
        throughput,
        loss_probability,
        mean_num_jobs,
        mean_occupied_resource,
        runs,
    }
}

pub fn run_experiment_suite(scenarios: &[ScenarioConfig], suite_name: &str) -> ExperimentSuiteResult {
    let scenario_results = scenarios
        .par_iter()
        .map(run_scenario_experiment)
        .collect::<Vec<_>>();

    ExperimentSuiteResult {
        suite_name: suite_name.to_string(),
        created_at: chrono::Utc::now().to_rfc3339(),
        scenarios: scenario_results,
    }
}
