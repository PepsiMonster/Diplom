use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use thiserror::Error;

/// Путь по умолчанию к JSON-конфигу, который генерирует Python-часть.
pub const DEFAULT_EXPERIMENT_VALUES_PATH: &str = "py/generated/experiment_values.json";

#[derive(Debug, Error)]
pub enum ParamsError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

pub type Result<T> = std::result::Result<T, ParamsError>;

fn ensure_positive_f64(name: &str, value: f64) -> Result<()> {
    if !value.is_finite() || value <= 0.0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть конечным числом > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_nonnegative_f64(name: &str, value: f64) -> Result<()> {
    if !value.is_finite() || value < 0.0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть конечным числом >= 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_usize(name: &str, value: usize) -> Result<()> {
    if value == 0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_positive_u32(name: &str, value: u32) -> Result<()> {
    if value == 0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_probability(name: &str, value: f64) -> Result<()> {
    if !value.is_finite() || !(0.0 < value && value < 1.0) {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен лежать в интервале (0, 1), получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_probabilities_sum_to_one(name: &str, probs: &[f64], tol: f64) -> Result<()> {
    let total: f64 = probs.iter().sum();
    if (total - 1.0).abs() > tol {
        return Err(ParamsError::Validation(format!(
            "Сумма вероятностей '{name}' должна быть равна 1.0, сейчас это {total}"
        )));
    }
    Ok(())
}

fn ensure_nonempty_slice<T>(name: &str, values: &[T]) -> Result<()> {
    if values.is_empty() {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' не должен быть пустым"
        )));
    }
    Ok(())
}

fn ensure_unique_debug<T: Ord + Clone + std::fmt::Debug>(name: &str, values: &[T]) -> Result<()> {
    let uniq: BTreeSet<T> = values.iter().cloned().collect();
    if uniq.len() != values.len() {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' не должен содержать повторяющиеся значения: {:?}",
            values
        )));
    }
    Ok(())
}

fn ensure_unique_f64(name: &str, values: &[f64]) -> Result<()> {
    for i in 0..values.len() {
        for j in (i + 1)..values.len() {
            if values[i].to_bits() == values[j].to_bits() {
                return Err(ParamsError::Validation(format!(
                    "Параметр '{name}' не должен содержать повторяющиеся значения: {:?}",
                    values
                )));
            }
        }
    }
    Ok(())
}

/// Профиль workload-family из внешнего JSON.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkloadFamilyProfile {
    Fixed,
    Basic,
    Full,
}

/// Ключ workload-распределения, который приходит из JSON и
/// используется при построении сетки сценариев.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum WorkloadKind {
    #[serde(rename = "deterministic")]
    Deterministic,

    #[serde(rename = "exponential")]
    Exponential,

    #[serde(rename = "erlang_2")]
    Erlang2,

    #[serde(rename = "erlang_4")]
    Erlang4,

    #[serde(rename = "erlang_8")]
    Erlang8,

    #[serde(rename = "hyperexp_2")]
    Hyperexp2,

    #[serde(rename = "hyperexp_heavy")]
    HyperexpHeavy,
}

impl WorkloadKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Deterministic => "deterministic",
            Self::Exponential => "exponential",
            Self::Erlang2 => "erlang_2",
            Self::Erlang4 => "erlang_4",
            Self::Erlang8 => "erlang_8",
            Self::Hyperexp2 => "hyperexp_2",
            Self::HyperexpHeavy => "hyperexp_heavy",
        }
    }
}

/// Ключ arrival-process, который приходит из JSON и
/// используется при построении сетки сценариев.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum ArrivalProcessKind {
    #[serde(rename = "poisson")]
    Poisson,

    #[serde(rename = "erlang_2")]
    Erlang2,

    #[serde(rename = "erlang_4")]
    Erlang4,

    #[serde(rename = "hyperexp_2")]
    Hyperexp2,
}

impl ArrivalProcessKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Poisson => "poisson",
            Self::Erlang2 => "erlang_2",
            Self::Erlang4 => "erlang_4",
            Self::Hyperexp2 => "hyperexp_2",
        }
    }
}

/// Готовая численная спецификация распределения объёма работы.
/// Это уже не "ключ", а конкретные параметры, удобные для backend.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WorkloadDistributionSpec {
    Deterministic {
        mean: f64,
        label: String,
    },
    Exponential {
        mean: f64,
        label: String,
    },
    Erlang {
        mean: f64,
        order: usize,
        label: String,
    },
    Hyperexponential2 {
        mean: f64,
        p: f64,
        fast_rate_multiplier: f64,
        label: String,
    },
}

/// Готовая численная спецификация входящего потока.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ArrivalProcessSpec {
    Poisson,
    Erlang {
        order: usize,
    },
    Hyperexponential2 {
        p: f64,
        fast_rate_multiplier: f64,
    },
}

/// Спецификация распределения требований к ресурсу.
/// В этой GPU-ветке у нас только дискретное пользовательское распределение.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResourceDistributionSpec {
    pub values: Vec<u32>,
    pub probabilities: Vec<f64>,
}

impl ResourceDistributionSpec {
    pub fn validate(&self) -> Result<()> {
        ensure_nonempty_slice("resource.values", &self.values)?;
        ensure_nonempty_slice("resource.probabilities", &self.probabilities)?;

        if self.values.len() != self.probabilities.len() {
            return Err(ParamsError::Validation(format!(
                "Длины resource.values и resource.probabilities должны совпадать, \
                 получено {} и {}",
                self.values.len(),
                self.probabilities.len()
            )));
        }

        for (i, v) in self.values.iter().enumerate() {
            ensure_positive_u32(&format!("resource.values[{i}]"), *v)?;
        }

        for (i, p) in self.probabilities.iter().enumerate() {
            ensure_probability(&format!("resource.probabilities[{i}]"), *p)?;
        }

        ensure_probabilities_sum_to_one("resource.probabilities", &self.probabilities, 1e-10)?;
        Ok(())
    }

    pub fn min_value(&self) -> u32 {
        *self.values.iter().min().unwrap_or(&u32::MAX)
    }
}

/// Внешний конфиг серии экспериментов.
/// Он соответствует новому, упрощённому JSON из Python-ветки.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentConfig {
    pub suite_name: String,
    pub replications: usize,
    pub max_time: f64,
    pub warmup_time: f64,
    pub base_seed: u64,

    pub servers_n: usize,
    pub total_resource_r: u32,

    pub arrival_rate_levels: Vec<f64>,
    pub service_speed_levels: Vec<f64>,

    pub resource_values: Vec<u32>,
    pub resource_probabilities: Vec<f64>,

    pub mean_workload: f64,

    pub workload_family_profile: WorkloadFamilyProfile,
    pub fixed_workload: WorkloadKind,
    pub workload_family_basic: Vec<WorkloadKind>,
    pub workload_family_full: Vec<WorkloadKind>,

    pub workload_hyperexp_p: f64,
    pub workload_hyperexp_fast_multiplier: f64,
    pub workload_hyperexp_heavy_p: f64,
    pub workload_hyperexp_heavy_fast_multiplier: f64,

    pub arrival_process_family: Vec<ArrivalProcessKind>,
    pub arrival_hyperexp_p: f64,
    pub arrival_hyperexp_fast_multiplier: f64,
}

impl ExperimentConfig {
    /// Прочитать конфиг из JSON-файла.
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        let text = fs::read_to_string(path)?;
        let cfg: Self = serde_json::from_str(&text)?;
        cfg.validate()?;
        Ok(cfg)
    }

    /// Прочитать конфиг из стандартного пути.
    pub fn load_default() -> Result<Self> {
        Self::load(DEFAULT_EXPERIMENT_VALUES_PATH)
    }

    /// Применить CLI override-ы и ещё раз провалидировать результат.
    pub fn with_overrides(
        &self,
        suite_name: Option<String>,
        replications: Option<usize>,
        max_time: Option<f64>,
        warmup_time: Option<f64>,
    ) -> Result<Self> {
        let mut updated = self.clone();

        if let Some(v) = suite_name {
            updated.suite_name = v;
        }
        if let Some(v) = replications {
            updated.replications = v;
        }
        if let Some(v) = max_time {
            updated.max_time = v;
        }
        if let Some(v) = warmup_time {
            updated.warmup_time = v;
        }

        updated.validate()?;
        Ok(updated)
    }

    /// Для этой GPU-ветки мы считаем только loss-систему, поэтому K = N.
    pub fn capacity_k(&self) -> usize {
        self.servers_n
    }

    /// Эффективная длина окна наблюдения.
    pub fn observed_time(&self) -> f64 {
        self.max_time - self.warmup_time
    }

    /// Готовая спецификация распределения ресурса.
    pub fn resource_distribution(&self) -> ResourceDistributionSpec {
        ResourceDistributionSpec {
            values: self.resource_values.clone(),
            probabilities: self.resource_probabilities.clone(),
        }
    }

    /// Развернуть workload-family в конкретный список ключей.
    pub fn resolved_workload_family(&self) -> Result<Vec<WorkloadKind>> {
        let family = match self.workload_family_profile {
            WorkloadFamilyProfile::Fixed => vec![self.fixed_workload],
            WorkloadFamilyProfile::Basic => self.workload_family_basic.clone(),
            WorkloadFamilyProfile::Full => self.workload_family_full.clone(),
        };

        ensure_nonempty_slice("resolved_workload_family", &family)?;
        Ok(family)
    }

    /// Построить численную спецификацию workload-распределения по ключу.
    pub fn build_workload_spec(&self, kind: WorkloadKind) -> Result<WorkloadDistributionSpec> {
        ensure_positive_f64("mean_workload", self.mean_workload)?;

        let spec = match kind {
            WorkloadKind::Deterministic => WorkloadDistributionSpec::Deterministic {
                mean: self.mean_workload,
                label: "Deterministic".to_string(),
            },

            WorkloadKind::Exponential => WorkloadDistributionSpec::Exponential {
                mean: self.mean_workload,
                label: "Exponential".to_string(),
            },

            WorkloadKind::Erlang2 => WorkloadDistributionSpec::Erlang {
                mean: self.mean_workload,
                order: 2,
                label: "Erlang(2)".to_string(),
            },

            WorkloadKind::Erlang4 => WorkloadDistributionSpec::Erlang {
                mean: self.mean_workload,
                order: 4,
                label: "Erlang(4)".to_string(),
            },

            WorkloadKind::Erlang8 => WorkloadDistributionSpec::Erlang {
                mean: self.mean_workload,
                order: 8,
                label: "Erlang(8)".to_string(),
            },

            WorkloadKind::Hyperexp2 => {
                ensure_probability("workload_hyperexp_p", self.workload_hyperexp_p)?;
                ensure_positive_f64(
                    "workload_hyperexp_fast_multiplier",
                    self.workload_hyperexp_fast_multiplier,
                )?;

                WorkloadDistributionSpec::Hyperexponential2 {
                    mean: self.mean_workload,
                    p: self.workload_hyperexp_p,
                    fast_rate_multiplier: self.workload_hyperexp_fast_multiplier,
                    label: "HyperExp(2)".to_string(),
                }
            }

            WorkloadKind::HyperexpHeavy => {
                ensure_probability(
                    "workload_hyperexp_heavy_p",
                    self.workload_hyperexp_heavy_p,
                )?;
                ensure_positive_f64(
                    "workload_hyperexp_heavy_fast_multiplier",
                    self.workload_hyperexp_heavy_fast_multiplier,
                )?;

                WorkloadDistributionSpec::Hyperexponential2 {
                    mean: self.mean_workload,
                    p: self.workload_hyperexp_heavy_p,
                    fast_rate_multiplier: self.workload_hyperexp_heavy_fast_multiplier,
                    label: "HyperExp(heavy)".to_string(),
                }
            }
        };

        Ok(spec)
    }

    /// Построить численную спецификацию arrival-process по ключу.
    pub fn build_arrival_spec(&self, kind: ArrivalProcessKind) -> Result<ArrivalProcessSpec> {
        let spec = match kind {
            ArrivalProcessKind::Poisson => ArrivalProcessSpec::Poisson,

            ArrivalProcessKind::Erlang2 => ArrivalProcessSpec::Erlang { order: 2 },

            ArrivalProcessKind::Erlang4 => ArrivalProcessSpec::Erlang { order: 4 },

            ArrivalProcessKind::Hyperexp2 => {
                ensure_probability("arrival_hyperexp_p", self.arrival_hyperexp_p)?;
                ensure_positive_f64(
                    "arrival_hyperexp_fast_multiplier",
                    self.arrival_hyperexp_fast_multiplier,
                )?;

                ArrivalProcessSpec::Hyperexponential2 {
                    p: self.arrival_hyperexp_p,
                    fast_rate_multiplier: self.arrival_hyperexp_fast_multiplier,
                }
            }
        };

        Ok(spec)
    }

    /// Основная валидация конфига.
    pub fn validate(&self) -> Result<()> {
        if self.suite_name.trim().is_empty() {
            return Err(ParamsError::Validation(
                "Параметр 'suite_name' должен быть непустой строкой".to_string(),
            ));
        }

        ensure_positive_usize("replications", self.replications)?;
        ensure_positive_f64("max_time", self.max_time)?;
        ensure_nonnegative_f64("warmup_time", self.warmup_time)?;

        if self.warmup_time >= self.max_time {
            return Err(ParamsError::Validation(format!(
                "warmup_time должен быть строго меньше max_time, получено: {} >= {}",
                self.warmup_time, self.max_time
            )));
        }

        ensure_positive_usize("servers_n", self.servers_n)?;
        ensure_positive_u32("total_resource_r", self.total_resource_r)?;

    ensure_nonempty_slice("arrival_rate_levels", &self.arrival_rate_levels)?;
    for (i, v) in self.arrival_rate_levels.iter().enumerate() {
        ensure_nonnegative_f64(&format!("arrival_rate_levels[{i}]"), *v)?;
    }
    ensure_unique_f64("arrival_rate_levels", &self.arrival_rate_levels)?;

    ensure_nonempty_slice("service_speed_levels", &self.service_speed_levels)?;
    for (i, v) in self.service_speed_levels.iter().enumerate() {
        ensure_positive_f64(&format!("service_speed_levels[{i}]"), *v)?;
    }
    ensure_unique_f64("service_speed_levels", &self.service_speed_levels)?;

        ensure_positive_f64("mean_workload", self.mean_workload)?;

        let resource = self.resource_distribution();
        resource.validate()?;
        if resource.min_value() > self.total_resource_r {
            return Err(ParamsError::Validation(
                "Даже минимально возможное требование к ресурсу превышает total_resource_r: \
                 система не сможет принять ни одной заявки."
                    .to_string(),
            ));
        }

        ensure_nonempty_slice("workload_family_basic", &self.workload_family_basic)?;
        ensure_nonempty_slice("workload_family_full", &self.workload_family_full)?;
        ensure_unique_debug("workload_family_basic", &self.workload_family_basic)?;
        ensure_unique_debug("workload_family_full", &self.workload_family_full)?;

        ensure_probability("workload_hyperexp_p", self.workload_hyperexp_p)?;
        ensure_positive_f64(
            "workload_hyperexp_fast_multiplier",
            self.workload_hyperexp_fast_multiplier,
        )?;
        ensure_probability(
            "workload_hyperexp_heavy_p",
            self.workload_hyperexp_heavy_p,
        )?;
        ensure_positive_f64(
            "workload_hyperexp_heavy_fast_multiplier",
            self.workload_hyperexp_heavy_fast_multiplier,
        )?;

        ensure_nonempty_slice("arrival_process_family", &self.arrival_process_family)?;
        ensure_unique_debug("arrival_process_family", &self.arrival_process_family)?;

        ensure_probability("arrival_hyperexp_p", self.arrival_hyperexp_p)?;
        ensure_positive_f64(
            "arrival_hyperexp_fast_multiplier",
            self.arrival_hyperexp_fast_multiplier,
        )?;

        // Дополнительно проверяем, что профиль workload действительно разрешается.
        let resolved_workloads = self.resolved_workload_family()?;
        ensure_nonempty_slice("resolved_workload_family", &resolved_workloads)?;

        // И что все элементы arrival family можно построить.
        for kind in &self.arrival_process_family {
            let _ = self.build_arrival_spec(*kind)?;
        }

        Ok(())
    }

    /// Краткая текстовая сводка — удобно для validate-config и логов.
    pub fn summary_string(&self) -> Result<String> {
        self.validate()?;
        let resolved_workloads = self.resolved_workload_family()?;

        Ok(format!(
            concat!(
                "ExperimentConfig(\n",
                "  suite_name='{}',\n",
                "  replications={},\n",
                "  max_time={}, warmup_time={}, observed_time={},\n",
                "  servers_n={}, capacity_k={}, total_resource_r={},\n",
                "  arrival_rate_levels={:?},\n",
                "  service_speed_levels={:?},\n",
                "  workload_family_profile={:?},\n",
                "  resolved_workload_family={:?},\n",
                "  arrival_process_family={:?},\n",
                "  mean_workload={}\n",
                ")"
            ),
            self.suite_name,
            self.replications,
            self.max_time,
            self.warmup_time,
            self.observed_time(),
            self.servers_n,
            self.capacity_k(),
            self.total_resource_r,
            self.arrival_rate_levels,
            self.service_speed_levels,
            self.workload_family_profile,
            resolved_workloads,
            self.arrival_process_family,
            self.mean_workload,
        ))
    }
}