from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Iterable

import argparse

import json

import re

import matplotlib.pyplot as plt

import numpy as np

@dataclass(slots=True)

class PlotSuiteData:

    suite_name: str

    created_at: str

    scenario_results: dict[str, dict[str, Any]]

    def scenario_keys(self) -> list[str]:

        return list(self.scenario_results.keys())

def _read_json(filepath: str | Path) -> dict[str, Any]:

    path = Path(filepath)

    return json.loads(path.read_text(encoding="utf-8"))

def load_suite_data_from_json(filepath: str | Path) -> PlotSuiteData:

    payload = _read_json(filepath)

    return PlotSuiteData(

        suite_name=str(payload["suite_name"]),

        created_at=str(payload["created_at"]),

        scenario_results=dict(payload["scenario_results"]),

    )

def resolve_suite_result_json(input_path: str | Path) -> Path:

    path = Path(input_path)

    if path.is_dir():

        candidate = path / "suite_result.json"

        if not candidate.exists():

            raise FileNotFoundError(

                f"В директории '{path}' не найден файл suite_result.json"

            )

        return candidate

    if path.is_file():

        if path.name.lower() != "suite_result.json" and path.suffix.lower() != ".json":

            raise ValueError(

                f"Ожидался JSON-файл результата или директория результата, получено: {path}"

            )

        return path

    raise FileNotFoundError(f"Путь не найден: {path}")

def load_suite_data(input_path: str | Path) -> PlotSuiteData:

    json_path = resolve_suite_result_json(input_path)

    return load_suite_data_from_json(json_path)

def _metric_summary(

    suite_data: PlotSuiteData,

    scenario_key: str,

    metric_name: str,

) -> dict[str, Any]:

    scenario = suite_data.scenario_results[scenario_key]

    metric_summaries = scenario.get("metric_summaries", {})

    if metric_name not in metric_summaries:

        raise KeyError(

            f"Метрика '{metric_name}' отсутствует в сценарии '{scenario_key}'"

        )

    return dict(metric_summaries[metric_name])

def available_metric_names(suite_data: PlotSuiteData) -> list[str]:

    names: set[str] = set()

    for payload in suite_data.scenario_results.values():

        metric_summaries = payload.get("metric_summaries", {})

        names.update(metric_summaries.keys())

    return sorted(names)

def extract_metric_vectors(

    suite_data: PlotSuiteData,

    metric_name: str,

) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:

    labels: list[str] = []

    means: list[float] = []

    ci_lows: list[float] = []

    ci_highs: list[float] = []

    for scenario_key in suite_data.scenario_keys():

        summary = _metric_summary(suite_data, scenario_key, metric_name)

        labels.append(str(scenario_key))

        means.append(float(summary["mean"]))

        ci_lows.append(float(summary["ci_low"]))

        ci_highs.append(float(summary["ci_high"]))

    return (

        labels,

        np.asarray(means, dtype=float),

        np.asarray(ci_lows, dtype=float),

        np.asarray(ci_highs, dtype=float),

    )

def extract_run_values(

    suite_data: PlotSuiteData,

    metric_name: str,

) -> tuple[list[str], list[list[float]]]:

    labels: list[str] = []

    all_values: list[list[float]] = []

    for scenario_key in suite_data.scenario_keys():

        payload = suite_data.scenario_results[scenario_key]

        run_summaries = payload.get("run_summaries", [])

        values: list[float] = []

        for row in run_summaries:

            if metric_name in row:

                values.append(float(row[metric_name]))

        if values:

            labels.append(str(scenario_key))

            all_values.append(values)

    if not all_values:

        raise KeyError(f"Метрика '{metric_name}' не найдена на уровне отдельных прогонов")

    return labels, all_values

def extract_pi_hat_matrix(

    suite_data: PlotSuiteData,

) -> tuple[list[str], list[int], np.ndarray]:

    labels = suite_data.scenario_keys()

    state_indices: set[int] = set()

    for scenario_key in labels:

        payload = suite_data.scenario_results[scenario_key]

        for metric_name in payload.get("metric_summaries", {}):

            if metric_name.startswith("pi_hat_"):

                state_indices.add(int(metric_name.replace("pi_hat_", "")))

    if not state_indices:

        raise ValueError("В наборе результатов нет метрик вида pi_hat_k")

    states = sorted(state_indices)

    matrix = np.zeros((len(labels), len(states)), dtype=float)

    for i, scenario_key in enumerate(labels):

        for j, state in enumerate(states):

            name = f"pi_hat_{state}"

            payload = suite_data.scenario_results[scenario_key]

            if name in payload.get("metric_summaries", {}):

                matrix[i, j] = float(payload["metric_summaries"][name]["mean"])

    return labels, states, matrix

def _sanitize_filename(name: str) -> str:

    cleaned = re.sub(r"[^A-Za-z0-9А-Яа-я_.-]+", "_", name.strip())

    cleaned = cleaned.strip("._")

    return cleaned or "plot"

def _ensure_dir(path: str | Path) -> Path:

    path_obj = Path(path)

    path_obj.mkdir(parents=True, exist_ok=True)

    return path_obj

def _save_figure(fig: plt.Figure, output_path: str | Path, *, dpi: int = 200) -> Path:

    out = Path(output_path)

    out.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(out, dpi=dpi, bbox_inches="tight")

    plt.close(fig)

    return out

def plot_metric_comparison(

    suite_data: PlotSuiteData,

    metric_name: str,

    output_dir: str | Path,

    *,

    dpi: int = 200,

    title: str | None = None,

) -> Path:

    labels, means, ci_lows, ci_highs = extract_metric_vectors(suite_data, metric_name)

    errors = np.vstack((means - ci_lows, ci_highs - means))

    fig, ax = plt.subplots(figsize=(10, 5.5))

    x = np.arange(len(labels))

    ax.bar(x, means, yerr=errors, capsize=5)

    ax.set_xticks(x)

    ax.set_xticklabels(labels, rotation=20, ha="right")

    ax.set_ylabel(metric_name)

    ax.set_title(title or f"Сравнение сценариев по метрике: {metric_name}")

    ax.grid(axis="y", alpha=0.3)

    filename = f"metric_{_sanitize_filename(metric_name)}.png"

    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)

def plot_metric_boxplot(

    suite_data: PlotSuiteData,

    metric_name: str,

    output_dir: str | Path,

    *,

    dpi: int = 200,

    title: str | None = None,

) -> Path:

    labels, values = extract_run_values(suite_data, metric_name)

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.boxplot(values, tick_labels=labels)

    ax.set_ylabel(metric_name)

    ax.set_title(title or f"Разброс replication по метрике: {metric_name}")

    ax.grid(axis="y", alpha=0.3)

    filename = f"boxplot_{_sanitize_filename(metric_name)}.png"

    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)

def plot_stationary_distribution_by_scenarios(

    suite_data: PlotSuiteData,

    output_dir: str | Path,

    *,

    dpi: int = 200,

) -> Path:

    labels, states, matrix = extract_pi_hat_matrix(suite_data)

    fig, ax = plt.subplots(figsize=(10, 5.5))

    for i, scenario_label in enumerate(labels):

        ax.plot(states, matrix[i, :], marker="o", label=scenario_label)

    ax.set_xlabel("Состояние k")

    ax.set_ylabel(r"$\hat{\pi}(k)$")

    ax.set_title("Оценка стационарного распределения по числу заявок")

    ax.grid(alpha=0.3)

    ax.legend()

    return _save_figure(fig, Path(output_dir) / "stationary_distribution.png", dpi=dpi)

def plot_rejection_breakdown(

    suite_data: PlotSuiteData,

    output_dir: str | Path,

    *,

    dpi: int = 200,

) -> Path:

    labels = suite_data.scenario_keys()

    capacity = []

    server = []

    resource = []

    for scenario_key in labels:

        capacity.append(_metric_summary(suite_data, scenario_key, "rejected_capacity")["mean"])

        server.append(_metric_summary(suite_data, scenario_key, "rejected_server")["mean"])

        resource.append(_metric_summary(suite_data, scenario_key, "rejected_resource")["mean"])

    capacity_arr = np.asarray(capacity, dtype=float)

    server_arr = np.asarray(server, dtype=float)

    resource_arr = np.asarray(resource, dtype=float)

    fig, ax = plt.subplots(figsize=(10, 5.5))

    x = np.arange(len(labels))

    ax.bar(x, capacity_arr, label="capacity")

    ax.bar(x, server_arr, bottom=capacity_arr, label="server")

    ax.bar(x, resource_arr, bottom=capacity_arr + server_arr, label="resource")

    ax.set_xticks(x)

    ax.set_xticklabels(labels, rotation=20, ha="right")

    ax.set_ylabel("Среднее число отказов")

    ax.set_title("Декомпозиция отказов по причинам")

    ax.grid(axis="y", alpha=0.3)

    ax.legend()

    return _save_figure(fig, Path(output_dir) / "rejection_breakdown.png", dpi=dpi)

def plot_scenario_heatmap_pi(

    suite_data: PlotSuiteData,

    output_dir: str | Path,

    *,

    dpi: int = 200,

) -> Path:

    labels, states, matrix = extract_pi_hat_matrix(suite_data)

    fig, ax = plt.subplots(figsize=(10, 5.5))

    im = ax.imshow(matrix, aspect="auto")

    ax.set_yticks(np.arange(len(labels)))

    ax.set_yticklabels(labels)

    ax.set_xticks(np.arange(len(states)))

    ax.set_xticklabels(states)

    ax.set_xlabel("Состояние k")

    ax.set_ylabel("Сценарий")

    ax.set_title("Heatmap оценок $\\hat{\\pi}(k)$")

    fig.colorbar(im, ax=ax)

    return _save_figure(fig, Path(output_dir) / "pi_hat_heatmap.png", dpi=dpi)

def generate_standard_plots(

    suite_data: PlotSuiteData,

    output_dir: str | Path,

    *,

    dpi: int = 200,

    extra_metrics: Iterable[str] | None = None,

) -> list[Path]:

    out_dir = _ensure_dir(output_dir)

    created: list[Path] = []

    default_metrics = [

        "mean_num_jobs",

        "mean_occupied_resource",

        "loss_probability",

        "throughput",

        "accepted_arrivals",

        "rejected_arrivals",

        "completed_jobs",

    ]

    if extra_metrics is not None:

        for metric in extra_metrics:

            if metric not in default_metrics:

                default_metrics.append(metric)

    available = set(available_metric_names(suite_data))

    for metric in default_metrics:

        if metric in available:

            created.append(plot_metric_comparison(suite_data, metric, out_dir, dpi=dpi))

            try:

                created.append(plot_metric_boxplot(suite_data, metric, out_dir, dpi=dpi))

            except KeyError:

                pass

    if any(name.startswith("pi_hat_") for name in available):

        created.append(plot_stationary_distribution_by_scenarios(suite_data, out_dir, dpi=dpi))

        created.append(plot_scenario_heatmap_pi(suite_data, out_dir, dpi=dpi))

    rejection_metrics = {"rejected_capacity", "rejected_server", "rejected_resource"}

    if rejection_metrics.issubset(available):

        created.append(plot_rejection_breakdown(suite_data, out_dir, dpi=dpi))

    return created

def print_available_metrics(suite_data: PlotSuiteData) -> None:

    print("=" * 80)

    print(f"Набор результатов: {suite_data.suite_name}")

    print(f"Создан: {suite_data.created_at}")

    print(f"Сценариев: {len(suite_data.scenario_results)}")

    print("-" * 80)

    print("Доступные агрегированные метрики:")

    for name in available_metric_names(suite_data):

        print(f"  - {name}")

    print("=" * 80)

def build_arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        description="Построение графиков по результатам experiments.py"

    )

    parser.add_argument(

        "--input",

        required=True,

        help="Путь к директории результата или к suite_result.json",

    )

    parser.add_argument(

        "--output-dir",

        default=None,

        help="Куда сохранять графики. По умолчанию <input>/plots",

    )

    parser.add_argument(

        "--dpi",

        type=int,

        default=200,

        help="Разрешение PNG-файлов",

    )

    parser.add_argument(

        "--list-metrics",

        action="store_true",

        help="Только показать доступные метрики без построения графиков",

    )

    parser.add_argument(

        "--metrics",

        nargs="*",

        default=None,

        help=(

            "Дополнительные метрики для стандартного набора графиков. "

            "Например: --metrics rejected_capacity rejected_server"

        ),

    )

    return parser

def main() -> None:

    parser = build_arg_parser()

    args = parser.parse_args()

    suite_data = load_suite_data(args.input)

    if args.list_metrics:

        print_available_metrics(suite_data)

        return

    json_path = resolve_suite_result_json(args.input)

    default_output_dir = json_path.parent / "plots"

    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir

    generate_standard_plots(

        suite_data,

        output_dir=output_dir,

        dpi=args.dpi,

        extra_metrics=args.metrics,

    )

    print("=" * 80)

    print(f"Графики сохранены в: {output_dir}")

    print("=" * 80)

if __name__ == "__main__":

    main()
