from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PY_DIR = PROJECT_ROOT / "py"


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT), check=True)


def generate_experiment_json() -> Path:
    run_command([sys.executable, str(PY_DIR / "export_values.py")], cwd=PY_DIR)
    out = PY_DIR / "generated" / "experiment_values.json"
    if not out.exists():
        raise FileNotFoundError(f"JSON не был создан: {out}")
    return out


def run_rust_full(
    release: bool,
    suite_name: str | None,
    replications: int | None,
    max_time: float | None,
    warmup_time: float | None,
) -> None:
    cmd = ["cargo", "run"]
    if release:
        cmd.append("--release")
    cmd.extend(["--", "full"])

    if suite_name:
        cmd.extend(["--suite-name", suite_name])
    if replications is not None:
        cmd.extend(["--replications", str(replications)])
    if max_time is not None:
        cmd.extend(["--max-time", str(max_time)])
    if warmup_time is not None:
        cmd.extend(["--warmup-time", str(warmup_time)])

    run_command(cmd, cwd=PROJECT_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "1) Берёт значения из py/experiment_values.py, "
            "2) генерирует py/generated/experiment_values.json, "
            "3) запускает `cargo run -- full`."
        )
    )
    parser.add_argument("--release", action="store_true", help="Запустить rust в release-режиме")
    parser.add_argument("--suite-name", default=None, help="Опционально переопределить suite_name")
    parser.add_argument("--replications", type=int, default=None, help="Опционально переопределить replications")
    parser.add_argument("--max-time", type=float, default=None, help="Опционально переопределить max_time")
    parser.add_argument("--warmup-time", type=float, default=None, help="Опционально переопределить warmup_time")
    args = parser.parse_args()

    print("Шаг 1/3: Обновите py/experiment_values.py при необходимости (вручную).")
    print("Шаг 2/3: Генерируем JSON из Python-конфига...")
    out = generate_experiment_json()
    print(f"JSON создан: {out}")

    print("Шаг 3/3: Запускаем Rust full pipeline...")
    run_rust_full(
        release=args.release,
        suite_name=args.suite_name,
        replications=args.replications,
        max_time=args.max_time,
        warmup_time=args.warmup_time,
    )
    print("Готово.")


if __name__ == "__main__":
    main()
