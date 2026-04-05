use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use chrono::Local;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use thiserror::Error;

use crate::params::{
    build_base_scenario_from_values, load_default_external_experiment_values,
    standard_workload_family_from_values, ExternalExperimentValues, ParamsError, ScenarioConfig,
};
use crate::simulation::{simulate_one_run, SimulationError, SimulationRunResult};

#[derive(Debug, Error)]
pub enum ExperimentsError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),

    #[error(transparent)]
    Simulation(#[from] SimulationError),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Csv(#[from] csv::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

type Result<T> = std::result::Result<T, ExperimentsError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricSummary {
    pub name: String,
    pub n: usize,
    pub mean: f64,
    pub std: f64,
    pub stderr: f64,
    pub ci_level: f64,
    pub ci_low: f64,
    pub ci_high: f64,
    pub min_value: f64,
    pub max_value: f64,
}

impl MetricSummary {
    pub fn as_flat_dict(&self, prefix: &str) -> BTreeMap<String, Value> {
        let base = format!("{prefix}{}", self.name);
        let mut row = BTreeMap::new();
        row.insert(format!("{base}__n"), json!(self.n));
        row.insert(format!("{base}__mean"), json!(self.mean));
        row.insert(format!("{base}__std"), json!(self.std));
        row.insert(format!("{base}__stderr"), json!(self.stderr));
        row.insert(format!("{base}__ci_low"), json!(self.ci_low));
        row.insert(format!("{base}__ci_high"), json!(self.ci_high));
        row.insert(format!("{base}__min"), json!(self.min_value));
        row.insert(format!("{base}__max"), json!(self.max_value));
        row
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioExperimentResult {
    pub scenario_name: String,
    pub scenario_description: String,
    pub replications: usize,
    pub metric_summaries: BTreeMap<String, MetricSummary>,
    pub run_results: Vec<SimulationRunResult>,
    pub run_summaries: Vec<BTreeMap<String, Value>>,
}

impl ScenarioExperimentResult {
    pub fn get_metric(&self, metric_name: &str) -> Result<&MetricSummary> {
        self.metric_summaries.get(metric_name).ok_or_else(|| {
            ExperimentsError::Validation(format!(
                "Метрика '{metric_name}' отсутствует в результатах сценария"
            ))
        })
    }

    pub fn flat_summary(&self) -> BTreeMap<String, Value> {
        let mut row = BTreeMap::new();
        row.insert("scenario_name".to_string(), json!(self.scenario_name));
        row.insert(
            "scenario_description".to_string(),
            json!(self.scenario_description),
        );
        row.insert("replications".to_string(), json!(self.replications));

        for metric_name in self.metric_summaries.keys() {
            let metric = &self.metric_summaries[metric_name];
            row.extend(metric.as_flat_dict(""));
        }

        row
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSuiteResult {
    pub suite_name: String,
    pub created_at: String,
    pub scenario_results: BTreeMap<String, ScenarioExperimentResult>,
}

impl ExperimentSuiteResult {
    pub fn aggregated_rows(&self) -> Vec<BTreeMap<String, Value>> {
        self.scenario_results
            .values()
            .map(|result| result.flat_summary())
            .collect()
    }

    pub fn all_run_rows(&self) -> Vec<BTreeMap<String, Value>> {
        let mut rows = Vec::new();

        for (scenario_key, result) in &self.scenario_results {
            for run_summary in &result.run_summaries {
                let mut row = run_summary.clone();
                row.insert("suite_name".to_string(), json!(self.suite_name));
                row.insert("scenario_key".to_string(), json!(scenario_key));
                row.insert("scenario_name".to_string(), json!(result.scenario_name));
                row.insert(
                    "scenario_description".to_string(),
                    json!(result.scenario_description),
                );
                rows.push(row);
            }
        }

        rows
    }

    pub fn metric_rows(&self) -> Vec<BTreeMap<String, Value>> {
        let mut rows = Vec::new();

        for (scenario_key, result) in &self.scenario_results {
            for (metric_name, summary) in &result.metric_summaries {
                let mut row = BTreeMap::new();
                row.insert("suite_name".to_string(), json!(self.suite_name));
                row.insert("scenario_key".to_string(), json!(scenario_key));
                row.insert("scenario_name".to_string(), json!(result.scenario_name));
                row.insert(
                    "scenario_description".to_string(),
                    json!(result.scenario_description),
                );
                row.insert("metric_name".to_string(), json!(metric_name));
                row.insert("n".to_string(), json!(summary.n));
                row.insert("mean".to_string(), json!(summary.mean));
                row.insert("std".to_string(), json!(summary.std));
                row.insert("stderr".to_string(), json!(summary.stderr));
                row.insert("ci_level".to_string(), json!(summary.ci_level));
                row.insert("ci_low".to_string(), json!(summary.ci_low));
                row.insert("ci_high".to_string(), json!(summary.ci_high));
                row.insert("min_value".to_string(), json!(summary.min_value));
                row.insert("max_value".to_string(), json!(summary.max_value));
                rows.push(row);
            }
        }

        rows
    }
}

fn normal_critical_value(ci_level: f64) -> Result<f64> {
    let rounded = (ci_level * 1_000_000.0).round() / 1_000_000.0;

    if (rounded - 0.90).abs() < 1e-9 {
        return Ok(1.644_853_626_951_472_2);
    }
    if (rounded - 0.95).abs() < 1e-9 {
        return Ok(1.959_963_984_540_054);
    }
    if (rounded - 0.99).abs() < 1e-9 {
        return Ok(2.575_829_303_548_900_4);
    }

    Err(ExperimentsError::Validation(format!(
        "Поддерживаются только уровни доверия 0.90, 0.95 и 0.99 (получено: {ci_level})"
    )))
}

pub fn summarize_numeric_metric(
    values: &[f64],
    metric_name: &str,
    ci_level: f64,
) -> Result<MetricSummary> {
    if values.is_empty() {
        return Err(ExperimentsError::Validation(format!(
            "Нельзя агрегировать пустой набор значений для метрики '{metric_name}'"
        )));
    }

    let n = values.len();
    let mean = values.iter().sum::<f64>() / n as f64;
    let min_value = values.iter().copied().fold(f64::INFINITY, f64::min);
    let max_value = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);

    let (std, stderr, ci_low, ci_high) = if n == 1 {
        (0.0, 0.0, mean, mean)
    } else {
        let sum_sq = values
            .iter()
            .map(|x| {
                let d = *x - mean;
                d * d
            })
            .sum::<f64>();

        let std = (sum_sq / (n as f64 - 1.0)).sqrt();
        let stderr = std / (n as f64).sqrt();
        let z = normal_critical_value(ci_level)?;
        let half_width = z * stderr;
        (std, stderr, mean - half_width, mean + half_width)
    };

    Ok(MetricSummary {
        name: metric_name.to_string(),
        n,
        mean,
        std,
        stderr,
        ci_level,
        ci_low,
        ci_high,
        min_value,
        max_value,
    })
}

pub fn extract_numeric_columns(rows: &[BTreeMap<String, Value>]) -> BTreeMap<String, Vec<f64>> {
    let mut columns: BTreeMap<String, Vec<f64>> = BTreeMap::new();

    for row in rows {
        for (key, value) in row {
            match value {
                Value::Number(num) => {
                    if let Some(v) = num.as_f64() {
                        columns.entry(key.clone()).or_default().push(v);
                    }
                }
                Value::Bool(_) => {}
                _ => {}
            }
        }
    }

    columns
}

pub fn run_scenario_experiment(
    scenario: &ScenarioConfig,
    ci_level: f64,
    keep_full_run_results: bool,
) -> Result<ScenarioExperimentResult> {
    scenario.validate()?;
    let replications = scenario.simulation.replications;

    let run_results_raw: Vec<std::result::Result<SimulationRunResult, ExperimentsError>> = (0
        ..replications)
        .into_par_iter()
        .map(|replication_index| {
            simulate_one_run(scenario.clone(), replication_index, None)
                .map_err(ExperimentsError::from)
        })
        .collect();

    let run_results: Vec<SimulationRunResult> = run_results_raw
        .into_iter()
        .collect::<std::result::Result<Vec<_>, _>>()?;

    let run_summaries: Vec<BTreeMap<String, Value>> =
        run_results.iter().map(|r| r.flat_summary()).collect();

    let numeric_columns = extract_numeric_columns(&run_summaries);

    let excluded_from_aggregation: BTreeSet<&str> = [
        "replication_index",
        "seed",
        "total_time",
        "warmup_time",
        "observed_time",
    ]
    .into_iter()
    .collect();

    let mut metric_summaries = BTreeMap::new();
    for (metric_name, values) in numeric_columns {
        if excluded_from_aggregation.contains(metric_name.as_str()) {
            continue;
        }

        let summary = summarize_numeric_metric(&values, &metric_name, ci_level)?;
        metric_summaries.insert(metric_name, summary);
    }

    Ok(ScenarioExperimentResult {
        scenario_name: scenario.name.clone(),
        scenario_description: scenario.short_description(),
        replications,
        metric_summaries,
        run_results: if keep_full_run_results {
            run_results
        } else {
            Vec::new()
        },
        run_summaries,
    })
}

pub fn run_experiment_suite(
    scenarios: &BTreeMap<String, ScenarioConfig>,
    suite_name: &str,
    ci_level: f64,
    keep_full_run_results: bool,
) -> Result<ExperimentSuiteResult> {
    let created_at = Local::now().format("%Y-%m-%dT%H:%M:%S").to_string();

    let results_raw: Vec<(String, Result<ScenarioExperimentResult>)> = scenarios
        .par_iter()
        .map(|(scenario_key, scenario)| {
            (
                scenario_key.clone(),
                run_scenario_experiment(scenario, ci_level, keep_full_run_results),
            )
        })
        .collect();

    let mut scenario_results = BTreeMap::new();
    for (scenario_key, result) in results_raw {
        scenario_results.insert(scenario_key, result?);
    }

    Ok(ExperimentSuiteResult {
        suite_name: suite_name.to_string(),
        created_at,
        scenario_results,
    })
}

pub fn print_scenario_experiment_summary(
    result: &ScenarioExperimentResult,
    metrics: Option<&[&str]>,
) {
    println!("{}", "=".repeat(96));
    println!("СЦЕНАРИЙ: {}", result.scenario_name);
    println!("{}", result.scenario_description);
    println!("Число повторов: {}", result.replications);
    println!("{}", "-".repeat(96));

    let default_metrics = [
        "mean_num_jobs",
        "mean_occupied_resource",
        "loss_probability",
        "throughput",
        "accepted_arrivals",
        "rejected_arrivals",
        "completed_jobs",
    ];

    let metrics_to_show = metrics.unwrap_or(&default_metrics);

    for metric_name in metrics_to_show {
        if let Some(m) = result.metric_summaries.get(*metric_name) {
            println!(
                "{:<28} mean={:>12.6} | std={:>12.6} | CI[{:.2}]=[{:>10.6}, {:>10.6}]",
                metric_name, m.mean, m.std, m.ci_level, m.ci_low, m.ci_high
            );
        }
    }

    println!("{}", "-".repeat(96));

    let pi_metrics: Vec<_> = result
        .metric_summaries
        .keys()
        .filter(|name| name.starts_with("pi_hat_"))
        .cloned()
        .collect();

    if !pi_metrics.is_empty() {
        println!("Оценка стационарного распределения по числу заявок:");
        for name in pi_metrics {
            let m = &result.metric_summaries[&name];
            let state_label = name.replace("pi_hat_", "");
            println!(
                "  k={:>2}: {:.6}  (CI[{:.2}] = [{:.6}, {:.6}])",
                state_label, m.mean, m.ci_level, m.ci_low, m.ci_high
            );
        }
    }

    println!("{}", "=".repeat(96));
    println!();
}

pub fn print_experiment_suite_summary(
    suite_result: &ExperimentSuiteResult,
    metrics: Option<&[&str]>,
) {
    println!("{}", "#".repeat(96));
    println!("НАБОР ЭКСПЕРИМЕНТОВ: {}", suite_result.suite_name);
    println!("Создан: {}", suite_result.created_at);
    println!("{}", "#".repeat(96));
    println!();

    for (scenario_key, result) in &suite_result.scenario_results {
        println!("[{}]", scenario_key);
        print_scenario_experiment_summary(result, metrics);
    }
}

fn ensure_directory(path: &Path) -> Result<()> {
    fs::create_dir_all(path)?;
    Ok(())
}

fn value_to_csv_string(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::Bool(v) => v.to_string(),
        Value::Number(v) => v.to_string(),
        Value::String(v) => v.clone(),
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

fn write_csv(rows: &[BTreeMap<String, Value>], filepath: &Path) -> Result<()> {
    if rows.is_empty() {
        fs::write(filepath, "")?;
        return Ok(());
    }

    let mut fieldnames = BTreeSet::new();
    for row in rows {
        for key in row.keys() {
            fieldnames.insert(key.clone());
        }
    }
    let fieldnames: Vec<String> = fieldnames.into_iter().collect();

    let file = File::create(filepath)?;
    let mut writer = BufWriter::new(file);

    writer.write_all(&[0xEF, 0xBB, 0xBF])?;

    let mut csv_writer = csv::Writer::from_writer(writer);
    csv_writer.write_record(&fieldnames)?;

    for row in rows {
        let record: Vec<String> = fieldnames
            .iter()
            .map(|key| row.get(key).map(value_to_csv_string).unwrap_or_default())
            .collect();
        csv_writer.write_record(&record)?;
    }

    csv_writer.flush()?;
    Ok(())
}

fn suite_to_json_ready(suite_result: &ExperimentSuiteResult) -> Value {
    let mut scenario_results_json = serde_json::Map::new();

    for (scenario_key, result) in &suite_result.scenario_results {
        let metric_summaries_json = result
            .metric_summaries
            .iter()
            .map(|(metric_name, metric_summary)| {
                (
                    metric_name.clone(),
                    serde_json::to_value(metric_summary).unwrap(),
                )
            })
            .collect::<serde_json::Map<String, Value>>();

        let scenario_json = json!({
            "scenario_name": result.scenario_name,
            "scenario_description": result.scenario_description,
            "replications": result.replications,
            "metric_summaries": metric_summaries_json,
            "run_summaries": result.run_summaries,
        });

        scenario_results_json.insert(scenario_key.clone(), scenario_json);
    }

    json!({
        "suite_name": suite_result.suite_name,
        "created_at": suite_result.created_at,
        "scenario_results": scenario_results_json,
    })
}

fn save_full_run_results_if_present(
    suite_result: &ExperimentSuiteResult,
    output_path: &Path,
) -> Result<()> {
    let base = output_path.join("full_run_results");
    let mut any_saved = false;

    for (scenario_key, result) in &suite_result.scenario_results {
        if result.run_results.is_empty() {
            continue;
        }
        any_saved = true;
        let scenario_dir = base.join(scenario_key);
        fs::create_dir_all(&scenario_dir)?;
        for run in &result.run_results {
            let file_name = format!("run_{:04}.json", run.replication_index);
            let path = scenario_dir.join(file_name);
            fs::write(path, serde_json::to_string_pretty(run)?)?;
        }
    }

    if !any_saved && base.exists() {
        fs::remove_dir_all(base)?;
    }

    Ok(())
}

pub fn save_experiment_suite(
    suite_result: &ExperimentSuiteResult,
    output_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let output_path = output_dir.as_ref().to_path_buf();
    ensure_directory(&output_path)?;

    let aggregated_rows = suite_result.aggregated_rows();
    let all_run_rows = suite_result.all_run_rows();
    let metric_rows = suite_result.metric_rows();
    let json_payload = suite_to_json_ready(suite_result);

    write_csv(
        &aggregated_rows,
        &output_path.join("aggregated_summary.csv"),
    )?;
    write_csv(&all_run_rows, &output_path.join("all_runs.csv"))?;
    write_csv(&metric_rows, &output_path.join("metric_summaries_long.csv"))?;
    fs::write(
        output_path.join("suite_result.json"),
        serde_json::to_string_pretty(&json_payload)?,
    )?;
    save_full_run_results_if_present(suite_result, &output_path)?;

    Ok(output_path)
}

pub fn build_default_experiment_suite(
    mean_workload: f64,
) -> Result<BTreeMap<String, ScenarioConfig>> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = mean_workload;
    build_default_experiment_suite_from_values(&values)
}

pub fn build_default_experiment_suite_from_values(
    values: &ExternalExperimentValues,
) -> Result<BTreeMap<String, ScenarioConfig>> {
    let workload_family = standard_workload_family_from_values(values)?;
    let baseline_workload = workload_family
        .get("deterministic")
        .cloned()
        .or_else(|| workload_family.values().next().cloned())
        .ok_or_else(|| {
            ExperimentsError::Validation(
                "Не удалось выбрать baseline workload для default-сценария".to_string(),
            )
        })?;
    let baseline = build_base_scenario_from_values(values, baseline_workload, "")?;

    let mut scenarios = BTreeMap::new();
    scenarios.insert("baseline".to_string(), baseline);
    Ok(scenarios)
}

pub fn self_test() -> Result<()> {
    let base_scenarios = build_default_experiment_suite(1.0)?;

    let mut demo_scenarios: BTreeMap<String, ScenarioConfig> = BTreeMap::new();
    for (key, scenario) in base_scenarios {
        let mut modified = scenario.clone();
        modified.simulation.max_time = 20_000.0;
        modified.simulation.warmup_time = 2_000.0;
        modified.simulation.replications = 5;
        modified.simulation.record_state_trace = false;
        modified.simulation.save_event_log = false;
        demo_scenarios.insert(key, modified);
    }

    let suite_result = run_experiment_suite(&demo_scenarios, "sensitivity_demo", 0.95, true)?;

    print_experiment_suite_summary(&suite_result, None);

    let timestamp = Local::now().format("%Y%m%d_%H%M%S").to_string();
    let output_dir = PathBuf::from("results").join("experiments").join(timestamp);
    let saved_path = save_experiment_suite(&suite_result, &output_dir)?;

    println!("Результаты сохранены в: {}", saved_path.display());
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summarize_numeric_metric_single_value() {
        let m = summarize_numeric_metric(&[1.5], "x", 0.95).unwrap();
        assert_eq!(m.n, 1);
        assert_eq!(m.mean, 1.5);
        assert_eq!(m.std, 0.0);
        assert_eq!(m.ci_low, 1.5);
        assert_eq!(m.ci_high, 1.5);
    }

    #[test]
    fn summarize_numeric_metric_multiple_values() {
        let m = summarize_numeric_metric(&[1.0, 2.0, 3.0], "x", 0.95).unwrap();
        assert_eq!(m.n, 3);
        assert!((m.mean - 2.0).abs() < 1e-12);
        assert!(m.std > 0.0);
        assert!(m.ci_high >= m.ci_low);
    }

    #[test]
    fn build_and_run_small_suite() {
        let mut scenarios = build_default_experiment_suite(1.0).unwrap();

        for scenario in scenarios.values_mut() {
            scenario.simulation.max_time = 50.0;
            scenario.simulation.warmup_time = 5.0;
            scenario.simulation.replications = 2;
            scenario.simulation.record_state_trace = false;
            scenario.simulation.save_event_log = false;
        }

        let suite = run_experiment_suite(&scenarios, "test_suite", 0.95, false).unwrap();
        assert!(!suite.scenario_results.is_empty());

        let aggregated = suite.aggregated_rows();
        assert_eq!(aggregated.len(), suite.scenario_results.len());

        let all_runs = suite.all_run_rows();
        assert_eq!(all_runs.len(), suite.scenario_results.len() * 2);
    }
}
