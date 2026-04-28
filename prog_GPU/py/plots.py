from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np
import pandas as pd


# =============================================================================
# DROP-IN REPLACEMENT FOR py/plots.py
# =============================================================================
#
# Назначение:
#   Файл сохраняет CLI-контракт старого plots.py, который вызывает py/launcher.py:
#       python py/plots.py --input <suite_result.json> --output-dir <.../plots> --dpi 200
#
#   Внутри строятся более репрезентативные графики для двух основных режимов:
#       - workload-sensitivity: сравнение распределений workload/service time;
#       - arrival-sensitivity: сравнение типов входящего потока.
#
#   Скрипт намеренно не требует seaborn и работает только на matplotlib/pandas/numpy.
#


# =============================================================================
# STYLE AND LABELS
# =============================================================================

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 220,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

WORKLOAD_ORDER = [
    "deterministic",
    "erlang_8",
    "erlang_4",
    "erlang_2",
    "exponential",
    "hyperexp_2",
    "hyperexp_heavy",
]

ARRIVAL_ORDER = [
    "poisson",
    "erlang_4",
    "erlang_2",
    "hyperexp_2",
]

WORKLOAD_LABELS = {
    "deterministic": "Детерм.",
    "exponential": "Эксп.",
    "erlang_2": "Эрланг-2",
    "erlang_4": "Эрланг-4",
    "erlang_8": "Эрланг-8",
    "hyperexp_2": "Гиперэксп.",
    "hyperexp_heavy": "Heavy-tail",
}

ARRIVAL_LABELS = {
    "poisson": "Пуассон",
    "erlang_2": "Эрланг-2",
    "erlang_4": "Эрланг-4",
    "hyperexp_2": "Гиперэксп.",
}

DIM_LABELS = {
    "workload": "распределение времени обслуживания",
    "arrival": "тип входящего потока",
}

METRIC_TITLES = {
    "loss_probability": "Вероятность отказа",
    "throughput": "Пропускная способность",
    "mean_num_jobs": "Среднее число заявок",
    "mean_occupied_resource": "Средний занятый ресурс",
    "mean_service_time": "Среднее время обслуживания",
    "mean_sojourn_time": "Среднее время пребывания",
    "std_service_time": "Std времени обслуживания",
    "std_sojourn_time": "Std времени пребывания",
    "accepted_arrivals": "Принятые заявки",
    "rejected_arrivals": "Отказы",
    "completed_jobs": "Завершённые заявки",
    "rejected_capacity": "Отказы по вместимости",
    "rejected_server": "Отказы по числу серверов",
    "rejected_resource": "Отказы по ресурсу",
    "arrival_attempts": "Попытки поступления",
    "completed_time_samples": "Число завершений в окне",
}

METRIC_UNITS = {
    "loss_probability": "доля",
    "throughput": "заявки / ед. времени",
    "mean_num_jobs": "заявок",
    "mean_occupied_resource": "ед. ресурса",
    "mean_service_time": "ед. времени",
    "mean_sojourn_time": "ед. времени",
    "std_service_time": "ед. времени",
    "std_sojourn_time": "ед. времени",
    "accepted_arrivals": "заявок",
    "rejected_arrivals": "заявок",
    "completed_jobs": "заявок",
    "rejected_capacity": "заявок",
    "rejected_server": "заявок",
    "rejected_resource": "заявок",
    "arrival_attempts": "заявок",
    "completed_time_samples": "заявок",
}

MAIN_METRICS = [
    "loss_probability",
    "throughput",
    "mean_num_jobs",
    "mean_occupied_resource",
]

TIME_METRICS = [
    "mean_service_time",
    "mean_sojourn_time",
]

DELTA_METRICS = [
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

REJECTION_LABELS = {
    "rejected_capacity": "Вместимость K",
    "rejected_server": "Серверы N",
    "rejected_resource": "Ресурс R",
}

PROBABILITY_METRICS = {
    "loss_probability",
    "queueing_probability",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(slots=True)
class SuiteData:
    suite_name: str
    created_at: str
    ci_level: float
    scenario_results: dict[str, dict[str, Any]]
    raw: dict[str, Any]


@dataclass(slots=True)
class PlotContext:
    suite: SuiteData
    scenario_df: pd.DataFrame
    run_df: pd.DataFrame
    metric_names: list[str]
    varying_dims: list[str]
    output_dir: Path
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
        if not candidate.exists():
            raise FileNotFoundError(f"В директории '{path}' не найден suite_result.json")
        return candidate
    if path.is_file():
        if path.suffix.lower() != ".json":
            raise ValueError(f"Ожидался .json или директория результата, получено: {path}")
        return path
    raise FileNotFoundError(f"Путь не найден: {path}")


def load_suite_data(input_path: str | Path) -> SuiteData:
    json_path = resolve_suite_result_json(input_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return SuiteData(
        suite_name=str(payload.get("suite_name", "suite")),
        created_at=str(payload.get("created_at", "")),
        ci_level=float(payload.get("ci_level", 0.95)),
        scenario_results=dict(payload.get("scenario_results", {})),
        raw=payload,
    )


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_figure(ctx: PlotContext, fig: plt.Figure, filename: str) -> Path:
    path = ctx.output_dir / sanitize_filename(filename)
    fig.tight_layout()
    fig.savefig(path, dpi=ctx.dpi, bbox_inches="tight")
    plt.close(fig)
    ctx.created_files.append(path)
    return path


# =============================================================================
# PARSING
# =============================================================================

def sanitize_filename(value: str) -> str:
    value = str(value).strip().replace(" ", "_")
    value = re.sub(r"[^A-Za-zА-Яа-я0-9_.=+\-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "plot"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        x = float(str(value).replace("p", "."))
    except Exception:
        return None
    if not math.isfinite(x):
        return None
    return x


def slug_to_float(token: str | None) -> float | None:
    if token is None:
        return None
    token = str(token).replace("p", ".")
    return safe_float(token)


def parse_pairs_from_name(name: str) -> dict[str, Any]:
    """Fallback parser for names like '...: arrival=poisson, workload=exponential, lambda=75'."""
    out: dict[str, Any] = {}
    tail = name.split(":", 1)[1] if ":" in name else name
    for part in tail.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in {"lambda", "lam", "arrival_rate"}:
            out["lambda"] = safe_float(value)
        elif key in {"sigma", "service_speed"}:
            out["sigma"] = safe_float(value)
        elif key in {"arrival", "arrival_kind", "arrival_process"}:
            out["arrival"] = value
        elif key in {"workload", "workload_kind"}:
            out["workload"] = value
        elif key in {"family"}:
            out["family"] = value
    if ":" in name:
        out.setdefault("family", name.split(":", 1)[0].strip())
    return out


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
        r"(?:__arr-(?P<arrival>[a-z0-9_\-]+))?"
        r"(?:__work-(?P<workload>[a-z0-9_\-]+))?"
        r"(?:__lam-(?P<lam>[0-9p.+\-]+))?"
        r"(?:__sig-(?P<sig>[0-9p.+\-]+))?$",
        re.IGNORECASE,
    )
    m = pattern.match(scenario_key)
    if m:
        gd = m.groupdict()
        meta["family"] = gd.get("family")
        meta["arrival"] = gd.get("arrival")
        meta["workload"] = gd.get("workload")
        meta["lambda"] = slug_to_float(gd.get("lam"))
        meta["sigma"] = slug_to_float(gd.get("sig"))

    fallback = parse_pairs_from_name(scenario_name)
    for key, value in fallback.items():
        if meta.get(key) is None and value is not None:
            meta[key] = value

    # Нормализуем частые варианты названий.
    for key in ["family", "arrival", "workload"]:
        if meta.get(key) is not None:
            meta[key] = str(meta[key]).strip().lower().replace("-", "_")

    return meta


def metric_summary_value(summary: dict[str, Any], name: str, default: float = np.nan) -> float:
    value = summary.get(name, default)
    try:
        return float(value)
    except Exception:
        return default


def build_dataframes(suite: SuiteData) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    scenario_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    metric_names: set[str] = set()

    for order, (scenario_key, payload) in enumerate(suite.scenario_results.items()):
        scenario_name = str(payload.get("scenario_name", scenario_key))
        meta = parse_scenario_meta(scenario_key, scenario_name)
        metric_summaries = dict(payload.get("metric_summaries", {}))
        metric_names.update(metric_summaries.keys())

        row: dict[str, Any] = {
            "scenario_order": order,
            **meta,
        }

        for metric_name, summary_obj in metric_summaries.items():
            if not isinstance(summary_obj, dict):
                continue
            row[metric_name] = metric_summary_value(summary_obj, "mean")
            row[f"{metric_name}__std"] = metric_summary_value(summary_obj, "std")
            row[f"{metric_name}__ci_low"] = metric_summary_value(summary_obj, "ci_low")
            row[f"{metric_name}__ci_high"] = metric_summary_value(summary_obj, "ci_high")

        scenario_rows.append(row)

        for run_idx, run_summary in enumerate(payload.get("run_summaries", [])):
            if not isinstance(run_summary, dict):
                continue
            run_row = {
                "scenario_order": order,
                "run_index": run_idx,
                **meta,
            }
            for key, value in run_summary.items():
                try:
                    run_row[key] = float(value)
                except Exception:
                    run_row[key] = value
            run_rows.append(run_row)

    scenario_df = pd.DataFrame(scenario_rows)
    run_df = pd.DataFrame(run_rows)
    metric_list = sorted(metric_names)

    if scenario_df.empty:
        varying_dims: list[str] = []
        return scenario_df, run_df, metric_list, varying_dims

    for col in ["lambda", "sigma"]:
        if col in scenario_df.columns:
            scenario_df[col] = pd.to_numeric(scenario_df[col], errors="coerce")
        if col in run_df.columns:
            run_df[col] = pd.to_numeric(run_df[col], errors="coerce")

    varying_dims = []
    for col in ["workload", "arrival", "lambda", "sigma"]:
        if col in scenario_df.columns and scenario_df[col].nunique(dropna=True) > 1:
            varying_dims.append(col)

    scenario_df = sort_scenario_df(scenario_df)
    if not run_df.empty:
        run_df = sort_scenario_df(run_df)

    return scenario_df, run_df, metric_list, varying_dims


def sort_key_for_value(value: Any, order: Sequence[str]) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return len(order) + 999
    s = str(value)
    try:
        return order.index(s)
    except ValueError:
        return len(order) + abs(hash(s)) % 1000


def sort_scenario_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["__workload_order"] = out.get("workload", pd.Series(index=out.index, dtype=object)).map(
        lambda x: sort_key_for_value(x, WORKLOAD_ORDER)
    )
    out["__arrival_order"] = out.get("arrival", pd.Series(index=out.index, dtype=object)).map(
        lambda x: sort_key_for_value(x, ARRIVAL_ORDER)
    )
    sort_cols = [c for c in ["sigma", "lambda", "__arrival_order", "__workload_order", "scenario_order"] if c in out.columns]
    out = out.sort_values(sort_cols, kind="stable").drop(columns=["__workload_order", "__arrival_order"], errors="ignore")
    return out.reset_index(drop=True)


# =============================================================================
# FORMATTING HELPERS
# =============================================================================

def display_metric(metric_name: str) -> str:
    return METRIC_TITLES.get(metric_name, metric_name)


def metric_ylabel(metric_name: str) -> str:
    unit = METRIC_UNITS.get(metric_name)
    title = display_metric(metric_name)
    return f"{title}, {unit}" if unit else title


def display_dim_value(dimension: str, value: Any) -> str:
    if dimension == "workload":
        return WORKLOAD_LABELS.get(str(value), str(value))
    if dimension == "arrival":
        return ARRIVAL_LABELS.get(str(value), str(value))
    return str(value)


def dimension_order(dimension: str) -> list[str]:
    if dimension == "workload":
        return WORKLOAD_ORDER
    if dimension == "arrival":
        return ARRIVAL_ORDER
    return []


def baseline_for_dimension(dimension: str, available_values: Sequence[str]) -> str | None:
    preferred = "deterministic" if dimension == "workload" else "poisson"
    if preferred in set(map(str, available_values)):
        return preferred
    ordered = [v for v in dimension_order(dimension) if v in set(map(str, available_values))]
    if ordered:
        return ordered[0]
    return str(available_values[0]) if available_values else None


def available_dimension_values(df: pd.DataFrame, dimension: str) -> list[str]:
    if dimension not in df.columns:
        return []
    raw = [str(x) for x in df[dimension].dropna().unique().tolist()]
    order = dimension_order(dimension)
    return sorted(raw, key=lambda x: sort_key_for_value(x, order))


def finite_values(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            x = float(value)
        except Exception:
            continue
        if math.isfinite(x):
            out.append(x)
    return out


def ci_errors(row: pd.Series, metric_name: str) -> tuple[float, float] | None:
    mean = safe_float(row.get(metric_name))
    low = safe_float(row.get(f"{metric_name}__ci_low"))
    high = safe_float(row.get(f"{metric_name}__ci_high"))
    if mean is None or low is None or high is None:
        return None
    return max(mean - low, 0.0), max(high - mean, 0.0)


def set_smart_ylim(ax: plt.Axes, values: Sequence[float], errors: Sequence[tuple[float, float]] | None = None, *, include_zero: bool = False) -> None:
    vals = finite_values(values)
    if not vals:
        return
    lows = vals.copy()
    highs = vals.copy()
    if errors:
        lows = [v - e[0] for v, e in zip(vals, errors)]
        highs = [v + e[1] for v, e in zip(vals, errors)]
    ymin = min(lows)
    ymax = max(highs)
    if include_zero:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)
    span = ymax - ymin
    if span <= 1e-14:
        margin = max(abs(ymax) * 0.03, 1e-6)
    else:
        margin = max(span * 0.12, 1e-8)
    ax.set_ylim(ymin - margin, ymax + margin)


def format_axis_for_metric(ax: plt.Axes, metric_name: str, values: Sequence[float] | None = None) -> None:
    if metric_name in PROBABILITY_METRICS:
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.4f"))
        return
    vals = finite_values(values or [])
    vmax = max(abs(v) for v in vals) if vals else 1.0
    if vmax >= 1000:
        ax.ticklabel_format(axis="y", style="plain")
    elif vmax < 1e-2:
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.6f"))
    elif vmax < 1:
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.4f"))


def sigma_suffix(sigma_value: Any) -> str:
    sigma = safe_float(sigma_value)
    if sigma is None:
        return ""
    return f"_sigma-{sigma:g}".replace(".", "p")


def lambda_suffix(lambda_value: Any) -> str:
    lam = safe_float(lambda_value)
    if lam is None:
        return ""
    return f"_lambda-{lam:g}".replace(".", "p")


def subtitle_for_filter(df: pd.DataFrame) -> str:
    parts: list[str] = []
    if "arrival" in df.columns and df["arrival"].nunique(dropna=True) == 1:
        parts.append(f"arrival={display_dim_value('arrival', df['arrival'].dropna().iloc[0])}")
    if "workload" in df.columns and df["workload"].nunique(dropna=True) == 1:
        parts.append(f"workload={display_dim_value('workload', df['workload'].dropna().iloc[0])}")
    if "sigma" in df.columns and df["sigma"].nunique(dropna=True) == 1:
        parts.append(f"σ={df['sigma'].dropna().iloc[0]:g}")
    return " | ".join(parts)


def unique_sigmas(df: pd.DataFrame) -> list[float | None]:
    if "sigma" not in df.columns or df["sigma"].dropna().empty:
        return [None]
    sigmas = sorted(df["sigma"].dropna().unique().tolist())
    return sigmas or [None]


def filter_sigma(df: pd.DataFrame, sigma: float | None) -> pd.DataFrame:
    if sigma is None or "sigma" not in df.columns:
        return df.copy()
    return df[np.isclose(df["sigma"].astype(float), float(sigma), equal_nan=False)].copy()


# =============================================================================
# GENERIC PLOT HELPERS
# =============================================================================

def make_panel_grid(n: int, *, title: str) -> tuple[plt.Figure, np.ndarray]:
    if n <= 2:
        rows, cols = 1, n
        figsize = (6.4 * cols, 4.7)
    else:
        rows, cols = 2, 2
        figsize = (13.2, 8.5)
    fig, axes = plt.subplots(rows, cols, figsize=figsize, squeeze=False)
    fig.suptitle(title, fontsize=15, fontweight="semibold", y=1.02)
    return fig, axes.ravel()


def hide_unused_axes(axes: Sequence[plt.Axes], used: int) -> None:
    for ax in axes[used:]:
        ax.axis("off")


def add_legend_outside(fig: plt.Figure, axes: Sequence[plt.Axes], *, title: str | None = None) -> None:
    handles: list[Any] = []
    labels: list[str] = []
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        for handle, label in zip(h, l):
            if label not in labels and not label.startswith("_"):
                handles.append(handle)
                labels.append(label)
    if handles:
        fig.legend(handles, labels, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, title=title)


def plot_metric_lines_or_bars(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    dimension: str,
    metric_name: str,
    use_ci: bool = True,
) -> None:
    dim_values = available_dimension_values(df, dimension)
    if not dim_values or metric_name not in df.columns:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(display_metric(metric_name))
        return

    lambda_values = sorted(finite_values(df.get("lambda", [])))
    lambda_values = sorted(set(lambda_values))
    all_y: list[float] = []
    all_err: list[tuple[float, float]] = []

    if len(lambda_values) >= 2:
        for value in dim_values:
            sub = df[df[dimension].astype(str) == str(value)].sort_values("lambda")
            if sub.empty:
                continue
            x = sub["lambda"].astype(float).to_numpy()
            y = sub[metric_name].astype(float).to_numpy()
            all_y.extend(y.tolist())
            if use_ci and f"{metric_name}__ci_low" in sub.columns and f"{metric_name}__ci_high" in sub.columns:
                low = sub[f"{metric_name}__ci_low"].astype(float).to_numpy()
                high = sub[f"{metric_name}__ci_high"].astype(float).to_numpy()
                yerr = np.vstack([np.maximum(y - low, 0.0), np.maximum(high - y, 0.0)])
                all_err.extend(list(zip(yerr[0].tolist(), yerr[1].tolist())))
                ax.errorbar(x, y, yerr=yerr, marker="o", linewidth=1.8, capsize=3, label=display_dim_value(dimension, value))
            else:
                ax.plot(x, y, marker="o", linewidth=1.8, label=display_dim_value(dimension, value))
        ax.set_xlabel("Интенсивность поступления λ")
        ax.xaxis.set_major_locator(MaxNLocator(integer=False))
    else:
        x = np.arange(len(dim_values))
        y_vals: list[float] = []
        err_low: list[float] = []
        err_high: list[float] = []
        for value in dim_values:
            sub = df[df[dimension].astype(str) == str(value)]
            if sub.empty:
                y_vals.append(np.nan)
                err_low.append(0.0)
                err_high.append(0.0)
                continue
            row = sub.iloc[0]
            y = safe_float(row.get(metric_name))
            y_vals.append(np.nan if y is None else y)
            err = ci_errors(row, metric_name) if use_ci else None
            err_low.append(err[0] if err else 0.0)
            err_high.append(err[1] if err else 0.0)
        ax.bar(x, y_vals, yerr=np.vstack([err_low, err_high]) if use_ci else None, capsize=3)
        ax.set_xticks(x)
        ax.set_xticklabels([display_dim_value(dimension, v) for v in dim_values], rotation=25, ha="right")
        all_y.extend([v for v in y_vals if math.isfinite(v)])
        all_err.extend(list(zip(err_low, err_high)))

    ax.set_title(display_metric(metric_name))
    ax.set_ylabel(metric_ylabel(metric_name))
    format_axis_for_metric(ax, metric_name, all_y)
    set_smart_ylim(ax, all_y, all_err if all_err else None, include_zero=False)


def plot_metric_panels_by_lambda(ctx: PlotContext, dimension: str, metrics: Sequence[str], *, prefix: str) -> None:
    available_metrics = [m for m in metrics if m in ctx.metric_names and m in ctx.scenario_df.columns]
    if not available_metrics or dimension not in ctx.scenario_df.columns:
        return

    for sigma in unique_sigmas(ctx.scenario_df):
        df = filter_sigma(ctx.scenario_df, sigma)
        if df[dimension].nunique(dropna=True) < 2:
            continue

        title = f"Основные метрики: {DIM_LABELS.get(dimension, dimension)}"
        sub = subtitle_for_filter(df)
        if sub:
            title += f"\n{sub}"
        fig, axes = make_panel_grid(len(available_metrics), title=title)
        for ax, metric in zip(axes, available_metrics):
            plot_metric_lines_or_bars(ax, df, dimension=dimension, metric_name=metric)
        hide_unused_axes(axes, len(available_metrics))
        add_legend_outside(fig, axes, title=DIM_LABELS.get(dimension, dimension))
        save_figure(ctx, fig, f"{prefix}_main_metrics{sigma_suffix(sigma)}.png")


def compute_delta_df(df: pd.DataFrame, dimension: str, metrics: Sequence[str]) -> tuple[pd.DataFrame, str | None]:
    dim_values = available_dimension_values(df, dimension)
    baseline = baseline_for_dimension(dimension, dim_values)
    if baseline is None:
        return pd.DataFrame(), None

    if dimension == "workload":
        group_cols = [c for c in ["lambda", "sigma", "arrival"] if c in df.columns]
    elif dimension == "arrival":
        group_cols = [c for c in ["lambda", "sigma", "workload"] if c in df.columns]
    else:
        group_cols = [c for c in ["lambda", "sigma"] if c in df.columns]

    rows: list[dict[str, Any]] = []
    for _, group in df.groupby(group_cols, dropna=False, sort=False):
        base_rows = group[group[dimension].astype(str) == str(baseline)]
        if base_rows.empty:
            continue
        base = base_rows.iloc[0]
        for _, row in group.iterrows():
            out = row.to_dict()
            for metric in metrics:
                if metric not in row or metric not in base:
                    continue
                value = safe_float(row.get(metric))
                base_value = safe_float(base.get(metric))
                if value is None or base_value is None:
                    out[f"{metric}__delta"] = np.nan
                    continue
                if metric in PROBABILITY_METRICS:
                    # Для вероятностей используем процентные пункты: так график устойчив при baseline≈0.
                    out[f"{metric}__delta"] = 100.0 * (value - base_value)
                elif abs(base_value) <= 1e-14:
                    out[f"{metric}__delta"] = np.nan
                else:
                    out[f"{metric}__delta"] = 100.0 * (value / base_value - 1.0)
            rows.append(out)

    return pd.DataFrame(rows), baseline


def plot_delta_panels_by_lambda(ctx: PlotContext, dimension: str, metrics: Sequence[str], *, prefix: str) -> None:
    available_metrics = [m for m in metrics if m in ctx.metric_names and m in ctx.scenario_df.columns]
    if not available_metrics or dimension not in ctx.scenario_df.columns:
        return

    for sigma in unique_sigmas(ctx.scenario_df):
        df_sigma = filter_sigma(ctx.scenario_df, sigma)
        if df_sigma[dimension].nunique(dropna=True) < 2:
            continue
        delta_df, baseline = compute_delta_df(df_sigma, dimension, available_metrics)
        if delta_df.empty or baseline is None:
            continue

        title = f"Отклонения от baseline: {display_dim_value(dimension, baseline)}"
        sub = subtitle_for_filter(df_sigma)
        if sub:
            title += f"\n{sub}"
        fig, axes = make_panel_grid(len(available_metrics), title=title)

        for ax, metric in zip(axes, available_metrics):
            delta_col = f"{metric}__delta"
            if delta_col not in delta_df.columns:
                ax.axis("off")
                continue
            for value in available_dimension_values(delta_df, dimension):
                subdf = delta_df[delta_df[dimension].astype(str) == str(value)].sort_values("lambda")
                if subdf.empty:
                    continue
                x = subdf["lambda"].astype(float).to_numpy() if "lambda" in subdf.columns else np.arange(len(subdf))
                y = subdf[delta_col].astype(float).to_numpy()
                ax.plot(x, y, marker="o", linewidth=1.8, label=display_dim_value(dimension, value))
            ax.axhline(0.0, linewidth=1.0, color="black", alpha=0.55)
            ax.set_title(display_metric(metric))
            ax.set_xlabel("Интенсивность поступления λ")
            if metric in PROBABILITY_METRICS:
                ax.set_ylabel("Δ, процентные пункты")
                ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
            else:
                ax.set_ylabel("Δ, %")
                ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f%%"))
            vals = finite_values(delta_df[delta_col].tolist())
            set_smart_ylim(ax, vals, include_zero=True)

        hide_unused_axes(axes, len(available_metrics))
        add_legend_outside(fig, axes, title=DIM_LABELS.get(dimension, dimension))
        save_figure(ctx, fig, f"{prefix}_delta_from_baseline{sigma_suffix(sigma)}.png")


def plot_grouped_metric_bars_by_lambda(ctx: PlotContext, dimension: str, metric_name: str, *, prefix: str) -> None:
    if dimension not in ctx.scenario_df.columns or metric_name not in ctx.scenario_df.columns:
        return
    if ctx.scenario_df[dimension].nunique(dropna=True) < 2:
        return

    for sigma in unique_sigmas(ctx.scenario_df):
        df = filter_sigma(ctx.scenario_df, sigma)
        lambda_values = sorted(set(finite_values(df.get("lambda", []))))
        dim_values = available_dimension_values(df, dimension)
        if not lambda_values or not dim_values:
            continue

        fig_width = max(9.0, 1.0 + 1.25 * len(dim_values))
        fig, ax = plt.subplots(figsize=(fig_width, 5.4))
        x = np.arange(len(dim_values))
        width = min(0.8 / max(len(lambda_values), 1), 0.24)
        offsets = (np.arange(len(lambda_values)) - (len(lambda_values) - 1) / 2.0) * width

        all_values: list[float] = []
        for offset, lam in zip(offsets, lambda_values):
            y_vals: list[float] = []
            err_low: list[float] = []
            err_high: list[float] = []
            for dim_value in dim_values:
                sub = df[(df[dimension].astype(str) == str(dim_value)) & np.isclose(df["lambda"].astype(float), lam)]
                if sub.empty:
                    y_vals.append(np.nan)
                    err_low.append(0.0)
                    err_high.append(0.0)
                    continue
                row = sub.iloc[0]
                y = safe_float(row.get(metric_name))
                y_vals.append(np.nan if y is None else y)
                err = ci_errors(row, metric_name)
                err_low.append(err[0] if err else 0.0)
                err_high.append(err[1] if err else 0.0)
            all_values.extend([v for v in y_vals if math.isfinite(v)])
            ax.bar(x + offset, y_vals, width=width, yerr=np.vstack([err_low, err_high]), capsize=3, label=f"λ={lam:g}")

        ax.set_xticks(x)
        ax.set_xticklabels([display_dim_value(dimension, v) for v in dim_values], rotation=20, ha="right")
        ax.set_ylabel(metric_ylabel(metric_name))
        ax.set_title(f"{display_metric(metric_name)} по уровням λ")
        sub = subtitle_for_filter(df)
        if sub:
            ax.set_xlabel(sub)
        ax.legend(frameon=False, ncols=min(3, len(lambda_values)))
        format_axis_for_metric(ax, metric_name, all_values)
        set_smart_ylim(ax, all_values, include_zero=False)
        save_figure(ctx, fig, f"{prefix}_{metric_name}_bars_by_lambda{sigma_suffix(sigma)}.png")


# =============================================================================
# STATIONARY DISTRIBUTION PLOTS
# =============================================================================

def pi_metric_names(metric_names: Sequence[str]) -> list[str]:
    pairs: list[tuple[int, str]] = []
    for name in metric_names:
        m = re.fullmatch(r"pi_hat_(\d+)", name)
        if m:
            pairs.append((int(m.group(1)), name))
    return [name for _, name in sorted(pairs)]


def pi_states(metric_names: Sequence[str]) -> np.ndarray:
    states: list[int] = []
    for name in pi_metric_names(metric_names):
        m = re.fullmatch(r"pi_hat_(\d+)", name)
        if m:
            states.append(int(m.group(1)))
    return np.asarray(states, dtype=int)


def row_pi_values(row: pd.Series, names: Sequence[str]) -> np.ndarray:
    return np.asarray([safe_float(row.get(name)) or 0.0 for name in names], dtype=float)


def selected_lambda_values(df: pd.DataFrame) -> list[float | None]:
    if "lambda" not in df.columns or df["lambda"].dropna().empty:
        return [None]
    values = sorted(set(finite_values(df["lambda"].tolist())))
    if len(values) <= 2:
        return values
    return [values[0], values[-1]]


def filter_lambda(df: pd.DataFrame, lam: float | None) -> pd.DataFrame:
    if lam is None or "lambda" not in df.columns:
        return df.copy()
    return df[np.isclose(df["lambda"].astype(float), float(lam), equal_nan=False)].copy()


def plot_stationary_distribution(ctx: PlotContext, dimension: str, *, prefix: str) -> None:
    names = pi_metric_names(ctx.metric_names)
    if len(names) <= 1 or dimension not in ctx.scenario_df.columns:
        if len(names) == 1:
            ctx.notes.append("В JSON есть только pi_hat_0; распределение по состояниям построить нельзя.")
        return
    if ctx.scenario_df[dimension].nunique(dropna=True) < 2:
        return

    states = pi_states(ctx.metric_names)
    for sigma in unique_sigmas(ctx.scenario_df):
        df_sigma = filter_sigma(ctx.scenario_df, sigma)
        for lam in selected_lambda_values(df_sigma):
            df = filter_lambda(df_sigma, lam)
            if df.empty:
                continue
            fig, ax = plt.subplots(figsize=(10.2, 5.8))
            max_visible_state = 0
            for value in available_dimension_values(df, dimension):
                sub = df[df[dimension].astype(str) == str(value)]
                if sub.empty:
                    continue
                row = sub.iloc[0]
                y = row_pi_values(row, names)
                visible = states[y > max(1e-7, y.max() * 1e-4)] if y.size else np.array([], dtype=int)
                if visible.size:
                    max_visible_state = max(max_visible_state, int(visible.max()))
                ax.plot(states, y, marker="o", markersize=3, linewidth=1.5, label=display_dim_value(dimension, value))

            ax.set_title("Оценка стационарного распределения числа заявок")
            sub_parts = []
            if lam is not None:
                sub_parts.append(f"λ={lam:g}")
            sub = subtitle_for_filter(df)
            if sub:
                sub_parts.append(sub)
            if sub_parts:
                ax.set_xlabel("k — число заявок в системе | " + " | ".join(sub_parts))
            else:
                ax.set_xlabel("k — число заявок в системе")
            ax.set_ylabel("π̂(k)")
            ax.yaxis.set_major_formatter(FormatStrFormatter("%.5f"))
            ax.set_xlim(left=0, right=max(max_visible_state + 2, 5))
            ax.legend(frameon=False, ncols=2)
            save_figure(ctx, fig, f"{prefix}_stationary_distribution{sigma_suffix(sigma)}{lambda_suffix(lam)}.png")

            # Tail plot is useful when heavy-tailed workload or bursty arrivals change the right tail.
            fig_tail, ax_tail = plt.subplots(figsize=(10.2, 5.8))
            any_tail = False
            for value in available_dimension_values(df, dimension):
                sub = df[df[dimension].astype(str) == str(value)]
                if sub.empty:
                    continue
                y = row_pi_values(sub.iloc[0], names)
                if y.size == 0:
                    continue
                tail = np.flip(np.cumsum(np.flip(y)))
                tail = np.maximum(tail, 1e-16)
                ax_tail.semilogy(states, tail, marker="o", markersize=3, linewidth=1.5, label=display_dim_value(dimension, value))
                any_tail = True
            if any_tail:
                ax_tail.set_title("Хвост стационарного распределения")
                if sub_parts:
                    ax_tail.set_xlabel("k — число заявок в системе | " + " | ".join(sub_parts))
                else:
                    ax_tail.set_xlabel("k — число заявок в системе")
                ax_tail.set_ylabel("P{N ≥ k}")
                ax_tail.set_xlim(left=0, right=max(max_visible_state + 2, 5))
                ax_tail.legend(frameon=False, ncols=2)
                save_figure(ctx, fig_tail, f"{prefix}_stationary_tail{sigma_suffix(sigma)}{lambda_suffix(lam)}.png")
            else:
                plt.close(fig_tail)


# =============================================================================
# REJECTION BREAKDOWN AND REPLICATION BOXPLOTS
# =============================================================================

def plot_rejection_breakdown(ctx: PlotContext, dimension: str, *, prefix: str) -> None:
    if dimension not in ctx.scenario_df.columns:
        return
    if not all(m in ctx.scenario_df.columns for m in REJECTION_COMPONENTS):
        return
    if ctx.scenario_df[dimension].nunique(dropna=True) < 2:
        return

    for sigma in unique_sigmas(ctx.scenario_df):
        df_sigma = filter_sigma(ctx.scenario_df, sigma)
        for lam in selected_lambda_values(df_sigma):
            df = filter_lambda(df_sigma, lam)
            dim_values = available_dimension_values(df, dimension)
            if not dim_values:
                continue
            fig, ax = plt.subplots(figsize=(max(8.5, 1.15 * len(dim_values)), 5.4))
            x = np.arange(len(dim_values))
            bottom = np.zeros(len(dim_values), dtype=float)
            for metric in REJECTION_COMPONENTS:
                vals: list[float] = []
                for value in dim_values:
                    sub = df[df[dimension].astype(str) == str(value)]
                    vals.append(float(sub.iloc[0][metric]) if not sub.empty and pd.notna(sub.iloc[0][metric]) else 0.0)
                vals_arr = np.asarray(vals, dtype=float)
                ax.bar(x, vals_arr, bottom=bottom, label=REJECTION_LABELS.get(metric, metric))
                bottom += vals_arr
            ax.set_xticks(x)
            ax.set_xticklabels([display_dim_value(dimension, v) for v in dim_values], rotation=20, ha="right")
            ax.set_ylabel("Число отказов")
            title = "Структура отказов"
            parts = []
            if lam is not None:
                parts.append(f"λ={lam:g}")
            sub = subtitle_for_filter(df)
            if sub:
                parts.append(sub)
            if parts:
                title += "\n" + " | ".join(parts)
            ax.set_title(title)
            ax.legend(frameon=False)
            set_smart_ylim(ax, bottom.tolist(), include_zero=True)
            save_figure(ctx, fig, f"{prefix}_rejection_breakdown{sigma_suffix(sigma)}{lambda_suffix(lam)}.png")


def plot_replication_boxplots(ctx: PlotContext, dimension: str, metrics: Sequence[str], *, prefix: str) -> None:
    if ctx.run_df.empty or dimension not in ctx.run_df.columns:
        return
    if ctx.run_df[dimension].nunique(dropna=True) < 2:
        return

    for metric_name in metrics:
        if metric_name not in ctx.run_df.columns:
            continue
        for sigma in unique_sigmas(ctx.run_df):
            df_sigma = filter_sigma(ctx.run_df, sigma)
            for lam in selected_lambda_values(df_sigma):
                df = filter_lambda(df_sigma, lam)
                dim_values = available_dimension_values(df, dimension)
                series: list[list[float]] = []
                labels: list[str] = []
                for value in dim_values:
                    vals = finite_values(df[df[dimension].astype(str) == str(value)][metric_name].tolist())
                    if vals:
                        series.append(vals)
                        labels.append(display_dim_value(dimension, value))
                if len(series) < 2:
                    continue
                fig, ax = plt.subplots(figsize=(max(8.5, 1.15 * len(series)), 5.4))
                ax.boxplot(series, labels=labels, showmeans=True)
                ax.set_title(f"Разброс по репликациям: {display_metric(metric_name)}")
                parts = []
                if lam is not None:
                    parts.append(f"λ={lam:g}")
                sub = subtitle_for_filter(df)
                if sub:
                    parts.append(sub)
                if parts:
                    ax.set_xlabel(" | ".join(parts))
                ax.set_ylabel(metric_ylabel(metric_name))
                ax.tick_params(axis="x", rotation=20)
                format_axis_for_metric(ax, metric_name, [v for values in series for v in values])
                save_figure(ctx, fig, f"{prefix}_boxplot_{metric_name}{sigma_suffix(sigma)}{lambda_suffix(lam)}.png")


# =============================================================================
# FALLBACK SUMMARY PLOTS
# =============================================================================

def plot_fallback_metric_bars(ctx: PlotContext, metrics: Sequence[str]) -> None:
    available_metrics = [m for m in metrics if m in ctx.scenario_df.columns]
    if not available_metrics:
        return
    labels = ctx.scenario_df["scenario_name"].astype(str).tolist()
    if len(labels) > 16:
        labels = ctx.scenario_df["scenario_key"].astype(str).tolist()

    fig, axes = make_panel_grid(len(available_metrics), title="Сравнение сценариев")
    x = np.arange(len(ctx.scenario_df))
    for ax, metric in zip(axes, available_metrics):
        y = ctx.scenario_df[metric].astype(float).to_numpy()
        err_low = np.zeros_like(y)
        err_high = np.zeros_like(y)
        if f"{metric}__ci_low" in ctx.scenario_df.columns and f"{metric}__ci_high" in ctx.scenario_df.columns:
            low = ctx.scenario_df[f"{metric}__ci_low"].astype(float).to_numpy()
            high = ctx.scenario_df[f"{metric}__ci_high"].astype(float).to_numpy()
            err_low = np.maximum(y - low, 0.0)
            err_high = np.maximum(high - y, 0.0)
        ax.bar(x, y, yerr=np.vstack([err_low, err_high]), capsize=3)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right")
        ax.set_title(display_metric(metric))
        ax.set_ylabel(metric_ylabel(metric))
        format_axis_for_metric(ax, metric, y.tolist())
        set_smart_ylim(ax, y.tolist(), list(zip(err_low.tolist(), err_high.tolist())), include_zero=False)
    hide_unused_axes(axes, len(available_metrics))
    save_figure(ctx, fig, "scenario_metric_bars.png")


# =============================================================================
# TABLE OUTPUT
# =============================================================================

def write_summary_table(ctx: PlotContext) -> None:
    keep_cols = [
        "scenario_key",
        "scenario_name",
        "family",
        "arrival",
        "workload",
        "lambda",
        "sigma",
    ]
    metric_cols = [m for m in MAIN_METRICS + TIME_METRICS if m in ctx.scenario_df.columns]
    cols = [c for c in keep_cols if c in ctx.scenario_df.columns] + metric_cols
    if not cols:
        return
    path = ctx.output_dir / "plot_summary_table.csv"
    ctx.scenario_df[cols].to_csv(path, index=False, encoding="utf-8-sig")
    ctx.created_files.append(path)


# =============================================================================
# MAIN GENERATION LOGIC
# =============================================================================

def infer_plot_dimensions(scenario_df: pd.DataFrame) -> list[str]:
    dims: list[str] = []
    if "workload" in scenario_df.columns and scenario_df["workload"].nunique(dropna=True) > 1:
        dims.append("workload")
    if "arrival" in scenario_df.columns and scenario_df["arrival"].nunique(dropna=True) > 1:
        dims.append("arrival")
    return dims


def prefix_for_dimension(dimension: str) -> str:
    return "workload_sensitivity" if dimension == "workload" else "arrival_sensitivity"


def generate_standard_plots(
    suite_data: SuiteData,
    output_dir: str | Path,
    *,
    dpi: int = 220,
    extra_metrics: Iterable[str] | None = None,
    build_delta_plots: bool = True,
) -> list[Path]:
    scenario_df, run_df, metric_names, varying_dims = build_dataframes(suite_data)
    out_dir = ensure_dir(output_dir)
    ctx = PlotContext(
        suite=suite_data,
        scenario_df=scenario_df,
        run_df=run_df,
        metric_names=metric_names,
        varying_dims=varying_dims,
        output_dir=out_dir,
        dpi=dpi,
        created_files=[],
        notes=[],
    )

    if scenario_df.empty:
        ctx.notes.append("scenario_results пуст: графики не построены.")
        return ctx.created_files

    requested_extra = list(extra_metrics or [])
    main_metrics = []
    for metric in MAIN_METRICS + requested_extra:
        if metric in metric_names and metric not in main_metrics:
            main_metrics.append(metric)

    time_metrics = [m for m in TIME_METRICS if m in metric_names]
    delta_metrics = [m for m in DELTA_METRICS if m in metric_names]

    dims = infer_plot_dimensions(scenario_df)
    if not dims:
        ctx.notes.append("Не найдено варьирующееся измерение workload/arrival; построен fallback-график по сценариям.")
        plot_fallback_metric_bars(ctx, main_metrics[:4])
        write_summary_table(ctx)
        print_notes(ctx)
        return ctx.created_files

    for dimension in dims:
        prefix = prefix_for_dimension(dimension)

        plot_metric_panels_by_lambda(ctx, dimension, main_metrics[:4], prefix=prefix)

        if time_metrics:
            plot_metric_panels_by_lambda(ctx, dimension, time_metrics, prefix=f"{prefix}_time")

        if build_delta_plots and delta_metrics:
            plot_delta_panels_by_lambda(ctx, dimension, delta_metrics[:4], prefix=prefix)

        if "loss_probability" in metric_names:
            plot_grouped_metric_bars_by_lambda(ctx, dimension, "loss_probability", prefix=prefix)

        if "mean_num_jobs" in metric_names:
            plot_grouped_metric_bars_by_lambda(ctx, dimension, "mean_num_jobs", prefix=prefix)

        plot_stationary_distribution(ctx, dimension, prefix=prefix)
        plot_rejection_breakdown(ctx, dimension, prefix=prefix)
        plot_replication_boxplots(ctx, dimension, [m for m in BOXPLOT_METRICS if m in metric_names], prefix=prefix)

    write_summary_table(ctx)
    print_notes(ctx)
    return ctx.created_files


def print_notes(ctx: PlotContext) -> None:
    if not ctx.notes:
        return
    print("Notes:")
    for note in dict.fromkeys(ctx.notes):
        print(f"  * {note}")


# =============================================================================
# CLI
# =============================================================================

def print_available_metrics(suite_data: SuiteData) -> None:
    scenario_df, run_df, metric_names, varying_dims = build_dataframes(suite_data)
    print("=" * 88)
    print(f"Suite: {suite_data.suite_name}")
    print(f"Created at: {suite_data.created_at}")
    print(f"CI level: {suite_data.ci_level}")
    print(f"Scenarios: {len(scenario_df)}")
    print(f"Run rows: {len(run_df)}")
    print(f"Varying dims: {varying_dims}")
    print("-" * 88)
    print("Доступные метрики:")
    for name in metric_names:
        print(f"  - {name}")
    print("=" * 88)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Построение графиков по suite_result.json для GPU-пайплайна"
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
        help="Дополнительные метрики для главных панелей",
    )
    parser.add_argument(
        "--no-delta-plots",
        action="store_true",
        help="Не строить графики отклонения от baseline",
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

    print("=" * 88)
    print(f"Suite: {suite_data.suite_name}")
    print(f"Графики сохранены в: {output_dir}")
    print(f"Создано файлов: {len(created)}")
    for path in created:
        print(f"  - {path}")
    print("=" * 88)


if __name__ == "__main__":
    main()
