from pathlib import Path
import json

import experiment_values as v
import values_validation as vv

BASE_DIR = Path(__file__).resolve().parent


def resolve_workload_family(values_module) -> list[str]:
    return vv.resolve_workload_family(values_module)


def export_values(output_path: str = None) -> Path:
    vv.validate_experiment_values(v)
    resolved_workload_family = resolve_workload_family(v)

    payload = {
        "suite_name": v.SUITE_NAME,
        "mean_workload": v.MEAN_WORKLOAD,
        "replications": v.REPLICATIONS,
        "max_time": v.MAX_TIME,
        "warmup_time": v.WARMUP_TIME,
        "base_seed": v.BASE_SEED,
        "record_state_trace": v.RECORD_STATE_TRACE,
        "save_event_log": v.SAVE_EVENT_LOG,
        "keep_full_run_results": v.KEEP_FULL_RUN_RESULTS,
        "animation_log_max_jobs": v.ANIMATION_LOG_MAX_JOBS,
        "full_run_results_per_scenario": v.FULL_RUN_RESULTS_PER_SCENARIO,

        # Пока Rust может это не использовать, но логически это уже часть внешней конфигурации
        "system_architecture": v.SYSTEM_ARCHITECTURE,
        "service_speed_profile": v.SERVICE_SPEED_PROFILE,
        "arrival_rate_profile": v.ARRIVAL_RATE_PROFILE,
        "workload_family_profile": v.WORKLOAD_FAMILY_PROFILE,
        "fixed_workload": v.FIXED_WORKLOAD,
        "queue_capacity": vv.compute_queue_capacity(v),

        "capacity_k": v.CAPACITY_K,
        "servers_n": v.SERVERS_N,
        "total_resource_r": v.TOTAL_RESOURCE_R,

        "arrival_normal_value": v.ARRIVAL_NORMAL_VALUE,
        "arrival_threshold_offset": v.ARRIVAL_THRESHOLD_OFFSET,
        "arrival_reduced_value": v.ARRIVAL_REDUCED_VALUE,
        "arrival_full_state_value": v.ARRIVAL_FULL_STATE_VALUE,

        "service_start_value": v.SERVICE_START_VALUE,
        "service_step": v.SERVICE_STEP,
        "service_floor_value": v.SERVICE_FLOOR_VALUE,

        "resource_values": v.RESOURCE_VALUES,
        "resource_probabilities": v.RESOURCE_PROBABILITIES,

        "workload_family": resolved_workload_family,
        "workload_hyperexp_p": v.WORKLOAD_HYPEREXP_P,
        "workload_hyperexp_fast_multiplier": v.WORKLOAD_HYPEREXP_FAST_MULTIPLIER,
        "workload_hyperexp_heavy_p": v.WORKLOAD_HYPEREXP_HEAVY_P,
        "workload_hyperexp_heavy_fast_multiplier": v.WORKLOAD_HYPEREXP_HEAVY_FAST_MULTIPLIER,

        "arrival_process_family": v.ARRIVAL_PROCESS_FAMILY,
        "arrival_hyperexp_p": v.ARRIVAL_HYPEREXP_P,
        "arrival_hyperexp_fast_multiplier": v.ARRIVAL_HYPEREXP_FAST_MULTIPLIER,
    }

    if output_path is None:
        path = BASE_DIR / "generated" / "experiment_values.json"
    else:
        path = Path(output_path)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    out = export_values()
    print(f"Written: {out}")
    print(vv.validation_summary(v))
