from __future__ import annotations

import argparse
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


# =============================================================================
# STYLE
# =============================================================================

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 220,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "axes.titleweight": "semibold",
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "#fbfbfc",
        "grid.alpha": 0.24,
        "grid.linewidth": 0.75,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


# =============================================================================
# CONSTANTS
# =============================================================================

CORE_METRICS = [
    "loss_probability",
    "throughput",
    "mean_num_jobs",
    "mean_occupied_resource",
    "mean_service_time",
    "mean_sojourn_time",
]

PRIMARY_METRICS = [
    "loss_probability",
    "throughput",
    "mean_num_jobs",
    "mean_occupied_resource",
]

BOXPLOT_METRICS = [
    "loss_probability",
    "mean_service_time",
    "mean_sojourn_time",
]

REJECTION_COMPONENTS = [
    "rejected_capacity",
    "rejected_server",
    "rejected_resource",
]

WORKLOAD_ORDER = [
    "deterministic",
    "erlang_2",
    "erlang_4",
    "erlang_8",
    "exponential",
    "hyperexp_2",
    "hyperexp_heavy",
]

ARRIVAL_ORDER = [
    "poisson",
    "erlang_2",
    "erlang_4",
    "hyperexp_2",
]

DISPLAY_NAMES = {
    "deterministic": "Детерм.",
    "exponential": "Эксп.",
    "erlang_2": "Эрланг-2",
    "erlang_4": "Эрланг-4",
    "erlang_8": "Эрланг-8",
    "hyperexp_2": "Гиперэксп.",
    "hyperexp_heavy": "Heavy-tail",
    "poisson": "Пуассон",
}

METRIC_TITLES = {
    "mean_num_jobs": "Среднее число заявок",
    "mean_occupied_resource": "Средний занятый ресурс",
    "loss_probability": "Вероятность отказа",
    "throughput": "Пропускная способность",
    "accepted_arrivals": "Принятые заявки",
    "rejected_arrivals": "Отказы",
    "completed_jobs": "Завершённые заявки",
    "mean_service_time": "Среднее время обслуживания",
    "mean_sojourn_time": "Среднее время пребывания",
    "std_service_time": "Std времени обслуживания",
    "std_sojourn_time": "Std времени пребывания",
    "rejected_capacity": "Отказы по вместимости K",
    "rejected_server": "Отказы по серверам N",
    "rejected_resource": "Отказы по ресурсу R",
}

METRIC_UNITS = {
    "mean_num_jobs": "заявок",
    "mean_occupied_resource": "ед. ресурса",
    "throughput": "заявки / ед. времени",
    "accepted_arrivals": "заявок",
    "rejected_arrivals": "заявок",
    "completed_jobs": "заявок",
    "mean_service_time": "ед. времени",
    "mean_sojourn_time": "ед. времени",
    "std_service_time": "ед. времени",
    "std_sojourn_time": "ед. времени",
    "rejected_capacity": "заявок",
    "rejected_server": "заявок",
    "rejected_resource": "заявок",
}

PROBABILITY_METRICS = {
    "loss_probability",
}

BASELINE_ARRIVAL = "poisson"
BASELINE_WORKLOAD = "deterministic"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(slots=True)
class SuiteData:
    suite_name: str
    created_at: str
    ci_level: float
    raw: dict[str, Any]


@dataclass(slots=True)
class PlotContext:
    suite: SuiteData
    scenario_df: pd.DataFrame
    run_df: pd.DataFrame
    metric_names: list[str]
    varying_dims: list[str]
    output_dir: Path
    formats: list[str]
    dpi: int
    created_files: list[Path]
    notes: list[str]


# =============================================================================
# IO
# =============================================================================

def resolve_suite_result_json(input_path: str | Path) -> Path:
    path = Path(input_path)

    if path.is_dir():
        candidate = path / "suite_result.json"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"В директории '{path}' не найден suite_result.json")

    if path.is_file():
        if path.suffix.lower() != ".json":
            raise ValueError(f"Ожидался .json, получено: {path}")
        return path

    raise FileNotFoundError(f"Путь не найден: {path}")


def load_suite_data(input_path: str | Path) -> SuiteData:
    json_path = resolve_suite_result_json(input_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    return SuiteData(
        suite_name=str(payload.get("suite_name", json_path.parent.name)),
        created_at=str(payload.get("created_at", "")),
        ci_level=float(payload.get("ci_level", 0.95)),
        raw=payload,
    )


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_output_dir(output_dir: Path) -> None:
    """
    Чистит старые артефакты рендера, чтобы не оставались дубли png/svg/pdf.

    Функция не рекурсивная и не трогает JSON.
    """
    if not output_dir.exists():
        return

    suffixes = {".png", ".svg", ".pdf", ".html", ".csv"}
    for path in output_dir.iterdir():
        if path.is_file() and path.suffix.lower() in suffixes:
            path.unlink()


# =============================================================================
# PARSING HELPERS
# =============================================================================

def _float_slug_to_value(token: str) -> float:
    return float(token.replace("p", "."))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        out = float(value)
    except Exception:
        return None

    if not math.isfinite(out):
        return None

    return out


def _parse_pairs_from_name(name: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if ":" in name:
        family, tail = name.split(":", 1)
        result["family_name"] = family.strip()
    else:
        tail = name

    for part in tail.split(","):
        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if key in {"lambda", "lam", "arrival_rate"}:
            result["lambda"] = _safe_float(value)
        elif key in {"sigma", "service_speed"}:
            result["sigma"] = _safe_float(value)
        elif key in {"arrival", "workload"}:
            result[key] = value

    return result


def parse_scenario_meta(scenario_key: str, scenario_name: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "scenario_key": scenario_key,
        "scenario_name": scenario_name,
        "family": None,
        "arrival": None,
        "workload": None,
        "lambda": None,
        "sigma": None,
    }

    pattern = re.compile(
        r"^(?P<family>[a-z0-9_\-]+)"
        r"(?:__arr-(?P<arrival>[a-z0-9_]+))?"
        r"(?:__work-(?P<workload>[a-z0-9_]+))?"
        r"(?:__lam-(?P<lam>[0-9p.]+))?"
        r"(?:__sig-(?P<sig>[0-9p.]+))?$",
        re.IGNORECASE,
    )

    match = pattern.match(scenario_key)
    if match:
        groups = match.groupdict()
        meta["family"] = groups.get("family")
        meta["arrival"] = groups.get("arrival")
        meta["workload"] = groups.get("workload")

        if groups.get("lam"):
            meta["lambda"] = _float_slug_to_value(groups["lam"])
        if groups.get("sig"):
            meta["sigma"] = _float_slug_to_value(groups["sig"])

    pairs = _parse_pairs_from_name(scenario_name)

    meta["arrival"] = pairs.get("arrival", meta["arrival"])
    meta["workload"] = pairs.get("workload", meta["workload"])
    meta["lambda"] = pairs.get("lambda", meta["lambda"])
    meta["sigma"] = pairs.get("sigma", meta["sigma"])

    if pairs.get("family_name") and not meta["family"]:
        meta["family"] = str(pairs["family_name"]).lower().replace("sensitivity", "").strip("_-")

    return meta


def _ordered_unique(
    values: Iterable[Any],
    preferred_order: Sequence[Any] | None = None,
) -> list[Any]:
    cleaned = [x for x in values if pd.notna(x)]
    unique = list(dict.fromkeys(cleaned))

    if preferred_order:
        preferred = [x for x in preferred_order if x in unique]
        rest = [x for x in unique if x not in preferred_order]
        try:
            rest = sorted(rest)
        except TypeError:
            pass
        return preferred + rest

    try:
        return sorted(unique)
    except TypeError:
        return unique


def dim_values(df: pd.DataFrame, dim: str) -> list[Any]:
    if dim not in df.columns:
        return []

    if dim == "workload":
        return _ordered_unique(df[dim].dropna().tolist(), WORKLOAD_ORDER)

    if dim == "arrival":
        return _ordered_unique(df[dim].dropna().tolist(), ARRIVAL_ORDER)

    return _ordered_unique(df[dim].dropna().tolist())


def display_value(value: Any) -> str:
    return DISPLAY_NAMES.get(str(value), str(value))


def lambda_label(value: Any) -> str:
    if value is None or pd.isna(value):
        return "λ=∅"
    return f"λ={float(value):g}"


def sigma_label(value: Any) -> str:
    if value is None or pd.isna(value):
        return "σ=∅"
    return f"σ={float(value):g}"


def filename_float(value: Any) -> str:
    if value is None or pd.isna(value):
        return "none"

    return f"{float(value):g}".replace(".", "p").replace("-", "m")


# =============================================================================
# DATAFRAMES
# =============================================================================

def build_dataframes(
    suite: SuiteData,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    scenario_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []

    scenario_results = dict(suite.raw.get("scenario_results", {}))
    if not scenario_results:
        return pd.DataFrame(), pd.DataFrame(), [], []

    metric_names = sorted(
        set().union(
            *[
                set(payload.get("metric_summaries", {}).keys())
                for payload in scenario_results.values()
            ]
        )
    )

    for scenario_key, payload in scenario_results.items():
        scenario_name = str(payload.get("scenario_name", scenario_key))
        meta = parse_scenario_meta(scenario_key, scenario_name)

        scenario_row: dict[str, Any] = {
            **meta,
            "replications": int(
                payload.get(
                    "replications",
                    len(payload.get("run_summaries", [])),
                )
            ),
        }

        for metric_name, summary in payload.get("metric_summaries", {}).items():
            scenario_row[metric_name] = float(summary.get("mean", np.nan))
            scenario_row[f"{metric_name}__ci_low"] = float(summary.get("ci_low", np.nan))
            scenario_row[f"{metric_name}__ci_high"] = float(summary.get("ci_high", np.nan))
            scenario_row[f"{metric_name}__std"] = float(summary.get("std", np.nan))
            scenario_row[f"{metric_name}__stderr"] = float(summary.get("stderr", np.nan))

        scenario_rows.append(scenario_row)

        for run in payload.get("run_summaries", []):
            run_row = {
                **meta,
                "scenario_key": scenario_key,
                "scenario_name": scenario_name,
                "replication_index": int(run.get("replication_index", -1)),
                "seed": int(run.get("seed", -1)),
            }

            for key, value in run.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    run_row[key] = float(value)

            pi_hat = run.get("pi_hat")
            if isinstance(pi_hat, list):
                run_row["pi_hat_len"] = len(pi_hat)

            run_rows.append(run_row)

    scenario_df = pd.DataFrame(scenario_rows)
    run_df = pd.DataFrame(run_rows)

    for df in (scenario_df, run_df):
        if df.empty:
            continue

        for dim in ["lambda", "sigma"]:
            if dim in df.columns:
                df[dim] = pd.to_numeric(df[dim], errors="coerce")

    varying_dims: list[str] = []
    for dim in ["arrival", "workload", "lambda", "sigma"]:
        if dim in scenario_df.columns and scenario_df[dim].nunique(dropna=True) > 1:
            varying_dims.append(dim)

    sort_cols = [
        col
        for col in ["sigma", "lambda", "workload", "arrival"]
        if col in scenario_df.columns
    ]

    if sort_cols:
        scenario_df = scenario_df.sort_values(sort_cols, kind="stable").reset_index(drop=True)

    run_sort_cols = [
        col
        for col in ["sigma", "lambda", "workload", "arrival", "replication_index"]
        if col in run_df.columns
    ]

    if run_sort_cols and not run_df.empty:
        run_df = run_df.sort_values(run_sort_cols, kind="stable").reset_index(drop=True)

    return scenario_df, run_df, metric_names, varying_dims


# =============================================================================
# PLOT HELPERS
# =============================================================================

def metric_title(metric: str) -> str:
    return METRIC_TITLES.get(metric, metric)


def is_probability_metric(metric: str) -> bool:
    return metric in PROBABILITY_METRICS


def metric_to_plot_values(metric: str, values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if is_probability_metric(metric):
        return arr * 100.0
    return arr


def metric_ylabel(metric: str) -> str:
    if is_probability_metric(metric):
        return f"{metric_title(metric)}, %"

    unit = METRIC_UNITS.get(metric)
    if unit:
        return f"{metric_title(metric)}, {unit}"

    return metric_title(metric)


def value_formatter(metric: str, values: Sequence[float] | np.ndarray | None = None):
    if is_probability_metric(metric):
        return lambda x: f"{x:.2f}%"

    if values is None:
        vmax = 1.0
    else:
        arr = np.asarray(values, dtype=float)
        finite = arr[np.isfinite(arr)]
        vmax = float(np.nanmax(np.abs(finite))) if finite.size else 1.0

    if vmax >= 10000:
        return lambda x: f"{x:,.0f}".replace(",", " ")
    if vmax >= 1000:
        return lambda x: f"{x:,.1f}".replace(",", " ")
    if vmax >= 100:
        return lambda x: f"{x:.1f}"
    if vmax >= 10:
        return lambda x: f"{x:.2f}"
    if vmax >= 1:
        return lambda x: f"{x:.3f}"
    if vmax >= 1e-2:
        return lambda x: f"{x:.4f}"

    return lambda x: f"{x:.6f}"


def delta_kind(metric: str) -> str:
    if is_probability_metric(metric):
        return "percentage_points"
    return "relative_percent"


def compute_delta(current: np.ndarray, baseline: np.ndarray, metric: str) -> np.ndarray:
    current = np.asarray(current, dtype=float)
    baseline = np.asarray(baseline, dtype=float)

    if delta_kind(metric) == "percentage_points":
        return (current - baseline) * 100.0

    return np.where(
        np.abs(baseline) > 1e-15,
        (current / baseline - 1.0) * 100.0,
        np.nan,
    )


def delta_ylabel(metric: str) -> str:
    if delta_kind(metric) == "percentage_points":
        return f"Δ {metric_title(metric)}, п.п."
    return f"Δ {metric_title(metric)}, %"


def delta_formatter(metric: str):
    if delta_kind(metric) == "percentage_points":
        return lambda x: f"{x:+.3f}"
    return lambda x: f"{x:+.2f}%"


def nice_bounds(
    values: Sequence[float] | np.ndarray,
    *,
    include_zero: bool = False,
) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    finite = arr[np.isfinite(arr)]

    if finite.size == 0:
        return 0.0, 1.0

    ymin = float(np.nanmin(finite))
    ymax = float(np.nanmax(finite))

    if include_zero:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)

    span = ymax - ymin
    if span <= 1e-15:
        margin = max(abs(ymax) * 0.05, 1e-6)
    else:
        margin = max(span * 0.10, 1e-6)

    return ymin - margin, ymax + margin


def ci_errors(df: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray] | None:
    low_col = f"{metric}__ci_low"
    high_col = f"{metric}__ci_high"

    if low_col not in df.columns or high_col not in df.columns:
        return None

    y = df[metric].to_numpy(dtype=float)
    low = y - df[low_col].to_numpy(dtype=float)
    high = df[high_col].to_numpy(dtype=float) - y

    if is_probability_metric(metric):
        low *= 100.0
        high *= 100.0

    return np.maximum(low, 0.0), np.maximum(high, 0.0)


def grid_shape(n_items: int, *, max_cols: int = 3) -> tuple[int, int]:
    ncols = min(max_cols, max(1, int(math.ceil(math.sqrt(n_items)))))
    nrows = int(math.ceil(n_items / ncols))
    return nrows, ncols


def apply_common_axis_style(ax: plt.Axes) -> None:
    ax.grid(True, alpha=0.24)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def mark_manual_layout(fig: plt.Figure) -> None:
    """Запрещает save_figure вызывать tight_layout для фигур с ручной разметкой."""
    setattr(fig, "_plots_reworked_manual_layout", True)


def split_ylabel(label: str) -> str:
    """Делает длинную вертикальную подпись компактнее: 2 строки вместо одной."""
    if ", " in label:
        left, right = label.split(", ", 1)
        return f"{left},\n{right}"
    if " [" in label:
        left, right = label.split(" [", 1)
        return f"{left}\n[{right}"
    return label


def add_side_colorbar(
    fig: plt.Figure,
    image: Any,
    label: str,
    *,
    rect: tuple[float, float, float, float] = (0.895, 0.20, 0.018, 0.58),
) -> None:
    """Добавляет colorbar в отдельную ось справа, не поверх heatmap-панелей."""
    cax = fig.add_axes(list(rect))
    colorbar = fig.colorbar(image, cax=cax)
    colorbar.set_label(label, labelpad=8)
    colorbar.ax.tick_params(labelsize=9)

def save_figure(ctx: PlotContext, fig: plt.Figure, stem: str) -> None:
    if not getattr(fig, "_plots_reworked_manual_layout", False):
        try:
            fig.tight_layout()
        except Exception as exc:
            ctx.notes.append(f"tight_layout не применён для {stem}: {exc}")

    for fmt in ctx.formats:
        out = ctx.output_dir / f"{stem}.{fmt}"
        fig.savefig(out, dpi=ctx.dpi, bbox_inches="tight")
        ctx.created_files.append(out)

    plt.close(fig)


def subset_by_sigma(ctx: PlotContext) -> list[tuple[float | None, pd.DataFrame]]:
    df = ctx.scenario_df

    if "sigma" not in df.columns:
        return [(None, df.copy())]

    if df["sigma"].nunique(dropna=True) <= 1:
        if df["sigma"].dropna().empty:
            return [(None, df.copy())]
        return [(float(df["sigma"].dropna().iloc[0]), df.copy())]

    return [
        (float(sigma), df[df["sigma"] == sigma].copy())
        for sigma in dim_values(df, "sigma")
    ]


def subtitle_sigma(sigma: float | None) -> str:
    if sigma is None:
        return ""
    return f" | {sigma_label(sigma)}"


# =============================================================================
# ABSOLUTE COMPARISONS
# =============================================================================

def plot_heatmaps_workload_arrival_by_lambda(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    if not metrics:
        return

    required = {"workload", "arrival", "lambda"}
    if not required.issubset(ctx.scenario_df.columns):
        return

    for metric in metrics:
        for sigma, sigma_df in subset_by_sigma(ctx):
            lambdas = dim_values(sigma_df, "lambda")
            workloads = dim_values(sigma_df, "workload")
            arrivals = dim_values(sigma_df, "arrival")

            if not lambdas or not workloads or not arrivals:
                continue

            ncols = len(lambdas)

            fig, axes = plt.subplots(
                1,
                ncols,
                figsize=(4.45 * ncols + 2.2, 0.62 * len(workloads) + 4.25),
                squeeze=False,
            )

            all_values = metric_to_plot_values(
                metric,
                sigma_df[metric].to_numpy(dtype=float),
            )
            finite_all = all_values[np.isfinite(all_values)]

            vmin = float(np.nanmin(finite_all)) if finite_all.size else None
            vmax = float(np.nanmax(finite_all)) if finite_all.size else None
            formatter = value_formatter(metric, finite_all)

            image = None

            for col_idx, lam in enumerate(lambdas):
                ax = axes[0, col_idx]
                matrix = np.full((len(workloads), len(arrivals)), np.nan)

                for i, workload in enumerate(workloads):
                    for j, arrival in enumerate(arrivals):
                        hit = sigma_df[
                            (sigma_df["lambda"] == lam)
                            & (sigma_df["workload"] == workload)
                            & (sigma_df["arrival"] == arrival)
                        ]

                        if not hit.empty:
                            matrix[i, j] = float(
                                metric_to_plot_values(metric, [hit.iloc[0][metric]])[0]
                            )

                image = ax.imshow(
                    matrix,
                    aspect="auto",
                    interpolation="nearest",
                    vmin=vmin,
                    vmax=vmax,
                )

                ax.set_title(lambda_label(lam), pad=10)
                ax.set_xticks(np.arange(len(arrivals)))
                ax.set_xticklabels(
                    [display_value(a) for a in arrivals],
                    rotation=25,
                    ha="right",
                )
                ax.set_yticks(np.arange(len(workloads)))

                if col_idx == 0:
                    ax.set_yticklabels([display_value(w) for w in workloads])
                    ax.set_ylabel("workload")
                else:
                    ax.set_yticklabels([])

                ax.set_xlabel("тип входящего потока")

                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if np.isfinite(matrix[i, j]):
                            ax.text(
                                j,
                                i,
                                formatter(matrix[i, j]),
                                ha="center",
                                va="center",
                                fontsize=8.1,
                            )

            # Важно: ручная раскладка. Последняя heatmap заканчивается до colorbar.
            fig.subplots_adjust(
                left=0.075,
                right=0.800,
                bottom=0.205,
                top=0.800,
                wspace=0.115,
            )

            if image is not None:
                add_side_colorbar(
                    fig,
                    image,
                    metric_ylabel(metric),
                    rect=(0.845, 0.225, 0.016, 0.515),
                )

            fig.suptitle(
                f"Матрица workload × arrival: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=18,
                fontweight="semibold",
                y=0.965,
            )

            mark_manual_layout(fig)

            save_figure(
                ctx,
                fig,
                f"01_heatmap_workload_arrival_{metric}_sigma-{filename_float(sigma)}",
            )


def plot_lines_arrivals_within_each_workload(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda"}
    if not metrics or not required.issubset(ctx.scenario_df.columns):
        return

    for metric in metrics:
        for sigma, sigma_df in subset_by_sigma(ctx):
            workloads = dim_values(sigma_df, "workload")
            arrivals = dim_values(sigma_df, "arrival")
            lambdas = dim_values(sigma_df, "lambda")

            if not workloads or not arrivals or not lambdas:
                continue

            nrows, ncols = grid_shape(len(workloads), max_cols=3)
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(6.0 * ncols, 4.3 * nrows),
                squeeze=False,
                sharex=True,
            )

            axes_flat = axes.ravel()

            y_all = metric_to_plot_values(
                metric,
                sigma_df[metric].to_numpy(dtype=float),
            )
            ymin, ymax = nice_bounds(y_all)

            handles: list[Any] = []
            labels: list[str] = []

            for ax_idx, workload in enumerate(workloads):
                ax = axes_flat[ax_idx]
                work_df = sigma_df[sigma_df["workload"] == workload].copy()

                for arrival in arrivals:
                    line_df = work_df[work_df["arrival"] == arrival].sort_values("lambda")
                    if line_df.empty:
                        continue

                    x = line_df["lambda"].to_numpy(dtype=float)
                    y = metric_to_plot_values(
                        metric,
                        line_df[metric].to_numpy(dtype=float),
                    )

                    errors = ci_errors(line_df, metric)
                    yerr = [errors[0], errors[1]] if errors is not None else None

                    artist = ax.errorbar(
                        x,
                        y,
                        yerr=yerr,
                        marker="o",
                        linewidth=2.0,
                        capsize=3,
                        label=display_value(arrival),
                    )

                    if ax_idx == 0:
                        handles.append(artist)
                        labels.append(display_value(arrival))

                ax.set_title(f"workload = {display_value(workload)}")
                ax.set_xlabel("Интенсивность поступления λ")
                ax.set_ylabel(metric_ylabel(metric))
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(MaxNLocator(nbins=min(6, len(lambdas) + 1)))
                apply_common_axis_style(ax)

            for ax in axes_flat[len(workloads):]:
                ax.axis("off")

            fig.suptitle(
                f"Сравнение arrival при фиксированном workload: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=18,
                fontweight="semibold",
                y=1.01,
            )

            if handles:
                fig.legend(
                    handles,
                    labels,
                    title="Тип входящего потока",
                    loc="center right",
                    bbox_to_anchor=(1.01, 0.5),
                    frameon=True,
                )
                fig.subplots_adjust(right=0.84)

            save_figure(
                ctx,
                fig,
                f"02_compare_arrivals_fixed_workload_{metric}_sigma-{filename_float(sigma)}",
            )


def plot_lines_workloads_within_each_arrival(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda"}
    if not metrics or not required.issubset(ctx.scenario_df.columns):
        return

    for metric in metrics:
        for sigma, sigma_df in subset_by_sigma(ctx):
            arrivals = dim_values(sigma_df, "arrival")
            workloads = dim_values(sigma_df, "workload")
            lambdas = dim_values(sigma_df, "lambda")

            if not arrivals or not workloads or not lambdas:
                continue

            nrows, ncols = grid_shape(len(arrivals), max_cols=2)
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(7.0 * ncols, 4.6 * nrows),
                squeeze=False,
                sharex=True,
            )

            axes_flat = axes.ravel()

            y_all = metric_to_plot_values(
                metric,
                sigma_df[metric].to_numpy(dtype=float),
            )
            ymin, ymax = nice_bounds(y_all)

            handles: list[Any] = []
            labels: list[str] = []

            for ax_idx, arrival in enumerate(arrivals):
                ax = axes_flat[ax_idx]
                arr_df = sigma_df[sigma_df["arrival"] == arrival].copy()

                for workload in workloads:
                    line_df = arr_df[arr_df["workload"] == workload].sort_values("lambda")
                    if line_df.empty:
                        continue

                    x = line_df["lambda"].to_numpy(dtype=float)
                    y = metric_to_plot_values(
                        metric,
                        line_df[metric].to_numpy(dtype=float),
                    )

                    errors = ci_errors(line_df, metric)
                    yerr = [errors[0], errors[1]] if errors is not None else None

                    artist = ax.errorbar(
                        x,
                        y,
                        yerr=yerr,
                        marker="o",
                        linewidth=2.0,
                        capsize=3,
                        label=display_value(workload),
                    )

                    if ax_idx == 0:
                        handles.append(artist)
                        labels.append(display_value(workload))

                ax.set_title(f"arrival = {display_value(arrival)}")
                ax.set_xlabel("Интенсивность поступления λ")
                ax.set_ylabel(metric_ylabel(metric))
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(MaxNLocator(nbins=min(6, len(lambdas) + 1)))
                apply_common_axis_style(ax)

            for ax in axes_flat[len(arrivals):]:
                ax.axis("off")

            fig.suptitle(
                f"Сравнение workload при фиксированном arrival: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=18,
                fontweight="semibold",
                y=1.01,
            )

            if handles:
                fig.legend(
                    handles,
                    labels,
                    title="Workload",
                    loc="center right",
                    bbox_to_anchor=(1.01, 0.5),
                    frameon=True,
                )
                fig.subplots_adjust(right=0.84)

            save_figure(
                ctx,
                fig,
                f"03_compare_workloads_fixed_arrival_{metric}_sigma-{filename_float(sigma)}",
            )


# =============================================================================
# DELTA PLOTS
# =============================================================================

def plot_delta_arrival_vs_poisson_by_workload(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda", "sigma"}
    if not metrics or not required.issubset(ctx.scenario_df.columns):
        return

    if BASELINE_ARRIVAL not in set(ctx.scenario_df["arrival"].dropna().tolist()):
        ctx.notes.append("Не построены Δ-графики arrival: отсутствует baseline arrival=poisson.")
        return

    for metric in metrics:
        base = ctx.scenario_df[ctx.scenario_df["arrival"] == BASELINE_ARRIVAL][
            ["workload", "lambda", "sigma", metric]
        ].rename(columns={metric: "__base"})

        merged = ctx.scenario_df.merge(
            base,
            on=["workload", "lambda", "sigma"],
            how="left",
        )

        merged[f"__delta_{metric}"] = compute_delta(
            merged[metric].to_numpy(dtype=float),
            merged["__base"].to_numpy(dtype=float),
            metric,
        )

        temp_ctx = PlotContext(
            suite=ctx.suite,
            scenario_df=merged,
            run_df=ctx.run_df,
            metric_names=ctx.metric_names,
            varying_dims=ctx.varying_dims,
            output_dir=ctx.output_dir,
            formats=ctx.formats,
            dpi=ctx.dpi,
            created_files=ctx.created_files,
            notes=ctx.notes,
        )

        for sigma, sigma_df in subset_by_sigma(temp_ctx):
            workloads = dim_values(sigma_df, "workload")
            arrivals = dim_values(sigma_df, "arrival")

            if not workloads or not arrivals:
                continue

            nrows, ncols = grid_shape(len(workloads), max_cols=3)
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(6.0 * ncols, 4.25 * nrows),
                squeeze=False,
                sharex=True,
            )

            axes_flat = axes.ravel()
            y_all = sigma_df[f"__delta_{metric}"].to_numpy(dtype=float)
            ymin, ymax = nice_bounds(y_all, include_zero=True)

            handles: list[Any] = []
            labels: list[str] = []

            for ax_idx, workload in enumerate(workloads):
                ax = axes_flat[ax_idx]
                wdf = sigma_df[sigma_df["workload"] == workload]

                ax.axhline(0.0, linewidth=1.2, color="black", alpha=0.55)

                for arrival in arrivals:
                    line_df = wdf[wdf["arrival"] == arrival].sort_values("lambda")
                    if line_df.empty:
                        continue

                    x = line_df["lambda"].to_numpy(dtype=float)
                    y = line_df[f"__delta_{metric}"].to_numpy(dtype=float)

                    artist = ax.plot(
                        x,
                        y,
                        marker="o",
                        linewidth=2.0,
                        label=display_value(arrival),
                    )[0]

                    if ax_idx == 0:
                        handles.append(artist)
                        labels.append(display_value(arrival))

                ax.set_title(f"workload = {display_value(workload)}")
                ax.set_xlabel("Интенсивность поступления λ")
                ax.set_ylabel(delta_ylabel(metric))
                ax.set_ylim(ymin, ymax)
                apply_common_axis_style(ax)

            for ax in axes_flat[len(workloads):]:
                ax.axis("off")

            fig.suptitle(
                f"Смещение arrival относительно Пуассона при том же workload: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=18,
                fontweight="semibold",
                y=1.01,
            )

            if handles:
                fig.legend(
                    handles,
                    labels,
                    title="Тип входящего потока",
                    loc="center right",
                    bbox_to_anchor=(1.01, 0.5),
                    frameon=True,
                )
                fig.subplots_adjust(right=0.84)

            save_figure(
                ctx,
                fig,
                f"04_delta_arrival_vs_poisson_by_workload_{metric}_sigma-{filename_float(sigma)}",
            )


def plot_delta_workload_vs_deterministic_by_arrival(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda", "sigma"}
    if not metrics or not required.issubset(ctx.scenario_df.columns):
        return

    if BASELINE_WORKLOAD not in set(ctx.scenario_df["workload"].dropna().tolist()):
        ctx.notes.append("Не построены Δ-графики workload: отсутствует baseline workload=deterministic.")
        return

    for metric in metrics:
        base = ctx.scenario_df[ctx.scenario_df["workload"] == BASELINE_WORKLOAD][
            ["arrival", "lambda", "sigma", metric]
        ].rename(columns={metric: "__base"})

        merged = ctx.scenario_df.merge(
            base,
            on=["arrival", "lambda", "sigma"],
            how="left",
        )

        merged[f"__delta_{metric}"] = compute_delta(
            merged[metric].to_numpy(dtype=float),
            merged["__base"].to_numpy(dtype=float),
            metric,
        )

        temp_ctx = PlotContext(
            suite=ctx.suite,
            scenario_df=merged,
            run_df=ctx.run_df,
            metric_names=ctx.metric_names,
            varying_dims=ctx.varying_dims,
            output_dir=ctx.output_dir,
            formats=ctx.formats,
            dpi=ctx.dpi,
            created_files=ctx.created_files,
            notes=ctx.notes,
        )

        for sigma, sigma_df in subset_by_sigma(temp_ctx):
            arrivals = dim_values(sigma_df, "arrival")
            workloads = dim_values(sigma_df, "workload")

            if not arrivals or not workloads:
                continue

            nrows, ncols = grid_shape(len(arrivals), max_cols=2)
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(7.0 * ncols, 4.5 * nrows),
                squeeze=False,
                sharex=True,
            )

            axes_flat = axes.ravel()
            y_all = sigma_df[f"__delta_{metric}"].to_numpy(dtype=float)
            ymin, ymax = nice_bounds(y_all, include_zero=True)

            handles: list[Any] = []
            labels: list[str] = []

            for ax_idx, arrival in enumerate(arrivals):
                ax = axes_flat[ax_idx]
                adf = sigma_df[sigma_df["arrival"] == arrival]

                ax.axhline(0.0, linewidth=1.2, color="black", alpha=0.55)

                for workload in workloads:
                    line_df = adf[adf["workload"] == workload].sort_values("lambda")
                    if line_df.empty:
                        continue

                    x = line_df["lambda"].to_numpy(dtype=float)
                    y = line_df[f"__delta_{metric}"].to_numpy(dtype=float)

                    artist = ax.plot(
                        x,
                        y,
                        marker="o",
                        linewidth=2.0,
                        label=display_value(workload),
                    )[0]

                    if ax_idx == 0:
                        handles.append(artist)
                        labels.append(display_value(workload))

                ax.set_title(f"arrival = {display_value(arrival)}")
                ax.set_xlabel("Интенсивность поступления λ")
                ax.set_ylabel(delta_ylabel(metric))
                ax.set_ylim(ymin, ymax)
                apply_common_axis_style(ax)

            for ax in axes_flat[len(arrivals):]:
                ax.axis("off")

            fig.suptitle(
                f"Смещение workload относительно детерминированного при том же arrival: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=18,
                fontweight="semibold",
                y=1.01,
            )

            if handles:
                fig.legend(
                    handles,
                    labels,
                    title="Workload",
                    loc="center right",
                    bbox_to_anchor=(1.01, 0.5),
                    frameon=True,
                )
                fig.subplots_adjust(right=0.84)

            save_figure(
                ctx,
                fig,
                f"05_delta_workload_vs_deterministic_by_arrival_{metric}_sigma-{filename_float(sigma)}",
            )


def plot_joint_baseline_delta_heatmaps(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda", "sigma"}
    if not metrics or not required.issubset(ctx.scenario_df.columns):
        return

    has_joint_base = (
        (ctx.scenario_df["arrival"] == BASELINE_ARRIVAL)
        & (ctx.scenario_df["workload"] == BASELINE_WORKLOAD)
    ).any()

    if not has_joint_base:
        ctx.notes.append(
            "Не построены совместные Δ-heatmap: отсутствует baseline deterministic × poisson."
        )
        return

    for metric in metrics:
        for sigma, sigma_df in subset_by_sigma(ctx):
            lambdas = dim_values(sigma_df, "lambda")
            workloads = dim_values(sigma_df, "workload")
            arrivals = dim_values(sigma_df, "arrival")

            if not lambdas or not workloads or not arrivals:
                continue

            ncols = len(lambdas)
            fig, axes = plt.subplots(
                1,
                ncols,
                figsize=(4.4 * ncols + 1.5, 0.58 * len(workloads) + 4.0),
                squeeze=False,
            )

            matrices: list[np.ndarray] = []

            for lam in lambdas:
                lam_df = sigma_df[sigma_df["lambda"] == lam]
                base_hit = lam_df[
                    (lam_df["arrival"] == BASELINE_ARRIVAL)
                    & (lam_df["workload"] == BASELINE_WORKLOAD)
                ]

                if base_hit.empty:
                    matrices.append(np.full((len(workloads), len(arrivals)), np.nan))
                    continue

                base_value = float(base_hit.iloc[0][metric])
                matrix = np.full((len(workloads), len(arrivals)), np.nan)

                for i, workload in enumerate(workloads):
                    for j, arrival in enumerate(arrivals):
                        hit = lam_df[
                            (lam_df["workload"] == workload)
                            & (lam_df["arrival"] == arrival)
                        ]

                        if not hit.empty:
                            matrix[i, j] = compute_delta(
                                np.array([float(hit.iloc[0][metric])]),
                                np.array([base_value]),
                                metric,
                            )[0]

                matrices.append(matrix)

            finite_parts = [m[np.isfinite(m)] for m in matrices if np.isfinite(m).any()]
            finite = np.concatenate(finite_parts) if finite_parts else np.array([0.0])
            vmax = max(float(np.nanmax(np.abs(finite))), 1e-9)

            formatter = delta_formatter(metric)
            image = None

            for col_idx, (lam, matrix) in enumerate(zip(lambdas, matrices)):
                ax = axes[0, col_idx]

                image = ax.imshow(
                    matrix,
                    aspect="auto",
                    interpolation="nearest",
                    cmap="coolwarm",
                    vmin=-vmax,
                    vmax=vmax,
                )

                ax.set_title(lambda_label(lam))
                ax.set_xticks(np.arange(len(arrivals)))
                ax.set_xticklabels(
                    [display_value(a) for a in arrivals],
                    rotation=25,
                    ha="right",
                )
                ax.set_yticks(np.arange(len(workloads)))

                if col_idx == 0:
                    ax.set_yticklabels([display_value(w) for w in workloads])
                    ax.set_ylabel("workload")
                else:
                    ax.set_yticklabels([])

                ax.set_xlabel("тип входящего потока")

                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if np.isfinite(matrix[i, j]):
                            ax.text(
                                j,
                                i,
                                formatter(matrix[i, j]),
                                ha="center",
                                va="center",
                                fontsize=8.1,
                            )

            fig.subplots_adjust(
                            left=0.075,
                            right=0.865,
                            bottom=0.20,
                            top=0.78,
                            wspace=0.10,
                        )

            if image is not None:
                add_side_colorbar(
                    fig,
                    image,
                    delta_ylabel(metric),
                    rect=(0.895, 0.22, 0.018, 0.52),
                )

            fig.suptitle(
                f"Совместное смещение относительно workload=Детерм., arrival=Пуассон: {metric_title(metric)}{subtitle_sigma(sigma)}",
                fontsize=17,
                fontweight="semibold",
                y=0.965,
            )
            mark_manual_layout(fig)

            save_figure(
                ctx,
                fig,
                f"06_joint_delta_vs_det_poisson_{metric}_sigma-{filename_float(sigma)}",
            )


# =============================================================================
# REPLICATIONS
# =============================================================================

def boxplot_compat(
    ax: plt.Axes,
    data: Sequence[np.ndarray],
    labels: Sequence[str],
    **kwargs: Any,
):
    try:
        return ax.boxplot(data, tick_labels=labels, **kwargs)
    except TypeError:
        return ax.boxplot(data, labels=labels, **kwargs)


def plot_replication_boxplots(
    ctx: PlotContext,
    metrics: Sequence[str],
) -> None:
    if ctx.run_df.empty:
        return

    metrics = [m for m in metrics if m in ctx.run_df.columns]

    required = {"workload", "arrival", "lambda"}
    if not metrics or not required.issubset(ctx.run_df.columns):
        return

    if "sigma" in ctx.run_df.columns and ctx.run_df["sigma"].nunique(dropna=True) > 1:
        sigma_values: list[float | None] = [
            float(x)
            for x in dim_values(ctx.run_df, "sigma")
        ]
    elif "sigma" in ctx.run_df.columns and not ctx.run_df["sigma"].dropna().empty:
        sigma_values = [float(ctx.run_df["sigma"].dropna().iloc[0])]
    else:
        sigma_values = [None]

    for metric in metrics:
        for sigma in sigma_values:
            sigma_df = ctx.run_df.copy()

            if sigma is not None and "sigma" in sigma_df.columns:
                sigma_df = sigma_df[sigma_df["sigma"] == sigma]

            for lam in dim_values(sigma_df, "lambda"):
                lam_df = sigma_df[sigma_df["lambda"] == lam]

                workloads = dim_values(lam_df, "workload")
                arrivals = dim_values(lam_df, "arrival")

                if not workloads or not arrivals:
                    continue

                fig, axes = plt.subplots(
                    len(workloads),
                    1,
                    figsize=(11.8, max(3.0, 2.15 * len(workloads))),
                    squeeze=False,
                    sharex=True,
                )

                axes_flat = axes.ravel()
                y_global: list[float] = []

                for ax_idx, workload in enumerate(workloads):
                    ax = axes_flat[ax_idx]
                    wdf = lam_df[lam_df["workload"] == workload]

                    series: list[np.ndarray] = []
                    labels: list[str] = []

                    for arrival in arrivals:
                        values = wdf[wdf["arrival"] == arrival][metric].dropna().to_numpy(dtype=float)

                        if values.size:
                            values_plot = metric_to_plot_values(metric, values)
                            series.append(values_plot)
                            labels.append(display_value(arrival))
                            y_global.extend(values_plot.tolist())

                    if series:
                        bp = boxplot_compat(
                            ax,
                            series,
                            labels,
                            showmeans=True,
                            patch_artist=True,
                            widths=0.65,
                        )

                        for box in bp.get("boxes", []):
                            box.set_alpha(0.75)

                    ax.set_title(f"workload = {display_value(workload)}")
                    ax.set_ylabel("")
                    apply_common_axis_style(ax)

                if y_global:
                    ymin, ymax = nice_bounds(y_global)
                    for ax in axes_flat:
                        ax.set_ylim(ymin, ymax)

                axes_flat[-1].set_xlabel("тип входящего потока")

                fig.suptitle(
                    f"Разброс по репликациям: {metric_title(metric)} | {lambda_label(lam)}{subtitle_sigma(sigma)}",
                    fontsize=18,
                    fontweight="semibold",
                    y=1.01,
                )

                # fig.suptitle(
                #     f"Разброс по репликациям: {metric_title(metric)} | {lambda_label(lam)}{subtitle_sigma(sigma)}",
                #     fontsize=18,
                #     fontweight="semibold",
                #     y=0.965,
                # )

                fig.text(
                    0.025,
                    0.50,
                    split_ylabel(metric_ylabel(metric)),
                    rotation=90,
                    va="center",
                    ha="center",
                    fontsize=12,
                )

                fig.subplots_adjust(
                    left=0.11,
                    right=0.985,
                    bottom=0.11,
                    top=0.88,
                    hspace=0.62,
                )
                mark_manual_layout(fig)

                save_figure(
                    ctx,
                    fig,
                    f"07_replication_boxplots_{metric}_lambda-{filename_float(lam)}_sigma-{filename_float(sigma)}",
                )


# =============================================================================
# REJECTIONS
# =============================================================================

def plot_rejection_component_heatmaps(ctx: PlotContext) -> None:
    components = [m for m in REJECTION_COMPONENTS if m in ctx.scenario_df.columns]

    required = {"workload", "arrival", "lambda"}
    if not components or not required.issubset(ctx.scenario_df.columns):
        return

    for sigma, sigma_df in subset_by_sigma(ctx):
        lambdas = dim_values(sigma_df, "lambda")
        workloads = dim_values(sigma_df, "workload")
        arrivals = dim_values(sigma_df, "arrival")

        if not lambdas or not workloads or not arrivals:
            continue

        fig, axes = plt.subplots(
            len(components),
            len(lambdas),
            figsize=(4.2 * len(lambdas) + 1.4, 3.2 * len(components)),
            squeeze=False,
        )

        all_values = sigma_df[components].to_numpy(dtype=float)
        finite_all = all_values[np.isfinite(all_values)]
        vmin = 0.0
        vmax = float(np.nanmax(finite_all)) if finite_all.size else 1.0

        image = None

        for row_idx, component in enumerate(components):
            formatter = value_formatter(
                component,
                sigma_df[component].to_numpy(dtype=float),
            )

            for col_idx, lam in enumerate(lambdas):
                ax = axes[row_idx, col_idx]
                lam_df = sigma_df[sigma_df["lambda"] == lam]
                matrix = np.full((len(workloads), len(arrivals)), np.nan)

                for i, workload in enumerate(workloads):
                    for j, arrival in enumerate(arrivals):
                        hit = lam_df[
                            (lam_df["workload"] == workload)
                            & (lam_df["arrival"] == arrival)
                        ]

                        if not hit.empty:
                            matrix[i, j] = float(hit.iloc[0][component])

                image = ax.imshow(
                    matrix,
                    aspect="auto",
                    interpolation="nearest",
                    vmin=vmin,
                    vmax=vmax,
                )

                ax.set_title(f"{metric_title(component)}\n{lambda_label(lam)}")
                ax.set_xticks(np.arange(len(arrivals)))
                ax.set_xticklabels(
                    [display_value(a) for a in arrivals],
                    rotation=25,
                    ha="right",
                )
                ax.set_yticks(np.arange(len(workloads)))

                if col_idx == 0:
                    ax.set_yticklabels([display_value(w) for w in workloads])
                else:
                    ax.set_yticklabels([])

                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if np.isfinite(matrix[i, j]):
                            ax.text(
                                j,
                                i,
                                formatter(matrix[i, j]),
                                ha="center",
                                va="center",
                                fontsize=8.0,
                            )

        fig.subplots_adjust(
            left=0.07,
            right=0.865,
            bottom=0.11,
            top=0.88,
            wspace=0.10,
            hspace=0.62,
        )

        if image is not None:
            add_side_colorbar(
                fig,
                image,
                "число отказов",
                rect=(0.895, 0.18, 0.018, 0.64),
            )

        fig.suptitle(
            f"Структура отказов по workload × arrival{subtitle_sigma(sigma)}",
            fontsize=18,
            fontweight="semibold",
            y=0.965,
        )
        mark_manual_layout(fig)

        save_figure(
            ctx,
            fig,
            f"08_rejection_components_heatmaps_sigma-{filename_float(sigma)}",
        )


# =============================================================================
# STATIONARY DISTRIBUTION
# =============================================================================

def pi_metric_names(ctx: PlotContext) -> list[str]:
    return sorted(
        [
            name
            for name in ctx.metric_names
            if re.fullmatch(r"pi_hat_\d+", name)
        ],
        key=lambda item: int(item.split("_")[-1]),
    )


def plot_stationary_tail_curves(ctx: PlotContext) -> None:
    pi_metrics = pi_metric_names(ctx)

    if not pi_metrics:
        ctx.notes.append("Метрики pi_hat_k отсутствуют: графики стационарного распределения не построены.")
        return

    if len(pi_metrics) <= 1:
        ctx.notes.append("В JSON присутствует только pi_hat_0: полноценный хвост стационарного распределения неинформативен.")
        return

    required = {"workload", "arrival", "lambda"}
    if not required.issubset(ctx.scenario_df.columns):
        return

    states = np.asarray(
        [int(name.split("_")[-1]) for name in pi_metrics],
        dtype=int,
    )

    for sigma, sigma_df in subset_by_sigma(ctx):
        for lam in dim_values(sigma_df, "lambda"):
            lam_df = sigma_df[sigma_df["lambda"] == lam]

            workloads = dim_values(lam_df, "workload")
            arrivals = dim_values(lam_df, "arrival")

            if not workloads or not arrivals:
                continue

            nrows, ncols = grid_shape(len(workloads), max_cols=3)
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(6.0 * ncols, 4.2 * nrows),
                squeeze=False,
                sharex=True,
            )

            axes_flat = axes.ravel()

            handles: list[Any] = []
            labels: list[str] = []

            for ax_idx, workload in enumerate(workloads):
                ax = axes_flat[ax_idx]
                wdf = lam_df[lam_df["workload"] == workload]

                for arrival in arrivals:
                    hit = wdf[wdf["arrival"] == arrival]

                    if hit.empty:
                        continue

                    probs = hit.iloc[0][pi_metrics].to_numpy(dtype=float)
                    probs = np.clip(probs, 0.0, None)

                    if probs.sum() > 0:
                        probs = probs / probs.sum()

                    tail = np.flip(np.cumsum(np.flip(probs)))
                    mask = tail > 0

                    artist = ax.plot(
                        states[mask],
                        tail[mask],
                        marker="o",
                        markersize=3.5,
                        linewidth=1.8,
                        label=display_value(arrival),
                    )[0]

                    if ax_idx == 0:
                        handles.append(artist)
                        labels.append(display_value(arrival))

                ax.set_yscale("log")
                ax.set_title(f"workload = {display_value(workload)}")
                ax.set_xlabel("k — число заявок в системе")
                ax.set_ylabel(r"$P\{N \geq k\}$")
                apply_common_axis_style(ax)

            for ax in axes_flat[len(workloads):]:
                ax.axis("off")

            fig.suptitle(
                f"Хвост стационарного распределения по arrival при фиксированном workload | {lambda_label(lam)}{subtitle_sigma(sigma)}",
                fontsize=17,
                fontweight="semibold",
                y=1.01,
            )

            if handles:
                fig.legend(
                    handles,
                    labels,
                    title="Тип входящего потока",
                    loc="center right",
                    bbox_to_anchor=(1.01, 0.5),
                    frameon=True,
                )
                fig.subplots_adjust(right=0.84)

            save_figure(
                ctx,
                fig,
                f"09_stationary_tail_by_workload_lambda-{filename_float(lam)}_sigma-{filename_float(sigma)}",
            )


# =============================================================================
# EXPORTS
# =============================================================================

def write_summary_table(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]

    cols = [
        col
        for col in [
            "family",
            "arrival",
            "workload",
            "lambda",
            "sigma",
            "scenario_key",
            "scenario_name",
        ]
        if col in ctx.scenario_df.columns
    ]

    out = ctx.scenario_df[cols + metrics].copy()
    path = ctx.output_dir / "scenario_summary_pretty.csv"
    out.to_csv(path, index=False, encoding="utf-8-sig")
    ctx.created_files.append(path)


def write_html_report(ctx: PlotContext, metrics: Sequence[str]) -> None:
    images = sorted(
        [
            path
            for path in ctx.created_files
            if path.suffix.lower() in {".png", ".svg", ".pdf"}
        ],
        key=lambda path: path.name,
    )

    summary_cols = [
        col
        for col in ["arrival", "workload", "lambda", "sigma"]
        if col in ctx.scenario_df.columns
    ]

    table_cols = summary_cols + [
        metric
        for metric in metrics
        if metric in ctx.scenario_df.columns
    ]

    table_df = ctx.scenario_df[table_cols].copy()

    for dim in ["arrival", "workload"]:
        if dim in table_df.columns:
            table_df[dim] = table_df[dim].map(display_value)

    for metric in [m for m in metrics if m in table_df.columns]:
        values = metric_to_plot_values(metric, table_df[metric].to_numpy(dtype=float))
        formatter = value_formatter(metric, values)

        if is_probability_metric(metric):
            table_df[metric] = values

        table_df[metric] = table_df[metric].map(
            lambda x, f=formatter: f(float(x)) if pd.notna(x) else ""
        )

    html_images = "\n".join(
        f'<section class="card"><h2>{html.escape(path.stem)}</h2><img src="{html.escape(path.name)}" alt="{html.escape(path.stem)}"></section>'
        for path in images
    )

    notes_html = "\n".join(
        f"<li>{html.escape(note)}</li>"
        for note in dict.fromkeys(ctx.notes)
    )

    report = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{html.escape(ctx.suite.suite_name)} — combined plot report</title>
  <style>
    body {{ font-family: Inter, Segoe UI, Arial, sans-serif; margin: 24px; color: #1b1f28; background: #f5f7fb; }}
    h1, h2 {{ margin: 0 0 10px 0; }}
    .header, .card {{ background: white; border: 1px solid #dfe4ee; border-radius: 16px; padding: 18px 20px; box-shadow: 0 8px 24px rgba(18, 28, 45, 0.06); margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); gap: 18px; }}
    img {{ width: 100%; height: auto; border-radius: 12px; background: white; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e7eaf1; padding: 8px 10px; text-align: left; }}
    th {{ background: #f7f9fc; position: sticky; top: 0; }}
    ul {{ margin: 8px 0 0 22px; }}
  </style>
</head>
<body>
  <section class="header">
    <h1>{html.escape(ctx.suite.suite_name)}</h1>
    <p>
      <strong>Создано:</strong> {html.escape(ctx.suite.created_at)}<br>
      <strong>CI:</strong> {ctx.suite.ci_level:.2f}<br>
      <strong>Сценариев:</strong> {len(ctx.scenario_df)}<br>
      <strong>Варьирующие измерения:</strong> {html.escape(", ".join(ctx.varying_dims) if ctx.varying_dims else "нет")}<br>
      <strong>Baseline arrival:</strong> {html.escape(display_value(BASELINE_ARRIVAL))}<br>
      <strong>Baseline workload:</strong> {html.escape(display_value(BASELINE_WORKLOAD))}
    </p>
  </section>

  <section class="card">
    <h2>Сводная таблица</h2>
    {table_df.to_html(index=False, border=0, classes="summary-table")}
  </section>

  <section class="card">
    <h2>Замечания рендера</h2>
    <ul>{notes_html or "<li>Нет замечаний.</li>"}</ul>
  </section>

  <div class="grid">
    {html_images}
  </div>
</body>
</html>
"""

    path = ctx.output_dir / "report.html"
    path.write_text(report, encoding="utf-8")
    ctx.created_files.append(path)


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def generate_plots(
    suite: SuiteData,
    output_dir: str | Path,
    *,
    dpi: int,
    formats: Sequence[str],
    metrics: Sequence[str] | None,
    clean_output: bool,
) -> PlotContext:
    scenario_df, run_df, metric_names, varying_dims = build_dataframes(suite)
    output = ensure_dir(output_dir)

    if clean_output:
        clean_output_dir(output)

    if scenario_df.empty:
        raise ValueError("В suite_result.json нет сценариев")

    available_metrics = [
        metric
        for metric in CORE_METRICS
        if metric in metric_names
    ]

    if metrics:
        requested = [
            metric
            for metric in metrics
            if metric in metric_names
        ]

        if requested:
            available_metrics = requested

    primary_metrics = [
        metric
        for metric in PRIMARY_METRICS
        if metric in metric_names
    ]

    if metrics:
        primary_metrics = [
            metric
            for metric in available_metrics
            if metric in metric_names
        ]

    ctx = PlotContext(
        suite=suite,
        scenario_df=scenario_df,
        run_df=run_df,
        metric_names=metric_names,
        varying_dims=varying_dims,
        output_dir=output,
        formats=list(formats),
        dpi=dpi,
        created_files=[],
        notes=[],
    )

    if "arrival" not in scenario_df.columns or scenario_df["arrival"].nunique(dropna=True) <= 1:
        ctx.notes.append("Arrival-процесс не варьируется; часть combined-графиков будет пропущена.")

    if "workload" not in scenario_df.columns or scenario_df["workload"].nunique(dropna=True) <= 1:
        ctx.notes.append("Workload не варьируется; часть combined-графиков будет пропущена.")

    if "lambda" not in scenario_df.columns or scenario_df["lambda"].nunique(dropna=True) <= 1:
        ctx.notes.append("λ не варьируется; линейные графики будут содержать по одной точке.")

    if "sigma" in scenario_df.columns and scenario_df["sigma"].nunique(dropna=True) == 1:
        if not scenario_df["sigma"].dropna().empty:
            sigma = float(scenario_df["sigma"].dropna().iloc[0])
            ctx.notes.append(f"Скорость обслуживания фиксирована: σ={sigma:g}.")

    # Абсолютные сравнения.
    plot_heatmaps_workload_arrival_by_lambda(ctx, primary_metrics)
    plot_lines_arrivals_within_each_workload(ctx, primary_metrics)
    plot_lines_workloads_within_each_arrival(ctx, primary_metrics)

    # Явные baseline-смещения.
    plot_delta_arrival_vs_poisson_by_workload(ctx, primary_metrics)
    plot_delta_workload_vs_deterministic_by_arrival(ctx, primary_metrics)
    plot_joint_baseline_delta_heatmaps(ctx, primary_metrics)

    # Диагностика.
    plot_replication_boxplots(ctx, [m for m in BOXPLOT_METRICS if m in metric_names])
    plot_rejection_component_heatmaps(ctx)
    plot_stationary_tail_curves(ctx)

    write_summary_table(ctx, available_metrics)
    write_html_report(ctx, available_metrics)

    return ctx


# =============================================================================
# CLI
# =============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone renderer для combined-sensitivity suite_result.json"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Путь к suite_result.json или к директории серии",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Куда сохранять графики. По умолчанию <input>/plots_reworked",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=260,
        help="DPI для raster-форматов",
    )

    parser.add_argument(
        "--formats",
        nargs="+",
        default=["png"],
        help="Какие форматы сохранять. По умолчанию только png. Например: --formats svg или --formats png pdf",
    )

    parser.add_argument(
        "--metrics",
        nargs="*",
        default=None,
        help="Явно указать метрики для главных панелей",
    )

    parser.add_argument(
        "--list-metrics",
        action="store_true",
        help="Только вывести список доступных метрик",
    )

    parser.add_argument(
        "--clean-output",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Перед рендером удалить старые png/svg/pdf/html/csv из output-dir. По умолчанию включено.",
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    suite = load_suite_data(args.input)
    scenario_df, run_df, metric_names, varying_dims = build_dataframes(suite)

    if args.list_metrics:
        print("Доступные метрики:")
        for metric in metric_names:
            print(f"  - {metric}")
        print()
        print(f"Сценариев: {len(scenario_df)}")
        print(f"Варьирующие измерения: {varying_dims}")
        print(f"Run rows: {len(run_df)}")
        return

    json_path = resolve_suite_result_json(args.input)

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else json_path.parent / "plots_reworked"
    )

    output_dir = ensure_dir(output_dir)

    allowed_formats = {"png", "svg", "pdf"}
    formats = [
        fmt.lower().lstrip(".")
        for fmt in args.formats
    ]

    bad_formats = [
        fmt
        for fmt in formats
        if fmt not in allowed_formats
    ]

    if bad_formats:
        raise ValueError(
            f"Неподдерживаемые форматы: {bad_formats}. Доступны: {sorted(allowed_formats)}"
        )

    ctx = generate_plots(
        suite,
        output_dir,
        dpi=args.dpi,
        formats=formats,
        metrics=args.metrics,
        clean_output=bool(args.clean_output),
    )

    print("=" * 88)
    print(f"Suite: {ctx.suite.suite_name}")
    print(f"Created at: {ctx.suite.created_at}")
    print(f"Output dir: {ctx.output_dir}")
    print(f"Scenarios: {len(ctx.scenario_df)} | Runs: {len(ctx.run_df)}")
    print(f"Varying dims: {ctx.varying_dims}")
    print(f"Formats: {ctx.formats}")
    print(f"Saved files: {len(ctx.created_files)}")

    for path in ctx.created_files:
        print(f"  - {path}")

    if ctx.notes:
        print("Notes:")
        for note in dict.fromkeys(ctx.notes):
            print(f"  * {note}")

    print("=" * 88)


if __name__ == "__main__":
    main()