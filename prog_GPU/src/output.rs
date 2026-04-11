use crate::experiments::render_suite_summary_text;
use crate::stats::{ExperimentSuiteResult, StatsError};
use chrono::Local;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::BufWriter;
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum OutputError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Csv(#[from] csv::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),

    #[error(transparent)]
    Stats(#[from] StatsError),
}

pub type Result<T> = std::result::Result<T, OutputError>;

/// Что именно сохранять на диск.
#[derive(Debug, Clone)]
pub struct SaveOptions {
    pub save_run_summaries: bool,
    pub save_metric_tables: bool,
    pub save_text_summary: bool,
}

impl Default for SaveOptions {
    fn default() -> Self {
        Self {
            save_run_summaries: true,
            save_metric_tables: true,
            save_text_summary: true,
        }
    }
}

/// Пути к созданным артефактам.
#[derive(Debug, Clone)]
pub struct OutputArtifacts {
    pub output_dir: PathBuf,
    pub suite_result_json: PathBuf,
    pub suite_summary_txt: Option<PathBuf>,
    pub aggregated_summary_csv: PathBuf,
    pub metric_summaries_csv: Option<PathBuf>,
    pub run_summaries_csv: Option<PathBuf>,
}

impl OutputArtifacts {
    pub fn summary_string(&self) -> String {
        format!(
            concat!(
                "OutputArtifacts(",
                "output_dir='{}', suite_result_json='{}', ",
                "suite_summary_txt={:?}, aggregated_summary_csv='{}', ",
                "metric_summaries_csv={:?}, run_summaries_csv={:?}",
                ")"
            ),
            self.output_dir.display(),
            self.suite_result_json.display(),
            self.suite_summary_txt
                .as_ref()
                .map(|p| p.display().to_string()),
            self.aggregated_summary_csv.display(),
            self.metric_summaries_csv
                .as_ref()
                .map(|p| p.display().to_string()),
            self.run_summaries_csv
                .as_ref()
                .map(|p| p.display().to_string()),
        )
    }
}

/// Timestamp в формате, удобном для имён папок.
pub fn timestamp() -> String {
    Local::now().format("%Y%m%d_%H%M%S").to_string()
}

/// Безопасный slug для имени серии.
pub fn suite_slug(suite_name: &str) -> String {
    let mut out = String::with_capacity(suite_name.len());

    for ch in suite_name.chars() {
        if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' || ch == '.' {
            out.push(ch);
        } else {
            out.push('_');
        }
    }

    let trimmed = out.trim_matches('_');
    if trimmed.is_empty() {
        "suite".to_string()
    } else {
        trimmed.to_string()
    }
}

fn ensure_directory(path: &Path) -> Result<()> {
    fs::create_dir_all(path)?;
    Ok(())
}

/// Создать output-папку для серии вида:
/// results/<timestamp>__<suite_slug>
pub fn make_suite_output_dir(output_root: impl AsRef<Path>, suite_name: &str) -> Result<PathBuf> {
    if suite_name.trim().is_empty() {
        return Err(OutputError::Validation(
            "suite_name не должен быть пустым".to_string(),
        ));
    }

    let dir = output_root
        .as_ref()
        .join(format!("{}__{}", timestamp(), suite_slug(suite_name)));

    ensure_directory(&dir)?;
    Ok(dir)
}

fn save_text(text: &str, path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = path.as_ref().to_path_buf();
    let mut body = text.to_string();
    if !body.ends_with('\n') {
        body.push('\n');
    }
    fs::write(&path, body)?;
    Ok(path)
}

fn value_to_csv_string(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::Bool(v) => v.to_string(),
        Value::Number(v) => v.to_string(),
        Value::String(v) => v.clone(),
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

fn write_csv(rows: &[BTreeMap<String, Value>], filepath: &Path) -> Result<PathBuf> {
    if let Some(parent) = filepath.parent() {
        ensure_directory(parent)?;
    }

    if rows.is_empty() {
        fs::write(filepath, "")?;
        return Ok(filepath.to_path_buf());
    }

    let mut fieldnames = BTreeSet::new();
    for row in rows {
        for key in row.keys() {
            fieldnames.insert(key.clone());
        }
    }
    let fieldnames: Vec<String> = fieldnames.into_iter().collect();

    let file = File::create(filepath)?;
    let writer = BufWriter::new(file);
    let mut csv_writer = csv::Writer::from_writer(writer);

    csv_writer.write_record(&fieldnames)?;

    for row in rows {
        let record: Vec<String> = fieldnames
            .iter()
            .map(|key| row.get(key).map(value_to_csv_string).unwrap_or_default())
            .collect();
        csv_writer.write_record(&record)?;
    }

    csv_writer.flush()?;
    Ok(filepath.to_path_buf())
}

/// Сохранить полный набор результатов серии в уже существующую папку.
pub fn save_suite_result_to_dir(
    suite_result: &ExperimentSuiteResult,
    output_dir: impl AsRef<Path>,
    options: &SaveOptions,
) -> Result<OutputArtifacts> {
    suite_result.validate()?;

    let output_dir = output_dir.as_ref().to_path_buf();
    ensure_directory(&output_dir)?;

    let suite_result_json = output_dir.join("suite_result.json");
    fs::write(&suite_result_json, serde_json::to_string_pretty(suite_result)?)?;

    let aggregated_summary_csv = write_csv(
        &suite_result.aggregated_rows(),
        &output_dir.join("aggregated_summary.csv"),
    )?;

    let suite_summary_txt = if options.save_text_summary {
        Some(save_text(
            &render_suite_summary_text(suite_result, None),
            output_dir.join("suite_summary.txt"),
        )?)
    } else {
        None
    };

    let metric_summaries_csv = if options.save_metric_tables {
        Some(write_csv(
            &suite_result.metric_rows(),
            &output_dir.join("metric_summaries.csv"),
        )?)
    } else {
        None
    };

    let run_summaries_csv = if options.save_run_summaries {
        Some(write_csv(
            &suite_result.all_run_rows(),
            &output_dir.join("run_summaries.csv"),
        )?)
    } else {
        None
    };

    Ok(OutputArtifacts {
        output_dir,
        suite_result_json,
        suite_summary_txt,
        aggregated_summary_csv,
        metric_summaries_csv,
        run_summaries_csv,
    })
}

/// Удобная обёртка:
/// - создать timestamped output-dir;
/// - сохранить туда всю серию;
/// - вернуть пути к артефактам.
pub fn save_suite_result(
    suite_result: &ExperimentSuiteResult,
    output_root: impl AsRef<Path>,
    options: &SaveOptions,
) -> Result<OutputArtifacts> {
    let output_dir = make_suite_output_dir(output_root, &suite_result.suite_name)?;
    save_suite_result_to_dir(suite_result, output_dir, options)
}