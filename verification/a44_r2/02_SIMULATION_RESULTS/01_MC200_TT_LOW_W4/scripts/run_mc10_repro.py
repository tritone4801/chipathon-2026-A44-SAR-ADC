#!/usr/bin/env python3
"""Run the frozen 10-seed dual-band current-MC200 reproduction campaign."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from run_fixed50_subset import (
    ngspice_snapshot,
    verify_dependencies,
    verify_production_source,
)
from run_v7 import merge_rows, run_die
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import (
    CONFIG_DIR,
    load_manifest_checksums,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


TARGET_PATH = ROOT / "config" / "mc10_target_contract.csv"
CONTRACT_PATH = ROOT / "config" / "mc10_target_contract.json"
MASTER_PATH = ROOT / "csv" / "mc10_master.csv"
CODE_PATH = ROOT / "csv" / "mc10_codes.csv"
TRACE_PATH = ROOT / "csv" / "mc10_resource_trace.csv"
STATUS_PATH = ROOT / "results" / "mc10_execution_status.json"
JOB_MATRIX_PATH = ROOT / "manifests" / "job_matrix.csv"
MAXSTEP_PS = 50
WORKERS = 4
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Monitor:
    def __init__(self) -> None:
        self.rows = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self) -> None:
        while not self.stop_event.is_set():
            processes = ngspice_snapshot()
            self.rows.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "process_count": len(processes),
                    "total_threads": sum(p["threads"] for p in processes),
                    "total_rss_kb": sum(p["rss_kb"] for p in processes),
                    "pids": ";".join(str(p["pid"]) for p in processes),
                }
            )
            self.stop_event.wait(2)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)


def write_trace(rows: list[dict]) -> None:
    with TRACE_PATH.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "timestamp_utc",
                "process_count",
                "total_threads",
                "total_rss_kb",
                "pids",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_job_matrix(master_rows: list[dict]) -> None:
    master = {
        (int(row["mismatch_seed"]), row["band"]): row for row in master_rows
    }
    jobs = read_csv(JOB_MATRIX_PATH)
    for job in jobs:
        key = (int(job["mismatch_seed"]), job["band"])
        if key not in master:
            continue
        result = master[key]
        job.update(
            {
                "state": result["state"],
                "attempt_count": result.get("attempt_count", ""),
                "measurement_stem": result.get("measurement_stem", ""),
                "compact_code_checksum_sha256": result.get(
                    "compact_code_checksum_sha256", ""
                ),
            }
        )
    write_csv_atomic(JOB_MATRIX_PATH, jobs)


def main() -> int:
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = "1"

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    targets = read_csv(TARGET_PATH)
    target_keys = {
        (int(row["mismatch_seed"]), row["band"]) for row in targets
    }
    selected = [int(seed) for seed in contract["selected_seeds"]]
    method_checks = {
        "contract_frozen": contract["status"] == "FROZEN_BEFORE_EXECUTION",
        "ten_selected_seeds": len(selected) == 10 and len(set(selected)) == 10,
        "twenty_unique_target_records": len(targets) == 20
        and len(target_keys) == 20,
        "all_targets_fixed_50ps": all(
            int(row["maxstep_ps"]) == MAXSTEP_PS for row in targets
        ),
        "all_targets_robust_gear": all(
            row["solver_profile"] == "ROBUST_GEAR" for row in targets
        ),
        "all_targets_separate_process": all(
            row["execution_mode"] == "SEPARATE_PROCESS_FALLBACK"
            for row in targets
        ),
        "no_existing_formal_outputs": not MASTER_PATH.exists()
        and not CODE_PATH.exists(),
        "no_active_ngspice_at_start": not ngspice_snapshot(),
    }
    cache = json.loads(
        (CONFIG_DIR / "qualification_cache.json").read_text(encoding="ascii")
    )
    qualification_checks = {
        "qualification_complete": all(
            (
                cache.get("fixed_pilot_complete"),
                cache.get("numerical_qualification_pass"),
                cache.get("session_equivalence_complete"),
                cache.get("resource_admission_pass"),
            )
        ),
        "selected_formal_maxstep_50ps": int(
            cache.get("selected_formal_maxstep_ps", 0)
        )
        == MAXSTEP_PS,
        "separate_process_fallback": cache.get("session_execution_mode")
        == "SEPARATE_PROCESS_FALLBACK",
        "admitted_workers_at_least_4": int(
            cache.get("resource", {}).get("selected_formal_workers", 0)
        )
        >= WORKERS,
    }
    dependencies = verify_dependencies()
    production_source = verify_production_source()
    provenance_root = ROOT / "references" / "current_mc200_provenance"
    historical_source = json.loads(
        (provenance_root / "host_production_source_audit.json").read_text(
            encoding="utf-8"
        )
    )
    historical_execution = json.loads(
        (provenance_root / "execution_audit.json").read_text(encoding="utf-8")
    )
    expected_external_role = {
        "production_analog_package_manifest",
    }
    failed_roles = {
        item["role"] for item in dependencies.get("failures", [])
    }
    frozen_input_closure = {
        "nineteen_live_simulation_dependencies_match": (
            dependencies["matching"] == 19
            and dependencies["declared"] == 20
            and failed_roles == expected_external_role
        ),
        "current_mc200_historical_source_113_of_113": (
            historical_source.get("pass") is True
            and historical_source.get("declared_files") == 113
            and historical_source.get("matching_files") == 113
        ),
        "current_mc200_active_binding_and_pin_order_pass": (
            historical_execution.get("checks", {}).get(
                "active_binding_and_pin_order_pass"
            )
            is True
        ),
        "current_mc200_production_source_113_of_113": (
            historical_execution.get("checks", {}).get(
                "production_source_113_of_113"
            )
            is True
        ),
    }
    preflight = {
        "status": "PASS_MC10_PREFLIGHT",
        "pass": all(method_checks.values())
        and all(qualification_checks.values())
        and all(frozen_input_closure.values()),
        "checks": method_checks,
        "qualification_checks": qualification_checks,
        "dependencies": dependencies,
        "frozen_input_closure": frozen_input_closure,
        "live_production_source_drift_warning": {
            "status": (
                "LIVE_PRODUCTION_SOURCE_MATCH"
                if production_source["pass"]
                else "LIVE_PRODUCTION_SOURCE_DRIFT_AFTER_REFERENCE_FREEZE"
            ),
            "blocking": False,
            "audit": production_source,
            "reason": (
                "Reproduction is bound to the sealed current-MC200 inputs; "
                "the changed live production tree is not substituted."
            ),
        },
        "target_records": len(targets),
    }
    preflight["status"] = (
        "PASS_MC10_PREFLIGHT" if preflight["pass"] else "FAIL_MC10_PREFLIGHT"
    )
    write_json_atomic(ROOT / "results" / "mc10_preflight.json", preflight)
    if not preflight["pass"]:
        raise RuntimeError("MC10 preflight failed")
    if "--preflight-only" in sys.argv[1:]:
        print(json.dumps(preflight, indent=2), flush=True)
        return 0

    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    work = [
        (int(row["mismatch_seed"]), row["band"])
        for row in targets
    ]
    started_utc = datetime.now(timezone.utc)
    started = time.monotonic()
    master_rows: list[dict] = []
    code_rows: list[dict] = []
    monitor = Monitor()
    monitor.start()
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {
                executor.submit(
                    run_die,
                    grouped,
                    timing,
                    seed,
                    MAXSTEP_PS,
                    mismatch_checksums,
                    noise_checksums,
                    [band],
                ): (seed, band)
                for seed, band in work
            }
            for future in as_completed(futures):
                seed, band = futures[future]
                rows, codes = future.result()
                master_rows = merge_rows(
                    MASTER_PATH,
                    rows,
                    ("mismatch_seed", "band"),
                )
                master_rows.sort(
                    key=lambda row: (
                        selected.index(int(row["mismatch_seed"])),
                        row["band"],
                    )
                )
                write_csv_atomic(MASTER_PATH, master_rows)
                code_rows = merge_rows(
                    CODE_PATH,
                    codes,
                    ("mismatch_seed", "band", "frame_index"),
                )
                code_rows.sort(
                    key=lambda row: (
                        selected.index(int(row["mismatch_seed"])),
                        row["band"],
                        int(row["frame_index"]),
                    )
                )
                write_csv_atomic(CODE_PATH, code_rows)
                row = rows[0]
                print(
                    f"MC10_DONE seed={seed} band={band} "
                    f"state={row['state']} sndr_db={row.get('sndr_db', '')}",
                    flush=True,
                )
    finally:
        monitor.stop()
    elapsed_s = time.monotonic() - started
    write_trace(monitor.rows)

    final_master = read_csv(MASTER_PATH)
    final_codes = read_csv(CODE_PATH)
    final_keys = {
        (int(row["mismatch_seed"]), row["band"]) for row in final_master
    }
    valid = [row for row in final_master if row["state"] in VALID_STATES]
    frame_keys = {
        (
            int(row["mismatch_seed"]),
            row["band"],
            int(row["frame_index"]),
        )
        for row in final_codes
    }
    checks = {
        "all_20_target_keys_present": final_keys == target_keys,
        "all_20_records_valid": len(valid) == 20,
        "all_1280_unique_codes_present": len(final_codes) == 1280
        and len(frame_keys) == 1280,
        "all_frames_0_through_63": all(
            {
                int(row["frame_index"])
                for row in final_codes
                if int(row["mismatch_seed"]) == seed and row["band"] == band
            }
            == set(range(64))
            for seed, band in target_keys
        ),
        "all_records_50ps": all(
            float(row["maxstep_ns"]) == 0.05 for row in final_master
        ),
        "all_records_robust_gear": all(
            row["measurement_solver_profile"] == "ROBUST_GEAR"
            for row in final_master
        ),
        "all_records_separate_process": all(
            row["execution_mode"] == "SEPARATE_PROCESS_FALLBACK"
            for row in final_master
        ),
        "all_noise_checksums_match": all(
            row["noise_draw_checksum_match"] == "True" for row in final_master
        ),
        "no_timeouts": all(row["timed_out"] == "False" for row in final_master),
        "no_simulation_aborts": all(
            row["simulation_aborted"] == "False" for row in final_master
        ),
        "all_parseval_checks_pass": all(
            row["parseval_pass"] == "True" for row in final_master
        ),
        "max_four_ngspice_processes": max(
            (int(row["process_count"]) for row in monitor.rows), default=0
        )
        <= WORKERS,
    }
    update_job_matrix(final_master)
    status = {
        "status": "PASS_MC10_EXECUTION"
        if all(checks.values())
        else "FAIL_MC10_EXECUTION",
        "pass": all(checks.values()),
        "checks": checks,
        "preflight": preflight,
        "selected_seeds": selected,
        "requested_records": len(targets),
        "valid_records": len(valid),
        "code_rows": len(final_codes),
        "started_utc": started_utc.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed_s,
        "workers": WORKERS,
        "max_ngspice_processes": max(
            (int(row["process_count"]) for row in monitor.rows), default=0
        ),
        "max_total_threads": max(
            (int(row["total_threads"]) for row in monitor.rows), default=0
        ),
        "max_total_rss_kb": max(
            (int(row["total_rss_kb"]) for row in monitor.rows), default=0
        ),
        "master_sha256": sha256(MASTER_PATH),
        "codes_sha256": sha256(CODE_PATH),
    }
    write_json_atomic(STATUS_PATH, status)
    print(json.dumps(status, indent=2), flush=True)
    return 0 if status["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
