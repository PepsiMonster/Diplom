"""
Этот файлик отвечает за серию прогонов:
1. перебираем несколько распределений объёма работы;
2. запускаем несколько повторов для каждого распределения;
3. собираем сырые результаты;
4. считаем агрегированные показатели;
5. сохраняем всё в CSV.


simulation.py = "как моделируется одна траектория",
experiments.py = "как поставлен вычислительный эксперимент".
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from params import build_base_scenario, standard_workload_family
from simulation import SimulationResult, simulate_one_run

# Численные функции
# Среднее и выборочное стандартное отклонение.
# Надо добавить еще

def mean(values: list[float]) -> float:
    """
    Возвращает среднее арифметическое списка.
    Если список пуст, возвращается 0.0. (не должно происходить)
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def sample_std(values: list[float]) -> float:
    """
    Возвращает выборочное стандартное отклонение.
    Если наблюдение одно, возвращаем 0.0.
    """
    n = len(values)
    if n <= 1:
        return 0.0

    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return variance ** 0.5

# Подготовка директорий для сохранения результатов

def ensure_results_dirs(base_dir: str = "results") -> dict[str, Path]:
    """
    Возвращается словарь с путями.
    """
    root = Path(base_dir)
    raw_dir = root / "raw"
    figures_dir = root / "figures"

    raw_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "raw": raw_dir,
        "figures": figures_dir,
    }



# Агрегирование результатов

# Один прогон даёт один SimulationResult.
# Для анализа чувствительности нужен не один прогон, а несколько повторов.
# Так что здесь мы собираем усреднённую строку по серии повторов.



def aggregate_results(results: list[SimulationResult], workload_name: str) -> dict[str, Any]:
    """
    Строит агрегированную сводку по списку прогонов одного сценария.

    На вход подаются результаты, отличающиеся только replication_index.
    На выходе получается одна строка summary.

    В summary включаем:
    - средние значения метрик;
    - стандартные отклонения;
    - усреднённую оценку pi_hat(k).
    """
    if not results:
        raise ValueError("Нельзя агрегировать пустой список результатов")

    first = results[0]
    num_states = len(first.pi_hat)

    mean_num_jobs_values = [r.mean_num_jobs for r in results]
    mean_occupied_resource_values = [r.mean_occupied_resource for r in results]
    loss_probability_values = [r.loss_probability for r in results]
    throughput_values = [r.throughput for r in results]

    accepted_values = [float(r.accepted_arrivals) for r in results]
    rejected_values = [float(r.rejected_arrivals) for r in results]
    completed_values = [float(r.completed_jobs) for r in results]

    summary: dict[str, Any] = {
        "scenario_name": first.scenario_name,
        "workload_name": workload_name,
        "replications": len(results),
        "mean_num_jobs_mean": mean(mean_num_jobs_values),
        "mean_num_jobs_std": sample_std(mean_num_jobs_values),
        "mean_occupied_resource_mean": mean(mean_occupied_resource_values),
        "mean_occupied_resource_std": sample_std(mean_occupied_resource_values),
        "loss_probability_mean": mean(loss_probability_values),
        "loss_probability_std": sample_std(loss_probability_values),
        "throughput_mean": mean(throughput_values),
        "throughput_std": sample_std(throughput_values),
        "accepted_arrivals_mean": mean(accepted_values),
        "rejected_arrivals_mean": mean(rejected_values),
        "completed_jobs_mean": mean(completed_values),
    }

    # Добавляем усреднённые pi_hat(k) по всем состояниям. Важно для сравнения стац. распр.
    for k in range(num_states):
        pi_values = [r.pi_hat[k] for r in results]
        summary[f"pi_hat_{k}_mean"] = mean(pi_values)
        summary[f"pi_hat_{k}_std"] = sample_std(pi_values)

    return summary

# Сохраняем в csv

def save_dict_rows_to_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# Запуск серии ЭЭЭЭЭкспериментов

def run_workload_sensitivity_experiments(
    *,
    mean_workload: float = 1.0,
    replications_override: int | None = None,
    max_time_override: float | None = None,
    warmup_time_override: float | None = None,
) -> tuple[list[SimulationResult], list[dict[str, Any]]]:
    """
    Фиксируем:
    - K;
    - N;
    - R;
    - lambda_k;
    - sigma_k;
    - распределение ресурса;

    Меняется только распределение объёма работы при одном и том же среднем.

    На выходе:
    raw_results:
        список всех отдельных прогонов;
    summary_rows:
        агрегированные строки по каждому распределению.
    """
    workload_family = standard_workload_family(mean=mean_workload)

    raw_results: list[SimulationResult] = []
    summary_rows: list[dict[str, Any]] = []

    for workload_name, workload_cfg in workload_family.items():
        scenario = build_base_scenario(
            workload_cfg,
            name_suffix=f"_{workload_name}",
        )
        # Для быстрой переделки параметров прогона, чтобы не лезть в params
        if replications_override is not None:
            scenario.simulation.replications = replications_override
        if max_time_override is not None:
            scenario.simulation.max_time = max_time_override
        if warmup_time_override is not None:
            scenario.simulation.warmup_time = warmup_time_override

        scenario.validate()
        scenario_results: list[SimulationResult] = []

        for replication_index in range(scenario.simulation.replications):
            result = simulate_one_run(scenario, replication_index=replication_index)
            raw_results.append(result)
            scenario_results.append(result)

        summary = aggregate_results(scenario_results, workload_name=workload_name)
        summary_rows.append(summary)

    return raw_results, summary_rows

# Результаты в csv

def build_raw_rows(results: list[SimulationResult]) -> list[dict[str, Any]]:
    """
    Преобразует список SimulationResult в список словарей для CSV.
    """
    return [result.flat_summary() for result in results]

# 3, 2, 1, ПУСК!

def run_all_experiments(
    *,
    mean_workload: float = 1.0,
    replications_override: int | None = None,
    max_time_override: float | None = None,
    warmup_time_override: float | None = None,
    results_dir: str = "results",
) -> dict[str, Path]:
    dirs = ensure_results_dirs(results_dir)

    raw_results, summary_rows = run_workload_sensitivity_experiments(
        mean_workload=mean_workload,
        replications_override=replications_override,
        max_time_override=max_time_override,
        warmup_time_override=warmup_time_override,
    )

    raw_rows = build_raw_rows(raw_results)

    run_results_path = dirs["raw"] / "run_results.csv"
    summary_results_path = dirs["raw"] / "summary_results.csv"

    save_dict_rows_to_csv(raw_rows, run_results_path)
    save_dict_rows_to_csv(summary_rows, summary_results_path)

    print("Эксперименты завершены.")
    print(f"Сырые результаты сохранены в: {run_results_path}")
    print(f"Агрегированные результаты сохранены в: {summary_results_path}")

    return {
        "run_results_csv": run_results_path,
        "summary_results_csv": summary_results_path,
    }

# Позволяет запустить experiments.py отдельно без run.py.

if __name__ == "__main__":
    # Для self-test делаем серию короткой,
    # чтобы можно было быстро проверить работоспособность.
    run_all_experiments(
        mean_workload=1.0,
        replications_override=3,
        max_time_override=2_000.0,
        warmup_time_override=200.0,
    )