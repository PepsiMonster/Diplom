from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import values as v


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PY_DIR = PROJECT_ROOT / "py"
CUDA_DIR = PROJECT_ROOT / "cuda"
KERNEL_CU = CUDA_DIR / "sim_kernel.cu"
KERNEL_PTX = CUDA_DIR / "sim_kernel.ptx"


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT), check=True)


def run_command_capture(
    cmd: list[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    print(">", " ".join(str(x) for x in cmd))
    return subprocess.run(
        cmd,
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        capture_output=True,
    )


def generate_experiment_json() -> Path:
    run_command([sys.executable, str(PY_DIR / "export_values.py")], cwd=PY_DIR)
    out = PY_DIR / "generated" / "experiment_values.json"
    if not out.exists():
        raise FileNotFoundError(f"JSON не был создан: {out}")
    return out


def ensure_kernel_ptx() -> None:
    if not KERNEL_CU.exists():
        raise FileNotFoundError(f"CUDA kernel source not found: {KERNEL_CU}")

    must_rebuild = (not KERNEL_PTX.exists()) or (KERNEL_CU.stat().st_mtime > KERNEL_PTX.stat().st_mtime)
    if not must_rebuild:
        print(f"PTX актуален: {KERNEL_PTX}")
        return

    nvcc = shutil.which("nvcc")
    if nvcc is None:
        raise RuntimeError(
            "PTX требуется пересобрать, но nvcc не найден в PATH. "
            "Установите CUDA Toolkit или добавьте nvcc в PATH."
        )

    print("PTX отсутствует или устарел. Пересобираю kernel...")
    base_cmd = [
        nvcc,
        "-ptx",
        str(KERNEL_CU),
        "-o",
        str(KERNEL_PTX),
    ]
    if platform.system().lower().startswith("win"):
        ccbin = _find_msvc_compiler_dir_from_path()
        if ccbin is not None:
            base_cmd.extend(["-ccbin", str(ccbin)])

    result = run_command_capture(base_cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        return

    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    cl_missing = (
        "Cannot find compiler 'cl.exe' in PATH" in stderr
        or "Cannot find compiler 'cl.exe' in PATH" in stdout
    )

    if platform.system().lower().startswith("win") and cl_missing:
        vcvars = _find_vcvars64_bat()
        if vcvars is not None:
            print("Обнаружена ошибка cl.exe в PATH. Пробую запустить через vcvars64.bat ...")
            cmdline = (
                f'call "{vcvars}" && "{nvcc}" -ptx "{KERNEL_CU}" -o "{KERNEL_PTX}"'
            )
            wrapped = ["cmd.exe", "/d", "/s", "/c", cmdline]
            retry = run_command_capture(wrapped, cwd=PROJECT_ROOT)
            if retry.returncode == 0:
                return
            stderr = (retry.stderr or "").strip()
            stdout = (retry.stdout or "").strip()

    raise RuntimeError(
        "Не удалось собрать PTX через nvcc.\n"
        f"stdout:\n{stdout}\n\nstderr:\n{stderr}\n\n"
        "Подсказка: откройте 'x64 Native Tools Command Prompt for VS 2022' "
        "или добавьте cl.exe/VC tools в PATH."
    )


def _find_vcvars64_bat() -> Path | None:
    env_path = os.environ.get("VCVARS64_BAT")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    vswhere_default = Path(
        r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    if not vswhere_default.exists():
        return None

    try:
        out = subprocess.check_output(
            [
                str(vswhere_default),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            text=True,
        ).strip()
    except Exception:
        return None

    if not out:
        return None

    candidate = Path(out) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if candidate.exists():
        return candidate
    return None


def _find_msvc_compiler_dir_from_path() -> Path | None:
    raw_path = os.environ.get("PATH", "")
    for item in raw_path.split(os.pathsep):
        entry = item.strip().strip('"')
        if not entry:
            continue
        p = Path(entry)
        if p.is_file() and p.name.lower() == "cl.exe":
            return p.parent
        if p.is_dir():
            cl = p / "cl.exe"
            if cl.exists():
                return p
    return None


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
    gpu_block_size: int | None,
    gpu_save_pi_hat: bool,
    verbose: bool,
    compact_summary: bool,
    compute_only: bool,
) -> float:
    cmd = ["cargo", "run"]
    if not verbose:
        cmd.append("--quiet")

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
    if compact_summary:
        cmd.append("--compact-summary")
    if compute_only:
        cmd.append("--compute-only")

    env = None
    if backend == "gpu":
        env = dict(os.environ)
        if gpu_block_size is not None:
            env["SIM_GPU_BLOCK_SIZE"] = str(gpu_block_size)
        env["SIM_GPU_SAVE_PI_HAT"] = "1" if gpu_save_pi_hat else "0"
        if not verbose:
            env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Awarnings").strip()

    started = time.perf_counter()
    print(">", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True, env=env)
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
    parser.add_argument(
        "--gpu-block-size",
        type=int,
        choices=[64, 128, 256],
        default=128,
        help="Размер CUDA блока для GPU backend",
    )
    parser.add_argument(
        "--gpu-no-pi-hat",
        action="store_true",
        help="Отключить сбор pi_hat (ускоренный режим без state_times)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Печатать полный вывод cargo/rustc (включая предупреждения)",
    )
    parser.add_argument(
        "--full-summary",
        action="store_true",
        help="Печатать полный suite summary (по умолчанию — компактный вывод)",
    )
    parser.add_argument(
        "--compute-only",
        action="store_true",
        help="Не сохранять выходные CSV/JSON/TXT (режим speed benchmark)",
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

    if args.backend == "gpu":
        print(
            f"GPU options: block_size={args.gpu_block_size}, save_pi_hat={not args.gpu_no_pi_hat}"
        )
        print("Шаг 1.5/4: Проверка и сборка PTX kernel (при необходимости)...")
        ensure_kernel_ptx()
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
        try:
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
                gpu_block_size=args.gpu_block_size,
                gpu_save_pi_hat=not args.gpu_no_pi_hat,
                verbose=args.verbose,
                compact_summary=not args.full_summary,
                compute_only=args.compute_only,
            )
        except subprocess.CalledProcessError as e:
            print(
                f"Preflight завершился с ошибкой (exit={e.returncode}). "
                "Для --with-estimate продолжаю основной запуск без оценки."
            )
            if args.estimate_only:
                raise
            preflight_elapsed = None

        if preflight_elapsed is not None:
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
        gpu_block_size=args.gpu_block_size,
        gpu_save_pi_hat=not args.gpu_no_pi_hat,
        verbose=args.verbose,
        compact_summary=not args.full_summary,
        compute_only=args.compute_only,
    )
    print(f"Rust pipeline elapsed: {run_elapsed:.1f} sec ({run_elapsed/60.0:.1f} min)")
    print()

    if args.compute_only:
        print("Шаг 3/4 и 4/4 пропущены: включён режим --compute-only.")
        print()
        print("Готово (compute-only).")
        return

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
