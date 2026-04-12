from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import values as v


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PY_DIR = PROJECT_ROOT / "py"


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT), check=True)


def generate_experiment_json() -> Path:
    run_command([sys.executable, str(PY_DIR / "export_values.py")], cwd=PY_DIR)
    out = PY_DIR / "generated" / "experiment_values.json"
    if not out.exists():
        raise FileNotFoundError(f"JSON не был создан: {out}")
    return out


def list_existing_dirs(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {p.resolve() for p in root.iterdir() if p.is_dir()}


def find_latest_output_dir(root: Path, before: set[Path]) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Корневая папка результатов не найдена: {root}")

    after = list_existing_dirs(root)
    created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if created:
        return created[0]

    candidates = sorted(after, key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        f"Не удалось найти созданную папку результатов внутри: {root}"
    )


def run_rust_full(
    *,
    release: bool,
    input_json: Path,
    scenario_family: str,
    backend: str,
    output_root: Path,
    suite_name: str | None,
    replications: int | None,
    max_time: float | None,
    warmup_time: float | None,
) -> float:
    cmd = ["cargo", "run"]

    if release:
        cmd.append("--release")

    # Явно управляем feature-набором Cargo.
    if backend == "cpu-ref":
        cmd.extend(["--no-default-features", "--features", "cpu-ref"])
    elif backend == "gpu":
        cmd.extend(["--no-default-features", "--features", "gpu"])
    else:
        raise ValueError(f"Неизвестный backend: {backend!r}")

    cmd.extend(
        [
            "--",
            "full",
            "--input",
            str(input_json),
            "--scenario-family",
            scenario_family,
            "--backend",
            backend,
            "--output-root",
            str(output_root),
        ]
    )

    if suite_name is not None:
        cmd.extend(["--suite-name", suite_name])
    if replications is not None:
        cmd.extend(["--replications", str(replications)])
    if max_time is not None:
        cmd.extend(["--max-time", str(max_time)])
    if warmup_time is not None:
        cmd.extend(["--warmup-time", str(warmup_time)])

    started = time.perf_counter()
    run_command(cmd, cwd=PROJECT_ROOT)
    return time.perf_counter() - started


def _resolved_workload_family(values_payload: dict, profile: str) -> list[str]:
    if profile == "fixed":
        return [str(values_payload["fixed_workload"])]
    if profile == "basic":
        return [str(x) for x in values_payload["workload_family_basic"]]
    if profile == "full":
        return [str(x) for x in values_payload["workload_family_full"]]
    raise ValueError(f"Unknown workload_family_profile: {profile!r}")


def estimate_num_runs(values_payload: dict, scenario_family: str, replications: int) -> int:
    arrival_levels = values_payload["arrival_rate_levels"]
    service_levels = values_payload["service_speed_levels"]
    arrivals = values_payload["arrival_process_family"]
    workloads = _resolved_workload_family(values_payload, values_payload["workload_family_profile"])

    if scenario_family == "base":
        scenarios = len(arrival_levels) * len(service_levels)
    elif scenario_family == "workload-sensitivity":
        scenarios = len(workloads) * len(arrival_levels) * len(service_levels)
    elif scenario_family == "arrival-sensitivity":
        scenarios = len(arrivals) * len(arrival_levels) * len(service_levels)
    elif scenario_family == "combined-sensitivity":
        scenarios = len(workloads) * len(arrivals) * len(arrival_levels) * len(service_levels)
    else:
        raise ValueError(f"Неизвестный scenario_family: {scenario_family!r}")

    return scenarios * replications


def run_plots(
    *,
    suite_result_json: Path,
    output_dir: Path,
    dpi: int,
    metrics: list[str],
) -> None:
    plots_script = PY_DIR / "plots.py"
    if not plots_script.exists():
        print(f"plots.py не найден, пропускаю построение графиков: {plots_script}")
        return

    if not suite_result_json.exists():
        raise FileNotFoundError(f"Не найден suite_result.json: {suite_result_json}")

    cmd = [
        sys.executable,
        str(plots_script),
        "--input",
        str(suite_result_json),
        "--output-dir",
        str(output_dir),
        "--dpi",
        str(dpi),
    ]

    if metrics:
        cmd.append("--metrics")
        cmd.extend(metrics)

    run_command(cmd, cwd=PY_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Полный запуск GPU-ветки: "
            "1) валидация values.py, "
            "2) генерация py/generated/experiment_values.json, "
            "3) cargo run -- full, "
            "4) запуск plots.py."
        )
    )

    parser.add_argument("--release", action="store_true", help="Запустить Rust в release-режиме")
    parser.add_argument(
        "--scenario-family",
        choices=["base", "workload-sensitivity", "arrival-sensitivity", "combined-sensitivity"],
        default="base",
        help="Какое семейство сценариев запускать",
    )
    parser.add_argument(
        "--backend",
        choices=["cpu-ref", "gpu"],
        default="cpu-ref",
        help="Какой backend использовать",
    )
    parser.add_argument(
        "--suite-name",
        default=None,
        help="Опционально переопределить имя серии",
    )
    parser.add_argument(
        "--replications",
        type=int,
        default=None,
        help="Опционально переопределить число повторов",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=None,
        help="Опционально переопределить max_time",
    )
    parser.add_argument(
        "--warmup-time",
        type=float,
        default=None,
        help="Опционально переопределить warmup_time",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "results"),
        help="Корневая папка результатов",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Не запускать plots.py после расчёта",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Сделать только быстрый preflight и вывести оценку времени полного прогона",
    )
    parser.add_argument(
        "--with-estimate",
        action="store_true",
        help="Сначала выполнить быстрый preflight с оценкой времени, затем основной прогон",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI для plots.py",
    )
    parser.add_argument(
        "--metrics",
        nargs="*",
        default=[],
        help="Опциональный список метрик для plots.py",
    )

    args = parser.parse_args()

    if args.estimate_only and args.with_estimate:
        parser.error("Флаги --estimate-only и --with-estimate нельзя использовать одновременно")

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    print("Шаг 1/4: Генерация JSON из Python-конфига...")
    json_path = generate_experiment_json()
    print(f"JSON создан: {json_path.resolve()}")
    print()

    values_payload = json.loads(json_path.read_text(encoding="utf-8"))
    effective_suite_name = args.suite_name or v.SUITE_NAME

    target_replications = args.replications if args.replications is not None else int(values_payload["replications"])
    target_max_time = args.max_time if args.max_time is not None else float(values_payload["max_time"])
    target_warmup_time = args.warmup_time if args.warmup_time is not None else float(values_payload["warmup_time"])

    preflight_replications = min(2, target_replications)
    preflight_max_time = min(2000.0, max(500.0, target_max_time / 10.0))
    preflight_warmup_time = min(200.0, max(50.0, target_warmup_time / 10.0))

    do_preflight = args.estimate_only or args.with_estimate
    if do_preflight:
        print("Preflight: быстрый прогон для оценки времени...")
        preflight_elapsed = run_rust_full(
            release=args.release,
            input_json=json_path,
            scenario_family=args.scenario_family,
            backend=args.backend,
            output_root=output_root,
            suite_name=f"{effective_suite_name}__preflight",
            replications=preflight_replications,
            max_time=preflight_max_time,
            warmup_time=preflight_warmup_time,
        )

        target_runs = estimate_num_runs(values_payload, args.scenario_family, target_replications)
        preflight_runs = estimate_num_runs(values_payload, args.scenario_family, preflight_replications)

        estimate_seconds = (
            preflight_elapsed
            * (target_replications / preflight_replications)
            * (target_max_time / preflight_max_time)
            * (target_runs / preflight_runs)
        )

        print()
        print("Оценка времени полного прогона:")
        print(f"  preflight elapsed: {preflight_elapsed:.1f} sec")
        print(f"  target runs: {target_runs}, preflight runs: {preflight_runs}")
        print(f"  estimated full runtime: {estimate_seconds:.1f} sec ({estimate_seconds/60.0:.1f} min)")
        print()

        if args.estimate_only:
            print("Запрошен только preflight (--estimate-only), основной запуск пропущен.")
            return

    before_dirs = list_existing_dirs(output_root)

    print("Шаг 2/4: Запуск Rust pipeline...")
    run_elapsed = run_rust_full(
        release=args.release,
        input_json=json_path,
        scenario_family=args.scenario_family,
        backend=args.backend,
        output_root=output_root,
        suite_name=effective_suite_name,
        replications=args.replications,
        max_time=args.max_time,
        warmup_time=args.warmup_time,
    )
    print(f"Rust pipeline elapsed: {run_elapsed:.1f} sec ({run_elapsed/60.0:.1f} min)")
    print()

    print("Шаг 3/4: Поиск созданной папки результатов...")
    suite_output_dir = find_latest_output_dir(output_root, before_dirs)
    suite_result_json = suite_output_dir / "suite_result.json"
    print(f"Найдена папка результатов: {suite_output_dir}")
    print(f"Найден suite_result.json: {suite_result_json}")
    print()

    if args.skip_plots:
        print("Шаг 4/4: Построение графиков пропущено по флагу --skip-plots.")
    else:
        print("Шаг 4/4: Построение графиков...")
        plots_output_dir = suite_output_dir / "plots"
        run_plots(
            suite_result_json=suite_result_json,
            output_dir=plots_output_dir,
            dpi=args.dpi,
            metrics=args.metrics,
        )
        print(f"Графики сохранены в: {plots_output_dir}")

    print()
    print("Готово.")
    print(f"Папка серии: {suite_output_dir}")


if __name__ == "__main__":
    main()
