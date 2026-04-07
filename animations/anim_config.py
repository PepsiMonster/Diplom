from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FigureConfig:
    """Параметры итоговой matplotlib-фигуры."""
    width: float = 16.0
    height: float = 9.0
    dpi: int = 140


@dataclass(frozen=True)
class LayoutConfig:
    """
    Геометрия сцены в нормированных координатах [0, 1] x [0, 1].

    Вся сцена будет рисоваться в координатах matplotlib:
    x in [0, 1], y in [0, 1].
    """
    # Общие отступы
    left_margin: float = 0.05
    right_margin: float = 0.05
    top_margin: float = 0.08
    bottom_margin: float = 0.08

    # Левая вертикальная зона входа/очереди
    queue_left: float = 0.07
    queue_width: float = 0.14
    queue_bottom: float = 0.18
    queue_top: float = 0.82

    # Правая часть: N дорожек обслуживания
    lanes_left: float = 0.22
    lanes_right: float = 0.88
    lanes_bottom: float = 0.18
    lanes_top: float = 0.82

    # Верхняя ресурсная полоса R
    resource_bar_left: float = 0.22
    resource_bar_right: float = 0.88
    resource_bar_bottom: float = 0.86
    resource_bar_height: float = 0.045

    # Нижняя строка статуса / времени
    time_box_left: float = 0.72
    time_box_bottom: float = 0.06
    time_box_width: float = 0.16
    time_box_height: float = 0.06

    # Карточка-легенда для текущего режима
    info_box_left: float = 0.07
    info_box_bottom: float = 0.06
    info_box_width: float = 0.34
    info_box_height: float = 0.08

    # Размеры заявок
    job_height: float = 0.052
    queue_job_max_width: float = 0.11
    lane_job_max_width: float = 0.62  # реальная ширина будет масштабироваться по R

    # Отдельная зона для визуализации отказа
    reject_zone_x: float = 0.93
    reject_zone_y: float = 0.52


@dataclass(frozen=True)
class StyleConfig:
    """Цвета и стили сцены."""
    background_color: str = "#f6f4ef"
    panel_fill: str = "#ece8df"
    panel_edge: str = "#222222"
    lane_line: str = "#222222"
    queue_fill: str = "#e3ded2"

    resource_bar_fill: str = "#ddd7c8"
    resource_bar_edge: str = "#222222"
    resource_used_fill: str = "#6baed6"

    # Заявки
    accepted_job_fill: str = "#8ecae6"
    queued_job_fill: str = "#ffcc80"
    rejected_job_fill: str = "#ef9a9a"
    completed_job_fill: str = "#bde0b7"

    accepted_job_edge: str = "#1d3557"
    queued_job_edge: str = "#8d5524"
    rejected_job_edge: str = "#8b0000"
    completed_job_edge: str = "#2d6a4f"

    text_color: str = "#111111"
    subtle_text_color: str = "#444444"

    time_box_fill: str = "#ffffff"
    info_box_fill: str = "#ffffff"

    # Сетка
    show_background_grid: bool = True
    grid_color: str = "#d8d2c6"
    grid_alpha: float = 0.45


@dataclass(frozen=True)
class TypographyConfig:
    """Размеры шрифтов."""
    title_size: int = 20
    label_size: int = 13
    small_label_size: int = 11
    job_text_size: int = 11
    time_text_size: int = 14


@dataclass(frozen=True)
class AnimationConfig:
    """
    Параметры самой анимации.

    model_time_* — время в единицах модели.
    video_* — параметры ролика в секундах/кадрах.
    """
    fps: int = 30

    # Если trace длинный, на первых шагах лучше ограничиваться небольшим окном
    max_jobs_to_load: int = 80

    # Дополнительные поля вокруг диапазона времен
    head_padding_model_time: float = 0.4
    tail_padding_model_time: float = 0.8

    # Визуальная скорость объектов внутри сцены
    arrival_travel_video_sec: float = 0.55
    queue_to_lane_video_sec: float = 0.60
    reject_fade_video_sec: float = 0.90
    complete_fade_video_sec: float = 0.70

    # Насколько сглаживать движение при интерполяции
    use_easing: bool = True

    # Длина готового ролика можно либо вычислять по данным,
    # либо потом зафиксировать отдельно
    target_video_seconds: float | None = None


@dataclass(frozen=True)
class SystemFallbackConfig:
    """
    Значения по умолчанию, если trace неполный.
    Они не должны подменять реальные метаданные, только страховать код.
    """
    system_architecture: str = "buffer"
    servers_n: int = 12
    capacity_k: int = 18
    queue_capacity: int = 6
    total_resource_r: int = 96


@dataclass(frozen=True)
class SceneConfig:
    figure: FigureConfig = field(default_factory=FigureConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    style: StyleConfig = field(default_factory=StyleConfig)
    typography: TypographyConfig = field(default_factory=TypographyConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    fallback: SystemFallbackConfig = field(default_factory=SystemFallbackConfig)


DEFAULT_SCENE_CONFIG = SceneConfig()