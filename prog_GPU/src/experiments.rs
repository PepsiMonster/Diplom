use crate::backend::{
    build_run_requests, create_backend, BackendError, RunRequest, SimulationBackend,
};
use crate::cli::{BackendKind, ScenarioFamily};
use crate::params::{ExperimentConfig, ParamsError};
use crate::scenario_grid::{build_scenario_grid, ScenarioGrid, ScenarioGridError, ScenarioSpec};
use crate::stats::{
    summarize_scenario_runs, ExperimentSuiteResult, RunSummary, ScenarioStats, StatsError,
};
use chrono::Local;
use std::collections::BTreeMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ExperimentsError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),

    #[error(transparent)]
    ScenarioGrid(#[from] ScenarioGridError),

    #[error(transparent)]
    Backend(#[from] BackendError),

    #[error(transparent)]
    Stats(#[from] StatsError),
}

pub type Result<T> = std::result::Result<T, ExperimentsError>;

/// Полный план серии экспериментов:
/// - итоговая конфигурация после override-ов,
/// - выбранное семейство сценариев,
/// - готовая сетка сценариев,
/// - развёрнутый список run requests.
#[derive(Debug, Clone)]
pub struct ExperimentPlan {
    pub suite_name: String,
    pub family: ScenarioFamily,
    pub config: ExperimentConfig,
    pub grid: ScenarioGrid,
    pub run_requests: Vec<RunRequest>,
}

impl ExperimentPlan {
    pub fn summary_string(&self) -> String {
        format!(
            concat!(
                "ExperimentPlan(",
                "suite_name='{}', family={:?}, scenarios={}, runs={}",
                ")"
            ),
            self.suite_name,
            self.family,
            self.grid.scenarios.len(),
            self.run_requests.len()
        )
    }
}

/// Построить полный план эксперимента:
/// config -> scenario grid -> run requests.
pub fn build_experiment_plan(
    config: &ExperimentConfig,
    family: ScenarioFamily,
    suite_name_override: Option<String>,
) -> Result<ExperimentPlan> {
    config.validate()?;

    let effective_config = config.with_overrides(suite_name_override, None, None, None)?;
    let grid = build_scenario_grid(&effective_config, family)?;
    let run_requests = build_run_requests(&grid.scenarios);

    if run_requests.is_empty() {
        return Err(ExperimentsError::Validation(
            "После построения плана список run_requests оказался пустым".to_string(),
        ));
    }

    Ok(ExperimentPlan {
        suite_name: effective_config.suite_name.clone(),
        family,
        config: effective_config,
        grid,
        run_requests,
    })
}

/// Удобная обёртка:
/// - создать backend по BackendKind;
/// - построить план;
/// - выполнить серию;
/// - вернуть полный ExperimentSuiteResult.
pub fn run_experiment_suite(
    config: &ExperimentConfig,
    family: ScenarioFamily,
    backend_kind: BackendKind,
    suite_name_override: Option<String>,
    ci_level: f64,
) -> Result<ExperimentSuiteResult> {
    let plan = build_experiment_plan(config, family, suite_name_override)?;
    let backend = create_backend(backend_kind)?;
    execute_experiment_plan(&plan, backend.as_ref(), ci_level)
}

/// Выполнить уже построенный план эксперимента через конкретный backend.
pub fn execute_experiment_plan(
    plan: &ExperimentPlan,
    backend: &dyn SimulationBackend,
    ci_level: f64,
) -> Result<ExperimentSuiteResult> {
    let run_summaries: Vec<RunSummary> = backend.execute_batch(&plan.run_requests)?;

    assemble_suite_result(
        &plan.suite_name,
        ci_level,
        &plan.grid.scenarios,
        run_summaries,
    )
}

/// Собрать итоговый suite result из:
/// - имени серии,
/// - уровня доверия,
/// - списка сценариев,
/// - списка результатов отдельных прогонов.
pub fn assemble_suite_result(
    suite_name: &str,
    ci_level: f64,
    scenarios: &[ScenarioSpec],
    run_summaries: Vec<RunSummary>,
) -> Result<ExperimentSuiteResult> {
    if suite_name.trim().is_empty() {
        return Err(ExperimentsError::Validation(
            "suite_name не должен быть пустым".to_string(),
        ));
    }

    if scenarios.is_empty() {
        return Err(ExperimentsError::Validation(
            "Нельзя собрать suite result для пустого списка сценариев".to_string(),
        ));
    }

    if run_summaries.is_empty() {
        return Err(ExperimentsError::Validation(
            "Нельзя собрать suite result для пустого списка run summaries".to_string(),
        ));
    }

    let mut scenarios_by_key: BTreeMap<String, &ScenarioSpec> = BTreeMap::new();
    for scenario in scenarios {
        let prev = scenarios_by_key.insert(scenario.scenario_key.clone(), scenario);
        if prev.is_some() {
            return Err(ExperimentsError::Validation(format!(
                "Обнаружен дублирующий scenario_key в сетке сценариев: {}",
                scenario.scenario_key
            )));
        }
    }

    let mut grouped_runs: BTreeMap<String, Vec<RunSummary>> = BTreeMap::new();
    for run in run_summaries {
        run.validate()?;

        if !scenarios_by_key.contains_key(&run.scenario_key) {
            return Err(ExperimentsError::Validation(format!(
                "RunSummary ссылается на неизвестный scenario_key: {}",
                run.scenario_key
            )));
        }

        grouped_runs
            .entry(run.scenario_key.clone())
            .or_default()
            .push(run);
    }

    let mut scenario_results: BTreeMap<String, ScenarioStats> = BTreeMap::new();

    for (scenario_key, scenario) in scenarios_by_key {
        let runs = grouped_runs.remove(&scenario_key).ok_or_else(|| {
            ExperimentsError::Validation(format!(
                "Для сценария '{}' не найдено ни одного RunSummary",
                scenario_key
            ))
        })?;

        let stats = summarize_scenario_runs(
            &scenario.scenario_key,
            &scenario.scenario_name,
            runs,
            ci_level,
        )?;

        scenario_results.insert(scenario_key, stats);
    }

    if !grouped_runs.is_empty() {
        let unexpected: Vec<String> = grouped_runs.keys().cloned().collect();
        return Err(ExperimentsError::Validation(format!(
            "Остались RunSummary для неожиданных scenario_key: {:?}",
            unexpected
        )));
    }

    let suite_result = ExperimentSuiteResult {
        suite_name: suite_name.to_string(),
        created_at: Local::now().format("%Y-%m-%dT%H:%M:%S").to_string(),
        ci_level,
        scenario_results,
    };

    suite_result.validate()?;
    Ok(suite_result)
}

/// Утилита для режима `list-scenarios`:
/// построить grid и вернуть строки для печати.
pub fn list_scenario_descriptions(
    config: &ExperimentConfig,
    family: ScenarioFamily,
    suite_name_override: Option<String>,
) -> Result<Vec<String>> {
    let plan = build_experiment_plan(config, family, suite_name_override)?;
    Ok(plan
        .grid
        .scenarios
        .iter()
        .map(|s| s.short_description())
        .collect())
}

/// Краткая сводка по сценарию — удобно печатать в консоль.
pub fn render_scenario_stats_text(stats: &ScenarioStats, metric_names: Option<&[&str]>) -> String {
    let default_metrics = [
        "mean_num_jobs",
        "mean_occupied_resource",
        "loss_probability",
        "throughput",
        "accepted_arrivals",
        "rejected_arrivals",
        "completed_jobs",
        "mean_service_time",
        "mean_sojourn_time",
    ];

    let metrics_to_show = metric_names.unwrap_or(&default_metrics);

    let mut out = String::new();
    out.push_str(&format!("{}\n", "=".repeat(96)));
    out.push_str(&format!("SCENARIO: {}\n", stats.scenario_name));
    out.push_str(&format!("KEY: {}\n", stats.scenario_key));
    out.push_str(&format!("Replications: {}\n", stats.replications));
    out.push_str(&format!("{}\n", "-".repeat(96)));

    for metric_name in metrics_to_show {
        if let Some(m) = stats.metric_summaries.get(*metric_name) {
            out.push_str(&format!(
                "{:<28} mean={:>12.6} | std={:>12.6} | CI[{:.2}]=[{:>10.6}, {:>10.6}]\n",
                metric_name, m.mean, m.std, m.ci_level, m.ci_low, m.ci_high
            ));
        }
    }

    let pi_metrics: Vec<_> = stats
        .metric_summaries
        .keys()
        .filter(|name| name.starts_with("pi_hat_"))
        .cloned()
        .collect();

    if !pi_metrics.is_empty() {
        out.push_str(&format!("{}\n", "-".repeat(96)));
        out.push_str("Stationary distribution estimate pi_hat(k):\n");
        for name in pi_metrics {
            if let Some(m) = stats.metric_summaries.get(&name) {
                let state_label = name.replace("pi_hat_", "");
                out.push_str(&format!(
                    "  k={:>3}: {:.6}  (CI[{:.2}] = [{:.6}, {:.6}])\n",
                    state_label, m.mean, m.ci_level, m.ci_low, m.ci_high
                ));
            }
        }
    }

    out.push_str(&format!("{}\n", "=".repeat(96)));
    out
}

/// Краткая сводка по всей серии — удобно печатать в консоль.
pub fn render_suite_summary_text(
    suite_result: &ExperimentSuiteResult,
    metric_names: Option<&[&str]>,
) -> String {
    let mut out = String::new();

    out.push_str(&format!("{}\n", "#".repeat(96)));
    out.push_str(&format!("SUITE: {}\n", suite_result.suite_name));
    out.push_str(&format!("Created at: {}\n", suite_result.created_at));
    out.push_str(&format!("CI level: {}\n", suite_result.ci_level));
    out.push_str(&format!(
        "Scenarios: {}\n",
        suite_result.scenario_results.len()
    ));
    out.push_str(&format!("{}\n\n", "#".repeat(96)));

    for stats in suite_result.scenario_results.values() {
        out.push_str(&render_scenario_stats_text(stats, metric_names));
        out.push('\n');
    }

    out
}
