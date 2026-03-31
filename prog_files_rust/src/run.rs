use std::fs;
use std::path::{Path, PathBuf};

use clap::{Parser, Subcommand};

use crate::experiments::{aggregated_rows, all_run_rows, run_experiment_suite, ExperimentSuiteResult};
use crate::params::{build_base_scenario, build_sensitivity_scenarios};
use crate::plots::{plot_metric_bar, plot_stationary_distribution};
use crate::simulation::simulate_one_run;

#[derive(Debug, Parser)]
#[command(name = "prog_files_rust")]
#[command(about = "Rust CLI для имитационной модели", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Debug, Subcommand)]
pub enum Commands {
    Single {
        #[arg(long, default_value_t = 1.0)]
        mean_workload: f64,
        #[arg(long, default_value_t = 0)]
        replication_index: usize,
        #[arg(long)]
        seed: Option<u64>,
        #[arg(long, default_value_t = 100_000.0)]
        max_time: f64,
        #[arg(long, default_value_t = 20_000.0)]
        warmup_time: f64,
        #[arg(long, default_value = "results_rust")]
        output_dir: PathBuf,
    },
    Suite {
        #[arg(long, default_value = "suite_rust")]
        suite_name: String,
        #[arg(long, default_value = "sensitivity")]
        scenario_family: String,
        #[arg(long, default_value_t = 1.0)]
        mean_workload: f64,
        #[arg(long, default_value_t = 10)]
        replications: usize,
        #[arg(long, default_value_t = 100_000.0)]
        max_time: f64,
        #[arg(long, default_value_t = 20_000.0)]
        warmup_time: f64,
        #[arg(long, default_value = "results_rust")]
        output_dir: PathBuf,
    },
    Plots {
        #[arg(long, default_value = "results_rust/suite_result.json")]
        suite_json: PathBuf,
        #[arg(long, default_value = "results_rust/plots")]
        output_dir: PathBuf,
    },
    Full {
        #[arg(long, default_value = "full_rust")]
        suite_name: String,
        #[arg(long, default_value = "sensitivity")]
        scenario_family: String,
        #[arg(long, default_value_t = 1.0)]
        mean_workload: f64,
        #[arg(long, default_value_t = 10)]
        replications: usize,
        #[arg(long, default_value_t = 100_000.0)]
        max_time: f64,
        #[arg(long, default_value_t = 20_000.0)]
        warmup_time: f64,
        #[arg(long, default_value = "results_rust")]
        output_dir: PathBuf,
    },
}

fn write_csv_rows(path: &Path, rows: &[Vec<(String, String)>]) -> Result<(), Box<dyn std::error::Error>> {
    let mut writer = csv::Writer::from_path(path)?;
    if rows.is_empty() {
        writer.flush()?;
        return Ok(());
    }
    let headers = rows[0].iter().map(|(k, _)| k.as_str()).collect::<Vec<_>>();
    writer.write_record(headers)?;

    for row in rows {
        let values = row.iter().map(|(_, v)| v.as_str()).collect::<Vec<_>>();
        writer.write_record(values)?;
    }
    writer.flush()?;
    Ok(())
}

fn save_suite_json(result: &ExperimentSuiteResult, output_dir: &Path) -> Result<PathBuf, Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;
    let path = output_dir.join("suite_result.json");
    let body = serde_json::to_string_pretty(result)?;
    fs::write(&path, body)?;
    Ok(path)
}

fn save_suite_csv_and_txt(result: &ExperimentSuiteResult, output_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;

    let agg = aggregated_rows(result);
    let runs = all_run_rows(result);

    write_csv_rows(&output_dir.join("aggregated_summary.csv"), &agg)?;
    write_csv_rows(&output_dir.join("all_runs.csv"), &runs)?;

    let mut txt = String::new();
    txt.push_str("Краткий отчёт по серии экспериментов\n");
    txt.push_str("==================================\n\n");
    txt.push_str(&format!("suite_name: {}\n", result.suite_name));
    txt.push_str(&format!("created_at: {}\n\n", result.created_at));
    for s in &result.scenarios {
        txt.push_str(&format!(
            "- {}: throughput={:.6}, loss_probability={:.6}, mean_num_jobs={:.6}\n",
            s.scenario_name, s.throughput.mean, s.loss_probability.mean, s.mean_num_jobs.mean
        ));
    }
    fs::write(output_dir.join("suite_report.txt"), txt)?;

    let mut md = String::new();
    md.push_str("# Suite report\n\n");
    md.push_str(&format!("- suite_name: **{}**\n", result.suite_name));
    md.push_str(&format!("- created_at: **{}**\n\n", result.created_at));
    md.push_str("## Scenarios\n");
    for s in &result.scenarios {
        md.push_str(&format!(
            "- **{}**: throughput `{:.6}`, loss_probability `{:.6}`, mean_num_jobs `{:.6}`\n",
            s.scenario_name, s.throughput.mean, s.loss_probability.mean, s.mean_num_jobs.mean
        ));
    }
    fs::write(output_dir.join("suite_report.md"), md)?;

    Ok(())
}

fn save_single_json(result: &crate::simulation::SimulationRunResult, output_dir: &Path) -> Result<PathBuf, Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;
    let path = output_dir.join("single_run_result.json");
    fs::write(&path, serde_json::to_string_pretty(result)?)?;

    let md = format!(
        "# Single run\n\n- scenario: **{}**\n- replication: **{}**\n- throughput: `{:.6}`\n- loss_probability: `{:.6}`\n- mean_num_jobs: `{:.6}`\n",
        result.scenario_name, result.replication_index, result.throughput, result.loss_probability, result.mean_num_jobs
    );
    fs::write(output_dir.join("single_run_report.md"), md)?;

    Ok(path)
}

fn generate_plots_from_suite(result: &ExperimentSuiteResult, output_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;
    plot_metric_bar(&result.scenarios, "throughput", &output_dir.join("metric_throughput.png"))?;
    plot_metric_bar(&result.scenarios, "loss_probability", &output_dir.join("metric_loss_probability.png"))?;
    plot_metric_bar(&result.scenarios, "mean_num_jobs", &output_dir.join("metric_mean_num_jobs.png"))?;

    if let Some(first) = result.scenarios.first().and_then(|s| s.runs.first()) {
        plot_stationary_distribution(&first.pi_hat, &output_dir.join("stationary_distribution.png"))?;
    }

    fs::write(
        output_dir.join("plots_report.md"),
        "# Plots report\n\nГрафики построены успешно.\n",
    )?;

    Ok(())
}

pub fn cli_entry() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let command = cli.command.unwrap_or(Commands::Full {
        suite_name: "full_rust".to_string(),
        scenario_family: "sensitivity".to_string(),
        mean_workload: 1.0,
        replications: 10,
        max_time: 100_000.0,
        warmup_time: 20_000.0,
        output_dir: PathBuf::from("results_rust"),
    });

    match command {
        Commands::Single {
            mean_workload,
            replication_index,
            seed,
            max_time,
            warmup_time,
            output_dir,
        } => {
            let mut scenario = build_base_scenario(mean_workload);
            scenario.simulation.max_time = max_time;
            scenario.simulation.warmup_time = warmup_time;
            scenario.validate().map_err(|e| format!("Scenario validation error: {e}"))?;
            let result = simulate_one_run(&scenario, replication_index, seed);
            let path = save_single_json(&result, &output_dir)?;
            println!("single result saved: {}", path.display());
        }
        Commands::Suite {
            suite_name,
            scenario_family,
            mean_workload,
            replications,
            max_time,
            warmup_time,
            output_dir,
        } => {
            let mut scenarios = if scenario_family == "default" {
                vec![build_base_scenario(mean_workload)]
            } else {
                build_sensitivity_scenarios(mean_workload)
            };
            for s in &mut scenarios {
                s.simulation.replications = replications;
                s.simulation.max_time = max_time;
                s.simulation.warmup_time = warmup_time;
                s.validate().map_err(|e| format!("Scenario validation error: {e}"))?;
            }
            let suite = run_experiment_suite(&scenarios, &suite_name);
            let path = save_suite_json(&suite, &output_dir)?;
            save_suite_csv_and_txt(&suite, &output_dir)?;
            println!("suite result saved: {}", path.display());
        }
        Commands::Plots {
            suite_json,
            output_dir,
        } => {
            let data = fs::read_to_string(&suite_json)?;
            let suite: ExperimentSuiteResult = serde_json::from_str(&data)?;
            generate_plots_from_suite(&suite, &output_dir)?;
            println!("plots saved to: {}", output_dir.display());
        }
        Commands::Full {
            suite_name,
            scenario_family,
            mean_workload,
            replications,
            max_time,
            warmup_time,
            output_dir,
        } => {
            let mut scenarios = if scenario_family == "default" {
                vec![build_base_scenario(mean_workload)]
            } else {
                build_sensitivity_scenarios(mean_workload)
            };
            for s in &mut scenarios {
                s.simulation.replications = replications;
                s.simulation.max_time = max_time;
                s.simulation.warmup_time = warmup_time;
                s.validate().map_err(|e| format!("Scenario validation error: {e}"))?;
            }
            let suite = run_experiment_suite(&scenarios, &suite_name);
            let json_path = save_suite_json(&suite, &output_dir)?;
            save_suite_csv_and_txt(&suite, &output_dir)?;
            let plots_dir = output_dir.join("plots");
            generate_plots_from_suite(&suite, &plots_dir)?;
            println!("full done: {}, {}", json_path.display(), plots_dir.display());
        }
    }

    Ok(())
}
