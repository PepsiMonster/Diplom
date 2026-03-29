"""
Этот файлик хранит:
1. параметры запуска симуляции;
2. параметры распределения ресурсных требований;
3. параметры распределения объёма работы;
4. полную конфигурацию сценария;
5. несколько готовых фабрик для базовых сценариев.


Поддерживаются:
- одно-ресурсная loss-система;
- state-dependent профиль входа lambda_k;
- state-dependent профиль скорости обслуживания sigma_k;
- несколько распределений объёма работы с одинаковым средним для анализа чувствительности к старшим моментам.

Допущения на данный момент:
- у каждой заявки есть остаточный объём работы;
- в состоянии k каждая активная заявка убывает со скоростью sigma_k.

Если потребуется, файл можно будет потом расширить.

На будущее попробовать сразу:
уменьшить K,
уменьшить N,
уменьшить R,
увеличить средний объём работы,
усилить падение sigma_k.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class SimulationConfig:
    """
    Параметры одного прогона или серии прогонов.

    Поля:
    -----
    max_time:
        Полное время моделирования.
    warmup_time:
        Длина разгона. Статистика до этого момента не учитывается.
    seed:
        Базовый seed генератора случайных чисел.
    replications:
        Число независимых повторов одного сценария.
    time_epsilon:
        Малый численный допуск для сравнения моментов времени.
    record_state_trace:
        Сохранять ли снимки состояния для отладки.
    save_event_log:
        Сохранять ли журнал событий для отладки.
    """

    max_time: float = 100_000.0
    warmup_time: float = 10_000.0
    seed: int = 42
    replications: int = 10
    time_epsilon: float = 1e-12
    record_state_trace: bool = False
    save_event_log: bool = False

    def validate(self) -> None:
        if self.max_time <= 0:
            raise ValueError("max_time должен быть > 0")
        if self.warmup_time < 0:
            raise ValueError("warmup_time должен быть >= 0")
        if self.warmup_time >= self.max_time:
            raise ValueError("warmup_time должен быть меньше max_time")
        if self.replications <= 0:
            raise ValueError("replications должен быть > 0")
        if self.time_epsilon <= 0:
            raise ValueError("time_epsilon должен быть > 0")


@dataclass(slots=True)
class ResourceDistributionConfig:
    """
    Конфигурация распределения требований заявки к ресурсу.

    Поддерживаются два варианта:
    - deterministic
    - discrete_uniform
    """
    kind: str
    deterministic_value: Optional[int] = None
    min_units: Optional[int] = None
    max_units: Optional[int] = None

    def validate(self) -> None:
        """
        Валидируем, чтобы избежать ошибок т.к. первый файл в цепочке
        """
        if self.kind not in {"deterministic", "discrete_uniform"}:
            raise ValueError("Поддерживаются только deterministic и discrete_uniform")

        if self.kind == "deterministic":
            if self.deterministic_value is None or self.deterministic_value <= 0:
                raise ValueError("Для deterministic нужен deterministic_value > 0")

        if self.kind == "discrete_uniform":
            if self.min_units is None or self.max_units is None:
                raise ValueError("Для discrete_uniform нужны min_units и max_units")
            if self.min_units <= 0 or self.max_units <= 0:
                raise ValueError("min_units и max_units должны быть > 0")
            if self.min_units > self.max_units:
                raise ValueError("min_units не может быть больше max_units")

    def mean(self) -> float:
        self.validate()

        if self.kind == "deterministic":
            return float(self.deterministic_value)

        return 0.5 * (self.min_units + self.max_units)

    def short_label(self) -> str:
        if self.kind == "deterministic":
            return f"Det({self.deterministic_value})"
        return f"DU({self.min_units},{self.max_units})"

# Распределение обхема работы

@dataclass(slots=True)
class WorkloadDistributionConfig:
    """
    Конфигурация распределения объёма работы заявки, например:
    - deterministic
    - exponential
    - erlang
    - hyperexponential2

    Здесь задаётся именно объём работы заявки, а не готовое время обслуживания.
    Затем этот объём уменьшается со скоростью sigma_k.
    """
    kind: str
    mean: float
    label: str
    erlang_order: Optional[int] = None
    hyper_p: Optional[float] = None
    hyper_rates: Optional[tuple[float, float]] = None

    def validate(self) -> None:
        if self.kind not in {"deterministic", "exponential", "erlang", "hyperexponential2"}:
            raise ValueError("Неподдерживаемый kind для WorkloadDistributionConfig")

        if self.mean <= 0:
            raise ValueError("mean должен быть > 0")

        if self.kind == "erlang":
            if self.erlang_order is None or self.erlang_order <= 0:
                raise ValueError("Для erlang нужен erlang_order > 0")

        if self.kind == "hyperexponential2":
            if self.hyper_p is None or not (0.0 < self.hyper_p < 1.0):
                raise ValueError("Для hyperexponential2 нужен hyper_p из интервала (0, 1)")
            if self.hyper_rates is None or len(self.hyper_rates) != 2:
                raise ValueError("Для hyperexponential2 нужен кортеж hyper_rates длины 2")
            if self.hyper_rates[0] <= 0 or self.hyper_rates[1] <= 0:
                raise ValueError("Обе интенсивности hyper_rates должны быть > 0")

# Классы для разных распределений

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
        """
        Строит двухфазное гиперэкспоненциальное распределение с заданным средним.
        """
        if mean <= 0:
            raise ValueError("mean должен быть > 0")
        if not (0.0 < p < 1.0):
            raise ValueError("p должен лежать в интервале (0, 1)")
        if fast_rate_multiplier <= 0:
            raise ValueError("fast_rate_multiplier должен быть > 0")

        rate_1 = fast_rate_multiplier / mean
        denominator = mean - p / rate_1
        if denominator <= 0:
            raise ValueError("Некорректные параметры для hyperexponential2")

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

# Полноценная конфигурация сценария

@dataclass(slots=True)
class ScenarioConfig:
    """
    Полная конфигурация одного сценария.
    name:
        Имя сценария.
    capacity_k:
        Максимальное число заявок в системе.
    servers_n:
        Число обслуживающих приборов.
    total_resource_r:
        Общий доступный ресурс.
    arrival_rate_by_state:
        Профиль lambda_k, k = 0, ..., K.
    service_speed_by_state:
        Профиль sigma_k, k = 0, ..., K.
    resource_distribution:
        Закон распределения ресурса на заявку.
    workload_distribution:
        Закон распределения объёма работы на заявку.
    simulation:
        Параметры запуска имитации.
    """
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

    def validate(self) -> None: # В финальном варианте планируется сделать валидацию значений более универсально
        if self.capacity_k <= 0:
            raise ValueError("capacity_k должен быть > 0")
        if self.servers_n <= 0:
            raise ValueError("servers_n должен быть > 0")
        if self.total_resource_r <= 0:
            raise ValueError("total_resource_r должен быть > 0")
        if self.capacity_k < self.servers_n:
            raise ValueError("Ожидается capacity_k >= servers_n")

        expected_len = self.capacity_k + 1
        if len(self.arrival_rate_by_state) != expected_len:
            raise ValueError("arrival_rate_by_state должен иметь длину K + 1")
        if len(self.service_speed_by_state) != expected_len:
            raise ValueError("service_speed_by_state должен иметь длину K + 1")

        if any(x < 0 for x in self.arrival_rate_by_state):
            raise ValueError("Все arrival_rate_by_state должны быть >= 0")
        if any(x < 0 for x in self.service_speed_by_state):
            raise ValueError("Все service_speed_by_state должны быть >= 0")

        self.resource_distribution.validate()
        self.workload_distribution.validate()
        self.simulation.validate()

    def short_description(self) -> str:
        return (
            f"Scenario(name='{self.name}', "
            f"K={self.capacity_k}, N={self.servers_n}, R={self.total_resource_r}, "
            f"work='{self.workload_distribution.short_label()}')"
        )

# Базовые профили lambda_k И sigma_k

def build_base_arrival_profile(capacity_k: int) -> tuple[float, ...]:
    """
    Базовый профиль lambda_k.

    Пока система не слишком загружена, входной поток выше.
    После порога интенсивность падает.
    В полном состоянии k = K принимаем lambda_K = 0.
    """
    if capacity_k <= 0:
        raise ValueError("capacity_k должен быть > 0")

    threshold_k = max(1, capacity_k - 3)
    values: list[float] = []

    for k in range(capacity_k + 1):
        if k < threshold_k:
            values.append(1.80)
        else:
            values.append(1.10)

    values[-1] = 0.0
    return tuple(values)


def build_base_service_profile(capacity_k: int) -> tuple[float, ...]:
    """
    Базовый профиль sigma_k.

    Скорость убывает по мере роста числа заявок.
    Это отражает эффект конкуренции за вычислительный ресурс.
    """
    if capacity_k <= 0:
        raise ValueError("capacity_k должен быть > 0")

    values = []
    for k in range(capacity_k + 1):
        sigma_k = max(1.15 - 0.07 * k, 0.45)
        values.append(sigma_k)

    return tuple(values)

# Типовые распределения для анализа чувствительности

def standard_workload_family(mean: float) -> dict[str, WorkloadDistributionConfig]:
    """
    Стандартное семейство распределений объёма работы с одинаковым средним.

    Набор достаточен для первого анализа чувствительности:
    - deterministic
    - exponential
    - erlang_2
    - erlang_4
    - hyperexp_2
    """
    if mean <= 0:
        raise ValueError("mean должен быть > 0")

    return {
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

# Базовый сценарий

def build_base_scenario(workload_distribution: WorkloadDistributionConfig,*,name_suffix: str = "",
                        ) -> ScenarioConfig:
    """
    Собираем базовый сценарий и фиксируем:
    - K = 8;
    - N = 6;
    - R = 12;
    - простой закон требований к ресурсу;
    - базовые профили lambda_k и sigma_k.

    Меняется только распределение объёма работы.
    """
    capacity_k = 8
    servers_n = 6
    total_resource_r = 12

    scenario = ScenarioConfig(
        name=f"base{name_suffix}",
        capacity_k=capacity_k,
        servers_n=servers_n,
        total_resource_r=total_resource_r,
        arrival_rate_by_state=build_base_arrival_profile(capacity_k),
        service_speed_by_state=build_base_service_profile(capacity_k),
        resource_distribution=ResourceDistributionConfig(
            kind="discrete_uniform",
            min_units=1,
            max_units=3,
        ),
        workload_distribution=workload_distribution,
        simulation=SimulationConfig(),
        note="Базовый сценарий для анализа чувствительности.",
    )
    scenario.validate()
    return scenario


# Минимальный самотест

if __name__ == "__main__":
    family = standard_workload_family(mean=1.0)
    scenario = build_base_scenario(family["exponential"], name_suffix="_test")
    print(scenario.short_description())
    print("lambda_k:", scenario.arrival_rate_by_state)
    print("sigma_k:", scenario.service_speed_by_state)
