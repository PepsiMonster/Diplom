"""
Этот модуль запускает один прогон имитации.

На каждом шаге:
1. вычисляется время до следующего поступления;
2. вычисляется время до ближайшего завершения;
3. выбирается ближайшее событие;
4. система продвигается по времени;
5. обновляется статистика;
6. обрабатывается arrival или departure.

Что считается:
- оценка стационарного распределения по числу заявок: pi_hat(k);
- среднее число заявок в системе;
- средний занятый ресурс;
- число попыток поступления;
- число принятых заявок;
- число отказов;
- вероятность отказа;
- эффективная пропускная способность.

Сейчас можно:
- проверить корректность работы симулятора;
- провести первые эксперименты по чувствительности;
- получить таблицы и графики для главы по имитации.

Что позже возможно добавить добавить:
- больше диагностических метрик;
- сохранение результатов;
- батч-средние;
- доверительные интервалы;
- более сложные сценарии.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Optional

import numpy as np

from params import (
    ResourceDistributionConfig,
    ScenarioConfig,
    WorkloadDistributionConfig,
    build_base_scenario,
    standard_workload_family,
)
from model import RejectionReason, SystemState

"""
Результаты одного прогона
Они:
- сохраняются в csv
- агрегируются по повторам
- передаются в plots.py
"""

@dataclass(slots=True)
class SimulationResult:
    """
    Итог одного прогона симуляции.
    Поля:
    -
    scenario_name:
        Имя сценария.
    replication_index:
        Номер повтора.
    seed:
        Seed, использованный в прогоне.
    total_time:
        Полное время моделирования.
    warmup_time:
        Длина разгона.
    observed_time:
        Длина участка, на котором реально собиралась статистика.
    pi_hat:
        Оценка стационарного распределения по числу заявок.
    mean_num_jobs:
        Среднее число заявок в системе.
    mean_occupied_resource:
        Средний занятый ресурс.
    arrival_attempts:
        Число попыток поступления на участке наблюдения.
    accepted_arrivals:
        Число принятых заявок.
    rejected_arrivals:
        Число отказов.
    rejected_capacity / rejected_server / rejected_resource:
        Разбиение отказов по причинам.
    completed_jobs:
        Число завершившихся заявок.
    loss_probability:
        Оценка вероятности отказа.
    throughput:
        Эффективная пропускная способность.
    state_trace:
        Снимки состояния во времени, если включено в params.py.
    event_log:
        Краткий журнал событий, если включено в params.py.
    """

    scenario_name: str
    replication_index: int
    seed: int

    total_time: float
    warmup_time: float
    observed_time: float

    pi_hat: tuple[float, ...]
    mean_num_jobs: float
    mean_occupied_resource: float

    arrival_attempts: int
    accepted_arrivals: int
    rejected_arrivals: int

    rejected_capacity: int
    rejected_server: int
    rejected_resource: int

    completed_jobs: int

    loss_probability: float
    throughput: float

    state_trace: tuple[tuple[float, int, int], ...] = ()
    event_log: tuple[str, ...] = ()

    def flat_summary(self) -> dict[str, float | int | str]:
        """
        Возвращает результат в виде плоского словаря.
        Это пригодится позже, когда мы будем собирать таблицы результатов.
        """
        result: dict[str, float | int | str] = {
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
            result[f"pi_hat_{k}"] = value

        return result


# Вспомогательные функции

# Здесь содержится вся генерация случайных величин и маленькие численные утилиты. 
# Это упрощает основной цикл симуляции.


def derive_run_seed(base_seed: int, replication_index: int) -> int:
    """
    Строит seed отдельного прогона из базового seed. Это даёт воспроизводимость.
    """
    return int(base_seed + 1_000_003 * replication_index)


def interval_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    """
    Возвращает длину пересечения интервалов [a0, a1] и [b0, b1].

    Каждый интервал между событиями надо пересекать с интервалом наблюдения [warmup_time, max_time]
    """
    left = max(a0, b0)
    right = min(a1, b1)
    return max(0.0, right - left)


def sample_resource_demand(
    rng: np.random.Generator,
    config: ResourceDistributionConfig,
) -> int:
    """
    Генерирует требование заявки к ресурсу.
    """
    if config.kind == "deterministic":
        return int(config.deterministic_value)

    return int(rng.integers(config.min_units, config.max_units + 1))    # discrete_uniform


def sample_workload(
    rng: np.random.Generator,
    config: WorkloadDistributionConfig,
) -> float:
    """
    Генерирует объём работы заявки.
    Это не готовое время обслуживания.
    Затем этот объём будет уменьшаться со скоростью sigma_k.
    """
    if config.kind == "deterministic":
        return float(config.mean)

    if config.kind == "exponential":
        return float(rng.exponential(scale=config.mean))

    if config.kind == "erlang":
        return float(rng.gamma(shape=config.erlang_order, scale=config.mean / config.erlang_order))

    if config.kind == "hyperexponential2":
        p = config.hyper_p
        rate_1, rate_2 = config.hyper_rates
        if rng.random() < p:
            return float(rng.exponential(scale=1.0 / rate_1))
        return float(rng.exponential(scale=1.0 / rate_2))

    raise ValueError(f"Неизвестный kind={config.kind}")


def sample_arrival_delta(
    rng: np.random.Generator,
    state: SystemState,
    scenario: ScenarioConfig,
) -> float:
    """
    Генерирует время до следующего поступления.

    Если текущая интенсивность поступления равна нулю, возвращается бесконечность.
    """
    rate = state.current_arrival_rate(scenario)
    if rate <= 0:
        return inf
    return float(rng.exponential(scale=1.0 / rate))


# Основной симулятор; DES-цикл


def simulate_one_run(
    scenario: ScenarioConfig,
    replication_index: int = 0,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Выполняет один прогон симуляции:

    1. Инициализируем RNG и пустое состояние.
    2. Пока текущее время меньше max_time:
       - ищем ближайшее arrival;
       - ищем ближайшее departure;
       - продвигаем систему до ближайшего события;
       - обновляем time-average статистику;
       - обрабатываем событие.
    3. Строим агрегированные оценки и возвращаем результат.
    """
    scenario.validate()

    run_seed = derive_run_seed(scenario.simulation.seed, replication_index) if seed is None else int(seed)
    rng = np.random.default_rng(run_seed)

    state = SystemState()

    max_time = scenario.simulation.max_time
    warmup_time = scenario.simulation.warmup_time
    eps = scenario.simulation.time_epsilon

    # Статистика; пока в простых переменных
    state_times = [0.0 for _ in range(scenario.capacity_k + 1)]
    resource_time_integral = 0.0

    arrival_attempts = 0
    accepted_arrivals = 0
    rejected_arrivals = 0

    rejected_capacity = 0
    rejected_server = 0
    rejected_resource = 0

    completed_jobs = 0

    state_trace: list[tuple[float, int, int]] = []
    event_log: list[str] = []

    def record_state_snapshot() -> None:
        """
        Сохраняет краткий снимок состояния, если это включено в конфиге.
        Формат: (time, num_jobs, occupied_resource)
        """
        if scenario.simulation.record_state_trace:
            state_trace.append((state.current_time, state.num_jobs, state.occupied_resource))

    def record_event(message: str) -> None:
        """
        Сохраняет текстовую запись события, если это включено в конфиге.
        """
        if scenario.simulation.save_event_log:
            event_log.append(message)

    def observe_interval(t0: float, t1: float) -> None:
        """
        Учитывает вклад интервала [t_0,t_1] в стационарные оценки.
        На промежутке между событиями:
        - число заявок в системе постоянно;
        - занятый ресурс постоянен.

        Поэтому time-average статистика собирается именно по таким кускам.
        """
        nonlocal resource_time_integral

        overlap = interval_overlap(t0, t1, warmup_time, max_time)
        if overlap <= 0:
            return

        state_times[state.num_jobs] += overlap
        resource_time_integral += state.occupied_resource * overlap

    record_state_snapshot()

# Основной цикл событий
    while state.current_time < max_time - eps:
        t0 = state.current_time

        arrival_dt = sample_arrival_delta(rng, state, scenario)     # Время до следующего поступления.
        _, departure_dt = state.next_completion(scenario)           # Время до ближайшего завершения.
        next_dt = min(arrival_dt, departure_dt)                     # Ближайшее событие.

        # Если событий больше не будет, просто доходим до конца горизонта.
        if next_dt == inf:
            observe_interval(t0, max_time)
            state.advance_time(max_time - t0, scenario)
            record_state_snapshot()
            break

        # Если ближайшее событие уже за границей горизонта моделирования, тоже просто доходим до max_time.
        if t0 + next_dt > max_time:
            observe_interval(t0, max_time)
            state.advance_time(max_time - t0, scenario)
            record_state_snapshot()
            break

        # Накопление статистики на интервале постоянного состояния.
        t1 = t0 + next_dt
        observe_interval(t0, t1)

        # Продвигаем систему до момента события.
        state.advance_time(next_dt, scenario)
        """
        # Обработка ближайшего события.
        # Если времена arrival и departure совпали, сначала обрабатываем
        # departure, потом arrival. Это удобное и естественное правило:
        # сначала освобождаются ресурсы, затем может быть принят новый запрос.
        """

        if departure_dt <= arrival_dt + eps:
            completed_ids = state.completed_job_ids()
            for job_id in completed_ids:
                state.remove_job(job_id)
                if state.current_time >= warmup_time:
                    completed_jobs += 1
                record_event(f"t={state.current_time:.6f}: departure job_id={job_id}")

            record_state_snapshot()

            # Если было почти точное совпадение arrival и departure, то arrival обрабатываем в тот же момент времени.
            if abs(arrival_dt - departure_dt) <= eps:
                resource_demand = sample_resource_demand(rng, scenario.resource_distribution)
                workload = sample_workload(rng, scenario.workload_distribution)

                if state.current_time >= warmup_time:
                    arrival_attempts += 1

                decision = state.can_accept(resource_demand, scenario)

                if decision.accepted:
                    job = state.create_job(resource_demand=resource_demand, workload=workload)
                    state.add_job(job, scenario)
                    if state.current_time >= warmup_time:
                        accepted_arrivals += 1
                    record_event(
                        f"t={state.current_time:.6f}: arrival accepted "
                        f"job_id={job.job_id}, resource={resource_demand}, work={workload:.6f}"
                    )
                else:
                    if state.current_time >= warmup_time:
                        rejected_arrivals += 1
                        if decision.reason == RejectionReason.CAPACITY_LIMIT:
                            rejected_capacity += 1
                        elif decision.reason == RejectionReason.SERVER_LIMIT:
                            rejected_server += 1
                        elif decision.reason == RejectionReason.RESOURCE_LIMIT:
                            rejected_resource += 1

                    record_event(
                        f"t={state.current_time:.6f}: arrival rejected "
                        f"reason={decision.reason.value}, resource={resource_demand}, work={workload:.6f}"
                    )

                record_state_snapshot()

        else:
            # Здесь ближайшее событие — arrival.
            resource_demand = sample_resource_demand(rng, scenario.resource_distribution)
            workload = sample_workload(rng, scenario.workload_distribution)

            if state.current_time >= warmup_time:
                arrival_attempts += 1

            decision = state.can_accept(resource_demand, scenario)

            if decision.accepted:
                job = state.create_job(resource_demand=resource_demand, workload=workload)
                state.add_job(job, scenario)
                if state.current_time >= warmup_time:
                    accepted_arrivals += 1
                record_event(
                    f"t={state.current_time:.6f}: arrival accepted "
                    f"job_id={job.job_id}, resource={resource_demand}, work={workload:.6f}"
                )
            else:
                if state.current_time >= warmup_time:
                    rejected_arrivals += 1
                    if decision.reason == RejectionReason.CAPACITY_LIMIT:
                        rejected_capacity += 1
                    elif decision.reason == RejectionReason.SERVER_LIMIT:
                        rejected_server += 1
                    elif decision.reason == RejectionReason.RESOURCE_LIMIT:
                        rejected_resource += 1

                record_event(
                    f"t={state.current_time:.6f}: arrival rejected "
                    f"reason={decision.reason.value}, resource={resource_demand}, work={workload:.6f}"
                )

            record_state_snapshot()

    # Финальная обработка результатов
    observed_time = max_time - warmup_time

    pi_hat = tuple(time_in_state / observed_time for time_in_state in state_times)
    mean_num_jobs = sum(k * pi_hat[k] for k in range(len(pi_hat)))
    mean_occupied_resource = resource_time_integral / observed_time

    if arrival_attempts > 0:
        loss_probability = rejected_arrivals / arrival_attempts
    else:
        loss_probability = 0.0

    throughput = completed_jobs / observed_time

    return SimulationResult(
        scenario_name=scenario.name,
        replication_index=replication_index,
        seed=run_seed,
        total_time=max_time,
        warmup_time=warmup_time,
        observed_time=observed_time,
        pi_hat=pi_hat,
        mean_num_jobs=mean_num_jobs,
        mean_occupied_resource=mean_occupied_resource,
        arrival_attempts=arrival_attempts,
        accepted_arrivals=accepted_arrivals,
        rejected_arrivals=rejected_arrivals,
        rejected_capacity=rejected_capacity,
        rejected_server=rejected_server,
        rejected_resource=rejected_resource,
        completed_jobs=completed_jobs,
        loss_probability=loss_probability,
        throughput=throughput,
        state_trace=tuple(state_trace),
        event_log=tuple(event_log),
    )


# Принты для одиночного запуска


def print_result(result: SimulationResult) -> None:
    """
    Печатает ключевые итоги одного прогона.

    Здесь сознательно выводится только самое важное.
    """
    print("=" * 80) # Для красоты
    print("ИТОГ ОДНОГО ПРОГОНА")
    print("=" * 80) # Для престижа
    print(f"Сценарий:               {result.scenario_name}")
    print(f"Replication:            {result.replication_index}")
    print(f"Seed:                   {result.seed}")
    print(f"Наблюдаемое время:      {result.observed_time}")
    print(f"Среднее число заявок:   {result.mean_num_jobs:.6f}")
    print(f"Средний занятый ресурс: {result.mean_occupied_resource:.6f}")
    print(f"Попытки поступления:    {result.arrival_attempts}")
    print(f"Принятые заявки:        {result.accepted_arrivals}")
    print(f"Отказы:                 {result.rejected_arrivals}")
    print(f"Вероятность отказа:     {result.loss_probability:.6f}")
    print(f"Throughput:             {result.throughput:.6f}")
    print("-" * 80)
    print("pi_hat(k):")
    for k, value in enumerate(result.pi_hat):
        print(f"  k={k:>2}: {value:.6f}")
    print("=" * 80)


if __name__ == "__main__":
    family = standard_workload_family(mean=1.0)
    scenario = build_base_scenario(family["exponential"], name_suffix="_sim_test")

    # Для self-test делаем прогон короче и включаем минимальную диагностику.
    scenario.simulation.max_time = 2_000.0
    scenario.simulation.warmup_time = 200.0
    scenario.simulation.record_state_trace = True
    scenario.simulation.save_event_log = True

    result = simulate_one_run(scenario, replication_index=0)
    print_result(result)

    print()
    print("Первые 10 записей state_trace:")
    for item in result.state_trace[:10]:
        print(item)

    print()
    print("Первые 10 записей event_log:")
    for item in result.event_log[:10]:
        print(item)