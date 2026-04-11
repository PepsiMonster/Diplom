# Базовые параметры серии экспериментов
# Задача данного файла в том, чтобы можно было в удобной форме
# вносить новые параметры имитации и видеть, за что они отвечают


# Выбор архитектуры системы
# "loss"   — система без очереди
# "buffer" — система с конечной очередью Q = K - N
SYSTEM_ARCHITECTURE = "loss"

# Выбор профиля скорости обслуживания
# "state_dependent" - скорость обслуживания зависит от загруженности системы
# "constant" - скорость обслуживания sigma_k - константа
# state_dependent случай интересный
SERVICE_SPEED_PROFILE = "constant"

# Выбор интенсивности поступления
# "state_dependent" - интенсивность поступления новых заявок зависит от загрузки
# "constant" - интенсивность поступления новых заявок константа
# из в ARRIVAL_PROCESS_FAMILY и не зависит от загрузки системы
# arrival_rate зависящий от состояни системы - очередь в супермаркете, 
# когда люди решают даже в нее не вставать, lambda_k динамичная
# Не имеет никакого отношения к ARRIVAL_PROCESS_FAMILY
ARRIVAL_RATE_PROFILE = "constant"

# Выбор профиля workload_family
# "fixed" - экспоненциальный для анализа чувствительности 
# к распределению заявок при фиксированным workload
# "basic" - короткий набор для быстрых сравнений
# "full" - полный набор распределений
WORKLOAD_FAMILY_PROFILE = "basic"

# Какой закон обслуживания использовать при WORKLOAD_FAMILY_PROFILE = "fixed"
# Допустимы:
# "deterministic", "exponential", "erlang_2", "erlang_4",
# "erlang_8", "hyperexp_2", "hyperexp_heavy"
FIXED_WORKLOAD = "exponential"


"""
Позволяет смотреть чувствительность к распределению обслуживания:
SERVICE_SPEED_PROFILE = "constant"
ARRIVAL_RATE_PROFILE = "constant"
WORKLOAD_FAMILY_PROFILE = "basic" или full
ARRIVAL_PROCESS_FAMILY = ["poisson"] 
Запуск:
python py/launcher.py --scenario-family workload-sensitivity

---

Позволяет смотреть чувствительность к типу входящего потока:
SERVICE_SPEED_PROFILE = "constant"
ARRIVAL_RATE_PROFILE = "constant"
WORKLOAD_FAMILY_PROFILE = "fixed"
ARRIVAL_PROCESS_FAMILY = ["poisson","erlang_2","erlang_4","hyperexp_2",]
Запуск:
python py/launcher.py --scenario-family arrival-sensitivity

---

Позволяет смотреть чувствительно при обеих параметрах вместе. 
SERVICE_SPEED_PROFILE = "constant"
ARRIVAL_RATE_PROFILE = "constant"
WORKLOAD_FAMILY_PROFILE = "basic" или full
ARRIVAL_PROCESS_FAMILY = ["poisson","erlang_2","erlang_4","hyperexp_2",]
Запуск:
python py/launcher.py --scenario-family combined-sensitivity
"""

# Имя серии экспериментов. Используется как метка результатов и папок
# Пока почти бесполезна, просто подпись, не менять
SUITE_NAME = "baseline"

# Число независимых повторов каждого сценария
# Нужен для усреднения и доверительных интервалов
REPLICATIONS = 5 # 40

# Полное время моделирования.
# Чем больше, тем устойчивее оценки, но тем дольше расчёт
MAX_TIME = 50_000.0 # 200_000.0

# Длина разогрева.
# Интервал [0, WARMUP_TIME] исключается из статистики
WARMUP_TIME = MAX_TIME*0.1    # 5_000.0 # 40_000.0

# Базовый seed для воспроизводимости.
BASE_SEED = 42

# Флаги детализации результатов:
# - RECORD_STATE_TRACE: сохранять временную траекторию состояния
# - SAVE_EVENT_LOG: сохранять журнал событий (arrival/departure/queue promotion)
# - KEEP_FULL_RUN_RESULTS: сохранять полные результаты прогонов для per-run JSON
RECORD_STATE_TRACE = False
SAVE_EVENT_LOG = False
# Нужно для анимаций и более полных результатов, дает 60% к времени запуска
# Включать только когда все параметры уже настроены
KEEP_FULL_RUN_RESULTS = False # True
# Ограниченный короткий JSON для анимации: число обработанных заявок, которые пишутся в jobs-log
# 0 = отключено
ANIMATION_LOG_MAX_JOBS = 1000
# Сколько per-run JSON сохранять для каждого типа распределения (сценария).
# Остальные прогоны учитываются в статистике, но не пишутся в отдельные run_XXXX.json.
FULL_RUN_RESULTS_PER_SCENARIO = 3



# Параметры базовой ресурсной системы


# Максимальное число заявок в системе.
CAPACITY_K = 96

# Число обслуживающих приборов / каналов.
SERVERS_N = 96

# Общий объём доступного ресурса.
TOTAL_RESOURCE_R = 590


# Профиль интенсивности поступления lambda_k

# Интенсивность поступления при малой и средней загрузке
ARRIVAL_NORMAL_VALUE = 82.20 # наша λ

# Насколько близко к K начинается снижение интенсивности
# threshold_k = CAPACITY_K - ARRIVAL_THRESHOLD_OFFSET
# только в state_dependent профиле
ARRIVAL_THRESHOLD_OFFSET = 18

# Интенсивность поступления при высокой загрузке
# только в state_dependent профиле
ARRIVAL_REDUCED_VALUE = 72.20

# Интенсивность в полном состоянии k = K
# только в state_dependent профиле
ARRIVAL_FULL_STATE_VALUE = 60.0 # было 0.0, но смысла в этом нет


# Профиль скорости обслуживания sigma_k

# Скорость обслуживания при малой загрузке
SERVICE_START_VALUE = 1.20 # точка отсчета 1.40 

# Снижение скорости на одну дополнительную заявку
SERVICE_STEP = 0.06 # точка отсчета 0.07

# Нижняя граница скорости при перегрузке.
SERVICE_FLOOR_VALUE = 0.30 # точка отсчета 0.35


# Распределение требований к ресурсу

# Возможные объёмы требуемого ресурса.
RESOURCE_VALUES = [2, 4, 8, 12, 16]

# Вероятности соответствующих resource-demand значений.
RESOURCE_PROBABILITIES = [0.30, 0.25, 0.25, 0.15, 0.05]


# Семейство распределений обслуживания

# Средний объём работы заявки
# Это базовый масштаб service time / workload
# Распространяется на все распределения, которые мы используем в эксперименте
MEAN_WORKLOAD = 1.0

# Какие виды распределений объёма работы сравниваем
# Позволяет исследовать чувствительность к распределению времени обслуживания
# Не напрямую а через отношение workload к sigma_k: integral_{0}^{T} sigma_k(u) du >= W
WORKLOAD_FAMILY_BASIC = [
    "deterministic",
    "exponential",
    "erlang_4",
    "hyperexp_heavy",
]

WORKLOAD_FAMILY_FULL = [
    "deterministic",
    "exponential",
    "erlang_2",
    "erlang_4",
    "erlang_8",
    "hyperexp_2",
    "hyperexp_heavy",
]

# Параметр p для HyperExp(2)
WORKLOAD_HYPEREXP_P = 0.75

# Множитель для быстрой ветви HyperExp(2)
WORKLOAD_HYPEREXP_FAST_MULTIPLIER = 4.0

# Параметр p для более тяжёлого гиперэкспоненциального случая
WORKLOAD_HYPEREXP_HEAVY_P = 0.85

# Множитель для быстрой ветви тяжёлого HyperExp
WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER = 6.0


# Будущий резерв под тип входящего потока


# Позволит исследовать чувствительность к "типу входящего потока"
ARRIVAL_PROCESS_FAMILY = [
    "poisson", # A∼Exp(λ)
    "erlang_2", # A∼Erlang(2, mean=1/λ)
    "erlang_4", # A∼Erlang(4, mean=1/λ)
    "hyperexp_2", # A∼HyperExp2​,E[A]=1/λ
]

# Параметры для arrival-процесса HyperExp(2)
ARRIVAL_HYPEREXP_P = 0.75
ARRIVAL_HYPEREXP_FAST_MULTIPLIER = 4.0

# взять маленькое, среднее и большшое значнеи для серии экспериментов