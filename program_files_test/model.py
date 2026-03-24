"""
Минимальная предметная модель системы массового обслуживания с ограниченными ресурсами и state-dependent характеристиками.

Этот файлик описывает:

1. Заявку:
    - сколько ресурса она занимает;
    - какой у неё полный объём работы;
    - сколько работы осталось.

2. Состояние системы:
    - текущее время;
    - какие заявки сейчас активны;
    - сколько заявок в системе;
    - сколько ресурса занято.

3. Базовые операции:
    - можно ли принять новую заявку;
    - как добавить заявку;
    - как удалить заявку;
    - как продвинуть систему по времени;
    - какая заявка завершится первой.

Ключевая идея модели:
Мы храним у каждой заявки не "готовое время завершения", а остаточный объём работы remaining_workload.

Это важно, потому что скорость обслуживания зависит от состояния системы.
Если число заявок меняется, меняется и sigma_k, а значит удобнее хранить 
именно остаток работы и уменьшать его по мере движения времени.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import inf
from typing import Optional

from params import ScenarioConfig, build_base_scenario, standard_workload_family

# Причины отказа

class RejectionReason(str, Enum):
    """
    Причины отказа в приёме заявки.

    Значения:
    capacity_limit:
        Система уже заполнена по общей ёмкости K.
    server_limit:
        Нет свободного прибора обслуживания.
    resource_limit:
        Не хватает свободного ресурса.
    none:
        Отказа нет, заявку можно принять.
    """

    CAPACITY_LIMIT = "capacity_limit"
    SERVER_LIMIT = "server_limit"
    RESOURCE_LIMIT = "resource_limit"
    NONE = "none" # важная строчка

# Решение о допуске поступающей заявки
# Вместо "просто True/False" удобно сразу возвращать объект,
# который хранит и сам факт допуска, и причину отказа.

@dataclass(slots=True)
class AdmissionDecision:
    """
    Результат проверки возможности принять заявку.
    accepted:
        True, если заявку можно принять.
    reason:
        Причина отказа, если accepted == False.
    """
    accepted: bool
    reason: RejectionReason = RejectionReason.NONE
"""
Заява
Каждая заявка хранит:
 - идентификатор;
 - момент поступления;
 - требуемый ресурс;
 - полный объём работы;
 - остаточный объём работы.
"""

@dataclass(slots=True)
class Job:
    """
    Описание одной заявки.

    job_id:
        Уникальный идентификатор заявки.
    arrival_time:
        Момент поступления заявки.
    resource_demand:
        Объём ресурса, который заявка занимает на всём интервале нахождения
        в системе.
    total_workload:
        Полный объём работы заявки.
    remaining_workload:
        Остаточный объём работы.

    !Если remaining_workload не задан явно, он автоматически принимается равным total_workload.
    """

    job_id: int
    arrival_time: float
    resource_demand: int
    total_workload: float
    remaining_workload: Optional[float] = None

    def __post_init__(self) -> None:
        """
        Минимальная проверка корректности заявки.
        """
        if self.arrival_time < 0:
            raise ValueError("arrival_time должен быть >= 0")
        if self.resource_demand <= 0:
            raise ValueError("resource_demand должен быть > 0")
        if self.total_workload <= 0:
            raise ValueError("total_workload должен быть > 0")

        if self.remaining_workload is None:
            self.remaining_workload = self.total_workload

        if self.remaining_workload < 0:
            raise ValueError("remaining_workload должен быть >= 0")

    def progress(self, dt: float, service_speed: float) -> None:
        """
        Уменьшает остаточный объём работы на интервале длины dt.
        remaining_workload <- max(remaining_workload - service_speed * dt, 0)

        Здесь предполагается, что на интервале длины dt состояние системы
        не меняется, а значит скорость обслуживания постоянна.
        """
        if dt < 0:
            raise ValueError("dt должен быть >= 0")
        if service_speed < 0:
            raise ValueError("service_speed должен быть >= 0")

        if dt == 0 or service_speed == 0:
            return

        assert self.remaining_workload is not None
        self.remaining_workload = max(self.remaining_workload - service_speed * dt, 0.0)

    def is_completed(self, tol: float = 1e-12) -> bool:
        """
        Проверяет, завершилась ли заявка.
        Небольшой допуск tol нужен, чтобы не зависеть от численных ошибок.
        """
        assert self.remaining_workload is not None
        return self.remaining_workload <= tol

    def time_to_completion(self, service_speed: float) -> float:
        """
        Возвращает время до завершения заявки при фиксированной скорости.
        Если service_speed == 0, заявка не может завершиться за конечное время, поэтому возвращается +inf.
        """
        if service_speed < 0:
            raise ValueError("service_speed должен быть >= 0")

        assert self.remaining_workload is not None

        if self.is_completed():
            return 0.0

        if service_speed == 0.0:
            return inf

        return self.remaining_workload / service_speed

# Состояние системы
# Оно хранит текущее состояние системы и реализует базовые операции над ним

@dataclass(slots=True)
class SystemState:
    """
    Текущее состояние системы.

    current_time:
        Текущее модельное время.
    active_jobs:
        Словарь активных заявок.
        Ключ -> job_id
        Значение -> Job
    next_job_id:
        Следующий идентификатор, который будет присвоен новой заявке.

    Здесь не хранятся статистики эксперимента.
    """

    current_time: float = 0.0
    active_jobs: dict[int, Job] = field(default_factory=dict)
    next_job_id: int = 1

# Базовые св-ва состояния

    @property
    def num_jobs(self) -> int:
        """
        Текущее число заявок в системе.
        """
        return len(self.active_jobs)

    @property
    def occupied_resource(self) -> int:
        """
        Суммарный объём занятого ресурса.
        """
        return sum(job.resource_demand for job in self.active_jobs.values())

    def current_arrival_rate(self, scenario: ScenarioConfig) -> float:
        """
        Возвращает текущую интенсивность поступления lambda_k,
        где k = число заявок в системе.
        """
        return scenario.arrival_rate_by_state[self.num_jobs]

    def current_service_speed(self, scenario: ScenarioConfig) -> float:
        """
        Возвращает текущую скорость обслуживания sigma_k,где k = число заявок в системе.

        sigma_k — это скорость уменьшения остаточного объёма работы
        каждой активной заявки в состоянии k.
        """
        return scenario.service_speed_by_state[self.num_jobs]

    # Проверка допуска

    def can_accept(self, resource_demand: int, scenario: ScenarioConfig) -> AdmissionDecision:
        """
        Проверяет, можно ли принять новую заявку с данным требованием ресурса.

        Проверяются три ограничения:
        - общая ёмкость системы K;
        - число приборов N;
        - доступный ресурс R.
        """
        if resource_demand <= 0:
            raise ValueError("resource_demand должен быть > 0")
        if self.num_jobs >= scenario.capacity_k:                                # Проверка общей ёмкости.
            return AdmissionDecision(False, RejectionReason.CAPACITY_LIMIT)
        if self.num_jobs >= scenario.servers_n:                                 # Проверка числа приборов.
            return AdmissionDecision(False, RejectionReason.SERVER_LIMIT)
        if self.occupied_resource + resource_demand > scenario.total_resource_r:# Проверка ресурса.
            return AdmissionDecision(False, RejectionReason.RESOURCE_LIMIT)

        return AdmissionDecision(True, RejectionReason.NONE)

# Создание и добавление заявок

    def create_job(
            self,*,resource_demand: int,
        workload: float,arrival_time: Optional[float] = None,
    ) -> Job:
        """
        Создаёт новую заявку, но не добавляет её автоматически в систему.
        - сначала можно сгенерировать параметры заявки;
        - потом проверить can_accept(...);
        - потом явно вызвать add_job(...).

        arrival_time использует текущее модельное время, если не задан явно.
        """
        if resource_demand <= 0:
            raise ValueError("resource_demand должен быть > 0")
        if workload <= 0:
            raise ValueError("workload должен быть > 0")

        job = Job(
            job_id=self.next_job_id,
            arrival_time=self.current_time if arrival_time is None else arrival_time,
            resource_demand=resource_demand,
            total_workload=workload,
        )
        self.next_job_id += 1
        return job

    def add_job(self, job: Job, scenario: ScenarioConfig) -> None:
        """
        Добавляет заявку в систему.
        Если заявка не помещается, выбрасывается исключение.
        Это удобно, потому что попытка добавить "недопустимую" заявку
        обычно означает ошибку логики в вызывающем коде.
        """
        decision = self.can_accept(job.resource_demand, scenario)
        if not decision.accepted:
            raise ValueError(f"Нельзя добавить заявку: {decision.reason.value}")

        if job.job_id in self.active_jobs:
            raise ValueError("Заявка с таким job_id уже есть в системе")

        self.active_jobs[job.job_id] = job

    def remove_job(self, job_id: int) -> Job:
        """
        Удаляет заявку из системы и возвращает её объект.
        Это пригодится позже в simulation.py, когда нужно будет:
        - фиксировать завершения;
        - считать время пребывания;
        - обновлять статистику.
        """
        if job_id not in self.active_jobs:
            raise KeyError(f"Заявка {job_id} не найдена")

        return self.active_jobs.pop(job_id)

# Продвижение времени

    def advance_time(self, dt: float, scenario: ScenarioConfig) -> None:
        """
        Продвигает систему по времени на dt.

        На этом интервале:
        - состояние считается неизменным;
        - скорость обслуживания sigma_k постоянна;
        - остаток работы всех активных заявок уменьшается.

        После обновления заявок модельное время увеличивается на dt.
        """
        if dt < 0:
            raise ValueError("dt должен быть >= 0")

        if dt == 0:
            return

        service_speed = self.current_service_speed(scenario)

        for job in self.active_jobs.values():
            job.progress(dt=dt, service_speed=service_speed)

        self.current_time += dt

# Информация о завершениях

    def completed_job_ids(self, tol: float = 1e-12) -> list[int]:
        """
        Возвращает список заявок, у которых обслуживание завершено.
        """
        result = []
        for job_id, job in self.active_jobs.items():
            if job.is_completed(tol=tol):
                result.append(job_id)
        return sorted(result)

    def next_completion(self, scenario: ScenarioConfig) -> tuple[Optional[int], float]:
        """
        Возвращает ближайшее завершение в виде пары:
            (job_id, delta_t)
        Если активных заявок нет, возвращается:
            (None, inf)
        Если несколько заявок завершаются одновременно, выбирается та, у которой меньший job_id.
        """
        if not self.active_jobs:
            return None, inf

        service_speed = self.current_service_speed(scenario)

        best_job_id = None
        best_dt = inf

        for job_id, job in self.active_jobs.items():
            dt = job.time_to_completion(service_speed)

            if dt < best_dt:
                best_dt = dt
                best_job_id = job_id
            elif dt == best_dt and best_job_id is not None and job_id < best_job_id:
                best_job_id = job_id

        return best_job_id, best_dt

# ПРинт

    def short_summary(self) -> str:
        """
        Краткая текстовая сводка по текущему состоянию.
        """
        return (
            f"SystemState(t={self.current_time:.6f}, "
            f"k={self.num_jobs}, "
            f"resource={self.occupied_resource})"
        )


# мини SELF-TEST
# Этот блок позволяет проверить model.py отдельно, до simulation.py.



if __name__ == "__main__":
    family = standard_workload_family(mean=1.0) # Берём одно из стандартных распределений объёма работы.
    scenario = build_base_scenario(             # Строим базовый сценарий.
        family["exponential"], 
        name_suffix="_model_test")
    state = SystemState()                       # Создаём пустое состояние.
    print("Начальное состояние:")
    print(state.short_summary())
    print()

    # Добавляем первую заявку.
    job_1 = state.create_job(resource_demand=2, workload=1.5)
    decision_1 = state.can_accept(job_1.resource_demand, scenario)
    print("Допуск первой заявки:", decision_1.accepted, decision_1.reason.value)
    state.add_job(job_1, scenario)
    print(state.short_summary())
    print()

    # Добавляем вторую заявку.
    job_2 = state.create_job(resource_demand=3, workload=0.8)
    decision_2 = state.can_accept(job_2.resource_demand, scenario)
    print("Допуск второй заявки:", decision_2.accepted, decision_2.reason.value)
    state.add_job(job_2, scenario)
    print(state.short_summary())
    print()

    # Смотрим, какая заявка завершится первой.
    next_job_id, next_dt = state.next_completion(scenario)
    print(f"Ближайшее завершение: job_id={next_job_id}, через {next_dt:.6f}")
    print()

    # Продвигаем время до ближайшего завершения.
    state.advance_time(next_dt, scenario)
    print("Состояние после продвижения времени:")
    print(state.short_summary())
    print()

    # Удаляем все завершившиеся заявки.
    completed = state.completed_job_ids()
    print("Завершившиеся заявки:", completed)

    for job_id in completed:
        removed = state.remove_job(job_id)
        print(
            f"Удалена заявка {removed.job_id}: "
            f"resource={removed.resource_demand}, "
            f"total_workload={removed.total_workload}"
        )

    print()
    print("Итоговое состояние:")
    print(state.short_summary())