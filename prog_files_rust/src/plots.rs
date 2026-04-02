use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use plotters::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

use crate::experiments::MetricSummary;

#[derive(Debug, Error)]
pub enum PlotsError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

type Result<T> = std::result::Result<T, PlotsError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlotScenarioData {
    pub scenario_name: String,
    pub scenario_description: String,
    pub replications: usize,
    pub metric_summaries: BTreeMap<String, MetricSummary>,
    pub run_summaries: Vec<BTreeMap<String, Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlotSuiteData {
    pub suite_name: String,
    pub created_at: String,
    pub scenario_results: BTreeMap<String, PlotScenarioData>,
}

impl PlotSuiteData {
    pub fn scenario_keys(&self) -> Vec<String> {
        self.scenario_results.keys().cloned().collect()
    }
}

fn read_json(filepath: impl AsRef<Path>) -> Result<Value> {
    let path = filepath.as_ref();
    let text = fs::read_to_string(path)?;
    Ok(serde_json::from_str(&text)?)
}

pub fn load_suite_data_from_json(filepath: impl AsRef<Path>) -> Result<PlotSuiteData> {
    let payload = read_json(filepath)?;
    Ok(serde_json::from_value(payload)?)
}

pub fn resolve_suite_result_json(input_path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = input_path.as_ref();

    if path.is_dir() {
        let candidate = path.join("suite_result.json");
        if !candidate.exists() {
            return Err(PlotsError::Validation(format!(
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

        let is_suite_name = path
            .file_name()
            .and_then(|name| name.to_str())
            .map(|s| s.eq_ignore_ascii_case("suite_result.json"))
            .unwrap_or(false);

        if !is_json && !is_suite_name {
            return Err(PlotsError::Validation(format!(
                "Ожидался JSON-файл результата или директория результата, получено: {}",
                path.display()
            )));
        }

        return Ok(path.to_path_buf());
    }

    Err(PlotsError::Validation(format!(
        "Путь не найден: {}",
        path.display()
    )))
}

pub fn load_suite_data(input_path: impl AsRef<Path>) -> Result<PlotSuiteData> {
    let json_path = resolve_suite_result_json(input_path)?;
    load_suite_data_from_json(json_path)
}

fn metric_summary<'a>(
    suite_data: &'a PlotSuiteData,
    scenario_key: &str,
    metric_name: &str,
) -> Result<&'a MetricSummary> {
    let scenario = suite_data
        .scenario_results
        .get(scenario_key)
        .ok_or_else(|| PlotsError::Validation(format!("Сценарий '{scenario_key}' отсутствует")))?;

    scenario.metric_summaries.get(metric_name).ok_or_else(|| {
        PlotsError::Validation(format!(
            "Метрика '{metric_name}' отсутствует в сценарии '{scenario_key}'"
        ))
    })
}

pub fn available_metric_names(suite_data: &PlotSuiteData) -> Vec<String> {
    let mut names: BTreeSet<String> = BTreeSet::new();
    for payload in suite_data.scenario_results.values() {
        names.extend(payload.metric_summaries.keys().cloned());
    }
    names.into_iter().collect()
}

pub fn extract_metric_vectors(
    suite_data: &PlotSuiteData,
    metric_name: &str,
) -> Result<(Vec<String>, Vec<f64>, Vec<f64>, Vec<f64>)> {
    let mut labels = Vec::new();
    let mut means = Vec::new();
    let mut ci_lows = Vec::new();
    let mut ci_highs = Vec::new();

    for scenario_key in suite_data.scenario_keys() {
        let summary = metric_summary(suite_data, &scenario_key, metric_name)?;
        labels.push(scenario_key);
        means.push(summary.mean);
        ci_lows.push(summary.ci_low);
        ci_highs.push(summary.ci_high);
    }

    Ok((labels, means, ci_lows, ci_highs))
}

pub fn extract_run_values(
    suite_data: &PlotSuiteData,
    metric_name: &str,
) -> Result<(Vec<String>, Vec<Vec<f64>>)> {
    let mut labels = Vec::new();
    let mut all_values = Vec::new();

    for scenario_key in suite_data.scenario_keys() {
        let payload = suite_data
            .scenario_results
            .get(&scenario_key)
            .ok_or_else(|| {
                PlotsError::Validation(format!("Сценарий '{scenario_key}' отсутствует"))
            })?;

        let mut values = Vec::new();
        for row in &payload.run_summaries {
            if let Some(Value::Number(num)) = row.get(metric_name) {
                if let Some(v) = num.as_f64() {
                    values.push(v);
                }
            }
        }

        if !values.is_empty() {
            labels.push(scenario_key);
            all_values.push(values);
        }
    }

    if all_values.is_empty() {
        return Err(PlotsError::Validation(format!(
            "Метрика '{metric_name}' не найдена на уровне отдельных прогонов"
        )));
    }

    Ok((labels, all_values))
}

pub fn extract_pi_hat_matrix(
    suite_data: &PlotSuiteData,
) -> Result<(Vec<String>, Vec<usize>, Vec<Vec<f64>>)> {
    let labels = suite_data.scenario_keys();

    let mut state_indices = BTreeSet::new();
    for scenario_key in &labels {
        let payload = suite_data
            .scenario_results
            .get(scenario_key)
            .ok_or_else(|| {
                PlotsError::Validation(format!("Сценарий '{scenario_key}' отсутствует"))
            })?;

        for metric_name in payload.metric_summaries.keys() {
            if let Some(rest) = metric_name.strip_prefix("pi_hat_") {
                let idx = rest.parse::<usize>().map_err(|e| {
                    PlotsError::Validation(format!(
                        "Не удалось распарсить индекс состояния из '{metric_name}': {e}"
                    ))
                })?;
                state_indices.insert(idx);
            }
        }
    }

    if state_indices.is_empty() {
        return Err(PlotsError::Validation(
            "В наборе результатов нет метрик вида pi_hat_k".to_string(),
        ));
    }

    let states: Vec<usize> = state_indices.into_iter().collect();
    let mut matrix = vec![vec![0.0; states.len()]; labels.len()];

    for (i, scenario_key) in labels.iter().enumerate() {
        let payload = suite_data
            .scenario_results
            .get(scenario_key)
            .ok_or_else(|| {
                PlotsError::Validation(format!("Сценарий '{scenario_key}' отсутствует"))
            })?;

        for (j, state) in states.iter().enumerate() {
            let name = format!("pi_hat_{state}");
            if let Some(summary) = payload.metric_summaries.get(&name) {
                matrix[i][j] = summary.mean;
            }
        }
    }

    Ok((labels, states, matrix))
}

fn sanitize_filename(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    for ch in name.chars() {
        if ch.is_ascii_alphanumeric()
            || ch == '.'
            || ch == '_'
            || ch == '-'
            || ('А'..='я').contains(&ch)
            || ch == 'Ё'
            || ch == 'ё'
        {
            out.push(ch);
        } else {
            out.push('_');
        }
    }

    let cleaned = out.trim_matches(|c: char| c == '.' || c == '_').to_string();
    if cleaned.is_empty() {
        "plot".to_string()
    } else {
        cleaned
    }
}

fn ensure_dir(path: impl AsRef<Path>) -> Result<PathBuf> {
    let path_obj = path.as_ref().to_path_buf();
    fs::create_dir_all(&path_obj)?;
    Ok(path_obj)
}

fn y_bounds_with_margin(values: &[f64]) -> (f64, f64) {
    if values.is_empty() {
        return (0.0, 1.0);
    }
    let min = values.iter().copied().fold(f64::INFINITY, f64::min);
    let max = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let span = (max - min).abs();
    let margin = (span * 0.15).max(1e-6);
    (min - margin, max + margin)
}

fn quartiles(values: &[f64]) -> Result<(f64, f64, f64, f64, f64)> {
    if values.is_empty() {
        return Err(PlotsError::Validation(
            "Нельзя построить boxplot по пустому набору значений".to_string(),
        ));
    }

    let mut v = values.to_vec();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());

    fn median(sorted: &[f64]) -> f64 {
        let n = sorted.len();
        if n % 2 == 1 {
            sorted[n / 2]
        } else {
            0.5 * (sorted[n / 2 - 1] + sorted[n / 2])
        }
    }

    let n = v.len();
    let med = median(&v);
    let (lower, upper) = if n % 2 == 1 {
        (&v[..n / 2], &v[n / 2 + 1..])
    } else {
        (&v[..n / 2], &v[n / 2..])
    };

    let q1 = if lower.is_empty() {
        v[0]
    } else {
        median(lower)
    };
    let q3 = if upper.is_empty() {
        v[n - 1]
    } else {
        median(upper)
    };

    Ok((v[0], q1, med, q3, v[n - 1]))
}

pub fn plot_metric_comparison(
    suite_data: &PlotSuiteData,
    metric_name: &str,
    output_dir: impl AsRef<Path>,
    title: Option<&str>,
) -> Result<PathBuf> {
    let (labels, means, ci_lows, ci_highs) = extract_metric_vectors(suite_data, metric_name)?;
    let all_y: Vec<f64> = means
        .iter()
        .copied()
        .chain(ci_lows.iter().copied())
        .chain(ci_highs.iter().copied())
        .collect();

    let (y_min, y_max) = y_bounds_with_margin(&all_y);
    let baseline = 0.0f64.min(y_min);

    let out_dir = ensure_dir(output_dir)?;

    let out_path = out_dir.join(format!("metric_{}.png", sanitize_filename(metric_name)));

    {
        let backend_path = out_path.clone();
        let root = BitMapBackend::new(&backend_path, (1200, 700)).into_drawing_area();
        root.fill(&WHITE)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        let mut chart = ChartBuilder::on(&root)
            .caption(
                title.unwrap_or(&format!("Сравнение сценариев по метрике: {metric_name}")),
                ("sans-serif", 30),
            )
            .margin(20)
            .x_label_area_size(80)
            .y_label_area_size(80)
            .build_cartesian_2d(0..labels.len(), y_min..y_max)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        chart
            .configure_mesh()
            .x_labels(labels.len())
            .x_label_formatter(&|x| labels.get(*x).cloned().unwrap_or_else(|| x.to_string()))
            .y_desc(metric_name)
            .light_line_style(RGBColor(220, 220, 220))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        for i in 0..means.len() {
            chart
                .draw_series(std::iter::once(Rectangle::new(
                    [(i, baseline), (i + 1, means[i])],
                    BLUE.mix(0.55).filled(),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            let center_x = i;
            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center_x, ci_lows[i]), (center_x, ci_highs[i])],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center_x, ci_lows[i]), (center_x + 1, ci_lows[i])],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center_x, ci_highs[i]), (center_x + 1, ci_highs[i])],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
        }

        root.present()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
    }

    Ok(out_path)
}

pub fn plot_metric_boxplot(
    suite_data: &PlotSuiteData,
    metric_name: &str,
    output_dir: impl AsRef<Path>,
    title: Option<&str>,
) -> Result<PathBuf> {
    let (labels, values) = extract_run_values(suite_data, metric_name)?;

    let all_values: Vec<f64> = values.iter().flatten().copied().collect();
    let (y_min, y_max) = y_bounds_with_margin(&all_values);

    let out_dir = ensure_dir(output_dir)?;
    let out_path = out_dir.join(format!("boxplot_{}.png", sanitize_filename(metric_name)));

    {
        let backend_path = out_path.clone();
        let root = BitMapBackend::new(&backend_path, (1200, 700)).into_drawing_area();
        root.fill(&WHITE)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        let mut chart = ChartBuilder::on(&root)
            .caption(
                title.unwrap_or(&format!("Разброс replication по метрике: {metric_name}")),
                ("sans-serif", 30),
            )
            .margin(20)
            .x_label_area_size(80)
            .y_label_area_size(80)
            .build_cartesian_2d(0..labels.len(), y_min..y_max)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        chart
            .configure_mesh()
            .x_labels(labels.len())
            .x_label_formatter(&|x| labels.get(*x).cloned().unwrap_or_else(|| x.to_string()))
            .y_desc(metric_name)
            .light_line_style(RGBColor(220, 220, 220))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        for (i, scenario_values) in values.iter().enumerate() {
            let (min_v, q1, med, q3, max_v) = quartiles(scenario_values)?;

            chart
                .draw_series(std::iter::once(Rectangle::new(
                    [(i, q1), (i + 1, q3)],
                    BLUE.mix(0.30).filled(),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(i, med), (i + 1, med)],
                    BLUE.stroke_width(3),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            let center = i;
            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center, min_v), (center, q1)],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center, q3), (center, max_v)],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center, min_v), (center + 1, min_v)],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(PathElement::new(
                    vec![(center, max_v), (center + 1, max_v)],
                    BLACK.stroke_width(2),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
        }

        root.present()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
    }

    Ok(out_path)
}

pub fn plot_stationary_distribution_by_scenarios(
    suite_data: &PlotSuiteData,
    output_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let (labels, states, matrix) = extract_pi_hat_matrix(suite_data)?;

    let max_state = states.iter().copied().max().unwrap_or(0);
    let max_y = matrix
        .iter()
        .flatten()
        .copied()
        .fold(0.0_f64, f64::max)
        .max(1e-6);

    let out_dir = ensure_dir(output_dir)?;
    let out_path = out_dir.join("stationary_distribution.png");

    {
        let backend_path = out_path.clone();
        let root = BitMapBackend::new(&backend_path, (1200, 700)).into_drawing_area();
        root.fill(&WHITE)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        let mut chart = ChartBuilder::on(&root)
            .caption(
                "Оценка стационарного распределения по числу заявок",
                ("sans-serif", 30),
            )
            .margin(20)
            .x_label_area_size(70)
            .y_label_area_size(80)
            .build_cartesian_2d(0..(max_state + 1), 0.0..(max_y * 1.15))
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        chart
            .configure_mesh()
            .x_desc("Состояние k")
            .y_desc("pi_hat(k)")
            .light_line_style(RGBColor(220, 220, 220))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        for (i, scenario_label) in labels.iter().enumerate() {
            let color = Palette99::pick(i).mix(0.9);

            let points: Vec<(usize, f64)> = states
                .iter()
                .enumerate()
                .map(|(j, state)| (*state, matrix[i][j]))
                .collect();

            chart
                .draw_series(LineSeries::new(points.clone(), &color))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?
                .label(scenario_label.clone())
                .legend(move |(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], color));

            chart
                .draw_series(
                    points
                        .into_iter()
                        .map(|(x, y)| Circle::new((x, y), 4, color.filled())),
                )
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
        }

        chart
            .configure_series_labels()
            .border_style(&BLACK)
            .background_style(&WHITE.mix(0.8))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        root.present()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
    }

    Ok(out_path)
}

pub fn plot_rejection_breakdown(
    suite_data: &PlotSuiteData,
    output_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let labels = suite_data.scenario_keys();

    let mut capacity = Vec::new();
    let mut server = Vec::new();
    let mut resource = Vec::new();

    for scenario_key in &labels {
        capacity.push(metric_summary(suite_data, scenario_key, "rejected_capacity")?.mean);
        server.push(metric_summary(suite_data, scenario_key, "rejected_server")?.mean);
        resource.push(metric_summary(suite_data, scenario_key, "rejected_resource")?.mean);
    }

    // let max_y = capacity
    //     .iter()
    //     .zip(server.iter())
    //     .zip(resource.iter())
    //     .map(|((a, b), c)| a + b + c)
    //     .fold(0.0_f64, f64::max)
    //     .max(1e-6);

    let out_dir = ensure_dir(output_dir)?;
    let out_path = out_dir.join("rejection_breakdown.png");

    {
        let backend_path = out_path.clone();
        let root = BitMapBackend::new(&backend_path, (1200, 700)).into_drawing_area();
        root.fill(&WHITE)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        let max_y = capacity
            .iter()
            .zip(server.iter())
            .zip(resource.iter())
            .map(|((c, s), r)| c + s + r)
            .fold(0.0, f64::max);

        let mut chart = ChartBuilder::on(&root)
            .caption("Декомпозиция отказов по причинам", ("sans-serif", 30))
            .margin(20)
            .x_label_area_size(80)
            .y_label_area_size(80)
            .build_cartesian_2d(0..labels.len(), 0.0..(max_y * 1.15))
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        chart
            .configure_mesh()
            .x_labels(labels.len())
            .x_label_formatter(&|x| labels.get(*x).cloned().unwrap_or_else(|| x.to_string()))
            .y_desc("Среднее число отказов")
            .light_line_style(&RGBColor(220, 220, 220))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        for i in 0..labels.len() {
            let c0 = 0.0;
            let c1 = capacity[i];
            let s1 = c1 + server[i];
            let r1 = s1 + resource[i];

            chart
                .draw_series(std::iter::once(Rectangle::new(
                    [(i, c0), (i + 1, c1)],
                    BLUE.mix(0.6).filled(),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(Rectangle::new(
                    [(i, c1), (i + 1, s1)],
                    RED.mix(0.6).filled(),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

            chart
                .draw_series(std::iter::once(Rectangle::new(
                    [(i, s1), (i + 1, r1)],
                    GREEN.mix(0.6).filled(),
                )))
                .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
        }

        root.present()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
    }

    Ok(out_path)
}

fn heatmap_color(value: f64, min_v: f64, max_v: f64) -> HSLColor {
    let denom = (max_v - min_v).abs().max(1e-12);
    let t = ((value - min_v) / denom).clamp(0.0, 1.0);
    HSLColor(240.0 * (1.0 - t), 0.80, 0.55)
}

pub fn plot_scenario_heatmap_pi(
    suite_data: &PlotSuiteData,
    output_dir: impl AsRef<Path>,
) -> Result<PathBuf> {
    let (labels, states, matrix) = extract_pi_hat_matrix(suite_data)?;

    let flat: Vec<f64> = matrix.iter().flatten().copied().collect();
    let min_v = flat.iter().copied().fold(f64::INFINITY, f64::min);
    let max_v = flat.iter().copied().fold(f64::NEG_INFINITY, f64::max);

    let out_dir = ensure_dir(output_dir)?;
    let out_path = out_dir.join("pi_hat_heatmap.png");

    {
        let backend_path = out_path.clone();
        let root = BitMapBackend::new(&backend_path, (1200, 700)).into_drawing_area();
        root.fill(&WHITE)
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        let mut chart = ChartBuilder::on(&root)
            .caption("Heatmap оценок pi_hat(k)", ("sans-serif", 30))
            .margin(20)
            .x_label_area_size(70)
            .y_label_area_size(100)
            .build_cartesian_2d(0..states.len(), 0..labels.len())
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        chart
            .configure_mesh()
            .x_desc("Состояние k")
            .y_desc("Сценарий")
            .x_labels(states.len())
            .y_labels(labels.len())
            .x_label_formatter(&|x| {
                states
                    .get(*x)
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| x.to_string())
            })
            .y_label_formatter(&|y| labels.get(*y).cloned().unwrap_or_else(|| y.to_string()))
            .draw()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;

        for (i, row) in matrix.iter().enumerate() {
            for (j, value) in row.iter().enumerate() {
                let color = heatmap_color(*value, min_v, max_v);
                chart
                    .draw_series(std::iter::once(Rectangle::new(
                        [(j, i), (j + 1, i + 1)],
                        color.filled(),
                    )))
                    .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
            }
        }

        root.present()
            .map_err(|e| PlotsError::Validation(format!("Plot error: {e}")))?;
    }

    Ok(out_path)
}

pub fn generate_standard_plots(
    suite_data: &PlotSuiteData,
    output_dir: impl AsRef<Path>,
    extra_metrics: Option<&[&str]>,
) -> Result<Vec<PathBuf>> {
    let out_dir = ensure_dir(output_dir)?;
    let mut created = Vec::new();

    let mut default_metrics = vec![
        "mean_num_jobs".to_string(),
        "mean_occupied_resource".to_string(),
        "loss_probability".to_string(),
        "throughput".to_string(),
        "accepted_arrivals".to_string(),
        "rejected_arrivals".to_string(),
        "completed_jobs".to_string(),
    ];

    if let Some(metrics) = extra_metrics {
        for metric in metrics {
            if !default_metrics.iter().any(|m| m == metric) {
                default_metrics.push((*metric).to_string());
            }
        }
    }

    let available: BTreeSet<String> = available_metric_names(suite_data).into_iter().collect();

    for metric in &default_metrics {
        if available.contains(metric) {
            created.push(plot_metric_comparison(suite_data, metric, &out_dir, None)?);

            if extract_run_values(suite_data, metric).is_ok() {
                created.push(plot_metric_boxplot(suite_data, metric, &out_dir, None)?);
            }
        }
    }

    if available.iter().any(|name| name.starts_with("pi_hat_")) {
        created.push(plot_stationary_distribution_by_scenarios(
            suite_data, &out_dir,
        )?);
        created.push(plot_scenario_heatmap_pi(suite_data, &out_dir)?);
    }

    let rejection_metrics: BTreeSet<String> = [
        "rejected_capacity".to_string(),
        "rejected_server".to_string(),
        "rejected_resource".to_string(),
    ]
    .into_iter()
    .collect();

    if rejection_metrics.is_subset(&available) {
        created.push(plot_rejection_breakdown(suite_data, &out_dir)?);
    }

    Ok(created)
}

pub fn print_available_metrics(suite_data: &PlotSuiteData) {
    println!("{}", "=".repeat(80));
    println!("Набор результатов: {}", suite_data.suite_name);
    println!("Создан: {}", suite_data.created_at);
    println!("Сценариев: {}", suite_data.scenario_results.len());
    println!("{}", "-".repeat(80));
    println!("Доступные агрегированные метрики:");
    for name in available_metric_names(suite_data) {
        println!("  - {}", name);
    }
    println!("{}", "=".repeat(80));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::experiments::MetricSummary;
    use serde_json::json;

    fn demo_suite() -> PlotSuiteData {
        let mut metric_summaries = BTreeMap::new();
        metric_summaries.insert(
            "throughput".to_string(),
            MetricSummary {
                name: "throughput".to_string(),
                n: 3,
                mean: 1.2,
                std: 0.1,
                stderr: 0.05,
                ci_level: 0.95,
                ci_low: 1.1,
                ci_high: 1.3,
                min_value: 1.0,
                max_value: 1.4,
            },
        );
        metric_summaries.insert(
            "pi_hat_0".to_string(),
            MetricSummary {
                name: "pi_hat_0".to_string(),
                n: 3,
                mean: 0.4,
                std: 0.1,
                stderr: 0.05,
                ci_level: 0.95,
                ci_low: 0.3,
                ci_high: 0.5,
                min_value: 0.2,
                max_value: 0.6,
            },
        );
        metric_summaries.insert(
            "pi_hat_1".to_string(),
            MetricSummary {
                name: "pi_hat_1".to_string(),
                n: 3,
                mean: 0.6,
                std: 0.1,
                stderr: 0.05,
                ci_level: 0.95,
                ci_low: 0.5,
                ci_high: 0.7,
                min_value: 0.4,
                max_value: 0.8,
            },
        );

        let run_summaries = vec![
            BTreeMap::from([
                ("throughput".to_string(), json!(1.0)),
                ("loss_probability".to_string(), json!(0.1)),
            ]),
            BTreeMap::from([
                ("throughput".to_string(), json!(1.2)),
                ("loss_probability".to_string(), json!(0.2)),
            ]),
            BTreeMap::from([
                ("throughput".to_string(), json!(1.4)),
                ("loss_probability".to_string(), json!(0.15)),
            ]),
        ];

        let scenario_a = PlotScenarioData {
            scenario_name: "A".to_string(),
            scenario_description: "Scenario A".to_string(),
            replications: 3,
            metric_summaries: metric_summaries.clone(),
            run_summaries: run_summaries.clone(),
        };

        let mut metric_summaries_b = metric_summaries.clone();
        if let Some(m) = metric_summaries_b.get_mut("throughput") {
            m.mean = 1.8;
            m.ci_low = 1.7;
            m.ci_high = 1.9;
        }

        let scenario_b = PlotScenarioData {
            scenario_name: "B".to_string(),
            scenario_description: "Scenario B".to_string(),
            replications: 3,
            metric_summaries: metric_summaries_b,
            run_summaries,
        };

        PlotSuiteData {
            suite_name: "demo".to_string(),
            created_at: "2026-03-31T12:00:00".to_string(),
            scenario_results: BTreeMap::from([
                ("scenario_a".to_string(), scenario_a),
                ("scenario_b".to_string(), scenario_b),
            ]),
        }
    }

    #[test]
    fn available_metrics_are_detected() {
        let suite = demo_suite();
        let names = available_metric_names(&suite);
        assert!(names.contains(&"throughput".to_string()));
        assert!(names.contains(&"pi_hat_0".to_string()));
    }

    #[test]
    fn pi_hat_matrix_is_extracted() {
        let suite = demo_suite();
        let (labels, states, matrix) = extract_pi_hat_matrix(&suite).unwrap();
        assert_eq!(labels.len(), 2);
        assert_eq!(states, vec![0, 1]);
        assert_eq!(matrix.len(), 2);
        assert_eq!(matrix[0].len(), 2);
    }

    #[test]
    fn sanitize_filename_works() {
        assert_eq!(sanitize_filename("throughput mean"), "throughput_mean");
    }
}
