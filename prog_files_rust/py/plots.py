from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


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


def load_suite_data(input_path: str | Path) -> dict[str, Any]:
    json_path = resolve_suite_result_json(input_path)
    return json.loads(json_path.read_text(encoding="utf-8"))


def available_metric_names(suite_data: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for payload in suite_data["scenario_results"].values():
        names.update(payload.get("metric_summaries", {}).keys())
    return sorted(names)


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яЁё._-]+", "_", name).strip("._")
    return cleaned or "plot"


def extract_metric_vectors(
    suite_data: dict[str, Any], metric_name: str
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    labels: list[str] = []
    means: list[float] = []
    ci_lows: list[float] = []
    ci_highs: list[float] = []

    for key, scenario in suite_data["scenario_results"].items():
        metric = scenario.get("metric_summaries", {}).get(metric_name)
        if metric is None:
            continue
        labels.append(key)
        means.append(float(metric["mean"]))
        ci_lows.append(float(metric["ci_low"]))
        ci_highs.append(float(metric["ci_high"]))

    if not labels:
        raise ValueError(f"Метрика '{metric_name}' отсутствует в наборе результатов.")

    return (
        labels,
        np.asarray(means, dtype=float),
        np.asarray(ci_lows, dtype=float),
        np.asarray(ci_highs, dtype=float),
    )


def plot_metric_comparison(
    suite_data: dict[str, Any], metric_name: str, output_dir: Path
) -> Path:
    labels, means, ci_lows, ci_highs = extract_metric_vectors(suite_data, metric_name)

    x = np.arange(len(labels))
    yerr_lower = np.maximum(means - ci_lows, 0.0)
    yerr_upper = np.maximum(ci_highs - means, 0.0)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, means, color="#4C78A8", alpha=0.9)
    ax.errorbar(
        x,
        means,
        yerr=np.vstack([yerr_lower, yerr_upper]),
        fmt="none",
        ecolor="#111111",
        elinewidth=1.2,
        capsize=4,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title(f"{metric_name}: сравнение по сценариям")
    ax.set_ylabel(metric_name)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    out_path = output_dir / f"metric_{sanitize_filename(metric_name)}.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def extract_run_values(suite_data: dict[str, Any], metric_name: str) -> tuple[list[str], list[list[float]]]:
    labels: list[str] = []
    all_values: list[list[float]] = []

    for key, scenario in suite_data["scenario_results"].items():
        runs = scenario.get("run_summaries", [])
        values = [float(row[metric_name]) for row in runs if metric_name in row]
        if values:
            labels.append(key)
            all_values.append(values)

    if not all_values:
        raise ValueError(f"Метрика '{metric_name}' не найдена на уровне отдельных прогонов.")

    return labels, all_values


def plot_metric_boxplot(suite_data: dict[str, Any], metric_name: str, output_dir: Path) -> Path:
    labels, all_values = extract_run_values(suite_data, metric_name)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot(all_values, labels=labels, showmeans=True)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title(f"{metric_name}: распределение по прогонам")
    ax.set_ylabel(metric_name)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    out_path = output_dir / f"boxplot_{sanitize_filename(metric_name)}.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_stationary_distribution(suite_data: dict[str, Any], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))

    state_keys: set[int] = set()
    for scenario in suite_data["scenario_results"].values():
        for metric_name in scenario.get("metric_summaries", {}).keys():
            if metric_name.startswith("pi_hat_"):
                state_keys.add(int(metric_name.replace("pi_hat_", "")))

    states = sorted(state_keys)
    for label, scenario in suite_data["scenario_results"].items():
        y_values = []
        for state in states:
            key = f"pi_hat_{state}"
            value = scenario.get("metric_summaries", {}).get(key, {}).get("mean", 0.0)
            y_values.append(float(value))
        ax.plot(states, y_values, marker="o", linewidth=1.8, label=label)

    ax.set_xlabel("Состояние k")
    ax.set_ylabel("pi_hat(k)")
    ax.set_title("Стационарное распределение по сценариям")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    out_path = output_dir / "stationary_distribution.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_rejection_breakdown(suite_data: dict[str, Any], output_dir: Path) -> Path:
    labels = list(suite_data["scenario_results"].keys())
    cap: list[float] = []
    srv: list[float] = []
    res: list[float] = []

    for scenario in suite_data["scenario_results"].values():
        ms = scenario.get("metric_summaries", {})
        cap.append(float(ms.get("rejected_capacity", {}).get("mean", 0.0)))
        srv.append(float(ms.get("rejected_server", {}).get("mean", 0.0)))
        res.append(float(ms.get("rejected_resource", {}).get("mean", 0.0)))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, cap, label="rejected_capacity")
    ax.bar(x, srv, bottom=cap, label="rejected_server")
    ax.bar(x, res, bottom=np.array(cap) + np.array(srv), label="rejected_resource")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title("Декомпозиция отказов")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    out_path = output_dir / "rejection_breakdown.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_pi_hat_heatmap(suite_data: dict[str, Any], output_dir: Path) -> Path:
    labels = list(suite_data["scenario_results"].keys())
    state_keys: set[int] = set()
    for scenario in suite_data["scenario_results"].values():
        for metric_name in scenario.get("metric_summaries", {}).keys():
            if metric_name.startswith("pi_hat_"):
                state_keys.add(int(metric_name.replace("pi_hat_", "")))

    states = sorted(state_keys)
    matrix = np.zeros((len(labels), len(states)))
    for i, scenario in enumerate(suite_data["scenario_results"].values()):
        ms = scenario.get("metric_summaries", {})
        for j, state in enumerate(states):
            matrix[i, j] = float(ms.get(f"pi_hat_{state}", {}).get("mean", 0.0))

    fig, ax = plt.subplots(figsize=(12, 6))
    img = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_xticks(np.arange(len(states)))
    ax.set_xticklabels([str(s) for s in states], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_title("Тепловая карта pi_hat(k)")
    fig.colorbar(img, ax=ax)
    fig.tight_layout()

    out_path = output_dir / "pi_hat_heatmap.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def generate_standard_plots(
    suite_data: dict[str, Any], output_dir: Path, extra_metrics: list[str] | None = None
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
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

    for metric in extra_metrics or []:
        if metric not in default_metrics:
            default_metrics.append(metric)

    available = set(available_metric_names(suite_data))
    for metric in default_metrics:
        if metric in available:
            created.append(plot_metric_comparison(suite_data, metric, output_dir))
            try:
                created.append(plot_metric_boxplot(suite_data, metric, output_dir))
            except Exception:
                pass

    if any(name.startswith("pi_hat_") for name in available):
        created.append(plot_stationary_distribution(suite_data, output_dir))
        created.append(plot_pi_hat_heatmap(suite_data, output_dir))

    if {"rejected_capacity", "rejected_server", "rejected_resource"}.issubset(available):
        created.append(plot_rejection_breakdown(suite_data, output_dir))

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Python plotting for prog_files_rust suite outputs")
    parser.add_argument("--input", required=True, help="Path to suite_result.json or its parent directory")
    parser.add_argument("--output-dir", required=True, help="Directory to save plots")
    parser.add_argument("--metrics", nargs="*", default=[], help="Additional metric names")
    args = parser.parse_args()

    suite_data = load_suite_data(args.input)
    output_dir = Path(args.output_dir)
    created = generate_standard_plots(suite_data, output_dir, args.metrics)
    print(f"Python plots generated: {len(created)} files in {output_dir}")


if __name__ == "__main__":
    main()
