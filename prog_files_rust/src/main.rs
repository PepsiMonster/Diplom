mod experiments;
mod model;
mod params;
mod run;
mod simulation;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    run::cli_entry()?;
    Ok(())
}
