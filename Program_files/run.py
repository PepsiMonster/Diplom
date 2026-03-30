from __future__ import annotations

from dataclasses import asdict, replace

from datetime import datetime

from pathlib import Path

from typing import Any

import argparse

import json

from params import (
    ScenarioConfig,
    build_base_scenario,
    build_sensitivity_scenarios,
    print_scenario_summary,
    standard_workload_family,
)

from simulation import simulate_one_run, print_run_summary

from experiments import (
    ExperimentSuiteResult,
    build_default_experiment_suite,

    print_experiment_suite_summary,

    run_experiment_suite,

    save_experiment_suite,

)

from plots import generate_standard_plots, load_suite_data, resolve_suite_result_json

def _timestamp() -> str:

    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _ensure_dir(path: str | Path) -> Path:

    path_obj = Path(path)

    path_obj.mkdir(parents=True, exist_ok=True)

    return path_obj

def _make_run_root(base_dir: str | Path, prefix: str) -> Path:

    return _ensure_dir(Path(base_dir) / prefix / _timestamp())

def _override_simulation_config(

    scenario: ScenarioConfig,

    *,

    max_time: float | None,

    warmup_time: float | None,

    replications: int | None,

    record_state_trace: bool | None,

    save_event_log: bool | None,

) -> ScenarioConfig:

    sim = scenario.simulation

    updated = replace(

        sim,

        max_time=max_time if max_time is not None else sim.max_time,

        warmup_time=warmup_time if warmup_time is not None else sim.warmup_time,

        replications=replications if replications is not None else sim.replications,

        record_state_trace=record_state_trace if record_state_trace is not None else sim.record_state_trace,

        save_event_log=save_event_log if save_event_log is not None else sim.save_event_log,

    )

    return replace(scenario, simulation=updated)

def _save_single_run_result(result, output_dir: str | Path) -> Path:
    out_dir = _ensure_dir(output_dir)

    payload = asdict(result)

    out_path = out_dir / "single_run_result.json"

    out_path.write_text(

        json.dumps(payload, ensure_ascii=False, indent=2),

        encoding="utf-8",

    )

    return out_path

def _format_metric(value: Any) -> str:

    if isinstance(value, float):

        return f"{value:.6f}"

    return str(value)

def _save_markdown_report(lines: list[str], output_path: str | Path) -> Path:

    out = Path(output_path)

    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return out

def _save_single_run_report(

    *,

    result,

    scenario: ScenarioConfig,

    args: argparse.Namespace,

    output_root: Path,

    json_path: Path,

) -> Path:

    lines = [
        "# Отчёт по одному прогону",
        "",
        "## Что запускалось",
        f"- Сценарий: **{scenario.name}**.",
        f"- Replication index: **{result.replication_index}**.",
        f"- Seed: **{result.seed}**.",
        f"- Время моделирования: **{result.total_time}**, warm-up: **{result.warmup_time}**.",
        "",
        "## Текстовое описание результата",
        (
            "Прогон завершён успешно. Ниже собраны ключевые показатели, "
            "которые можно читать как текстовый лог-отчёт, а не как raw JSON."
        ),
        "",
        "## Ключевые метрики",
    ]

    key_metrics = [
        ("Наблюдаемое время", result.observed_time),
        ("Среднее число заявок", result.mean_num_jobs),
        ("Средний занятый ресурс", result.mean_occupied_resource),
        ("Попытки поступления", result.arrival_attempts),
        ("Принятые заявки", result.accepted_arrivals),
        ("Отказы", result.rejected_arrivals),
        ("Завершённые заявки", result.completed_jobs),
        ("Вероятность отказа", result.loss_probability),
        ("Пропускная способность", result.throughput),
    ]

    lines.extend([f"- {name}: **{_format_metric(value)}**." for name, value in key_metrics])

    lines.extend([
        "",
        "## Где лежат артефакты",
        f"- JSON с полным результатом: `{json_path}`.",
        f"- Папка прогона: `{output_root}`.",
        "",
        "## Параметры запуска CLI",
        f"- max_time={args.max_time}, warmup_time={args.warmup_time}, "
        f"record_state_trace={args.record_state_trace}, save_event_log={args.save_event_log}.",
    ])

    return _save_markdown_report(lines, output_root / "single_run_report.md")

def _save_suite_report(

    *,

    suite_result: ExperimentSuiteResult,

    output_root: Path,

    suite_dir: Path,

) -> Path:

    lines = [
        "# Отчёт по серии экспериментов",
        "",
        "## Что произошло",
        (
            "Серия прогонов выполнена. В этом отчёте собраны агрегированные "
            "итоги по каждому сценарию простым текстом."
        ),
        "",
        "## Общая информация",
        f"- Имя серии: **{suite_result.suite_name}**.",
        f"- Время формирования: **{suite_result.created_at}**.",
        f"- Число сценариев: **{len(suite_result.scenario_results)}**.",
        "",
        "## Итоги по сценариям",
    ]

    for scenario_key, result in suite_result.scenario_results.items():

        lines.append(f"### {scenario_key}")
        lines.append(f"- Описание: {result.scenario_description}.")
        lines.append(f"- Replications: **{result.replications}**.")
        for metric_name in ("throughput", "loss_probability", "mean_num_jobs", "mean_occupied_resource"):
            summary = result.metric_summaries.get(metric_name)
            if summary is None:
                continue
            lines.append(
                f"- {metric_name}: mean={summary.mean:.6f}, "
                f"95% CI=[{summary.ci_low:.6f}, {summary.ci_high:.6f}]."
            )
        lines.append("")

    lines.extend([
        "## Где лежат артефакты",
        f"- Папка серии: `{suite_dir}`.",
        f"- Таблицы/JSON: `{suite_dir / 'aggregated_summary.csv'}`, "
        f"`{suite_dir / 'all_runs.csv'}`, `{suite_dir / 'suite_result.json'}`.",
    ])

    return _save_markdown_report(lines, output_root / "suite_report.md")

def _save_plots_report(

    *,

    suite_data,

    input_path: str | Path,

    output_dir: Path,

) -> Path:

    png_count = len(list(output_dir.glob("*.png")))

    lines = [
        "# Отчёт по построению графиков",
        "",
        "## Что произошло",
        "Графики успешно построены на основании сохранённых результатов серии.",
        "",
        "## Источник данных",
        f"- Вход: `{input_path}`.",
        f"- Набор: **{suite_data.suite_name}**.",
        f"- Создан: **{suite_data.created_at}**.",
        f"- Сценариев: **{len(suite_data.scenario_results)}**.",
        "",
        "## Результат",
        f"- Папка графиков: `{output_dir}`.",
        f"- Найдено PNG-файлов после генерации: **{png_count}**.",
    ]

    return _save_markdown_report(lines, output_dir.parent / "plots_report.md")

def run_single_mode(args: argparse.Namespace) -> Path:

    workload = standard_workload_family(args.mean_workload)["exponential"]

    scenario = build_base_scenario(workload_distribution=workload)

    scenario = _override_simulation_config(

        scenario,

        max_time=args.max_time,

        warmup_time=args.warmup_time,

        replications=None,

        record_state_trace=args.record_state_trace,

        save_event_log=args.save_event_log,

    )

    print_scenario_summary(scenario)

    result = simulate_one_run(

        scenario=scenario,

        replication_index=args.replication_index,

        seed=args.seed,

    )

    print_run_summary(result)

    output_root = _make_run_root(args.output_root, "single_runs")

    json_path = _save_single_run_result(result, output_root)

    report_path = _save_single_run_report(
        result=result,
        scenario=scenario,
        args=args,
        output_root=output_root,
        json_path=json_path,
    )

    print("=" * 80)

    print(f"Результат одного прогона сохранён в: {json_path}")
    print(f"Markdown-отчёт сохранён в: {report_path}")

    print("=" * 80)

    return output_root

def _build_suite_scenarios(args: argparse.Namespace) -> dict[str, ScenarioConfig]:

    if args.scenario_family == "default":

        scenarios = build_default_experiment_suite(mean_workload=args.mean_workload)

    elif args.scenario_family == "sensitivity":

        scenarios = build_sensitivity_scenarios(mean_workload=args.mean_workload)

    else:

        raise ValueError(f"Неизвестное семейство сценариев: {args.scenario_family}")

    updated: dict[str, ScenarioConfig] = {}

    for key, scenario in scenarios.items():

        updated[key] = _override_simulation_config(

            scenario,

            max_time=args.max_time,

            warmup_time=args.warmup_time,

            replications=args.replications,

            record_state_trace=args.record_state_trace,

            save_event_log=args.save_event_log,

        )

    return updated

def run_suite_mode(args: argparse.Namespace) -> Path:

    scenarios = _build_suite_scenarios(args)

    suite_result = run_experiment_suite(

        scenarios,

        suite_name=args.suite_name,

        ci_level=args.ci_level,

        keep_full_run_results=args.keep_full_run_results,

    )

    print_experiment_suite_summary(suite_result)

    output_root = _make_run_root(args.output_root, "experiments")

    suite_dir = save_experiment_suite(suite_result, output_root)

    report_path = _save_suite_report(
        suite_result=suite_result,
        output_root=output_root,
        suite_dir=suite_dir,
    )

    print("=" * 80)

    print(f"Результаты серии экспериментов сохранены в: {suite_dir}")
    print(f"Markdown-отчёт сохранён в: {report_path}")

    print("=" * 80)

    return output_root

def run_plots_mode(args: argparse.Namespace) -> Path:

    suite_data = load_suite_data(args.input)

    json_path = resolve_suite_result_json(args.input)

    output_dir = Path(args.output_dir) if args.output_dir else json_path.parent / "plots"

    generate_standard_plots(

        suite_data,

        output_dir=output_dir,

        dpi=args.dpi,

        extra_metrics=args.metrics,

    )

    print("=" * 80)

    print(f"Папка с графиками: {output_dir}")

    report_path = _save_plots_report(
        suite_data=suite_data,
        input_path=args.input,
        output_dir=output_dir,
    )

    print(f"Markdown-отчёт сохранён в: {report_path}")

    print("=" * 80)

    return Path(output_dir)

def run_full_mode(args: argparse.Namespace) -> Path:

    suite_dir = run_suite_mode(args)

    suite_data = load_suite_data(suite_dir)

    plots_dir = suite_dir / "plots"

    generate_standard_plots(

        suite_data,

        output_dir=plots_dir,

        dpi=args.dpi,

        extra_metrics=args.metrics,

    )

    print("=" * 80)

    print("Полный запуск завершён.")

    print(f"Результаты серии: {suite_dir}")

    print(f"Графики: {plots_dir}")

    report_path = _save_plots_report(
        suite_data=suite_data,
        input_path=suite_dir,
        output_dir=plots_dir,
    )

    print(f"Markdown-отчёт по графикам: {report_path}")

    print("=" * 80)

    return suite_dir

def build_arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        description="Единая точка входа для симуляции, экспериментов и plotting"

    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Выполнить один прогон")

    single.add_argument("--seed", type=int, default=None, help="Явный seed для одного прогона")

    single.add_argument("--replication-index", type=int, default=0, help="Индекс повтора")

    single.add_argument("--max-time", type=float, default=None, help="Полное время моделирования")

    single.add_argument("--warmup-time", type=float, default=None, help="Время разгона")

    single.add_argument("--mean-workload", type=float, default=1.0, help="Средний объём работы")

    single.add_argument("--record-state-trace", action="store_true", help="Сохранять траекторию состояния")

    single.add_argument("--save-event-log", action="store_true", help="Сохранять лог событий")

    single.add_argument("--output-root", default="results", help="Корневой каталог результатов")

    single.set_defaults(func=run_single_mode)

    suite = subparsers.add_parser("suite", help="Выполнить серию экспериментов")

    suite.add_argument("--scenario-family", choices=["default", "sensitivity"], default="default")

    suite.add_argument("--suite-name", default="experiment_suite", help="Имя набора экспериментов")

    suite.add_argument("--mean-workload", type=float, default=1.0, help="Средний объём работы")

    suite.add_argument("--replications", type=int, default=None, help="Число повторов на сценарий")

    suite.add_argument("--max-time", type=float, default=None, help="Полное время моделирования")

    suite.add_argument("--warmup-time", type=float, default=None, help="Время разгона")

    suite.add_argument("--ci-level", type=float, default=0.95, help="Уровень доверительного интервала")

    suite.add_argument("--record-state-trace", action="store_true", help="Сохранять траекторию состояния")

    suite.add_argument("--save-event-log", action="store_true", help="Сохранять лог событий")

    suite.add_argument("--keep-full-run-results", action="store_true", help="Хранить полные результаты прогонов в памяти")

    suite.add_argument("--output-root", default="results", help="Корневой каталог результатов")

    suite.set_defaults(func=run_suite_mode)

    plots = subparsers.add_parser("plots", help="Построить графики по уже сохранённым результатам")

    plots.add_argument("--input", required=True, help="Путь к директории с результатами или к suite_result.json")

    plots.add_argument("--output-dir", default=None, help="Папка для графиков")

    plots.add_argument("--dpi", type=int, default=200, help="Разрешение PNG")

    plots.add_argument("--metrics", nargs="*", default=None, help="Дополнительные метрики")

    plots.set_defaults(func=run_plots_mode)

    full = subparsers.add_parser("full", help="Серия экспериментов + графики")

    full.add_argument("--scenario-family", choices=["default", "sensitivity"], default="default")

    full.add_argument("--suite-name", default="full_pipeline", help="Имя набора экспериментов")

    full.add_argument("--mean-workload", type=float, default=1.0, help="Средний объём работы")

    full.add_argument("--replications", type=int, default=None, help="Число повторов на сценарий")

    full.add_argument("--max-time", type=float, default=None, help="Полное время моделирования")

    full.add_argument("--warmup-time", type=float, default=None, help="Время разгона")

    full.add_argument("--ci-level", type=float, default=0.95, help="Уровень доверительного интервала")

    full.add_argument("--record-state-trace", action="store_true", help="Сохранять траекторию состояния")

    full.add_argument("--save-event-log", action="store_true", help="Сохранять лог событий")

    full.add_argument("--keep-full-run-results", action="store_true", help="Хранить полные результаты прогонов в памяти")

    full.add_argument("--output-root", default="results", help="Корневой каталог результатов")

    full.add_argument("--dpi", type=int, default=200, help="Разрешение PNG")

    full.add_argument("--metrics", nargs="*", default=None, help="Дополнительные метрики для plotting")

    full.set_defaults(func=run_full_mode)

    return parser

def main() -> None:

    parser = build_arg_parser()

    args = parser.parse_args()

    args.func(args)

if __name__ == "__main__":

    main()
