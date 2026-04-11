use crate::cli::BackendKind;
use crate::scenario_grid::ScenarioSpec;
use crate::stats::{RunSummary, StatsError};
use thiserror::Error;

#[cfg(feature = "cpu-ref")]
pub mod cpu_ref;

#[cfg(feature = "gpu")]
pub mod gpu;

#[derive(Debug, Error)]
pub enum BackendError {
    #[error("{0}")]
    Validation(String),

    #[error("{0}")]
    NotCompiled(String),

    #[error("{0}")]
    NotImplemented(String),

    #[error(transparent)]
    Stats(#[from] StatsError),
}

pub type Result<T> = std::result::Result<T, BackendError>;

/// Один конкретный запуск:
/// - конкретный сценарий,
/// - конкретный replication_index,
/// - конкретный seed.
#[derive(Debug, Clone)]
pub struct RunRequest {
    pub scenario: ScenarioSpec,
    pub replication_index: usize,
    pub seed: u64,
}

impl RunRequest {
    pub fn scenario_key(&self) -> &str {
        &self.scenario.scenario_key
    }

    pub fn scenario_name(&self) -> &str {
        &self.scenario.scenario_name
    }
}

/// Общий интерфейс вычислительного backend-а.
/// Вся верхняя логика проекта работает только с этим trait.
pub trait SimulationBackend: Send + Sync {
    fn kind(&self) -> &'static str;

    fn execute_batch(&self, requests: &[RunRequest]) -> Result<Vec<RunSummary>>;
}

/// Формула seed по replication_index.
/// Совместима по духу с вашей старой CPU-веткой.
pub fn derive_run_seed(base_seed: u64, replication_index: usize) -> u64 {
    base_seed.wrapping_add(1_000_003u64.wrapping_mul(replication_index as u64))
}

/// Построить полный список запусков по всем сценариям и их репликациям.
pub fn build_run_requests(scenarios: &[ScenarioSpec]) -> Vec<RunRequest> {
    let mut requests = Vec::new();

    for scenario in scenarios {
        for replication_index in 0..scenario.replications {
            requests.push(RunRequest {
                scenario: scenario.clone(),
                replication_index,
                seed: derive_run_seed(scenario.base_seed, replication_index),
            });
        }
    }

    requests
}

/// Создать backend по выбранному типу.
pub fn create_backend(kind: BackendKind) -> Result<Box<dyn SimulationBackend>> {
    match kind {
        BackendKind::CpuRef => {
            #[cfg(feature = "cpu-ref")]
            {
                Ok(Box::new(cpu_ref::CpuRefBackend::new()))
            }

            #[cfg(not(feature = "cpu-ref"))]
            {
                Err(BackendError::NotCompiled(
                    "CPU reference backend не собран: включите feature 'cpu-ref'".to_string(),
                ))
            }
        }

        BackendKind::Gpu => {
            #[cfg(feature = "gpu")]
            {
                Ok(Box::new(gpu::GpuBackend::new()?))
            }

            #[cfg(not(feature = "gpu"))]
            {
                Err(BackendError::NotCompiled(
                    "GPU backend не собран: включите feature 'gpu'".to_string(),
                ))
            }
        }
    }
}