"""
Запускает весь рабочий конвейер:
1. выполняет серию экспериментов;
2. сохраняет таблицы результатов;
3. строит графики по этим таблицам.
"""

from __future__ import annotations

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


if __name__ == "__main__":
    main()
