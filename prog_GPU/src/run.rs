use crate::cli::{
    parse_cli, BackendKind, Commands, CommonArgs, FullArgs, ListScenariosArgs, SuiteArgs,
    ValidateConfigArgs,
};
use crate::experiments::{
    build_experiment_plan, list_scenario_descriptions, render_suite_summary_text,
    run_experiment_suite, ExperimentsError,
};
use crate::output::{save_suite_result, OutputArtifacts, OutputError, SaveOptions};
use crate::params::{ExperimentConfig, ParamsError};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RunError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),

    #[error(transparent)]
    Experiments(#[from] ExperimentsError),

    #[error(transparent)]
    Output(#[from] OutputError),
}

type Result<T> = std::result::Result<T, RunError>;

pub fn entry() -> Result<()> {
    let cli = parse_cli();

    match cli.command {
        Commands::ValidateConfig(args) => handle_validate_config(args),
        Commands::ListScenarios(args) => handle_list_scenarios(args),
        Commands::Suite(args) => handle_suite(args),
        Commands::Full(args) => handle_full(args),
    }
}

fn handle_validate_config(args: ValidateConfigArgs) -> Result<()> {
    let config = ExperimentConfig::load(&args.input)?;
    println!("{}", config.summary_string()?);
    Ok(())
}

fn handle_list_scenarios(args: ListScenariosArgs) -> Result<()> {
    let config = load_effective_config(&args.common)?;
    let descriptions = list_scenario_descriptions(&config, args.common.scenario_family, None)?;

    println!("Сценариев: {}", descriptions.len());
    for (idx, line) in descriptions.iter().enumerate() {
        println!("[{:>3}] {}", idx + 1, line);
    }

    Ok(())
}

fn handle_suite(args: SuiteArgs) -> Result<()> {
    let save_options = SaveOptions::default();
    run_suite_like(
        &args.common,
        args.backend,
        args.ci_level,
        &save_options,
        false,
    )
}

fn handle_full(args: FullArgs) -> Result<()> {
    let save_options = SaveOptions {
        save_run_summaries: args.save_run_summaries,
        save_metric_tables: args.save_metric_tables,
        save_text_summary: true,
    };

    run_suite_like(
        &args.common,
        args.backend,
        args.ci_level,
        &save_options,
        true,
    )
}

fn run_suite_like(
    common: &CommonArgs,
    backend: BackendKind,
    ci_level: f64,
    save_options: &SaveOptions,
    is_full_mode: bool,
) -> Result<()> {
    let config = load_effective_config(common)?;

    println!("Загружена конфигурация:");
    println!("{}", config.summary_string()?);
    println!();

    let plan = build_experiment_plan(&config, common.scenario_family, None)?;
    println!("{}", plan.summary_string());
    println!("{}", plan.grid.summary_string());
    println!("Backend: {:?}", backend);
    println!("CI level: {}", ci_level);
    println!("Output root: {}", common.output_root.display());
    println!();

    let suite_result = run_experiment_suite(&config, common.scenario_family, backend, None, ci_level)?;

    println!("{}", render_suite_summary_text(&suite_result, None));

    let artifacts = save_suite_result(&suite_result, &common.output_root, save_options)?;
    print_artifacts(&artifacts);

    if is_full_mode {
        println!("Full pipeline завершён успешно.");
    } else {
        println!("Suite run завершён успешно.");
    }

    Ok(())
}

fn load_effective_config(common: &CommonArgs) -> Result<ExperimentConfig> {
    let config = ExperimentConfig::load(&common.input)?;
    let effective = config.with_overrides(
        common.suite_name.clone(),
        common.replications,
        common.max_time,
        common.warmup_time,
    )?;
    Ok(effective)
}

fn print_artifacts(artifacts: &OutputArtifacts) {
    println!("Сохранённые артефакты:");
    println!("  output_dir: {}", artifacts.output_dir.display());
    println!("  suite_result.json: {}", artifacts.suite_result_json.display());
    println!(
        "  aggregated_summary.csv: {}",
        artifacts.aggregated_summary_csv.display()
    );

    if let Some(path) = &artifacts.suite_summary_txt {
        println!("  suite_summary.txt: {}", path.display());
    }
    if let Some(path) = &artifacts.metric_summaries_csv {
        println!("  metric_summaries.csv: {}", path.display());
    }
    if let Some(path) = &artifacts.run_summaries_csv {
        println!("  run_summaries.csv: {}", path.display());
    }
}