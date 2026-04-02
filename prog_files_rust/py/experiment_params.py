from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json



# ====================================
# Базовые параметры имитации (simulation)
# ====================================

# Полное время моделирования. Чем больше, тем устойчивее оценки, но тем дольше расчёт.
SIM_MAX_TIME = 200_000.0

# Длина разогрева. Всё, что до warm-up, не участвует в финальной статистике.
SIM_WARMUP_TIME = 40_000.0

# Базовый seed для генератора случайных чисел. Нужен для воспроизводимости.
SIM_SEED = 42

# Число повторов на сценарий. Именно оно влияет на ширину доверительных интервалов.
SIM_REPLICATIONS = 30

# Численная толерантность для сравнения почти совпадающих событий во времени.
SIM_TIME_EPSILON = 1e-12

# Сохранять ли траекторию состояния системы во времени.
SIM_RECORD_STATE_TRACE = False

# Сохранять ли детальный лог событий.
SIM_SAVE_EVENT_LOG = False

# ======================================
# Базовые параметры ресурсной системы СМО
# ======================================

# Максимальное число заявок в системе.
SCENARIO_CAPACITY_K = 20

# Число обслуживающих приборов / каналов.
SCENARIO_SERVERS_N = 12

# Общий объём ограниченного ресурса.
SCENARIO_TOTAL_RESOURCE_R = 40

# Комментарий к сценарию. Уходит в summary/report и помогает не потерять смысл прогона.
SCENARIO_NOTE = (
    "Базовый напряжённый сценарий для анализа чувствительности "
    "ресурсной СМО к распределению объёма работ."
)


# ========================================
# Параметры профиля интенсивности поступления
# ========================================

# Интенсивность поступления при низкой и средней загрузке.
ARRIVAL_NORMAL_VALUE = 3.20

# Порог по числу заявок, после которого интенсивность снижается.
# None означает: вычислить как K - 4.
ARRIVAL_THRESHOLD_K = None

# Интенсивность поступления при высокой загрузке.
ARRIVAL_REDUCED_VALUE = 2.20

# Интенсивность в полностью заполненном состоянии.
# Обычно 0.0, чтобы при k = K новые внешние поступления не моделировались.
ARRIVAL_FULL_STATE_VALUE = 0.0


# =====================================
# Параметры профиля скорости обслуживания
# =====================================

# Скорость обслуживания при малом числе заявок.
SERVICE_START_VALUE = 1.40

# Линейное снижение скорости на один дополнительный job.
SERVICE_STEP = 0.07

# Нижняя граница скорости обслуживания при перегрузке.
SERVICE_FLOOR_VALUE = 0.35


# =======================================
# Базовое распределение требований к ресурсу
# =======================================

# Возможные значения потребления ресурса заявкой.
RESOURCE_VALUES = [2, 4, 8, 12, 16]

# Вероятности соответствующих resource-demand значений.
RESOURCE_PROBABILITIES = [0.30, 0.30, 0.20, 0.15, 0.05]


# ==================================================
# Базовые параметры семейства распределений обслуживания
# ==================================================

# Средний объём работы одной заявки.
WORKLOAD_MEAN = 1.0

# Параметр p для умеренно вариативного hyperexponential.
WORKLOAD_HYPEREXP_P = 0.75

# Множитель для первой (быстрой) интенсивности в HyperExp(2).
WORKLOAD_HYPEREXP_FAST_MULTIPLIER = 4.0

# Параметр p для более тяжёлого hyperexponential-сценария.
WORKLOAD_HYPEREXP_HEAVY_P = 0.85

# Множитель для более тяжёлого hyperexponential-сценария.
WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER = 6.0

# Порядки Erlang-распределений, которые хотим сравнивать.
WORKLOAD_ERLANG_ORDERS = [2, 4, 8]


# ==================================================
# Параметры, влияющие на агрегацию и отчёты experiments
# ==================================================

# Уровень доверительного интервала для summary по сценариям.
SUITE_CI_LEVEL = 0.95

# Хранить ли полные результаты всех прогонов в памяти и в сериализованной структуре.
SUITE_KEEP_FULL_RUN_RESULTS = True

# Имя baseline-серии экспериментов.
SUITE_NAME_BASELINE = "baseline"

# Имя серии по чувствительности к распределению обслуживания.
SUITE_NAME_SERVICE_SENSITIVITY = "service_time_sensitivity"


# ======================================
# Параметры построения графиков в Python
# ======================================

# DPI для matplotlib-графиков.
PLOTS_DPI = 220

# Дополнительные метрики, которые тоже нужно строить, кроме стандартного набора.
PLOTS_EXTRA_METRICS = [
    "rejected_capacity",
    "rejected_server",
    "rejected_resource",
]

# =========================
# Общие служебные параметры
# =========================

# Путь к release-бинарнику Rust. Нужен Python-launcher'у, не самому Rust-коду.
RUST_BINARY = "target/release/prog_files_rust.exe"

# Корневая директория, куда Rust будет складывать результаты экспериментов.
OUTPUT_ROOT = "results"

# Имя поддиректории для графиков рядом с suite_result.json.
PLOTS_DIRNAME = "plots"

# Каталог, куда Python будет писать JSON-конфиги для Rust.
GENERATED_CONFIG_DIR = "py/generated"








# ==================================================
# Резерв под будущий анализ типа входящего потока
# ==================================================
# Сейчас текущий Rust-движок ещё не использует это напрямую:
# в simulation.rs межприходовые интервалы по-прежнему генерируются
# как экспоненциальные с текущей state-dependent интенсивностью.
# Но эти определения уже стоит держать рядом с остальными
# исследовательскими параметрами.

ARRIVAL_PROCESS_FAMILY = {
    # Пуассоновский поток: текущая логика Rust.
    "poisson": {
        "kind": "poisson",
        "label": "Poisson",
    },

    # Зарезервировано под будущую реализацию в Rust.
    "erlang_2": {
        "kind": "erlang",
        "label": "ErlangArrival(2)",
        "order": 2,
    },

    # Зарезервировано под будущую реализацию в Rust.
    "erlang_4": {
        "kind": "erlang",
        "label": "ErlangArrival(4)",
        "order": 4,
    },

    # Зарезервировано под будущую реализацию в Rust.
    "hyperexp_2": {
        "kind": "hyperexponential2",
        "label": "HyperExpArrival(2)",
        "p": 0.75,
        "fast_rate_multiplier": 4.0,
    },
}


# ============================================
# Вспомогательные функции для построения профилей
# ============================================

def build_threshold_profile(
    *,
    capacity_k: int,
    normal_value: float,
    threshold_k: int,
    reduced_value: float,
    full_state_value: float,
) -> list[float]:
    """Строит threshold-профиль lambda_k."""
    profile: list[float] = []
    for k in range(capacity_k + 1):
        if k < threshold_k:
            profile.append(float(normal_value))
        else:
            profile.append(float(reduced_value))
    profile[-1] = float(full_state_value)
    return profile


def build_linear_decreasing_profile(
    *,
    capacity_k: int,
    start_value: float,
    step: float,
    floor_value: float,
) -> list[float]:
    """Строит линейно убывающий профиль sigma_k."""
    return [
        max(float(start_value) - float(step) * k, float(floor_value))
        for k in range(capacity_k + 1)
    ]


# ============================================
# Конструкторы конфигов, совпадающих с Rust serde
# ============================================

def make_simulation_config(
    *,
    max_time: float = SIM_MAX_TIME,
    warmup_time: float = SIM_WARMUP_TIME,
    seed: int = SIM_SEED,
    replications: int = SIM_REPLICATIONS,
    time_epsilon: float = SIM_TIME_EPSILON,
    record_state_trace: bool = SIM_RECORD_STATE_TRACE,
    save_event_log: bool = SIM_SAVE_EVENT_LOG,
) -> dict:
    """Возвращает структуру, совместимую с Rust SimulationConfig."""
    return {
        "max_time": float(max_time),
        "warmup_time": float(warmup_time),
        "seed": int(seed),
        "replications": int(replications),
        "time_epsilon": float(time_epsilon),
        "record_state_trace": bool(record_state_trace),
        "save_event_log": bool(save_event_log),
    }


def make_resource_distribution_baseline() -> dict:
    """Возвращает структуру, совместимую с Rust ResourceDistributionConfig."""
    return {
        "kind": "discrete_custom",
        "values": list(RESOURCE_VALUES),
        "probabilities": list(RESOURCE_PROBABILITIES),
    }


def make_workload_distribution(kind: str, *, mean: float = WORKLOAD_MEAN) -> dict:
    """Возвращает структуру, совместимую с Rust WorkloadDistributionConfig."""
    if kind == "deterministic":
        return {
            "kind": "deterministic",
            "mean": float(mean),
            "label": "Deterministic",
        }

    if kind == "exponential":
        return {
            "kind": "exponential",
            "mean": float(mean),
            "label": "Exponential",
        }

    if kind.startswith("erlang_"):
        order = int(kind.split("_", 1)[1])
        return {
            "kind": "erlang",
            "mean": float(mean),
            "label": f"Erlang({order})",
            "erlang_order": int(order),
        }

    if kind == "hyperexp_2":
        return _make_hyperexp_distribution(
            mean=mean,
            p=WORKLOAD_HYPEREXP_P,
            fast_rate_multiplier=WORKLOAD_HYPEREXP_FAST_MULTIPLIER,
            label="HyperExp(2)",
        )

    if kind == "hyperexp_heavy":
        return _make_hyperexp_distribution(
            mean=mean,
            p=WORKLOAD_HYPEREXP_HEAVY_P,
            fast_rate_multiplier=WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER,
            label="HyperExpHeavy",
        )

    raise ValueError(f"Неизвестный workload kind: {kind}")


def _make_hyperexp_distribution(
    *,
    mean: float,
    p: float,
    fast_rate_multiplier: float,
    label: str,
) -> dict:
    """
    Повторяет логику Rust WorkloadDistributionConfig::hyperexponential2:
    rates подбираются так, чтобы среднее оставалось равным mean.
    """
    rate_1 = fast_rate_multiplier / mean
    denominator = mean - p / rate_1
    if denominator <= 0.0:
        raise ValueError(
            "Некорректные параметры hyperexponential2: denominator <= 0.0"
        )
    rate_2 = (1.0 - p) / denominator

    return {
        "kind": "hyperexponential2",
        "mean": float(mean),
        "label": label,
        "hyper_p": float(p),
        "hyper_rates": [float(rate_1), float(rate_2)],
    }


def make_base_scenario(
    *,
    scenario_name: str,
    workload_kind: str,
    mean_workload: float = WORKLOAD_MEAN,
    note: str = SCENARIO_NOTE,
    simulation_overrides: dict | None = None,
) -> dict:
    """
    Строит полностью разрешённый ScenarioConfig, совпадающий по полям
    с Rust struct ScenarioConfig. Такой словарь можно напрямую писать в JSON
    и читать в Rust через serde.
    """
    threshold_k = (
        ARRIVAL_THRESHOLD_K
        if ARRIVAL_THRESHOLD_K is not None
        else max(0, SCENARIO_CAPACITY_K - 4)
    )

    simulation_cfg = make_simulation_config()
    if simulation_overrides:
        simulation_cfg.update(simulation_overrides)

    scenario = {
        # Имя сценария. Используется во всех summary и названиях артефактов.
        "name": str(scenario_name),

        # Ёмкость системы по числу заявок.
        "capacity_k": int(SCENARIO_CAPACITY_K),

        # Число обслуживающих приборов / каналов.
        "servers_n": int(SCENARIO_SERVERS_N),

        # Общий объём ограниченного ресурса.
        "total_resource_r": int(SCENARIO_TOTAL_RESOURCE_R),

        # Полный state-dependent профиль интенсивности поступления.
        "arrival_rate_by_state": build_threshold_profile(
            capacity_k=SCENARIO_CAPACITY_K,
            normal_value=ARRIVAL_NORMAL_VALUE,
            threshold_k=threshold_k,
            reduced_value=ARRIVAL_REDUCED_VALUE,
            full_state_value=ARRIVAL_FULL_STATE_VALUE,
        ),

        # Полный state-dependent профиль скорости обслуживания.
        "service_speed_by_state": build_linear_decreasing_profile(
            capacity_k=SCENARIO_CAPACITY_K,
            start_value=SERVICE_START_VALUE,
            step=SERVICE_STEP,
            floor_value=SERVICE_FLOOR_VALUE,
        ),

        # Распределение требований к ресурсу заявки.
        "resource_distribution": make_resource_distribution_baseline(),

        # Распределение объёма работы заявки.
        "workload_distribution": make_workload_distribution(
            workload_kind,
            mean=mean_workload,
        ),

        # Конфиг имитационного запуска.
        "simulation": simulation_cfg,

        # Текстовая пометка сценария.
        "note": str(note),
    }

    return scenario


def build_service_time_sensitivity_scenarios(
    *,
    mean_workload: float = WORKLOAD_MEAN,
    simulation_overrides: dict | None = None,
) -> dict[str, dict]:
    """
    Возвращает семейство сценариев для анализа чувствительности
    к распределению времени обслуживания / объёма работы.
    """
    workload_kinds = [
        "deterministic",
        "exponential",
        "erlang_2",
        "erlang_4",
        "erlang_8",
        "hyperexp_2",
        "hyperexp_heavy",
    ]

    scenarios: dict[str, dict] = {}
    for key in workload_kinds:
        scenarios[key] = make_base_scenario(
            scenario_name=f"base_{key}",
            workload_kind=key,
            mean_workload=mean_workload,
            simulation_overrides=simulation_overrides,
        )
    return scenarios


# ======================================
# Готовые пресеты для launcher / кампаний
# ======================================

SUITE_PRESETS = {
    "baseline": {
        # Имя серии экспериментов.
        "suite_name": SUITE_NAME_BASELINE,

        # Средний объём работы.
        "mean_workload": WORKLOAD_MEAN,

        # Уровень доверительных интервалов.
        "ci_level": SUITE_CI_LEVEL,

        # Хранить полные run_results в памяти и сериализованной структуре.
        "keep_full_run_results": SUITE_KEEP_FULL_RUN_RESULTS,

        # Куда Rust будет сохранять результаты.
        "output_root": OUTPUT_ROOT,

        # Параметры plotting-слоя.
        "plots": {
            "dpi": PLOTS_DPI,
            "extra_metrics": list(PLOTS_EXTRA_METRICS),
        },

        # Переопределения simulation для всей серии.
        "simulation_overrides": {
            "max_time": SIM_MAX_TIME,
            "warmup_time": SIM_WARMUP_TIME,
            "seed": SIM_SEED,
            "replications": SIM_REPLICATIONS,
            "time_epsilon": SIM_TIME_EPSILON,
            "record_state_trace": False,
            "save_event_log": False,
        },
    },

    "debug_small": {
        "suite_name": "debug_small",
        "mean_workload": WORKLOAD_MEAN,
        "ci_level": SUITE_CI_LEVEL,
        "keep_full_run_results": True,
        "output_root": OUTPUT_ROOT,
        "plots": {
            "dpi": PLOTS_DPI,
            "extra_metrics": list(PLOTS_EXTRA_METRICS),
        },
        "simulation_overrides": {
            "max_time": 5_000.0,
            "warmup_time": 500.0,
            "seed": SIM_SEED,
            "replications": 5,
            "time_epsilon": SIM_TIME_EPSILON,
            "record_state_trace": False,
            "save_event_log": False,
        },
    },
}


SINGLE_RUN_PRESET = {
    # Имя сценария для одного прогона.
    "scenario_name": "base_exponential",

    # Какой workload использовать.
    "workload_kind": "exponential",

    # Средний объём работы.
    "mean_workload": WORKLOAD_MEAN,

    # Индекс повтора.
    "replication_index": 0,

    # Явный seed override. None означает derive от базового seed.
    "seed_override": None,

    # Переопределения для simulation.
    "simulation_overrides": {
        "max_time": 2_000.0,
        "warmup_time": 200.0,
        "seed": SIM_SEED,
        "replications": SIM_REPLICATIONS,
        "time_epsilon": SIM_TIME_EPSILON,
        "record_state_trace": True,
        "save_event_log": True,
    },

    # Куда Rust сохраняет single-run результаты.
    "output_root": OUTPUT_ROOT,
}


# ==================================================
# Подготовка JSON-запросов, которые потом читает Rust
# ==================================================

def build_suite_request(preset_name: str = "baseline") -> dict:
    """
    Возвращает top-level JSON payload для Rust suite-режима.
    Важно: внутри scenarios уже лежат полностью материализованные ScenarioConfig.
    """
    preset = deepcopy(SUITE_PRESETS[preset_name])

    scenarios = build_service_time_sensitivity_scenarios(
        mean_workload=float(preset["mean_workload"]),
        simulation_overrides=dict(preset["simulation_overrides"]),
    )

    return {
        # Вид запроса для Rust launcher / config-subcommand.
        "request_kind": "suite",

        # Имя серии.
        "suite_name": str(preset["suite_name"]),

        # Уровень доверительных интервалов.
        "ci_level": float(preset["ci_level"]),

        # Сохранять ли полные run_results.
        "keep_full_run_results": bool(preset["keep_full_run_results"]),

        # Корневая директория результатов.
        "output_root": str(preset["output_root"]),

        # Готовые сценарии, уже совместимые с Rust ScenarioConfig.
        "scenarios": scenarios,

        # Параметры plotting-слоя.
        "plots": deepcopy(preset["plots"]),
    }


def build_single_request() -> dict:
    """
    Возвращает top-level JSON payload для Rust single-режима.
    """
    preset = deepcopy(SINGLE_RUN_PRESET)

    scenario = make_base_scenario(
        scenario_name=str(preset["scenario_name"]),
        workload_kind=str(preset["workload_kind"]),
        mean_workload=float(preset["mean_workload"]),
        simulation_overrides=dict(preset["simulation_overrides"]),
    )

    return {
        # Вид запроса для Rust launcher / config-subcommand.
        "request_kind": "single",

        # Полностью материализованный ScenarioConfig.
        "scenario": scenario,

        # Индекс повтора.
        "replication_index": int(preset["replication_index"]),

        # Явный seed override или None.
        "seed": preset["seed_override"],

        # Корневая директория результатов.
        "output_root": str(preset["output_root"]),
    }


def write_request_json(payload: dict, filepath: str | Path) -> Path:
    """
    Пишет JSON-конфиг, который потом считывает Rust.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    generated_dir = Path(GENERATED_CONFIG_DIR)

    suite_path = write_request_json(
        build_suite_request("baseline"),
        generated_dir / "baseline_suite.json",
    )
    print(f"Written: {suite_path}")

    single_path = write_request_json(
        build_single_request(),
        generated_dir / "single_exponential.json",
    )
    print(f"Written: {single_path}")