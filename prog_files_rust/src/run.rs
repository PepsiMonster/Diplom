use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::collections::BTreeMap;

use chrono::Local;
use clap::{Args, Parser, Subcommand, ValueEnum};
// use serde_json::json;
use thiserror::Error;

use crate::experiments::{
    build_default_experiment_suite, run_experiment_suite, save_experiment_suite,
    ExperimentSuiteResult, ExperimentsError,
};
use crate::params::{
    build_base_scenario_from_values, build_sensitivity_scenarios_from_values,
    load_default_external_experiment_values, standard_workload_family_from_values, ExternalExperimentValues,
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

#[derive(Debug, Clone, serde::Deserialize)]
struct PlotSuiteData {
    suite_name: String,
    created_at: String,
    scenario_results: BTreeMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ScenarioFamily {
    Default,
    Sensitivity,
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
    #[arg(long, value_enum, default_value_t = ScenarioFamily::Default)]
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
    #[arg(long, value_enum, default_value_t = ScenarioFamily::Default)]
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

fn load_suite_data(input_path: impl AsRef<Path>) -> Result<PlotSuiteData> {
    let json_path = resolve_suite_result_json(input_path)?;
    let text = fs::read_to_string(json_path)?;
    Ok(serde_json::from_str(&text)?)
}

fn collect_png_paths(output_dir: impl AsRef<Path>) -> Result<Vec<PathBuf>> {
    let mut pngs = Vec::new();
    for entry in fs::read_dir(output_dir)? {
        let entry = entry?;
        let path = entry.path();
        let is_png = path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.eq_ignore_ascii_case("png"))
            .unwrap_or(false);
        if is_png {
            pngs.push(path);
        }
    }
    pngs.sort();
    Ok(pngs)
}

fn short_profile(value: &str) -> &str {
    match value {
        "state_dependent" => "sd",
        "constant" => "const",
        other => other,
    }
}

fn architecture_slug(values: &ExternalExperimentValues) -> &'static str {
    match values.system_architecture {
        crate::params::SystemArchitecture::Loss => "loss",
        crate::params::SystemArchitecture::Buffer => "buffer",
    }
}

fn profile_slug(values: &ExternalExperimentValues) -> String {
    format!(
        "arch-{}__arrprof-{}__srvprof-{}__work-{}",
        architecture_slug(values),
        short_profile(&values.arrival_rate_profile),
        short_profile(&values.service_speed_profile),
        values.workload_family_profile
    )
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
        "Вероятность отказа: {:.6}\n",
        result.loss_probability
    ));
    out.push_str(&format!(
        "Эффективная пропускная способность: {:.6}\n",
        result.throughput
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
            "loss_probability",
            "throughput",
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
            "Вероятность отказа",
            format!("{:.6}", result.loss_probability),
        ),
        (
            "Пропускная способность",
            format!("{:.6}", result.throughput),
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

fn save_suite_report(
    suite_result: &ExperimentSuiteResult,
    output_root: impl AsRef<Path>,
    suite_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let output_root = output_root.as_ref();
    let suite_dir = suite_dir.as_ref();

    let mut lines = vec![
        "# Отчёт по серии экспериментов".to_string(),
        "".to_string(),
        "## Что произошло".to_string(),
        "Серия прогонов выполнена. В этом отчёте собраны агрегированные итоги по каждому сценарию."
            .to_string(),
        "".to_string(),
        "## Общая информация".to_string(),
        format!("- Имя серии: **{}**.", suite_result.suite_name),
        format!("- Время формирования: **{}**.", suite_result.created_at),
        format!(
            "- Число сценариев: **{}**.",
            suite_result.scenario_results.len()
        ),
        "".to_string(),
        "## Итоги по сценариям".to_string(),
    ];

    for (scenario_key, result) in &suite_result.scenario_results {
        lines.push(format!("### {}", scenario_key));
        lines.push(format!("- Описание: {}.", result.scenario_description));
        lines.push(format!("- Replications: **{}**.", result.replications));

        for metric_name in [
            "throughput",
            "loss_probability",
            "mean_num_jobs",
            "mean_occupied_resource",
        ] {
            if let Some(summary) = result.metric_summaries.get(metric_name) {
                lines.push(format!(
                    "- {}: mean={:.6}, 95% CI=[{:.6}, {:.6}].",
                    metric_name, summary.mean, summary.ci_low, summary.ci_high
                ));
            }
        }

        lines.push(String::new());
    }

    lines.extend([
        "## Где лежат артефакты".to_string(),
        format!("- Папка серии: `{}`.", suite_dir.display()),
        format!(
            "- Таблицы/JSON: `{}`, `{}`, `{}`, `{}`.",
            suite_dir.join("aggregated_summary.csv").display(),
            suite_dir.join("all_runs.csv").display(),
            suite_dir.join("metric_summaries_long.csv").display(),
            suite_dir.join("suite_result.json").display()
        ),
    ]);

    save_markdown_report(&lines, output_root.join("suite_report.md"))
}

fn save_plots_report(
    suite_data: &PlotSuiteData,
    input_path: impl AsRef<Path>,
    output_dir: impl AsRef<Path>,
    created_paths: &[PathBuf],
) -> Result<PathBuf> {
    let input_path = input_path.as_ref();
    let output_dir = output_dir.as_ref();

    let mut lines = vec![
        "# Отчёт по построению графиков".to_string(),
        "".to_string(),
        "## Что произошло".to_string(),
        "Графики успешно построены на основании сохранённых результатов серии.".to_string(),
        "".to_string(),
        "## Источник данных".to_string(),
        format!("- Вход: `{}`.", input_path.display()),
        format!("- Набор: **{}**.", suite_data.suite_name),
        format!("- Создан: **{}**.", suite_data.created_at),
        format!("- Сценариев: **{}**.", suite_data.scenario_results.len()),
        "".to_string(),
        "## Результат".to_string(),
        format!("- Папка графиков: `{}`.", output_dir.display()),
        format!("- Построено PNG-файлов: **{}**.", created_paths.len()),
    ];

    if !created_paths.is_empty() {
        lines.push(String::new());
        lines.push("## Встроенные графики".to_string());

        let report_dir = output_dir.parent().unwrap_or(output_dir);

        for image_path in created_paths {
            let filename = image_path
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("plot.png");

            let relative_path = image_path
                .strip_prefix(report_dir)
                .unwrap_or(image_path)
                .to_string_lossy()
                .replace('\\', "/");

            lines.push(format!("### {}", filename));
            lines.push(format!("![{}]({})", filename, relative_path));
            lines.push(String::new());
        }
    }

    let parent = output_dir.parent().unwrap_or(output_dir);
    save_markdown_report(&lines, parent.join("plots_report.md"))
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

    let base = build_base_scenario_from_values(&values, workload, "")?;
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
        ScenarioFamily::Default => build_default_experiment_suite(args.mean_workload)?,
        ScenarioFamily::Sensitivity => build_sensitivity_scenarios_from_values(&values)?,
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
        ScenarioFamily::Default => build_default_experiment_suite(args.mean_workload)?,
        ScenarioFamily::Sensitivity => build_sensitivity_scenarios_from_values(&values)?,
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
    let scenario = build_single_scenario(args)?;

    let result = simulate_one_run(scenario.clone(), args.replication_index, args.seed)?;

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
    println!("{}", "=".repeat(80));

    Ok(output_root)
}

pub fn run_suite_mode(args: &SuiteArgs) -> Result<PathBuf> {
    let values = load_default_external_experiment_values()?;
    let keep_full_run_results = args.keep_full_run_results || values.keep_full_run_results;
    let scenarios = build_suite_scenarios(args)?;
    let suite_result = run_experiment_suite(
        &scenarios,
        &args.suite_name,
        args.ci_level,
        keep_full_run_results,
    )?;

    let output_root = make_timestamped_dir_with_slug(&args.output_root, &profile_slug(&values))?;
    let suite_dir = save_experiment_suite(&suite_result, &output_root)?;
    let report_path = save_suite_report(&suite_result, &output_root, &suite_dir)?;
    let txt_summary_path = save_text_report(
        &render_suite_summary_text(&suite_result),
        output_root.join("suite_summary.txt"),
    )?;
    let suite_data = load_suite_data(&suite_dir)?;
    let plots_dir = suite_dir.join("plots");
    run_python_plots(&suite_dir, &plots_dir, &args.metrics, 200)?;
    let created = collect_png_paths(&plots_dir)?;
    let plots_report_path = save_plots_report(&suite_data, &suite_dir, &plots_dir, &created)?;

    println!("{}", "=".repeat(80));
    println!(
        "Результаты серии экспериментов сохранены в: {}",
        suite_dir.display()
    );
    println!(
        "Текстовый summary сохранён в: {}",
        txt_summary_path.display()
    );
    println!("Markdown-отчёт сохранён в: {}", report_path.display());
    println!("Графики сохранены в: {}", plots_dir.display());
    println!(
        "Markdown-отчёт по графикам сохранён в: {}",
        plots_report_path.display()
    );
    println!("{}", "=".repeat(80));

    Ok(output_root)
}

pub fn run_plots_mode(args: &PlotsArgs) -> Result<PathBuf> {
    let suite_data = load_suite_data(&args.input)?;
    let json_path = resolve_suite_result_json(&args.input)?;

    let output_dir = if let Some(out) = &args.output_dir {
        PathBuf::from(out)
    } else {
        json_path.parent().unwrap_or(Path::new(".")).join("plots")
    };

    run_python_plots(&args.input, &output_dir, &args.metrics, args.dpi)?;
    let created = collect_png_paths(&output_dir)?;

    println!("{}", "=".repeat(80));
    println!("Папка с графиками: {}", output_dir.display());

    let report_path = save_plots_report(&suite_data, &args.input, &output_dir, &created)?;
    println!("Markdown-отчёт сохранён в: {}", report_path.display());
    println!("{}", "=".repeat(80));

    Ok(output_dir)
}

pub fn run_full_mode(args: &FullArgs) -> Result<PathBuf> {
    let values = load_default_external_experiment_values()?;
    let keep_full_run_results = args.keep_full_run_results || values.keep_full_run_results;
    let scenarios = build_full_scenarios(args)?;
    let suite_result = run_experiment_suite(
        &scenarios,
        &args.suite_name,
        args.ci_level,
        keep_full_run_results,
    )?;

    let suite_dir = make_timestamped_dir_with_slug(&args.output_root, &profile_slug(&values))?;
    let suite_dir = save_experiment_suite(&suite_result, &suite_dir)?;

    let suite_report_path = save_suite_report(&suite_result, &suite_dir, &suite_dir)?;
    let suite_txt_summary_path = save_text_report(
        &render_suite_summary_text(&suite_result),
        suite_dir.join("suite_summary.txt"),
    )?;

    let suite_data = load_suite_data(&suite_dir)?;
    let plots_dir = suite_dir.join("plots");
    run_python_plots(&suite_dir, &plots_dir, &args.metrics, args.dpi)?;
    let created = collect_png_paths(&plots_dir)?;
    let plots_report_path = save_plots_report(&suite_data, &suite_dir, &plots_dir, &created)?;

    println!("{}", "=".repeat(80));
    println!("Полный запуск завершён.");
    println!("Результаты серии: {}", suite_dir.display());
    println!("Графики: {}", plots_dir.display());
    println!(
        "Текстовый summary по серии: {}",
        suite_txt_summary_path.display()
    );
    println!("Markdown-отчёт по серии: {}", suite_report_path.display());
    println!(
        "Markdown-отчёт по графикам: {}",
        plots_report_path.display()
    );
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
        let base = build_base_scenario_from_values(&values, workload, "").unwrap();

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
