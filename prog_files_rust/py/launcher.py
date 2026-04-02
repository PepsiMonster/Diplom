# запуск теперь через python py/launcher.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from export_values import export_values


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUST_BINARY = PROJECT_ROOT / "target" / "release" / "prog_files_rust.exe"
PYTHON_DIR = PROJECT_ROOT / "py"


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=True)


def ensure_release_binary() -> None:
    if not RUST_BINARY.exists():
        run_command(["cargo", "build", "--release"])


def export_params_json() -> Path:
    out = export_values(str(PYTHON_DIR / "generated" / "experiment_values.json"))
    print(f"Exported params JSON: {out}")
    return Path(out)


def run_rust_single() -> None:
    ensure_release_binary()
    export_params_json()

    run_command([
        str(RUST_BINARY),
        "single",
    ])


def run_rust_suite() -> None:
    ensure_release_binary()
    export_params_json()

    run_command([
        str(RUST_BINARY),
        "suite",
        "--suite-name",
        "baseline",
    ])


def run_python_plots(input_path: str | Path | None = None) -> None:
    script = PYTHON_DIR / "plots.py"

    if input_path is None:
        input_path = PROJECT_ROOT / "results"

    run_command([
        sys.executable,
        str(script),
        "--input",
        str(input_path),
    ])


def main() -> None:
    # Простейший вариант: suite без длинной cargo-команды.
    run_rust_suite()

    # Позже можно автоматически искать последнюю директорию результатов
    # и сразу рисовать графики. Пока plots вызываем отдельно.
    print("Suite run finished.")


if __name__ == "__main__":
    main()