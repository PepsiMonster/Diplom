<<<<<<< HEAD
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

=======
# параметры экспериментов
"""
Централизованное описание параметров для имитационной модели системы
массового обслуживания с ограниченными ресурсами и зависящими от состояния
характеристиками поступления и обслуживания.

Что моделируется

Мы рассматриваем систему, в которой:

1. В систему поступают заявки.
2. Интенсивность поступления зависит от текущего состояния системы:
   если в системе сейчас k заявок, то используется интенсивность lambda_k.
3. Каждая заявка:
   - требует некоторое количество ресурса;
   - имеет некоторый объём работы.
4. В системе есть:
   - ограничение на число одновременно находящихся заявок;
   - ограничение на суммарный доступный ресурс.
5. Скорость "выработки" объёма работы зависит от текущего состояния:
   если в системе k заявок, то остатки работ убывают со скоростью sigma_k.
6. Если новая заявка не помещается по числу мест или по ресурсу, она теряется.

Этот файл:
- хранит параметры сценариев;
- проверяет, что параметры заданы корректно;
- предоставляет фабрики для типовых профилей lambda_k и sigma_k;
- предоставляет типовые семейства распределений обслуживания
  с одинаковым средним для анализа чувствительности к старшим моментам.


Файлик работает отдельно и:
- покажет seed наших случайных параметров;
- соберёт несколько готовых сценариев;
- проверит их;
- выведет сводку в консоль.
"""

from __future__ import annotations 
from dataclasses import dataclass, field 
from typing import Optional 

# Эти функции нужны для единообразной проверки входных данных.
# Мы специально выносим их отдельно, чтобы:
# 1) не дублировать одинаковые проверки в разных dataclass'ах;
# 2) получать понятные сообщения об ошибках;
# 3) не тратить время позже на поиск "странных" параметров.



def _ensure_positive(name: str, value: float | int) -> None: # Минимизация ошибок со старта
    """
    Проверяет, что значение строго положительно.

    Используется для:
    - среднего времени / объёма работы;
    - времени симуляции;
    - числа серверов;
    - объёма ресурса;
    - положительных скоростей и интенсивностей там, где это необходимо.

    Если проверка не проходит, бросаем ValueError с понятным сообщением.
    """
    if value <= 0:
        raise ValueError(f"Параметр '{name}' должен быть > 0, получено: {value}")


def _ensure_nonnegative(name: str, value: float | int) -> None: # Минимизация ошибок со старта
    """
    Проверяет, что значение неотрицательно.

    Используется там, где ноль допустим:
    - интенсивность прихода в состоянии полной системы;
    - скорость обслуживания в крайних моделях;
    - warmup_time и т.п.
    """
    if value < 0:
        raise ValueError(f"Параметр '{name}' должен быть >= 0, получено: {value}")


def _ensure_probability(name: str, value: float) -> None: 
    """
    Проверяет, что число лежит в интервале (0, 1).

    Нам нужен именно открытый интервал, потому что вероятность ветви
    в гиперэкспоненциальной смеси не должна быть ни 0, ни 1:
    иначе смесь вырождается и теряет смысл:(.
    """
    if not (0.0 < value < 1.0):
        raise ValueError(f"Параметр '{name}' должен лежать в интервале (0, 1), получено: {value}") # VallueError не должен выскакивать впринципе


def _ensure_tuple_length(name: str, values: tuple[float, ...], expected: int) -> None:
    """
    Проверяет длину кортежа.

    Для профилей lambda_k и sigma_k длина должна быть ровно K + 1,
    потому что состояния системы мы индексируем как k = 0, 1, ..., K.
    """
    if len(values) != expected:
        raise ValueError(
            f"Параметр '{name}' должен иметь длину {expected}, "
            f"получено {len(values)}"
        )


def _ensure_probabilities_sum_to_one(name: str, probs: tuple[float, ...], tol: float = 1e-10) -> None:
    """
    Проверяет, что набор вероятностей суммируется в 1.
    Небольшой численный допуск нужен, чтобы не ломаться на округлениях.
    """
    total = sum(probs)
    if abs(total - 1.0) > tol:
        raise ValueError(
            f"Сумма вероятностей '{name}' должна быть равна 1.0, "
            f"сейчас это {total}"
        )


# КОНФИГУРАЦИЯ ИМИТАЦИИ
# Здесь собраны параметры, не относящиеся к самой математической модели,
# а относящиеся к технике эксперимента:
# - длина прогона;
# - разгон;
# - seed!
# - число повторов.


@dataclass(slots=True)
class SimulationConfig:

    max_time: float = 100_000.0         # Полная длина одной траектории моделирования.
    warmup_time: float = 10_000.0       # Длина начального отрезка, который НЕ используется при оценке стационарных характеристик.
                                        # Это стандартный приём для снятия влияния начального состояния.
    seed: int = 42                      # Базовое значение для генератора случайных чисел.
    replications: int = 10              # Число независимых повторов одного и того же сценария, может меняться для оценки
                                        # дов. инт. и устройчиовсти результатов
    time_epsilon: float = 1e-12         # Очень маленький численный допуск для сравнения времён событий.
    record_state_trace: bool = False    # Если True, симулятор позже сможет сохранять подробную траекторию
                                        # изменения состояния во времени. Полезно для отладки, кушает память.
    save_event_log: bool = False        # Сохраняет покомпонентный лог событий, тоже для отладки

    def validate(self) -> None:         # Проверка логической корректности параметров моделирования.

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
        """
        Возвращает длительность участка, который реально используется для оценки стационарных характеристик.
        """
        return self.max_time - self.warmup_time


# КОНФИГУРАЦИЯ РАСПРЕДЕЛЕНИЯ РЕСУРСНЫХ ТРЕБОВАНИЙ
# Сейчас нам достаточно трёх базовых вариантов:
# 1) deterministic    - всегда один и тот же объём ресурса;
# 2) discrete_uniform - равновероятные целые значения на отрезке;
# 3) discrete_custom  - пользовательский дискретный закон.
# Можно добавить новые типы при необходимости, пока так.

    """
    Описание распределения требований заявки к ресурсу.
    kind:
        Тип распределения.
        Поддерживаемые значения:
        - "deterministic"
        - "discrete_uniform"
        - "discrete_custom"
    deterministic_value:
        Значение ресурса для вырожденного распределения.
    min_units, max_units:
        Границы для равномерного дискретного распределения.
    values, probabilities:
        Поддержка и вероятности для произвольного дискретного закона.
    """
@dataclass(slots=True)
class ResourceDistributionConfig:
    """
    Описание распределения требований заявки к ресурсу.
    """

    kind: str
    deterministic_value: Optional[int] = None
    min_units: Optional[int] = None
    max_units: Optional[int] = None
    values: tuple[int, ...] = ()
    probabilities: tuple[float, ...] = ()

    def validate(self) -> None:
        """
        Проверка корректности параметров распределения ресурса.
        """
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
>>>>>>> main
                _ensure_probability(f"probabilities[{index}]", prob)

            _ensure_probabilities_sum_to_one("probabilities", self.probabilities)

    def mean(self) -> float:
<<<<<<< HEAD

        self.validate()

        if self.kind == "deterministic":

            assert self.deterministic_value is not None

            return float(self.deterministic_value)

        if self.kind == "discrete_uniform":

            assert self.min_units is not None and self.max_units is not None

=======
        """
        Возвращает математическое ожидание ресурса, потребляемого одной заявкой.
        """
        self.validate()

        if self.kind == "deterministic":
            assert self.deterministic_value is not None
            return float(self.deterministic_value)

        if self.kind == "discrete_uniform":
            assert self.min_units is not None and self.max_units is not None
>>>>>>> main
            return 0.5 * (self.min_units + self.max_units)

        return sum(value * prob for value, prob in zip(self.values, self.probabilities))

    def short_label(self) -> str:
<<<<<<< HEAD

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

=======
        """
        Короткое текстовое описание распределения.
        """
        if self.kind == "deterministic":
            return f"ResourceDet({self.deterministic_value})"
        if self.kind == "discrete_uniform":
            return f"ResourceDU({self.min_units},{self.max_units})"
        return "ResourceCustom"


# 
# КОНФИГУРАЦИЯ РАСПРЕДЕЛЕНИЯ ОБЪЁМА РАБОТЫ
# 
# Именно эта часть особенно важна для анализа чувствительности к старшим
# моментам. Мы хотим сравнивать разные распределения при одинаковом среднем.
#
# Здесь поддерживаются:
# - deterministic
# - exponential
# - erlang
# - hyperexponential2
#
# Позже можно добавить lognormal, gamma, Pareto и т.д., но для первой версии
# симулятора этого достаточно.
# 


@dataclass(slots=True)
class WorkloadDistributionConfig:
    """
    Описание распределения объёма работы заявки.

    Важное замечание:
    -
    Мы храним именно "объём работы", а не "готовое время обслуживания".
    В симуляторе позже это позволит корректно менять скорость обслуживания
    при переходах между состояниями: остаток работы будет уменьшаться со
    скоростью sigma_k.

    Поддерживаемые kind:
    ----
    - "deterministic"
    - "exponential"
    - "erlang"
    - "hyperexponential2"

    Поля:
    
    mean:
        Средний объём работы.

    erlang_order:
        Порядок Erlang-распределения.
        Используется только для kind="erlang".

    hyper_p, hyper_rates:
        Параметры двухфазного гиперэкспоненциального распределения.
        Используются только для kind="hyperexponential2".

        Интерпретация:
        - с вероятностью hyper_p берётся экспонента с rate=hyper_rates[0];
        - с вероятностью 1 - hyper_p берётся экспонента с rate=hyper_rates[1].
    """

    kind: str
    mean: float
    label: str
    erlang_order: Optional[int] = None
    hyper_p: Optional[float] = None
    hyper_rates: Optional[tuple[float, float]] = None

    def validate(self) -> None:
        """
        Проверка корректности распределения объёма работы.
        """
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
>>>>>>> main
            )

        _ensure_positive("mean", self.mean)

        if self.kind == "erlang":
<<<<<<< HEAD

            if self.erlang_order is None:

                raise ValueError("Для erlang нужно задать erlang_order")

            _ensure_positive("erlang_order", self.erlang_order)

        if self.kind == "hyperexponential2":

            if self.hyper_p is None:

                raise ValueError("Для hyperexponential2 нужно задать hyper_p")

            if self.hyper_rates is None:

=======
            if self.erlang_order is None:
                raise ValueError("Для erlang нужно задать erlang_order")
            _ensure_positive("erlang_order", self.erlang_order)

        if self.kind == "hyperexponential2":
            if self.hyper_p is None:
                raise ValueError("Для hyperexponential2 нужно задать hyper_p")
            if self.hyper_rates is None:
>>>>>>> main
                raise ValueError("Для hyperexponential2 нужно задать hyper_rates")

            _ensure_probability("hyper_p", self.hyper_p)

            if len(self.hyper_rates) != 2:
<<<<<<< HEAD

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

=======
                raise ValueError("Для hyperexponential2 hyper_rates должен содержать 2 интенсивности")

            _ensure_positive("hyper_rates[0]", self.hyper_rates[0])
            _ensure_positive("hyper_rates[1]", self.hyper_rates[1])

            # Проверяем, что среднее смеси действительно совпадает с заданным.
            implied_mean = self.implied_mean()
            if abs(implied_mean - self.mean) > 1e-9:
                raise ValueError(
                    "Параметры hyperexponential2 неконсистентны: "
                    f"заданное mean={self.mean}, а из параметров смеси получается {implied_mean}"
                )

    def implied_mean(self) -> float:
        """
        Возвращает среднее, вычисленное по внутренним параметрам распределения.

        Для deterministic/exponential mean уже задан прямо.
        Для Erlang среднее тоже задаётся напрямую.
        Для hyperexponential2 среднее вычисляется через параметры смеси.
        """
        if self.kind in {"deterministic", "exponential", "erlang"}:
            return self.mean

        assert self.hyper_p is not None
        assert self.hyper_rates is not None
        rate_1, rate_2 = self.hyper_rates
        return self.hyper_p / rate_1 + (1.0 - self.hyper_p) / rate_2

    @classmethod
    def deterministic(cls, mean: float, label: str = "Deterministic") -> "WorkloadDistributionConfig":
        """
        Фабрика для вырожденного закона: объём работы всегда равен mean.
        """
        cfg = cls(kind="deterministic", mean=mean, label=label)
        cfg.validate()
        return cfg

    @classmethod
    def exponential(cls, mean: float, label: str = "Exponential") -> "WorkloadDistributionConfig":
        """
        Фабрика для экспоненциального закона.
        """
        cfg = cls(kind="exponential", mean=mean, label=label)
        cfg.validate()
        return cfg

    @classmethod
    def erlang(cls, mean: float, order: int, label: Optional[str] = None) -> "WorkloadDistributionConfig":
        """
        Фабрика для Erlang-распределения заданного порядка.

        Важно:
        
        Здесь мы сохраняем только:
        - среднее;
        - порядок.
        А сама интенсивность стадий потом легко восстанавливается в симуляторе
        как rate = order / mean.
        """
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
        Фабрика для двухфазного гиперэкспоненциального распределения.

        Идея:
        
        Мы хотим задать смесь двух экспонент так, чтобы:
        1) среднее оставалось равным mean;
        2) дисперсия была больше, чем у экспоненциального закона.

        Как это делается:
        -
        - выбираем вероятность "быстрой" ветви p;
        - выбираем быструю интенсивность rate_1 = fast_rate_multiplier / mean;
        - из условия сохранения среднего восстанавливаем медленную интенсивность rate_2.

        Формула:
            mean = p / rate_1 + (1-p) / rate_2

        Отсюда:
            rate_2 = (1-p) / (mean - p / rate_1)

        Этот вариант удобен для первых чувствительных экспериментов:
        одинаковое среднее, но более тяжёлый хвост и больший разброс.
        """
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
>>>>>>> main
            )

        rate_2 = (1.0 - p) / denominator

        cfg = cls(
<<<<<<< HEAD

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

=======
            kind="hyperexponential2",
            mean=mean,
            label=label,
            hyper_p=p,
            hyper_rates=(rate_1, rate_2),
        )
        cfg.validate()
        return cfg

    def short_label(self) -> str:
        """
        Короткая метка для именования сценариев и файлов результатов.
        """
        return self.label.replace(" ", "_")


# 
# ОСНОВНОЙ КОНФИГ СЦЕНАРИЯ
# 
# Это "склейка" математической модели и параметров имитации.
#
# Один объект ScenarioConfig соответствует одному полноценному сценарию:
# - конкретная ёмкость;
# - конкретный ресурсный бюджет;
# - конкретные профили lambda_k и sigma_k;
# - конкретный закон распределения ресурса;
# - конкретный закон объёма работы;
# - параметры запуска симуляции.
# 


@dataclass(slots=True)
class ScenarioConfig:
    """
    Полная спецификация одного сценария.

    Поля:
    
    name:
        Имя сценария. Используется в логах, в названиях файлов,
        на графиках и в таблицах.

    capacity_k:
        Максимальное число заявок в системе.
        Состояния системы: k = 0, 1, ..., K.

    servers_n:
        Число приборов / каналов обслуживания.
        В первой версии симулятора это отдельное ограничение:
        даже если ресурс ещё есть, заявка не принимается при отсутствии
        свободного прибора.

    total_resource_r:
        Суммарный доступный объём ресурса.

    arrival_rate_by_state:
        Кортеж длины K+1.
        arrival_rate_by_state[k] = lambda_k

    service_speed_by_state:
        Кортеж длины K+1.
        service_speed_by_state[k] = sigma_k

        Это именно скорость убывания остатка работы каждой активной заявки
        в состоянии k.

    resource_distribution:
        Распределение требований к ресурсу.

    workload_distribution:
        Распределение объёма работы.

    simulation:
        Параметры техники моделирования.

    note:
        Произвольный комментарий к сценарию.
        Удобно для пояснений в будущих таблицах экспериментов.
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

    def validate(self) -> None:
        """
        Полная проверка внутренней согласованности сценария.
        """
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

        # В состоянии полной системы обычно логично ставить lambda_K = 0,
        # потому что новые заявки всё равно не принимаются.
        # Жёстко этого не требуем, но предупреждение в summary покажем.
        self.resource_distribution.validate()
        self.workload_distribution.validate()
        self.simulation.validate()

        # В обычной loss-системе часто K >= N.
        # Формально это не обязательно, но K < N выглядит странно:
        # максимальная вместимость меньше числа приборов.
        if self.capacity_k < self.servers_n:
            raise ValueError(
                "Обычно capacity_k должен быть >= servers_n. "
                f"Сейчас capacity_k={self.capacity_k}, servers_n={self.servers_n}"
            )

        # Полезный sanity-check: заявка должна теоретически иметь шанс поместиться.
        # Если среднее требование ресурса больше общего ресурса, это не ошибка,
        # но если минимально возможное требование уже больше total_resource_r,
        # система фактически никогда никого не примет.
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
        """
        Короткое текстовое описание сценария.
        Удобно для печати в консоль и отладки.
        """
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


# 
# ФАБРИКИ ПРОФИЛЕЙ lambda_k И sigma_k
# 
# Ниже идут вспомогательные функции, которые помогают быстро строить
# типовые state-dependent профили.
#
# Почему не задавать всё руками?
# 
# Можно и руками, но:
# - легко ошибиться с длиной;
# - неудобно многократно использовать;
# - неудобно менять один параметр и генерировать новые сценарии.
# 


def constant_profile(capacity_k: int, value: float, last_value: Optional[float] = None) -> tuple[float, ...]:
    """
    Возвращает профиль постоянного значения длины K+1.

    Пример:
        constant_profile(capacity_k=4, value=2.0, last_value=0.0)
    даст:
        (2.0, 2.0, 2.0, 2.0, 0.0)

    Для интенсивности поступления это особенно удобно:
    lambda_k можно держать постоянной до состояния K-1, а в состоянии K
    поставить 0.
    """
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
    """
    Строит пороговый профиль.

    Логика:
    
    - пока k < threshold_k, используется normal_value;
    - при k >= threshold_k используется reduced_value;
    - в полном состоянии k = K можно дополнительно задать full_state_value.

    Это естественно интерпретируется как:
    - admission control;
    - искусственное снижение интенсивности входа при перегрузке;
    - влияние наблюдаемой загруженности на входной поток.
    """
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
    """
    Линейно убывающий профиль.

    Формула:
        profile[k] = max(start_value - step * k, floor_value)

    Такая функция хорошо подходит для sigma_k, если ты хочешь моделировать:
    - деградацию скорости из-за конкуренции за ресурсы;
    - падение эффективной производительности при росте числа заявок;
    - эффект перегруженности системы.
    """
    _ensure_positive("capacity_k", capacity_k)
    _ensure_nonnegative("start_value", start_value)
    _ensure_nonnegative("step", step)
>>>>>>> main
    _ensure_nonnegative("floor_value", floor_value)

    return tuple(max(start_value - step * k, floor_value) for k in range(capacity_k + 1))

<<<<<<< HEAD
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

=======

# 
# ФАБРИКИ ТИПОВЫХ РАСПРЕДЕЛЕНИЙ ДЛЯ АНАЛИЗА ЧУВСТВИТЕЛЬНОСТИ
# 
# Здесь мы строим семейство распределений объёма работы с одинаковым средним.
# Это основной инструмент для сравнения чувствительности к старшим моментам.
# 


def standard_workload_family(mean: float) -> dict[str, WorkloadDistributionConfig]:
    """
    Возвращает стандартное семейство распределений объёма работы
    с одинаковым средним.

    В семейство входят:
    - deterministic
    - exponential
    - erlang_2
    - erlang_4
    - hyperexp_2

    Зачем именно такие варианты:
    
    Это уже даёт заметный спектр разброса:
    - deterministic: нулевая дисперсия;
    - Erlang(4): малая дисперсия;
    - Erlang(2): умеренная дисперсия;
    - exponential: базовый эталон;
    - hyperexp(2): повышенная дисперсия и более тяжёлый хвост.

    Для первой серии экспериментов по чувствительности этого достаточно.
    """
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
>>>>>>> main
    }

    return family

<<<<<<< HEAD
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

=======

# 
# ФАБРИКИ ТИПОВЫХ СЦЕНАРИЕВ
# 
# Это "заготовки" для будущих экспериментов.
# Очень удобно иметь один базовый сценарий и только менять распределение
# объёма работы.
# 


def build_base_simulation_config() -> SimulationConfig:
    """
    Возвращает разумные стартовые настройки имитации.

    Почему именно такие значения:
    -
    Они не "истинно правильные", а стартовые.
    Их задача:
    - дать достаточно длинный прогон;
    - оставить место для warm-up;
    - быть удобными для первых отладочных и исследовательских запусков.

    Потом их почти наверняка придётся подстроить по результатам первых тестов.
    """
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
    """
    Базовый закон требований к ресурсу.

    Здесь используем простой дискретный равномерный закон на {1, 2, 3}.
    Это удобно, потому что:
    - он не вырожден;
    - он легко интерпретируем;
    - он не слишком тяжёлый вычислительно;
    - он уже создаёт реальную конкуренцию за ресурс.
    """
    cfg = ResourceDistributionConfig(
        kind="discrete_uniform",
        min_units=1,
        max_units=3,
    )
    cfg.validate()
    return cfg


def build_base_arrival_profile(capacity_k: int) -> tuple[float, ...]:
    """
    Базовый state-dependent профиль входного потока.

    Интерпретация:
    
    - пока система умеренно загружена, интенсивность входа выше;
    - после порога начинается "самоограничение" или admission control;
    - в полном состоянии интенсивность ставим в 0.

    Это хорошо отражает реальную мотивацию state-dependent lambda_k.
    """
    return threshold_profile(
        capacity_k=capacity_k,
        normal_value=1.80,
        threshold_k=max(1, capacity_k - 3),
        reduced_value=1.10,
        full_state_value=0.0,
    )


def build_base_service_profile(capacity_k: int) -> tuple[float, ...]:
    """
    Базовый state-dependent профиль скорости обработки работы.

    Мы делаем скорость sigma_k убывающей по k.
    Это отражает ситуацию, когда при росте числа заявок:
    - увеличивается конкуренция за CPU / канал / память;
    - каждое задание продвигается медленнее.

    Важно:
    
    sigma_k здесь понимается именно как скорость уменьшения остатка работы,
    а не как параметр экспоненциального времени обслуживания.
    """
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
    """
    Собирает один базовый сценарий.

    Идея:
    
    Мы фиксируем:
    - K;
    - N;
    - R;
    - профиль входа;
    - профиль скорости обслуживания;
    - закон ресурса.

    И меняем только распределение объёма работы.
    Именно это нам потом и понадобится для исследования чувствительности
    к старшим моментам распределения обслуживания.
    """
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
    """
    Собирает набор сценариев для первичного анализа чувствительности.

    Все сценарии отличаются только законом объёма работы,
    но имеют одинаковое среднее.
    """
    family = standard_workload_family(mean_workload)

    scenarios: dict[str, ScenarioConfig] = {}
    for key, workload_cfg in family.items():
        scenario = build_base_scenario(
            workload_distribution=workload_cfg,
            name_suffix=f"_{key}",
        )
>>>>>>> main
        scenarios[key] = scenario

    return scenarios

<<<<<<< HEAD
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

=======

# 
# ФУНКЦИИ КРАСИВОГО ВЫВОДА
# 
# Это не обязательно для математики, но очень удобно для отладки и контроля.
# 


def print_scenario_summary(scenario: ScenarioConfig) -> None:
    """
    Печатает подробную сводку по одному сценарию.

    Эта функция полезна уже на раннем этапе, когда симулятора ещё нет:
    по печати можно глазами увидеть, что профиль параметров выглядит разумно.
    """
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


# 
# ТОЧКА ВХОДА ДЛЯ САМОСТОЯТЕЛЬНОГО ЗАПУСКА
# 
# Это делает файл params.py уже сейчас полезным как самостоятельный модуль.
# Он не требует simulation.py и других файлов.
# 


def _self_test() -> None:
    """
    Небольшой самотест модуля.

    Что он делает:
    
    1. Строит набор стандартных сценариев.
    2. Валидирует каждый из них.
    3. Печатает краткую сводку.

    Если этот код отрабатывает без ошибок, значит:
    - структура параметров корректна;
    - фабрики сценариев работают;
    - модуль можно использовать как основу для следующих файлов.
    """
    scenarios = build_sensitivity_scenarios(mean_workload=1.0)

    print("\nПроверка params.py: построение типовых сценариев завершено.\n")
    print(f"Собрано сценариев: {len(scenarios)}\n")

    for scenario in scenarios.values():
>>>>>>> main
        print_scenario_summary(scenario)

    print("Самотест params.py завершён успешно.")

<<<<<<< HEAD
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
=======

    def validate(self) -> None:
        """
        Проверка корректности параметров распределения ресурса.
        """
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

>>>>>>> main
