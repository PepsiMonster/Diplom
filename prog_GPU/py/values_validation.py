from __future__ import annotations

import math
import re
from types import ModuleType


class ExperimentValuesError(ValueError):
    """Ошибка в конфигурации experiment_values.py."""
    pass


_ALLOWED_WORKLOAD_FAMILY_PROFILES = {"fixed", "basic", "full"}

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


def _validate_nonempty_number_list(values, *, name: str, positive: bool) -> None:
    _require(isinstance(values, list), f"{name} должен быть list, получено: {type(values).__name__}")
    _require(len(values) > 0, f"{name} не должен быть пустым")

    for i, x in enumerate(values):
        if positive:
            _require(
                _is_positive_number(x),
                f"{name}[{i}] должен быть > 0, получено: {x!r}",
            )
        else:
            _require(
                _is_nonnegative_number(x),
                f"{name}[{i}] должен быть >= 0, получено: {x!r}",
            )


def resolve_workload_family(values_module: ModuleType) -> list[str]:
    profile = values_module.WORKLOAD_FAMILY_PROFILE

    if profile == "fixed":
        return [values_module.FIXED_WORKLOAD]
    if profile == "basic":
        return list(values_module.WORKLOAD_FAMILY_BASIC)
    if profile == "full":
        return list(values_module.WORKLOAD_FAMILY_FULL)

    raise ExperimentValuesError(
        f"Неизвестный WORKLOAD_FAMILY_PROFILE={profile!r}; "
        f"допустимы: {sorted(_ALLOWED_WORKLOAD_FAMILY_PROFILES)}"
    )


def validate_experiment_values(values_module: ModuleType) -> None:
    # ------------------------------------------------------------
    # 1. Общие параметры серии
    # ------------------------------------------------------------
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
            f"получено: {values_module.WARMUP_TIME} >= {values_module.MAX_TIME}"
        ),
    )

    _require(
        _is_nonnegative_int(values_module.BASE_SEED),
        f"BASE_SEED должен быть целым >= 0, получено: {values_module.BASE_SEED!r}",
    )

    # ------------------------------------------------------------
    # 2. Параметры loss-системы
    # ------------------------------------------------------------
    _require(
        _is_positive_int(values_module.SERVERS_N),
        f"SERVERS_N должен быть целым > 0, получено: {values_module.SERVERS_N!r}",
    )

    _require(
        _is_positive_int(values_module.TOTAL_RESOURCE_R),
        f"TOTAL_RESOURCE_R должен быть целым > 0, получено: {values_module.TOTAL_RESOURCE_R!r}",
    )

    # ------------------------------------------------------------
    # 3. Sweep по lambda и sigma
    # ------------------------------------------------------------
    _validate_nonempty_number_list(
        values_module.ARRIVAL_RATE_LEVELS,
        name="ARRIVAL_RATE_LEVELS",
        positive=False,
    )

    _validate_nonempty_number_list(
        values_module.SERVICE_SPEED_LEVELS,
        name="SERVICE_SPEED_LEVELS",
        positive=True,
    )

    # ------------------------------------------------------------
    # 4. Распределение ресурса
    # ------------------------------------------------------------
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
            "Длины RESOURCE_VALUES и RESOURCE_PROBABILITIES должны совпадать, "
            f"получено: {len(values_module.RESOURCE_VALUES)} и "
            f"{len(values_module.RESOURCE_PROBABILITIES)}"
        ),
    )

    for i, value in enumerate(values_module.RESOURCE_VALUES):
        _require(
            _is_positive_int(value),
            f"RESOURCE_VALUES[{i}] должен быть целым > 0, получено: {value!r}",
        )

    for i, p in enumerate(values_module.RESOURCE_PROBABILITIES):
        _validate_probability(p, name=f"RESOURCE_PROBABILITIES[{i}]")

    prob_sum = sum(values_module.RESOURCE_PROBABILITIES)
    _require(
        abs(prob_sum - 1.0) <= 1e-10,
        f"Сумма RESOURCE_PROBABILITIES должна быть равна 1.0, сейчас это {prob_sum}",
    )

    _require(
        min(values_module.RESOURCE_VALUES) <= values_module.TOTAL_RESOURCE_R,
        (
            "Даже минимально возможное требование к ресурсу превышает TOTAL_RESOURCE_R: "
            "система не сможет принять ни одной заявки."
        ),
    )

    # ------------------------------------------------------------
    # 5. Workload family
    # ------------------------------------------------------------
    _require(
        isinstance(values_module.WORKLOAD_FAMILY_PROFILE, str)
        and values_module.WORKLOAD_FAMILY_PROFILE in _ALLOWED_WORKLOAD_FAMILY_PROFILES,
        (
            "WORKLOAD_FAMILY_PROFILE должен быть одним из "
            f"{sorted(_ALLOWED_WORKLOAD_FAMILY_PROFILES)}, "
            f"получено: {values_module.WORKLOAD_FAMILY_PROFILE!r}"
        ),
    )

    _require(
        isinstance(values_module.FIXED_WORKLOAD, str)
        and values_module.FIXED_WORKLOAD in _ALLOWED_WORKLOADS,
        (
            "FIXED_WORKLOAD должен быть одним из "
            f"{sorted(_ALLOWED_WORKLOADS)}, "
            f"получено: {values_module.FIXED_WORKLOAD!r}"
        ),
    )

    _require(
        _is_positive_number(values_module.MEAN_WORKLOAD),
        f"MEAN_WORKLOAD должен быть > 0, получено: {values_module.MEAN_WORKLOAD!r}",
    )

    _require(
        isinstance(values_module.WORKLOAD_FAMILY_BASIC, list)
        and len(values_module.WORKLOAD_FAMILY_BASIC) > 0,
        "WORKLOAD_FAMILY_BASIC должен быть непустым списком",
    )

    _require(
        isinstance(values_module.WORKLOAD_FAMILY_FULL, list)
        and len(values_module.WORKLOAD_FAMILY_FULL) > 0,
        "WORKLOAD_FAMILY_FULL должен быть непустым списком",
    )

    for family_name, family_values in [
        ("WORKLOAD_FAMILY_BASIC", values_module.WORKLOAD_FAMILY_BASIC),
        ("WORKLOAD_FAMILY_FULL", values_module.WORKLOAD_FAMILY_FULL),
    ]:
        for i, item in enumerate(family_values):
            _require(
                isinstance(item, str) and item in _ALLOWED_WORKLOADS,
                f"{family_name}[{i}] имеет недопустимое значение: {item!r}",
            )

    resolved_workload_family = resolve_workload_family(values_module)
    _require(
        len(resolved_workload_family) > 0,
        "После resolve_workload_family список workload не должен быть пустым",
    )

    _validate_probability(values_module.WORKLOAD_HYPEREXP_P, name="WORKLOAD_HYPEREXP_P")
    _require(
        _is_positive_number(values_module.WORKLOAD_HYPEREXP_FAST_MULTIPLIER),
        (
            "WORKLOAD_HYPEREXP_FAST_MULTIPLIER должен быть > 0, "
            f"получено: {values_module.WORKLOAD_HYPEREXP_FAST_MULTIPLIER!r}"
        ),
    )

    _validate_probability(
        values_module.WORKLOAD_HYPEREXP_HEAVY_P,
        name="WORKLOAD_HYPEREXP_HEAVY_P",
    )
    _require(
        _is_positive_number(values_module.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER),
        (
            "WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER должен быть > 0, "
            f"получено: {values_module.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER!r}"
        ),
    )

    # ------------------------------------------------------------
    # 6. Arrival process family
    # ------------------------------------------------------------
    _require(
        isinstance(values_module.ARRIVAL_PROCESS_FAMILY, list)
        and len(values_module.ARRIVAL_PROCESS_FAMILY) > 0,
        "ARRIVAL_PROCESS_FAMILY должен быть непустым списком",
    )

    for i, item in enumerate(values_module.ARRIVAL_PROCESS_FAMILY):
        _require(
            isinstance(item, str) and item in _ALLOWED_ARRIVAL_PROCESSES,
            f"ARRIVAL_PROCESS_FAMILY[{i}] имеет недопустимое значение: {item!r}",
        )

    _validate_probability(values_module.ARRIVAL_HYPEREXP_P, name="ARRIVAL_HYPEREXP_P")
    _require(
        _is_positive_number(values_module.ARRIVAL_HYPEREXP_FAST_MULTIPLIER),
        (
            "ARRIVAL_HYPEREXP_FAST_MULTIPLIER должен быть > 0, "
            f"получено: {values_module.ARRIVAL_HYPEREXP_FAST_MULTIPLIER!r}"
        ),
    )


def validation_summary(values_module: ModuleType) -> str:
    resolved_workload_family = resolve_workload_family(values_module)

    return "\n".join([
        "Validation OK",
        f"SUITE_NAME={values_module.SUITE_NAME}",
        f"REPLICATIONS={values_module.REPLICATIONS}",
        f"MAX_TIME={values_module.MAX_TIME}",
        f"WARMUP_TIME={values_module.WARMUP_TIME}",
        f"SERVERS_N={values_module.SERVERS_N}",
        f"TOTAL_RESOURCE_R={values_module.TOTAL_RESOURCE_R}",
        f"ARRIVAL_RATE_LEVELS={values_module.ARRIVAL_RATE_LEVELS}",
        f"SERVICE_SPEED_LEVELS={values_module.SERVICE_SPEED_LEVELS}",
        f"WORKLOAD_FAMILY_PROFILE={values_module.WORKLOAD_FAMILY_PROFILE}",
        f"RESOLVED_WORKLOAD_FAMILY={resolved_workload_family}",
        f"ARRIVAL_PROCESS_FAMILY={values_module.ARRIVAL_PROCESS_FAMILY}",
    ])