use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;

use chrono::Local;
use clap::{Args, Parser, Subcommand, ValueEnum};
// use serde_json::json;
use thiserror::Error;

use crate::experiments::{
    build_default_experiment_suite, run_experiment_suite, save_experiment_suite,
    ExperimentSuiteResult, ExperimentsError,
};
use crate::params::{
    build_arrival_sensitivity_scenarios_from_values, build_base_scenario_from_values,
    build_combined_sensitivity_scenarios_from_values,
    build_workload_sensitivity_scenarios_from_values, load_default_external_experiment_values,
    standard_workload_family_from_values, ArrivalProcessConfig, ExternalExperimentValues,
    ParamsError, ScenarioConfig,
};
use crate::simulation::{simulate_one_run, SimulationError, SimulationRunResult};

#[derive(Debug, Error)]
pub enum RunError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),

    #[error(transparent)]
    Simulation(#[from] SimulationError),

    #[error(transparent)]
    Experiments(#[from] ExperimentsError),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

type Result<T> = std::result::Result<T, RunError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ScenarioFamily {
    Base,
    WorkloadSensitivity,
    ArrivalSensitivity,
    CombinedSensitivity,
}

#[derive(Debug, Parser)]
#[command(
    name = "prog_files_rust",
    about = "Единая точка входа для симуляции, экспериментов и plotting"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Debug, Subcommand)]
pub enum Commands {
    Single(SingleArgs),
    Suite(SuiteArgs),
    Plots(PlotsArgs),
    Full(FullArgs),
}

#[derive(Debug, Clone, Args)]
pub struct SingleArgs {
    #[arg(long)]
    pub seed: Option<u64>,

    #[arg(long, default_value_t = 0)]
    pub replication_index: usize,

    #[arg(long)]
    pub max_time: Option<f64>,

    #[arg(long)]
    pub warmup_time: Option<f64>,

    #[arg(long, default_value_t = 1.0)]
    pub mean_workload: f64,

    #[arg(long, default_value_t = false)]
    pub record_state_trace: bool,

    #[arg(long, default_value_t = false)]
    pub save_event_log: bool,

    #[arg(long, default_value = "results")]
    pub output_root: String,
}

#[derive(Debug, Clone, Args)]
pub struct SuiteArgs {
    #[arg(long, value_enum, default_value_t = ScenarioFamily::Base)]
    pub scenario_family: ScenarioFamily,

    #[arg(long, default_value = "experiment_suite")]
    pub suite_name: String,

    #[arg(long, default_value_t = 1.0)]
    pub mean_workload: f64,

    #[arg(long)]
    pub replications: Option<usize>,

    #[arg(long)]
    pub max_time: Option<f64>,

    #[arg(long)]
    pub warmup_time: Option<f64>,

    #[arg(long, default_value_t = 0.95)]
    pub ci_level: f64,

    #[arg(long, default_value_t = false)]
    pub record_state_trace: bool,

    #[arg(long, default_value_t = false)]
    pub save_event_log: bool,

    #[arg(long, default_value_t = false)]
    pub keep_full_run_results: bool,

    #[arg(long)]
    pub metrics: Vec<String>,

    #[arg(long, default_value = "results")]
    pub output_root: String,
}

#[derive(Debug, Clone, Args)]
pub struct PlotsArgs {
    #[arg(long)]
    pub input: String,

    #[arg(long)]
    pub output_dir: Option<String>,

    #[arg(long, default_value_t = 200)]
    pub dpi: u32,

    #[arg(long)]
    pub metrics: Vec<String>,
}

#[derive(Debug, Clone, Args)]
pub struct FullArgs {
    #[arg(long, value_enum, default_value_t = ScenarioFamily::Base)]
    pub scenario_family: ScenarioFamily,

    #[arg(long, default_value = "full_pipeline")]
    pub suite_name: String,

    #[arg(long, default_value_t = 1.0)]
    pub mean_workload: f64,

    #[arg(long)]
    pub replications: Option<usize>,

    #[arg(long)]
    pub max_time: Option<f64>,

    #[arg(long)]
    pub warmup_time: Option<f64>,

    #[arg(long, default_value_t = 0.95)]
    pub ci_level: f64,

    #[arg(long, default_value_t = false)]
    pub record_state_trace: bool,

    #[arg(long, default_value_t = false)]
    pub save_event_log: bool,

    #[arg(long, default_value_t = false)]
    pub keep_full_run_results: bool,

    #[arg(long, default_value = "results")]
    pub output_root: String,

    #[arg(long, default_value_t = 200)]
    pub dpi: u32,

    #[arg(long)]
    pub metrics: Vec<String>,
}

fn timestamp() -> String {
    Local::now().format("%Y%m%d_%H%M%S").to_string()
}

fn ensure_dir(path: impl AsRef<Path>) -> Result<PathBuf> {
    let path_obj = path.as_ref().to_path_buf();
    fs::create_dir_all(&path_obj)?;
    Ok(path_obj)
}

fn resolve_suite_result_json(input_path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = input_path.as_ref();

    if path.is_dir() {
        let candidate = path.join("suite_result.json");
        if !candidate.exists() {
            return Err(RunError::Validation(format!(
                "В директории '{}' не найден файл suite_result.json",
                path.display()
            )));
        }
        return Ok(candidate);
    }

    if path.is_file() {
        let is_json = path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|s| s.eq_ignore_ascii_case("json"))
            .unwrap_or(false);
        if !is_json {
            return Err(RunError::Validation(format!(
                "Ожидался JSON-файл результата или директория результата, получено: {}",
                path.display()
            )));
        }
        return Ok(path.to_path_buf());
    }

    Err(RunError::Validation(format!(
        "Путь не найден: {}",
        path.display()
    )))
}

fn short_profile(value: &str) -> &str {
    match value {
        "state_dependent" => "sd",
        "constant" => "const",
        other => other,
    }
}

fn fixed_arrival_process_key(values: &ExternalExperimentValues) -> String {
    if values.arrival_process_family.len() == 1 {
        return values.arrival_process_family[0].clone();
    }
    if values
        .arrival_process_family
        .iter()
        .any(|item| item == "poisson")
    {
        return "poisson".to_string();
    }
    "unspecified".to_string()
}

fn effective_workload_slug(
    values: &ExternalExperimentValues,
    scenario_family: ScenarioFamily,
) -> String {
    match scenario_family {
        ScenarioFamily::ArrivalSensitivity => format!("fixed-{}", values.fixed_workload),
        _ => values.workload_family_profile.clone(),
    }
}

fn profile_slug(values: &ExternalExperimentValues, scenario_family: ScenarioFamily) -> String {
    format!(
        "arrprof-{}__srvprof-{}__work-{}",
        short_profile(&values.arrival_rate_profile),
        short_profile(&values.service_speed_profile),
        effective_workload_slug(values, scenario_family)
    )
}

fn scenario_family_slug(scenario_family: ScenarioFamily) -> &'static str {
    match scenario_family {
        ScenarioFamily::Base => "base",
        ScenarioFamily::WorkloadSensitivity => "work",
        ScenarioFamily::ArrivalSensitivity => "arr",
        ScenarioFamily::CombinedSensitivity => "comb",
    }
}

fn output_series_slug(
    values: &ExternalExperimentValues,
    scenario_family: ScenarioFamily,
) -> String {
    format!(
        "sf-{}__{}",
        scenario_family_slug(scenario_family),
        profile_slug(values, scenario_family)
    )
}

fn profile_summary(values: &ExternalExperimentValues, scenario_family: ScenarioFamily) -> String {
    match scenario_family {
        ScenarioFamily::WorkloadSensitivity => format!(
            "arrival_rate={}, service_speed={}, workload_family={}, fixed_arrival_process={}",
            values.arrival_rate_profile,
            values.service_speed_profile,
            values.workload_family_profile,
            fixed_arrival_process_key(values)
        ),
        ScenarioFamily::ArrivalSensitivity => format!(
            "arrival_rate={}, service_speed={}, workload=fixed:{}",
            values.arrival_rate_profile, values.service_speed_profile, values.fixed_workload
        ),
        ScenarioFamily::CombinedSensitivity => format!(
            "arrival_rate={}, service_speed={}, workload_family={}, arrival_process_family={:?}",
            values.arrival_rate_profile,
            values.service_speed_profile,
            values.workload_family_profile,
            values.arrival_process_family
        ),
        ScenarioFamily::Base => format!(
            "arrival_rate={}, service_speed={}, workload=fixed:{}",
            values.arrival_rate_profile, values.service_speed_profile, values.fixed_workload
        ),
    }
}

fn scenario_family_summary(
    values: &ExternalExperimentValues,
    scenario_family: ScenarioFamily,
) -> String {
    match scenario_family {
        ScenarioFamily::Base => "base: один базовый сценарий".to_string(),
        ScenarioFamily::WorkloadSensitivity => format!(
            "workload-sensitivity: меняется workload family ({}), arrival process фиксируется",
            values.workload_family_profile
        ),
        ScenarioFamily::ArrivalSensitivity => format!(
            "arrival-sensitivity: меняется arrival process family, workload фиксируется ({})",
            values.fixed_workload
        ),
        ScenarioFamily::CombinedSensitivity => format!(
            "combined-sensitivity: меняются и arrival process family, и workload family ({})",
            values.workload_family_profile
        ),
    }
}

fn make_timestamped_dir_with_slug(base_dir: impl AsRef<Path>, slug: &str) -> Result<PathBuf> {
    ensure_dir(base_dir.as_ref().join(format!("{}__{}", timestamp(), slug)))
}

fn make_single_run_root(base_dir: impl AsRef<Path>) -> Result<PathBuf> {
    ensure_dir(base_dir.as_ref().join("single").join(timestamp()))
}

fn override_simulation_config(
    scenario: &ScenarioConfig,
    max_time: Option<f64>,
    warmup_time: Option<f64>,
    replications: Option<usize>,
    record_state_trace: bool,
    save_event_log: bool,
) -> ScenarioConfig {
    let mut updated = scenario.clone();

    if let Some(v) = max_time {
        updated.simulation.max_time = v;
    }
    if let Some(v) = warmup_time {
        updated.simulation.warmup_time = v;
    }
    if let Some(v) = replications {
        updated.simulation.replications = v;
    }
    if record_state_trace {
        updated.simulation.record_state_trace = true;
    }
    if save_event_log {
        updated.simulation.save_event_log = true;
    }

    updated
}

fn save_single_run_result(
    result: &SimulationRunResult,
    output_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let out_dir = ensure_dir(output_dir)?;
    let out_path = out_dir.join("single_run_result.json");
    fs::write(&out_path, serde_json::to_string_pretty(result)?)?;
    Ok(out_path)
}

fn format_metric<T: ToString>(value: T) -> String {
    value.to_string()
}

fn save_markdown_report(lines: &[String], output_path: impl AsRef<Path>) -> Result<PathBuf> {
    let out = output_path.as_ref().to_path_buf();
    let mut body = lines.join("\n");
    if !body.ends_with('\n') {
        body.push('\n');
    }
    fs::write(&out, body)?;
    Ok(out)
}

fn save_text_report(text: &str, output_path: impl AsRef<Path>) -> Result<PathBuf> {
    let out = output_path.as_ref().to_path_buf();
    let mut body = text.to_string();
    if !body.ends_with('\n') {
        body.push('\n');
    }
    fs::write(&out, body)?;
    Ok(out)
}

fn render_single_run_text(result: &SimulationRunResult, scenario: &ScenarioConfig) -> String {
    let mut out = String::new();
    out.push_str(&format!("{}\n", "=".repeat(90)));
    out.push_str("РЕЗУЛЬТАТ ОДНОГО ПРОГОНА\n");
    out.push_str(&format!("{}\n", "=".repeat(90)));
    out.push_str(&format!(
        "{}\n",
        scenario.summary_string().unwrap_or_default()
    ));
    out.push_str(&format!("Сценарий: {}\n", result.scenario_name));
    out.push_str(&format!(
        "Replication index: {}\n",
        result.replication_index
    ));
    out.push_str(&format!("Seed: {}\n", result.seed));
    out.push_str(&format!(
        "Полное время моделирования: {}\n",
        result.total_time
    ));
    out.push_str(&format!("Warm-up: {}\n", result.warmup_time));
    out.push_str(&format!("Наблюдаемое время: {}\n", result.observed_time));
    out.push_str(&format!("{}\n", "-".repeat(90)));
    out.push_str(&format!(
        "Среднее число заявок: {:.6}\n",
        result.mean_num_jobs
    ));
    out.push_str(&format!(
        "Средний занятый ресурс: {:.6}\n",
        result.mean_occupied_resource
    ));
    out.push_str(&format!(
        "Число попыток поступления: {}\n",
        result.arrival_attempts
    ));
    out.push_str(&format!(
        "Число принятых заявок: {}\n",
        result.accepted_arrivals
    ));
    out.push_str(&format!("Число отказов: {}\n", result.rejected_arrivals));
    out.push_str(&format!(
        "  из-за ёмкости K: {}\n",
        result.rejected_capacity
    ));
    out.push_str(&format!(
        "  из-за лимита приборов N: {}\n",
        result.rejected_server
    ));
    out.push_str(&format!(
        "  из-за лимита ресурса R: {}\n",
        result.rejected_resource
    ));
    out.push_str(&format!(
        "Число завершённых заявок: {}\n",
        result.completed_jobs
    ));
    out.push_str(&format!(
        "Сэмплов job-time в окне: {}\n",
        result.completed_time_samples
    ));
    out.push_str(&format!(
        "Вероятность отказа: {:.6}\n",
        result.loss_probability
    ));
    out.push_str(&format!(
        "Эффективная пропускная способность: {:.6}\n",
        result.throughput
    ));
    out.push_str(&format!(
        "Среднее время обслуживания: {:.6}\n",
        result.mean_service_time
    ));
    out.push_str(&format!(
        "Среднее время ожидания: {:.6}\n",
        result.mean_waiting_time
    ));
    out.push_str(&format!(
        "Среднее время пребывания: {:.6}\n",
        result.mean_sojourn_time
    ));
    out.push_str(&format!(
        "Std времени обслуживания: {:.6}\n",
        result.std_service_time
    ));
    out.push_str(&format!(
        "Std времени ожидания: {:.6}\n",
        result.std_waiting_time
    ));
    out.push_str(&format!(
        "Std времени пребывания: {:.6}\n",
        result.std_sojourn_time
    ));
    out.push_str("Оценка стационарного распределения pi_hat(k):\n");
    for (k, value) in result.pi_hat.iter().enumerate() {
        out.push_str(&format!("  k={:>2}: {:.6}\n", k, value));
    }
    out
}

fn render_suite_summary_text(suite_result: &ExperimentSuiteResult) -> String {
    let mut out = String::new();
    out.push_str(&format!("{}\n", "#".repeat(96)));
    out.push_str(&format!(
        "НАБОР ЭКСПЕРИМЕНТОВ: {}\n",
        suite_result.suite_name
    ));
    out.push_str(&format!("Создан: {}\n", suite_result.created_at));
    out.push_str(&format!("{}\n\n", "#".repeat(96)));

    for (scenario_key, result) in &suite_result.scenario_results {
        out.push_str(&format!("[{}]\n", scenario_key));
        out.push_str(&format!("СЦЕНАРИЙ: {}\n", result.scenario_name));
        out.push_str(&format!("{}\n", result.scenario_description));
        out.push_str(&format!("Число повторов: {}\n", result.replications));
        out.push_str(&format!("{}\n", "-".repeat(96)));
        for metric_name in [
            "mean_num_jobs",
            "mean_occupied_resource",
            "mean_queue_length",
            "queueing_probability",
            "loss_probability",
            "throughput",
            "mean_service_time",
            "mean_waiting_time",
            "mean_sojourn_time",
            "std_service_time",
            "std_waiting_time",
            "std_sojourn_time",
            "completed_time_samples",
            "accepted_arrivals",
            "rejected_arrivals",
            "completed_jobs",
        ] {
            if let Some(m) = result.metric_summaries.get(metric_name) {
                out.push_str(&format!(
                    "{:<28} mean={:>12.6} | std={:>12.6} | CI[{:.2}]=[{:>10.6}, {:>10.6}]\n",
                    metric_name, m.mean, m.std, m.ci_level, m.ci_low, m.ci_high
                ));
            }
        }
        out.push('\n');
    }

    out
}

fn save_single_run_report(
    result: &SimulationRunResult,
    scenario: &ScenarioConfig,
    args: &SingleArgs,
    output_root: impl AsRef<Path>,
    json_path: impl AsRef<Path>,
) -> Result<PathBuf> {
    let output_root = output_root.as_ref();
    let json_path = json_path.as_ref();

    let key_metrics = [
        ("Наблюдаемое время", format!("{:.6}", result.observed_time)),
        (
            "Среднее число заявок",
            format!("{:.6}", result.mean_num_jobs),
        ),
        (
            "Средний занятый ресурс",
            format!("{:.6}", result.mean_occupied_resource),
        ),
        (
            "Попытки поступления",
            format_metric(result.arrival_attempts),
        ),
        ("Принятые заявки", format_metric(result.accepted_arrivals)),
        ("Отказы", format_metric(result.rejected_arrivals)),
        ("Завершённые заявки", format_metric(result.completed_jobs)),
        (
            "Сэмплов job-time в окне",
            format_metric(result.completed_time_samples),
        ),
        (
            "Вероятность отказа",
            format!("{:.6}", result.loss_probability),
        ),
        (
            "Пропускная способность",
            format!("{:.6}", result.throughput),
        ),
        (
            "Среднее время обслуживания",
            format!("{:.6}", result.mean_service_time),
        ),
        (
            "Среднее время ожидания",
            format!("{:.6}", result.mean_waiting_time),
        ),
        (
            "Среднее время пребывания",
            format!("{:.6}", result.mean_sojourn_time),
        ),
        (
            "Std времени обслуживания",
            format!("{:.6}", result.std_service_time),
        ),
        (
            "Std времени ожидания",
            format!("{:.6}", result.std_waiting_time),
        ),
        (
            "Std времени пребывания",
            format!("{:.6}", result.std_sojourn_time),
        ),
    ];

    let mut lines = vec![
        "# Отчёт по одному прогону".to_string(),
        "".to_string(),
        "## Что запускалось".to_string(),
        format!("- Сценарий: **{}**.", scenario.name),
        format!("- Replication index: **{}**.", result.replication_index),
        format!("- Seed: **{}**.", result.seed),
        format!(
            "- Время моделирования: **{}**, warm-up: **{}**.",
            result.total_time, result.warmup_time
        ),
        "".to_string(),
        "## Текстовое описание результата".to_string(),
        "Прогон завершён успешно. Ниже собраны ключевые показатели.".to_string(),
        "".to_string(),
        "## Ключевые метрики".to_string(),
    ];

    for (name, value) in key_metrics {
        lines.push(format!("- {}: **{}**.", name, value));
    }

    lines.extend([
        "".to_string(),
        "## Где лежат артефакты".to_string(),
        format!("- JSON с полным результатом: `{}`.", json_path.display()),
        format!("- Папка прогона: `{}`.", output_root.display()),
        "".to_string(),
        "## Параметры запуска CLI".to_string(),
        format!(
            "- max_time={:?}, warmup_time={:?}, record_state_trace={}, save_event_log={}.",
            args.max_time, args.warmup_time, args.record_state_trace, args.save_event_log
        ),
    ]);

    save_markdown_report(&lines, output_root.join("single_run_report.md"))
}

fn run_python_plots(
    input_path: impl AsRef<Path>,
    output_dir: impl AsRef<Path>,
    metrics: &[String],
    dpi: u32,
) -> Result<()> {
    let script_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("py")
        .join("plots.py");

    let script_arg = script_path.to_string_lossy().to_string();
    let input_arg = input_path.as_ref().to_string_lossy().to_string();
    let output_arg = output_dir.as_ref().to_string_lossy().to_string();
    let dpi_arg = dpi.to_string();

    let metrics_args: Vec<String> = metrics.to_vec();

    let candidate_commands: Vec<(&str, Vec<String>)> = vec![
        ("python3", vec![script_arg.clone()]),
        ("python", vec![script_arg.clone()]),
        ("py", vec!["-3".to_string(), script_arg.clone()]),
    ];

    let mut launch_errors = Vec::new();

    for (program, mut base_args) in candidate_commands {
        base_args.push("--input".to_string());
        base_args.push(input_arg.clone());
        base_args.push("--output-dir".to_string());
        base_args.push(output_arg.clone());
        base_args.push("--dpi".to_string());
        base_args.push(dpi_arg.clone());

        if !metrics_args.is_empty() {
            base_args.push("--metrics".to_string());
            base_args.extend(metrics_args.iter().cloned());
        }

        match Command::new(program).args(&base_args).output() {
            Ok(output) => {
                if output.status.success() {
                    return Ok(());
                }

                launch_errors.push(format!(
                    "{program}: exit_code={:?}, stderr={}",
                    output.status.code(),
                    String::from_utf8_lossy(&output.stderr)
                ));
            }
            Err(e) => {
                launch_errors.push(format!("{program}: {e}"));
            }
        }
    }

    Err(RunError::Validation(format!(
        "Не удалось запустить Python plotting. Пробовали python3/python/py -3.\n{}",
        launch_errors.join("\n")
    )))
}

fn build_single_scenario(args: &SingleArgs) -> Result<ScenarioConfig> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = args.mean_workload;

    let workloads = standard_workload_family_from_values(&values)?;
    let workload = workloads
        .get("exponential")
        .cloned()
        .ok_or_else(|| RunError::Validation("Не найден workload 'exponential'".to_string()))?;

    let base =
        build_base_scenario_from_values(&values, workload, ArrivalProcessConfig::Poisson, "")?;
    let scenario = override_simulation_config(
        &base,
        args.max_time,
        args.warmup_time,
        None,
        args.record_state_trace,
        args.save_event_log,
    );
    scenario.validate()?;
    Ok(scenario)
}

fn build_suite_scenarios(
    args: &SuiteArgs,
) -> Result<std::collections::BTreeMap<String, ScenarioConfig>> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = args.mean_workload;

    let scenarios = match args.scenario_family {
        ScenarioFamily::Base => build_default_experiment_suite(args.mean_workload)?,
        ScenarioFamily::WorkloadSensitivity => {
            build_workload_sensitivity_scenarios_from_values(&values)?
        }
        ScenarioFamily::ArrivalSensitivity => {
            build_arrival_sensitivity_scenarios_from_values(&values)?
        }
        ScenarioFamily::CombinedSensitivity => {
            build_combined_sensitivity_scenarios_from_values(&values)?
        }
    };

    let mut updated = std::collections::BTreeMap::new();
    for (key, scenario) in scenarios {
        let modified = override_simulation_config(
            &scenario,
            args.max_time,
            args.warmup_time,
            args.replications,
            args.record_state_trace,
            args.save_event_log,
        );
        modified.validate()?;
        updated.insert(key, modified);
    }

    Ok(updated)
}

fn build_full_scenarios(
    args: &FullArgs,
) -> Result<std::collections::BTreeMap<String, ScenarioConfig>> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = args.mean_workload;

    let scenarios = match args.scenario_family {
        ScenarioFamily::Base => build_default_experiment_suite(args.mean_workload)?,
        ScenarioFamily::WorkloadSensitivity => {
            build_workload_sensitivity_scenarios_from_values(&values)?
        }
        ScenarioFamily::ArrivalSensitivity => {
            build_arrival_sensitivity_scenarios_from_values(&values)?
        }
        ScenarioFamily::CombinedSensitivity => {
            build_combined_sensitivity_scenarios_from_values(&values)?
        }
    };

    let mut updated = std::collections::BTreeMap::new();
    for (key, scenario) in scenarios {
        let modified = override_simulation_config(
            &scenario,
            args.max_time,
            args.warmup_time,
            args.replications,
            args.record_state_trace,
            args.save_event_log,
        );
        modified.validate()?;
        updated.insert(key, modified);
    }

    Ok(updated)
}

pub fn run_single_mode(args: &SingleArgs) -> Result<PathBuf> {
    let started_at = Instant::now();
    let scenario = build_single_scenario(args)?;

    let sim_started = Instant::now();
    let result = simulate_one_run(scenario.clone(), args.replication_index, args.seed)?;
    let sim_elapsed = sim_started.elapsed();

    let output_root = make_single_run_root(&args.output_root)?;
    let json_path = save_single_run_result(&result, &output_root)?;
    let report_path = save_single_run_report(&result, &scenario, args, &output_root, &json_path)?;
    let txt_summary_path = save_text_report(
        &render_single_run_text(&result, &scenario),
        output_root.join("single_run_summary.txt"),
    )?;

    println!("{}", "=".repeat(80));
    println!(
        "Результат одного прогона сохранён в: {}",
        json_path.display()
    );
    println!(
        "Текстовый summary сохранён в: {}",
        txt_summary_path.display()
    );
    println!("Markdown-отчёт сохранён в: {}", report_path.display());
    println!("Время simulation: {:.2?}", sim_elapsed);
    println!("Общее время run_single_mode: {:.2?}", started_at.elapsed());
    println!("{}", "=".repeat(80));

    Ok(output_root)
}

pub fn run_suite_mode(args: &SuiteArgs) -> Result<PathBuf> {
    let started_at = Instant::now();
    let values = load_default_external_experiment_values()?;
    let keep_full_run_results = args.keep_full_run_results || values.keep_full_run_results;
    println!(
        "Профили запуска: {}",
        profile_summary(&values, args.scenario_family)
    );
    println!(
        "Семейство сценариев: {}",
        scenario_family_summary(&values, args.scenario_family)
    );
    let scenarios = build_suite_scenarios(args)?;
    let sim_started = Instant::now();
    let suite_result = run_experiment_suite(
        &scenarios,
        &args.suite_name,
        args.ci_level,
        keep_full_run_results,
    )?;
    let sim_elapsed = sim_started.elapsed();

    let output_root = make_timestamped_dir_with_slug(
        &args.output_root,
        &output_series_slug(&values, args.scenario_family),
    )?;
    let suite_dir = save_experiment_suite(&suite_result, &output_root)?;
    let suite_text = format!(
        "Профили запуска: {}\nСемейство сценариев: {:?}\n\n{}",
        profile_summary(&values, args.scenario_family),
        args.scenario_family,
        render_suite_summary_text(&suite_result)
    );
    let txt_summary_path = save_text_report(&suite_text, output_root.join("suite_summary.txt"))?;
    let plots_dir = suite_dir.join("plots");
    let plots_started = Instant::now();
    run_python_plots(&suite_dir, &plots_dir, &args.metrics, 200)?;
    let plots_elapsed = plots_started.elapsed();

    println!("{}", "=".repeat(80));
    println!(
        "Результаты серии экспериментов сохранены в: {}",
        suite_dir.display()
    );
    println!(
        "Текстовый summary сохранён в: {}",
        txt_summary_path.display()
    );
    println!("Графики сохранены в: {}", plots_dir.display());
    println!("Время suite simulation: {:.2?}", sim_elapsed);
    println!("Время построения графиков: {:.2?}", plots_elapsed);
    println!("Общее время run_suite_mode: {:.2?}", started_at.elapsed());
    println!("{}", "=".repeat(80));

    Ok(output_root)
}

pub fn run_plots_mode(args: &PlotsArgs) -> Result<PathBuf> {
    let json_path = resolve_suite_result_json(&args.input)?;

    let output_dir = if let Some(out) = &args.output_dir {
        PathBuf::from(out)
    } else {
        json_path.parent().unwrap_or(Path::new(".")).join("plots")
    };

    run_python_plots(&args.input, &output_dir, &args.metrics, args.dpi)?;

    println!("{}", "=".repeat(80));
    println!("Папка с графиками: {}", output_dir.display());

    println!("{}", "=".repeat(80));

    Ok(output_dir)
}

pub fn run_full_mode(args: &FullArgs) -> Result<PathBuf> {
    let started_at = Instant::now();
    let values = load_default_external_experiment_values()?;
    let keep_full_run_results = args.keep_full_run_results || values.keep_full_run_results;
    println!(
        "Профили запуска: {}",
        profile_summary(&values, args.scenario_family)
    );
    println!(
        "Семейство сценариев: {}",
        scenario_family_summary(&values, args.scenario_family)
    );
    let scenarios = build_full_scenarios(args)?;
    let sim_started = Instant::now();
    let suite_result = run_experiment_suite(
        &scenarios,
        &args.suite_name,
        args.ci_level,
        keep_full_run_results,
    )?;
    let sim_elapsed = sim_started.elapsed();

    let suite_dir = make_timestamped_dir_with_slug(
        &args.output_root,
        &output_series_slug(&values, args.scenario_family),
    )?;
    let suite_dir = save_experiment_suite(&suite_result, &suite_dir)?;

    let suite_text = format!(
        "Профили запуска: {}\nСемейство сценариев: {:?}\n\n{}",
        profile_summary(&values, args.scenario_family),
        args.scenario_family,
        render_suite_summary_text(&suite_result)
    );
    let suite_txt_summary_path =
        save_text_report(&suite_text, suite_dir.join("suite_summary.txt"))?;

    let plots_dir = suite_dir.join("plots");
    let plots_started = Instant::now();
    run_python_plots(&suite_dir, &plots_dir, &args.metrics, args.dpi)?;
    let plots_elapsed = plots_started.elapsed();

    println!("{}", "=".repeat(80));
    println!("Полный запуск завершён.");
    println!("Результаты серии: {}", suite_dir.display());
    println!("Графики: {}", plots_dir.display());
    println!(
        "Текстовый summary по серии: {}",
        suite_txt_summary_path.display()
    );
    println!("Время full simulation: {:.2?}", sim_elapsed);
    println!("Время построения графиков: {:.2?}", plots_elapsed);
    println!("Общее время run_full_mode: {:.2?}", started_at.elapsed());
    println!("{}", "=".repeat(80));

    Ok(suite_dir)
}

pub fn cli_entry() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Single(args) => {
            run_single_mode(&args)?;
        }
        Commands::Suite(args) => {
            run_suite_mode(&args)?;
        }
        Commands::Plots(args) => {
            run_plots_mode(&args)?;
        }
        Commands::Full(args) => {
            run_full_mode(&args)?;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn override_simulation_config_works() {
        let mut values = load_default_external_experiment_values().unwrap();
        values.mean_workload = 1.0;
        let workloads = standard_workload_family_from_values(&values).unwrap();
        let workload = workloads.get("exponential").unwrap().clone();
        let base =
            build_base_scenario_from_values(&values, workload, ArrivalProcessConfig::Poisson, "")
                .unwrap();

        let updated =
            override_simulation_config(&base, Some(123.0), Some(12.0), Some(7), true, true);

        assert_eq!(updated.simulation.max_time, 123.0);
        assert_eq!(updated.simulation.warmup_time, 12.0);
        assert_eq!(updated.simulation.replications, 7);
        assert!(updated.simulation.record_state_trace);
        assert!(updated.simulation.save_event_log);
    }

    #[test]
    fn timestamp_is_nonempty() {
        assert!(!timestamp().is_empty());
    }
}
