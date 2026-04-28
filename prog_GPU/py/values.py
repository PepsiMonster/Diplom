# Базовые параметры серии экспериментов для GPU-ветки.
# Эта ветка специально упрощена:
# - только loss-система;
# - только constant arrival rate;
# - только constant service speed;
# - без state-dependent профилей;
# - без event/state logs как части основной постановки.
#
# Идея такая: Python задаёт компактную конфигурацию серии,
# а Rust/GPU-часть строит из неё сетку сценариев и считает их пакетно.


 
# 1. Режим серии экспериментов
 

# "fixed"  - одно фиксированное распределение workload
# "basic"  - короткий набор для быстрых сравнений
# "full"   - полный набор распределений
WORKLOAD_FAMILY_PROFILE = "basic"

# Используется только если WORKLOAD_FAMILY_PROFILE = "fixed"
# Допустимы:
# "deterministic", "exponential", "erlang_2", "erlang_4",
# "erlang_8", "hyperexp_2", "hyperexp_heavy"
FIXED_WORKLOAD = "exponential"


"""
Поддерживаемые семейства сценариев:

1) workload-sensitivity
   Сравнение чувствительности к распределению обслуживания.
   Обычно ARRIVAL_PROCESS_FAMILY = ["poisson"].

2) arrival-sensitivity
   Сравнение чувствительности к типу входящего потока.
   Обычно WORKLOAD_FAMILY_PROFILE = "fixed".

3) combined-sensitivity
   Совместная чувствительность и к workload family, и к arrival process.

Во всех трёх режимах можно дополнительно делать sweep по:
- ARRIVAL_RATE_LEVELS
- SERVICE_SPEED_LEVELS
"""


 
# 2. Общие параметры серии
 

# Имя серии экспериментов
SUITE_NAME = "baseline_gpu"

# Число независимых повторов каждого сценария
REPLICATIONS = 20

# Полное время моделирования
MAX_TIME = 50_000.0

# Длина разогрева
WARMUP_TIME = 5_000.0

# Базовый seed для воспроизводимости
BASE_SEED = 42


 
# 3. Параметры loss-системы
 

# Число обслуживающих каналов.
# Для этой GPU-ветки предполагается loss-архитектура без очереди,
# поэтому внутренне будет считаться, что K = N.
SERVERS_N = 96

# Общий доступный ресурс системы
TOTAL_RESOURCE_R = 590


 
# 4. Sweep по уровням нагрузки и скорости
 

# Уровни интенсивности поступления lambda.
# Это основной способ изучать сдвиг метрик и графиков при разных lambda.
ARRIVAL_RATE_LEVELS = [75.0, 86.5, 98.0]

# Уровни скорости обслуживания sigma.
# Если пока не хотите sweep по sigma, можно оставить один уровень.
SERVICE_SPEED_LEVELS = [1.2]


 
# 5. Распределение требований к ресурсу
 

# Возможные объёмы требуемого ресурса одной заявкой
RESOURCE_VALUES = [2, 4, 8, 12, 16]

# Вероятности соответствующих значений resource-demand
RESOURCE_PROBABILITIES = [0.25, 0.25, 0.30, 0.15, 0.05]


 
# 6. Семейство распределений workload
 

# Средний объём работы заявки
MEAN_WORKLOAD = 1.0

# Короткий набор распределений workload
WORKLOAD_FAMILY_BASIC = [
    "deterministic",
    "exponential",
    "erlang_4",
    "hyperexp_heavy",
]

# Полный набор распределений workload
WORKLOAD_FAMILY_FULL = [
    "deterministic",
    "exponential",
    "erlang_2",
    "erlang_4",
    "erlang_8",
    "hyperexp_2",
    "hyperexp_heavy",
]

# Параметры workload HyperExp(2)
WORKLOAD_HYPEREXP_P = 0.75
WORKLOAD_HYPEREXP_FAST_MULTIPLIER = 4.0

# Параметры более тяжёлого workload HyperExp
WORKLOAD_HYPEREXP_HEAVY_P = 0.85
WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER = 6.0


 
# 7. Семейство входных потоков
 

# Какие типы входящего потока сравниваем
ARRIVAL_PROCESS_FAMILY = [
    "poisson",     # A ~ Exp(lambda)
    "erlang_2",    # A ~ Erlang(2, mean = 1/lambda)
    "erlang_4",    # A ~ Erlang(4, mean = 1/lambda)
    "hyperexp_2",  # A ~ HyperExp(2), E[A] = 1/lambda
]

# Параметры arrival HyperExp(2)
ARRIVAL_HYPEREXP_P = 0.75
ARRIVAL_HYPEREXP_FAST_MULTIPLIER = 4.0