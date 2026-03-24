"""
Запускает весь рабочий конвейер:
1. выполняет серию экспериментов;
2. сохраняет таблицы результатов;
3. строит графики по этим таблицам.
"""

from experiments import run_all_experiments
from plots import build_all_plots

def main() -> None:

    print("Шаг 1. Запуск вычислительных экспериментов...")
    experiment_outputs = run_all_experiments()

    print()
    print("Шаг 2. Построение графиков...")
    plot_outputs = build_all_plots()

    print()
    print("Конвейер завершён успешно.")
    print("Сохранённые таблицы:")
    for name, path in experiment_outputs.items():
        print(f"  {name}: {path}")

    print("Сохранённые графики:")
    for name, path in plot_outputs.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()