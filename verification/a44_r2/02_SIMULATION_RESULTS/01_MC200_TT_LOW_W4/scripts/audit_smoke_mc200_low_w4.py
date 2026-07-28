#!/usr/bin/env python3
"""Audit the three execution-only W4 smoke jobs before the formal MC200 run."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "manifests" / "smoke_job_matrix.csv"
RESULTS = ROOT / "results" / "jobs"
PATHS = ROOT / "csv" / "job_paths"
OUTPUT = ROOT / "results" / "smoke_audit_mc200_low_w4.json"
EXPECTED_IDS = {
    "SMOKE_CMP_IN_A2P25_W_S001_LOW_W4",
    "SMOKE_CMP_IN_A2P25_W_S044_LOW_W4",
    "SMOKE_CMP_IN_A2P25_W_S096_LOW_W4",
}
TERMINAL_STATES = {"COMPLETE", "COMPLETE_WITH_FAIL"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    rows = read_csv(MATRIX)
    failures: list[str] = []
    jobs: list[dict[str, object]] = []

    if {row["job_id"] for row in rows} != EXPECTED_IDS:
        failures.append("smoke job IDs do not match the frozen three-job set")

    for row in rows:
        job_id = row["job_id"]
        result_path = RESULTS / f"{job_id}.json"
        path_path = PATHS / f"{job_id}.csv"
        if not result_path.is_file():
            failures.append(f"{job_id}: result JSON missing")
            continue
        if not path_path.is_file():
            failures.append(f"{job_id}: path CSV missing")
            continue

        result = json.loads(result_path.read_text(encoding="utf-8"))
        path_rows = read_csv(path_path)
        log_path = ROOT / str(result.get("log", ""))
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_path.is_file()
            else ""
        )
        checks = {
            "terminal_state": result.get("state") in TERMINAL_STATES,
            "matrix_state_matches": row.get("state") == result.get("state"),
            "returncode_zero": int(result.get("returncode", -1)) == 0,
            "protocol_clean": result.get("protocol_clean") is True,
            "valid_68_frames": int(result.get("valid_frame_count", -1)) == 68,
            "no_invalid_frames": int(result.get("invalid_count", -1)) == 0,
            "no_missing_frames": int(result.get("missing_frame_count", -1)) == 0,
            "no_duplicate_frames": int(result.get("duplicate_frame_count", -1)) == 0,
            "w4_window": (
                int(result.get("warmup_frames", -1)) == 4
                and int(result.get("retained_frame_start", -1)) == 4
                and int(result.get("retained_frame_end", -1)) == 67
                and int(result.get("nfft", -1)) == 64
            ),
            "parseval": result.get("steady_state_parseval_pass") is True,
            "first_conversion_protocol": (
                result.get("first_conversion_protocol_pass") is True
            ),
            "first_path_has_8_rows": len(path_rows) == 8,
            "method_ids": (
                result.get("method_id")
                == "FAST64_V2_FIRST_CONVERSION_SEPARATED"
                and result.get("steady_state_method_id") == "FAST64_SS_W4"
            ),
            "low_noise_on": (
                result.get("band") == "LOW"
                and result.get("noise_mode") == "ON"
            ),
            "formal_numerics": (
                float(result.get("maxstep_ns", -1.0)) == 0.05
            ),
            "ngspice_compatibility_hsa": (
                "Compatibility modes selected: hs a" in log_text
                and "No compatibility mode selected" not in log_text
            ),
        }
        failed_checks = [name for name, passed in checks.items() if not passed]
        if failed_checks:
            failures.append(f"{job_id}: failed {', '.join(failed_checks)}")
        jobs.append(
            {
                "job_id": job_id,
                "state": result.get("state"),
                "overall_status": result.get("overall_status"),
                "elapsed_s": result.get("elapsed_s"),
                "steady_state_sndr_db": result.get("steady_state_sndr_db"),
                "steady_state_enob_raw": result.get("steady_state_enob_raw"),
                "checks": checks,
            }
        )

    payload = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASS_P1_SMOKE_EXECUTION_PROTOCOL"
            if not failures
            else "FAIL_P1_SMOKE_EXECUTION_PROTOCOL"
        ),
        "pass": not failures,
        "scope": "execution and measurement protocol only; not MC200 performance",
        "expected_job_count": 3,
        "observed_result_count": len(jobs),
        "jobs": jobs,
        "failures": failures,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
