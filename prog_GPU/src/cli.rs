use clap::{Args, Parser, Subcommand, ValueEnum};
use std::path::PathBuf;

/// Какое семейство сценариев строить из внешней конфигурации.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ScenarioFamily {
    /// Базовый режим: один workload x один arrival process x уровни lambda/sigma.
    Base,

    /// Чувствительность к распределению обслуживания.
    WorkloadSensitivity,

    /// Чувствительность к типу входящего потока.
    ArrivalSensitivity,

    /// Совместная чувствительность и к workload, и к arrival process.
    CombinedSensitivity,
}

/// Какой backend использовать для вычислений.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum BackendKind {
    /// Референсный CPU-backend для проверки корректности и отладки.
    CpuRef,

    /// Основной GPU-backend.
    Gpu,
}

/// Общие аргументы, которые нужны большинству команд.
#[derive(Debug, Clone, Args)]
pub struct CommonArgs {
    /// Путь к JSON-конфигу, который экспортирует Python-часть проекта.
    #[arg(long, default_value = "py/generated/experiment_values.json")]
    pub input: PathBuf,

    /// Семейство сценариев, которое нужно построить.
    #[arg(long, value_enum, default_value_t = ScenarioFamily::Base)]
    pub scenario_family: ScenarioFamily,

    /// Корневая папка для результатов.
    #[arg(long, default_value = "results")]
    pub output_root: PathBuf,

    /// Опционально переопределить имя серии экспериментов.
    #[arg(long)]
    pub suite_name: Option<String>,

    /// Опционально переопределить число повторов каждого сценария.
    #[arg(long)]
    pub replications: Option<usize>,

    /// Опционально переопределить полное время моделирования.
    #[arg(long)]
    pub max_time: Option<f64>,

    /// Опционально переопределить длину warm-up.
    #[arg(long)]
    pub warmup_time: Option<f64>,
}

/// Полный запуск: чтение конфига, построение сетки сценариев,
/// расчёт, агрегация и сохранение результатов.
#[derive(Debug, Clone, Args)]
pub struct FullArgs {
    #[command(flatten)]
    pub common: CommonArgs,

    /// Какой backend использовать.
    #[arg(long, value_enum, default_value_t = BackendKind::CpuRef)]
    pub backend: BackendKind,

    /// Уровень доверия для доверительных интервалов.
    #[arg(long, default_value_t = 0.95)]
    pub ci_level: f64,

    /// Сохранить per-run таблицу/JSON с краткими итогами по каждому прогону.
    #[arg(long, default_value_t = true)]
    pub save_run_summaries: bool,

    /// Сохранить агрегированные таблицы по сценариям.
    #[arg(long, default_value_t = true)]
    pub save_metric_tables: bool,
}

/// Только проверка конфигурации и печать краткой сводки без запуска экспериментов.
#[derive(Debug, Clone, Args)]
pub struct ValidateConfigArgs {
    #[arg(long, default_value = "py/generated/experiment_values.json")]
    pub input: PathBuf,
}

/// Построить и вывести список сценариев без запуска вычислений.
#[derive(Debug, Clone, Args)]
pub struct ListScenariosArgs {
    #[command(flatten)]
    pub common: CommonArgs,
}

/// Запуск только расчёта серии без построения графиков.
/// По смыслу близко к Full, но без дополнительных шагов постобработки.
#[derive(Debug, Clone, Args)]
pub struct SuiteArgs {
    #[command(flatten)]
    pub common: CommonArgs,

    #[arg(long, value_enum, default_value_t = BackendKind::CpuRef)]
    pub backend: BackendKind,

    #[arg(long, default_value_t = 0.95)]
    pub ci_level: f64,
}

/// Аргументы верхнего уровня CLI.
#[derive(Debug, Parser)]
#[command(
    name = "prog_files_rust_gpu",
    version,
    about = "GPU-oriented pipeline для серии имитационных экспериментов"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

/// Поддерживаемые команды.
#[derive(Debug, Subcommand)]
pub enum Commands {
    /// Полный pipeline: конфиг -> сценарии -> backend -> агрегация -> сохранение.
    Full(FullArgs),

    /// Только серия экспериментов без дополнительных шагов постобработки.
    Suite(SuiteArgs),

    /// Проверить конфигурацию и вывести краткую сводку.
    ValidateConfig(ValidateConfigArgs),

    /// Построить и показать список сценариев без запуска вычислений.
    ListScenarios(ListScenariosArgs),
}

/// Удобная обёртка, чтобы в других модулях не тянуть clap::Parser напрямую.
pub fn parse_cli() -> Cli {
    Cli::parse()
}