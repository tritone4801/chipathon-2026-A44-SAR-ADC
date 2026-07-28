#!/usr/bin/env python3
"""Strict completion audit for the 200-die fixed-50-ps formal execution."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sar_campaign_common import ROOT


VALID_STATES = {"VALID_PASS", "VALID_FAIL"}


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def code_checksum(values) -> str:
    payload = bytes(int(value) for value in values)
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ngspice_count() -> int:
    count = 0
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            count += comm.read_text(encoding="ascii").strip() == "ngspice"
        except (FileNotFoundError, ProcessLookupError):
            continue
    return count


def main() -> int:
    contract = load_json(ROOT / "config" / "frozen_mc200_contract.json")
    production = load_json(ROOT / "results" / "host_production_source_audit.json")
    preflight = load_json(ROOT / "results" / "preflight_audit.json")
    smoke = load_json(ROOT / "results" / "anchor_smoke_audit.json")
    plot_smoke = load_json(ROOT / "results" / "plot_style_smoke_audit.json")
    plot_visual = load_json(ROOT / "results" / "plot_style_visual_review.json")
    resource = load_json(ROOT / "results" / "full_mc200_resource_summary.json")
    formal = load_json(ROOT / "results" / "formal_execution_audit.json")
    assembly = load_json(
        ROOT / "source_snapshot" / "sar_current" / "assembly_checks.json"
    )
    master = read_csv(ROOT / "csv" / "dynamic_master.csv")
    codes = read_csv(ROOT / "csv" / "dynamic_codes.csv")
    jobs = read_csv(ROOT / "manifests" / "job_matrix.csv")
    mismatch = {
        int(row["mismatch_seed"]): row
        for row in read_csv(ROOT / "manifests" / "mismatch_seed_manifest.csv")
    }
    noise = {
        int(row["mismatch_seed"]): row
        for row in read_csv(ROOT / "manifests" / "noise_seed_manifest.csv")
    }
    expected_keys = {
        (seed, band)
        for seed in range(1, 201)
        for band in ("LOW", "NEAR_NYQUIST")
    }
    master_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in master
    }
    code_by_key = {}
    for row in codes:
        code_by_key.setdefault((int(row["mismatch_seed"]), row["band"]), []).append(row)

    code_coverage_failures = []
    checksum_failures = []
    for key in sorted(expected_keys):
        rows = sorted(code_by_key.get(key, []), key=lambda row: int(row["frame_index"]))
        if len(rows) != 64 or [int(row["frame_index"]) for row in rows] != list(range(64)):
            code_coverage_failures.append({"seed": key[0], "band": key[1], "rows": len(rows)})
            continue
        actual = code_checksum(row["code"] for row in rows)
        if actual != master_by_key[key]["compact_code_checksum_sha256"]:
            checksum_failures.append(
                {
                    "seed": key[0],
                    "band": key[1],
                    "expected": master_by_key[key]["compact_code_checksum_sha256"],
                    "actual": actual,
                }
            )

    assembly_by_id = {row["check_id"]: row["status"] for row in assembly}
    required_binding_checks = {
        "authoritative_source_hashes",
        "top_local_symbol_binding",
        "cdac_local_switch_binding",
        "top_symbol_pin_order",
        "logic_symbol_frozen_subckt_binding",
        "accepted_top_pin_order",
        "accepted_top_hierarchy",
        "accepted_include_closure",
        "ngspice_accepted_hierarchy_parse",
    }
    checks = {
        "production_source_113_of_113": production["pass"] is True
        and production["declared_files"] == 113
        and production["matching_files"] == 113,
        "active_binding_and_pin_order_pass": all(
            assembly_by_id.get(check_id) == "PASS"
            for check_id in required_binding_checks
        ),
        "preflight_pass": preflight["pass"] is True,
        "anchor_smoke_pass": smoke["pass"] is True,
        "plot_style_smoke_pass": plot_smoke["pass"] is True,
        "plot_style_visual_review_pass": plot_visual["pass"] is True,
        "plot_style_visual_review_hashes_match": all(
            sha256(ROOT / "plots" / "style_smoke" / filename) == expected
            for filename, expected in plot_visual["reviewed_files"].items()
        )
        and sha256(ROOT / "scripts" / "plot_style_smoke.py")
        == plot_visual["plot_script_sha256"],
        "master_400_unique_expected_keys": len(master) == 400
        and set(master_by_key) == expected_keys,
        "codes_25600": len(codes) == 25600,
        "all_code_frames_0_through_63": not code_coverage_failures,
        "all_compact_code_checksums_match": not checksum_failures,
        "all_records_valid": all(row["state"] in VALID_STATES for row in master),
        "all_records_50ps": all(float(row["maxstep_ns"]) == 0.05 for row in master),
        "all_records_robust_gear": all(
            row["measurement_solver_profile"] == "ROBUST_GEAR" for row in master
        ),
        "all_records_separate_process": all(
            row["execution_mode"] == "SEPARATE_PROCESS_FALLBACK" for row in master
        ),
        "all_noise_checksums_match": all(
            str(row["noise_draw_checksum_match"]).lower() == "true"
            and row["noise_draw_checksum_sha256"]
            == noise[int(row["mismatch_seed"])]["noise_draw_checksum_sha256"]
            for row in master
        ),
        "all_mismatch_checksums_match": all(
            row["mismatch_checksum_sha256"]
            == mismatch[int(row["mismatch_seed"])]["mismatch_checksum_sha256"]
            for row in master
        ),
        "no_timeouts_or_aborts": all(
            str(row["timed_out"]).lower() == "false"
            and str(row["simulation_aborted"]).lower() == "false"
            and int(row["timeout_count"]) == 0
            for row in master
        ),
        "no_missing_duplicate_or_invalid_frames": all(
            int(row["missing_frame_count"]) == 0
            and int(row["duplicate_frame_count"]) == 0
            and int(row["invalid_count"]) == 0
            and int(row["valid_frame_count"]) == 64
            for row in master
        ),
        "all_parseval_checks_pass": all(
            str(row["parseval_pass"]).lower() == "true" for row in master
        ),
        "job_matrix_400_terminal": len(jobs) == 400
        and all(row["state"] in VALID_STATES for row in jobs),
        "resource_max_four_ngspice": resource["max_ngspice_processes"] <= 4,
        "no_ngspice_after_completion": ngspice_count() == 0,
        "formal_launcher_exit_zero": (
            ROOT / "results" / "full_mc200_exit_code.txt"
        ).read_text(encoding="ascii").strip()
        == "0",
        "formal_runner_contract_complete": formal["records_present"] == 400
        and formal["selected_maxstep_ps"] == 50
        and formal["workers"] == 4
        and formal["requested_seeds"] == list(range(1, 201))
        and formal["performance_early_stop"] is False,
        "contract_counts_honored": contract["record_count"] == len(master)
        and contract["code_row_count"] == len(codes),
    }
    result = {
        "status": "PASS_FULL_MC200_EXECUTION"
        if all(checks.values())
        else "FAIL_FULL_MC200_EXECUTION",
        "pass": all(checks.values()),
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "records": len(master),
        "code_rows": len(codes),
        "valid_pass_records": sum(row["state"] == "VALID_PASS" for row in master),
        "valid_fail_records": sum(row["state"] == "VALID_FAIL" for row in master),
        "code_coverage_failures": code_coverage_failures,
        "checksum_failures": checksum_failures,
        "master_sha256": hashlib.sha256(
            (ROOT / "csv" / "dynamic_master.csv").read_bytes()
        ).hexdigest(),
        "codes_sha256": hashlib.sha256(
            (ROOT / "csv" / "dynamic_codes.csv").read_bytes()
        ).hexdigest(),
        "resource_summary": resource,
    }
    (ROOT / "results" / "execution_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
