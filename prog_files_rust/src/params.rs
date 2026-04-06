use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ParamsError {
    #[error("{0}")]
    Validation(String),
}

type Result<T> = std::result::Result<T, ParamsError>;

pub const DEFAULT_EXTERNAL_EXPERIMENT_VALUES_PATH: &str =
    "py/generated/experiment_values.json";

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SystemArchitecture {
    Loss,
    Buffer,
}

impl Default for SystemArchitecture {
    fn default() -> Self {
        Self::Loss
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalExperimentValues {
    pub suite_name: String,
    pub mean_workload: f64,
    pub replications: usize,
    pub max_time: f64,
    pub warmup_time: f64,
    pub base_seed: u64,
    #[serde(default)]
    pub record_state_trace: bool,
    #[serde(default)]
    pub save_event_log: bool,
    #[serde(default)]
    pub keep_full_run_results: bool,
    #[serde(default)]
    pub animation_log_max_jobs: usize,
    #[serde(default = "default_full_run_results_per_scenario")]
    pub full_run_results_per_scenario: usize,
    #[serde(default)]
    pub system_architecture: SystemArchitecture,
    #[serde(default)]
    pub queue_capacity: usize,

    pub capacity_k: usize,
    pub servers_n: usize,
    pub total_resource_r: u32,

    pub arrival_normal_value: f64,
    pub arrival_threshold_offset: usize,
    pub arrival_reduced_value: f64,
    pub arrival_full_state_value: f64,

    pub service_start_value: f64,
    pub service_step: f64,
    pub service_floor_value: f64,

    pub resource_values: Vec<u32>,
    pub resource_probabilities: Vec<f64>,

    pub workload_family: Vec<String>,
    pub workload_hyperexp_p: f64,
    pub workload_hyperexp_fast_multiplier: f64,
    pub workload_hyperexp_heavy_p: f64,
    pub workload_hyperexp_heavy_fast_multiplier: f64,

    pub arrival_process_family: Vec<String>,
}

pub fn load_external_experiment_values(path: impl AsRef<Path>) -> Result<ExternalExperimentValues> {
    let text = fs::read_to_string(path).map_err(|e| {
        ParamsError::Validation(format!(
            "Не удалось прочитать файл внешних параметров: {e}"
        ))
    })?;

    let values: ExternalExperimentValues = serde_json::from_str(&text).map_err(|e| {
        ParamsError::Validation(format!(
            "Не удалось распарсить JSON внешних параметров: {e}"
        ))
    })?;

    Ok(values)
}

pub fn load_default_external_experiment_values() -> Result<ExternalExperimentValues> {
    load_external_experiment_values(DEFAULT_EXTERNAL_EXPERIMENT_VALUES_PATH)
}

fn default_full_run_results_per_scenario() -> usize {
    3
}

fn ensure_positive_f64(name: &str, value: f64) -> Result<()> {
    if value <= 0.0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть > 0, получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_nonnegative_f64(name: &str, value: f64) -> Result<()> {
    if value < 0.0 {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен быть >= 0, получено: {value}"
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
    if !(0.0 < value && value < 1.0) {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен лежать в интервале (0, 1), получено: {value}"
        )));
    }
    Ok(())
}

fn ensure_vec_length<T>(name: &str, values: &[T], expected: usize) -> Result<()> {
    if values.len() != expected {
        return Err(ParamsError::Validation(format!(
            "Параметр '{name}' должен иметь длину {expected}, получено {}",
            values.len()
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub max_time: f64,
    pub warmup_time: f64,
    pub seed: u64,
    pub replications: usize,
    pub time_epsilon: f64,
    pub record_state_trace: bool,
    pub save_event_log: bool,
    pub animation_log_max_jobs: usize,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            max_time: 100_000.0,
            warmup_time: 10_000.0,
            seed: 42,
            replications: 10,
            time_epsilon: 1e-12,
            record_state_trace: false,
            save_event_log: false,
            animation_log_max_jobs: 0,
        }
    }
}

impl SimulationConfig {
    pub fn validate(&self) -> Result<()> {
        ensure_positive_f64("max_time", self.max_time)?;
        ensure_nonnegative_f64("warmup_time", self.warmup_time)?;
        ensure_positive_usize("replications", self.replications)?;
        ensure_positive_f64("time_epsilon", self.time_epsilon)?;

        if self.warmup_time >= self.max_time {
            return Err(ParamsError::Validation(format!(
                "warmup_time должен быть строго меньше max_time, получено warmup_time={}, max_time={}",
                self.warmup_time, self.max_time
            )));
        }

        Ok(())
    }

    pub fn effective_observation_time(&self) -> f64 {
        self.max_time - self.warmup_time
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ResourceDistributionConfig {
    Deterministic {
        deterministic_value: u32,
    },
    DiscreteUniform {
        min_units: u32,
        max_units: u32,
    },
    DiscreteCustom {
        values: Vec<u32>,
        probabilities: Vec<f64>,
    },
}

impl ResourceDistributionConfig {
    pub fn validate(&self) -> Result<()> {
        match self {
            Self::Deterministic {
                deterministic_value,
            } => {
                ensure_positive_u32("deterministic_value", *deterministic_value)?;
            }
            Self::DiscreteUniform {
                min_units,
                max_units,
            } => {
                ensure_positive_u32("min_units", *min_units)?;
                ensure_positive_u32("max_units", *max_units)?;
                if min_units > max_units {
                    return Err(ParamsError::Validation(
                        "min_units не может быть больше max_units".to_string(),
                    ));
                }
            }
            Self::DiscreteCustom {
                values,
                probabilities,
            } => {
                if values.is_empty() {
                    return Err(ParamsError::Validation(
                        "Для discrete_custom нужно задать values".to_string(),
                    ));
                }
                if probabilities.is_empty() {
                    return Err(ParamsError::Validation(
                        "Для discrete_custom нужно задать probabilities".to_string(),
                    ));
                }
                if values.len() != probabilities.len() {
                    return Err(ParamsError::Validation(
                        "Длины values и probabilities должны совпадать".to_string(),
                    ));
                }

                for (i, value) in values.iter().enumerate() {
                    ensure_positive_u32(&format!("values[{i}]"), *value)?;
                }
                for (i, prob) in probabilities.iter().enumerate() {
                    ensure_probability(&format!("probabilities[{i}]"), *prob)?;
                }
                ensure_probabilities_sum_to_one("probabilities", probabilities, 1e-10)?;
            }
        }
        Ok(())
    }

    pub fn mean(&self) -> Result<f64> {
        self.validate()?;
        let mean = match self {
            Self::Deterministic {
                deterministic_value,
            } => *deterministic_value as f64,
            Self::DiscreteUniform {
                min_units,
                max_units,
            } => 0.5 * (*min_units as f64 + *max_units as f64),
            Self::DiscreteCustom {
                values,
                probabilities,
            } => values
                .iter()
                .zip(probabilities.iter())
                .map(|(v, p)| *v as f64 * *p)
                .sum(),
        };
        Ok(mean)
    }

    pub fn short_label(&self) -> String {
        match self {
            Self::Deterministic {
                deterministic_value,
            } => {
                format!("ResourceDet({deterministic_value})")
            }
            Self::DiscreteUniform {
                min_units,
                max_units,
            } => format!("ResourceDU({min_units},{max_units})"),
            Self::DiscreteCustom { .. } => "ResourceCustom".to_string(),
        }
    }

    pub fn min_possible_units(&self) -> u32 {
        match self {
            Self::Deterministic {
                deterministic_value,
            } => *deterministic_value,
            Self::DiscreteUniform { min_units, .. } => *min_units,
            Self::DiscreteCustom { values, .. } => *values.iter().min().unwrap_or(&u32::MAX),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WorkloadDistributionConfig {
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
        label: String,
        erlang_order: usize,
    },
    Hyperexponential2 {
        mean: f64,
        label: String,
        hyper_p: f64,
        hyper_rates: [f64; 2],
    },
}

impl WorkloadDistributionConfig {
    pub fn validate(&self) -> Result<()> {
        match self {
            Self::Deterministic { mean, .. } | Self::Exponential { mean, .. } => {
                ensure_positive_f64("mean", *mean)?;
            }
            Self::Erlang {
                mean, erlang_order, ..
            } => {
                ensure_positive_f64("mean", *mean)?;
                ensure_positive_usize("erlang_order", *erlang_order)?;
            }
            Self::Hyperexponential2 {
                mean,
                hyper_p,
                hyper_rates,
                ..
            } => {
                ensure_positive_f64("mean", *mean)?;
                ensure_probability("hyper_p", *hyper_p)?;
                ensure_positive_f64("hyper_rates[0]", hyper_rates[0])?;
                ensure_positive_f64("hyper_rates[1]", hyper_rates[1])?;

                let implied_mean = *hyper_p / hyper_rates[0] + (1.0 - *hyper_p) / hyper_rates[1];
                if (implied_mean - *mean).abs() > 1e-9 {
                    return Err(ParamsError::Validation(format!(
                        "Параметры hyperexponential2 неконсистентны: заданное mean={}, а из параметров смеси получается {}",
                        mean, implied_mean
                    )));
                }
            }
        }
        Ok(())
    }

    pub fn mean(&self) -> f64 {
        match self {
            Self::Deterministic { mean, .. }
            | Self::Exponential { mean, .. }
            | Self::Erlang { mean, .. }
            | Self::Hyperexponential2 { mean, .. } => *mean,
        }
    }

    pub fn label(&self) -> &str {
        match self {
            Self::Deterministic { label, .. }
            | Self::Exponential { label, .. }
            | Self::Erlang { label, .. }
            | Self::Hyperexponential2 { label, .. } => label,
        }
    }

    pub fn implied_mean(&self) -> f64 {
        match self {
            Self::Deterministic { mean, .. }
            | Self::Exponential { mean, .. }
            | Self::Erlang { mean, .. } => *mean,
            Self::Hyperexponential2 {
                hyper_p,
                hyper_rates,
                ..
            } => *hyper_p / hyper_rates[0] + (1.0 - *hyper_p) / hyper_rates[1],
        }
    }

    pub fn short_label(&self) -> String {
        self.label().replace(' ', "_")
    }

    pub fn deterministic(mean: f64, label: impl Into<String>) -> Result<Self> {
        let cfg = Self::Deterministic {
            mean,
            label: label.into(),
        };
        cfg.validate()?;
        Ok(cfg)
    }

    pub fn exponential(mean: f64, label: impl Into<String>) -> Result<Self> {
        let cfg = Self::Exponential {
            mean,
            label: label.into(),
        };
        cfg.validate()?;
        Ok(cfg)
    }

    pub fn erlang(mean: f64, order: usize, label: Option<String>) -> Result<Self> {
        let cfg = Self::Erlang {
            mean,
            label: label.unwrap_or_else(|| format!("Erlang({order})")),
            erlang_order: order,
        };
        cfg.validate()?;
        Ok(cfg)
    }

    pub fn hyperexponential2(
        mean: f64,
        p: f64,
        fast_rate_multiplier: f64,
        label: impl Into<String>,
    ) -> Result<Self> {
        ensure_positive_f64("mean", mean)?;
        ensure_probability("p", p)?;
        ensure_positive_f64("fast_rate_multiplier", fast_rate_multiplier)?;

        let rate_1 = fast_rate_multiplier / mean;
        let denominator = mean - p / rate_1;
        if denominator <= 0.0 {
            return Err(ParamsError::Validation(
                "Не удалось построить hyperexponential2: выбранные p и fast_rate_multiplier дают некорректную вторую интенсивность. Попробуй увеличить fast_rate_multiplier."
                    .to_string(),
            ));
        }
        let rate_2 = (1.0 - p) / denominator;

        let cfg = Self::Hyperexponential2 {
            mean,
            label: label.into(),
            hyper_p: p,
            hyper_rates: [rate_1, rate_2],
        };
        cfg.validate()?;
        Ok(cfg)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioConfig {
    pub name: String,
    pub system_architecture: SystemArchitecture,
    pub capacity_k: usize,
    pub servers_n: usize,
    pub total_resource_r: u32,
    pub arrival_rate_by_state: Vec<f64>,
    pub service_speed_by_state: Vec<f64>,
    pub resource_distribution: ResourceDistributionConfig,
    pub workload_distribution: WorkloadDistributionConfig,
    pub simulation: SimulationConfig,
    pub note: String,
}

impl ScenarioConfig {
    pub fn queue_capacity(&self) -> usize {
        self.capacity_k.saturating_sub(self.servers_n)
    }

    pub fn validate(&self) -> Result<()> {
        ensure_positive_usize("capacity_k", self.capacity_k)?;
        ensure_positive_usize("servers_n", self.servers_n)?;
        ensure_positive_u32("total_resource_r", self.total_resource_r)?;

        let expected_len = self.capacity_k + 1;
        ensure_vec_length(
            "arrival_rate_by_state",
            &self.arrival_rate_by_state,
            expected_len,
        )?;
        ensure_vec_length(
            "service_speed_by_state",
            &self.service_speed_by_state,
            expected_len,
        )?;

        for (k, value) in self.arrival_rate_by_state.iter().enumerate() {
            ensure_nonnegative_f64(&format!("arrival_rate_by_state[{k}]"), *value)?;
        }
        for (k, value) in self.service_speed_by_state.iter().enumerate() {
            ensure_nonnegative_f64(&format!("service_speed_by_state[{k}]"), *value)?;
        }

        self.resource_distribution.validate()?;
        self.workload_distribution.validate()?;
        self.simulation.validate()?;

        match self.system_architecture {
            SystemArchitecture::Loss => {
                if self.capacity_k != self.servers_n {
                    return Err(ParamsError::Validation(format!(
                        "Для архитектуры loss требуется capacity_k == servers_n. Сейчас capacity_k={}, servers_n={}",
                        self.capacity_k, self.servers_n
                    )));
                }
            }
            SystemArchitecture::Buffer => {
                if self.capacity_k <= self.servers_n {
                    return Err(ParamsError::Validation(format!(
                        "Для архитектуры buffer требуется capacity_k > servers_n. Сейчас capacity_k={}, servers_n={}",
                        self.capacity_k, self.servers_n
                    )));
                }
            }
        }

        if self.resource_distribution.min_possible_units() > self.total_resource_r {
            return Err(ParamsError::Validation(
                "Даже минимально возможное требование к ресурсу превышает total_resource_r: система не сможет принять ни одной заявки."
                    .to_string(),
            ));
        }

        Ok(())
    }

    pub fn short_description(&self) -> String {
        let lambda_full = self.arrival_rate_by_state.last().copied().unwrap_or(0.0);
        let warning = if lambda_full != 0.0 {
            " [ВНИМАНИЕ: lambda_K != 0]"
        } else {
            ""
        };

        format!(
            "Scenario(name='{}', arch={:?}, K={}, N={}, Q={}, R={}, resource='{}', work='{}', replications={}){}",
            self.name,
            self.system_architecture,
            self.capacity_k,
            self.servers_n,
            self.queue_capacity(),
            self.total_resource_r,
            self.resource_distribution.short_label(),
            self.workload_distribution.short_label(),
            self.simulation.replications,
            warning
        )
    }

    pub fn summary_string(&self) -> Result<String> {
        self.validate()?;

        let mut s = String::new();
        s.push_str(&format!("{}\n", "=".repeat(80)));
        s.push_str(&format!("СЦЕНАРИЙ: {}\n", self.name));
        s.push_str(&format!("{}\n", "-".repeat(80)));
        s.push_str(&format!(
            "K (ёмкость системы):                  {}\n",
            self.capacity_k
        ));
        s.push_str(&format!(
            "Архитектура:                          {:?}\n",
            self.system_architecture
        ));
        s.push_str(&format!(
            "N (число приборов):                  {}\n",
            self.servers_n
        ));
        s.push_str(&format!(
            "Q (ёмкость очереди):                  {}\n",
            self.queue_capacity()
        ));
        s.push_str(&format!(
            "R (общий ресурс):                    {}\n",
            self.total_resource_r
        ));
        s.push_str(&format!(
            "Распределение ресурса:               {}\n",
            self.resource_distribution.short_label()
        ));
        s.push_str(&format!(
            "Среднее требование к ресурсу:        {:.4}\n",
            self.resource_distribution.mean()?
        ));
        s.push_str(&format!(
            "Распределение объёма работы:         {}\n",
            self.workload_distribution.label()
        ));
        s.push_str(&format!(
            "Средний объём работы:                {:.4}\n",
            self.workload_distribution.mean()
        ));
        s.push_str(&format!(
            "Время моделирования:                 {}\n",
            self.simulation.max_time
        ));
        s.push_str(&format!(
            "Warm-up:                             {}\n",
            self.simulation.warmup_time
        ));
        s.push_str(&format!(
            "Эффективное время наблюдения:        {}\n",
            self.simulation.effective_observation_time()
        ));
        s.push_str(&format!(
            "Число повторов:                      {}\n",
            self.simulation.replications
        ));
        s.push_str(&format!(
            "Seed:                                {}\n",
            self.simulation.seed
        ));
        s.push_str(&format!(
            "Комментарий:                         {}\n",
            self.note
        ));
        s.push_str(&format!("{}\n", "-".repeat(80)));
        s.push_str("Профиль lambda_k:\n");
        s.push_str(&format!("  {:?}\n", self.arrival_rate_by_state));
        s.push_str("Профиль sigma_k:\n");
        s.push_str(&format!("  {:?}\n", self.service_speed_by_state));
        s.push_str(&format!("{}\n", "=".repeat(80)));

        Ok(s)
    }
}

pub fn constant_profile(
    capacity_k: usize,
    value: f64,
    last_value: Option<f64>,
) -> Result<Vec<f64>> {
    ensure_positive_usize("capacity_k", capacity_k)?;
    ensure_nonnegative_f64("value", value)?;

    let mut values = vec![value; capacity_k + 1];
    if let Some(v) = last_value {
        ensure_nonnegative_f64("last_value", v)?;
        if let Some(last) = values.last_mut() {
            *last = v;
        }
    }
    Ok(values)
}

pub fn threshold_profile(
    capacity_k: usize,
    normal_value: f64,
    threshold_k: usize,
    reduced_value: f64,
    full_state_value: f64,
) -> Result<Vec<f64>> {
    ensure_positive_usize("capacity_k", capacity_k)?;
    ensure_nonnegative_f64("normal_value", normal_value)?;
    ensure_nonnegative_f64("reduced_value", reduced_value)?;
    ensure_nonnegative_f64("full_state_value", full_state_value)?;

    if threshold_k > capacity_k {
        return Err(ParamsError::Validation(format!(
            "threshold_k должен лежать в диапазоне [0, {capacity_k}], получено: {threshold_k}"
        )));
    }

    let mut profile = Vec::with_capacity(capacity_k + 1);
    for k in 0..=capacity_k {
        if k < threshold_k {
            profile.push(normal_value);
        } else {
            profile.push(reduced_value);
        }
    }

    if let Some(last) = profile.last_mut() {
        *last = full_state_value;
    }

    Ok(profile)
}

pub fn linear_decreasing_profile(
    capacity_k: usize,
    start_value: f64,
    step: f64,
    floor_value: f64,
) -> Result<Vec<f64>> {
    ensure_positive_usize("capacity_k", capacity_k)?;
    ensure_nonnegative_f64("start_value", start_value)?;
    ensure_nonnegative_f64("step", step)?;
    ensure_nonnegative_f64("floor_value", floor_value)?;

    Ok((0..=capacity_k)
        .map(|k| (start_value - step * k as f64).max(floor_value))
        .collect())
}

pub fn standard_workload_family_from_values(
    values: &ExternalExperimentValues,
) -> Result<BTreeMap<String, WorkloadDistributionConfig>> {
    ensure_positive_f64("mean_workload", values.mean_workload)?;

    let mut family = BTreeMap::new();
    for key in &values.workload_family {
        let workload_cfg = match key.as_str() {
            "deterministic" => WorkloadDistributionConfig::deterministic(
                values.mean_workload,
                "Deterministic",
            )?,
            "exponential" => {
                WorkloadDistributionConfig::exponential(values.mean_workload, "Exponential")?
            }
            "erlang_2" => WorkloadDistributionConfig::erlang(
                values.mean_workload,
                2,
                Some("Erlang(2)".to_string()),
            )?,
            "erlang_4" => WorkloadDistributionConfig::erlang(
                values.mean_workload,
                4,
                Some("Erlang(4)".to_string()),
            )?,
            "erlang_8" => WorkloadDistributionConfig::erlang(
                values.mean_workload,
                8,
                Some("Erlang(8)".to_string()),
            )?,
            "hyperexp_2" => WorkloadDistributionConfig::hyperexponential2(
                values.mean_workload,
                values.workload_hyperexp_p,
                values.workload_hyperexp_fast_multiplier,
                "HyperExp(2)",
            )?,
            "hyperexp_heavy" => WorkloadDistributionConfig::hyperexponential2(
                values.mean_workload,
                values.workload_hyperexp_heavy_p,
                values.workload_hyperexp_heavy_fast_multiplier,
                "HyperExpHeavy",
            )?,
            _ => {
                return Err(ParamsError::Validation(format!(
                    "Неизвестный тип workload_distribution в workload_family: '{key}'"
                )));
            }
        };
        family.insert(key.clone(), workload_cfg);
    }

    Ok(family)
}

pub fn standard_workload_family(mean: f64) -> Result<BTreeMap<String, WorkloadDistributionConfig>> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = mean;
    standard_workload_family_from_values(&values)
}

pub fn build_simulation_config_from_values(
    values: &ExternalExperimentValues,
) -> Result<SimulationConfig> {
    let cfg = SimulationConfig {
        max_time: values.max_time,
        warmup_time: values.warmup_time,
        seed: values.base_seed,
        replications: values.replications,
        record_state_trace: values.record_state_trace,
        save_event_log: values.save_event_log,
        animation_log_max_jobs: values.animation_log_max_jobs,
        ..SimulationConfig::default()
    };
    cfg.validate()?;
    Ok(cfg)
}

pub fn build_base_simulation_config() -> Result<SimulationConfig> {
    let values = load_default_external_experiment_values()?;
    build_simulation_config_from_values(&values)
}

pub fn build_resource_distribution_from_values(
    values: &ExternalExperimentValues,
) -> Result<ResourceDistributionConfig> {
    let cfg = ResourceDistributionConfig::DiscreteCustom {
        values: values.resource_values.clone(),
        probabilities: values.resource_probabilities.clone(),
    };
    cfg.validate()?;
    Ok(cfg)
}

pub fn build_base_resource_distribution() -> Result<ResourceDistributionConfig> {
    let values = load_default_external_experiment_values()?;
    build_resource_distribution_from_values(&values)
}

pub fn build_arrival_profile_from_values(values: &ExternalExperimentValues) -> Result<Vec<f64>> {
    let threshold_k = values
        .capacity_k
        .saturating_sub(values.arrival_threshold_offset);

    threshold_profile(
        values.capacity_k,
        values.arrival_normal_value,
        threshold_k,
        values.arrival_reduced_value,
        values.arrival_full_state_value,
    )
}

pub fn build_base_arrival_profile(capacity_k: usize) -> Result<Vec<f64>> {
    let mut values = load_default_external_experiment_values()?;
    values.capacity_k = capacity_k;
    build_arrival_profile_from_values(&values)
}

pub fn build_service_profile_from_values(values: &ExternalExperimentValues) -> Result<Vec<f64>> {
    linear_decreasing_profile(
        values.capacity_k,
        values.service_start_value,
        values.service_step,
        values.service_floor_value,
    )
}

pub fn build_base_service_profile(capacity_k: usize) -> Result<Vec<f64>> {
    let mut values = load_default_external_experiment_values()?;
    values.capacity_k = capacity_k;
    build_service_profile_from_values(&values)
}

pub fn build_base_scenario_from_values(
    values: &ExternalExperimentValues,
    workload_distribution: WorkloadDistributionConfig,
    name_suffix: &str,
) -> Result<ScenarioConfig> {
    let scenario = ScenarioConfig {
        name: format!("base{name_suffix}"),
        system_architecture: values.system_architecture,
        capacity_k: values.capacity_k,
        servers_n: values.servers_n,
        total_resource_r: values.total_resource_r,
        arrival_rate_by_state: build_arrival_profile_from_values(values)?,
        service_speed_by_state: build_service_profile_from_values(values)?,
        resource_distribution: build_resource_distribution_from_values(values)?,
        workload_distribution,
        simulation: build_simulation_config_from_values(values)?,
        note: "Сценарий, собранный из внешнего Python-конфига.".to_string(),
    };

    scenario.validate()?;
    Ok(scenario)
}

pub fn build_base_scenario(
    workload_distribution: WorkloadDistributionConfig,
    name_suffix: &str,
) -> Result<ScenarioConfig> {
    let values = load_default_external_experiment_values()?;
    build_base_scenario_from_values(&values, workload_distribution, name_suffix)
}

pub fn build_sensitivity_scenarios_from_values(
    values: &ExternalExperimentValues,
) -> Result<BTreeMap<String, ScenarioConfig>> {
    let family = standard_workload_family_from_values(values)?;
    let mut scenarios = BTreeMap::new();

    for (key, workload_cfg) in family {
        let scenario = build_base_scenario_from_values(values, workload_cfg, &format!("_{key}"))?;
        scenarios.insert(key, scenario);
    }

    Ok(scenarios)
}

pub fn build_sensitivity_scenarios(mean_workload: f64) -> Result<BTreeMap<String, ScenarioConfig>> {
    let mut values = load_default_external_experiment_values()?;
    values.mean_workload = mean_workload;
    build_sensitivity_scenarios_from_values(&values)
}

pub fn print_scenario_summary(scenario: &ScenarioConfig) -> Result<()> {
    println!("{}", scenario.summary_string()?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_standard_sensitivity_family() {
        let scenarios = build_sensitivity_scenarios(1.0).unwrap();
        assert_eq!(scenarios.len(), 7);

        for scenario in scenarios.values() {
            scenario.validate().unwrap();
            assert_eq!(
                scenario.arrival_rate_by_state.len(),
                scenario.capacity_k + 1
            );
            assert_eq!(
                scenario.service_speed_by_state.len(),
                scenario.capacity_k + 1
            );
        }
    }

    #[test]
    fn hyperexp_is_mean_consistent() {
        let cfg =
            WorkloadDistributionConfig::hyperexponential2(1.0, 0.75, 4.0, "HyperExp(2)").unwrap();
        cfg.validate().unwrap();
        assert!((cfg.implied_mean() - 1.0).abs() < 1e-9);
    }

    #[test]
    fn threshold_profile_has_zero_at_full_state() {
        let p = build_base_arrival_profile(10).unwrap();
        assert_eq!(p.len(), 11);
        assert_eq!(p[10], 0.0);
    }
}
