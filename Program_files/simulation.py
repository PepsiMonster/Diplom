<<<<<<< HEAD
from __future__ import annotations

from dataclasses import dataclass, field, replace

from math import inf, isclose

=======
# DES или другой механизм расчёта.

"""
simulation.py
=============

DES-движок (Discrete Event Simulation) для системы массового обслуживания
с ограниченными ресурсами и state-dependent характеристиками.

Роль файла
----------
Если params.py отвечает за параметры модели, а model.py — за предметную
логику состояния системы, то этот модуль отвечает за "динамику":

1. генерацию случайных событий;
2. выбор ближайшего события;
3. продвижение модельного времени;
4. накопление статистики;
5. возврат результатов одного прогона в стандартизованной форме.

Что именно моделируется
-----------------------
Рассматривается loss-система без очереди ожидания:

- заявки поступают с интенсивностью lambda_k, зависящей от текущего числа
  заявок в системе k;
- каждая заявка требует:
    * некоторое количество ресурса;
    * некоторый объём работы;
- в системе есть:
    * ограничение по общей ёмкости K;
    * ограничение по числу приборов N;
    * ограничение по суммарному ресурсу R;
- если новая заявка не помещается, она теряется;
- скорость уменьшения остатка работы зависит от состояния:
    sigma_k = service_speed_by_state[k].

Ключевая модельная идея
-----------------------
Мы не моделируем "готовую дату окончания обслуживания" как фиксированную
величину в момент поступления. Вместо этого у каждой заявки хранится
remaining_workload, а при движении времени остаток работы убывает.

Это критически важно при state-dependent sigma_k:
если число заявок в системе меняется, меняется и скорость убывания
остатков работ.

Что накапливает симуляция
-------------------------
В этой версии собираются:

- оценка стационарного распределения по числу заявок: pi_hat(k);
- среднее число заявок в системе;
- средний занятый ресурс;
- вероятность отказа;
- число отказов по каждой причине;
- эффективная пропускная способность;
- число завершившихся заявок;
- опционально:
    * state trace;
    * event log.

Можно ли запускать этот файл отдельно?
--------------------------------------
Да.

Если запустить:
    python simulation.py

то модуль:
- построит один базовый сценарий;
- выполнит один прогон симуляции;
- распечатает сводные результаты;
- при включённой трассировке покажет несколько первых событий.

Это позволяет отладить DES-движок ещё до написания experiments.py и plots.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import inf, isclose
>>>>>>> main
from typing import Optional

import numpy as np

from params import (
<<<<<<< HEAD

    ResourceDistributionConfig,

    ScenarioConfig,

    SimulationConfig,

    WorkloadDistributionConfig,

    build_base_scenario,

    standard_workload_family,

)

from model import (

    AdmissionDecision,

    Job,

    RejectionReason,

    SystemState,

)

@dataclass(slots=True)

class StateSnapshot:

    time: float

    num_jobs: int

    occupied_resource: int

    arrival_rate: float

    service_speed: float

@dataclass(slots=True)

class EventRecord:

    time: float

    event_type: str

    job_id: Optional[int]

    num_jobs_before: int

    num_jobs_after: int

    occupied_resource_before: int

    occupied_resource_after: int

    details: str = ""

@dataclass(slots=True)

class SimulationRunResult:

    scenario_name: str

    replication_index: int

    seed: int

    total_time: float

    warmup_time: float

    observed_time: float

    state_times: tuple[float, ...]

    pi_hat: tuple[float, ...]

    mean_num_jobs: float

    mean_occupied_resource: float

    arrival_attempts: int

    accepted_arrivals: int

    rejected_arrivals: int

    rejected_capacity: int

    rejected_server: int

=======
    ResourceDistributionConfig,
    ScenarioConfig,
    SimulationConfig,
    WorkloadDistributionConfig,
    build_base_scenario,
    standard_workload_family,
)
from model import (
    AdmissionDecision,
    Job,
    RejectionReason,
    SystemState,
)


# ============================================================================
# СЛУЖЕБНЫЕ СТРУКТУРЫ ДАННЫХ ДЛЯ ЛОГА И ТРАЕКТОРИИ
# ============================================================================
# Эти dataclass'ы не нужны для "голой" симуляции, но полезны для:
# - ручной отладки;
# - демонстрации хода событий;
# - последующего сохранения состояния и событий в файл.
# ============================================================================


@dataclass(slots=True)
class StateSnapshot:
    """
    Снимок состояния системы в конкретный момент времени.

    Поля:
    -----
    time:
        Момент времени, к которому относится снимок.

    num_jobs:
        Число заявок в системе.

    occupied_resource:
        Суммарный занятый ресурс в этот момент.

    arrival_rate:
        Текущая интенсивность поступления lambda_k.

    service_speed:
        Текущая скорость обслуживания sigma_k.
    """

    time: float
    num_jobs: int
    occupied_resource: int
    arrival_rate: float
    service_speed: float


@dataclass(slots=True)
class EventRecord:
    """
    Лог отдельного события.

    Поля:
    -----
    time:
        Момент события.

    event_type:
        Тип события:
        - "arrival_accepted"
        - "arrival_rejected"
        - "departure"

    job_id:
        Идентификатор заявки, если применимо.

    num_jobs_before / num_jobs_after:
        Число заявок в системе до и после события.

    occupied_resource_before / occupied_resource_after:
        Занятый ресурс до и после события.

    details:
        Свободное текстовое поле. Удобно для отладки и пояснений.
    """

    time: float
    event_type: str
    job_id: Optional[int]
    num_jobs_before: int
    num_jobs_after: int
    occupied_resource_before: int
    occupied_resource_after: int
    details: str = ""


# ============================================================================
# ИТОГ ОДНОГО ПРОГОНА
# ============================================================================
# Результат одного прогона должен быть:
# - достаточно полным;
# - пригодным для последующей сериализации;
# - пригодным для перевода в CSV-таблицу;
# - пригодным для построения графиков.
# ============================================================================


@dataclass(slots=True)
class SimulationRunResult:
    """
    Итог одного прогона имитации.

    Это объект уровня "одна траектория / один replication".

    Поля:
    -----
    scenario_name:
        Имя сценария.

    replication_index:
        Номер повтора.

    seed:
        Seed, использованный именно в этом прогоне.

    total_time:
        Полная длина траектории.

    warmup_time:
        Длина разгона.

    observed_time:
        Длина участка траектории, на котором собиралась статистика.

    state_times:
        Время, проведённое системой в состояниях k = 0, ..., K
        на наблюдаемом интервале.

    pi_hat:
        Оценка стационарного распределения по состояниям.

    mean_num_jobs:
        Оценка среднего числа заявок в системе.

    mean_occupied_resource:
        Оценка среднего занятого ресурса.

    arrival_attempts:
        Число попыток поступления на наблюдаемом интервале.

    accepted_arrivals:
        Число принятых заявок.

    rejected_arrivals:
        Число потерянных заявок.

    rejected_capacity / rejected_server / rejected_resource:
        Детализация причин отказа.

    completed_jobs:
        Число завершённых заявок на наблюдаемом интервале.

    loss_probability:
        Оценка вероятности отказа.

    throughput:
        Эффективная пропускная способность.

    state_trace / event_log:
        Опциональные диагностические данные.
    """

    scenario_name: str
    replication_index: int
    seed: int

    total_time: float
    warmup_time: float
    observed_time: float

    state_times: tuple[float, ...]
    pi_hat: tuple[float, ...]

    mean_num_jobs: float
    mean_occupied_resource: float

    arrival_attempts: int
    accepted_arrivals: int
    rejected_arrivals: int

    rejected_capacity: int
    rejected_server: int
>>>>>>> main
    rejected_resource: int

    completed_jobs: int

    loss_probability: float
<<<<<<< HEAD

    throughput: float

    state_trace: tuple[StateSnapshot, ...] = ()

    event_log: tuple[EventRecord, ...] = ()

    def flat_summary(self) -> dict[str, float | int | str]:

        summary: dict[str, float | int | str] = {

            "scenario_name": self.scenario_name,

            "replication_index": self.replication_index,

            "seed": self.seed,

            "total_time": self.total_time,

            "warmup_time": self.warmup_time,

            "observed_time": self.observed_time,

            "mean_num_jobs": self.mean_num_jobs,

            "mean_occupied_resource": self.mean_occupied_resource,

            "arrival_attempts": self.arrival_attempts,

            "accepted_arrivals": self.accepted_arrivals,

            "rejected_arrivals": self.rejected_arrivals,

            "rejected_capacity": self.rejected_capacity,

            "rejected_server": self.rejected_server,

            "rejected_resource": self.rejected_resource,

            "completed_jobs": self.completed_jobs,

            "loss_probability": self.loss_probability,

            "throughput": self.throughput,

        }

        for k, value in enumerate(self.pi_hat):

=======
    throughput: float

    state_trace: tuple[StateSnapshot, ...] = ()
    event_log: tuple[EventRecord, ...] = ()

    def flat_summary(self) -> dict[str, float | int | str]:
        """
        Возвращает "плоский" словарь с агрегированными метриками.

        Такой формат удобно будет позже:
        - сохранять в CSV;
        - переводить в pandas.DataFrame;
        - скармливать plotting-слою.
        """
        summary: dict[str, float | int | str] = {
            "scenario_name": self.scenario_name,
            "replication_index": self.replication_index,
            "seed": self.seed,
            "total_time": self.total_time,
            "warmup_time": self.warmup_time,
            "observed_time": self.observed_time,
            "mean_num_jobs": self.mean_num_jobs,
            "mean_occupied_resource": self.mean_occupied_resource,
            "arrival_attempts": self.arrival_attempts,
            "accepted_arrivals": self.accepted_arrivals,
            "rejected_arrivals": self.rejected_arrivals,
            "rejected_capacity": self.rejected_capacity,
            "rejected_server": self.rejected_server,
            "rejected_resource": self.rejected_resource,
            "completed_jobs": self.completed_jobs,
            "loss_probability": self.loss_probability,
            "throughput": self.throughput,
        }

        # Добавляем pi_hat(k) в плоский словарь.
        for k, value in enumerate(self.pi_hat):
>>>>>>> main
            summary[f"pi_hat_{k}"] = value

        return summary

<<<<<<< HEAD
def _derive_run_seed(base_seed: int, replication_index: int) -> int:

    if replication_index < 0:

=======

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ЧИСЛЕННЫЕ ФУНКЦИИ
# ============================================================================


def _derive_run_seed(base_seed: int, replication_index: int) -> int:
    """
    Детерминированно строит seed отдельного прогона из базового seed.

    Почему это полезно:
    -------------------
    - один и тот же replication_index всегда даёт один и тот же seed;
    - можно воспроизводить отдельные прогоны;
    - можно делать серию независимых повторов без ручного управления seed.

    Формула простая и намеренно прозрачная.
    """
    if replication_index < 0:
>>>>>>> main
        raise ValueError(f"replication_index должен быть >= 0, получено: {replication_index}")

    return int(base_seed + 1_000_003 * replication_index)

<<<<<<< HEAD
def _interval_overlap_length(a0: float, a1: float, b0: float, b1: float) -> float:

    left = max(a0, b0)

    right = min(a1, b1)

    return max(0.0, right - left)

def sample_resource_demand(

    rng: np.random.Generator,

    config: ResourceDistributionConfig,

) -> int:

    config.validate()

    if config.kind == "deterministic":

        assert config.deterministic_value is not None

        return int(config.deterministic_value)

    if config.kind == "discrete_uniform":

        assert config.min_units is not None

        assert config.max_units is not None

        return int(rng.integers(config.min_units, config.max_units + 1))

    assert config.values

    assert config.probabilities

    return int(rng.choice(config.values, p=config.probabilities))

def sample_workload(

    rng: np.random.Generator,

    config: WorkloadDistributionConfig,

) -> float:

    config.validate()

    if config.kind == "deterministic":

        return float(config.mean)

    if config.kind == "exponential":

        return float(rng.exponential(scale=config.mean))

    if config.kind == "erlang":

        assert config.erlang_order is not None

        return float(rng.gamma(shape=config.erlang_order, scale=config.mean / config.erlang_order))

    if config.kind == "hyperexponential2":

        assert config.hyper_p is not None

        assert config.hyper_rates is not None

        rate_1, rate_2 = config.hyper_rates

        branch = rng.random() < config.hyper_p

        if branch:

            return float(rng.exponential(scale=1.0 / rate_1))

=======

def _interval_overlap_length(a0: float, a1: float, b0: float, b1: float) -> float:
    """
    Возвращает длину пересечения интервалов [a0, a1] и [b0, b1].

    Используется для корректного накопления статистики только на участке
    наблюдения [warmup_time, max_time].

    Важно:
    -------
    Состояние системы на интервале между событиями постоянно. Поэтому для
    time-average статистик нужно аккуратно учитывать только ту часть
    интервала, которая лежит в окне наблюдения.
    """
    left = max(a0, b0)
    right = min(a1, b1)
    return max(0.0, right - left)


# ============================================================================
# ГЕНЕРАЦИЯ СЛУЧАЙНЫХ ВЕЛИЧИН
# ============================================================================
# Вся случайность проекта должна проходить через единый RNG объекта
# numpy.random.Generator. Это критично для воспроизводимости.
# ============================================================================


def sample_resource_demand(
    rng: np.random.Generator,
    config: ResourceDistributionConfig,
) -> int:
    """
    Генерирует случайное требование к ресурсу согласно ResourceDistributionConfig.
    """
    config.validate()

    if config.kind == "deterministic":
        assert config.deterministic_value is not None
        return int(config.deterministic_value)

    if config.kind == "discrete_uniform":
        assert config.min_units is not None
        assert config.max_units is not None
        # integers(low, high) генерирует числа из [low, high),
        # поэтому верхнюю границу увеличиваем на 1.
        return int(rng.integers(config.min_units, config.max_units + 1))

    # discrete_custom
    assert config.values
    assert config.probabilities
    return int(rng.choice(config.values, p=config.probabilities))


def sample_workload(
    rng: np.random.Generator,
    config: WorkloadDistributionConfig,
) -> float:
    """
    Генерирует объём работы заявки согласно WorkloadDistributionConfig.

    Интерпретация:
    --------------
    Это не "готовое время обслуживания", а именно объём работы.
    Потом в системе этот объём будет уменьшаться со скоростью sigma_k.
    """
    config.validate()

    if config.kind == "deterministic":
        return float(config.mean)

    if config.kind == "exponential":
        # У numpy.exponential параметр — scale = 1 / rate = mean.
        return float(rng.exponential(scale=config.mean))

    if config.kind == "erlang":
        assert config.erlang_order is not None
        # Erlang(p) — это Gamma(shape=p, scale=mean/p).
        return float(rng.gamma(shape=config.erlang_order, scale=config.mean / config.erlang_order))

    if config.kind == "hyperexponential2":
        assert config.hyper_p is not None
        assert config.hyper_rates is not None
        rate_1, rate_2 = config.hyper_rates

        branch = rng.random() < config.hyper_p
        if branch:
            return float(rng.exponential(scale=1.0 / rate_1))
>>>>>>> main
        return float(rng.exponential(scale=1.0 / rate_2))

    raise ValueError(f"Неподдерживаемый kind='{config.kind}' для workload distribution")

<<<<<<< HEAD
def sample_next_arrival_delta(

    rng: np.random.Generator,

    state: SystemState,

    scenario: ScenarioConfig,

) -> float:

    current_rate = state.current_arrival_rate(scenario)

    if current_rate <= 0.0:

        return inf

    return float(rng.exponential(scale=1.0 / current_rate))

@dataclass(slots=True)

class StatisticsAccumulator:

    capacity_k: int

    total_time: float

    warmup_time: float

    state_times: list[float] = field(default_factory=list)

    resource_time_integral: float = 0.0

    arrival_attempts: int = 0

    accepted_arrivals: int = 0

    rejected_arrivals: int = 0

    rejected_capacity: int = 0

    rejected_server: int = 0

=======

def sample_next_arrival_delta(
    rng: np.random.Generator,
    state: SystemState,
    scenario: ScenarioConfig,
) -> float:
    """
    Генерирует время до следующего поступления в текущем состоянии системы.

    Если текущая интенсивность равна нулю, возвращаем +inf.
    """
    current_rate = state.current_arrival_rate(scenario)
    if current_rate <= 0.0:
        return inf
    return float(rng.exponential(scale=1.0 / current_rate))


# ============================================================================
# АККУМУЛЯТОР СТАТИСТИКИ
# ============================================================================
# Эта структура собирает всё, что относится к статистике прогона.
# Она нарочно отделена от SystemState:
# state отвечает за "что происходит сейчас",
# accumulator отвечает за "что мы измерили на траектории".
# ============================================================================


@dataclass(slots=True)
class StatisticsAccumulator:
    """
    Накопитель статистики одного прогона.

    Здесь собираются:
    - time-average характеристики;
    - event-count характеристики;
    - по необходимости — trace и event log.
    """

    capacity_k: int
    total_time: float
    warmup_time: float

    state_times: list[float] = field(default_factory=list)
    resource_time_integral: float = 0.0

    arrival_attempts: int = 0
    accepted_arrivals: int = 0
    rejected_arrivals: int = 0

    rejected_capacity: int = 0
    rejected_server: int = 0
>>>>>>> main
    rejected_resource: int = 0

    completed_jobs: int = 0

    def __post_init__(self) -> None:
<<<<<<< HEAD

        if self.capacity_k <= 0:

            raise ValueError(f"capacity_k должен быть > 0, получено: {self.capacity_k}")

        if self.total_time <= 0:

            raise ValueError(f"total_time должен быть > 0, получено: {self.total_time}")

        if self.warmup_time < 0:

=======
        """
        Инициализирует массив времён по состояниям длины K+1.
        """
        if self.capacity_k <= 0:
            raise ValueError(f"capacity_k должен быть > 0, получено: {self.capacity_k}")

        if self.total_time <= 0:
            raise ValueError(f"total_time должен быть > 0, получено: {self.total_time}")

        if self.warmup_time < 0:
>>>>>>> main
            raise ValueError(f"warmup_time должен быть >= 0, получено: {self.warmup_time}")

        self.state_times = [0.0 for _ in range(self.capacity_k + 1)]

    @property
<<<<<<< HEAD

    def observed_time(self) -> float:

        return self.total_time - self.warmup_time

    def is_in_observation_window(self, time_point: float) -> bool:

        return self.warmup_time <= time_point <= self.total_time

    def observe_constant_interval(

        self,

        *,

        t0: float,

        t1: float,

        num_jobs: int,

        occupied_resource: int,

    ) -> None:

        if t1 < t0:

            raise ValueError(f"Ожидалось t1 >= t0, получено t0={t0}, t1={t1}")

        if t1 == t0:

            return

        overlap = _interval_overlap_length(t0, t1, self.warmup_time, self.total_time)

        if overlap <= 0.0:

            return

        self.state_times[num_jobs] += overlap

        self.resource_time_integral += occupied_resource * overlap

    def register_arrival_attempt(self, event_time: float) -> None:

        if self.is_in_observation_window(event_time):

            self.arrival_attempts += 1

    def register_admission(self, event_time: float) -> None:

        if self.is_in_observation_window(event_time):

            self.accepted_arrivals += 1

    def register_rejection(self, event_time: float, reason: RejectionReason) -> None:

        if not self.is_in_observation_window(event_time):

=======
    def observed_time(self) -> float:
        """
        Возвращает длину интервала наблюдения.
        """
        return self.total_time - self.warmup_time

    def is_in_observation_window(self, time_point: float) -> bool:
        """
        Проверяет, лежит ли момент времени внутри окна наблюдения.

        Событие, произошедшее в момент t = warmup_time, считаем уже
        принадлежащим окну наблюдения.
        """
        return self.warmup_time <= time_point <= self.total_time

    def observe_constant_interval(
        self,
        *,
        t0: float,
        t1: float,
        num_jobs: int,
        occupied_resource: int,
    ) -> None:
        """
        Добавляет вклад интервала [t0, t1] в time-average статистики.

        Предпосылка:
        -----------
        На интервале между двумя соседними событиями состояние системы
        постоянно. Значит:
        - число заявок постоянно;
        - занятый ресурс постоянен.

        Тогда стационарное распределение и средние характеристики можно
        оценивать через интегралы по времени.
        """
        if t1 < t0:
            raise ValueError(f"Ожидалось t1 >= t0, получено t0={t0}, t1={t1}")

        if t1 == t0:
            return

        overlap = _interval_overlap_length(t0, t1, self.warmup_time, self.total_time)
        if overlap <= 0.0:
            return

        self.state_times[num_jobs] += overlap
        self.resource_time_integral += occupied_resource * overlap

    def register_arrival_attempt(self, event_time: float) -> None:
        """
        Регистрирует попытку поступления заявки.

        Считаем только события, попавшие в окно наблюдения.
        """
        if self.is_in_observation_window(event_time):
            self.arrival_attempts += 1

    def register_admission(self, event_time: float) -> None:
        """
        Регистрирует успешный приём заявки.
        """
        if self.is_in_observation_window(event_time):
            self.accepted_arrivals += 1

    def register_rejection(self, event_time: float, reason: RejectionReason) -> None:
        """
        Регистрирует отказ и его причину.
        """
        if not self.is_in_observation_window(event_time):
>>>>>>> main
            return

        self.rejected_arrivals += 1

        if reason == RejectionReason.CAPACITY_LIMIT:
<<<<<<< HEAD

            self.rejected_capacity += 1

        elif reason == RejectionReason.SERVER_LIMIT:

            self.rejected_server += 1

        elif reason == RejectionReason.RESOURCE_LIMIT:

            self.rejected_resource += 1

    def register_departure(self, event_time: float) -> None:

        if self.is_in_observation_window(event_time):

            self.completed_jobs += 1

    def build_result(

        self,

        *,

        scenario_name: str,

        replication_index: int,

        seed: int,

        state_trace: list[StateSnapshot],

        event_log: list[EventRecord],

    ) -> SimulationRunResult:

        observed_time = self.observed_time

        if observed_time <= 0:

            raise ValueError(

                f"observed_time должно быть > 0, получено: {observed_time}. "

                "Проверь max_time и warmup_time."

            )

        pi_hat = tuple(time_in_state / observed_time for time_in_state in self.state_times)

        mean_num_jobs = sum(k * pi_hat[k] for k in range(len(pi_hat)))

        mean_occupied_resource = self.resource_time_integral / observed_time

        if self.arrival_attempts > 0:

            loss_probability = self.rejected_arrivals / self.arrival_attempts

        else:

=======
            self.rejected_capacity += 1
        elif reason == RejectionReason.SERVER_LIMIT:
            self.rejected_server += 1
        elif reason == RejectionReason.RESOURCE_LIMIT:
            self.rejected_resource += 1

    def register_departure(self, event_time: float) -> None:
        """
        Регистрирует завершение обслуживания заявки.
        """
        if self.is_in_observation_window(event_time):
            self.completed_jobs += 1

    def build_result(
        self,
        *,
        scenario_name: str,
        replication_index: int,
        seed: int,
        state_trace: list[StateSnapshot],
        event_log: list[EventRecord],
    ) -> SimulationRunResult:
        """
        Преобразует накопленные статистики в итоговый объект результата.
        """
        observed_time = self.observed_time
        if observed_time <= 0:
            raise ValueError(
                f"observed_time должно быть > 0, получено: {observed_time}. "
                "Проверь max_time и warmup_time."
            )

        pi_hat = tuple(time_in_state / observed_time for time_in_state in self.state_times)
        mean_num_jobs = sum(k * pi_hat[k] for k in range(len(pi_hat)))
        mean_occupied_resource = self.resource_time_integral / observed_time

        if self.arrival_attempts > 0:
            loss_probability = self.rejected_arrivals / self.arrival_attempts
        else:
>>>>>>> main
            loss_probability = 0.0

        throughput = self.completed_jobs / observed_time

        return SimulationRunResult(
<<<<<<< HEAD

            scenario_name=scenario_name,

            replication_index=replication_index,

            seed=seed,

            total_time=self.total_time,

            warmup_time=self.warmup_time,

            observed_time=observed_time,

            state_times=tuple(self.state_times),

            pi_hat=pi_hat,

            mean_num_jobs=mean_num_jobs,

            mean_occupied_resource=mean_occupied_resource,

            arrival_attempts=self.arrival_attempts,

            accepted_arrivals=self.accepted_arrivals,

            rejected_arrivals=self.rejected_arrivals,

            rejected_capacity=self.rejected_capacity,

            rejected_server=self.rejected_server,

            rejected_resource=self.rejected_resource,

            completed_jobs=self.completed_jobs,

            loss_probability=loss_probability,

            throughput=throughput,

            state_trace=tuple(state_trace),

            event_log=tuple(event_log),

        )

class SingleRunSimulator:

    def __init__(

        self,

        scenario: ScenarioConfig,

        replication_index: int = 0,

        seed: Optional[int] = None,

    ) -> None:

        scenario.validate()

        self.scenario = scenario

        self.replication_index = replication_index

        self.seed = _derive_run_seed(scenario.simulation.seed, replication_index) if seed is None else int(seed)

        self.rng = np.random.default_rng(self.seed)

        self.state = SystemState()

        self.stats = StatisticsAccumulator(

            capacity_k=scenario.capacity_k,

            total_time=scenario.simulation.max_time,

            warmup_time=scenario.simulation.warmup_time,

        )

        self.state_trace: list[StateSnapshot] = []

        self.event_log: list[EventRecord] = []

        self._record_state_snapshot()

    def _record_state_snapshot(self) -> None:

        if not self.scenario.simulation.record_state_trace:

            return

        snapshot = StateSnapshot(

            time=self.state.current_time,

            num_jobs=self.state.num_jobs,

            occupied_resource=self.state.occupied_resource,

            arrival_rate=self.state.current_arrival_rate(self.scenario),

            service_speed=self.state.current_service_speed(self.scenario),

        )

        self.state_trace.append(snapshot)

    def _record_event(

        self,

        *,

        event_type: str,

        job_id: Optional[int],

        num_jobs_before: int,

        num_jobs_after: int,

        occupied_resource_before: int,

        occupied_resource_after: int,

        details: str = "",

    ) -> None:

        if not self.scenario.simulation.save_event_log:

            return

        record = EventRecord(

            time=self.state.current_time,

            event_type=event_type,

            job_id=job_id,

            num_jobs_before=num_jobs_before,

            num_jobs_after=num_jobs_after,

            occupied_resource_before=occupied_resource_before,

            occupied_resource_after=occupied_resource_after,

            details=details,

        )

        self.event_log.append(record)

    def _sample_new_job_parameters(self) -> tuple[int, float]:

        resource_demand = sample_resource_demand(self.rng, self.scenario.resource_distribution)

        workload = sample_workload(self.rng, self.scenario.workload_distribution)

        return resource_demand, workload

    def _process_arrival(self) -> None:

        num_jobs_before = self.state.num_jobs

=======
            scenario_name=scenario_name,
            replication_index=replication_index,
            seed=seed,
            total_time=self.total_time,
            warmup_time=self.warmup_time,
            observed_time=observed_time,
            state_times=tuple(self.state_times),
            pi_hat=pi_hat,
            mean_num_jobs=mean_num_jobs,
            mean_occupied_resource=mean_occupied_resource,
            arrival_attempts=self.arrival_attempts,
            accepted_arrivals=self.accepted_arrivals,
            rejected_arrivals=self.rejected_arrivals,
            rejected_capacity=self.rejected_capacity,
            rejected_server=self.rejected_server,
            rejected_resource=self.rejected_resource,
            completed_jobs=self.completed_jobs,
            loss_probability=loss_probability,
            throughput=throughput,
            state_trace=tuple(state_trace),
            event_log=tuple(event_log),
        )


# ============================================================================
# ОСНОВНОЙ DES-СИМУЛЯТОР ОДНОГО ПРОГОНА
# ============================================================================
# Это ядро модуля.
# Здесь реализуется:
# - выбор ближайшего события;
# - продвижение системы;
# - обработка arrivals и departures;
# - накопление статистики.
# ============================================================================


class SingleRunSimulator:
    """
    DES-симулятор одного прогона.

    Один объект = один сценарий + один replication + один seed.
    """

    def __init__(
        self,
        scenario: ScenarioConfig,
        replication_index: int = 0,
        seed: Optional[int] = None,
    ) -> None:
        """
        Инициализирует симулятор.

        Если seed не задан явно, он детерминированно строится из:
        - базового seed сценария;
        - replication_index.
        """
        scenario.validate()

        self.scenario = scenario
        self.replication_index = replication_index
        self.seed = _derive_run_seed(scenario.simulation.seed, replication_index) if seed is None else int(seed)

        self.rng = np.random.default_rng(self.seed)
        self.state = SystemState()

        self.stats = StatisticsAccumulator(
            capacity_k=scenario.capacity_k,
            total_time=scenario.simulation.max_time,
            warmup_time=scenario.simulation.warmup_time,
        )

        self.state_trace: list[StateSnapshot] = []
        self.event_log: list[EventRecord] = []

        # Фиксируем начальное состояние, если включена трассировка.
        self._record_state_snapshot()

    # ----------------------------------------------------------------------
    # СЛУЖЕБНЫЕ МЕТОДЫ ЛОГИРОВАНИЯ
    # ----------------------------------------------------------------------

    def _record_state_snapshot(self) -> None:
        """
        При необходимости добавляет снимок текущего состояния в state_trace.
        """
        if not self.scenario.simulation.record_state_trace:
            return

        snapshot = StateSnapshot(
            time=self.state.current_time,
            num_jobs=self.state.num_jobs,
            occupied_resource=self.state.occupied_resource,
            arrival_rate=self.state.current_arrival_rate(self.scenario),
            service_speed=self.state.current_service_speed(self.scenario),
        )
        self.state_trace.append(snapshot)

    def _record_event(
        self,
        *,
        event_type: str,
        job_id: Optional[int],
        num_jobs_before: int,
        num_jobs_after: int,
        occupied_resource_before: int,
        occupied_resource_after: int,
        details: str = "",
    ) -> None:
        """
        При необходимости добавляет запись о событии в event_log.
        """
        if not self.scenario.simulation.save_event_log:
            return

        record = EventRecord(
            time=self.state.current_time,
            event_type=event_type,
            job_id=job_id,
            num_jobs_before=num_jobs_before,
            num_jobs_after=num_jobs_after,
            occupied_resource_before=occupied_resource_before,
            occupied_resource_after=occupied_resource_after,
            details=details,
        )
        self.event_log.append(record)

    # ----------------------------------------------------------------------
    # ГЕНЕРАЦИЯ ПАРАМЕТРОВ НОВОЙ ЗАЯВКИ
    # ----------------------------------------------------------------------

    def _sample_new_job_parameters(self) -> tuple[int, float]:
        """
        Генерирует параметры новой заявки:
        - ресурсное требование;
        - объём работы.
        """
        resource_demand = sample_resource_demand(self.rng, self.scenario.resource_distribution)
        workload = sample_workload(self.rng, self.scenario.workload_distribution)
        return resource_demand, workload

    # ----------------------------------------------------------------------
    # ОБРАБОТКА СОБЫТИЙ
    # ----------------------------------------------------------------------

    def _process_arrival(self) -> None:
        """
        Обрабатывает событие поступления заявки.

        Логика:
        -------
        1. Генерируем параметры новой заявки.
        2. Увеличиваем счётчик попыток поступления.
        3. Проверяем возможность допуска.
        4. Если можно — создаём и добавляем заявку.
        5. Если нельзя — фиксируем отказ и его причину.

        Важно:
        -------
        create_job вызывается только после положительного решения о допуске.
        Это сделано намеренно, чтобы:
        - не "сжигать" job_id на потерянные заявки;
        - лог заявок оставался чистым.
        """
        num_jobs_before = self.state.num_jobs
>>>>>>> main
        occupied_resource_before = self.state.occupied_resource

        resource_demand, workload = self._sample_new_job_parameters()

        self.stats.register_arrival_attempt(self.state.current_time)

        decision: AdmissionDecision = self.state.can_accept(resource_demand, self.scenario)

        if decision.accepted:
<<<<<<< HEAD

            job = self.state.create_job(

                resource_demand=resource_demand,

                workload=workload,

                arrival_time=self.state.current_time,

            )

            self.state.add_job(job, self.scenario)

            self.stats.register_admission(self.state.current_time)

            self._record_event(

                event_type="arrival_accepted",

                job_id=job.job_id,

                num_jobs_before=num_jobs_before,

                num_jobs_after=self.state.num_jobs,

                occupied_resource_before=occupied_resource_before,

                occupied_resource_after=self.state.occupied_resource,

                details=(

                    f"resource_demand={resource_demand}, "

                    f"workload={workload:.6f}"

                ),

            )

        else:

            self.stats.register_rejection(self.state.current_time, decision.reason)

            self._record_event(

                event_type="arrival_rejected",

                job_id=None,

                num_jobs_before=num_jobs_before,

                num_jobs_after=self.state.num_jobs,

                occupied_resource_before=occupied_resource_before,

                occupied_resource_after=self.state.occupied_resource,

                details=(

                    f"reason={decision.reason.value}, "

                    f"resource_demand={resource_demand}, "

                    f"workload={workload:.6f}"

                ),

=======
            job = self.state.create_job(
                resource_demand=resource_demand,
                workload=workload,
                arrival_time=self.state.current_time,
            )
            self.state.add_job(job, self.scenario)
            self.stats.register_admission(self.state.current_time)

            self._record_event(
                event_type="arrival_accepted",
                job_id=job.job_id,
                num_jobs_before=num_jobs_before,
                num_jobs_after=self.state.num_jobs,
                occupied_resource_before=occupied_resource_before,
                occupied_resource_after=self.state.occupied_resource,
                details=(
                    f"resource_demand={resource_demand}, "
                    f"workload={workload:.6f}"
                ),
            )
        else:
            self.stats.register_rejection(self.state.current_time, decision.reason)

            self._record_event(
                event_type="arrival_rejected",
                job_id=None,
                num_jobs_before=num_jobs_before,
                num_jobs_after=self.state.num_jobs,
                occupied_resource_before=occupied_resource_before,
                occupied_resource_after=self.state.occupied_resource,
                details=(
                    f"reason={decision.reason.value}, "
                    f"resource_demand={resource_demand}, "
                    f"workload={workload:.6f}"
                ),
>>>>>>> main
            )

        self._record_state_snapshot()

    def _process_departures(self) -> None:
<<<<<<< HEAD

        completed_ids = self.state.completed_jobs()

        if not completed_ids:

            return

        for job_id in completed_ids:

            num_jobs_before = self.state.num_jobs

            occupied_resource_before = self.state.occupied_resource

            removed_job = self.state.remove_job(job_id)

            self.stats.register_departure(self.state.current_time)

            self._record_event(

                event_type="departure",

                job_id=removed_job.job_id,

                num_jobs_before=num_jobs_before,

                num_jobs_after=self.state.num_jobs,

                occupied_resource_before=occupied_resource_before,

                occupied_resource_after=self.state.occupied_resource,

                details=(

                    f"arrival_time={removed_job.arrival_time:.6f}, "

                    f"total_workload={removed_job.total_workload:.6f}"

                ),

=======
        """
        Обрабатывает завершения заявок в текущий момент времени.

        Почему сразу пакет завершений:
        ------------------------------
        После продвижения времени до ближайшего завершения может оказаться,
        что завершилось несколько заявок одновременно.
        Такое возможно:
        - из-за численных эффектов;
        - в частично вырожденных сценариях;
        - из-за особенностей распределений.

        Поэтому мы удаляем все завершившиеся заявки, а не только одну.
        """
        completed_ids = self.state.completed_jobs()

        if not completed_ids:
            # Формально такого быть не должно, если мы дошли до события departure.
            # Но мягкая защита полезна на этапе отладки.
            return

        for job_id in completed_ids:
            num_jobs_before = self.state.num_jobs
            occupied_resource_before = self.state.occupied_resource

            removed_job = self.state.remove_job(job_id)
            self.stats.register_departure(self.state.current_time)

            self._record_event(
                event_type="departure",
                job_id=removed_job.job_id,
                num_jobs_before=num_jobs_before,
                num_jobs_after=self.state.num_jobs,
                occupied_resource_before=occupied_resource_before,
                occupied_resource_after=self.state.occupied_resource,
                details=(
                    f"arrival_time={removed_job.arrival_time:.6f}, "
                    f"total_workload={removed_job.total_workload:.6f}"
                ),
>>>>>>> main
            )

        self._record_state_snapshot()

<<<<<<< HEAD
    def run(self) -> SimulationRunResult:

        max_time = self.scenario.simulation.max_time

        eps = self.scenario.simulation.time_epsilon

        while self.state.current_time < max_time - eps:

            t0 = self.state.current_time

            arrival_dt = sample_next_arrival_delta(self.rng, self.state, self.scenario)

            next_departure_job_id, departure_dt = self.state.next_completion(self.scenario)

            next_event_dt = min(arrival_dt, departure_dt)

            if next_event_dt == inf:

                t1 = max_time

                self.stats.observe_constant_interval(

                    t0=t0,

                    t1=t1,

                    num_jobs=self.state.num_jobs,

                    occupied_resource=self.state.occupied_resource,

                )

                self.state.advance_time_and_service(t1 - t0, self.scenario)

                self._record_state_snapshot()

                break

            if t0 + next_event_dt > max_time:

                t1 = max_time

                self.stats.observe_constant_interval(

                    t0=t0,

                    t1=t1,

                    num_jobs=self.state.num_jobs,

                    occupied_resource=self.state.occupied_resource,

                )

                self.state.advance_time_and_service(t1 - t0, self.scenario)

                self._record_state_snapshot()

                break

            t1 = t0 + next_event_dt

            self.stats.observe_constant_interval(

                t0=t0,

                t1=t1,

                num_jobs=self.state.num_jobs,

                occupied_resource=self.state.occupied_resource,

            )

            self.state.advance_time_and_service(next_event_dt, self.scenario)

            if departure_dt < arrival_dt - eps:

                self._process_departures()

            elif arrival_dt < departure_dt - eps:

                self._process_arrival()

            else:

                if next_departure_job_id is not None:

                    self._process_departures()

                self._process_arrival()

        return self.stats.build_result(

            scenario_name=self.scenario.name,

            replication_index=self.replication_index,

            seed=self.seed,

            state_trace=self.state_trace,

            event_log=self.event_log,

        )

def simulate_one_run(

    scenario: ScenarioConfig,

    replication_index: int = 0,

    seed: Optional[int] = None,

) -> SimulationRunResult:

    simulator = SingleRunSimulator(

        scenario=scenario,

        replication_index=replication_index,

        seed=seed,

    )

    return simulator.run()

def print_run_summary(result: SimulationRunResult) -> None:

    print("=" * 90)

    print("РЕЗУЛЬТАТ ОДНОГО ПРОГОНА")

    print("=" * 90)

    print(f"Сценарий:                         {result.scenario_name}")

    print(f"Replication index:                {result.replication_index}")

    print(f"Seed:                             {result.seed}")

    print(f"Полное время моделирования:       {result.total_time}")

    print(f"Warm-up:                          {result.warmup_time}")

    print(f"Наблюдаемое время:                {result.observed_time}")

    print("-" * 90)

    print(f"Среднее число заявок:             {result.mean_num_jobs:.6f}")

    print(f"Средний занятый ресурс:           {result.mean_occupied_resource:.6f}")

    print(f"Число попыток поступления:        {result.arrival_attempts}")

    print(f"Число принятых заявок:            {result.accepted_arrivals}")

    print(f"Число отказов:                    {result.rejected_arrivals}")

    print(f"  из-за ёмкости K:                {result.rejected_capacity}")

    print(f"  из-за лимита приборов N:        {result.rejected_server}")

    print(f"  из-за лимита ресурса R:         {result.rejected_resource}")

    print(f"Число завершённых заявок:         {result.completed_jobs}")

    print(f"Вероятность отказа:               {result.loss_probability:.6f}")

    print(f"Эффективная пропускная способность:{result.throughput:.6f}")

    print("-" * 90)

    print("Оценка стационарного распределения pi_hat(k):")

    for k, value in enumerate(result.pi_hat):

        print(f"  k={k:>2}: {value:.6f}")

    print("=" * 90)

    print()

def _self_test() -> None:

    workloads = standard_workload_family(mean=1.0)

    base_scenario = build_base_scenario(

        workloads["exponential"],

        name_suffix="_simulation_self_test",

    )

    test_sim_cfg: SimulationConfig = replace(

        base_scenario.simulation,

        max_time=2_000.0,

        warmup_time=200.0,

        replications=1,

        record_state_trace=True,

        save_event_log=True,

    )

    test_scenario: ScenarioConfig = replace(

        base_scenario,

        simulation=test_sim_cfg,

    )

    result = simulate_one_run(test_scenario, replication_index=0)

    print_run_summary(result)

    print("Первые 10 снимков состояния:")

    for snapshot in result.state_trace[:10]:

        print(

            f"  t={snapshot.time:>10.6f} | "

            f"k={snapshot.num_jobs:>2} | "

            f"res={snapshot.occupied_resource:>2} | "

            f"lambda={snapshot.arrival_rate:>7.4f} | "

            f"sigma={snapshot.service_speed:>7.4f}"

        )

    print()

    print("Первые 10 записей event log:")

    for event in result.event_log[:10]:

        print(

            f"  t={event.time:>10.6f} | "

            f"type={event.event_type:<17} | "

            f"job_id={str(event.job_id):>4} | "

            f"k: {event.num_jobs_before}->{event.num_jobs_after} | "

            f"res: {event.occupied_resource_before}->{event.occupied_resource_after} | "

            f"{event.details}"

        )

=======
    # ----------------------------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ СИМУЛЯЦИИ
    # ----------------------------------------------------------------------

    def run(self) -> SimulationRunResult:
        """
        Выполняет один прогон симуляции до момента max_time.

        Структура алгоритма:
        -------------------
        На каждом шаге:
        1. Вычисляем время до ближайшего arrival.
        2. Вычисляем время до ближайшего completion.
        3. Берём минимальное из них.
        4. На интервале до ближайшего события:
           - накапливаем time-average статистику;
           - продвигаем состояние по времени.
        5. Обрабатываем событие.

        Особый случай:
        --------------
        Если и arrival, и completion недостижимы (обе величины равны +inf),
        то дальнейших событий не будет. Тогда просто доходим до max_time
        с неизменным состоянием и завершаем прогон.
        """
        max_time = self.scenario.simulation.max_time
        eps = self.scenario.simulation.time_epsilon

        while self.state.current_time < max_time - eps:
            t0 = self.state.current_time

            # Время до следующего arrival.
            arrival_dt = sample_next_arrival_delta(self.rng, self.state, self.scenario)

            # Время до ближайшего completion.
            next_departure_job_id, departure_dt = self.state.next_completion(self.scenario)

            # Берём ближайшее событие.
            next_event_dt = min(arrival_dt, departure_dt)

            # Если событий больше не будет, состояние останется неизменным
            # до конца моделирования.
            if next_event_dt == inf:
                t1 = max_time
                self.stats.observe_constant_interval(
                    t0=t0,
                    t1=t1,
                    num_jobs=self.state.num_jobs,
                    occupied_resource=self.state.occupied_resource,
                )
                self.state.advance_time_and_service(t1 - t0, self.scenario)
                self._record_state_snapshot()
                break

            # Если ближайшее событие лежит за пределом max_time, то доходим
            # только до конца моделирования и завершаем.
            if t0 + next_event_dt > max_time:
                t1 = max_time
                self.stats.observe_constant_interval(
                    t0=t0,
                    t1=t1,
                    num_jobs=self.state.num_jobs,
                    occupied_resource=self.state.occupied_resource,
                )
                self.state.advance_time_and_service(t1 - t0, self.scenario)
                self._record_state_snapshot()
                break

            # Накопление статистики на интервале постоянного состояния.
            t1 = t0 + next_event_dt
            self.stats.observe_constant_interval(
                t0=t0,
                t1=t1,
                num_jobs=self.state.num_jobs,
                occupied_resource=self.state.occupied_resource,
            )

            # Продвигаем состояние до момента события.
            self.state.advance_time_and_service(next_event_dt, self.scenario)

            # Разрешение типа события.
            #
            # При точном совпадении времени arrival и departure приоритет
            # отдаём departures. Это разумно и устойчиво вычислительно:
            # сначала освобождаются места и ресурс, затем может войти новая заявка.
            if departure_dt < arrival_dt - eps:
                self._process_departures()
            elif arrival_dt < departure_dt - eps:
                self._process_arrival()
            else:
                # Практически нулевая по вероятности ситуация для непрерывных
                # распределений, но алгоритмически её надо обработать.
                # Сначала завершаем обслуживание, затем обрабатываем arrival
                # в тот же самый момент времени.
                if next_departure_job_id is not None:
                    self._process_departures()
                self._process_arrival()

        return self.stats.build_result(
            scenario_name=self.scenario.name,
            replication_index=self.replication_index,
            seed=self.seed,
            state_trace=self.state_trace,
            event_log=self.event_log,
        )


# ============================================================================
# ВНЕШНЯЯ ОБЁРТКА
# ============================================================================
# Небольшая функция-обёртка полезна для будущего experiments.py:
# её удобно вызывать в цикле по сценариям и репликациям.
# ============================================================================


def simulate_one_run(
    scenario: ScenarioConfig,
    replication_index: int = 0,
    seed: Optional[int] = None,
) -> SimulationRunResult:
    """
    Выполняет один прогон симуляции и возвращает его результат.

    Это тонкая обёртка над SingleRunSimulator, полезная как публичный API.
    """
    simulator = SingleRunSimulator(
        scenario=scenario,
        replication_index=replication_index,
        seed=seed,
    )
    return simulator.run()


# ============================================================================
# ПЕЧАТЬ КРАТКОЙ СВОДКИ
# ============================================================================
# Удобно для автономного запуска и ручной проверки корректности симулятора.
# ============================================================================


def print_run_summary(result: SimulationRunResult) -> None:
    """
    Печатает краткую человекочитаемую сводку по одному прогону.
    """
    print("=" * 90)
    print("РЕЗУЛЬТАТ ОДНОГО ПРОГОНА")
    print("=" * 90)
    print(f"Сценарий:                         {result.scenario_name}")
    print(f"Replication index:                {result.replication_index}")
    print(f"Seed:                             {result.seed}")
    print(f"Полное время моделирования:       {result.total_time}")
    print(f"Warm-up:                          {result.warmup_time}")
    print(f"Наблюдаемое время:                {result.observed_time}")
    print("-" * 90)
    print(f"Среднее число заявок:             {result.mean_num_jobs:.6f}")
    print(f"Средний занятый ресурс:           {result.mean_occupied_resource:.6f}")
    print(f"Число попыток поступления:        {result.arrival_attempts}")
    print(f"Число принятых заявок:            {result.accepted_arrivals}")
    print(f"Число отказов:                    {result.rejected_arrivals}")
    print(f"  из-за ёмкости K:                {result.rejected_capacity}")
    print(f"  из-за лимита приборов N:        {result.rejected_server}")
    print(f"  из-за лимита ресурса R:         {result.rejected_resource}")
    print(f"Число завершённых заявок:         {result.completed_jobs}")
    print(f"Вероятность отказа:               {result.loss_probability:.6f}")
    print(f"Эффективная пропускная способность:{result.throughput:.6f}")
    print("-" * 90)
    print("Оценка стационарного распределения pi_hat(k):")
    for k, value in enumerate(result.pi_hat):
        print(f"  k={k:>2}: {value:.6f}")
    print("=" * 90)
    print()


# ============================================================================
# SELF-TEST
# ============================================================================
# Этот блок позволяет проверить simulation.py уже сейчас, не дожидаясь
# experiments.py и plots.py.
# ============================================================================


def _self_test() -> None:
    """
    Самотест DES-движка.

    Что делаем:
    ----------
    1. Берём базовый сценарий.
    2. Немного уменьшаем горизонт моделирования, чтобы self-test был быстрым.
    3. Включаем state trace и event log.
    4. Выполняем один прогон.
    5. Печатаем summary.
    6. Показываем первые записи trace и event log.

    Это полезно, потому что позволяет убедиться, что:
    - событийный цикл работает;
    - генерация arrival/departure работает;
    - статистика накапливается;
    - структура результата пригодна для дальнейших файлов.
    """
    workloads = standard_workload_family(mean=1.0)
    base_scenario = build_base_scenario(
        workloads["exponential"],
        name_suffix="_simulation_self_test",
    )

    # Для быстрой автономной проверки делаем прогон короче и включаем трассировку.
    test_sim_cfg: SimulationConfig = replace(
        base_scenario.simulation,
        max_time=2_000.0,
        warmup_time=200.0,
        replications=1,
        record_state_trace=True,
        save_event_log=True,
    )

    test_scenario: ScenarioConfig = replace(
        base_scenario,
        simulation=test_sim_cfg,
    )

    result = simulate_one_run(test_scenario, replication_index=0)
    print_run_summary(result)

    print("Первые 10 снимков состояния:")
    for snapshot in result.state_trace[:10]:
        print(
            f"  t={snapshot.time:>10.6f} | "
            f"k={snapshot.num_jobs:>2} | "
            f"res={snapshot.occupied_resource:>2} | "
            f"lambda={snapshot.arrival_rate:>7.4f} | "
            f"sigma={snapshot.service_speed:>7.4f}"
        )
    print()

    print("Первые 10 записей event log:")
    for event in result.event_log[:10]:
        print(
            f"  t={event.time:>10.6f} | "
            f"type={event.event_type:<17} | "
            f"job_id={str(event.job_id):>4} | "
            f"k: {event.num_jobs_before}->{event.num_jobs_after} | "
            f"res: {event.occupied_resource_before}->{event.occupied_resource_after} | "
            f"{event.details}"
        )
>>>>>>> main
    print()

    print("SELF-TEST simulation.py завершён успешно.")

<<<<<<< HEAD
if __name__ == "__main__":

    _self_test()
=======

if __name__ == "__main__":
    _self_test()
>>>>>>> main
