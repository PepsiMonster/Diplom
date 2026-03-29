"""
Этот файлик:
1. читает агрегированные результаты из summary_results.csv;
2. строит базовые графики;
3. сохраняет их в папку results/figures/.

В этой минимальной версии строятся:
1. среднее число заявок в системе;
2. вероятность отказа;
3. эффективная пропускная способность;
4. стационарное распределение pi_hat(k) для разных распределений объёма работы.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

# Загрузка данных из csv, созданных в experiments

def load_summary_rows(summary_csv_path: Path) -> list[dict[str, Any]]:
    """
    Читает summary_results.csv и возвращает список строк в виде словарей.
    """
    if not summary_csv_path.exists():
        raise FileNotFoundError(f"Файл не найден: {summary_csv_path}")

    rows: list[dict[str, Any]] = []

    with summary_csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_row: dict[str, Any] = {}
            for key, value in row.items():
                if value is None:
                    parsed_row[key] = value
                    continue
                # Пробуем интерпретировать строку как число.
                # Если не получается, оставляем как текст.
                try:
                    if "." in value or "e" in value.lower():
                        parsed_row[key] = float(value)
                    else:
                        parsed_row[key] = int(value)
                except ValueError:
                    parsed_row[key] = value
            rows.append(parsed_row)
    return rows

# Вспомогательные функции для директорий 

def ensure_figure_dir(results_dir: str = "results") -> Path:
    figures_dir = Path(results_dir) / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    return figures_dir

# Эти функции помогают не дублировать одну и ту же логику при построении нескольких графиков.

def get_workload_names(summary_rows: list[dict[str, Any]]) -> list[str]:
    """
    Возвращает список названий распределений объёма работы
    в том порядке, в котором они идут в summary_results.csv.
    """
    return [str(row["workload_name"]) for row in summary_rows]


def get_metric_values(summary_rows: list[dict[str, Any]], metric_name: str) -> list[float]:
    """
    Извлекает один столбец числовой метрики из списка summary-строк.
    """
    return [float(row[metric_name]) for row in summary_rows]


def get_pi_columns(summary_rows: list[dict[str, Any]]) -> list[str]:
    """
    Возвращает список столбцов вида pi_hat_k_mean, отсортированных по k.
    Это нужно для построения графика стационарного распределения.
    """
    if not summary_rows:
        return []

    keys = summary_rows[0].keys()
    pi_keys = [key for key in keys if key.startswith("pi_hat_") and key.endswith("_mean")]

    def state_index(key: str) -> int:
        return int(key.replace("pi_hat_", "").replace("_mean", "")) # Формат ключа: pi_hat_{k}_mean

    pi_keys.sort(key=state_index)
    return pi_keys

# Графики по агрегированным метрикам

def plot_metric_bar(
    summary_rows: list[dict[str, Any]],
    metric_name: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    """
    Столбец по 1й метрике, например: 
    - среднее число заявок;
    - вероятность отказа;
    - throughput.
    """
    workload_names = get_workload_names(summary_rows)
    values = get_metric_values(summary_rows, metric_name)

    plt.figure(figsize=(10, 6))
    plt.bar(workload_names, values)
    plt.xlabel("Распределение объёма работы")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_stationary_distribution(
    summary_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Строит график оценок стационарного распределения pi_hat(k)
    для всех сравниваемых распределений объёма работы:
    По оси X — состояние k,
    по оси Y — оценка pi_hat(k),
    """
    pi_columns = get_pi_columns(summary_rows)
    if not pi_columns:
        return

    # Восстанавливаем список состояний k.
    states = [int(col.replace("pi_hat_", "").replace("_mean", "")) for col in pi_columns]

    plt.figure(figsize=(10, 6))

    for row in summary_rows:
        workload_name = str(row["workload_name"])
        values = [float(row[col]) for col in pi_columns]
        plt.plot(states, values, marker="o", label=workload_name)

    plt.xlabel("Состояние системы k")
    plt.ylabel("Оценка стационарной вероятности")
    plt.title("Сравнение оценок стационарного распределения")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()



def build_all_plots(results_dir: str = "results") -> dict[str, Path]:
    """
    Строит все графики, вызывается в run.py
    """
    results_root = Path(results_dir)
    summary_csv_path = results_root / "raw" / "summary_results.csv"
    figures_dir = ensure_figure_dir(results_dir)

    summary_rows = load_summary_rows(summary_csv_path)

    mean_num_jobs_path = figures_dir / "mean_num_jobs.png"
    loss_probability_path = figures_dir / "loss_probability.png"
    throughput_path = figures_dir / "throughput.png"
    stationary_distribution_path = figures_dir / "stationary_distribution.png"

    plot_metric_bar(
        summary_rows=summary_rows,
        metric_name="mean_num_jobs_mean",
        ylabel="Среднее число заявок",
        title="Среднее число заявок для разных распределений объёма работы",
        output_path=mean_num_jobs_path,
    )

    plot_metric_bar(
        summary_rows=summary_rows,
        metric_name="loss_probability_mean",
        ylabel="Вероятность отказа",
        title="Вероятность отказа для разных распределений объёма работы",
        output_path=loss_probability_path,
    )

    plot_metric_bar(
        summary_rows=summary_rows,
        metric_name="throughput_mean",
        ylabel="Эффективная пропускная способность",
        title="Пропускная способность для разных распределений объёма работы",
        output_path=throughput_path,
    )

    plot_stationary_distribution(
        summary_rows=summary_rows,
        output_path=stationary_distribution_path,
    )

    return {
        "mean_num_jobs_png": mean_num_jobs_path,
        "loss_probability_png": loss_probability_path,
        "throughput_png": throughput_path,
        "stationary_distribution_png": stationary_distribution_path,
    }

# Отдельный запуск вне run

if __name__ == "__main__":
    build_all_plots()
