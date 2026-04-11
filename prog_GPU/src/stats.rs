use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StatsError {
    #[error("{0}")]
    Validation(String),
}

pub type Result<T> = std::result::Result<T, StatsError>;

fn ensure_finite(name: &str, value: f64) -> Result<()> {
    if !value.is_finite() {
        return Err(StatsError::Validation(format!(
            "Значение '{name}' должно быть конечным числом, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_nonnegative_f64(name: &str, value: f64) -> Result<()> {
    ensure_finite(name, value)?;
    if value < 0.0 {
        return Err(StatsError::Validation(format!(
            "Значение '{name}' должно быть >= 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_nonnegative_u64(_name: &str, _value: u64) -> Result<()> {
    Ok(())
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

    Err(StatsError::Validation(format!(
        "Поддерживаются только уровни доверия 0.90, 0.95 и 0.99, получено: {ci_level}"
    )))
}

/// Краткий итог одного прогона.
/// Это основной контракт между backend и остальной частью проекта.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunSummary {
    pub scenario_key: String,
    pub scenario_name: String,
    pub replication_index: usize,
    pub seed: u64,

    pub total_time: f64,
    pub warmup_time: f64,
    pub observed_time: f64,

    pub arrival_attempts: u64,
    pub accepted_arrivals: u64,
    pub rejected_arrivals: u64,
    pub rejected_capacity: u64,
    pub rejected_server: u64,
    pub rejected_resource: u64,
    pub completed_jobs: u64,
    pub completed_time_samples: u64,

    pub mean_num_jobs: f64,
    pub mean_occupied_resource: f64,

    pub loss_probability: f64,
    pub throughput: f64,

    pub mean_service_time: f64,
    pub mean_sojourn_time: f64,
    pub std_service_time: f64,
    pub std_sojourn_time: f64,

    /// Оценка стационарного распределения по числу заявок в системе.
    /// Для loss-ветки длина обычно равна K+1 = N+1.
    pub pi_hat: Vec<f64>,
}

impl RunSummary {
    pub fn validate(&self) -> Result<()> {
        if self.scenario_key.trim().is_empty() {
            return Err(StatsError::Validation(
                "scenario_key не должен быть пустым".to_string(),
            ));
        }
        if self.scenario_name.trim().is_empty() {
            return Err(StatsError::Validation(
                "scenario_name не должен быть пустым".to_string(),
            ));
        }

        ensure_nonnegative_f64("total_time", self.total_time)?;
        ensure_nonnegative_f64("warmup_time", self.warmup_time)?;
        ensure_nonnegative_f64("observed_time", self.observed_time)?;

        if self.total_time <= 0.0 {
            return Err(StatsError::Validation(format!(
                "total_time должен быть > 0, получено: {}",
                self.total_time
            )));
        }

        if self.warmup_time >= self.total_time {
            return Err(StatsError::Validation(format!(
                "warmup_time должен быть строго меньше total_time, получено {} >= {}",
                self.warmup_time, self.total_time
            )));
        }

        if self.observed_time <= 0.0 {
            return Err(StatsError::Validation(format!(
                "observed_time должен быть > 0, получено: {}",
                self.observed_time
            )));
        }

        ensure_nonnegative_u64("arrival_attempts", self.arrival_attempts)?;
        ensure_nonnegative_u64("accepted_arrivals", self.accepted_arrivals)?;
        ensure_nonnegative_u64("rejected_arrivals", self.rejected_arrivals)?;
        ensure_nonnegative_u64("rejected_capacity", self.rejected_capacity)?;
        ensure_nonnegative_u64("rejected_server", self.rejected_server)?;
        ensure_nonnegative_u64("rejected_resource", self.rejected_resource)?;
        ensure_nonnegative_u64("completed_jobs", self.completed_jobs)?;
        ensure_nonnegative_u64("completed_time_samples", self.completed_time_samples)?;

        if self.accepted_arrivals + self.rejected_arrivals > self.arrival_attempts {
            return Err(StatsError::Validation(format!(
                "accepted_arrivals + rejected_arrivals не должно превышать arrival_attempts: {} + {} > {}",
                self.accepted_arrivals, self.rejected_arrivals, self.arrival_attempts
            )));
        }

        if self.rejected_capacity + self.rejected_server + self.rejected_resource
            > self.rejected_arrivals
        {
            return Err(StatsError::Validation(format!(
                "Сумма причин отказа не должна превышать rejected_arrivals: {} + {} + {} > {}",
                self.rejected_capacity,
                self.rejected_server,
                self.rejected_resource,
                self.rejected_arrivals
            )));
        }

        ensure_nonnegative_f64("mean_num_jobs", self.mean_num_jobs)?;
        ensure_nonnegative_f64("mean_occupied_resource", self.mean_occupied_resource)?;
        ensure_nonnegative_f64("loss_probability", self.loss_probability)?;
        ensure_nonnegative_f64("throughput", self.throughput)?;
        ensure_nonnegative_f64("mean_service_time", self.mean_service_time)?;
        ensure_nonnegative_f64("mean_sojourn_time", self.mean_sojourn_time)?;
        ensure_nonnegative_f64("std_service_time", self.std_service_time)?;
        ensure_nonnegative_f64("std_sojourn_time", self.std_sojourn_time)?;

        if self.loss_probability > 1.0 {
            return Err(StatsError::Validation(format!(
                "loss_probability не может быть > 1, получено: {}",
                self.loss_probability
            )));
        }

        if self.pi_hat.is_empty() {
            return Err(StatsError::Validation(
                "pi_hat не должен быть пустым".to_string(),
            ));
        }

        for (i, p) in self.pi_hat.iter().enumerate() {
            ensure_nonnegative_f64(&format!("pi_hat[{i}]"), *p)?;
        }

        let pi_sum: f64 = self.pi_hat.iter().sum();
        if (pi_sum - 1.0).abs() > 1e-6 {
            return Err(StatsError::Validation(format!(
                "Сумма pi_hat должна быть близка к 1.0, сейчас это {pi_sum}"
            )));
        }

        Ok(())
    }

    /// Все числовые метрики, пригодные для агрегирования по репликациям.
    pub fn numeric_metrics(&self) -> BTreeMap<String, f64> {
        let mut row = BTreeMap::new();

        row.insert("arrival_attempts".to_string(), self.arrival_attempts as f64);
        row.insert("accepted_arrivals".to_string(), self.accepted_arrivals as f64);
        row.insert("rejected_arrivals".to_string(), self.rejected_arrivals as f64);
        row.insert("rejected_capacity".to_string(), self.rejected_capacity as f64);
        row.insert("rejected_server".to_string(), self.rejected_server as f64);
        row.insert("rejected_resource".to_string(), self.rejected_resource as f64);
        row.insert("completed_jobs".to_string(), self.completed_jobs as f64);
        row.insert(
            "completed_time_samples".to_string(),
            self.completed_time_samples as f64,
        );

        row.insert("mean_num_jobs".to_string(), self.mean_num_jobs);
        row.insert(
            "mean_occupied_resource".to_string(),
            self.mean_occupied_resource,
        );
        row.insert("loss_probability".to_string(), self.loss_probability);
        row.insert("throughput".to_string(), self.throughput);
        row.insert("mean_service_time".to_string(), self.mean_service_time);
        row.insert("mean_sojourn_time".to_string(), self.mean_sojourn_time);
        row.insert("std_service_time".to_string(), self.std_service_time);
        row.insert("std_sojourn_time".to_string(), self.std_sojourn_time);

        for (k, value) in self.pi_hat.iter().enumerate() {
            row.insert(format!("pi_hat_{k}"), *value);
        }

        row
    }

    /// Плоское представление одного прогона для JSON/CSV.
    pub fn flat_row(&self) -> BTreeMap<String, Value> {
        let mut row = BTreeMap::new();

        row.insert("scenario_key".to_string(), json!(self.scenario_key));
        row.insert("scenario_name".to_string(), json!(self.scenario_name));
        row.insert("replication_index".to_string(), json!(self.replication_index));
        row.insert("seed".to_string(), json!(self.seed));

        row.insert("total_time".to_string(), json!(self.total_time));
        row.insert("warmup_time".to_string(), json!(self.warmup_time));
        row.insert("observed_time".to_string(), json!(self.observed_time));

        for (name, value) in self.numeric_metrics() {
            row.insert(name, json!(value));
        }

        row
    }
}

/// Агрегированная статистика по одной метрике.
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
    pub fn validate(&self) -> Result<()> {
        if self.name.trim().is_empty() {
            return Err(StatsError::Validation(
                "MetricSummary.name не должен быть пустым".to_string(),
            ));
        }

        if self.n == 0 {
            return Err(StatsError::Validation(
                "MetricSummary.n должен быть > 0".to_string(),
            ));
        }

        ensure_finite("mean", self.mean)?;
        ensure_nonnegative_f64("std", self.std)?;
        ensure_nonnegative_f64("stderr", self.stderr)?;
        ensure_finite("ci_low", self.ci_low)?;
        ensure_finite("ci_high", self.ci_high)?;
        ensure_finite("min_value", self.min_value)?;
        ensure_finite("max_value", self.max_value)?;

        if self.min_value > self.max_value {
            return Err(StatsError::Validation(format!(
                "MetricSummary.min_value не может быть больше max_value: {} > {}",
                self.min_value, self.max_value
            )));
        }

        Ok(())
    }

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

/// Полный набор результатов по одному сценарию:
/// - исходные прогоны,
/// - агрегированные метрики.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioStats {
    pub scenario_key: String,
    pub scenario_name: String,
    pub replications: usize,
    pub metric_summaries: BTreeMap<String, MetricSummary>,
    pub run_summaries: Vec<RunSummary>,
}

impl ScenarioStats {
    pub fn validate(&self) -> Result<()> {
        if self.scenario_key.trim().is_empty() {
            return Err(StatsError::Validation(
                "ScenarioStats.scenario_key не должен быть пустым".to_string(),
            ));
        }
        if self.scenario_name.trim().is_empty() {
            return Err(StatsError::Validation(
                "ScenarioStats.scenario_name не должен быть пустым".to_string(),
            ));
        }
        if self.replications == 0 {
            return Err(StatsError::Validation(
                "ScenarioStats.replications должен быть > 0".to_string(),
            ));
        }

        for run in &self.run_summaries {
            run.validate()?;
            if run.scenario_key != self.scenario_key {
                return Err(StatsError::Validation(format!(
                    "RunSummary.scenario_key={} не совпадает с ScenarioStats.scenario_key={}",
                    run.scenario_key, self.scenario_key
                )));
            }
        }

        for summary in self.metric_summaries.values() {
            summary.validate()?;
        }

        Ok(())
    }

    pub fn flat_summary_row(&self) -> BTreeMap<String, Value> {
        let mut row = BTreeMap::new();

        row.insert("scenario_key".to_string(), json!(self.scenario_key));
        row.insert("scenario_name".to_string(), json!(self.scenario_name));
        row.insert("replications".to_string(), json!(self.replications));

        for metric in self.metric_summaries.values() {
            row.extend(metric.as_flat_dict(""));
        }

        row
    }

    pub fn metric_rows(&self, suite_name: &str) -> Vec<BTreeMap<String, Value>> {
        let mut rows = Vec::new();

        for (metric_name, summary) in &self.metric_summaries {
            let mut row = BTreeMap::new();
            row.insert("suite_name".to_string(), json!(suite_name));
            row.insert("scenario_key".to_string(), json!(self.scenario_key));
            row.insert("scenario_name".to_string(), json!(self.scenario_name));
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

        rows
    }

    pub fn run_rows(&self, suite_name: &str) -> Vec<BTreeMap<String, Value>> {
        self.run_summaries
            .iter()
            .map(|run| {
                let mut row = run.flat_row();
                row.insert("suite_name".to_string(), json!(suite_name));
                row
            })
            .collect()
    }
}

/// Полный результат серии экспериментов.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSuiteResult {
    pub suite_name: String,
    pub created_at: String,
    pub ci_level: f64,
    pub scenario_results: BTreeMap<String, ScenarioStats>,
}

impl ExperimentSuiteResult {
    pub fn validate(&self) -> Result<()> {
        if self.suite_name.trim().is_empty() {
            return Err(StatsError::Validation(
                "ExperimentSuiteResult.suite_name не должен быть пустым".to_string(),
            ));
        }

        normal_critical_value(self.ci_level)?;

        for (scenario_key, stats) in &self.scenario_results {
            stats.validate()?;
            if scenario_key != &stats.scenario_key {
                return Err(StatsError::Validation(format!(
                    "Ключ в scenario_results ({}) не совпадает с stats.scenario_key ({})",
                    scenario_key, stats.scenario_key
                )));
            }
        }

        Ok(())
    }

    pub fn aggregated_rows(&self) -> Vec<BTreeMap<String, Value>> {
        self.scenario_results
            .values()
            .map(|stats| {
                let mut row = stats.flat_summary_row();
                row.insert("suite_name".to_string(), json!(self.suite_name));
                row.insert("created_at".to_string(), json!(self.created_at));
                row.insert("ci_level".to_string(), json!(self.ci_level));
                row
            })
            .collect()
    }

    pub fn metric_rows(&self) -> Vec<BTreeMap<String, Value>> {
        let mut rows = Vec::new();
        for stats in self.scenario_results.values() {
            rows.extend(stats.metric_rows(&self.suite_name));
        }
        rows
    }

    pub fn all_run_rows(&self) -> Vec<BTreeMap<String, Value>> {
        let mut rows = Vec::new();
        for stats in self.scenario_results.values() {
            rows.extend(stats.run_rows(&self.suite_name));
        }
        rows
    }
}

/// Сводка массива чисел в одну MetricSummary.
pub fn summarize_numeric_metric(
    values: &[f64],
    metric_name: &str,
    ci_level: f64,
) -> Result<MetricSummary> {
    if values.is_empty() {
        return Err(StatsError::Validation(format!(
            "Нельзя агрегировать пустой набор значений для метрики '{metric_name}'"
        )));
    }

    normal_critical_value(ci_level)?;

    for (i, v) in values.iter().enumerate() {
        ensure_finite(&format!("{metric_name}[{i}]"), *v)?;
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

    let summary = MetricSummary {
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
    };

    summary.validate()?;
    Ok(summary)
}

/// Сгруппировать числовые метрики из набора RunSummary.
/// Каждое имя метрики -> массив значений по всем репликациям.
pub fn collect_numeric_columns(runs: &[RunSummary]) -> Result<BTreeMap<String, Vec<f64>>> {
    if runs.is_empty() {
        return Err(StatsError::Validation(
            "Нельзя собрать numeric columns из пустого набора RunSummary".to_string(),
        ));
    }

    let mut columns: BTreeMap<String, Vec<f64>> = BTreeMap::new();

    for run in runs {
        run.validate()?;
        for (name, value) in run.numeric_metrics() {
            columns.entry(name).or_default().push(value);
        }
    }

    Ok(columns)
}

/// Построить агрегированную статистику по одному сценарию.
pub fn summarize_scenario_runs(
    scenario_key: &str,
    scenario_name: &str,
    runs: Vec<RunSummary>,
    ci_level: f64,
) -> Result<ScenarioStats> {
    if scenario_key.trim().is_empty() {
        return Err(StatsError::Validation(
            "scenario_key не должен быть пустым".to_string(),
        ));
    }
    if scenario_name.trim().is_empty() {
        return Err(StatsError::Validation(
            "scenario_name не должен быть пустым".to_string(),
        ));
    }
    if runs.is_empty() {
        return Err(StatsError::Validation(format!(
            "Для сценария '{scenario_key}' передан пустой набор run summaries"
        )));
    }

    let expected_key = scenario_key.to_string();
    let expected_name = scenario_name.to_string();

    for run in &runs {
        run.validate()?;
        if run.scenario_key != expected_key {
            return Err(StatsError::Validation(format!(
                "RunSummary.scenario_key={} не совпадает с ожидаемым {}",
                run.scenario_key, expected_key
            )));
        }
        if run.scenario_name != expected_name {
            return Err(StatsError::Validation(format!(
                "RunSummary.scenario_name={} не совпадает с ожидаемым {}",
                run.scenario_name, expected_name
            )));
        }
    }

    let columns = collect_numeric_columns(&runs)?;
    let mut metric_summaries = BTreeMap::new();

    for (metric_name, values) in columns {
        let summary = summarize_numeric_metric(&values, &metric_name, ci_level)?;
        metric_summaries.insert(metric_name, summary);
    }

    let stats = ScenarioStats {
        scenario_key: expected_key,
        scenario_name: expected_name,
        replications: runs.len(),
        metric_summaries,
        run_summaries: runs,
    };

    stats.validate()?;
    Ok(stats)
}

/// Утилита для красивого списка имён метрик.
pub fn sorted_metric_names(stats: &ScenarioStats) -> Vec<String> {
    let mut names: BTreeSet<String> = BTreeSet::new();
    for name in stats.metric_summaries.keys() {
        names.insert(name.clone());
    }
    names.into_iter().collect()
}