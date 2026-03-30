use std::path::Path;

use plotters::prelude::*;

use crate::experiments::ScenarioExperimentResult;

fn y_bounds_with_margin(values: &[f64]) -> (f64, f64) {
    let min = values.iter().copied().fold(f64::INFINITY, f64::min);
    let max = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let span = (max - min).abs();
    let margin = (span * 0.15).max(1e-6);
    (min - margin, max + margin)
}

pub fn plot_metric_bar(
    scenarios: &[ScenarioExperimentResult],
    metric_name: &str,
    output: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let values = scenarios
        .iter()
        .map(|s| match metric_name {
            "throughput" => s.throughput.mean,
            "loss_probability" => s.loss_probability.mean,
            "mean_num_jobs" => s.mean_num_jobs.mean,
            "mean_occupied_resource" => s.mean_occupied_resource.mean,
            _ => s.throughput.mean,
        })
        .collect::<Vec<_>>();

    let labels = scenarios.iter().map(|s| s.scenario_name.clone()).collect::<Vec<_>>();
    let (y_min, y_max) = y_bounds_with_margin(&values);

    let root = BitMapBackend::new(output, (1200, 700)).into_drawing_area();
    root.fill(&WHITE)?;

    let mut chart = ChartBuilder::on(&root)
        .caption(format!("{metric_name} by scenario"), ("sans-serif", 32))
        .margin(20)
        .x_label_area_size(60)
        .y_label_area_size(80)
        .build_cartesian_2d(0..values.len(), y_min..y_max)?;

    chart
        .configure_mesh()
        .x_labels(values.len())
        .x_label_formatter(&|x| labels[*x].clone())
        .y_label_formatter(&|y| format!("{:.4}", y))
        .light_line_style(RGBColor(220, 220, 220))
        .draw()?;

    for (i, value) in values.iter().enumerate() {
        chart.draw_series(std::iter::once(Rectangle::new(
            [(i, 0.0_f64.max(y_min)), (i + 1, *value)],
            BLUE.mix(0.6).filled(),
        )))?;

        chart.draw_series(std::iter::once(Text::new(
            format!("{value:.4}"),
            (i, *value),
            ("sans-serif", 18).into_font().color(&BLACK),
        )))?;
    }

    root.present()?;
    Ok(())
}

pub fn plot_stationary_distribution(
    pi_hat: &[f64],
    output: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let root = BitMapBackend::new(output, (1200, 700)).into_drawing_area();
    root.fill(&WHITE)?;

    let mut chart = ChartBuilder::on(&root)
        .caption("stationary_distribution", ("sans-serif", 32))
        .margin(20)
        .x_label_area_size(60)
        .y_label_area_size(80)
        .build_cartesian_2d(0..pi_hat.len(), 0.0..1.0)?;

    chart
        .configure_mesh()
        .x_desc("k")
        .y_desc("pi_hat(k)")
        .y_label_formatter(&|y| format!("{:.3}", y))
        .light_line_style(RGBColor(220, 220, 220))
        .draw()?;

    chart.draw_series(LineSeries::new(
        pi_hat.iter().enumerate().map(|(k, v)| (k, *v)),
        &RED,
    ))?;

    chart.draw_series(pi_hat.iter().enumerate().map(|(k, v)| Circle::new((k, *v), 4, RED.filled())))?;

    root.present()?;
    Ok(())
}
