#!/usr/bin/env python3
"""Freeze the FAST64 V2 package before any simulation is admitted."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fast64_v2_common import (
    CONFIG_DIR,
    MANIFEST_DIR,
    METHOD_ID,
    RESULT_DIR,
    ROOT,
    ensure_directories,
    formal_jobs,
    read_csv,
    sha256_file,
    smoke_jobs,
    write_csv_atomic,
    write_json_atomic,
)


BASE_LOCAL = Path(
    "/foss/designs/A44_MC10_CURRENT_MC200_REPRO_20260725_R1"
)
EXPECTED_BASE_MANIFEST_SHA256 = (
    "3c2130f305e70968e7a2651b6c5ec445b973c0b27d0e5a8c466ce09b4817d0a7"
)
EXPECTED_METHOD_SHA256 = (
    "12c4936f8039daeb28a472ed8f9cbf4193cf05e163e7357f1d17c61c3f238afe"
)

INPUT_PREFIXES = (
    "config/",
    "models/",
    "netlists/",
    "references/",
    "scripts/",
    "source_snapshot/",
    "tb/",
)
ACTIVE_INPUT_FILES = ("csv/cdac_mismatch_weights.csv",)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_lines(command: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        return [f"ERROR: {type(exc).__name__}: {exc}"]
    output = (result.stdout + "\n" + result.stderr).strip()
    return output.splitlines()[:20]


def environment_fingerprint() -> dict[str, object]:
    meminfo: dict[str, str] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                meminfo[key] = value.strip()
    return {
        "checked_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "ngspice": command_lines(["/foss/tools/bin/ngspice", "--version"]),
        "cpu_count": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)),
        "container_meminfo": meminfo,
        "thread_environment": {
            key: os.environ.get(key, "")
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }


def pin_binding_checks() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    expected = {
        "netlists/core/subckts/CDAC_native_extracted.subckt.spice": ".subckt CDAC ",
        "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice": ".subckt Comparator_StrongARM ",
        "netlists/core/subckts/SWITCH_BOOT_SP_native_extracted.subckt.spice": ".subckt SWITCH_BOOT_SP ",
    }
    for relative, signature in expected.items():
        path = ROOT / relative
        text = path.read_text(encoding="ascii", errors="replace") if path.is_file() else ""
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.lower().startswith(".subckt ")
        ]
        checks.append(
            {
                "relative_path": relative,
                "exists": path.is_file(),
                "expected_signature": signature.strip(),
                "subckt_lines": lines,
                "pass": path.is_file()
                and any(line.lower().startswith(signature.lower()) for line in lines),
                "sha256": sha256_file(path) if path.is_file() else "",
            }
        )
    behavior = ROOT / "models/SAR_LOGIC_BEH_TT_3P3_27C.so"
    checks.append(
        {
            "relative_path": behavior.relative_to(ROOT).as_posix(),
            "exists": behavior.is_file(),
            "expected_signature": "ELF shared object, campaign-local behavioral logic",
            "subckt_lines": [],
            "pass": behavior.is_file() and behavior.stat().st_size > 1024,
            "sha256": sha256_file(behavior) if behavior.is_file() else "",
        }
    )
    return checks


def active_input_paths() -> list[Path]:
    paths: set[Path] = set()
    for prefix in INPUT_PREFIXES:
        base = ROOT / prefix
        if base.is_dir():
            paths.update(path for path in base.rglob("*") if path.is_file())
    for relative in ACTIVE_INPUT_FILES:
        path = ROOT / relative
        if path.is_file():
            paths.add(path)
    excluded_parts = {"__pycache__"}
    return sorted(
        (
            path
            for path in paths
            if not excluded_parts.intersection(path.relative_to(ROOT).parts)
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preserve-job-state",
        action="store_true",
        help="Reseal analysis inputs without discarding already completed simulations.",
    )
    args = parser.parse_args()
    ensure_directories()
    failures: list[dict[str, object]] = []
    method_path = (
        ROOT
        / "references/method_contract/FAST64_V2_FIRST_CONVERSION_SEPARATED_CN.txt"
    )
    method_hash = sha256_file(method_path) if method_path.is_file() else ""
    if method_hash != EXPECTED_METHOD_SHA256:
        failures.append(
            {
                "gate": "METHOD_CONTRACT_HASH",
                "expected": EXPECTED_METHOD_SHA256,
                "observed": method_hash,
            }
        )

    base_manifest = BASE_LOCAL / "manifest_sha256.csv"
    base_hash = sha256_file(base_manifest) if base_manifest.is_file() else ""
    if base_hash != EXPECTED_BASE_MANIFEST_SHA256:
        failures.append(
            {
                "gate": "BASE_MANIFEST_HASH",
                "expected": EXPECTED_BASE_MANIFEST_SHA256,
                "observed": base_hash,
            }
        )
    try:
        base_audit = json.loads(
            (BASE_LOCAL / "manifest_audit.json").read_text(encoding="utf-8")
        )
    except Exception as exc:
        base_audit = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
    if not base_audit.get("pass"):
        failures.append({"gate": "BASE_MANIFEST_AUDIT", "observed": base_audit})

    binding_checks = pin_binding_checks()
    failures.extend(
        {"gate": "ACTIVE_BINDING", "observed": row}
        for row in binding_checks
        if not row["pass"]
    )

    contract = {
        "campaign": ROOT.name,
        "method_id": METHOD_ID,
        "steady_state_method_id": "FAST64_SS_W4",
        "historical_method_id": "FAST64_STARTUP_INCLUSIVE_W0",
        "measurement": {
            "sample_rate_hz": 2_000_000.0,
            "frame_period_ns": 500.0,
            "input_vpp_diff": 3.0,
            "input_phase_rad": 0.7853981633974483,
            "bands": {
                "LOW": {"bin": 7, "fin_hz": 218_750.0},
                "NEAR_NYQUIST": {"bin": 29, "fin_hz": 906_250.0},
            },
            "window": "rectangular",
            "warmup_frames": 4,
            "total_frames": 68,
            "retained_frames": [4, 67],
            "nfft": 64,
            "same_phase_reference_frame": 64,
            "dout_aperture_ns": 480.0,
            "formal_maxstep_ps": 50,
            "bulk_maxstep_ps": 100,
        },
        "resource_contract": {
            "formal_workers_max": 4,
            "total_ngspice_threads_max": 16,
            "affinity_core_count": 12,
        },
        "promoted_candidate": {
            "status": "NOT_APPLICABLE_NO_DISTINCT_PROMOTED_CANDIDATE",
            "reason": "The frozen MC10 binding contains one baseline DUT/netlist set and no distinct resizing candidate.",
            "binding_hashes": {
                row["relative_path"]: row["sha256"] for row in binding_checks
            },
        },
        "source_boundary": {
            "base_package": str(BASE_LOCAL),
            "base_manifest_sha256": base_hash,
            "base_manifest_entries": base_audit.get("manifest_entries"),
            "live_sar_current_used": False,
        },
        "method_contract": {
            "relative_path": method_path.relative_to(ROOT).as_posix(),
            "sha256": method_hash,
            "size_bytes": method_path.stat().st_size if method_path.is_file() else 0,
            "original_path": (
                "C:\\Users\\15031\\.codex\\attachments\\"
                "1373a0b4-f441-42a4-bfdd-d655c8f01127\\pasted-text.txt"
            ),
        },
        "created_utc": utc_now(),
    }
    write_json_atomic(CONFIG_DIR / "fast64_v2_contract.json", contract)
    write_json_atomic(CONFIG_DIR / "environment_fingerprint.json", environment_fingerprint())

    previous_jobs = (
        {
            row["job_id"]: row
            for row in read_csv(MANIFEST_DIR / "job_matrix.csv")
        }
        if args.preserve_job_state
        else {}
    )
    jobs = formal_jobs()
    if previous_jobs:
        for job in jobs:
            previous = previous_jobs.get(str(job["job_id"]))
            if previous:
                for field in (
                    "state",
                    "returncode",
                    "elapsed_s",
                    "overall_status",
                    "completed_utc",
                ):
                    if field in previous:
                        job[field] = previous[field]
    write_csv_atomic(MANIFEST_DIR / "job_matrix.csv", jobs)
    previous_smoke = (
        {
            row["job_id"]: row
            for row in read_csv(MANIFEST_DIR / "smoke_job_matrix.csv")
        }
        if args.preserve_job_state
        else {}
    )
    smoke = smoke_jobs()
    if previous_smoke:
        for job in smoke:
            previous = previous_smoke.get(str(job["job_id"]))
            if previous:
                for field in (
                    "state",
                    "returncode",
                    "elapsed_s",
                    "overall_status",
                    "completed_utc",
                ):
                    if field in previous:
                        job[field] = previous[field]
    write_csv_atomic(MANIFEST_DIR / "smoke_job_matrix.csv", smoke)

    input_rows = [
        {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in active_input_paths()
    ]
    write_csv_atomic(MANIFEST_DIR / "input_manifest_sha256.csv", input_rows)
    manifest_hash = sha256_file(MANIFEST_DIR / "input_manifest_sha256.csv")
    write_json_atomic(
        MANIFEST_DIR / "input_manifest_audit.json",
        {
            "status": "PASS_INPUT_MANIFEST_FREEZE" if not failures else "FAIL_INPUT_MANIFEST_FREEZE",
            "pass": not failures,
            "entries": len(input_rows),
            "manifest_sha256": manifest_hash,
            "failures": failures,
        },
    )
    write_json_atomic(
        RESULT_DIR / "setup_audit.json",
        {
            "status": "PASS_P0_PACKAGE_FREEZE" if not failures else "FAIL_P0_PACKAGE_FREEZE",
            "pass": not failures,
            "checked_utc": utc_now(),
            "base_manifest_sha256": base_hash,
            "method_contract_sha256": method_hash,
            "formal_job_count": len(jobs),
            "pending_job_count": sum(row["state"] == "PENDING" for row in jobs),
            "preserve_job_state": args.preserve_job_state,
            "preserved_terminal_job_count": sum(
                row["state"] != "PENDING" for row in jobs
            ),
            "initial_p0_audit": (
                "references/setup_initial_p0_audit.json"
                if args.preserve_job_state
                else ""
            ),
            "binding_checks": binding_checks,
            "input_manifest_entries": len(input_rows),
            "input_manifest_sha256": manifest_hash,
            "failures": failures,
        },
    )
    print(
        json.dumps(
            {
                "status": "PASS_P0_PACKAGE_FREEZE"
                if not failures
                else "FAIL_P0_PACKAGE_FREEZE",
                "formal_jobs": len(jobs),
                "input_manifest_entries": len(input_rows),
                "failures": len(failures),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
