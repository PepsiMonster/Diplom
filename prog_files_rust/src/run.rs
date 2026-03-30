use std::fs;
use std::path::{Path, PathBuf};

use clap::{Parser, Subcommand};

use crate::experiments::{run_experiment_suite, ExperimentSuiteResult};
use crate::params::build_base_scenario;
use crate::plots::{plot_metric_bar, plot_stationary_distribution};
use crate::simulation::simulate_one_run;

#[derive(Debug, Parser)]
#[command(name = "prog_files_rust")]
#[command(about = "Rust CLI для имитационной модели", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
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
        #[arg(long, default_value = "results_rust")]
        output_dir: PathBuf,
    },
    Suite {
        #[arg(long, default_value_t = 1.0)]
        mean_workload: f64,
        #[arg(long, default_value_t = 10)]
        replications: usize,
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
        #[arg(long, default_value_t = 1.0)]
        mean_workload: f64,
        #[arg(long, default_value_t = 10)]
        replications: usize,
        #[arg(long, default_value = "results_rust")]
        output_dir: PathBuf,
    },
}

fn save_suite_json(result: &ExperimentSuiteResult, output_dir: &Path) -> Result<PathBuf, Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;
    let path = output_dir.join("suite_result.json");
    let body = serde_json::to_string_pretty(result)?;
    fs::write(&path, body)?;
    Ok(path)
}

fn save_single_json(result: &crate::simulation::SimulationRunResult, output_dir: &Path) -> Result<PathBuf, Box<dyn std::error::Error>> {
    fs::create_dir_all(output_dir)?;
    let path = output_dir.join("single_run_result.json");
    fs::write(&path, serde_json::to_string_pretty(result)?)?;
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
    Ok(())
}

pub fn cli_entry() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Single {
            mean_workload,
            replication_index,
            seed,
            output_dir,
        } => {
            let scenario = build_base_scenario(mean_workload);
            scenario.validate().map_err(|e| format!("Scenario validation error: {e}"))?;
            let result = simulate_one_run(&scenario, replication_index, seed);
            let path = save_single_json(&result, &output_dir)?;
            println!("single result saved: {}", path.display());
        }
        Commands::Suite {
            mean_workload,
            replications,
            output_dir,
        } => {
            let mut base = build_base_scenario(mean_workload);
            base.simulation.replications = replications;
            base.validate().map_err(|e| format!("Scenario validation error: {e}"))?;
            let suite = run_experiment_suite(&[base], "suite_rust");
            let path = save_suite_json(&suite, &output_dir)?;
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
            mean_workload,
            replications,
            output_dir,
        } => {
            let mut base = build_base_scenario(mean_workload);
            base.simulation.replications = replications;
            let suite = run_experiment_suite(&[base], "full_rust");
            let json_path = save_suite_json(&suite, &output_dir)?;
            let plots_dir = output_dir.join("plots");
            generate_plots_from_suite(&suite, &plots_dir)?;
            println!("full done: {}, {}", json_path.display(), plots_dir.display());
        }
    }

    Ok(())
}
