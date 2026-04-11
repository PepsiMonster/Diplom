from __future__ import annotations

from pathlib import Path
import json

import values as v
import values_validation as vv

BASE_DIR = Path(__file__).resolve().parent


def export_values(output_path: str | Path | None = None) -> Path:
    vv.validate_experiment_values(v)

    payload = {
        "suite_name": v.SUITE_NAME,
        "replications": int(v.REPLICATIONS),
        "max_time": float(v.MAX_TIME),
        "warmup_time": float(v.WARMUP_TIME),
        "base_seed": int(v.BASE_SEED),

        "servers_n": int(v.SERVERS_N),
        "total_resource_r": int(v.TOTAL_RESOURCE_R),

        "arrival_rate_levels": [float(x) for x in v.ARRIVAL_RATE_LEVELS],
        "service_speed_levels": [float(x) for x in v.SERVICE_SPEED_LEVELS],

        "resource_values": [int(x) for x in v.RESOURCE_VALUES],
        "resource_probabilities": [float(x) for x in v.RESOURCE_PROBABILITIES],

        "mean_workload": float(v.MEAN_WORKLOAD),

        "workload_family_profile": v.WORKLOAD_FAMILY_PROFILE,
        "fixed_workload": v.FIXED_WORKLOAD,
        "workload_family_basic": list(v.WORKLOAD_FAMILY_BASIC),
        "workload_family_full": list(v.WORKLOAD_FAMILY_FULL),

        "workload_hyperexp_p": float(v.WORKLOAD_HYPEREXP_P),
        "workload_hyperexp_fast_multiplier": float(v.WORKLOAD_HYPEREXP_FAST_MULTIPLIER),
        "workload_hyperexp_heavy_p": float(v.WORKLOAD_HYPEREXP_HEAVY_P),
        "workload_hyperexp_heavy_fast_multiplier": float(v.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER),

        "arrival_process_family": list(v.ARRIVAL_PROCESS_FAMILY),
        "arrival_hyperexp_p": float(v.ARRIVAL_HYPEREXP_P),
        "arrival_hyperexp_fast_multiplier": float(v.ARRIVAL_HYPEREXP_FAST_MULTIPLIER),
    }

    if output_path is None:
        path = BASE_DIR / "generated" / "experiment_values.json"
    else:
        path = Path(output_path).expanduser()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    out = export_values()
    print(f"Written: {out.resolve()}")
    print(vv.validation_summary(v))