from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter, writers

from anim_config import DEFAULT_SCENE_CONFIG, SceneConfig
from scene import (
    create_figure,
    draw_static_scene,
    draw_job_card,
    update_resource_display,
    update_time_display,
    job_draw_height,
    job_width_from_resource,
    queue_job_width_from_resource,
    queue_slot_center_y,
    lane_center_y,
)


# ======================================================================
# Пути к JSON из результатов Rust
# Раскомментирован один путь, остальные оставлены для быстрого переключения.
# ======================================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
RESULTS_DIR = BASE_DIR / "results"

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\deterministic\run_0000.json"
# )

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\exponential\run_0000.json"
# )

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\erlang_2\run_0000.json"
# )

TRACE_PATH = Path(
    r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260406_154147\full_run_results\hyperexp_heavy\run_0002.json"
)

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\erlang_4\run_0000.json"
# )

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\erlang_8\run_0000.json"
# )

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\hyperexp_2\run_0000.json"
# )

# TRACE_PATH = Path(
#     r"C:\Users\kotof\Study\Diploma\prog_files_rust\results\buffered\20260405_231623\full_run_results\hyperexp_heavy\run_0000.json"
# )


# ======================================================================
# Параметры сборки ролика
# ======================================================================

CFG: SceneConfig = DEFAULT_SCENE_CONFIG

FPS = 15
# TARGET_VIDEO_SECONDS = 60.0

# Сколько заявок максимум брать из trace для анимации
MAX_JOBS = 300

# Минимум заявок, даже если ключевые события уже встретились
MIN_JOBS = 20

# Визуальные длительности переходов в ДОЛЯХ от общего model-time окна
ARRIVAL_TRANSITION_FRAC = 0.035
QUEUE_TO_LANE_TRANSITION_FRAC = 0.035
REJECT_FADE_FRAC = 0.05
COMPLETE_FADE_FRAC = 0.04

# Минимальные визуальные длительности переходов в model time
MIN_TRANSITION_MODEL_TIME = 0.12

# Сколько пустого времени оставить до первого и после последнего события
HEAD_PAD_FRAC = 0.03
TAIL_PAD_FRAC = 0.06


# ======================================================================
# Утилиты
# ======================================================================

def smoothstep(x: float) -> float:
    """Плавная интерполяция на [0, 1]."""
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def lerp(a: float, b: float, p: float) -> float:
    """Линейная интерполяция."""
    return a + (b - a) * p


def extract_trace_payload(path: Path) -> dict[str, Any]:
    """
    Поддерживает два формата:
    1) полный run_0000.json, где нужные данные лежат в payload["animation_log"]
    2) компактный demo_trace.json, где в корне уже есть {"meta": ..., "jobs": ...}
    """
    payload = json.loads(path.read_text(encoding="utf-8"))

    if "animation_log" in payload:
        trace = payload["animation_log"]
        if "meta" in trace:
            trace["meta"]["scenario_name"] = payload.get("scenario_name", trace["meta"].get("scenario_name", "trace"))
        return trace

    if "meta" in payload and "jobs" in payload:
        return payload

    raise ValueError(
        f"Не удалось найти animation trace в файле: {path}\n"
        f"Ожидался либо run_XXXX.json с полем 'animation_log', либо компактный trace c полями 'meta'/'jobs'."
    )


def choose_interesting_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Берём компактный фрагмент trace:
    стараемся захватить принятие, очередь, завершение и отказ.
    """
    ordered = sorted(jobs, key=lambda j: (j.get("arrival_time", 0.0), j.get("job_id", 0)))

    selected: list[dict[str, Any]] = []
    saw_queue = False
    saw_reject = False
    saw_complete = False

    for job in ordered:
        selected.append(job)

        decision = job.get("decision")
        if decision == "queued":
            saw_queue = True
        if decision == "rejected":
            saw_reject = True
        if job.get("service_end_time") is not None:
            saw_complete = True

        if len(selected) >= MAX_JOBS:
            break

        if len(selected) >= MIN_JOBS and saw_queue and saw_reject and saw_complete:
            break

    return selected


def build_time_window(jobs: list[dict[str, Any]]) -> tuple[float, float]:
    """
    Вычисляем model-time окно, которое реально будем анимировать.
    """
    arrivals = [float(j["arrival_time"]) for j in jobs]
    starts = [float(j["service_start_time"]) for j in jobs if j.get("service_start_time") is not None]
    ends = [float(j["service_end_time"]) for j in jobs if j.get("service_end_time") is not None]

    t_min = min(arrivals) if arrivals else 0.0
    t_max = max(ends + starts + arrivals) if (arrivals or starts or ends) else 1.0

    span = max(t_max - t_min, 1.0)
    head_pad = HEAD_PAD_FRAC * span
    tail_pad = TAIL_PAD_FRAC * span

    return t_min - head_pad, t_max + tail_pad


def transition_times(t0: float, t1: float) -> tuple[float, float]:
    """
    Нормализует интервалы времени.
    """
    if t1 <= t0:
        return t0, t0 + 1e-9
    return t0, t1


def resource_used_at_time(t: float, jobs: list[dict[str, Any]]) -> float:
    """
    В текущей модели ресурс считается занятым с момента допуска в систему
    и до service_end. Для rejected заявок ресурс не резервируется.
    """
    total = 0.0
    for job in jobs:
        if job.get("decision") == "rejected":
            continue

        a = job.get("arrival_time")
        e = job.get("service_end_time")
        if a is None or e is None:
            continue

        if float(a) <= t < float(e):
            total += float(job.get("resource_demand", 0.0))
    return total


def queue_waiting_jobs_at_time(t: float, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Возвращает список заявок, которые на момент t находятся в очереди
    и не находятся в фазе перехода queue -> lane.
    """
    waiting = []
    for job in jobs:
        if job.get("decision") != "queued":
            continue

        q_enter = job.get("queue_enter_time")
        s_start = job.get("service_start_time")

        if q_enter is None or s_start is None:
            continue

        if float(q_enter) <= t < float(s_start):
            waiting.append(job)

    waiting.sort(key=lambda j: (j.get("queue_enter_time", 0.0), j.get("job_id", 0)))
    return waiting


def determine_output_path(trace_path: Path) -> Path:
    """
    Строим имя результата по имени распределения и файла.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    distribution_name = trace_path.parent.name
    stem = trace_path.stem
    return RESULTS_DIR / f"animation_{distribution_name}_{stem}.mp4"


# ======================================================================
# Геометрия позиций
# ======================================================================

def get_scene_positions(handles: dict[str, Any]) -> dict[str, float]:
    """
    Ключевые опорные координаты сцены.
    """
    queue_x, queue_y, queue_w, queue_h = handles["queue_geometry"]
    lanes_x, lanes_y, lanes_w, lanes_h = handles["lanes_geometry"]

    return {
        "input_x": queue_x - 0.07,
        "input_y": queue_y + 0.47 * queue_h,

        "queue_x": queue_x + 0.015,
        "queue_y": queue_y,
        "queue_w": queue_w,
        "queue_h": queue_h,

        "lane_x": lanes_x + 0.02,
        "lanes_x": lanes_x,
        "lanes_y": lanes_y,
        "lanes_w": lanes_w,
        "lanes_h": lanes_h,

        "reject_x": 0.91,
        "reject_y": 0.55,

        "complete_x": lanes_x + lanes_w + 0.02,
    }


# ======================================================================
# Рисование одного кадра
# ======================================================================

def draw_jobs_for_time(
    ax,
    handles: dict[str, Any],
    jobs: list[dict[str, Any]],
    t: float,
    t_start: float,
    t_end: float,
) -> list[Any]:
    """
    Рисует все динамические элементы на момент model-time = t.
    Возвращает список artists для последующего удаления.
    """
    artists: list[Any] = []
    pos = get_scene_positions(handles)
    meta = handles["meta"]

    span = max(t_end - t_start, 1.0)

    arrival_tau = max(ARRIVAL_TRANSITION_FRAC * span, MIN_TRANSITION_MODEL_TIME)
    queue_to_lane_tau = max(QUEUE_TO_LANE_TRANSITION_FRAC * span, MIN_TRANSITION_MODEL_TIME)
    reject_tau = max(REJECT_FADE_FRAC * span, MIN_TRANSITION_MODEL_TIME)
    complete_tau = max(COMPLETE_FADE_FRAC * span, MIN_TRANSITION_MODEL_TIME)

    # Текущая очередь (только "статически стоящие" waiting jobs)
    waiting_now = queue_waiting_jobs_at_time(t, jobs)
    queue_slot_map = {int(job["job_id"]): idx for idx, job in enumerate(waiting_now)}

    for job in jobs:
        job_id = int(job.get("job_id", -1))
        r = float(job.get("resource_demand", 0.0))
        decision = job.get("decision")
        arrival_time = float(job.get("arrival_time", 0.0))
        queue_enter_time = job.get("queue_enter_time")
        service_start_time = job.get("service_start_time")
        service_end_time = job.get("service_end_time")
        lane_id = job.get("lane_id")
        reject_reason = job.get("reject_reason")

        label = f"{int(r)}"

        # ----------------------------------------------------------
        # REJECTED
        # ----------------------------------------------------------
        if decision == "rejected":
            rej_t0 = arrival_time
            rej_t1 = arrival_time + reject_tau
            fade_t1 = rej_t1 + reject_tau

            if t < rej_t0 or t > fade_t1:
                continue

            if t <= rej_t1:
                p = smoothstep((t - rej_t0) / max(rej_t1 - rej_t0, 1e-9))
                x = lerp(pos["input_x"], pos["reject_x"], p)
                y = lerp(pos["input_y"], pos["reject_y"], p)
                alpha = 1.0
            else:
                x = pos["reject_x"]
                y = pos["reject_y"]
                alpha = max(0.0, 1.0 - (t - rej_t1) / max(fade_t1 - rej_t1, 1e-9))

            width = queue_job_width_from_resource(r, meta["total_resource_r"], CFG)
            height = 0.055

            item = draw_job_card(
                ax=ax,
                x_left=x,
                y_center=y,
                width=width,
                height=height,
                label=label,
                facecolor=CFG.style.rejected_job_fill,
                edgecolor=CFG.style.rejected_job_edge,
                cfg=CFG,
                alpha=alpha,
                zorder=7,
            )
            artists.extend([item["patch"], item["text"]])

            if alpha > 0.2 and reject_reason:
                txt = ax.text(
                    x + width * 0.5,
                    y - 0.045,
                    str(reject_reason),
                    ha="center",
                    va="top",
                    fontsize=CFG.typography.small_label_size,
                    color=CFG.style.rejected_job_edge,
                    alpha=alpha,
                    zorder=8,
                )
                artists.append(txt)

            continue

        # ----------------------------------------------------------
        # ACCEPTED IMMEDIATELY (no queue)
        # ----------------------------------------------------------
        if decision == "accepted":
            if service_end_time is None or lane_id is None:
                continue

            service_start = float(service_start_time if service_start_time is not None else arrival_time)
            service_end = float(service_end_time)
            lane_y = lane_center_y(int(lane_id), meta, CFG)

            move_t0 = arrival_time
            move_t1 = arrival_time + arrival_tau
            complete_t1 = service_end + complete_tau

            if t < move_t0 or t > complete_t1:
                continue

            width = job_width_from_resource(r, meta["total_resource_r"], CFG)
            height = job_draw_height(meta, CFG)

            if t <= move_t1:
                p = smoothstep((t - move_t0) / max(move_t1 - move_t0, 1e-9))
                x = lerp(pos["input_x"], pos["lane_x"], p)
                y = lerp(pos["input_y"], lane_y, p)
                alpha = 1.0
                fill = CFG.style.accepted_job_fill
                edge = CFG.style.accepted_job_edge
            elif t < service_end:
                x = pos["lane_x"]
                y = lane_y
                alpha = 1.0
                fill = CFG.style.accepted_job_fill
                edge = CFG.style.accepted_job_edge
            else:
                p = smoothstep((t - service_end) / max(complete_t1 - service_end, 1e-9))
                x = lerp(pos["lane_x"], pos["complete_x"], p)
                y = lane_y
                alpha = max(0.0, 1.0 - p)
                fill = CFG.style.completed_job_fill
                edge = CFG.style.completed_job_edge

            item = draw_job_card(
                ax=ax,
                x_left=x,
                y_center=y,
                width=width,
                height=height,
                label=label,
                facecolor=fill,
                edgecolor=edge,
                cfg=CFG,
                alpha=alpha,
                zorder=6,
            )
            artists.extend([item["patch"], item["text"]])
            continue

        # ----------------------------------------------------------
        # QUEUED
        # ----------------------------------------------------------
        if decision == "queued":
            if queue_enter_time is None:
                continue

            q_enter = float(queue_enter_time)
            service_start = float(service_start_time) if service_start_time is not None else None
            service_end = float(service_end_time) if service_end_time is not None else None

            queue_arrive_t0 = arrival_time
            queue_arrive_t1 = q_enter + arrival_tau

            width_q = queue_job_width_from_resource(r, meta["total_resource_r"], CFG)
            height_q = 0.052

            if service_start is None:
                # Заявка вошла в очередь и не успела начать обслуживание
                if t < queue_arrive_t0:
                    continue

                if t <= queue_arrive_t1:
                    slot_index = 0
                    target_y = queue_slot_center_y(slot_index, meta, CFG)
                    p = smoothstep((t - queue_arrive_t0) / max(queue_arrive_t1 - queue_arrive_t0, 1e-9))
                    x = lerp(pos["input_x"], pos["queue_x"], p)
                    y = lerp(pos["input_y"], target_y, p)
                else:
                    slot_index = queue_slot_map.get(job_id, 0)
                    x = pos["queue_x"]
                    y = queue_slot_center_y(slot_index, meta, CFG)

                item = draw_job_card(
                    ax=ax,
                    x_left=x,
                    y_center=y,
                    width=width_q,
                    height=height_q,
                    label=label,
                    facecolor=CFG.style.queued_job_fill,
                    edgecolor=CFG.style.queued_job_edge,
                    cfg=CFG,
                    alpha=1.0,
                    zorder=6,
                )
                artists.extend([item["patch"], item["text"]])
                continue

            # Есть и queue, и старт обслуживания
            lane_y = lane_center_y(int(lane_id), meta, CFG) if lane_id is not None else pos["input_y"]
            width_lane = job_width_from_resource(r, meta["total_resource_r"], CFG)
            height_lane = job_draw_height(meta, CFG)
            to_lane_t1 = service_start + queue_to_lane_tau
            complete_t1 = (service_end + complete_tau) if service_end is not None else (to_lane_t1 + complete_tau)

            if t < queue_arrive_t0 or t > complete_t1:
                continue

            # Фаза 1: вход в очередь
            if t <= queue_arrive_t1:
                target_y = queue_slot_center_y(0, meta, CFG)
                p = smoothstep((t - queue_arrive_t0) / max(queue_arrive_t1 - queue_arrive_t0, 1e-9))
                x = lerp(pos["input_x"], pos["queue_x"], p)
                y = lerp(pos["input_y"], target_y, p)

                item = draw_job_card(
                    ax=ax,
                    x_left=x,
                    y_center=y,
                    width=width_q,
                    height=height_q,
                    label=label,
                    facecolor=CFG.style.queued_job_fill,
                    edgecolor=CFG.style.queued_job_edge,
                    cfg=CFG,
                    alpha=1.0,
                    zorder=6,
                )
                artists.extend([item["patch"], item["text"]])
                continue

            # Фаза 2: стоит в очереди
            if t < service_start:
                slot_index = queue_slot_map.get(job_id, 0)
                x = pos["queue_x"]
                y = queue_slot_center_y(slot_index, meta, CFG)

                item = draw_job_card(
                    ax=ax,
                    x_left=x,
                    y_center=y,
                    width=width_q,
                    height=height_q,
                    label=label,
                    facecolor=CFG.style.queued_job_fill,
                    edgecolor=CFG.style.queued_job_edge,
                    cfg=CFG,
                    alpha=1.0,
                    zorder=6,
                )
                artists.extend([item["patch"], item["text"]])
                continue

            # Фаза 3: переход queue -> lane
            if t <= to_lane_t1:
                p = smoothstep((t - service_start) / max(to_lane_t1 - service_start, 1e-9))
                x = lerp(pos["queue_x"], pos["lane_x"], p)
                y = lerp(queue_slot_center_y(0, meta, CFG), lane_y, p)

                width = lerp(width_q, width_lane, p)
                height = lerp(height_q, height_lane, p)

                item = draw_job_card(
                    ax=ax,
                    x_left=x,
                    y_center=y,
                    width=width,
                    height=height,
                    label=label,
                    facecolor=CFG.style.accepted_job_fill,
                    edgecolor=CFG.style.accepted_job_edge,
                    cfg=CFG,
                    alpha=1.0,
                    zorder=7,
                )
                artists.extend([item["patch"], item["text"]])
                continue

            # Фаза 4: обслуживание
            if service_end is not None and t < service_end:
                item = draw_job_card(
                    ax=ax,
                    x_left=pos["lane_x"],
                    y_center=lane_y,
                    width=width_lane,
                    height=height_lane,
                    label=label,
                    facecolor=CFG.style.accepted_job_fill,
                    edgecolor=CFG.style.accepted_job_edge,
                    cfg=CFG,
                    alpha=1.0,
                    zorder=6,
                )
                artists.extend([item["patch"], item["text"]])
                continue

            # Фаза 5: завершение
            if service_end is not None and t <= complete_t1:
                p = smoothstep((t - service_end) / max(complete_t1 - service_end, 1e-9))
                x = lerp(pos["lane_x"], pos["complete_x"], p)
                alpha = max(0.0, 1.0 - p)

                item = draw_job_card(
                    ax=ax,
                    x_left=x,
                    y_center=lane_y,
                    width=width_lane,
                    height=height_lane,
                    label=label,
                    facecolor=CFG.style.completed_job_fill,
                    edgecolor=CFG.style.completed_job_edge,
                    cfg=CFG,
                    alpha=alpha,
                    zorder=6,
                )
                artists.extend([item["patch"], item["text"]])
                continue

    return artists


# ======================================================================
# Сборка анимации
# ======================================================================

def make_animation(trace_path: Path = TRACE_PATH) -> Path:
    trace = extract_trace_payload(trace_path)
    meta = trace.get("meta", {})
    all_jobs = trace.get("jobs", [])

    if not all_jobs:
        raise ValueError(f"В trace нет jobs: {trace_path}")

    jobs = choose_interesting_jobs(all_jobs)
    t_start, t_end = build_time_window(jobs)
    video_duration = t_end - t_start

    total_frames = max(2, int(round(FPS * video_duration)))
    output_mp4 = determine_output_path(trace_path)
    output_gif = output_mp4.with_suffix(".gif")

    fig, ax = create_figure(CFG)
    handles = draw_static_scene(ax, meta=meta, cfg=CFG, current_time=t_start, resource_used=0.0)

    dynamic_artists: list[Any] = []

    def model_time_from_frame(frame_idx: int) -> float:
        if total_frames <= 1:
            return t_start
        p = frame_idx / (total_frames - 1)
        return lerp(t_start, t_end, p)

    def update(frame_idx: int):
        nonlocal dynamic_artists

        # Удаляем динамические artists предыдущего кадра
        for artist in dynamic_artists:
            try:
                artist.remove()
            except Exception:
                pass
        dynamic_artists = []

        t = model_time_from_frame(frame_idx)

        # Обновляем статусные элементы
        resource_now = resource_used_at_time(t, jobs)
        update_time_display(handles, t)
        update_resource_display(handles, resource_now, CFG)

        # Рисуем заявки
        dynamic_artists = draw_jobs_for_time(ax, handles, jobs, t, t_start, t_end)

        # Возвращаем artists для blit=False — не критично, но оставим
        return dynamic_artists + [
            handles["time_text"],
            handles["resource_text"],
            handles["resource_fill"],
        ]

    anim = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=1000 / FPS,
        blit=False,
        repeat=True,
    )

    # Предпочитаем mp4, потому что он обычно легче gif
    if writers.is_available("ffmpeg"):
        writer = FFMpegWriter(fps=FPS, bitrate=1800)
        anim.save(str(output_mp4), writer=writer)
        plt.close(fig)
        return output_mp4

    # Fallback на gif
    writer = PillowWriter(fps=FPS)
    anim.save(str(output_gif), writer=writer)
    plt.close(fig)
    return output_gif


if __name__ == "__main__":
    out = make_animation(TRACE_PATH)
    print(f"Animation saved to: {out}")