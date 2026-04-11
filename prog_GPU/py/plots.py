from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import argparse
import json
import math
import re

import matplotlib.pyplot as plt
import numpy as np


# ============================================================================
# БАЗОВЫЕ НАСТРОЙКИ ВИЗУАЛИЗАЦИИ
# ============================================================================

plt.rcParams["figure.figsize"] = (10, 5.8)
plt.rcParams["axes.grid"] = False
plt.rcParams["axes.titlesize"] = 15
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11
plt.rcParams["legend.fontsize"] = 11
plt.rcParams["font.size"] = 11


# ============================================================================
# СТРУКТУРЫ ДАННЫХ
# ============================================================================

@dataclass(slots=True)
class PlotSuiteData:
    suite_name: str
    created_at: str
    ci_level: float
    scenario_results: dict[str, dict[str, Any]]

    def scenario_keys(self) -> list[str]:
        return list(self.scenario_results.keys())

    def scenario_labels(self) -> list[str]:
        """
        Для графиков предпочтительнее использовать scenario_name.
        Если scenario_name повторяются, откатываемся к scenario_key.
        """
        keys = self.scenario_keys()
        names = [
            str(self.scenario_results[key].get("scenario_name", key))
            for key in keys
        ]

        if len(set(names)) == len(names):
            return names

        return keys


# ============================================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================================

def _read_json(filepath: str | Path) -> dict[str, Any]:
    path = Path(filepath)
    return json.loads(path.read_text(encoding="utf-8"))


def load_suite_data_from_json(filepath: str | Path) -> PlotSuiteData:
    payload = _read_json(filepath)
    return PlotSuiteData(
        suite_name=str(payload["suite_name"]),
        created_at=str(payload["created_at"]),
        ci_level=float(payload.get("ci_level", 0.95)),
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


# ============================================================================
# ИЗВЛЕЧЕНИЕ МЕТРИК
# ============================================================================

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

    scenario_keys = suite_data.scenario_keys()
    scenario_labels = suite_data.scenario_labels()

    for scenario_key, label in zip(scenario_keys, scenario_labels):
        summary = _metric_summary(suite_data, scenario_key, metric_name)
        labels.append(label)
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

    scenario_keys = suite_data.scenario_keys()
    scenario_labels = suite_data.scenario_labels()

    for scenario_key, label in zip(scenario_keys, scenario_labels):
        payload = suite_data.scenario_results[scenario_key]
        run_summaries = payload.get("run_summaries", [])
        values: list[float] = []
        for row in run_summaries:
            if metric_name in row:
                values.append(float(row[metric_name]))
        if values:
            labels.append(label)
            all_values.append(values)

    if not all_values:
        raise KeyError(
            f"Метрика '{metric_name}' не найдена на уровне отдельных прогонов"
        )

    return labels, all_values


def extract_pi_hat_matrix(
    suite_data: PlotSuiteData,
) -> tuple[list[str], list[int], np.ndarray]:
    scenario_keys = suite_data.scenario_keys()
    labels = suite_data.scenario_labels()

    state_indices: set[int] = set()
    for scenario_key in scenario_keys:
        payload = suite_data.scenario_results[scenario_key]
        for metric_name in payload.get("metric_summaries", {}):
            if metric_name.startswith("pi_hat_"):
                state_indices.add(int(metric_name.replace("pi_hat_", "")))

    if not state_indices:
        raise ValueError("В наборе результатов нет метрик вида pi_hat_k")

    states = sorted(state_indices)
    matrix = np.zeros((len(labels), len(states)), dtype=float)

    for i, scenario_key in enumerate(scenario_keys):
        payload = suite_data.scenario_results[scenario_key]
        for j, state in enumerate(states):
            name = f"pi_hat_{state}"
            if name in payload.get("metric_summaries", {}):
                matrix[i, j] = float(payload["metric_summaries"][name]["mean"])

    return labels, states, matrix


# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9А-Яа-я_.-]+", "_", name.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "plot"


def _ensure_dir(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def _save_figure(fig: plt.Figure, output_path: str | Path, *, dpi: int = 220) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out


def _set_rotated_xticklabels(ax: plt.Axes, labels: list[str]) -> None:
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")


def _auto_zoom_ylim(
    ax: plt.Axes,
    values: np.ndarray,
    lower_errors: np.ndarray | None = None,
    upper_errors: np.ndarray | None = None,
    *,
    include_zero: bool = False,
) -> None:
    arr = np.asarray(values, dtype=float)

    ymin = float(arr.min())
    ymax = float(arr.max())

    if lower_errors is not None:
        ymin = min(ymin, float(np.min(arr - lower_errors)))
    if upper_errors is not None:
        ymax = max(ymax, float(np.max(arr + upper_errors)))

    if include_zero:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)

    span = ymax - ymin

    if span <= 1e-14:
        margin = max(abs(ymax) * 0.02, 1e-6)
    else:
        margin = max(0.15 * span, 1e-6)

    ax.set_ylim(ymin - margin, ymax + margin)


def _format_metric_axis(ax: plt.Axes, values: np.ndarray) -> None:
    vmax = float(np.max(np.abs(values))) if len(values) else 1.0

    if vmax >= 1000:
        ax.ticklabel_format(axis="y", style="plain")
    elif vmax >= 1:
        pass
    elif vmax >= 1e-2:
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter("%.4f"))
    else:
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter("%.6f"))


def _baseline_percent_delta(values: np.ndarray) -> np.ndarray:
    base = float(values[0])
    if abs(base) <= 1e-14:
        return np.zeros_like(values)
    return (values / base - 1.0) * 100.0


def _metric_display_name(metric_name: str) -> str:
    replacements = {
        "mean_num_jobs": "Среднее число заявок",
        "mean_occupied_resource": "Средний занятый ресурс",
        "loss_probability": "Вероятность отказа",
        "throughput": "Пропускная способность",
        "accepted_arrivals": "Принятые поступления",
        "rejected_arrivals": "Отказы",
        "completed_jobs": "Завершённые заявки",
        "rejected_capacity": "Отказы по K",
        "rejected_server": "Отказы по N",
        "rejected_resource": "Отказы по R",
        "mean_queue_length": "Средняя длина очереди",
        "queueing_probability": "Вероятность попадания в очередь",
        "mean_service_time": "Среднее время обслуживания",
        "mean_waiting_time": "Среднее время ожидания",
        "mean_sojourn_time": "Среднее время пребывания",
        "std_service_time": "Std времени обслуживания",
        "std_sojourn_time": "Std времени пребывания",
        "arrival_attempts": "Попытки поступления",
        "completed_time_samples": "Число завершений в окне",
    }
    return replacements.get(metric_name, metric_name)


def _metric_unit(metric_name: str) -> str | None:
    time_metrics = {
        "mean_service_time",
        "mean_waiting_time",
        "mean_sojourn_time",
        "std_service_time",
        "std_waiting_time",
        "std_sojourn_time",
        "total_time",
        "warmup_time",
        "observed_time",
    }
    probability_metrics = {"loss_probability", "queueing_probability"}
    jobs_count_metrics = {
        "mean_num_jobs",
        "mean_queue_length",
        "mean_waiting_jobs",
        "accepted_arrivals",
        "rejected_arrivals",
        "completed_jobs",
        "rejected_capacity",
        "rejected_server",
        "rejected_resource",
        "arrival_attempts",
        "completed_time_samples",
    }
    rate_metrics = {"throughput"}

    if metric_name in time_metrics:
        return "ед. времени"
    if metric_name in probability_metrics:
        return "доля"
    if metric_name in jobs_count_metrics:
        return "заявки"
    if metric_name in rate_metrics:
        return "заявки / ед. времени"
    return None


def _metric_ylabel(metric_name: str) -> str:
    unit = _metric_unit(metric_name)
    title = _metric_display_name(metric_name)
    return f"{title} [{unit}]" if unit else title


def _suite_is_loss_only(suite_data: PlotSuiteData) -> bool:
    """
    Новая ветка проекта — loss-only.
    Но оставляем проверку на случай смешанных JSON в будущем:
    если нет ни одной очередной метрики, считаем это loss-only.
    """
    available = set(available_metric_names(suite_data))
    queue_metrics = {
        "mean_queue_length",
        "queueing_probability",
        "mean_waiting_time",
        "mean_waiting_jobs",
    }
    return len(queue_metrics & available) == 0


# ============================================================================
# ГРАФИКИ
# ============================================================================

def plot_metric_comparison(
    suite_data: PlotSuiteData,
    metric_name: str,
    output_dir: str | Path,
    *,
    dpi: int = 220,
    title: str | None = None,
    zoom_y: bool = True,
) -> Path:
    labels, means, ci_lows, ci_highs = extract_metric_vectors(suite_data, metric_name)

    lower_errors = means - ci_lows
    upper_errors = ci_highs - means
    errors = np.vstack((lower_errors, upper_errors))

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(labels))

    ax.bar(
        x,
        means,
        yerr=errors,
        capsize=5,
        alpha=0.88,
        edgecolor="black",
        linewidth=0.8,
    )
    _set_rotated_xticklabels(ax, labels)
    ax.set_ylabel(_metric_ylabel(metric_name))
    ax.set_title(title or f"{_metric_display_name(metric_name)}: сравнение по сценариям")
    ax.grid(axis="y", alpha=0.25)

    if zoom_y:
        _auto_zoom_ylim(ax, means, lower_errors, upper_errors, include_zero=False)
    else:
        ax.set_ylim(bottom=0.0)

    _format_metric_axis(ax, means)

    filename = f"metric_{_sanitize_filename(metric_name)}.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


def plot_metric_comparison_delta(
    suite_data: PlotSuiteData,
    metric_name: str,
    output_dir: str | Path,
    *,
    dpi: int = 220,
    baseline_label: str | None = None,
) -> Path:
    labels, means, _, _ = extract_metric_vectors(suite_data, metric_name)
    deltas = _baseline_percent_delta(means)

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(labels))

    ax.bar(x, deltas, alpha=0.88, edgecolor="black", linewidth=0.8)
    _set_rotated_xticklabels(ax, labels)

    if baseline_label is None:
        baseline_label = labels[0]

    ax.axhline(0.0, color="black", linewidth=1.0, alpha=0.8)
    ax.set_ylabel(f"Отклонение от {baseline_label}, %")
    ax.set_title(f"{_metric_display_name(metric_name)}: отклонение от baseline")
    ax.grid(axis="y", alpha=0.25)

    _auto_zoom_ylim(ax, deltas, include_zero=True)
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter("%.3f"))

    filename = f"metric_delta_{_sanitize_filename(metric_name)}.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


def plot_metric_boxplot(
    suite_data: PlotSuiteData,
    metric_name: str,
    output_dir: str | Path,
    *,
    dpi: int = 220,
    title: str | None = None,
) -> Path:
    labels, values = extract_run_values(suite_data, metric_name)

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.boxplot(values, tick_labels=labels, patch_artist=True)

    for patch in ax.artists:
        patch.set_alpha(0.75)

    ax.set_ylabel(_metric_ylabel(metric_name))
    ax.set_title(title or f"{_metric_display_name(metric_name)}: разброс по replication")
    ax.grid(axis="y", alpha=0.25)

    for tick in ax.get_xticklabels():
        tick.set_rotation(25)
        tick.set_ha("right")

    all_vals = np.asarray([v for group in values for v in group], dtype=float)
    _auto_zoom_ylim(ax, all_vals, include_zero=False)
    _format_metric_axis(ax, all_vals)

    filename = f"boxplot_{_sanitize_filename(metric_name)}.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


def plot_stationary_distribution_by_scenarios(
    suite_data: PlotSuiteData,
    output_dir: str | Path,
    *,
    dpi: int = 220,
) -> Path:
    labels, states, matrix = extract_pi_hat_matrix(suite_data)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for i, scenario_label in enumerate(labels):
        ax.plot(states, matrix[i, :], marker="o", linewidth=2.0, label=scenario_label)

    ax.set_xlabel("Состояние k")
    ax.set_ylabel(r"$\hat{\pi}(k)$")
    ax.set_title("Оценка стационарного распределения по числу заявок")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)
    ax.set_xlim(min(states), max(states))

    filename = "stationary_distribution.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


def plot_rejection_breakdown(
    suite_data: PlotSuiteData,
    output_dir: str | Path,
    *,
    dpi: int = 220,
) -> Path:
    scenario_keys = suite_data.scenario_keys()
    labels = suite_data.scenario_labels()

    capacity = []
    server = []
    resource = []

    for scenario_key in scenario_keys:
        capacity.append(_metric_summary(suite_data, scenario_key, "rejected_capacity")["mean"])
        server.append(_metric_summary(suite_data, scenario_key, "rejected_server")["mean"])
        resource.append(_metric_summary(suite_data, scenario_key, "rejected_resource")["mean"])

    capacity_arr = np.asarray(capacity, dtype=float)
    server_arr = np.asarray(server, dtype=float)
    resource_arr = np.asarray(resource, dtype=float)

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(labels))

    ax.bar(x, capacity_arr, label="rejected_capacity", alpha=0.9)
    ax.bar(x, server_arr, bottom=capacity_arr, label="rejected_server", alpha=0.9)
    ax.bar(
        x,
        resource_arr,
        bottom=capacity_arr + server_arr,
        label="rejected_resource",
        alpha=0.9,
    )

    _set_rotated_xticklabels(ax, labels)
    ax.set_ylabel("Среднее число отказов")
    ax.set_title("Декомпозиция отказов")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()

    total = capacity_arr + server_arr + resource_arr
    _auto_zoom_ylim(ax, total, include_zero=True)

    filename = "rejection_breakdown.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


def plot_scenario_heatmap_pi(
    suite_data: PlotSuiteData,
    output_dir: str | Path,
    *,
    dpi: int = 220,
) -> Path:
    labels, states, matrix = extract_pi_hat_matrix(suite_data)

    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    im = ax.imshow(matrix, aspect="auto", interpolation="nearest")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    n_states = len(states)
    max_ticks = 20
    step = max(1, math.ceil(n_states / max_ticks))
    tick_positions = np.arange(0, n_states, step)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([states[idx] for idx in tick_positions], rotation=45, ha="right")
    ax.set_xlabel("Состояние k")
    ax.set_ylabel("Сценарий")
    ax.set_title("Тепловая карта pi_hat(k)")
    fig.colorbar(im, ax=ax)

    filename = "pi_hat_heatmap.png"
    return _save_figure(fig, Path(output_dir) / filename, dpi=dpi)


# ============================================================================
# ПОЛНЫЙ НАБОР ГРАФИКОВ
# ============================================================================

def generate_standard_plots(
    suite_data: PlotSuiteData,
    output_dir: str | Path,
    *,
    dpi: int = 220,
    extra_metrics: Iterable[str] | None = None,
    build_delta_plots: bool = True,
) -> list[Path]:
    out_dir = _ensure_dir(output_dir)
    created: list[Path] = []

    default_metrics = [
        "mean_num_jobs",
        "mean_occupied_resource",
        "loss_probability",
        "throughput",
        "mean_service_time",
        "mean_sojourn_time",
    ]

    if extra_metrics is not None:
        for metric in extra_metrics:
            if metric not in default_metrics:
                default_metrics.append(metric)

    available = set(available_metric_names(suite_data))
    is_loss_only = _suite_is_loss_only(suite_data)

    if (
        not is_loss_only
        and "mean_queue_length" in available
        and "mean_queue_length" not in default_metrics
    ):
        default_metrics.append("mean_queue_length")
    if (
        not is_loss_only
        and "queueing_probability" in available
        and "queueing_probability" not in default_metrics
    ):
        default_metrics.append("queueing_probability")
    if (
        not is_loss_only
        and "mean_waiting_time" in available
        and "mean_waiting_time" not in default_metrics
    ):
        default_metrics.append("mean_waiting_time")

    for metric in default_metrics:
        if metric in available:
            created.append(
                plot_metric_comparison(
                    suite_data,
                    metric,
                    out_dir,
                    dpi=dpi,
                    zoom_y=True,
                )
            )

            if (
                build_delta_plots
                and metric in {"loss_probability", "throughput", "mean_num_jobs", "mean_occupied_resource"}
                and len(suite_data.scenario_keys()) >= 2
            ):
                created.append(
                    plot_metric_comparison_delta(
                        suite_data,
                        metric,
                        out_dir,
                        dpi=dpi,
                    )
                )

            if metric in {
                "loss_probability",
                "mean_queue_length",
                "mean_service_time",
                "mean_waiting_time",
                "mean_sojourn_time",
            } and not (is_loss_only and metric in {"mean_queue_length", "mean_waiting_time"}):
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


# ============================================================================
# ПЕЧАТЬ МЕТРИК
# ============================================================================

def print_available_metrics(suite_data: PlotSuiteData) -> None:
    print("=" * 80)
    print(f"Набор результатов: {suite_data.suite_name}")
    print(f"Создан: {suite_data.created_at}")
    print(f"CI level: {suite_data.ci_level}")
    print(f"Сценариев: {len(suite_data.scenario_results)}")
    print("-" * 80)
    print("Доступные агрегированные метрики:")
    for name in available_metric_names(suite_data):
        print(f"  - {name}")
    print("=" * 80)


# ============================================================================
# CLI
# ============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Построение графиков по результатам экспериментов"
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
        default=220,
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
    parser.add_argument(
        "--no-delta-plots",
        action="store_true",
        help="Не строить графики отклонения от baseline в процентах",
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

    created = generate_standard_plots(
        suite_data,
        output_dir=output_dir,
        dpi=args.dpi,
        extra_metrics=args.metrics,
        build_delta_plots=not args.no_delta_plots,
    )

    print("=" * 80)
    print(f"Графики сохранены в: {output_dir}")
    print(f"Создано файлов: {len(created)}")
    for path in created:
        print(f"  - {path}")
    print("=" * 80)


if __name__ == "__main__":
    main()