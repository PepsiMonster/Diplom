use crate::cli::ScenarioFamily;
use crate::params::{
    ArrivalProcessKind, ArrivalProcessSpec, ExperimentConfig, ParamsError, ResourceDistributionSpec,
    WorkloadDistributionSpec, WorkloadKind,
};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ScenarioGridError {
    #[error("{0}")]
    Validation(String),

    #[error(transparent)]
    Params(#[from] ParamsError),
}

pub type Result<T> = std::result::Result<T, ScenarioGridError>;

/// Полностью развернутый сценарий.
/// Это уже не внешний конфиг серии, а конкретная точка в сетке:
/// - один тип входящего потока,
/// - одно распределение workload,
/// - один уровень lambda,
/// - один уровень sigma.
#[derive(Debug, Clone)]
pub struct ScenarioSpec {
    pub family: ScenarioFamily,
    pub scenario_key: String,
    pub scenario_name: String,

    pub arrival_kind: ArrivalProcessKind,
    pub arrival_spec: ArrivalProcessSpec,

    pub workload_kind: WorkloadKind,
    pub workload_spec: WorkloadDistributionSpec,

    pub arrival_rate: f64,
    pub service_speed: f64,

    pub servers_n: usize,
    pub capacity_k: usize,
    pub total_resource_r: u32,
    pub resource_distribution: ResourceDistributionSpec,

    pub replications: usize,
    pub max_time: f64,
    pub warmup_time: f64,
    pub base_seed: u64,

    pub mean_workload: f64,
}

impl ScenarioSpec {
    pub fn observed_time(&self) -> f64 {
        self.max_time - self.warmup_time
    }

    pub fn short_description(&self) -> String {
        format!(
            concat!(
                "ScenarioSpec(",
                "key='{}', family={:?}, arrival={}, workload={}, ",
                "lambda={}, sigma={}, N={}, K={}, R={}, replications={}",
                ")"
            ),
            self.scenario_key,
            self.family,
            self.arrival_kind.as_str(),
            self.workload_kind.as_str(),
            self.arrival_rate,
            self.service_speed,
            self.servers_n,
            self.capacity_k,
            self.total_resource_r,
            self.replications,
        )
    }
}

/// Результат построения сетки сценариев.
#[derive(Debug, Clone)]
pub struct ScenarioGrid {
    pub family: ScenarioFamily,
    pub scenarios: Vec<ScenarioSpec>,
}

impl ScenarioGrid {
    pub fn len(&self) -> usize {
        self.scenarios.len()
    }

    pub fn is_empty(&self) -> bool {
        self.scenarios.is_empty()
    }

    pub fn scenario_keys(&self) -> Vec<&str> {
        self.scenarios.iter().map(|s| s.scenario_key.as_str()).collect()
    }

    pub fn summary_string(&self) -> String {
        let preview: Vec<&str> = self
            .scenarios
            .iter()
            .take(5)
            .map(|s| s.scenario_key.as_str())
            .collect();

        if self.scenarios.is_empty() {
            format!("ScenarioGrid(family={:?}, scenarios=0)", self.family)
        } else {
            format!(
                "ScenarioGrid(family={:?}, scenarios={}, preview={:?})",
                self.family,
                self.scenarios.len(),
                preview
            )
        }
    }
}

/// Построить сетку сценариев из конфига серии и выбранного семейства.
pub fn build_scenario_grid(
    config: &ExperimentConfig,
    family: ScenarioFamily,
) -> Result<ScenarioGrid> {
    config.validate()?;

    let scenarios = match family {
        ScenarioFamily::Base => build_base_scenarios(config)?,
        ScenarioFamily::WorkloadSensitivity => build_workload_sensitivity_scenarios(config)?,
        ScenarioFamily::ArrivalSensitivity => build_arrival_sensitivity_scenarios(config)?,
        ScenarioFamily::CombinedSensitivity => build_combined_sensitivity_scenarios(config)?,
    };

    if scenarios.is_empty() {
        return Err(ScenarioGridError::Validation(
            "После построения сетка сценариев оказалась пустой".to_string(),
        ));
    }

    Ok(ScenarioGrid { family, scenarios })
}

fn build_base_scenarios(config: &ExperimentConfig) -> Result<Vec<ScenarioSpec>> {
    let workload_kind = first_resolved_workload(config)?;
    let arrival_kind = first_arrival_kind(config)?;

    let mut scenarios = Vec::new();
    for &arrival_rate in &config.arrival_rate_levels {
        for &service_speed in &config.service_speed_levels {
            scenarios.push(build_scenario_spec(
                config,
                ScenarioFamily::Base,
                workload_kind,
                arrival_kind,
                arrival_rate,
                service_speed,
            )?);
        }
    }

    Ok(scenarios)
}

fn build_workload_sensitivity_scenarios(config: &ExperimentConfig) -> Result<Vec<ScenarioSpec>> {
    let workloads = config.resolved_workload_family()?;
    let arrival_kind = first_arrival_kind(config)?;

    let mut scenarios = Vec::new();
    for workload_kind in workloads {
        for &arrival_rate in &config.arrival_rate_levels {
            for &service_speed in &config.service_speed_levels {
                scenarios.push(build_scenario_spec(
                    config,
                    ScenarioFamily::WorkloadSensitivity,
                    workload_kind,
                    arrival_kind,
                    arrival_rate,
                    service_speed,
                )?);
            }
        }
    }

    Ok(scenarios)
}

fn build_arrival_sensitivity_scenarios(config: &ExperimentConfig) -> Result<Vec<ScenarioSpec>> {
    let workload_kind = fixed_or_first_workload(config)?;
    let arrival_kinds = &config.arrival_process_family;

    let mut scenarios = Vec::new();
    for &arrival_kind in arrival_kinds {
        for &arrival_rate in &config.arrival_rate_levels {
            for &service_speed in &config.service_speed_levels {
                scenarios.push(build_scenario_spec(
                    config,
                    ScenarioFamily::ArrivalSensitivity,
                    workload_kind,
                    arrival_kind,
                    arrival_rate,
                    service_speed,
                )?);
            }
        }
    }

    Ok(scenarios)
}

fn build_combined_sensitivity_scenarios(config: &ExperimentConfig) -> Result<Vec<ScenarioSpec>> {
    let workloads = config.resolved_workload_family()?;
    let arrival_kinds = &config.arrival_process_family;

    let mut scenarios = Vec::new();
    for workload_kind in workloads {
        for &arrival_kind in arrival_kinds {
            for &arrival_rate in &config.arrival_rate_levels {
                for &service_speed in &config.service_speed_levels {
                    scenarios.push(build_scenario_spec(
                        config,
                        ScenarioFamily::CombinedSensitivity,
                        workload_kind,
                        arrival_kind,
                        arrival_rate,
                        service_speed,
                    )?);
                }
            }
        }
    }

    Ok(scenarios)
}

fn build_scenario_spec(
    config: &ExperimentConfig,
    family: ScenarioFamily,
    workload_kind: WorkloadKind,
    arrival_kind: ArrivalProcessKind,
    arrival_rate: f64,
    service_speed: f64,
) -> Result<ScenarioSpec> {
    let workload_spec = config.build_workload_spec(workload_kind)?;
    let arrival_spec = config.build_arrival_spec(arrival_kind)?;
    let resource_distribution = config.resource_distribution();

    let scenario_key = make_scenario_key(
        family,
        arrival_kind,
        workload_kind,
        arrival_rate,
        service_speed,
    );

    let scenario_name = make_scenario_name(
        family,
        arrival_kind,
        workload_kind,
        arrival_rate,
        service_speed,
    );

    Ok(ScenarioSpec {
        family,
        scenario_key,
        scenario_name,
        arrival_kind,
        arrival_spec,
        workload_kind,
        workload_spec,
        arrival_rate,
        service_speed,
        servers_n: config.servers_n,
        capacity_k: config.capacity_k(),
        total_resource_r: config.total_resource_r,
        resource_distribution,
        replications: config.replications,
        max_time: config.max_time,
        warmup_time: config.warmup_time,
        base_seed: config.base_seed,
        mean_workload: config.mean_workload,
    })
}

fn first_resolved_workload(config: &ExperimentConfig) -> Result<WorkloadKind> {
    let workloads = config.resolved_workload_family()?;
    workloads.first().copied().ok_or_else(|| {
        ScenarioGridError::Validation(
            "Не удалось выбрать первый workload из resolved_workload_family".to_string(),
        )
    })
}

fn fixed_or_first_workload(config: &ExperimentConfig) -> Result<WorkloadKind> {
    match config.workload_family_profile {
        crate::params::WorkloadFamilyProfile::Fixed => Ok(config.fixed_workload),
        _ => first_resolved_workload(config),
    }
}

fn first_arrival_kind(config: &ExperimentConfig) -> Result<ArrivalProcessKind> {
    config.arrival_process_family.first().copied().ok_or_else(|| {
        ScenarioGridError::Validation(
            "arrival_process_family не должен быть пустым".to_string(),
        )
    })
}

fn make_scenario_key(
    family: ScenarioFamily,
    arrival_kind: ArrivalProcessKind,
    workload_kind: WorkloadKind,
    arrival_rate: f64,
    service_speed: f64,
) -> String {
    format!(
        "{}__arr-{}__work-{}__lam-{}__sig-{}",
        family_slug(family),
        arrival_kind.as_str(),
        workload_kind.as_str(),
        float_slug(arrival_rate),
        float_slug(service_speed),
    )
}

fn make_scenario_name(
    family: ScenarioFamily,
    arrival_kind: ArrivalProcessKind,
    workload_kind: WorkloadKind,
    arrival_rate: f64,
    service_speed: f64,
) -> String {
    format!(
        "{:?}: arrival={}, workload={}, lambda={}, sigma={}",
        family,
        arrival_kind.as_str(),
        workload_kind.as_str(),
        arrival_rate,
        service_speed,
    )
}

fn family_slug(family: ScenarioFamily) -> &'static str {
    match family {
        ScenarioFamily::Base => "base",
        ScenarioFamily::WorkloadSensitivity => "workload",
        ScenarioFamily::ArrivalSensitivity => "arrival",
        ScenarioFamily::CombinedSensitivity => "combined",
    }
}

/// Превратить число в безопасный slug для имени сценария.
/// Например:
/// 82.2  -> "82p2"
/// 70.0  -> "70"
/// 1.25  -> "1p25"
fn float_slug(value: f64) -> String {
    let mut s = format!("{value:.6}");

    while s.contains('.') && s.ends_with('0') {
        s.pop();
    }
    if s.ends_with('.') {
        s.pop();
    }

    s.replace('-', "m").replace('.', "p")
}