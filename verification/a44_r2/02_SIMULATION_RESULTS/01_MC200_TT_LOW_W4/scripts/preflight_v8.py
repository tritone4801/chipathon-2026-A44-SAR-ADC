#!/usr/bin/env python3
"""Audit the isolated V8 quick-regression package before timed execution."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from v7_common import ROOT, read_csv, sha256_file, write_json_atomic


SOURCE_ROOT = Path(
    "/foss/designs/manual_goal/verification/A44_FAST64_D3_ONLY_MC200_V7"
)
PRODUCTION_ROOT = Path("/foss/designs/manual_goal/analog/SAR_CURRENT")
CORE_SEEDS = (1, 21, 25, 44, 48, 64, 115, 129, 140, 166, 170, 183)
OPTIONAL_SEEDS = (13, 167)
ALL_SEEDS = set(CORE_SEEDS + OPTIONAL_SEEDS)
BANDS = {"LOW", "NEAR_NYQUIST"}


def parse_utc(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def active_ngspice_pids():
    pids = []
    for comm_path in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm_path.read_text(encoding="ascii").strip() == "ngspice":
                pids.append(int(comm_path.parent.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return sorted(pids)


def remap_dependency(path_text):
    path = Path(path_text)
    try:
        relative = path.relative_to(SOURCE_ROOT)
    except ValueError:
        return path
    return ROOT / relative


def main():
    preflight_started = datetime.now(timezone.utc)
    copy_timing_path = ROOT / "results" / "preflight_copy_timing.json"
    copy_timing = json.loads(copy_timing_path.read_text(encoding="ascii"))

    dependency_record = json.loads(
        (ROOT / "config" / "dependency_hashes.json").read_text(encoding="ascii")
    )
    qualification = json.loads(
        (ROOT / "config" / "qualification_cache.json").read_text(encoding="ascii")
    )

    dependency_failures = []
    for item in dependency_record["dependencies"]:
        live_path = remap_dependency(item["path"])
        failure = None
        if not live_path.is_file():
            failure = "missing"
        elif live_path.stat().st_size != int(item["size_bytes"]):
            failure = "size"
        elif sha256_file(live_path) != item["sha256"]:
            failure = "sha256"
        if failure:
            dependency_failures.append(
                {
                    "role": item["role"],
                    "source_path": item["path"],
                    "live_path": str(live_path),
                    "failure": failure,
                }
            )

    source_rows = read_csv(ROOT / "manifests" / "production_source_integrity.csv")
    source_failures = []
    for row in source_rows:
        live_path = PRODUCTION_ROOT / row["relative_path"]
        if (
            not live_path.is_file()
            or live_path.stat().st_size != int(row["expected_size_bytes"])
            or sha256_file(live_path) != row["expected_sha256"]
        ):
            source_failures.append(row["relative_path"])

    jobs = read_csv(ROOT / "manifests" / "job_matrix.csv")
    job_keys = {(int(row["mismatch_seed"]), row["band"]) for row in jobs}
    expected_keys = {(seed, band) for seed in ALL_SEEDS for band in BANDS}

    baseline_master = read_csv(
        ROOT / "references" / "baseline_mc200" / "dynamic_master.csv"
    )
    baseline_codes = read_csv(
        ROOT / "references" / "baseline_mc200" / "dynamic_codes.csv"
    )
    selected_baseline_master = [
        row for row in baseline_master if int(row["mismatch_seed"]) in ALL_SEEDS
    ]
    selected_baseline_codes = [
        row for row in baseline_codes if int(row["mismatch_seed"]) in ALL_SEEDS
    ]
    disk_free_gb = shutil.disk_usage(ROOT).free / (1024**3)

    checks = {
        "isolated_root_is_v8": ROOT.name == "A44_FAST64_D3_MC12_PLUS2_1H_V8",
        "active_master_absent": not (ROOT / "csv" / "dynamic_master.csv").exists(),
        "active_codes_absent": not (ROOT / "csv" / "dynamic_codes.csv").exists(),
        "dependency_hashes_match": not dependency_failures,
        "qualification_cache_key_matches": qualification.get("cache_key_sha256")
        == dependency_record.get("cache_key_sha256"),
        "qualification_complete": all(
            (
                qualification.get("fixed_pilot_complete"),
                qualification.get("numerical_qualification_pass"),
                qualification.get("session_equivalence_complete"),
                qualification.get("resource_admission_pass"),
            )
        ),
        "selected_maxstep_50ps": int(
            qualification.get("selected_formal_maxstep_ps", 0)
        )
        == 50,
        "separate_process_fallback": qualification.get("session_execution_mode")
        == "SEPARATE_PROCESS_FALLBACK",
        "selected_workers_4": int(
            qualification.get("resource", {}).get("selected_formal_workers", 0)
        )
        == 4,
        "production_source_113_of_113": len(source_rows) == 113
        and not source_failures,
        "job_matrix_28_rows": len(jobs) == 28,
        "job_matrix_exact_keys": job_keys == expected_keys,
        "job_matrix_all_pending": all(row["state"] == "PENDING" for row in jobs),
        "baseline_selected_master_28": len(selected_baseline_master) == 28,
        "baseline_selected_codes_1792": len(selected_baseline_codes) == 1792,
        "disk_free_at_least_5gb": disk_free_gb >= 5.0,
        "no_active_ngspice": not active_ngspice_pids(),
    }
    finished = datetime.now(timezone.utc)
    audit = {
        "validation_id": "A44_FAST64_D3_MC12_PLUS2_1H_V8",
        "pass": all(checks.values()),
        "checks": checks,
        "core_seeds": list(CORE_SEEDS),
        "optional_seeds": list(OPTIONAL_SEEDS),
        "dependency_failures": dependency_failures,
        "production_source_failures": source_failures,
        "active_ngspice_pids": active_ngspice_pids(),
        "disk_free_gb": disk_free_gb,
        "validation_started_utc": preflight_started.isoformat(),
        "preflight_finished_utc": finished.isoformat(),
        "preflight_audit_elapsed_s": (
            finished - preflight_started
        ).total_seconds(),
        "copy_elapsed_s": copy_timing["copy_elapsed_s"],
        "operational_preflight_elapsed_s": copy_timing["copy_elapsed_s"]
        + (finished - preflight_started).total_seconds(),
    }
    write_json_atomic(ROOT / "results" / "preflight_audit.json", audit)
    print(
        "PREFLIGHT pass={} elapsed_s={:.3f} dependencies={} source={}/{}".format(
            audit["pass"],
            audit["operational_preflight_elapsed_s"],
            len(dependency_record["dependencies"]) - len(dependency_failures),
            len(source_rows) - len(source_failures),
            len(source_rows),
        ),
        flush=True,
    )
    raise SystemExit(0 if audit["pass"] else 1)


if __name__ == "__main__":
    main()
