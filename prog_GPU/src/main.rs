mod backend;
mod cli;
mod experiments;
mod output;
mod params;
mod run;
mod scenario_grid;
mod stats;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    run::entry()?;
    Ok(())
}