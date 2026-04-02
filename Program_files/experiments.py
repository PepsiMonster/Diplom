<<<<<<< HEAD
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

from datetime import datetime

from math import sqrt

from pathlib import Path

from typing import Any, Iterable, Mapping

import csv

=======
# серии прогонов
"""
experiments.py
==============

Оркестратор серий имитационных экспериментов для модели СМО
с ограниченными ресурсами и state-dependent характеристиками.

Роль файла
----------
Если:
- params.py задаёт параметры и фабрики сценариев;
- model.py задаёт предметную логику состояния системы;
- simulation.py умеет выполнить ОДИН прогон,

то experiments.py отвечает за уровень "серии экспериментов":

1. запуск нескольких replication одного сценария;
2. агрегацию метрик по повторам;
3. построение доверительных интервалов;
4. сохранение результатов в CSV / JSON;
5. печать аккуратной сводки;
6. запуск набора сценариев одной командой.

Что именно считается
--------------------
На уровне одного прогона simulation.py уже возвращает стандартизованный
объект SimulationRunResult. Здесь мы строим поверх него более высокий слой:

- ScenarioExperimentResult:
    результат серии повторов одного сценария;

- ExperimentSuiteResult:
    результат набора сценариев.

Основная идея
-------------
Мы не смешиваем:
- логику имитации одного прогона;
- логику статистической обработки серии прогонов.

Это упрощает код, делает архитектуру прозрачнее и облегчает проверку.

Файлик можно запускать отдельно:
    python experiments.py

В этом случае будет:
1. собран стандартный набор сценариев чувствительности;
2. выполнены серии прогонов;
3. напечатана сводка;
4. результаты сохранятся в папку results/experiments/<timestamp>.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from math import sqrt
from pathlib import Path
from typing import Any, Iterable, Mapping
import csv
>>>>>>> main
import json

import numpy as np

from params import (
<<<<<<< HEAD

    ScenarioConfig,

    build_sensitivity_scenarios,

)

from simulation import SimulationRunResult, simulate_one_run

@dataclass(slots=True)

class MetricSummary:

    name: str

    n: int

    mean: float

    std: float

    stderr: float

    ci_level: float

    ci_low: float

    ci_high: float

    min_value: float

    max_value: float

    def as_flat_dict(self, prefix: str = "") -> dict[str, float | int]:

        base = prefix + self.name

        return {

            f"{base}__n": self.n,

            f"{base}__mean": self.mean,

            f"{base}__std": self.std,

            f"{base}__stderr": self.stderr,

            f"{base}__ci_low": self.ci_low,

            f"{base}__ci_high": self.ci_high,

            f"{base}__min": self.min_value,

            f"{base}__max": self.max_value,

        }

@dataclass(slots=True)

class ScenarioExperimentResult:

    scenario_name: str

    scenario_description: str

    replications: int

    metric_summaries: dict[str, MetricSummary]

    run_results: tuple[SimulationRunResult, ...] = ()

    run_summaries: tuple[dict[str, Any], ...] = ()

    def get_metric(self, metric_name: str) -> MetricSummary:

        if metric_name not in self.metric_summaries:

            raise KeyError(f"Метрика '{metric_name}' отсутствует в результатах сценария")

        return self.metric_summaries[metric_name]

    def flat_summary(self) -> dict[str, Any]:

        row: dict[str, Any] = {

            "scenario_name": self.scenario_name,

            "scenario_description": self.scenario_description,

            "replications": self.replications,

        }

        for metric_name in sorted(self.metric_summaries):

            row.update(self.metric_summaries[metric_name].as_flat_dict())

        return row

@dataclass(slots=True)

class ExperimentSuiteResult:

    suite_name: str

    created_at: str

    scenario_results: dict[str, ScenarioExperimentResult] = field(default_factory=dict)

    def aggregated_rows(self) -> list[dict[str, Any]]:

        return [result.flat_summary() for result in self.scenario_results.values()]

    def all_run_rows(self) -> list[dict[str, Any]]:

        rows: list[dict[str, Any]] = []

        for scenario_name, result in self.scenario_results.items():

            for run_summary in result.run_summaries:

                row = dict(run_summary)

                row["scenario_name"] = scenario_name

                rows.append(row)

        return rows

def _normal_critical_value(ci_level: float) -> float:

    predefined = {

        0.90: 1.6448536269514722,

        0.95: 1.959963984540054,

        0.99: 2.5758293035489004,

    }

    rounded = round(ci_level, 6)

    for key, value in predefined.items():

        if abs(rounded - key) < 1e-9:

            return value

    raise ValueError(

        "Поддерживаются только уровни доверия 0.90, 0.95 и 0.99 "

        f"(получено: {ci_level})"

    )

def summarize_numeric_metric(

    values: Iterable[float | int],

    metric_name: str,

    *,

    ci_level: float = 0.95,

) -> MetricSummary:

    arr = np.asarray(list(values), dtype=float)

    if arr.size == 0:

        raise ValueError(f"Нельзя агрегировать пустой набор значений для метрики '{metric_name}'")

    n = int(arr.size)

    mean = float(arr.mean())

    min_value = float(arr.min())

    max_value = float(arr.max())

    if n == 1:

        std = 0.0

        stderr = 0.0

        ci_low = mean

        ci_high = mean

    else:

        std = float(arr.std(ddof=1))

        stderr = std / sqrt(n)

        z = _normal_critical_value(ci_level)

        half_width = z * stderr

        ci_low = mean - half_width

        ci_high = mean + half_width

    return MetricSummary(

        name=metric_name,

        n=n,

        mean=mean,

        std=std,

        stderr=stderr,

        ci_level=ci_level,

        ci_low=ci_low,

        ci_high=ci_high,

        min_value=min_value,

        max_value=max_value,

    )

def _extract_numeric_columns(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[float]]:

    rows_list = list(rows)

    if not rows_list:

        return {}

    columns: dict[str, list[float]] = {}

    for row in rows_list:

        for key, value in row.items():

            if isinstance(value, bool):

                continue

            if isinstance(value, (int, float, np.integer, np.floating)):

                columns.setdefault(key, []).append(float(value))

    return columns

def run_scenario_experiment(

    scenario: ScenarioConfig,

    *,

    ci_level: float = 0.95,

    keep_full_run_results: bool = True,

) -> ScenarioExperimentResult:

    scenario.validate()

    replications = scenario.simulation.replications

    run_results: list[SimulationRunResult] = []

    run_summaries: list[dict[str, Any]] = []

    for replication_index in range(replications):

        result = simulate_one_run(

            scenario=scenario,

            replication_index=replication_index,

            seed=None,

        )

        run_results.append(result)

=======
    ScenarioConfig,
    build_sensitivity_scenarios,
)
from simulation import SimulationRunResult, simulate_one_run


# ============================================================================
# БАЗОВЫЕ СТАТИСТИЧЕСКИЕ СТРУКТУРЫ
# ============================================================================


@dataclass(slots=True)
class MetricSummary:
    """
    Агрегированная статистика по одной числовой метрике.

    Поля:
    -----
    name:
        Имя метрики.

    n:
        Число наблюдений.

    mean:
        Выборочное среднее.

    std:
        Выборочное стандартное отклонение.
        Для n=1 принимается равным 0.

    stderr:
        Стандартная ошибка среднего.

    ci_level:
        Уровень доверительного интервала.

    ci_low / ci_high:
        Нижняя и верхняя границы доверительного интервала для среднего.

    min_value / max_value:
        Минимум и максимум по сериям.
    """

    name: str
    n: int
    mean: float
    std: float
    stderr: float
    ci_level: float
    ci_low: float
    ci_high: float
    min_value: float
    max_value: float

    def as_flat_dict(self, prefix: str = "") -> dict[str, float | int]:
        """
        Возвращает плоское представление для CSV/JSON.
        """
        base = prefix + self.name
        return {
            f"{base}__n": self.n,
            f"{base}__mean": self.mean,
            f"{base}__std": self.std,
            f"{base}__stderr": self.stderr,
            f"{base}__ci_low": self.ci_low,
            f"{base}__ci_high": self.ci_high,
            f"{base}__min": self.min_value,
            f"{base}__max": self.max_value,
        }


@dataclass(slots=True)
class ScenarioExperimentResult:
    """
    Итог серии прогонов одного сценария.

    Поля:
    -----
    scenario_name:
        Имя сценария.

    scenario_description:
        Короткое описание сценария для логов и сводок.

    replications:
        Фактическое число выполненных повторов.

    metric_summaries:
        Агрегированная статистика по числовым метрикам.

    run_results:
        Полные результаты отдельных прогонов.
        Полезно для последующего глубокого анализа или отладки.

    run_summaries:
        Плоские словари отдельных прогонов.
        Именно они удобны для CSV/таблиц.
    """

    scenario_name: str
    scenario_description: str
    replications: int
    metric_summaries: dict[str, MetricSummary]
    run_results: tuple[SimulationRunResult, ...] = ()
    run_summaries: tuple[dict[str, Any], ...] = ()

    def get_metric(self, metric_name: str) -> MetricSummary:
        """
        Возвращает агрегированную статистику по имени метрики.
        """
        if metric_name not in self.metric_summaries:
            raise KeyError(f"Метрика '{metric_name}' отсутствует в результатах сценария")
        return self.metric_summaries[metric_name]

    def flat_summary(self) -> dict[str, Any]:
        """
        Возвращает плоскую итоговую сводку по сценарию.
        Удобно для CSV с агрегатами.
        """
        row: dict[str, Any] = {
            "scenario_name": self.scenario_name,
            "scenario_description": self.scenario_description,
            "replications": self.replications,
        }
        for metric_name in sorted(self.metric_summaries):
            row.update(self.metric_summaries[metric_name].as_flat_dict())
        return row


@dataclass(slots=True)
class ExperimentSuiteResult:
    """
    Итог набора сценариев.

    Поля:
    -----
    suite_name:
        Имя набора экспериментов.

    created_at:
        Временная метка формирования результата.

    scenario_results:
        Результаты по каждому сценарию.
    """

    suite_name: str
    created_at: str
    scenario_results: dict[str, ScenarioExperimentResult] = field(default_factory=dict)

    def aggregated_rows(self) -> list[dict[str, Any]]:
        """
        Возвращает список агрегированных строк по сценариям.
        """
        return [result.flat_summary() for result in self.scenario_results.values()]

    def all_run_rows(self) -> list[dict[str, Any]]:
        """
        Возвращает список строк уровня отдельных прогонов по всем сценариям.
        """
        rows: list[dict[str, Any]] = []
        for scenario_name, result in self.scenario_results.items():
            for run_summary in result.run_summaries:
                row = dict(run_summary)
                row["scenario_name"] = scenario_name
                rows.append(row)
        return rows


# ============================================================================
# СТАТИСТИЧЕСКИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def _normal_critical_value(ci_level: float) -> float:
    """
    Возвращает нормальный квантиль для двустороннего ДИ.

    Почему именно так:
    ------------------
    Для полноценной реализации через t-распределение понадобился бы scipy.
    Чтобы не вводить лишнюю зависимость, используем нормальное приближение.

    Для типовых уровней возвращаем стандартные значения:
    - 0.90 -> 1.64485
    - 0.95 -> 1.95996
    - 0.99 -> 2.57583
    """
    predefined = {
        0.90: 1.6448536269514722,
        0.95: 1.959963984540054,
        0.99: 2.5758293035489004,
    }
    rounded = round(ci_level, 6)
    for key, value in predefined.items():
        if abs(rounded - key) < 1e-9:
            return value

    raise ValueError(
        "Поддерживаются только уровни доверия 0.90, 0.95 и 0.99 "
        f"(получено: {ci_level})"
    )


def summarize_numeric_metric(
    values: Iterable[float | int],
    metric_name: str,
    *,
    ci_level: float = 0.95,
) -> MetricSummary:
    """
    Строит агрегированную статистику по одной метрике.
    """
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        raise ValueError(f"Нельзя агрегировать пустой набор значений для метрики '{metric_name}'")

    n = int(arr.size)
    mean = float(arr.mean())
    min_value = float(arr.min())
    max_value = float(arr.max())

    if n == 1:
        std = 0.0
        stderr = 0.0
        ci_low = mean
        ci_high = mean
    else:
        std = float(arr.std(ddof=1))
        stderr = std / sqrt(n)
        z = _normal_critical_value(ci_level)
        half_width = z * stderr
        ci_low = mean - half_width
        ci_high = mean + half_width

    return MetricSummary(
        name=metric_name,
        n=n,
        mean=mean,
        std=std,
        stderr=stderr,
        ci_level=ci_level,
        ci_low=ci_low,
        ci_high=ci_high,
        min_value=min_value,
        max_value=max_value,
    )


def _extract_numeric_columns(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[float]]:
    """
    Извлекает числовые столбцы из списка плоских словарей.

    Важно:
    ------
    Мы агрегируем только числовые значения.
    Строковые поля вроде scenario_name не участвуют в статистике.
    """
    rows_list = list(rows)
    if not rows_list:
        return {}

    columns: dict[str, list[float]] = {}
    for row in rows_list:
        for key, value in row.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float, np.integer, np.floating)):
                columns.setdefault(key, []).append(float(value))
    return columns


# ============================================================================
# ЗАПУСК ОДНОГО СЦЕНАРИЯ
# ============================================================================


def run_scenario_experiment(
    scenario: ScenarioConfig,
    *,
    ci_level: float = 0.95,
    keep_full_run_results: bool = True,
) -> ScenarioExperimentResult:
    """
    Выполняет серию независимых прогонов одного сценария.

    Алгоритм:
    ---------
    1. Валидируем сценарий.
    2. Запускаем replications отдельных прогонов через simulation.py.
    3. Переводим результаты в плоские summary-строки.
    4. Для каждой числовой метрики строим:
       - среднее,
       - std,
       - stderr,
       - доверительный интервал.
    5. Возвращаем единый объект результата.
    """
    scenario.validate()

    replications = scenario.simulation.replications
    run_results: list[SimulationRunResult] = []
    run_summaries: list[dict[str, Any]] = []

    for replication_index in range(replications):
        result = simulate_one_run(
            scenario=scenario,
            replication_index=replication_index,
            seed=None,
        )
        run_results.append(result)
>>>>>>> main
        run_summaries.append(result.flat_summary())

    numeric_columns = _extract_numeric_columns(run_summaries)

    excluded_from_aggregation = {
<<<<<<< HEAD

        "replication_index",

        "seed",

        "total_time",

        "warmup_time",

        "observed_time",

    }

    metric_summaries: dict[str, MetricSummary] = {}

    for metric_name, values in sorted(numeric_columns.items()):

        if metric_name in excluded_from_aggregation:

            continue

        metric_summaries[metric_name] = summarize_numeric_metric(

            values,

            metric_name=metric_name,

            ci_level=ci_level,

        )

    return ScenarioExperimentResult(

        scenario_name=scenario.name,

        scenario_description=scenario.short_description(),

        replications=replications,

        metric_summaries=metric_summaries,

        run_results=tuple(run_results) if keep_full_run_results else (),

        run_summaries=tuple(run_summaries),

    )

def run_experiment_suite(

    scenarios: Mapping[str, ScenarioConfig],

    *,

    suite_name: str = "experiment_suite",

    ci_level: float = 0.95,

    keep_full_run_results: bool = True,

) -> ExperimentSuiteResult:

    created_at = datetime.now().isoformat(timespec="seconds")

    result = ExperimentSuiteResult(

        suite_name=suite_name,

        created_at=created_at,

    )

    for scenario_key, scenario in scenarios.items():

        scenario_result = run_scenario_experiment(

            scenario=scenario,

            ci_level=ci_level,

            keep_full_run_results=keep_full_run_results,

        )

=======
        "replication_index",
        "seed",
        "total_time",
        "warmup_time",
        "observed_time",
    }

    metric_summaries: dict[str, MetricSummary] = {}
    for metric_name, values in sorted(numeric_columns.items()):
        if metric_name in excluded_from_aggregation:
            continue
        metric_summaries[metric_name] = summarize_numeric_metric(
            values,
            metric_name=metric_name,
            ci_level=ci_level,
        )

    return ScenarioExperimentResult(
        scenario_name=scenario.name,
        scenario_description=scenario.short_description(),
        replications=replications,
        metric_summaries=metric_summaries,
        run_results=tuple(run_results) if keep_full_run_results else (),
        run_summaries=tuple(run_summaries),
    )


# ============================================================================
# ЗАПУСК НАБОРА СЦЕНАРИЕВ
# ============================================================================


def run_experiment_suite(
    scenarios: Mapping[str, ScenarioConfig],
    *,
    suite_name: str = "experiment_suite",
    ci_level: float = 0.95,
    keep_full_run_results: bool = True,
) -> ExperimentSuiteResult:
    """
    Выполняет набор экспериментов по нескольким сценариям.

    Ключи словаря scenarios используются только как внешние имена группы,
    а внутри каждого результата главным именем остаётся scenario.name.
    """
    created_at = datetime.now().isoformat(timespec="seconds")
    result = ExperimentSuiteResult(
        suite_name=suite_name,
        created_at=created_at,
    )

    for scenario_key, scenario in scenarios.items():
        scenario_result = run_scenario_experiment(
            scenario=scenario,
            ci_level=ci_level,
            keep_full_run_results=keep_full_run_results,
        )
>>>>>>> main
        result.scenario_results[scenario_key] = scenario_result

    return result

<<<<<<< HEAD
def print_scenario_experiment_summary(

    result: ScenarioExperimentResult,

    *,

    metrics: Iterable[str] | None = None,

) -> None:

    print("=" * 96)

    print(f"СЦЕНАРИЙ: {result.scenario_name}")

    print(result.scenario_description)

    print(f"Число повторов: {result.replications}")

    print("-" * 96)

    if metrics is None:

        metrics = (

            "mean_num_jobs",

            "mean_occupied_resource",

            "loss_probability",

            "throughput",

            "accepted_arrivals",

            "rejected_arrivals",

            "completed_jobs",

        )

    for metric_name in metrics:

        if metric_name not in result.metric_summaries:

            continue

        m = result.metric_summaries[metric_name]

        print(

            f"{metric_name:<28}"

            f" mean={m.mean:>12.6f} |"

            f" std={m.std:>12.6f} |"

            f" CI[{m.ci_level:.2f}]=[{m.ci_low:>10.6f}, {m.ci_high:>10.6f}]"

=======

# ============================================================================
# ФОРМАТИРОВАННЫЙ ВЫВОД В КОНСОЛЬ
# ============================================================================


def print_scenario_experiment_summary(
    result: ScenarioExperimentResult,
    *,
    metrics: Iterable[str] | None = None,
) -> None:
    """
    Печатает краткую читабельную сводку по одному сценарию.
    """
    print("=" * 96)
    print(f"СЦЕНАРИЙ: {result.scenario_name}")
    print(result.scenario_description)
    print(f"Число повторов: {result.replications}")
    print("-" * 96)

    if metrics is None:
        metrics = (
            "mean_num_jobs",
            "mean_occupied_resource",
            "loss_probability",
            "throughput",
            "accepted_arrivals",
            "rejected_arrivals",
            "completed_jobs",
        )

    for metric_name in metrics:
        if metric_name not in result.metric_summaries:
            continue
        m = result.metric_summaries[metric_name]
        print(
            f"{metric_name:<28}"
            f" mean={m.mean:>12.6f} |"
            f" std={m.std:>12.6f} |"
            f" CI[{m.ci_level:.2f}]=[{m.ci_low:>10.6f}, {m.ci_high:>10.6f}]"
>>>>>>> main
        )

    print("-" * 96)

    pi_metrics = [
<<<<<<< HEAD

        name for name in sorted(result.metric_summaries)

        if name.startswith("pi_hat_")

    ]

    if pi_metrics:

        print("Оценка стационарного распределения по числу заявок:")

        for name in pi_metrics:

            m = result.metric_summaries[name]

            state_label = name.replace("pi_hat_", "")

            print(

                f"  k={state_label:>2}: "

                f"{m.mean:.6f}  "

                f"(CI[{m.ci_level:.2f}] = [{m.ci_low:.6f}, {m.ci_high:.6f}])"

            )

    print("=" * 96)

    print()

def print_experiment_suite_summary(

    suite_result: ExperimentSuiteResult,

    *,

    metrics: Iterable[str] | None = None,

) -> None:

    print("#" * 96)

    print(f"НАБОР ЭКСПЕРИМЕНТОВ: {suite_result.suite_name}")

    print(f"Создан: {suite_result.created_at}")

    print("#" * 96)

    print()

    for scenario_key, result in suite_result.scenario_results.items():

        print(f"[{scenario_key}]")

        print_scenario_experiment_summary(result, metrics=metrics)

def _ensure_directory(path: Path) -> None:

    path.mkdir(parents=True, exist_ok=True)

def _write_csv(rows: list[Mapping[str, Any]], filepath: Path) -> None:

    if not rows:

        filepath.write_text("", encoding="utf-8")

        return

    fieldnames: list[str] = sorted({key for row in rows for key in row.keys()})

    with filepath.open("w", encoding="utf-8-sig", newline="") as f:

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()

        for row in rows:

            writer.writerow(dict(row))

def _suite_to_json_ready(suite_result: ExperimentSuiteResult) -> dict[str, Any]:

    data: dict[str, Any] = {

        "suite_name": suite_result.suite_name,

        "created_at": suite_result.created_at,

        "scenario_results": {},

    }

    for scenario_key, result in suite_result.scenario_results.items():

        data["scenario_results"][scenario_key] = {

            "scenario_name": result.scenario_name,

            "scenario_description": result.scenario_description,

            "replications": result.replications,

            "metric_summaries": {

                metric_name: asdict(metric_summary)

                for metric_name, metric_summary in result.metric_summaries.items()

            },

            "run_summaries": list(result.run_summaries),

=======
        name for name in sorted(result.metric_summaries)
        if name.startswith("pi_hat_")
    ]
    if pi_metrics:
        print("Оценка стационарного распределения по числу заявок:")
        for name in pi_metrics:
            m = result.metric_summaries[name]
            state_label = name.replace("pi_hat_", "")
            print(
                f"  k={state_label:>2}: "
                f"{m.mean:.6f}  "
                f"(CI[{m.ci_level:.2f}] = [{m.ci_low:.6f}, {m.ci_high:.6f}])"
            )

    print("=" * 96)
    print()


def print_experiment_suite_summary(
    suite_result: ExperimentSuiteResult,
    *,
    metrics: Iterable[str] | None = None,
) -> None:
    """
    Печатает сводку по всему набору сценариев.
    """
    print("#" * 96)
    print(f"НАБОР ЭКСПЕРИМЕНТОВ: {suite_result.suite_name}")
    print(f"Создан: {suite_result.created_at}")
    print("#" * 96)
    print()

    for scenario_key, result in suite_result.scenario_results.items():
        print(f"[{scenario_key}]")
        print_scenario_experiment_summary(result, metrics=metrics)


# ============================================================================
# СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
# ============================================================================


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_csv(rows: list[Mapping[str, Any]], filepath: Path) -> None:
    """
    Универсальная запись списка словарей в CSV.
    """
    if not rows:
        filepath.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = sorted({key for row in rows for key in row.keys()})
    with filepath.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _suite_to_json_ready(suite_result: ExperimentSuiteResult) -> dict[str, Any]:
    """
    Переводит результаты набора экспериментов в JSON-совместимый словарь.

    Полные объекты SimulationRunResult содержат кортежи dataclass-объектов,
    поэтому здесь сериализуем только:
    - агрегированные summary;
    - плоские run_summaries.
    """
    data: dict[str, Any] = {
        "suite_name": suite_result.suite_name,
        "created_at": suite_result.created_at,
        "scenario_results": {},
    }

    for scenario_key, result in suite_result.scenario_results.items():
        data["scenario_results"][scenario_key] = {
            "scenario_name": result.scenario_name,
            "scenario_description": result.scenario_description,
            "replications": result.replications,
            "metric_summaries": {
                metric_name: asdict(metric_summary)
                for metric_name, metric_summary in result.metric_summaries.items()
            },
            "run_summaries": list(result.run_summaries),
>>>>>>> main
        }

    return data

<<<<<<< HEAD
def save_experiment_suite(

    suite_result: ExperimentSuiteResult,

    output_dir: str | Path,

) -> Path:

    output_path = Path(output_dir)

    _ensure_directory(output_path)

    aggregated_rows = suite_result.aggregated_rows()

    all_run_rows = suite_result.all_run_rows()

    json_payload = _suite_to_json_ready(suite_result)

    _write_csv(aggregated_rows, output_path / "aggregated_summary.csv")

    _write_csv(all_run_rows, output_path / "all_runs.csv")

    (output_path / "suite_result.json").write_text(

        json.dumps(json_payload, ensure_ascii=False, indent=2),

        encoding="utf-8",

=======

def save_experiment_suite(
    suite_result: ExperimentSuiteResult,
    output_dir: str | Path,
) -> Path:
    """
    Сохраняет набор результатов на диск.

    Будут созданы:
    - aggregated_summary.csv
    - all_runs.csv
    - suite_result.json
    """
    output_path = Path(output_dir)
    _ensure_directory(output_path)

    aggregated_rows = suite_result.aggregated_rows()
    all_run_rows = suite_result.all_run_rows()
    json_payload = _suite_to_json_ready(suite_result)

    _write_csv(aggregated_rows, output_path / "aggregated_summary.csv")
    _write_csv(all_run_rows, output_path / "all_runs.csv")
    (output_path / "suite_result.json").write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
>>>>>>> main
    )

    return output_path

<<<<<<< HEAD
def build_default_experiment_suite(mean_workload: float = 1.0) -> dict[str, ScenarioConfig]:

    return build_sensitivity_scenarios(mean_workload=mean_workload)

def _self_test() -> None:

    base_scenarios = build_default_experiment_suite(mean_workload=1.0)

    demo_scenarios: dict[str, ScenarioConfig] = {}

    for key, scenario in base_scenarios.items():

        demo_sim_cfg = replace(

            scenario.simulation,

            max_time=20_000.0,

            warmup_time=2_000.0,

            replications=5,

            record_state_trace=False,

            save_event_log=False,

        )

        demo_scenarios[key] = replace(scenario, simulation=demo_sim_cfg)

    suite_result = run_experiment_suite(

        demo_scenarios,

        suite_name="sensitivity_demo",

        ci_level=0.95,

        keep_full_run_results=True,

=======

# ============================================================================
# ГОТОВЫЕ СЦЕНАРИИ ДЛЯ ПЕРВОГО ИССЛЕДОВАНИЯ
# ============================================================================


def build_default_experiment_suite(mean_workload: float = 1.0) -> dict[str, ScenarioConfig]:
    """
    Возвращает стандартный набор сценариев для первого серьёзного запуска.

    Сейчас это набор чувствительности к распределению объёма работы
    при одинаковом среднем.
    """
    return build_sensitivity_scenarios(mean_workload=mean_workload)


# ============================================================================
# SELF-TEST / DEMO
# ============================================================================


def _self_test() -> None:
    """
    Автономная демонстрация experiments.py.

    Что она делает:
    ---------------
    1. Строит стандартный набор сценариев.
    2. Для ускорения demo немного уменьшает длину прогона и число повторов.
    3. Выполняет набор экспериментов.
    4. Печатает сводку.
    5. Сохраняет результаты в папку results/experiments/<timestamp>.
    """
    base_scenarios = build_default_experiment_suite(mean_workload=1.0)

    demo_scenarios: dict[str, ScenarioConfig] = {}
    for key, scenario in base_scenarios.items():
        demo_sim_cfg = replace(
            scenario.simulation,
            max_time=20_000.0,
            warmup_time=2_000.0,
            replications=5,
            record_state_trace=False,
            save_event_log=False,
        )
        demo_scenarios[key] = replace(scenario, simulation=demo_sim_cfg)

    suite_result = run_experiment_suite(
        demo_scenarios,
        suite_name="sensitivity_demo",
        ci_level=0.95,
        keep_full_run_results=True,
>>>>>>> main
    )

    print_experiment_suite_summary(suite_result)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
<<<<<<< HEAD

    output_dir = Path("results") / "experiments" / timestamp

=======
    output_dir = Path("results") / "experiments" / timestamp
>>>>>>> main
    saved_path = save_experiment_suite(suite_result, output_dir)

    print(f"Результаты сохранены в: {saved_path}")

<<<<<<< HEAD
if __name__ == "__main__":

=======

if __name__ == "__main__":
>>>>>>> main
    _self_test()
