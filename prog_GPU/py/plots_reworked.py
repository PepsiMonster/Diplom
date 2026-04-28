from __future__ import annotations

import argparse
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable, Sequence 
'''
Чивапчичи
'''
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


# =============================================================================
# STYLE
# =============================================================================

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 220,
        "font.size": 11,
        "axes.titlesize": 16,
        "axes.labelsize": 12,
        "axes.titleweight": "semibold",
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "#fbfbfc",
        "grid.alpha": 0.25,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

CORE_METRICS = [
    "loss_probability",
    "throughput",
    "mean_num_jobs",
    "mean_occupied_resource",
    "mean_service_time",
    "mean_sojourn_time",
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

NAME_SHORT = {
    "deterministic": "Det",
    "exponential": "Exp",
    "erlang_2": "E2",
    "erlang_4": "E4",
    "erlang_8": "E8",
    "hyperexp_2": "H2",
    "hyperexp_heavy": "Heavy",
    "poisson": "Pois",
    "arrival": "arr",
    "workload": "work",
    "lambda": "λ",
    "sigma": "σ",
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
    "rejected_capacity": "Отказы по вместимости",
    "rejected_server": "Отказы по числу серверов",
    "rejected_resource": "Отказы по ресурсу",
}

METRIC_UNITS = {
    "mean_num_jobs": "заявок",
    "mean_occupied_resource": "ед. ресурса",
    "loss_probability": "доля",
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
        suite_name=str(payload["suite_name"]),
        created_at=str(payload.get("created_at", "")),
        ci_level=float(payload.get("ci_level", 0.95)),
        raw=payload,
    )


# =============================================================================
# PARSING HELPERS
# =============================================================================


def _float_slug_to_value(token: str) -> float:
    token = token.replace("p", ".")
    return float(token)



def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None



def _parse_pairs_from_name(name: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if ":" in name:
        _, tail = name.split(":", 1)
    else:
        tail = name
    for part in tail.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in {"lambda", "sigma"}:
            result[key] = _safe_float(value)
        else:
            result[key] = value
    if ":" in name:
        fam = name.split(":", 1)[0].strip()
        result.setdefault("family_name", fam)
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
        r"^(?P<family>[a-z0-9_]+)(?:__arr-(?P<arrival>[a-z0-9_]+))?(?:__work-(?P<workload>[a-z0-9_]+))?(?:__lam-(?P<lam>[0-9p]+))?(?:__sig-(?P<sig>[0-9p]+))?$",
        re.IGNORECASE,
    )
    m = pattern.match(scenario_key)
    if m:
        gd = m.groupdict()
        meta["family"] = gd.get("family")
        meta["arrival"] = gd.get("arrival")
        meta["workload"] = gd.get("workload")
        if gd.get("lam"):
            meta["lambda"] = _float_slug_to_value(gd["lam"])
        if gd.get("sig"):
            meta["sigma"] = _float_slug_to_value(gd["sig"])

    pairs = _parse_pairs_from_name(scenario_name)
    meta["arrival"] = pairs.get("arrival", meta["arrival"])
    meta["workload"] = pairs.get("workload", meta["workload"])
    meta["lambda"] = pairs.get("lambda", meta["lambda"])
    meta["sigma"] = pairs.get("sigma", meta["sigma"])

    fam_name = pairs.get("family_name")
    if fam_name and not meta["family"]:
        meta["family"] = fam_name.lower().replace("sensitivity", "")

    return meta



def _ordered_unique(values: Iterable[Any], preferred_order: Sequence[Any] | None = None) -> list[Any]:
    cleaned = [x for x in values if pd.notna(x)]
    unique = list(dict.fromkeys(cleaned))
    if preferred_order:
        preferred = [x for x in preferred_order if x in unique]
        rest = [x for x in unique if x not in preferred]
        rest_sorted = sorted(rest)
        return preferred + rest_sorted
    try:
        return sorted(unique)
    except TypeError:
        return unique



def _format_dim_value(dim: str, value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "∅"
    if dim == "lambda":
        return f"λ={float(value):g}"
    if dim == "sigma":
        return f"σ={float(value):g}"
    if dim in {"arrival", "workload"}:
        return NAME_SHORT.get(str(value), str(value))
    return str(value)



def _long_dim_value(dim: str, value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "∅"
    if dim == "lambda":
        return f"λ={float(value):g}"
    if dim == "sigma":
        return f"σ={float(value):g}"
    return str(value)



def build_short_label(row: pd.Series, varying_dims: list[str], *, multiline: bool = True) -> str:
    parts = []
    for dim in varying_dims:
        if dim == "arrival" and row.get(dim) == "poisson" and len(varying_dims) > 1:
            continue
        parts.append(_format_dim_value(dim, row.get(dim)))
    if not parts:
        parts = [Path(str(row.get("scenario_key", "scenario"))).name]
    sep = "\n" if multiline else " | "
    return sep.join(parts)


# =============================================================================
# DATAFRAMES
# =============================================================================


def build_dataframes(suite: SuiteData) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    scenario_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []

    scenario_results = dict(suite.raw["scenario_results"])
    metric_names = sorted(
        set().union(*[set(v.get("metric_summaries", {}).keys()) for v in scenario_results.values()])
    )

    for scenario_key, payload in scenario_results.items():
        scenario_name = str(payload.get("scenario_name", scenario_key))
        meta = parse_scenario_meta(scenario_key, scenario_name)
        row: dict[str, Any] = {
            **meta,
            "replications": int(payload.get("replications", len(payload.get("run_summaries", [])))),
        }
        metric_summaries = payload.get("metric_summaries", {})
        for metric_name, summary in metric_summaries.items():
            row[metric_name] = float(summary.get("mean", np.nan))
            row[f"{metric_name}__ci_low"] = float(summary.get("ci_low", np.nan))
            row[f"{metric_name}__ci_high"] = float(summary.get("ci_high", np.nan))
            row[f"{metric_name}__std"] = float(summary.get("std", np.nan))
            row[f"{metric_name}__stderr"] = float(summary.get("stderr", np.nan))
        scenario_rows.append(row)

        for run in payload.get("run_summaries", []):
            run_row = {**meta}
            run_row["replication_index"] = int(run.get("replication_index", -1))
            run_row["seed"] = int(run.get("seed", -1))
            for k, value in run.items():
                if isinstance(value, (int, float)):
                    run_row[k] = float(value)
            pi_hat = run.get("pi_hat")
            if isinstance(pi_hat, list):
                run_row["pi_hat_len"] = len(pi_hat)
            run_rows.append(run_row)

    scenario_df = pd.DataFrame(scenario_rows)
    run_df = pd.DataFrame(run_rows)

    for dim in ["lambda", "sigma"]:
        if dim in scenario_df.columns:
            scenario_df[dim] = pd.to_numeric(scenario_df[dim], errors="coerce")
        if dim in run_df.columns:
            run_df[dim] = pd.to_numeric(run_df[dim], errors="coerce")

    varying_dims = []
    for dim in ["arrival", "workload", "lambda", "sigma"]:
        if dim in scenario_df.columns:
            uniques = [x for x in scenario_df[dim].dropna().unique().tolist()]
            if len(uniques) > 1:
                varying_dims.append(dim)

    scenario_df = scenario_df.copy()
    scenario_df["short_label"] = scenario_df.apply(
        lambda row: build_short_label(row, varying_dims, multiline=True), axis=1
    )
    scenario_df["short_label_inline"] = scenario_df.apply(
        lambda row: build_short_label(row, varying_dims, multiline=False), axis=1
    )

    if not scenario_df.empty:
        sort_cols = [c for c in ["arrival", "workload", "lambda", "sigma"] if c in scenario_df.columns]
        scenario_df = scenario_df.sort_values(sort_cols, kind="stable").reset_index(drop=True)
        if not run_df.empty:
            run_sort_cols = [c for c in ["arrival", "workload", "lambda", "sigma", "replication_index"] if c in run_df.columns]
            run_df = run_df.sort_values(run_sort_cols, kind="stable").reset_index(drop=True)

    return scenario_df, run_df, metric_names, varying_dims


# =============================================================================
# PLOT HELPERS
# =============================================================================


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path



def metric_title(metric: str) -> str:
    return METRIC_TITLES.get(metric, metric)



def metric_ylabel(metric: str) -> str:
    unit = METRIC_UNITS.get(metric)
    if unit:
        return f"{metric_title(metric)} [{unit}]"
    return metric_title(metric)



def series_formatter(values: np.ndarray):
    vmax = float(np.nanmax(np.abs(values))) if len(values) else 1.0
    if vmax >= 1000:
        return lambda x: f"{x:,.0f}".replace(",", " ")
    if vmax >= 10:
        return lambda x: f"{x:.2f}"
    if vmax >= 1:
        return lambda x: f"{x:.3f}"
    if vmax >= 1e-2:
        return lambda x: f"{x:.4f}"
    return lambda x: f"{x:.6f}"



def nice_bounds(values: np.ndarray, lower: np.ndarray | None = None, upper: np.ndarray | None = None, *, include_zero: bool = False) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    ymin = float(np.nanmin(arr))
    ymax = float(np.nanmax(arr))
    if lower is not None:
        ymin = min(ymin, float(np.nanmin(arr - lower)))
    if upper is not None:
        ymax = max(ymax, float(np.nanmax(arr + upper)))
    if include_zero:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)
    span = ymax - ymin
    if span <= 1e-15:
        margin = max(abs(ymax) * 0.05, 1e-6)
    else:
        margin = max(span * 0.12, 1e-6)
    return ymin - margin, ymax + margin



def choose_x_and_group_dims(df: pd.DataFrame) -> tuple[str | None, str | None, list[str]]:
    varying = []
    for dim in ["arrival", "workload", "lambda", "sigma"]:
        if dim in df.columns and df[dim].nunique(dropna=True) > 1:
            varying.append(dim)

    if "lambda" in varying:
        x_dim = "lambda"
    elif "sigma" in varying:
        x_dim = "sigma"
    else:
        x_dim = None

    group_dim = None
    for candidate in ["workload", "arrival"]:
        if candidate in varying and candidate != x_dim:
            group_dim = candidate
            break

    facet_dims = [dim for dim in varying if dim not in {x_dim, group_dim}]
    return x_dim, group_dim, facet_dims



def choose_heatmap_dims(df: pd.DataFrame) -> tuple[str, str, list[str]]:
    varying = [
        dim
        for dim in ["workload", "arrival", "lambda", "sigma"]
        if dim in df.columns and df[dim].nunique(dropna=True) > 1
    ]

    if "workload" in varying and "lambda" in varying:
        row_dim, col_dim = "workload", "lambda"
    elif "arrival" in varying and "lambda" in varying:
        row_dim, col_dim = "arrival", "lambda"
    elif "workload" in varying and "sigma" in varying:
        row_dim, col_dim = "workload", "sigma"
    elif "arrival" in varying and "sigma" in varying:
        row_dim, col_dim = "arrival", "sigma"
    elif "arrival" in varying and "workload" in varying:
        row_dim, col_dim = "arrival", "workload"
    elif len(varying) >= 2:
        row_dim, col_dim = varying[0], varying[1]
    elif len(varying) == 1:
        row_dim, col_dim = varying[0], varying[0]
    else:
        row_dim, col_dim = "scenario_key", "scenario_key"

    facet_dims = [dim for dim in varying if dim not in {row_dim, col_dim}]
    return row_dim, col_dim, facet_dims



def dim_values(df: pd.DataFrame, dim: str) -> list[Any]:
    if dim == "workload":
        return _ordered_unique(df[dim].dropna().tolist(), WORKLOAD_ORDER)
    if dim == "arrival":
        return _ordered_unique(df[dim].dropna().tolist(), ARRIVAL_ORDER)
    return _ordered_unique(df[dim].dropna().tolist())



def axis_labels_for_values(dim: str, values: Sequence[Any]) -> list[str]:
    return [_long_dim_value(dim, v) for v in values]



def add_value_labels(ax: plt.Axes, xs: Sequence[float], ys: Sequence[float], formatter) -> None:
    ymin, ymax = ax.get_ylim()
    dy = ymax - ymin
    for x, y in zip(xs, ys):
        ax.text(x, y + dy * 0.015, formatter(y), ha="center", va="bottom", fontsize=9)



def save_figure(ctx: PlotContext, fig: plt.Figure, stem: str) -> None:
    fig.tight_layout()
    for fmt in ctx.formats:
        out = ctx.output_dir / f"{stem}.{fmt}"
        fig.savefig(out, dpi=ctx.dpi, bbox_inches="tight")
        ctx.created_files.append(out)
    plt.close(fig)



def make_note_figure(ctx: PlotContext, title: str, lines: list[str], stem: str) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.axis("off")
    ax.set_title(title, loc="left", pad=10)
    text = "\n".join(f"• {line}" for line in lines)
    ax.text(
        0.02,
        0.95,
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=12,
        family="DejaVu Sans",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f7f7fb", "edgecolor": "#d5d7e0"},
    )
    save_figure(ctx, fig, stem)


# =============================================================================
# DELTA REFERENCE LOGIC
# =============================================================================


def reference_dimension(df: pd.DataFrame) -> str | None:
    varying = [
        dim for dim in ["workload", "arrival", "lambda", "sigma"]
        if dim in df.columns and df[dim].nunique(dropna=True) > 1
    ]
    for dim in ["workload", "arrival", "lambda", "sigma"]:
        if dim in varying:
            return dim
    return None



def reference_value(df: pd.DataFrame, dim: str) -> Any:
    if dim == "workload":
        for name in ["deterministic", "exponential"]:
            if name in set(df[dim].dropna().tolist()):
                return name
        return dim_values(df, dim)[0]
    if dim == "arrival":
        if "poisson" in set(df[dim].dropna().tolist()):
            return "poisson"
        return dim_values(df, dim)[0]
    if dim == "lambda":
        return min(dim_values(df, dim))
    if dim == "sigma":
        return min(dim_values(df, dim))
    return None



def compute_delta_frame(df: pd.DataFrame, metrics: Sequence[str]) -> tuple[pd.DataFrame, str | None, Any]:
    ref_dim = reference_dimension(df)
    out = df.copy()
    if ref_dim is None:
        for metric in metrics:
            out[f"delta__{metric}"] = 0.0
        return out, None, None

    ref_val = reference_value(df, ref_dim)
    group_dims = [
        dim for dim in ["arrival", "workload", "lambda", "sigma"]
        if dim in out.columns and dim != ref_dim
    ]

    ref_rows = out[out[ref_dim] == ref_val].copy()
    ref_cols = group_dims + [metric for metric in metrics if metric in out.columns]
    ref_rows = ref_rows[ref_cols].copy()
    rename_map = {metric: f"__ref__{metric}" for metric in metrics if metric in ref_rows.columns}
    ref_rows = ref_rows.rename(columns=rename_map)

    merged = out.merge(ref_rows, on=group_dims, how="left") if group_dims else out.assign(**ref_rows.iloc[0].to_dict())
    if not group_dims:
        for ref_col, ref_value in ref_rows.iloc[0].to_dict().items():
            merged[ref_col] = ref_value

    for metric in metrics:
        if metric not in merged.columns:
            continue
        ref_col = f"__ref__{metric}"
        base = merged[ref_col].astype(float)
        cur = merged[metric].astype(float)
        delta = np.where(np.abs(base) > 1e-15, (cur / base - 1.0) * 100.0, 0.0)
        merged[f"delta__{metric}"] = delta

    return merged, ref_dim, ref_val


# =============================================================================
# PLOTS
# =============================================================================


def plot_metric_dashboard(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    if not metrics:
        return

    x_dim, group_dim, facet_dims = choose_x_and_group_dims(ctx.scenario_df)
    formatter_cache = {
        metric: series_formatter(ctx.scenario_df[metric].to_numpy(dtype=float)) for metric in metrics
    }

    n = len(metrics)
    ncols = 2 if n > 1 else 1
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2 * ncols, 4.8 * nrows), squeeze=False)
    axes_flat = axes.ravel()

    if x_dim is None:
        order = ctx.scenario_df["short_label"].tolist()
        x = np.arange(len(order))
        for ax, metric in zip(axes_flat, metrics):
            values = ctx.scenario_df[metric].to_numpy(dtype=float)
            low = ctx.scenario_df[metric] - ctx.scenario_df.get(f"{metric}__ci_low", ctx.scenario_df[metric])
            high = ctx.scenario_df.get(f"{metric}__ci_high", ctx.scenario_df[metric]) - ctx.scenario_df[metric]
            low = np.asarray(low, dtype=float)
            high = np.asarray(high, dtype=float)
            ax.bar(x, values, width=0.72, alpha=0.88)
            ax.errorbar(x, values, yerr=[low, high], fmt="none", capsize=4, color="black", lw=1.2)
            ax.set_xticks(x)
            ax.set_xticklabels(order, rotation=0)
            ax.set_title(metric_title(metric))
            ax.set_ylabel(metric_ylabel(metric))
            ax.set_ylim(*nice_bounds(values, low, high, include_zero=False))
            add_value_labels(ax, x, values, formatter_cache[metric])
    else:
        x_values = dim_values(ctx.scenario_df, x_dim)
        x_positions = np.arange(len(x_values), dtype=float)

        if group_dim is None:
            groups = [(None, ctx.scenario_df)]
        else:
            groups = []
            for group_value in dim_values(ctx.scenario_df, group_dim):
                subset = ctx.scenario_df[ctx.scenario_df[group_dim] == group_value].copy()
                if not subset.empty:
                    groups.append((group_value, subset))

        if facet_dims:
            note = "Для линейных панелей дополнительные измерения свернуты в одну ось легенды."
            if note not in ctx.notes:
                ctx.notes.append(note)

        for ax, metric in zip(axes_flat, metrics):
            for group_value, subset in groups:
                subset = subset.sort_values(x_dim)
                y = subset[metric].to_numpy(dtype=float)
                xvals = subset[x_dim].to_numpy(dtype=float)
                low = subset[metric].to_numpy(dtype=float) - subset.get(f"{metric}__ci_low", subset[metric]).to_numpy(dtype=float)
                high = subset.get(f"{metric}__ci_high", subset[metric]).to_numpy(dtype=float) - subset[metric].to_numpy(dtype=float)
                label = _long_dim_value(group_dim, group_value) if group_dim is not None else None
                ax.errorbar(
                    xvals,
                    y,
                    yerr=[low, high],
                    marker="o",
                    linewidth=2.2,
                    capsize=3,
                    label=label,
                )
                for xv, yv in zip(xvals, y):
                    ax.annotate(
                        formatter_cache[metric](yv),
                        (xv, yv),
                        textcoords="offset points",
                        xytext=(0, 6),
                        ha="center",
                        fontsize=8.5,
                    )
            all_vals = ctx.scenario_df[metric].to_numpy(dtype=float)
            low_all = all_vals - ctx.scenario_df.get(f"{metric}__ci_low", ctx.scenario_df[metric]).to_numpy(dtype=float)
            high_all = ctx.scenario_df.get(f"{metric}__ci_high", ctx.scenario_df[metric]).to_numpy(dtype=float) - all_vals
            ax.set_title(metric_title(metric))
            axis_title = {"lambda": "Интенсивность поступления λ", "sigma": "Скорость обслуживания σ"}.get(x_dim, x_dim)
            ax.set_xlabel(axis_title)
            ax.set_ylabel(metric_ylabel(metric))
            ax.set_xlim(min(x_values) - 0.05 * max(1.0, abs(min(x_values))), max(x_values) + 0.05 * max(1.0, abs(max(x_values))))
            ax.set_ylim(*nice_bounds(all_vals, low_all, high_all, include_zero=False))
            ax.xaxis.set_major_locator(MaxNLocator(integer=False, nbins=min(6, len(x_values) + 1)))
            if group_dim is not None:
                ax.legend(frameon=True, title=group_dim, ncol=1)

    for ax in axes_flat[n:]:
        ax.axis("off")

    fig.suptitle(f"{ctx.suite.suite_name}: аккуратные сравнительные панели", y=1.01, fontsize=18)
    save_figure(ctx, fig, "01_metric_dashboard")



def plot_metric_heatmaps(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    if not metrics:
        return

    row_dim, col_dim, facet_dims = choose_heatmap_dims(ctx.scenario_df)
    if row_dim == col_dim == "scenario_key":
        make_note_figure(
            ctx,
            "Тепловые карты метрик",
            ["В данных нет минимум двух меняющихся измерений, поэтому тепловые карты неинформативны."],
            "02_metric_heatmaps",
        )
        return

    facet_combinations = [({}, "all")]
    if facet_dims:
        facet_frame = ctx.scenario_df[facet_dims].drop_duplicates().reset_index(drop=True)
        facet_combinations = []
        for _, facet_row in facet_frame.iterrows():
            mapping = {dim: facet_row[dim] for dim in facet_dims}
            title = ", ".join(_long_dim_value(dim, val) for dim, val in mapping.items())
            facet_combinations.append((mapping, title))

    # Most readable default: first facet only. If many facets, make separate figure notes.
    if len(facet_combinations) > 1:
        ctx.notes.append(
            f"Для тепловых карт найдено {len(facet_combinations)} фасетов; сохранен набор по всем фасетам в отдельных панелях."
        )

    max_facets_per_fig = 4
    chunk_index = 0
    for start in range(0, len(facet_combinations), max_facets_per_fig):
        chunk = facet_combinations[start:start + max_facets_per_fig]
        n_metrics = len(metrics)
        n_facets = len(chunk)
        fig, axes = plt.subplots(
            n_metrics,
            n_facets,
            figsize=(5.0 * n_facets, 3.7 * n_metrics),
            squeeze=False,
        )

        for col_idx, (facet_filter, facet_title) in enumerate(chunk):
            subset = ctx.scenario_df.copy()
            for dim, value in facet_filter.items():
                subset = subset[subset[dim] == value]

            row_values = dim_values(subset, row_dim)
            col_values = dim_values(subset, col_dim)
            row_labels = axis_labels_for_values(row_dim, row_values)
            col_labels = axis_labels_for_values(col_dim, col_values)

            for row_idx, metric in enumerate(metrics):
                ax = axes[row_idx, col_idx]
                matrix = np.full((len(row_values), len(col_values)), np.nan, dtype=float)
                for i, row_value in enumerate(row_values):
                    for j, col_value in enumerate(col_values):
                        hit = subset[(subset[row_dim] == row_value) & (subset[col_dim] == col_value)]
                        if not hit.empty:
                            matrix[i, j] = float(hit.iloc[0][metric])
                finite = matrix[np.isfinite(matrix)]
                if finite.size == 0:
                    ax.axis("off")
                    continue
                im = ax.imshow(matrix, aspect="auto", interpolation="nearest")
                ax.set_yticks(np.arange(len(row_values)))
                ax.set_yticklabels(row_labels)
                ax.set_xticks(np.arange(len(col_values)))
                ax.set_xticklabels(col_labels, rotation=0)
                ax.set_title(metric_title(metric) + (f"\n{facet_title}" if facet_title != "all" else ""))
                formatter = series_formatter(finite)
                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if np.isfinite(matrix[i, j]):
                            ax.text(j, i, formatter(matrix[i, j]), ha="center", va="center", fontsize=8.6)
                if col_idx == 0:
                    ax.set_ylabel(row_dim)
                if row_idx == n_metrics - 1:
                    ax.set_xlabel(col_dim)
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        stem = f"02_metric_heatmaps_{chunk_index:02d}" if len(facet_combinations) > max_facets_per_fig else "02_metric_heatmaps"
        save_figure(ctx, fig, stem)
        chunk_index += 1



def plot_delta_heatmaps(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    if not metrics:
        return

    delta_df, ref_dim, ref_val = compute_delta_frame(ctx.scenario_df, metrics)
    if ref_dim is None:
        make_note_figure(
            ctx,
            "Отклонения относительно базовой точки",
            ["В данных нет меняющихся осей, поэтому отклонения не рассчитывались."],
            "03_delta_heatmaps",
        )
        return

    row_dim, col_dim, facet_dims = choose_heatmap_dims(delta_df)
    facet_combinations = [({}, "all")]
    if facet_dims:
        facet_frame = delta_df[facet_dims].drop_duplicates().reset_index(drop=True)
        facet_combinations = []
        for _, facet_row in facet_frame.iterrows():
            mapping = {dim: facet_row[dim] for dim in facet_dims}
            title = ", ".join(_long_dim_value(dim, val) for dim, val in mapping.items())
            facet_combinations.append((mapping, title))

    max_facets_per_fig = 4
    chunk_index = 0
    for start in range(0, len(facet_combinations), max_facets_per_fig):
        chunk = facet_combinations[start:start + max_facets_per_fig]
        fig, axes = plt.subplots(
            len(metrics),
            len(chunk),
            figsize=(5.1 * len(chunk), 3.8 * len(metrics)),
            squeeze=False,
        )
        for col_idx, (facet_filter, facet_title) in enumerate(chunk):
            subset = delta_df.copy()
            for dim, value in facet_filter.items():
                subset = subset[subset[dim] == value]

            row_values = dim_values(subset, row_dim)
            col_values = dim_values(subset, col_dim)
            row_labels = axis_labels_for_values(row_dim, row_values)
            col_labels = axis_labels_for_values(col_dim, col_values)

            for row_idx, metric in enumerate(metrics):
                ax = axes[row_idx, col_idx]
                colname = f"delta__{metric}"
                matrix = np.full((len(row_values), len(col_values)), np.nan)
                for i, row_value in enumerate(row_values):
                    for j, col_value in enumerate(col_values):
                        hit = subset[(subset[row_dim] == row_value) & (subset[col_dim] == col_value)]
                        if not hit.empty:
                            matrix[i, j] = float(hit.iloc[0][colname])
                finite = matrix[np.isfinite(matrix)]
                if finite.size == 0:
                    ax.axis("off")
                    continue
                vmax = float(np.nanmax(np.abs(finite)))
                im = ax.imshow(matrix, aspect="auto", interpolation="nearest", vmin=-vmax, vmax=vmax, cmap="coolwarm")
                ax.set_yticks(np.arange(len(row_values)))
                ax.set_yticklabels(row_labels)
                ax.set_xticks(np.arange(len(col_values)))
                ax.set_xticklabels(col_labels, rotation=0)
                ref_text = f"ref: {_long_dim_value(ref_dim, ref_val)}"
                title = f"Δ {metric_title(metric)}, %\n{ref_text}"
                if facet_title != "all":
                    title += f"\n{facet_title}"
                ax.set_title(title)
                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if np.isfinite(matrix[i, j]):
                            ax.text(j, i, f"{matrix[i, j]:+.2f}", ha="center", va="center", fontsize=8.4)
                if col_idx == 0:
                    ax.set_ylabel(row_dim)
                if row_idx == len(metrics) - 1:
                    ax.set_xlabel(col_dim)
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        stem = f"03_delta_heatmaps_{chunk_index:02d}" if len(facet_combinations) > max_facets_per_fig else "03_delta_heatmaps"
        save_figure(ctx, fig, stem)
        chunk_index += 1



def plot_replication_boxplots(ctx: PlotContext, metrics: Sequence[str]) -> None:
    if ctx.run_df.empty:
        return
    metrics = [m for m in metrics if m in ctx.run_df.columns]
    if not metrics:
        return

    x_dim, facet_dim, remaining = choose_x_and_group_dims(ctx.run_df)
    if x_dim not in {"lambda", "sigma"}:
        # fallback to short scenario labels
        x_dim = None
        facet_dim = None
        remaining = []

    if x_dim is None or facet_dim is None:
        n = len(metrics)
        fig, axes = plt.subplots(n, 1, figsize=(12.0, 4.2 * n), squeeze=False)
        axes_flat = axes.ravel()
        order = ctx.scenario_df["scenario_key"].tolist()
        labels = ctx.scenario_df["short_label"].tolist()
        for ax, metric in zip(axes_flat, metrics):
            data = [ctx.run_df.loc[ctx.run_df["scenario_key"] == key, metric].dropna().to_numpy() for key in order]
            ax.boxplot(data, patch_artist=True, widths=0.65, showfliers=True)
            ax.set_xticks(np.arange(1, len(labels) + 1))
            ax.set_xticklabels(labels, rotation=0)
            ax.set_title(metric_title(metric))
            ax.set_ylabel(metric_ylabel(metric))
        save_figure(ctx, fig, "04_replication_boxplots")
        return

    facet_values = dim_values(ctx.run_df, facet_dim)
    x_values = dim_values(ctx.run_df, x_dim)
    n = len(metrics)
    ncols = len(facet_values)
    fig, axes = plt.subplots(n, ncols, figsize=(5.0 * ncols, 4.1 * n), squeeze=False)

    for col_idx, facet_value in enumerate(facet_values):
        facet_subset = ctx.run_df[ctx.run_df[facet_dim] == facet_value].copy()
        for row_idx, metric in enumerate(metrics):
            ax = axes[row_idx, col_idx]
            data = []
            positions = []
            for pos, x_value in enumerate(x_values, start=1):
                values = facet_subset.loc[facet_subset[x_dim] == x_value, metric].dropna().to_numpy(dtype=float)
                if values.size:
                    data.append(values)
                    positions.append(pos)
            if data:
                bp = ax.boxplot(data, positions=positions, patch_artist=True, widths=0.58, showfliers=True)
                for box in bp["boxes"]:
                    box.set_alpha(0.9)
                for median in bp["medians"]:
                    median.set_linewidth(1.6)
            ax.set_xticks(np.arange(1, len(x_values) + 1))
            ax.set_xticklabels([_long_dim_value(x_dim, x) for x in x_values])
            ax.set_title(f"{metric_title(metric)}\n{facet_dim}={facet_value}")
            ax.set_ylabel(metric_ylabel(metric))
            if row_idx == n - 1:
                ax.set_xlabel(x_dim)
    save_figure(ctx, fig, "04_replication_boxplots")



def plot_rejection_breakdown(ctx: PlotContext) -> None:
    available = [m for m in REJECTION_COMPONENTS if m in ctx.scenario_df.columns]
    if len(available) < 2:
        return

    x_dim, facet_dim, _ = choose_x_and_group_dims(ctx.scenario_df)
    if x_dim not in {"lambda", "sigma"}:
        x_dim = None
        facet_dim = None

    if x_dim is None:
        fig, ax = plt.subplots(figsize=(12.0, 5.6))
        order_df = ctx.scenario_df.copy()
        bottom = np.zeros(len(order_df), dtype=float)
        x = np.arange(len(order_df))
        for metric in available:
            y = order_df[metric].to_numpy(dtype=float)
            ax.bar(x, y, bottom=bottom, width=0.74, label=metric_title(metric), alpha=0.92)
            bottom += y
        ax.set_xticks(x)
        ax.set_xticklabels(order_df["short_label"].tolist(), rotation=0)
        ax.set_ylabel("Среднее число отказов")
        ax.set_title("Декомпозиция отказов")
        ax.legend(frameon=True)
        save_figure(ctx, fig, "05_rejection_breakdown")
        return

    if facet_dim is None:
        facet_values = [None]
    else:
        facet_values = dim_values(ctx.scenario_df, facet_dim)

    ncols = len(facet_values)
    fig, axes = plt.subplots(1, ncols, figsize=(5.4 * ncols, 4.6), squeeze=False)

    x_values = dim_values(ctx.scenario_df, x_dim)
    for idx, facet_value in enumerate(facet_values):
        ax = axes[0, idx]
        subset = ctx.scenario_df.copy()
        if facet_dim is not None:
            subset = subset[subset[facet_dim] == facet_value]
        subset = subset.sort_values(x_dim)
        bottom = np.zeros(len(x_values), dtype=float)
        for metric in available:
            y = []
            for x_value in x_values:
                hit = subset[subset[x_dim] == x_value]
                y.append(float(hit.iloc[0][metric]) if not hit.empty else 0.0)
            y_arr = np.asarray(y, dtype=float)
            ax.bar(np.arange(len(x_values)), y_arr, bottom=bottom, width=0.68, label=metric_title(metric), alpha=0.92)
            bottom += y_arr
        ax.set_xticks(np.arange(len(x_values)))
        ax.set_xticklabels([_long_dim_value(x_dim, x) for x in x_values])
        title = "Декомпозиция отказов"
        if facet_dim is not None:
            title += f"\n{facet_dim}={facet_value}"
        ax.set_title(title)
        ax.set_ylabel("Среднее число отказов")
        if idx == 0:
            ax.legend(frameon=True)
    save_figure(ctx, fig, "05_rejection_breakdown")



def plot_stationary_distribution(ctx: PlotContext) -> None:
    pi_metrics = sorted(
        [name for name in ctx.metric_names if re.fullmatch(r"pi_hat_\d+", name)],
        key=lambda x: int(x.split("_")[-1]),
    )
    if not pi_metrics:
        make_note_figure(ctx, "Стационарное распределение", ["Метрики вида pi_hat_k отсутствуют в JSON."], "06_stationary_distribution")
        return

    states = [int(name.split("_")[-1]) for name in pi_metrics]
    if len(states) <= 1:
        make_note_figure(
            ctx,
            "Стационарное распределение",
            [
                "В JSON сохранено только одно состояние k=0.",
                "Для содержательного графика нужно запускать расчёт без --gpu-no-pi-hat, чтобы backend сохранил state_times и полный вектор π̂(k).",
                "Сейчас построение полноценного распределения бессмысленно: на всех сценариях π̂(0)=1.",
            ],
            "06_stationary_distribution",
        )
        return

    matrix = ctx.scenario_df[pi_metrics].to_numpy(dtype=float)
    labels = ctx.scenario_df["short_label"].tolist()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.2), gridspec_kw={"width_ratios": [1.25, 1.0]})

    for i, row in enumerate(matrix):
        ax1.plot(states, row, marker="o", linewidth=1.8, alpha=0.85, label=labels[i])
    ax1.set_xlabel("Состояние k")
    ax1.set_ylabel(r"$\hat{\pi}(k)$")
    ax1.set_title("Оценка стационарного распределения")
    if len(labels) <= 8:
        ax1.legend(frameon=True, fontsize=9)

    im = ax2.imshow(matrix, aspect="auto", interpolation="nearest")
    ax2.set_yticks(np.arange(len(labels)))
    ax2.set_yticklabels(labels)
    ax2.set_xticks(np.arange(len(states)))
    ax2.set_xticklabels([str(s) for s in states])
    ax2.set_xlabel("Состояние k")
    ax2.set_title("Тепловая карта π̂(k)")
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)

    save_figure(ctx, fig, "06_stationary_distribution")



def plot_compact_overview(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    if not metrics:
        return
    x = np.arange(len(ctx.scenario_df))
    labels = ctx.scenario_df["short_label"].tolist()
    n = len(metrics)
    ncols = 2 if n > 1 else 1
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.0 * ncols, 3.9 * nrows), squeeze=False)
    for ax, metric in zip(axes.ravel(), metrics):
        y = ctx.scenario_df[metric].to_numpy(dtype=float)
        low = y - ctx.scenario_df.get(f"{metric}__ci_low", ctx.scenario_df[metric]).to_numpy(dtype=float)
        high = ctx.scenario_df.get(f"{metric}__ci_high", ctx.scenario_df[metric]).to_numpy(dtype=float) - y
        ax.bar(x, y, width=0.75, alpha=0.88)
        ax.errorbar(x, y, yerr=[low, high], fmt="none", capsize=3, color="black", lw=1.0)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=0)
        ax.set_title(metric_title(metric))
        ax.set_ylabel(metric_ylabel(metric))
        ax.set_ylim(*nice_bounds(y, low, high, include_zero=False))
    for ax in axes.ravel()[len(metrics):]:
        ax.axis("off")
    save_figure(ctx, fig, "07_compact_overview")


# =============================================================================
# REPORT
# =============================================================================


def write_summary_table(ctx: PlotContext, metrics: Sequence[str]) -> None:
    metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    cols = [c for c in ["family", "arrival", "workload", "lambda", "sigma", "short_label_inline"] if c in ctx.scenario_df.columns]
    export_cols = cols + list(metrics)
    out = ctx.scenario_df[export_cols].copy()
    csv_path = ctx.output_dir / "scenario_summary_pretty.csv"
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    ctx.created_files.append(csv_path)



def write_html_report(ctx: PlotContext, metrics: Sequence[str]) -> None:
    images = sorted([p for p in ctx.created_files if p.suffix.lower() in {".png", ".svg"} and p.name != "report.html"])
    preferred_images: dict[str, Path] = {}
    for img in images:
        stem = img.stem
        preferred_images.setdefault(stem, img)
        if img.suffix.lower() == ".png":
            preferred_images[stem] = img

    summary_cols = [c for c in ["arrival", "workload", "lambda", "sigma"] if c in ctx.scenario_df.columns]
    table_cols = summary_cols + [m for m in metrics if m in ctx.scenario_df.columns]
    table_df = ctx.scenario_df[[*table_cols]].copy()
    for metric in [m for m in metrics if m in table_df.columns]:
        fmt = series_formatter(table_df[metric].to_numpy(dtype=float))
        table_df[metric] = table_df[metric].map(fmt)

    html_images = "\n".join(
        f'<section class="card"><h2>{html.escape(path.stem)}</h2><img src="{html.escape(path.name)}" alt="{html.escape(path.stem)}"></section>'
        for path in preferred_images.values()
    )

    notes_html = "\n".join(f"<li>{html.escape(note)}</li>" for note in dict.fromkeys(ctx.notes))
    report = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{html.escape(ctx.suite.suite_name)} — plot report</title>
  <style>
    body {{ font-family: Inter, Segoe UI, Arial, sans-serif; margin: 24px; color: #1b1f28; background: #f5f7fb; }}
    h1, h2 {{ margin: 0 0 10px 0; }}
    .header, .card {{ background: white; border: 1px solid #dfe4ee; border-radius: 16px; padding: 18px 20px; box-shadow: 0 8px 24px rgba(18, 28, 45, 0.06); margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 18px; }}
    img {{ width: 100%; height: auto; border-radius: 12px; background: white; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e7eaf1; padding: 8px 10px; text-align: left; }}
    th {{ background: #f7f9fc; position: sticky; top: 0; }}
    ul {{ margin: 8px 0 0 22px; }}
    code {{ background: #f1f4f8; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <section class="header">
    <h1>{html.escape(ctx.suite.suite_name)}</h1>
    <p><strong>Создано:</strong> {html.escape(ctx.suite.created_at)}<br>
       <strong>CI:</strong> {ctx.suite.ci_level:.2f}<br>
       <strong>Сценариев:</strong> {len(ctx.scenario_df)}<br>
       <strong>Варьирующие измерения:</strong> {html.escape(', '.join(ctx.varying_dims) if ctx.varying_dims else 'нет')}</p>
  </section>

  <section class="card">
    <h2>Сводная таблица</h2>
    {table_df.to_html(index=False, border=0, classes='summary-table')}
  </section>

  <section class="card">
    <h2>Замечания рендера</h2>
    <ul>{notes_html or '<li>Нет замечаний.</li>'}</ul>
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
) -> PlotContext:
    scenario_df, run_df, metric_names, varying_dims = build_dataframes(suite)
    output = ensure_dir(output_dir)

    available_metrics = [m for m in CORE_METRICS if m in metric_names]
    if metrics:
        requested = [m for m in metrics if m in metric_names]
        if requested:
            available_metrics = requested

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

    if scenario_df.empty:
        raise ValueError("В suite_result.json нет сценариев")

    # Diagnostic notes
    if "pi_hat_0" in metric_names and len([m for m in metric_names if m.startswith("pi_hat_")]) == 1:
        ctx.notes.append("В JSON присутствует только pi_hat_0; полноценный график стационарного распределения недоступен.")
    if "arrival" in scenario_df.columns and scenario_df["arrival"].nunique(dropna=True) == 1:
        ctx.notes.append(f"Arrival-процесс фиксирован: {scenario_df['arrival'].dropna().iloc[0]}.")
    if "sigma" in scenario_df.columns and scenario_df["sigma"].nunique(dropna=True) == 1:
        ctx.notes.append(f"Скорость обслуживания фиксирована: σ={scenario_df['sigma'].dropna().iloc[0]:g}.")

    plot_metric_dashboard(ctx, available_metrics[:6])
    plot_metric_heatmaps(ctx, available_metrics[:4])
    plot_delta_heatmaps(ctx, [m for m in ["loss_probability", "throughput", "mean_num_jobs", "mean_occupied_resource"] if m in available_metrics or m in metric_names])
    plot_replication_boxplots(ctx, [m for m in BOXPLOT_METRICS if m in metric_names])
    plot_rejection_breakdown(ctx)
    plot_stationary_distribution(ctx)
    plot_compact_overview(ctx, [m for m in available_metrics if m in ["loss_probability", "throughput", "mean_service_time", "mean_sojourn_time"]][:4])

    write_summary_table(ctx, available_metrics)
    write_html_report(ctx, available_metrics)
    return ctx


# =============================================================================
# CLI
# =============================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Новый standalone-рендерер графиков по suite_result.json"
    )
    parser.add_argument("--input", required=True, help="Путь к suite_result.json или к директории серии")
    parser.add_argument("--output-dir", default=None, help="Куда сохранять графики. По умолчанию <input>/plots_reworked")
    parser.add_argument("--dpi", type=int, default=260, help="DPI для raster-форматов")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["png", "svg"],
        help="Какие форматы сохранять, например: --formats png svg pdf",
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
    output_dir = Path(args.output_dir) if args.output_dir else json_path.parent / "plots_reworked"
    output_dir = ensure_dir(output_dir)

    ctx = generate_plots(
        suite,
        output_dir,
        dpi=args.dpi,
        formats=[fmt.lower().lstrip(".") for fmt in args.formats],
        metrics=args.metrics,
    )

    print("=" * 88)
    print(f"Suite: {ctx.suite.suite_name}")
    print(f"Created at: {ctx.suite.created_at}")
    print(f"Output dir: {ctx.output_dir}")
    print(f"Scenarios: {len(ctx.scenario_df)} | Runs: {len(ctx.run_df)}")
    print(f"Varying dims: {ctx.varying_dims}")
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
