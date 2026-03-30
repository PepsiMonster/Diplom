from __future__ import annotations

from dataclasses import dataclass, field, replace

from math import inf, isclose

from typing import Optional

import numpy as np

from params import (

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

    rejected_resource: int

    completed_jobs: int

    loss_probability: float

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

            summary[f"pi_hat_{k}"] = value

        return summary

def _derive_run_seed(base_seed: int, replication_index: int) -> int:

    if replication_index < 0:

        raise ValueError(f"replication_index должен быть >= 0, получено: {replication_index}")

    return int(base_seed + 1_000_003 * replication_index)

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

        return float(rng.exponential(scale=1.0 / rate_2))

    raise ValueError(f"Неподдерживаемый kind='{config.kind}' для workload distribution")

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

    rejected_resource: int = 0

    completed_jobs: int = 0

    def __post_init__(self) -> None:

        if self.capacity_k <= 0:

            raise ValueError(f"capacity_k должен быть > 0, получено: {self.capacity_k}")

        if self.total_time <= 0:

            raise ValueError(f"total_time должен быть > 0, получено: {self.total_time}")

        if self.warmup_time < 0:

            raise ValueError(f"warmup_time должен быть >= 0, получено: {self.warmup_time}")

        self.state_times = [0.0 for _ in range(self.capacity_k + 1)]

    @property

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

            return

        self.rejected_arrivals += 1

        if reason == RejectionReason.CAPACITY_LIMIT:

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

            loss_probability = 0.0

        throughput = self.completed_jobs / observed_time

        return SimulationRunResult(

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

        occupied_resource_before = self.state.occupied_resource

        resource_demand, workload = self._sample_new_job_parameters()

        self.stats.register_arrival_attempt(self.state.current_time)

        decision: AdmissionDecision = self.state.can_accept(resource_demand, self.scenario)

        if decision.accepted:

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

            )

        self._record_state_snapshot()

    def _process_departures(self) -> None:

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

            )

        self._record_state_snapshot()

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

    print()

    print("SELF-TEST simulation.py завершён успешно.")

if __name__ == "__main__":

    _self_test()
