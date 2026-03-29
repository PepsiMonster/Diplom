# описание модели, λ(n)λ(n), μ(n)μ(n), генерация сценариев
"""
model.py
========

Предметная модель системы массового обслуживания с ограниченными ресурсами
и state-dependent характеристиками.

Роль этого файла в проекте
--------------------------
Этот модуль описывает "физику" и "логику" системы, но не сам DES-движок.
Именно здесь формализуются:

1. Заявка:
   - момент поступления;
   - требуемый объём ресурса;
   - полный объём работы;
   - остаточный объём работы.

2. Состояние системы:
   - текущее время;
   - список активных заявок;
   - занятый ресурс;
   - текущее число заявок.

3. Правила:
   - можно ли принять новую заявку;
   - как добавить заявку;
   - как удалить заявку;
   - как с течением времени уменьшается остаточный объём работы;
   - какая заявка завершится первой при текущем состоянии.

Почему это выделено в отдельный файл
------------------------------------
Это промежуточный слой между:
- params.py  -> "что моделируем";
- simulation.py -> "как проигрываем события во времени".

Если этот слой сделать чистым и строгим, то дальше:
- симулятор получается проще;
- отладка становится легче;
- код лучше соответствует математической постановке из ВКР.

Можно ли запускать файл отдельно?
---------------------------------
Да.

Если запустить:
    python model.py

то будет выполнен небольшой self-test:
- построится базовый сценарий;
- создастся пустое состояние;
- будут добавлены заявки;
- выполнится продвижение времени;
- проверится логика завершения и удаления заявки.

Важно
-----
В этой версии предполагается, что в состоянии k каждая активная заявка
получает скорость обслуживания sigma_k, то есть остаток работы каждой
активной заявки убывает с одной и той же скоростью sigma_k.

Это согласовано с параметрической схемой из params.py, где
service_speed_by_state[k] интерпретируется именно как скорость убывания
остатка работы активной заявки в состоянии k.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import inf, isclose
from typing import Optional

from params import ScenarioConfig, build_base_scenario, standard_workload_family


# ============================================================================
# КЛАССИФИКАЦИЯ ПРИЧИН ОТКАЗА
# ============================================================================
# Новая заявка может быть не принята по нескольким причинам.
# Мы сразу кодируем эти причины явно, потому что потом это понадобится:
# - для статистики;
# - для таблиц в ВКР;
# - для интерпретации результатов.
# ============================================================================


class RejectionReason(str, Enum):
    """
    Причина отказа в приёме заявки.

    Значения:
    ---------
    CAPACITY_LIMIT
        В системе уже достигнута максимальная ёмкость K.

    SERVER_LIMIT
        Нет свободного обслуживающего прибора.

    RESOURCE_LIMIT
        Не хватает суммарного доступного ресурса.

    NONE
        Отказа нет, заявка может быть принята.
    """

    CAPACITY_LIMIT = "capacity_limit"
    SERVER_LIMIT = "server_limit"
    RESOURCE_LIMIT = "resource_limit"
    NONE = "none"


# ============================================================================
# РЕШЕНИЕ О ДОПУСКЕ
# ============================================================================
# Отдельный dataclass удобнее, чем просто bool:
# - код становится самодокументируемым;
# - можно передавать причину отказа;
# - позже легче собирать статистику.
# ============================================================================


@dataclass(slots=True)
class AdmissionDecision:
    """
    Результат проверки возможности принять заявку.

    Поля:
    -----
    accepted:
        True, если заявка может быть принята.

    reason:
        Причина отказа, если accepted=False.
        Если accepted=True, reason должен быть RejectionReason.NONE.
    """

    accepted: bool
    reason: RejectionReason = RejectionReason.NONE


# ============================================================================
# ОПИСАНИЕ АКТИВНОЙ ЗАЯВКИ
# ============================================================================
# Это базовая сущность модели.
# У каждой заявки хранятся:
# - уникальный идентификатор;
# - момент поступления;
# - требование к ресурсу;
# - полный объём работы;
# - остаточный объём работы.
#
# Ключевая идея:
# мы моделируем не "время завершения", а "остаток работы".
# Это особенно важно при state-dependent sigma_k:
# если число заявок в системе меняется, скорость обработки меняется тоже,
# поэтому удобнее хранить именно остаток работы.
# ============================================================================


@dataclass(slots=True)
class Job:
    """
    Активная или только что поступившая заявка.

    Поля:
    -----
    job_id:
        Уникальный идентификатор заявки.

    arrival_time:
        Время поступления заявки в систему.

    resource_demand:
        Объём ресурса, который заявка занимает всё время нахождения в системе.

    total_workload:
        Полный объём работы заявки.

    remaining_workload:
        Остаточный объём работы.
        В момент создания, если не указан явно, равен total_workload.

    Методы:
    -------
    progress(dt, service_speed):
        Уменьшает remaining_workload на service_speed * dt.

    is_completed():
        Проверяет, завершена ли заявка.
    """

    job_id: int
    arrival_time: float
    resource_demand: int
    total_workload: float
    remaining_workload: Optional[float] = None

    def __post_init__(self) -> None:
        """
        Инициализация и базовая валидация объекта.
        """
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
        """
        Продвигает обслуживание заявки на интервале длины dt.

        Формула:
            remaining_workload <- max(remaining_workload - service_speed * dt, 0)

        Почему именно так:
        ------------------
        Если в течение интервала времени состояние системы не меняется,
        то для всех активных заявок скорость обслуживания постоянна.
        Значит, остаток работы линейно убывает.

        Параметры:
        ----------
        dt:
            Длина временного интервала.

        service_speed:
            Скорость обработки работы в текущем состоянии системы.

        Замечание:
        ----------
        Если service_speed == 0, работа не продвигается.
        Это не ошибка: такая модель может быть осмысленной.
        """
        if dt < 0:
            raise ValueError(f"dt должен быть >= 0, получено: {dt}")

        if service_speed < 0:
            raise ValueError(f"service_speed должен быть >= 0, получено: {service_speed}")

        if dt == 0 or service_speed == 0:
            return

        assert self.remaining_workload is not None
        self.remaining_workload = max(self.remaining_workload - service_speed * dt, 0.0)

    def is_completed(self, tol: float = 1e-12) -> bool:
        """
        Проверяет, завершена ли заявка.

        Используется небольшой численный допуск, чтобы не зависеть
        от погрешностей машинной арифметики.
        """
        assert self.remaining_workload is not None
        return self.remaining_workload <= tol

    def time_to_completion(self, service_speed: float) -> float:
        """
        Возвращает время до завершения заявки при фиксированной текущей скорости.

        Если service_speed == 0, то заявка не может завершиться за конечное время,
        поэтому возвращаем +inf.
        """
        if service_speed < 0:
            raise ValueError(f"service_speed должен быть >= 0, получено: {service_speed}")

        assert self.remaining_workload is not None

        if self.is_completed():
            return 0.0

        if service_speed == 0.0:
            return inf

        return self.remaining_workload / service_speed


# ============================================================================
# СОСТОЯНИЕ СИСТЕМЫ
# ============================================================================
# Это центральный объект предметной модели.
#
# Он хранит текущее состояние и реализует все операции над ним:
# - проверку допуска;
# - добавление/удаление заявок;
# - продвижение времени;
# - вычисление ближайшего завершения.
# ============================================================================


@dataclass(slots=True)
class SystemState:
    """
    Текущее состояние системы.

    Поля:
    -----
    current_time:
        Текущее модельное время.

    active_jobs:
        Словарь активных заявок:
            ключ   -> job_id
            значение -> Job

        Почему словарь:
        ---------------
        - удобно быстро доставать заявку по идентификатору;
        - удобно удалять завершившиеся заявки;
        - порядок вставки в Python сохраняется, что полезно при отладке.

    next_job_id:
        Счётчик идентификаторов.
        Каждый новый job получает уникальный номер, после чего счётчик увеличивается.

    Комментарий:
    ------------
    Здесь не хранятся агрегированные статистики эксперимента.
    Это будет задачей simulation.py.
    SystemState отвечает только за текущее состояние системы.
    """

    current_time: float = 0.0
    active_jobs: dict[int, Job] = field(default_factory=dict)
    next_job_id: int = 1

    # ------------------------------------------------------------------------
    # БАЗОВЫЕ СВОЙСТВА СОСТОЯНИЯ
    # ------------------------------------------------------------------------

    @property
    def num_jobs(self) -> int:
        """
        Текущее число активных заявок в системе.
        """
        return len(self.active_jobs)

    @property
    def occupied_resource(self) -> int:
        """
        Суммарный занятый ресурс.
        """
        return sum(job.resource_demand for job in self.active_jobs.values())

    def free_resource(self, scenario: ScenarioConfig) -> int:
        """
        Возвращает объём свободного ресурса.
        """
        return scenario.total_resource_r - self.occupied_resource

    def free_servers(self, scenario: ScenarioConfig) -> int:
        """
        Возвращает число свободных приборов.
        """
        return scenario.servers_n - self.num_jobs

    # ------------------------------------------------------------------------
    # ТЕКУЩИЕ STATE-DEPENDENT ПАРАМЕТРЫ
    # ------------------------------------------------------------------------

    def current_arrival_rate(self, scenario: ScenarioConfig) -> float:
        """
        Текущая интенсивность поступления lambda_k.

        Здесь k = текущее число заявок в системе.
        """
        return scenario.arrival_rate_by_state[self.num_jobs]

    def current_service_speed(self, scenario: ScenarioConfig) -> float:
        """
        Текущая скорость обслуживания sigma_k.

        Здесь k = текущее число заявок в системе.

        Важно:
        sigma_k трактуется как скорость уменьшения остатка работы
        КАЖДОЙ активной заявки.
        """
        return scenario.service_speed_by_state[self.num_jobs]

    # ------------------------------------------------------------------------
    # ПРОВЕРКА ДОПУСКА
    # ------------------------------------------------------------------------

    def can_accept(self, resource_demand: int, scenario: ScenarioConfig) -> AdmissionDecision:
        """
        Проверяет, может ли система принять новую заявку.

        Логика проверки:
        ----------------
        1. Ограничение по общей ёмкости K.
        2. Ограничение по числу приборов N.
        3. Ограничение по свободному ресурсу.

        Порядок не принципиален математически, но полезен интерпретационно:
        если система уже полна по числу заявок, дальнейшие проверки не нужны.

        Замечание:
        ----------
        Для базовой loss-модели предполагаем, что заявка либо принимается сразу,
        либо теряется. Очередь ожидания здесь не реализуется.
        """
        if resource_demand <= 0:
            raise ValueError(f"resource_demand должен быть > 0, получено: {resource_demand}")

        # Ограничение по общей ёмкости системы K.
        if self.num_jobs >= scenario.capacity_k:
            return AdmissionDecision(False, RejectionReason.CAPACITY_LIMIT)

        # Ограничение по числу обслуживающих приборов.
        if self.num_jobs >= scenario.servers_n:
            return AdmissionDecision(False, RejectionReason.SERVER_LIMIT)

        # Ограничение по суммарному ресурсу.
        if self.occupied_resource + resource_demand > scenario.total_resource_r:
            return AdmissionDecision(False, RejectionReason.RESOURCE_LIMIT)

        return AdmissionDecision(True, RejectionReason.NONE)

    # ------------------------------------------------------------------------
    # ДОБАВЛЕНИЕ / УДАЛЕНИЕ ЗАЯВОК
    # ------------------------------------------------------------------------

    def create_job(
        self,
        *,
        resource_demand: int,
        workload: float,
        arrival_time: Optional[float] = None,
    ) -> Job:
        """
        Создаёт объект заявки, но НЕ добавляет его в систему автоматически.

        Это полезно, потому что:
        - сначала можно сгенерировать параметры заявки;
        - затем проверить допуск;
        - затем уже явно вызвать add_job.

        arrival_time:
            Если не указан, используется текущее время состояния.
        """
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
        """
        Добавляет заявку в систему.

        Перед добавлением обязательно проверяется возможность допуска.
        Если заявка не помещается, выбрасывается ValueError.

        Почему здесь именно исключение:
        --------------------------------
        Потому что если код уже дошёл до add_job, обычно это означает,
        что вызывающая сторона уже приняла решение о допуске.
        Значит, попадание сюда с недопустимой заявкой — это ошибка логики.
        """
        decision = self.can_accept(job.resource_demand, scenario)
        if not decision.accepted:
            raise ValueError(
                f"Невозможно добавить job_id={job.job_id}: отказ по причине {decision.reason.value}"
            )

        if job.job_id in self.active_jobs:
            raise ValueError(f"Заявка job_id={job.job_id} уже есть в системе")

        self.active_jobs[job.job_id] = job

    def remove_job(self, job_id: int) -> Job:
        """
        Удаляет заявку из системы и возвращает её объект.

        Это нужно для того, чтобы позже симулятор мог:
        - посчитать время пребывания;
        - сохранить сведения о завершившейся заявке;
        - обновить статистику.

        Если job_id не найден, выбрасывается KeyError.
        """
        if job_id not in self.active_jobs:
            raise KeyError(f"Заявка job_id={job_id} не найдена среди активных")

        return self.active_jobs.pop(job_id)

    # ------------------------------------------------------------------------
    # ПРОДВИЖЕНИЕ ВРЕМЕНИ И РАБОТЫ
    # ------------------------------------------------------------------------

    def advance_time_and_service(self, dt: float, scenario: ScenarioConfig) -> None:
        """
        Продвигает модельное время на dt и уменьшает остатки работ
        у всех активных заявок.

        Ключевая предпосылка:
        --------------------
        На интервале длины dt состояние системы не меняется,
        то есть число заявок остаётся постоянным.
        Следовательно, скорость sigma_k постоянна на всём интервале.

        Это именно та операция, которую DES-движок будет вызывать каждый раз
        перед обработкой очередного события.
        """
        if dt < 0:
            raise ValueError(f"dt должен быть >= 0, получено: {dt}")

        if dt == 0:
            return

        current_k = self.num_jobs
        service_speed = scenario.service_speed_by_state[current_k]

        # Сначала обновляем остатки работы всех активных заявок.
        for job in self.active_jobs.values():
            job.progress(dt=dt, service_speed=service_speed)

        # Затем двигаем модельное время.
        self.current_time += dt

    # ------------------------------------------------------------------------
    # ИНФОРМАЦИЯ О БЛИЖАЙШЕМ ЗАВЕРШЕНИИ
    # ------------------------------------------------------------------------

    def completion_offsets(self, scenario: ScenarioConfig) -> dict[int, float]:
        """
        Возвращает словарь:
            job_id -> время до завершения
        при условии, что состояние системы не изменится.

        Это одна из ключевых функций для DES-движка.
        Именно по ней потом можно определить ближайшее событие завершения.
        """
        if not self.active_jobs:
            return {}

        service_speed = self.current_service_speed(scenario)

        return {
            job_id: job.time_to_completion(service_speed)
            for job_id, job in self.active_jobs.items()
        }

    def next_completion(self, scenario: ScenarioConfig) -> tuple[Optional[int], float]:
        """
        Возвращает ближайшее завершение в виде пары:
            (job_id, delta_t)

        Если активных заявок нет или при текущей скорости завершение невозможно,
        возвращается:
            (None, inf)

        Замечание:
        ----------
        Если несколько заявок завершаются одновременно, выбирается заявка
        с минимальным job_id. Это задаёт детерминированное правило развязки.
        """
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
                # Детерминированное правило тай-брейка:
                # при почти одновременных завершениях выбираем меньший job_id.
                if job_id < best_job_id:
                    best_job_id = job_id

        return best_job_id, best_dt

    def completed_jobs(self, tol: float = 1e-12) -> list[int]:
        """
        Возвращает список идентификаторов заявок, у которых работа завершена.

        Это полезно на случай, если после продвижения времени выяснилось,
        что одновременно завершилось несколько заявок.
        """
        result: list[int] = []
        for job_id, job in self.active_jobs.items():
            if job.is_completed(tol=tol):
                result.append(job_id)
        return sorted(result)

    # ------------------------------------------------------------------------
    # СЛУЖЕБНЫЙ ВЫВОД
    # ------------------------------------------------------------------------

    def short_summary(self) -> str:
        """
        Краткая строка-сводка по состоянию системы.
        """
        return (
            f"SystemState(t={self.current_time:.6f}, "
            f"k={self.num_jobs}, "
            f"occupied_resource={self.occupied_resource}, "
            f"next_job_id={self.next_job_id})"
        )

    def pretty_print(self) -> None:
        """
        Печатает подробное состояние системы в консоль.

        Это полезно для ручной отладки без ноутбука и без симулятора.
        """
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


# ============================================================================
# SELF-TEST
# ============================================================================
# Этот блок нужен, чтобы model.py можно было проверить отдельно,
# без готового simulation.py.
# ============================================================================


def _self_test() -> None:
    """
    Простой самотест предметной модели.

    Сценарий проверки:
    ------------------
    1. Создаём базовый сценарий.
    2. Создаём пустое состояние.
    3. Добавляем две заявки.
    4. Проверяем ближайшее завершение.
    5. Продвигаем время.
    6. Удаляем завершившуюся заявку.
    7. Пробуем добавить заявку, которая не помещается по ресурсу.

    Если этот тест проходит, значит:
    - логика состояния работает;
    - правила допуска работают;
    - уменьшение остатка работы работает;
    - базовая структура model.py готова для использования в simulation.py.
    """
    workloads = standard_workload_family(mean=1.0)
    scenario = build_base_scenario(workloads["exponential"], name_suffix="_model_self_test")

    print("\nSELF-TEST model.py\n")
    print("Используемый сценарий:")
    print(scenario.short_description())
    print()

    state = SystemState()
    print("Шаг 1. Пустое состояние.")
    state.pretty_print()

    # ----------------------------------------------------------------------
    # Создаём и добавляем первую заявку.
    # ----------------------------------------------------------------------
    print("Шаг 2. Добавляем первую заявку.")
    job_1 = state.create_job(resource_demand=2, workload=1.5)
    decision_1 = state.can_accept(job_1.resource_demand, scenario)
    print(f"Решение о допуске job_1: accepted={decision_1.accepted}, reason={decision_1.reason.value}")
    state.add_job(job_1, scenario)
    state.pretty_print()

    # ----------------------------------------------------------------------
    # Создаём и добавляем вторую заявку.
    # ----------------------------------------------------------------------
    print("Шаг 3. Добавляем вторую заявку.")
    job_2 = state.create_job(resource_demand=3, workload=0.8)
    decision_2 = state.can_accept(job_2.resource_demand, scenario)
    print(f"Решение о допуске job_2: accepted={decision_2.accepted}, reason={decision_2.reason.value}")
    state.add_job(job_2, scenario)
    state.pretty_print()

    # ----------------------------------------------------------------------
    # Проверяем, какая заявка завершится первой.
    # ----------------------------------------------------------------------
    print("Шаг 4. Вычисляем ближайшее завершение.")
    next_job_id, next_dt = state.next_completion(scenario)
    print(f"Ближайшее завершение: job_id={next_job_id}, через dt={next_dt:.6f}\n")

    # ----------------------------------------------------------------------
    # Продвигаем время ровно до ближайшего завершения.
    # ----------------------------------------------------------------------
    print("Шаг 5. Продвигаем время до ближайшего завершения.")
    state.advance_time_and_service(next_dt, scenario)
    state.pretty_print()

    completed = state.completed_jobs()
    print(f"Завершившиеся заявки после продвижения времени: {completed}\n")

    # ----------------------------------------------------------------------
    # Удаляем завершившиеся заявки.
    # ----------------------------------------------------------------------
    print("Шаг 6. Удаляем завершившиеся заявки.")
    for job_id in completed:
        removed = state.remove_job(job_id)
        print(
            f"Удалена заявка job_id={removed.job_id}, "
            f"время поступления={removed.arrival_time:.4f}, "
            f"остаток={removed.remaining_workload:.6f}"
        )

    state.pretty_print()

    # ----------------------------------------------------------------------
    # Проверяем отказ по ресурсу.
    # ----------------------------------------------------------------------
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