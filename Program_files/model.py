from __future__ import annotations

from dataclasses import dataclass, field

from enum import Enum

from math import inf, isclose

from typing import Optional

from params import ScenarioConfig, build_base_scenario, standard_workload_family

class RejectionReason(str, Enum):

    CAPACITY_LIMIT = "capacity_limit"

    SERVER_LIMIT = "server_limit"

    RESOURCE_LIMIT = "resource_limit"

    NONE = "none"

@dataclass(slots=True)

class AdmissionDecision:

    accepted: bool

    reason: RejectionReason = RejectionReason.NONE

@dataclass(slots=True)

class Job:

    job_id: int

    arrival_time: float

    resource_demand: int

    total_workload: float

    remaining_workload: Optional[float] = None

    def __post_init__(self) -> None:

        if self.arrival_time < 0:

            raise ValueError(f"arrival_time должен быть >= 0, получено: {self.arrival_time}")

        if self.resource_demand <= 0:

            raise ValueError(f"resource_demand должен быть > 0, получено: {self.resource_demand}")

        if self.total_workload <= 0:

            raise ValueError(f"total_workload должен быть > 0, получено: {self.total_workload}")

        if self.remaining_workload is None:

            self.remaining_workload = self.total_workload

        if self.remaining_workload < 0:

            raise ValueError(

                f"remaining_workload должен быть >= 0, получено: {self.remaining_workload}"

            )

    def progress(self, dt: float, service_speed: float) -> None:

        if dt < 0:

            raise ValueError(f"dt должен быть >= 0, получено: {dt}")

        if service_speed < 0:

            raise ValueError(f"service_speed должен быть >= 0, получено: {service_speed}")

        if dt == 0 or service_speed == 0:

            return

        assert self.remaining_workload is not None

        self.remaining_workload = max(self.remaining_workload - service_speed * dt, 0.0)

    def is_completed(self, tol: float = 1e-12) -> bool:

        assert self.remaining_workload is not None

        return self.remaining_workload <= tol

    def time_to_completion(self, service_speed: float) -> float:

        if service_speed < 0:

            raise ValueError(f"service_speed должен быть >= 0, получено: {service_speed}")

        assert self.remaining_workload is not None

        if self.is_completed():

            return 0.0

        if service_speed == 0.0:

            return inf

        return self.remaining_workload / service_speed

@dataclass(slots=True)

class SystemState:

    current_time: float = 0.0

    active_jobs: dict[int, Job] = field(default_factory=dict)

    next_job_id: int = 1

    @property

    def num_jobs(self) -> int:

        return len(self.active_jobs)

    @property

    def occupied_resource(self) -> int:

        return sum(job.resource_demand for job in self.active_jobs.values())

    def free_resource(self, scenario: ScenarioConfig) -> int:

        return scenario.total_resource_r - self.occupied_resource

    def free_servers(self, scenario: ScenarioConfig) -> int:

        return scenario.servers_n - self.num_jobs

    def current_arrival_rate(self, scenario: ScenarioConfig) -> float:

        return scenario.arrival_rate_by_state[self.num_jobs]

    def current_service_speed(self, scenario: ScenarioConfig) -> float:

        return scenario.service_speed_by_state[self.num_jobs]

    def can_accept(self, resource_demand: int, scenario: ScenarioConfig) -> AdmissionDecision:

        if resource_demand <= 0:

            raise ValueError(f"resource_demand должен быть > 0, получено: {resource_demand}")

        if self.num_jobs >= scenario.capacity_k:

            return AdmissionDecision(False, RejectionReason.CAPACITY_LIMIT)

        if self.num_jobs >= scenario.servers_n:

            return AdmissionDecision(False, RejectionReason.SERVER_LIMIT)

        if self.occupied_resource + resource_demand > scenario.total_resource_r:

            return AdmissionDecision(False, RejectionReason.RESOURCE_LIMIT)

        return AdmissionDecision(True, RejectionReason.NONE)

    def create_job(

        self,

        *,

        resource_demand: int,

        workload: float,

        arrival_time: Optional[float] = None,

    ) -> Job:

        if resource_demand <= 0:

            raise ValueError(f"resource_demand должен быть > 0, получено: {resource_demand}")

        if workload <= 0:

            raise ValueError(f"workload должен быть > 0, получено: {workload}")

        job = Job(

            job_id=self.next_job_id,

            arrival_time=self.current_time if arrival_time is None else arrival_time,

            resource_demand=resource_demand,

            total_workload=workload,

        )

        self.next_job_id += 1

        return job

    def add_job(self, job: Job, scenario: ScenarioConfig) -> None:

        decision = self.can_accept(job.resource_demand, scenario)

        if not decision.accepted:

            raise ValueError(

                f"Невозможно добавить job_id={job.job_id}: отказ по причине {decision.reason.value}"

            )

        if job.job_id in self.active_jobs:

            raise ValueError(f"Заявка job_id={job.job_id} уже есть в системе")

        self.active_jobs[job.job_id] = job

    def remove_job(self, job_id: int) -> Job:

        if job_id not in self.active_jobs:

            raise KeyError(f"Заявка job_id={job_id} не найдена среди активных")

        return self.active_jobs.pop(job_id)

    def advance_time_and_service(self, dt: float, scenario: ScenarioConfig) -> None:

        if dt < 0:

            raise ValueError(f"dt должен быть >= 0, получено: {dt}")

        if dt == 0:

            return

        current_k = self.num_jobs

        service_speed = scenario.service_speed_by_state[current_k]

        for job in self.active_jobs.values():

            job.progress(dt=dt, service_speed=service_speed)

        self.current_time += dt

    def completion_offsets(self, scenario: ScenarioConfig) -> dict[int, float]:

        if not self.active_jobs:

            return {}

        service_speed = self.current_service_speed(scenario)

        return {

            job_id: job.time_to_completion(service_speed)

            for job_id, job in self.active_jobs.items()

        }

    def next_completion(self, scenario: ScenarioConfig) -> tuple[Optional[int], float]:

        offsets = self.completion_offsets(scenario)

        if not offsets:

            return None, inf

        best_job_id = None

        best_dt = inf

        for job_id, dt in offsets.items():

            if dt < best_dt:

                best_job_id = job_id

                best_dt = dt

            elif isclose(dt, best_dt, abs_tol=1e-12) and best_job_id is not None:

                if job_id < best_job_id:

                    best_job_id = job_id

        return best_job_id, best_dt

    def completed_jobs(self, tol: float = 1e-12) -> list[int]:

        result: list[int] = []

        for job_id, job in self.active_jobs.items():

            if job.is_completed(tol=tol):

                result.append(job_id)

        return sorted(result)

    def short_summary(self) -> str:

        return (

            f"SystemState(t={self.current_time:.6f}, "

            f"k={self.num_jobs}, "

            f"occupied_resource={self.occupied_resource}, "

            f"next_job_id={self.next_job_id})"

        )

    def pretty_print(self) -> None:

        print("=" * 80)

        print(self.short_summary())

        print("-" * 80)

        if not self.active_jobs:

            print("Активных заявок нет.")

        else:

            print("Активные заявки:")

            for job in sorted(self.active_jobs.values(), key=lambda x: x.job_id):

                print(

                    f"  job_id={job.job_id:>3} | "

                    f"arrival={job.arrival_time:>8.4f} | "

                    f"resource={job.resource_demand:>2} | "

                    f"total_work={job.total_workload:>8.4f} | "

                    f"remaining={job.remaining_workload:>8.4f}"

                )

        print("=" * 80)

        print()

def _self_test() -> None:

    workloads = standard_workload_family(mean=1.0)

    scenario = build_base_scenario(workloads["exponential"], name_suffix="_model_self_test")

    print("\nSELF-TEST model.py\n")

    print("Используемый сценарий:")

    print(scenario.short_description())

    print()

    state = SystemState()

    print("Шаг 1. Пустое состояние.")

    state.pretty_print()

    print("Шаг 2. Добавляем первую заявку.")

    job_1 = state.create_job(resource_demand=2, workload=1.5)

    decision_1 = state.can_accept(job_1.resource_demand, scenario)

    print(f"Решение о допуске job_1: accepted={decision_1.accepted}, reason={decision_1.reason.value}")

    state.add_job(job_1, scenario)

    state.pretty_print()

    print("Шаг 3. Добавляем вторую заявку.")

    job_2 = state.create_job(resource_demand=3, workload=0.8)

    decision_2 = state.can_accept(job_2.resource_demand, scenario)

    print(f"Решение о допуске job_2: accepted={decision_2.accepted}, reason={decision_2.reason.value}")

    state.add_job(job_2, scenario)

    state.pretty_print()

    print("Шаг 4. Вычисляем ближайшее завершение.")

    next_job_id, next_dt = state.next_completion(scenario)

    print(f"Ближайшее завершение: job_id={next_job_id}, через dt={next_dt:.6f}\n")

    print("Шаг 5. Продвигаем время до ближайшего завершения.")

    state.advance_time_and_service(next_dt, scenario)

    state.pretty_print()

    completed = state.completed_jobs()

    print(f"Завершившиеся заявки после продвижения времени: {completed}\n")

    print("Шаг 6. Удаляем завершившиеся заявки.")

    for job_id in completed:

        removed = state.remove_job(job_id)

        print(

            f"Удалена заявка job_id={removed.job_id}, "

            f"время поступления={removed.arrival_time:.4f}, "

            f"остаток={removed.remaining_workload:.6f}"

        )

    state.pretty_print()

    print("Шаг 7. Проверяем логику отказа по ресурсу.")

    oversized_resource = scenario.total_resource_r + 1

    decision_3 = state.can_accept(oversized_resource, scenario)

    print(

        f"Решение о допуске слишком большой заявки: "

        f"accepted={decision_3.accepted}, reason={decision_3.reason.value}"

    )

    print()

    print("SELF-TEST model.py завершён успешно.")

if __name__ == "__main__":

    _self_test()
