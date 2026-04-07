from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle

from anim_config import DEFAULT_SCENE_CONFIG, SceneConfig


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"


def _merge_meta(meta: dict[str, Any] | None, cfg: SceneConfig) -> dict[str, Any]:
    """
    Дополняет meta значениями по умолчанию из fallback-конфига.
    """
    meta = dict(meta or {})
    fb = cfg.fallback

    return {
        "system_architecture": meta.get("system_architecture", fb.system_architecture),
        "servers_n": int(meta.get("servers_n", fb.servers_n)),
        "capacity_k": int(meta.get("capacity_k", fb.capacity_k)),
        "queue_capacity": int(meta.get("queue_capacity", fb.queue_capacity)),
        "total_resource_r": int(meta.get("total_resource_r", fb.total_resource_r)),
        "scenario_name": meta.get("scenario_name", "animation_preview"),
    }


def create_figure(cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> tuple[Figure, Axes]:
    """
    Создаёт matplotlib figure/axes для дальнейшего рисования сцены.
    """
    fig, ax = plt.subplots(
        figsize=(cfg.figure.width, cfg.figure.height),
        dpi=cfg.figure.dpi,
    )
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("auto")
    ax.axis("off")
    fig.patch.set_facecolor(cfg.style.background_color)
    ax.set_facecolor(cfg.style.background_color)
    return fig, ax


def draw_background_grid(ax: Axes, cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> None:
    """
    Лёгкая фоновая сетка. Нужна только как визуальный ориентир.
    """
    if not cfg.style.show_background_grid:
        return

    step = 0.02
    x = 0.0
    while x <= 1.0001:
        ax.plot(
            [x, x],
            [0.0, 1.0],
            color=cfg.style.grid_color,
            alpha=cfg.style.grid_alpha,
            linewidth=0.5,
            zorder=0,
        )
        x += step

    y = 0.0
    while y <= 1.0001:
        ax.plot(
            [0.0, 1.0],
            [y, y],
            color=cfg.style.grid_color,
            alpha=cfg.style.grid_alpha,
            linewidth=0.5,
            zorder=0,
        )
        y += step


def lane_height(meta: dict[str, Any], cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> float:
    """
    Высота одной дорожки обслуживания.
    """
    servers_n = max(1, int(meta["servers_n"]))
    return (cfg.layout.lanes_top - cfg.layout.lanes_bottom) / servers_n


def job_draw_height(meta: dict[str, Any], cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> float:
    """
    Реальная высота карточки заявки на дорожке.
    """
    lh = lane_height(meta, cfg)
    return min(cfg.layout.job_height, 0.72 * lh)


def lane_center_y(lane_id: int, meta: dict[str, Any], cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> float:
    """
    Центр дорожки с номером lane_id.
    Нумерация дорожек снизу вверх: 0, 1, 2, ...
    """
    lh = lane_height(meta, cfg)
    return cfg.layout.lanes_bottom + (lane_id + 0.5) * lh


def queue_slot_center_y(slot_index: int, meta: dict[str, Any], cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> float:
    """
    Центр ячейки очереди.
    Нумерация слотов сверху вниз: 0, 1, 2, ...
    """
    q = max(1, int(meta["queue_capacity"]))
    total_h = cfg.layout.queue_top - cfg.layout.queue_bottom
    slot_h = total_h / q
    return cfg.layout.queue_top - (slot_index + 0.5) * slot_h


def job_width_from_resource(
    resource_demand: float,
    total_resource_r: float,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
) -> float:
    """
    Преобразует требование ресурса r в ширину карточки заявки на дорожке.
    """
    total_resource_r = max(float(total_resource_r), 1.0)
    frac = max(0.0, min(float(resource_demand) / total_resource_r, 1.0))
    min_w = 0.035
    max_w = cfg.layout.lane_job_max_width
    return min_w + frac * (max_w - min_w)


def queue_job_width_from_resource(
    resource_demand: float,
    total_resource_r: float,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
) -> float:
    """
    Аналогично, но для карточек в очереди.
    """
    total_resource_r = max(float(total_resource_r), 1.0)
    frac = max(0.0, min(float(resource_demand) / total_resource_r, 1.0))
    min_w = 0.035
    max_w = cfg.layout.queue_job_max_width
    return min_w + frac * (max_w - min_w)


def draw_job_card(
    ax: Axes,
    x_left: float,
    y_center: float,
    width: float,
    height: float,
    label: str,
    facecolor: str,
    edgecolor: str,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
    alpha: float = 1.0,
    zorder: int = 5,
) -> dict[str, Any]:
    """
    Рисует одну карточку заявки.
    """
    y_bottom = y_center - 0.5 * height

    patch = FancyBboxPatch(
        (x_left, y_bottom),
        width,
        height,
        boxstyle="round,pad=0.003,rounding_size=0.01",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.3,
        alpha=alpha,
        zorder=zorder,
    )
    ax.add_patch(patch)

    text = ax.text(
        x_left + 0.5 * width,
        y_center,
        label,
        ha="center",
        va="center",
        fontsize=cfg.typography.job_text_size,
        color=cfg.style.text_color,
        weight="bold",
        zorder=zorder + 1,
    )

    return {"patch": patch, "text": text}


def draw_reject_zone(ax: Axes, cfg: SceneConfig = DEFAULT_SCENE_CONFIG) -> None:
    """
    Правая зона для rejected-job.
    """
    x = 0.94
    y = 0.57

    ax.text(
        x,
        y + 0.03,
        "Reject",
        ha="center",
        va="center",
        fontsize=cfg.typography.title_size - 2,
        color=cfg.style.text_color,
        weight="bold",
    )
    ax.text(
        x,
        y - 0.005,
        "(resource / capacity)",
        ha="center",
        va="center",
        fontsize=cfg.typography.label_size,
        color=cfg.style.subtle_text_color,
    )


def draw_static_scene(
    ax: Axes,
    meta: dict[str, Any] | None = None,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
    current_time: float = 0.0,
    resource_used: float = 0.0,
) -> dict[str, Any]:
    """
    Рисует всю статическую сцену и возвращает handles,
    которые потом пригодятся для анимации.
    """
    meta = _merge_meta(meta, cfg)
    style = cfg.style
    typo = cfg.typography

    draw_background_grid(ax, cfg)

    # ---------------------------------
    # Локально ужимаем/уточняем геометрию
    # ---------------------------------
    queue_x = 0.07
    queue_y = 0.18
    queue_w = 0.14
    queue_h = 0.64

    lanes_x = 0.22
    lanes_y = 0.18
    lanes_w = 0.66
    lanes_h = 0.64

    rb_x = 0.22
    rb_y = 0.865
    rb_w = 0.66
    rb_h = 0.045

    # ---------------------------------
    # Основные панели
    # ---------------------------------
    queue_panel = Rectangle(
        (queue_x, queue_y),
        queue_w,
        queue_h,
        facecolor=style.queue_fill,
        edgecolor=style.panel_edge,
        linewidth=1.6,
        zorder=1,
    )
    ax.add_patch(queue_panel)

    service_panel = Rectangle(
        (lanes_x, lanes_y),
        lanes_w,
        lanes_h,
        facecolor=style.panel_fill,
        edgecolor=style.panel_edge,
        linewidth=1.6,
        zorder=1,
    )
    ax.add_patch(service_panel)

    # ---------------------------------
    # Дорожки обслуживания
    # ---------------------------------
    servers_n = int(meta["servers_n"])
    lh = lanes_h / servers_n

    for lane_id in range(servers_n + 1):
        y = lanes_y + lane_id * lh
        ax.plot(
            [lanes_x, lanes_x + lanes_w],
            [y, y],
            color=style.lane_line,
            linewidth=1.0,
            zorder=2,
        )

    for lane_id in range(servers_n):
        yc = lanes_y + (lane_id + 0.5) * lh
        ax.text(
            lanes_x + 0.01,
            yc,
            f"{lane_id + 1}",
            ha="left",
            va="center",
            fontsize=typo.small_label_size,
            color=style.subtle_text_color,
            zorder=3,
        )

    # ---------------------------------
    # Верхние подписи
    # ---------------------------------
    ax.text(
        queue_x + 0.5 * queue_w,
        queue_y + queue_h + 0.015,
        "Queue",
        ha="center",
        va="bottom",
        fontsize=typo.title_size - 2,
        color=style.text_color,
        weight="bold",
    )
    ax.text(
        queue_x + 0.5 * queue_w,
        queue_y + queue_h - 0.005,
        f"Q = {meta['queue_capacity']}",
        ha="center",
        va="top",
        fontsize=typo.label_size + 1,
        color=style.subtle_text_color,
    )

    # Надпись между resource bar и service panel
    ax.text(
        lanes_x + 0.5 * lanes_w,
        0.835,
        f"Service channels  |  N = {meta['servers_n']}",
        ha="center",
        va="top",
        fontsize=typo.title_size - 3,
        color=style.text_color,
        weight="bold",
    )

    # ---------------------------------
    # Вертикальная подпись K слева
    # ---------------------------------
    k_line_x = queue_x - 0.025
    k_top = queue_y + queue_h + 0.025
    k_bottom = queue_y

    ax.plot([k_line_x, k_line_x], [k_bottom, k_top], color=style.panel_edge, linewidth=1.3, zorder=2)
    ax.plot([k_line_x, queue_x], [k_top, k_top], color=style.panel_edge, linewidth=1.3, zorder=2)
    ax.plot([k_line_x, queue_x], [k_bottom, k_bottom], color=style.panel_edge, linewidth=1.3, zorder=2)

    ax.text(
        k_line_x - 0.028,
        0.5 * (k_top + k_bottom),
        f"Total system capacity K = {meta['capacity_k']}",
        ha="center",
        va="center",
        rotation=90,
        fontsize=typo.label_size + 1,
        color=style.text_color,
        weight="bold",
    )

    # ---------------------------------
    # Входная стрелка + подпись снизу
    # ---------------------------------
    arrow_y = queue_y + 0.47 * queue_h
    ax.annotate(
        "",
        xy=(queue_x, arrow_y),
        xytext=(queue_x - 0.05, arrow_y),
        arrowprops=dict(arrowstyle="->", linewidth=1.7, color=style.panel_edge),
    )
    ax.text(
        queue_x - 0.025,
        queue_y - 0.045,
        "Input flow",
        ha="center",
        va="top",
        fontsize=typo.title_size - 4,
        color=style.text_color,
        weight="bold",
    )

    # ---------------------------------
    # Глобальная полоса ресурса R
    # ---------------------------------
    rb_bg = FancyBboxPatch(
        (rb_x, rb_y),
        rb_w,
        rb_h,
        boxstyle="round,pad=0.004,rounding_size=0.01",
        facecolor=style.resource_bar_fill,
        edgecolor=style.resource_bar_edge,
        linewidth=1.4,
        zorder=2,
    )
    ax.add_patch(rb_bg)

    total_resource_r = max(float(meta["total_resource_r"]), 1.0)
    used_frac = max(0.0, min(float(resource_used) / total_resource_r, 1.0))
    rb_used = FancyBboxPatch(
        (rb_x, rb_y),
        rb_w * used_frac,
        rb_h,
        boxstyle="round,pad=0.004,rounding_size=0.01",
        facecolor=style.resource_used_fill,
        edgecolor=style.resource_used_fill,
        linewidth=0.0,
        zorder=3,
    )
    ax.add_patch(rb_used)

    ax.text(
        rb_x + 0.5 * rb_w,
        rb_y + rb_h + 0.012,
        f"Global resource bar R = {meta['total_resource_r']}",
        ha="center",
        va="bottom",
        fontsize=typo.title_size - 2,
        color=style.text_color,
        weight="bold",
    )

    rb_text = ax.text(
        rb_x + rb_w + 0.01,
        rb_y + 0.5 * rb_h,
        f"{resource_used:.1f} / {total_resource_r:.1f}",
        ha="left",
        va="center",
        fontsize=typo.label_size,
        color=style.text_color,
    )

    # ---------------------------------
    # Бокс времени
    # ---------------------------------
    tb_x = 0.73
    tb_y = 0.065
    tb_w = 0.14
    tb_h = 0.06

    time_box = FancyBboxPatch(
        (tb_x, tb_y),
        tb_w,
        tb_h,
        boxstyle="round,pad=0.004,rounding_size=0.01",
        facecolor=style.time_box_fill,
        edgecolor=style.panel_edge,
        linewidth=1.2,
        zorder=2,
    )
    ax.add_patch(time_box)

    time_text = ax.text(
        tb_x + 0.5 * tb_w,
        tb_y + 0.5 * tb_h,
        f"t = {current_time:.2f}",
        ha="center",
        va="center",
        fontsize=typo.time_text_size,
        color=style.text_color,
        weight="bold",
    )

    # ---------------------------------
    # Инфо-бокс — левее, под очередью
    # ---------------------------------
    ib_x = 0.07
    ib_y = 0.065
    ib_w = 0.34
    ib_h = 0.065

    info_box = FancyBboxPatch(
        (ib_x, ib_y),
        ib_w,
        ib_h,
        boxstyle="round,pad=0.004,rounding_size=0.01",
        facecolor=style.info_box_fill,
        edgecolor=style.panel_edge,
        linewidth=1.2,
        zorder=2,
    )
    ax.add_patch(info_box)

    info_lines = [
        f"architecture = {meta['system_architecture']}",
        f"scenario = {meta['scenario_name']}",
    ]
    ax.text(
        ib_x + 0.015,
        ib_y + 0.5 * ib_h,
        " | ".join(info_lines),
        ha="left",
        va="center",
        fontsize=typo.label_size,
        color=style.text_color,
    )

    draw_reject_zone(ax, cfg)

    return {
        "meta": meta,
        "resource_fill": rb_used,
        "resource_text": rb_text,
        "time_text": time_text,
        "resource_bar": (rb_x, rb_y, rb_w, rb_h),
        "queue_panel": queue_panel,
        "service_panel": service_panel,
        "lanes_geometry": (lanes_x, lanes_y, lanes_w, lanes_h),
        "queue_geometry": (queue_x, queue_y, queue_w, queue_h),
    }


def update_time_display(handles: dict[str, Any], current_time: float) -> None:
    """
    Обновляет надпись времени.
    """
    handles["time_text"].set_text(f"t = {current_time:.2f}")


def update_resource_display(
    handles: dict[str, Any],
    resource_used: float,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
) -> None:
    """
    Обновляет заполнение полосы ресурса и подпись справа.
    """
    meta = handles["meta"]
    rb_x, rb_y, rb_w, rb_h = handles["resource_bar"]
    total_resource_r = max(float(meta["total_resource_r"]), 1.0)
    used_frac = max(0.0, min(float(resource_used) / total_resource_r, 1.0))

    patch = handles["resource_fill"]
    patch.set_x(rb_x)
    patch.set_y(rb_y)
    patch.set_width(rb_w * used_frac)
    patch.set_height(rb_h)

    handles["resource_text"].set_text(f"{resource_used:.1f} / {total_resource_r:.1f}")


def save_scene_preview(
    output_path: str | Path | None = None,
    meta: dict[str, Any] | None = None,
    cfg: SceneConfig = DEFAULT_SCENE_CONFIG,
) -> Path:
    """
    Сохраняет preview-картинку статической сцены.
    """
    if output_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESULTS_DIR / "scene_preview.png"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = create_figure(cfg)
    draw_static_scene(ax, meta=meta, cfg=cfg, current_time=0.0, resource_used=0.0)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    preview_meta = {
        "system_architecture": "buffer",
        "servers_n": 12,
        "capacity_k": 18,
        "queue_capacity": 6,
        "total_resource_r": 96,
        "scenario_name": "preview",
    }
    out = save_scene_preview(meta=preview_meta)
    print(f"Scene preview saved to: {out}")