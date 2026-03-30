mod params;
mod model;
mod simulation;
mod experiments;
mod plots;
mod run;

fn main() {
    if let Err(e) = run::cli_entry() {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}
