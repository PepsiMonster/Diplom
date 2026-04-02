"""
Запускает весь рабочий конвейер:
1. выполняет серию экспериментов;
2. сохраняет таблицы результатов;
3. строит графики по этим таблицам.
"""

from __future__ import annotations

<<<<<<< HEAD
import csv
=======
>>>>>>> main
import json
from pathlib import Path

from experiments import run_all_experiments
from plots import build_all_plots


def save_pipeline_report(
    *,
    experiment_outputs: dict[str, Path],
    plot_outputs: dict[str, Path],
    output_path: Path,
) -> None:
    """
    Сохраняет единый JSON-отчёт по артефактам конвейера.
    """
    report = {
        "status": "ok",
        "artifacts": {
            "experiments": {name: str(path) for name, path in experiment_outputs.items()},
            "plots": {name: str(path) for name, path in plot_outputs.items()},
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

<<<<<<< HEAD

def save_pipeline_report_txt(
    *,
    experiment_outputs: dict[str, Path],
    plot_outputs: dict[str, Path],
    output_path: Path,
) -> None:
    """
    Сохраняет короткий текстовый отчёт по результатам прогона.
    """
    lines: list[str] = [
        "Короткий текстовый отчёт по прогону",
        "=" * 44,
        "",
        "Сформированные артефакты:",
    ]
    for name, path in experiment_outputs.items():
        lines.append(f"- {name}: {path}")
    for name, path in plot_outputs.items():
        lines.append(f"- {name}: {path}")

    summary_csv = experiment_outputs.get("summary_results_csv")
    if summary_csv and summary_csv.exists():
        lines.extend(["", "Агрегированная сводка по сценариям:"])
        with summary_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scenario = row.get("scenario_name", "unknown")
                workload = row.get("workload_name", "unknown")
                throughput = row.get("throughput_mean", "n/a")
                loss = row.get("loss_probability_mean", "n/a")
                mean_jobs = row.get("mean_num_jobs_mean", "n/a")
                lines.append(
                    f"- {scenario} ({workload}): "
                    f"throughput={throughput}, loss_probability={loss}, mean_num_jobs={mean_jobs}"
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    experiment_outputs = run_all_experiments()
    plot_outputs = build_all_plots()
    report_path = Path("results") / "pipeline_report.json"
    text_report_path = Path("results") / "pipeline_report.txt"
    save_pipeline_report(
        experiment_outputs=experiment_outputs,
        plot_outputs=plot_outputs,
        output_path=report_path,
    )
    save_pipeline_report_txt(
        experiment_outputs=experiment_outputs,
        plot_outputs=plot_outputs,
        output_path=text_report_path,
    )

    print(f"Конвейер завершён успешно. Отчёты: {report_path}, {text_report_path}")
=======

def main() -> None:
    experiment_outputs = run_all_experiments()
    plot_outputs = build_all_plots()
    report_path = Path("results") / "pipeline_report.json"
    save_pipeline_report(
        experiment_outputs=experiment_outputs,
        plot_outputs=plot_outputs,
        output_path=report_path,
    )

    print(f"Конвейер завершён успешно. Отчёт: {report_path}")
>>>>>>> main


if __name__ == "__main__":
    main()
