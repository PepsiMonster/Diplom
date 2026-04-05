from __future__ import annotations

import math
import re
from types import ModuleType


class ExperimentValuesError(ValueError):
    """Ошибка в конфигурации experiment_values.py."""
    pass


_ALLOWED_ARCHITECTURES = {"loss", "buffer"}

_ALLOWED_WORKLOADS = {
    "deterministic",
    "exponential",
    "erlang_2",
    "erlang_4",
    "erlang_8",
    "hyperexp_2",
    "hyperexp_heavy",
}

_ALLOWED_ARRIVAL_PROCESSES = {
    "poisson",
    "erlang_2",
    "erlang_4",
    "hyperexp_2",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExperimentValuesError(message)


def _is_positive_number(x) -> bool:
    return (
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and math.isfinite(x)
        and x > 0
    )


def _is_nonnegative_number(x) -> bool:
    return (
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and math.isfinite(x)
        and x >= 0
    )


def _is_positive_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x > 0


def _is_nonnegative_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 0


def _validate_probability(p: float, *, name: str) -> None:
    _require(
        isinstance(p, (int, float))
        and not isinstance(p, bool)
        and math.isfinite(p)
        and 0.0 < p < 1.0,
        f"{name} должен лежать в интервале (0, 1), получено: {p!r}",
    )


def compute_queue_capacity(values_module: ModuleType) -> int:
    """
    Возвращает производную ёмкость очереди.

    Для архитектуры 'loss' очередь отсутствует, поэтому Q = 0.
    Для архитектуры 'buffer' очередь имеет ёмкость Q = K - N.
    """
    architecture = values_module.SYSTEM_ARCHITECTURE
    if architecture == "loss":
        return 0
    if architecture == "buffer":
        return values_module.CAPACITY_K - values_module.SERVERS_N
    raise ExperimentValuesError(
        f"Неизвестная архитектура {architecture!r}; допустимы: {sorted(_ALLOWED_ARCHITECTURES)}"
    )


def validate_experiment_values(values_module: ModuleType) -> None:
    """
    Проверяет согласованность параметров из experiment_values.py.
    """
    _require(
        isinstance(values_module.SYSTEM_ARCHITECTURE, str)
        and values_module.SYSTEM_ARCHITECTURE in _ALLOWED_ARCHITECTURES,
        (
            "SYSTEM_ARCHITECTURE должен быть одним из "
            f"{sorted(_ALLOWED_ARCHITECTURES)}, получено: {values_module.SYSTEM_ARCHITECTURE!r}"
        ),
    )

    _require(
        isinstance(values_module.SUITE_NAME, str)
        and values_module.SUITE_NAME.strip() != "",
        "SUITE_NAME должен быть непустой строкой",
    )

    _require(
        re.fullmatch(r"[A-Za-z0-9_.-]+", values_module.SUITE_NAME) is not None,
        (
            "SUITE_NAME должен содержать только буквы, цифры, '.', '_' или '-', "
            f"получено: {values_module.SUITE_NAME!r}"
        ),
    )

    _require(
        _is_positive_number(values_module.MEAN_WORKLOAD),
        f"MEAN_WORKLOAD должен быть > 0, получено: {values_module.MEAN_WORKLOAD!r}",
    )
    _require(
        _is_positive_int(values_module.REPLICATIONS),
        f"REPLICATIONS должен быть целым > 0, получено: {values_module.REPLICATIONS!r}",
    )
    _require(
        _is_positive_number(values_module.MAX_TIME),
        f"MAX_TIME должен быть > 0, получено: {values_module.MAX_TIME!r}",
    )
    _require(
        _is_nonnegative_number(values_module.WARMUP_TIME),
        f"WARMUP_TIME должен быть >= 0, получено: {values_module.WARMUP_TIME!r}",
    )
    _require(
        values_module.WARMUP_TIME < values_module.MAX_TIME,
        (
            "WARMUP_TIME должен быть строго меньше MAX_TIME, "
            f"получено {values_module.WARMUP_TIME} >= {values_module.MAX_TIME}"
        ),
    )
    _require(
        _is_nonnegative_int(values_module.BASE_SEED),
        f"BASE_SEED должен быть целым >= 0, получено: {values_module.BASE_SEED!r}",
    )
    _require(
        isinstance(values_module.RECORD_STATE_TRACE, bool),
        f"RECORD_STATE_TRACE должен быть bool, получено: {values_module.RECORD_STATE_TRACE!r}",
    )
    _require(
        isinstance(values_module.SAVE_EVENT_LOG, bool),
        f"SAVE_EVENT_LOG должен быть bool, получено: {values_module.SAVE_EVENT_LOG!r}",
    )
    _require(
        isinstance(values_module.KEEP_FULL_RUN_RESULTS, bool),
        f"KEEP_FULL_RUN_RESULTS должен быть bool, получено: {values_module.KEEP_FULL_RUN_RESULTS!r}",
    )

    _require(
        _is_positive_int(values_module.CAPACITY_K),
        f"CAPACITY_K должен быть целым > 0, получено: {values_module.CAPACITY_K!r}",
    )
    _require(
        _is_positive_int(values_module.SERVERS_N),
        f"SERVERS_N должен быть целым > 0, получено: {values_module.SERVERS_N!r}",
    )
    _require(
        _is_positive_int(values_module.TOTAL_RESOURCE_R),
        (
            "TOTAL_RESOURCE_R должен быть целым > 0, "
            f"получено: {values_module.TOTAL_RESOURCE_R!r}"
        ),
    )

    if values_module.SYSTEM_ARCHITECTURE == "loss":
        _require(
            values_module.CAPACITY_K == values_module.SERVERS_N,
            (
                "Для архитектуры 'loss' требуется CAPACITY_K == SERVERS_N, "
                "поскольку очередь отсутствует. "
                f"Сейчас CAPACITY_K={values_module.CAPACITY_K}, "
                f"SERVERS_N={values_module.SERVERS_N}"
            ),
        )

    if values_module.SYSTEM_ARCHITECTURE == "buffer":
        _require(
            values_module.CAPACITY_K > values_module.SERVERS_N,
            (
                "Для архитектуры 'buffer' требуется CAPACITY_K > SERVERS_N, "
                "чтобы очередь имела положительную ёмкость Q = K - N. "
                f"Сейчас CAPACITY_K={values_module.CAPACITY_K}, "
                f"SERVERS_N={values_module.SERVERS_N}"
            ),
        )

    queue_capacity = compute_queue_capacity(values_module)
    _require(
        queue_capacity >= 0,
        f"Вычисленная ёмкость очереди должна быть >= 0, получено: {queue_capacity}",
    )

    _require(
        _is_nonnegative_number(values_module.ARRIVAL_NORMAL_VALUE),
        (
            "ARRIVAL_NORMAL_VALUE должен быть >= 0, "
            f"получено: {values_module.ARRIVAL_NORMAL_VALUE!r}"
        ),
    )
    _require(
        _is_nonnegative_int(values_module.ARRIVAL_THRESHOLD_OFFSET),
        (
            "ARRIVAL_THRESHOLD_OFFSET должен быть целым >= 0, "
            f"получено: {values_module.ARRIVAL_THRESHOLD_OFFSET!r}"
        ),
    )
    _require(
        _is_nonnegative_number(values_module.ARRIVAL_REDUCED_VALUE),
        (
            "ARRIVAL_REDUCED_VALUE должен быть >= 0, "
            f"получено: {values_module.ARRIVAL_REDUCED_VALUE!r}"
        ),
    )
    _require(
        _is_nonnegative_number(values_module.ARRIVAL_FULL_STATE_VALUE),
        (
            "ARRIVAL_FULL_STATE_VALUE должен быть >= 0, "
            f"получено: {values_module.ARRIVAL_FULL_STATE_VALUE!r}"
        ),
    )

    _require(
        values_module.ARRIVAL_THRESHOLD_OFFSET <= values_module.CAPACITY_K,
        (
            "ARRIVAL_THRESHOLD_OFFSET не может быть больше CAPACITY_K. "
            f"Сейчас offset={values_module.ARRIVAL_THRESHOLD_OFFSET}, "
            f"K={values_module.CAPACITY_K}"
        ),
    )

    _require(
        values_module.ARRIVAL_REDUCED_VALUE <= values_module.ARRIVAL_NORMAL_VALUE,
        (
            "ARRIVAL_REDUCED_VALUE должен быть <= ARRIVAL_NORMAL_VALUE. "
            f"Сейчас reduced={values_module.ARRIVAL_REDUCED_VALUE}, "
            f"normal={values_module.ARRIVAL_NORMAL_VALUE}"
        ),
    )

    _require(
        values_module.ARRIVAL_FULL_STATE_VALUE == 0.0,
        (
            "В текущей постановке требуется ARRIVAL_FULL_STATE_VALUE == 0.0, "
            "чтобы в полном состоянии система не принимала новые заявки."
        ),
    )

    _require(
        _is_positive_number(values_module.SERVICE_START_VALUE),
        (
            "SERVICE_START_VALUE должен быть > 0, "
            f"получено: {values_module.SERVICE_START_VALUE!r}"
        ),
    )
    _require(
        _is_nonnegative_number(values_module.SERVICE_STEP),
        f"SERVICE_STEP должен быть >= 0, получено: {values_module.SERVICE_STEP!r}",
    )
    _require(
        _is_nonnegative_number(values_module.SERVICE_FLOOR_VALUE),
        (
            "SERVICE_FLOOR_VALUE должен быть >= 0, "
            f"получено: {values_module.SERVICE_FLOOR_VALUE!r}"
        ),
    )
    _require(
        values_module.SERVICE_FLOOR_VALUE <= values_module.SERVICE_START_VALUE,
        (
            "SERVICE_FLOOR_VALUE должен быть <= SERVICE_START_VALUE, "
            f"сейчас floor={values_module.SERVICE_FLOOR_VALUE}, "
            f"start={values_module.SERVICE_START_VALUE}"
        ),
    )

    _require(
        isinstance(values_module.RESOURCE_VALUES, list)
        and len(values_module.RESOURCE_VALUES) > 0,
        "RESOURCE_VALUES должен быть непустым списком",
    )
    _require(
        isinstance(values_module.RESOURCE_PROBABILITIES, list)
        and len(values_module.RESOURCE_PROBABILITIES) > 0,
        "RESOURCE_PROBABILITIES должен быть непустым списком",
    )
    _require(
        len(values_module.RESOURCE_VALUES) == len(values_module.RESOURCE_PROBABILITIES),
        (
            "RESOURCE_VALUES и RESOURCE_PROBABILITIES должны иметь одинаковую длину, "
            f"сейчас {len(values_module.RESOURCE_VALUES)} и "
            f"{len(values_module.RESOURCE_PROBABILITIES)}"
        ),
    )

    for i, value in enumerate(values_module.RESOURCE_VALUES):
        _require(
            _is_positive_int(value),
            f"RESOURCE_VALUES[{i}] должен быть целым > 0, получено: {value!r}",
        )

    _require(
        values_module.RESOURCE_VALUES == sorted(set(values_module.RESOURCE_VALUES)),
        (
            "RESOURCE_VALUES должен быть строго возрастающим списком без повторов. "
            f"Сейчас: {values_module.RESOURCE_VALUES!r}"
        ),
    )

    for i, p in enumerate(values_module.RESOURCE_PROBABILITIES):
        _validate_probability(p, name=f"RESOURCE_PROBABILITIES[{i}]")

    total_prob = sum(values_module.RESOURCE_PROBABILITIES)
    _require(
        abs(total_prob - 1.0) <= 1e-10,
        (
            "Сумма RESOURCE_PROBABILITIES должна быть равна 1.0, "
            f"сейчас {total_prob}"
        ),
    )

    _require(
        min(values_module.RESOURCE_VALUES) <= values_module.TOTAL_RESOURCE_R,
        (
            "Даже минимальное требование к ресурсу не должно превышать TOTAL_RESOURCE_R. "
            f"min(RESOURCE_VALUES)={min(values_module.RESOURCE_VALUES)}, "
            f"TOTAL_RESOURCE_R={values_module.TOTAL_RESOURCE_R}"
        ),
    )

    _require(
        isinstance(values_module.WORKLOAD_FAMILY, list)
        and len(values_module.WORKLOAD_FAMILY) > 0,
        "WORKLOAD_FAMILY должен быть непустым списком",
    )
    _require(
        len(values_module.WORKLOAD_FAMILY) == len(set(values_module.WORKLOAD_FAMILY)),
        f"WORKLOAD_FAMILY не должен содержать дубликатов, сейчас: {values_module.WORKLOAD_FAMILY!r}",
    )

    for i, item in enumerate(values_module.WORKLOAD_FAMILY):
        _require(
            item in _ALLOWED_WORKLOADS,
            (
                f"WORKLOAD_FAMILY[{i}] имеет неизвестное значение {item!r}; "
                f"допустимы: {sorted(_ALLOWED_WORKLOADS)}"
            ),
        )

    _validate_probability(values_module.WORKLOAD_HYPEREXP_P, name="WORKLOAD_HYPEREXP_P")
    _require(
        _is_positive_number(values_module.WORKLOAD_HYPEREXP_FAST_MULTIPLIER),
        (
            "WORKLOAD_HYPEREXP_FAST_MULTIPLIER должен быть > 0, "
            f"получено: {values_module.WORKLOAD_HYPEREXP_FAST_MULTIPLIER!r}"
        ),
    )

    _validate_probability(values_module.WORKLOAD_HYPEREXP_HEAVY_P, name="WORKLOAD_HYPEREXP_HEAVY_P")
    _require(
        _is_positive_number(values_module.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER),
        (
            "WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER должен быть > 0, "
            f"получено: {values_module.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER!r}"
        ),
    )

    rate_1 = values_module.WORKLOAD_HYPEREXP_FAST_MULTIPLIER / values_module.MEAN_WORKLOAD
    denominator = values_module.MEAN_WORKLOAD - values_module.WORKLOAD_HYPEREXP_P / rate_1
    _require(
        denominator > 0.0,
        (
            "Параметры WORKLOAD_HYPEREXP_P и "
            "WORKLOAD_HYPEREXP_FAST_MULTIPLIER дают некорректную вторую интенсивность HyperExp(2)."
        ),
    )

    heavy_rate_1 = values_module.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER / values_module.MEAN_WORKLOAD
    heavy_denominator = values_module.MEAN_WORKLOAD - values_module.WORKLOAD_HYPEREXP_HEAVY_P / heavy_rate_1
    _require(
        heavy_denominator > 0.0,
        (
            "Параметры WORKLOAD_HYPEREXP_HEAVY_P и "
            "WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER дают некорректную вторую интенсивность HyperExpHeavy."
        ),
    )

    _require(
        isinstance(values_module.ARRIVAL_PROCESS_FAMILY, list)
        and len(values_module.ARRIVAL_PROCESS_FAMILY) > 0,
        "ARRIVAL_PROCESS_FAMILY должен быть непустым списком",
    )
    _require(
        len(values_module.ARRIVAL_PROCESS_FAMILY) == len(set(values_module.ARRIVAL_PROCESS_FAMILY)),
        (
            "ARRIVAL_PROCESS_FAMILY не должен содержать дубликатов, "
            f"сейчас: {values_module.ARRIVAL_PROCESS_FAMILY!r}"
        ),
    )

    for i, item in enumerate(values_module.ARRIVAL_PROCESS_FAMILY):
        _require(
            item in _ALLOWED_ARRIVAL_PROCESSES,
            (
                f"ARRIVAL_PROCESS_FAMILY[{i}] имеет неизвестное значение {item!r}; "
                f"допустимы: {sorted(_ALLOWED_ARRIVAL_PROCESSES)}"
            ),
        )


def validation_summary(values_module: ModuleType) -> str:
    queue_capacity = compute_queue_capacity(values_module)
    return (
        "experiment_values.py: конфигурация корректна\n"
        f"SYSTEM_ARCHITECTURE = {values_module.SYSTEM_ARCHITECTURE}\n"
        f"QUEUE_CAPACITY = {queue_capacity}\n"
        f"CAPACITY_K = {values_module.CAPACITY_K}\n"
        f"SERVERS_N = {values_module.SERVERS_N}"
    )


if __name__ == "__main__":
    import experiment_values as v

    validate_experiment_values(v)
    print(validation_summary(v))
