from __future__ import annotations

from dataclasses import dataclass, field

from typing import Optional

def _ensure_positive(name: str, value: float | int) -> None:

    if value <= 0:

        raise ValueError(f"Параметр '{name}' должен быть > 0, получено: {value}")

def _ensure_nonnegative(name: str, value: float | int) -> None:

    if value < 0:

        raise ValueError(f"Параметр '{name}' должен быть >= 0, получено: {value}")

def _ensure_probability(name: str, value: float) -> None:

    if not (0.0 < value < 1.0):

        raise ValueError(f"Параметр '{name}' должен лежать в интервале (0, 1), получено: {value}")

def _ensure_tuple_length(name: str, values: tuple[float, ...], expected: int) -> None:

    if len(values) != expected:

        raise ValueError(

            f"Параметр '{name}' должен иметь длину {expected}, "

            f"получено {len(values)}"

        )

def _ensure_probabilities_sum_to_one(name: str, probs: tuple[float, ...], tol: float = 1e-10) -> None:

    total = sum(probs)

    if abs(total - 1.0) > tol:

        raise ValueError(

            f"Сумма вероятностей '{name}' должна быть равна 1.0, "

            f"сейчас это {total}"

        )

@dataclass(slots=True)

class SimulationConfig:

    max_time: float = 100_000.0

    warmup_time: float = 10_000.0

    seed: int = 42

    replications: int = 10

    time_epsilon: float = 1e-12

    record_state_trace: bool = False

    save_event_log: bool = False

    def validate(self) -> None:

        _ensure_positive("max_time", self.max_time)

        _ensure_nonnegative("warmup_time", self.warmup_time)

        _ensure_positive("replications", self.replications)

        _ensure_positive("time_epsilon", self.time_epsilon)

        if self.warmup_time >= self.max_time:

            raise ValueError(

                "warmup_time должен быть строго меньше max_time, "

                f"получено warmup_time={self.warmup_time}, max_time={self.max_time}"

            )

    def effective_observation_time(self) -> float:

        return self.max_time - self.warmup_time

@dataclass(slots=True)

class ResourceDistributionConfig:

    kind: str

    deterministic_value: Optional[int] = None

    min_units: Optional[int] = None

    max_units: Optional[int] = None

    values: tuple[int, ...] = ()

    probabilities: tuple[float, ...] = ()

    def validate(self) -> None:

        supported_kinds = {"deterministic", "discrete_uniform", "discrete_custom"}

        if self.kind not in supported_kinds:

            raise ValueError(

                f"Неподдерживаемый kind='{self.kind}' для ResourceDistributionConfig. "

                f"Поддерживаются: {sorted(supported_kinds)}"

            )

        if self.kind == "deterministic":

            if self.deterministic_value is None:

                raise ValueError("Для deterministic нужно задать deterministic_value")

            _ensure_positive("deterministic_value", self.deterministic_value)

        elif self.kind == "discrete_uniform":

            if self.min_units is None or self.max_units is None:

                raise ValueError("Для discrete_uniform нужно задать min_units и max_units")

            _ensure_positive("min_units", self.min_units)

            _ensure_positive("max_units", self.max_units)

            if self.min_units > self.max_units:

                raise ValueError("min_units не может быть больше max_units")

        elif self.kind == "discrete_custom":

            if not self.values:

                raise ValueError("Для discrete_custom нужно задать values")

            if not self.probabilities:

                raise ValueError("Для discrete_custom нужно задать probabilities")

            if len(self.values) != len(self.probabilities):

                raise ValueError("Длины values и probabilities должны совпадать")

            for index, value in enumerate(self.values):

                _ensure_positive(f"values[{index}]", value)

            for index, prob in enumerate(self.probabilities):

                _ensure_probability(f"probabilities[{index}]", prob)

            _ensure_probabilities_sum_to_one("probabilities", self.probabilities)

    def mean(self) -> float:

        self.validate()

        if self.kind == "deterministic":

            assert self.deterministic_value is not None

            return float(self.deterministic_value)

        if self.kind == "discrete_uniform":

            assert self.min_units is not None and self.max_units is not None

            return 0.5 * (self.min_units + self.max_units)

        return sum(value * prob for value, prob in zip(self.values, self.probabilities))

    def short_label(self) -> str:

        if self.kind == "deterministic":

            return f"ResourceDet({self.deterministic_value})"

        if self.kind == "discrete_uniform":

            return f"ResourceDU({self.min_units},{self.max_units})"

        return "ResourceCustom"

@dataclass(slots=True)

class WorkloadDistributionConfig:

    kind: str

    mean: float

    label: str

    erlang_order: Optional[int] = None

    hyper_p: Optional[float] = None

    hyper_rates: Optional[tuple[float, float]] = None

    def validate(self) -> None:

        supported_kinds = {

            "deterministic",

            "exponential",

            "erlang",

            "hyperexponential2",

        }

        if self.kind not in supported_kinds:

            raise ValueError(

                f"Неподдерживаемый kind='{self.kind}' для WorkloadDistributionConfig. "

                f"Поддерживаются: {sorted(supported_kinds)}"

            )

        _ensure_positive("mean", self.mean)

        if self.kind == "erlang":

            if self.erlang_order is None:

                raise ValueError("Для erlang нужно задать erlang_order")

            _ensure_positive("erlang_order", self.erlang_order)

        if self.kind == "hyperexponential2":

            if self.hyper_p is None:

                raise ValueError("Для hyperexponential2 нужно задать hyper_p")

            if self.hyper_rates is None:

                raise ValueError("Для hyperexponential2 нужно задать hyper_rates")

            _ensure_probability("hyper_p", self.hyper_p)

            if len(self.hyper_rates) != 2:

                raise ValueError("Для hyperexponential2 hyper_rates должен содержать 2 интенсивности")

            _ensure_positive("hyper_rates[0]", self.hyper_rates[0])

            _ensure_positive("hyper_rates[1]", self.hyper_rates[1])

            implied_mean = self.implied_mean()

            if abs(implied_mean - self.mean) > 1e-9:

                raise ValueError(

                    "Параметры hyperexponential2 неконсистентны: "

                    f"заданное mean={self.mean}, а из параметров смеси получается {implied_mean}"

                )

    def implied_mean(self) -> float:

        if self.kind in {"deterministic", "exponential", "erlang"}:

            return self.mean

        assert self.hyper_p is not None

        assert self.hyper_rates is not None

        rate_1, rate_2 = self.hyper_rates

        return self.hyper_p / rate_1 + (1.0 - self.hyper_p) / rate_2

    @classmethod

    def deterministic(cls, mean: float, label: str = "Deterministic") -> "WorkloadDistributionConfig":

        cfg = cls(kind="deterministic", mean=mean, label=label)

        cfg.validate()

        return cfg

    @classmethod

    def exponential(cls, mean: float, label: str = "Exponential") -> "WorkloadDistributionConfig":

        cfg = cls(kind="exponential", mean=mean, label=label)

        cfg.validate()

        return cfg

    @classmethod

    def erlang(cls, mean: float, order: int, label: Optional[str] = None) -> "WorkloadDistributionConfig":

        cfg = cls(

            kind="erlang",

            mean=mean,

            label=label or f"Erlang({order})",

            erlang_order=order,

        )

        cfg.validate()

        return cfg

    @classmethod

    def hyperexponential2(

        cls,

        mean: float,

        p: float = 0.75,

        fast_rate_multiplier: float = 4.0,

        label: str = "HyperExp(2)",

    ) -> "WorkloadDistributionConfig":

        _ensure_positive("mean", mean)

        _ensure_probability("p", p)

        _ensure_positive("fast_rate_multiplier", fast_rate_multiplier)

        rate_1 = fast_rate_multiplier / mean

        denominator = mean - p / rate_1

        if denominator <= 0:

            raise ValueError(

                "Не удалось построить hyperexponential2: выбранные p и fast_rate_multiplier "

                "дают некорректную вторую интенсивность. "

                "Попробуй увеличить fast_rate_multiplier."

            )

        rate_2 = (1.0 - p) / denominator

        cfg = cls(

            kind="hyperexponential2",

            mean=mean,

            label=label,

            hyper_p=p,

            hyper_rates=(rate_1, rate_2),

        )

        cfg.validate()

        return cfg

    def short_label(self) -> str:

        return self.label.replace(" ", "_")

@dataclass(slots=True)

class ScenarioConfig:

    name: str

    capacity_k: int

    servers_n: int

    total_resource_r: int

    arrival_rate_by_state: tuple[float, ...]

    service_speed_by_state: tuple[float, ...]

    resource_distribution: ResourceDistributionConfig

    workload_distribution: WorkloadDistributionConfig

    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    note: str = ""

    def validate(self) -> None:

        _ensure_positive("capacity_k", self.capacity_k)

        _ensure_positive("servers_n", self.servers_n)

        _ensure_positive("total_resource_r", self.total_resource_r)

        expected_len = self.capacity_k + 1

        _ensure_tuple_length("arrival_rate_by_state", self.arrival_rate_by_state, expected_len)

        _ensure_tuple_length("service_speed_by_state", self.service_speed_by_state, expected_len)

        for k, value in enumerate(self.arrival_rate_by_state):

            _ensure_nonnegative(f"arrival_rate_by_state[{k}]", value)

        for k, value in enumerate(self.service_speed_by_state):

            _ensure_nonnegative(f"service_speed_by_state[{k}]", value)

        self.resource_distribution.validate()

        self.workload_distribution.validate()

        self.simulation.validate()

        if self.capacity_k < self.servers_n:

            raise ValueError(

                "Обычно capacity_k должен быть >= servers_n. "

                f"Сейчас capacity_k={self.capacity_k}, servers_n={self.servers_n}"

            )

        if self.resource_distribution.kind == "deterministic":

            assert self.resource_distribution.deterministic_value is not None

            if self.resource_distribution.deterministic_value > self.total_resource_r:

                raise ValueError(

                    "Даже минимально возможное требование к ресурсу "

                    "превышает total_resource_r: система не сможет принять ни одной заявки."

                )

        if self.resource_distribution.kind == "discrete_uniform":

            assert self.resource_distribution.min_units is not None

            if self.resource_distribution.min_units > self.total_resource_r:

                raise ValueError(

                    "Даже минимально возможное требование к ресурсу "

                    "превышает total_resource_r: система не сможет принять ни одной заявки."

                )

        if self.resource_distribution.kind == "discrete_custom":

            if min(self.resource_distribution.values) > self.total_resource_r:

                raise ValueError(

                    "Даже минимально возможное требование к ресурсу "

                    "превышает total_resource_r: система не сможет принять ни одной заявки."

                )

    def short_description(self) -> str:

        lambda_full = self.arrival_rate_by_state[-1]

        warning = ""

        if lambda_full != 0.0:

            warning = " [ВНИМАНИЕ: lambda_K != 0]"

        return (

            f"Scenario(name='{self.name}', "

            f"K={self.capacity_k}, N={self.servers_n}, R={self.total_resource_r}, "

            f"resource='{self.resource_distribution.short_label()}', "

            f"work='{self.workload_distribution.short_label()}', "

            f"replications={self.simulation.replications}){warning}"

        )

def constant_profile(capacity_k: int, value: float, last_value: Optional[float] = None) -> tuple[float, ...]:

    _ensure_positive("capacity_k", capacity_k)

    _ensure_nonnegative("value", value)

    values = [value] * (capacity_k + 1)

    if last_value is not None:

        _ensure_nonnegative("last_value", last_value)

        values[-1] = last_value

    return tuple(values)

def threshold_profile(

    capacity_k: int,

    normal_value: float,

    threshold_k: int,

    reduced_value: float,

    full_state_value: float = 0.0,

) -> tuple[float, ...]:

    _ensure_positive("capacity_k", capacity_k)

    _ensure_nonnegative("normal_value", normal_value)

    _ensure_nonnegative("reduced_value", reduced_value)

    _ensure_nonnegative("full_state_value", full_state_value)

    if not (0 <= threshold_k <= capacity_k):

        raise ValueError(

            f"threshold_k должен лежать в диапазоне [0, {capacity_k}], получено: {threshold_k}"

        )

    profile = []

    for k in range(capacity_k + 1):

        if k < threshold_k:

            profile.append(normal_value)

        else:

            profile.append(reduced_value)

    profile[-1] = full_state_value

    return tuple(profile)

def linear_decreasing_profile(

    capacity_k: int,

    start_value: float,

    step: float,

    floor_value: float = 0.0,

) -> tuple[float, ...]:

    _ensure_positive("capacity_k", capacity_k)

    _ensure_nonnegative("start_value", start_value)

    _ensure_nonnegative("step", step)

    _ensure_nonnegative("floor_value", floor_value)

    return tuple(max(start_value - step * k, floor_value) for k in range(capacity_k + 1))

def standard_workload_family(mean: float) -> dict[str, WorkloadDistributionConfig]:

    _ensure_positive("mean", mean)

    family = {

        "deterministic": WorkloadDistributionConfig.deterministic(mean, label="Deterministic"),

        "exponential": WorkloadDistributionConfig.exponential(mean, label="Exponential"),

        "erlang_2": WorkloadDistributionConfig.erlang(mean, order=2, label="Erlang(2)"),

        "erlang_4": WorkloadDistributionConfig.erlang(mean, order=4, label="Erlang(4)"),

        "hyperexp_2": WorkloadDistributionConfig.hyperexponential2(

            mean,

            p=0.75,

            fast_rate_multiplier=4.0,

            label="HyperExp(2)",

        ),

    }

    return family

def build_base_simulation_config() -> SimulationConfig:

    cfg = SimulationConfig(

        max_time=100_000.0,

        warmup_time=10_000.0,

        seed=42,

        replications=10,

        time_epsilon=1e-12,

        record_state_trace=False,

        save_event_log=False,

    )

    cfg.validate()

    return cfg

def build_base_resource_distribution() -> ResourceDistributionConfig:

    cfg = ResourceDistributionConfig(

        kind="discrete_uniform",

        min_units=1,

        max_units=3,

    )

    cfg.validate()

    return cfg

def build_base_arrival_profile(capacity_k: int) -> tuple[float, ...]:

    return threshold_profile(

        capacity_k=capacity_k,

        normal_value=1.80,

        threshold_k=max(1, capacity_k - 3),

        reduced_value=1.10,

        full_state_value=0.0,

    )

def build_base_service_profile(capacity_k: int) -> tuple[float, ...]:

    return linear_decreasing_profile(

        capacity_k=capacity_k,

        start_value=1.20,

        step=0.04,

        floor_value=0.60,

    )

def build_base_scenario(

    workload_distribution: WorkloadDistributionConfig,

    *,

    name_suffix: str = "",

) -> ScenarioConfig:

    capacity_k = 10

    servers_n = 10

    total_resource_r = 20

    scenario = ScenarioConfig(

        name=f"base{name_suffix}",

        capacity_k=capacity_k,

        servers_n=servers_n,

        total_resource_r=total_resource_r,

        arrival_rate_by_state=build_base_arrival_profile(capacity_k),

        service_speed_by_state=build_base_service_profile(capacity_k),

        resource_distribution=build_base_resource_distribution(),

        workload_distribution=workload_distribution,

        simulation=build_base_simulation_config(),

        note=(

            "Базовый сценарий для сравнения распределений объёма работы "

            "при фиксированных K, N, R, lambda_k и sigma_k."

        ),

    )

    scenario.validate()

    return scenario

def build_sensitivity_scenarios(mean_workload: float = 1.0) -> dict[str, ScenarioConfig]:

    family = standard_workload_family(mean_workload)

    scenarios: dict[str, ScenarioConfig] = {}

    for key, workload_cfg in family.items():

        scenario = build_base_scenario(

            workload_distribution=workload_cfg,

            name_suffix=f"_{key}",

        )

        scenarios[key] = scenario

    return scenarios

def print_scenario_summary(scenario: ScenarioConfig) -> None:

    scenario.validate()

    print("=" * 80)

    print(f"СЦЕНАРИЙ: {scenario.name}")

    print("-" * 80)

    print(f"K (ёмкость системы):                  {scenario.capacity_k}")

    print(f"N (число приборов):                  {scenario.servers_n}")

    print(f"R (общий ресурс):                    {scenario.total_resource_r}")

    print(f"Распределение ресурса:               {scenario.resource_distribution.short_label()}")

    print(f"Среднее требование к ресурсу:        {scenario.resource_distribution.mean():.4f}")

    print(f"Распределение объёма работы:         {scenario.workload_distribution.label}")

    print(f"Средний объём работы:                {scenario.workload_distribution.mean:.4f}")

    print(f"Время моделирования:                 {scenario.simulation.max_time}")

    print(f"Warm-up:                             {scenario.simulation.warmup_time}")

    print(f"Эффективное время наблюдения:        {scenario.simulation.effective_observation_time()}")

    print(f"Число повторов:                      {scenario.simulation.replications}")

    print(f"Seed:                                {scenario.simulation.seed}")

    print(f"Комментарий:                         {scenario.note}")

    print("-" * 80)

    print("Профиль lambda_k:")

    print("  ", scenario.arrival_rate_by_state)

    print("Профиль sigma_k:")

    print("  ", scenario.service_speed_by_state)

    print("=" * 80)

    print()

def _self_test() -> None:

    scenarios = build_sensitivity_scenarios(mean_workload=1.0)

    print("\nПроверка params.py: построение типовых сценариев завершено.\n")

    print(f"Собрано сценариев: {len(scenarios)}\n")

    for scenario in scenarios.values():

        print_scenario_summary(scenario)

    print("Самотест params.py завершён успешно.")

    def validate(self) -> None:

        supported_kinds = {"deterministic", "discrete_uniform", "discrete_custom"}

        if self.kind not in supported_kinds:

            raise ValueError(

                f"Неподдерживаемый kind='{self.kind}' для ResourceDistributionConfig. "

                f"Поддерживаются: {sorted(supported_kinds)}"

            )

        if self.kind == "deterministic":

            if self.deterministic_value is None:

                raise ValueError("Для deterministic нужно задать deterministic_value")

            _ensure_positive("deterministic_value", self.deterministic_value)

        elif self.kind == "discrete_uniform":

            if self.min_units is None or self.max_units is None:

                raise ValueError("Для discrete_uniform нужно задать min_units и max_units")

            _ensure_positive("min_units", self.min_units)

            _ensure_positive("max_units", self.max_units)

            if self.min_units > self.max_units:

                raise ValueError("min_units не может быть больше max_units")

        elif self.kind == "discrete_custom":

            if not self.values:

                raise ValueError("Для discrete_custom нужно задать values")

            if not self.probabilities:

                raise ValueError("Для discrete_custom нужно задать probabilities")

            if len(self.values) != len(self.probabilities):

                raise ValueError("Длины values и probabilities должны совпадать")

            for index, value in enumerate(self.values):

                _ensure_positive(f"values[{index}]", value)

            for index, prob in enumerate(self.probabilities):

                _ensure_probability(f"probabilities[{index}]", prob)

            _ensure_probabilities_sum_to_one("probabilities", self.probabilities)

if __name__ == "__main__":

    _self_test()
