#!/usr/bin/env python3
"""CACE preflight, quick first-five replay, and full A44 campaign launcher."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "02_SIMULATION_RESULTS"
TOOLS = ROOT / "03_CACE_AND_SIMULATION_TOOLS"
CIRCUITS = ROOT / "01_CURRENT_CIRCUIT_FILES"
CACE_ROOT = TOOLS / "CACE"
PDK_ROOT = TOOLS / "PDK"
SCRIPTS = TOOLS / "scripts"
OUTPUTS = RESULTS / "06_RUN_OUTPUTS"
AUDITS = ROOT / "05_PACKAGE_AUDIT"
COMPARATOR_SHA256 = (
    "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"
)
PDK_HASHES = {
    "design.ngspice": (
        "091cb530bf85160a1f07878fb81f789ca367d018991c8ab41a584cd1a85c6692"
    ),
    "sm141064.ngspice": (
        "677822db50bf8968f77854bb455006ac5c245deb46ecfc8b352934e752135c46"
    ),
    "sm141064_mim.ngspice": (
        "b7918b5ad4f4dad0ce5cb2fc08114e25b10ff5f9f827754334bb0bdfe2a89767"
    ),
}
STATIC_CASES = (
    "S044_TT",
    "S116_TT",
    "S180_TT",
    "S106_TT",
    "S044_SS",
    "S044_FF",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_tag(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_tree_manifest(root: Path, destination: Path) -> None:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == destination.resolve():
            continue
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_csv(destination, rows)


def run_command(
    command: list[str],
    *,
    cwd: Path,
    log_path: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
    print(completed.stdout, end="", flush=True)
    return completed


def binding_paths() -> list[Path]:
    paths = [
        CIRCUITS
        / "spice"
        / "subckts"
        / "Comparator_StrongARM_extracted.subckt.spice",
        RESULTS
        / "01_MC200_TT_LOW_W4"
        / "netlists"
        / "core"
        / "subckts"
        / "Comparator_StrongARM_extracted.subckt.spice",
        RESULTS
        / "02_PVT3_MC20_LOW_W4"
        / "netlists"
        / "core"
        / "subckts"
        / "Comparator_StrongARM_extracted.subckt.spice",
    ]
    paths.extend(
        RESULTS
        / "03_FULL255_STATIC"
        / "cases"
        / case
        / "netlists"
        / "candidate"
        / "Comparator_StrongARM_CURRENT.subckt.spice"
        for case in STATIC_CASES
    )
    return paths


def preflight(run_root: Path | None = None) -> dict[str, Any]:
    if run_root is None:
        run_root = OUTPUTS / run_tag("PREFLIGHT")
    run_root.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []

    for path in binding_paths():
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "check": "current_comparator_binding",
                "path": path.relative_to(ROOT).as_posix(),
                "expected_sha256": COMPARATOR_SHA256,
                "actual_sha256": actual,
                "pass": actual == COMPARATOR_SHA256,
            }
        )

    pdk_root = PDK_ROOT / "gf180mcuD" / "libs.tech" / "ngspice"
    for name, expected in PDK_HASHES.items():
        path = pdk_root / name
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "check": "package_owned_pdk",
                "path": path.relative_to(ROOT).as_posix(),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "pass": actual == expected,
            }
        )

    required = [
        CIRCUITS / "xschem" / "SAR_ADC_TOP_FIXED.sch",
        CIRCUITS
        / "xschem"
        / "A44_SAR_ADC_TOP_FIXED.sym",
        RESULTS
        / "01_MC200_TT_LOW_W4"
        / "models"
        / "SAR_LOGIC_BEH_TT_3P3_27C.so",
        RESULTS / "01_MC200_TT_LOW_W4" / "manifests" / "job_matrix.csv",
        RESULTS / "02_PVT3_MC20_LOW_W4" / "manifests" / "job_matrix.csv",
        CACE_ROOT
        / "cace"
        / "templates"
        / "tb_package_preflight.sch",
    ]
    for path in required:
        checks.append(
            {
                "check": "required_file",
                "path": path.relative_to(ROOT).as_posix(),
                "pass": path.is_file(),
            }
        )

    env = os.environ.copy()
    env["PATH"] = (
        "/foss/tools/bin:/usr/local/bin:/usr/bin:/bin:"
        + env.get("PATH", "")
    )
    cace_runs = run_root / "cace_runs"
    cace = run_command(
        [
            "cace",
            "cace/cace_job.yaml",
            "--run-path",
            str(cace_runs),
            "--no-plot",
            "--no-progress-bar",
            "-l",
            "INFO",
        ],
        cwd=CACE_ROOT,
        log_path=run_root / "cace_preflight.log",
        env=env,
    )
    summaries = list(cace_runs.rglob("simulation_summary.md"))
    cace_text = cace.stdout
    cace_pass = (
        cace.returncode == 0
        and bool(summaries)
        and "Completed A44 package CACE and ngspice preflight: Pass" in cace_text
        and " 1.250 " in cace_text
    )
    checks.append(
        {
            "check": "cace_2_9_executable_preflight",
            "returncode": cace.returncode,
            "simulation_summary_count": len(summaries),
            "pass": cace_pass,
        }
    )
    payload = {
        "status": (
            "PASS_STANDALONE_PREFLIGHT"
            if all(item["pass"] for item in checks)
            else "FAIL_STANDALONE_PREFLIGHT"
        ),
        "pass": all(item["pass"] for item in checks),
        "package_root": str(ROOT),
        "package_only_design_dependency": True,
        "external_tool_runtime": (
            "Docker image/container with CACE, Xschem, ngspice and Python"
        ),
        "checks": checks,
        "completed_utc": utc_now(),
    }
    write_json(run_root / "preflight.json", payload)
    return payload


def quick_verify() -> int:
    run_root = OUTPUTS / run_tag("RUN")
    run_root.mkdir(parents=True, exist_ok=False)
    status_path = run_root / "RUN_STATUS.json"
    write_json(
        status_path,
        {
            "state": "RUNNING",
            "mode": "QUICK_FIRST5_REPRODUCIBILITY",
            "started_utc": utc_now(),
        },
    )
    pre = preflight(run_root)
    if not pre["pass"]:
        write_json(
            status_path,
            {
                "state": "FAILED_PREFLIGHT",
                "mode": "QUICK_FIRST5_REPRODUCIBILITY",
                "preflight": "preflight.json",
                "completed_utc": utc_now(),
            },
        )
        return 2

    helper = SCRIPTS / "quick_verify_dynamic.py"
    dynamic_commands = [
        (
            "mc200",
            [
                sys.executable,
                str(helper),
                "--campaign",
                str(RESULTS / "01_MC200_TT_LOW_W4"),
                "--output",
                str(run_root / "dynamic_mc200"),
                "--phase",
                "P4_EVENT_NOISE_MC200_LOW",
                "--jobs-per-phase",
                "5",
                "--frames",
                "5",
                "--workers",
                "4",
            ],
        ),
        (
            "pvt3_mc20",
            [
                sys.executable,
                str(helper),
                "--campaign",
                str(RESULTS / "02_PVT3_MC20_LOW_W4"),
                "--output",
                str(run_root / "dynamic_pvt3_mc20"),
                "--phase",
                "P4_PVT_TT_MC20_LOW",
                "--phase",
                "P5_PVT_SS_MC20_LOW",
                "--phase",
                "P6_PVT_FF_MC20_LOW",
                "--jobs-per-phase",
                "5",
                "--frames",
                "5",
                "--workers",
                "4",
            ],
        ),
    ]
    command_results: list[dict[str, Any]] = []
    for name, command in dynamic_commands:
        completed = run_command(
            command,
            cwd=ROOT,
            log_path=run_root / f"{name}_launcher.log",
        )
        command_results.append(
            {"name": name, "returncode": completed.returncode}
        )

    static_helper = SCRIPTS / "quick_verify_static_case.py"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        for case in STATIC_CASES:
            command = [
                sys.executable,
                str(static_helper),
                "--case-root",
                str(RESULTS / "03_FULL255_STATIC" / "cases" / case),
                "--output",
                str(run_root / "static" / case),
                "--transition-count",
                "5",
            ]
            futures[
                pool.submit(
                    run_command,
                    command,
                    cwd=ROOT,
                    log_path=run_root / "static" / case / "launcher.log",
                )
            ] = case
        for future in as_completed(futures):
            case = futures[future]
            completed = future.result()
            command_results.append(
                {"name": f"static_{case}", "returncode": completed.returncode}
            )

    summaries = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(run_root.rglob("*first5_summary.json"))
    ]
    comparison_paths = sorted(run_root.rglob("*first5_comparison.csv"))
    comparison_rows: list[dict[str, Any]] = []
    for path in comparison_paths:
        for row in read_csv(path):
            comparison_rows.append(
                {
                    "source_comparison": path.relative_to(run_root).as_posix(),
                    **row,
                }
            )
    write_csv(run_root / "FIRST5_COMPARISON_ALL.csv", comparison_rows)

    all_pass = (
        len(summaries) == 8
        and all(bool(summary.get("pass")) for summary in summaries)
        and all(item["returncode"] == 0 for item in command_results)
    )
    aggregate = {
        "status": (
            "PASS_QUICK_REPRODUCIBILITY_ALL_LANES"
            if all_pass
            else "FAIL_QUICK_REPRODUCIBILITY"
        ),
        "pass": all_pass,
        "mode": "CACE_PREFLIGHT_PLUS_W4_RETAINED5_DYNAMIC_AND_BRACKET5_STATIC",
        "preflight_pass": bool(pre["pass"]),
        "dynamic_campaign_count": 2,
        "static_unique_case_count": 6,
        "summary_count": len(summaries),
        "comparison_record_count": len(comparison_rows),
        "matching_record_count": sum(
            str(row.get("row_pass", "")).strip().lower() == "true"
            for row in comparison_rows
        ),
        "expected_comparison_record_count": 130,
        "commands": command_results,
        "summaries": summaries,
        "early_stop_boundary": (
            "Dynamic jobs run diagnostic frames 0-3, compare the first five "
            "formal W4 retained records at frames 4-8, then stop. "
            "Static cases stop after the first five historical transition "
            "lower/upper brackets match. Unscheduled suffix work makes this "
            "a quick reproducibility audit, not a replacement full campaign."
        ),
        "source_campaign_performance_status": (
            "COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION"
        ),
        "completed_utc": utc_now(),
    }
    write_json(run_root / "QUICK_REPRODUCIBILITY_SUMMARY.json", aggregate)
    write_json(
        status_path,
        {
            "state": "COMPLETE" if all_pass else "FAILED",
            "mode": "QUICK_FIRST5_REPRODUCIBILITY",
            "status": aggregate["status"],
            "preflight": "preflight.json",
            "summary": "QUICK_REPRODUCIBILITY_SUMMARY.json",
            "comparison": "FIRST5_COMPARISON_ALL.csv",
            "completed_utc": utc_now(),
        },
    )
    write_tree_manifest(run_root, run_root / "RUN_MANIFEST_SHA256.csv")
    latest = OUTPUTS / "LATEST_QUICK_RUN.json"
    write_json(
        latest,
        {
            "run": run_root.name,
            "status": aggregate["status"],
            "pass": all_pass,
            "completed_utc": aggregate["completed_utc"],
        },
    )
    print(json.dumps(aggregate, indent=2, ensure_ascii=False), flush=True)
    return 0 if all_pass else 2


def safe_remove(path: Path, boundary: Path) -> None:
    resolved = path.resolve()
    root = boundary.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"refusing to remove outside {root}: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def reset_dynamic(root: Path, phases: set[str]) -> None:
    matrix_path = root / "manifests" / "job_matrix.csv"
    rows = read_csv(matrix_path)
    for row in rows:
        if row["phase"] in phases:
            row["state"] = "PENDING"
            row["returncode"] = ""
            row["elapsed_s"] = ""
            row["overall_status"] = ""
            row["completed_utc"] = ""
    write_csv(matrix_path, rows)
    for relative in (
        "jobs",
        "logs",
        "results/jobs",
        "csv/job_codes",
        "csv/job_paths",
    ):
        path = root / relative
        if path.exists():
            safe_remove(path, root)
        path.mkdir(parents=True, exist_ok=True)
    for path in (root / "results").glob("execution_*.json"):
        safe_remove(path, root)


def reset_static(static_root: Path) -> None:
    for case in STATIC_CASES:
        case_root = static_root / "cases" / case
        for relative in ("generated/jobs", "generated/raw", "logs"):
            path = case_root / relative
            if path.exists():
                safe_remove(path, case_root)
            path.mkdir(parents=True, exist_ok=True)
        patterns = [
            "pilot_*_transitions.csv",
            "*_transitions_up.csv",
            "*_full_evaluations.csv",
            "runtime_resource_trace.csv",
        ]
        for pattern in patterns:
            for path in (case_root / "csv").glob(pattern):
                safe_remove(path, case_root)
        for name in (
            "runtime_pilot.json",
            "full_transition_execution.json",
            "current_full255_summary.json",
        ):
            path = case_root / "results" / name
            if path.exists():
                safe_remove(path, case_root)


def prepare_full_run() -> tuple[Path, list[list[str]]]:
    run_root = OUTPUTS / run_tag("FULL")
    work = run_root / "work"
    run_root.mkdir(parents=True, exist_ok=False)
    for name in (
        "01_MC200_TT_LOW_W4",
        "02_PVT3_MC20_LOW_W4",
        "03_FULL255_STATIC",
        "04_CROSS_CAMPAIGN_SUMMARY",
    ):
        shutil.copytree(RESULTS / name, work / name)
    shutil.copytree(PDK_ROOT, work / "PDK")
    reset_dynamic(
        work / "01_MC200_TT_LOW_W4",
        {"P4_EVENT_NOISE_MC200_LOW"},
    )
    reset_dynamic(
        work / "02_PVT3_MC20_LOW_W4",
        {
            "P4_PVT_TT_MC20_LOW",
            "P5_PVT_SS_MC20_LOW",
            "P6_PVT_FF_MC20_LOW",
        },
    )
    reset_static(work / "03_FULL255_STATIC")
    commands = [
        [
            sys.executable,
            "scripts/run_fast64_v2.py",
            "--phase",
            "mc200-low",
            "--workers",
            "4",
        ],
        [sys.executable, "scripts/analyze_mc200_low_w4.py"],
        [
            sys.executable,
            "scripts/run_fast64_v2.py",
            "--phase",
            "pvt-formal",
            "--workers",
            "4",
        ],
        [sys.executable, "scripts/finalize_pvt3_mc20.py"],
        [
            sys.executable,
            "run_static_queue.py",
            "--queue",
            "tt_four_seeds",
            "S044_TT",
            "S116_TT",
            "S180_TT",
            "S106_TT",
        ],
        [
            sys.executable,
            "run_static_queue.py",
            "--queue",
            "seed44_pvt_remaining",
            "S044_SS",
            "S044_FF",
        ],
        [sys.executable, "build_final_summary.py"],
    ]
    write_json(
        run_root / "FULL_RUN_PLAN.json",
        {
            "state": "STAGED",
            "work_root": str(work),
            "commands": commands,
            "result_root": str(run_root),
            "source_baseline_unchanged": True,
            "staged_utc": utc_now(),
        },
    )
    return run_root, commands


def full_run(dry_run: bool) -> int:
    run_root, commands = prepare_full_run()
    work = run_root / "work"
    pre = preflight(run_root)
    if not pre["pass"]:
        write_json(
            run_root / "RUN_STATUS.json",
            {
                "state": "FAILED_PREFLIGHT",
                "mode": "FULL",
                "completed_utc": utc_now(),
            },
        )
        return 2
    if dry_run:
        write_json(
            run_root / "RUN_STATUS.json",
            {
                "state": "STAGED_DRY_RUN_PASS",
                "mode": "FULL_DRY_RUN",
                "preflight_pass": True,
                "commands": commands,
                "completed_utc": utc_now(),
            },
        )
        write_tree_manifest(run_root, run_root / "RUN_MANIFEST_SHA256.csv")
        print(f"FULL_DRY_RUN_STAGED {run_root}", flush=True)
        return 0

    command_specs = [
        (commands[0], work / "01_MC200_TT_LOW_W4", "01_mc200_run.log"),
        (commands[1], work / "01_MC200_TT_LOW_W4", "01_mc200_analyze.log"),
        (commands[2], work / "02_PVT3_MC20_LOW_W4", "02_pvt3_run.log"),
        (commands[3], work / "02_PVT3_MC20_LOW_W4", "02_pvt3_finalize.log"),
        (commands[4], work / "03_FULL255_STATIC", "03_static_tt.log"),
        (commands[5], work / "03_FULL255_STATIC", "03_static_seed44_pvt.log"),
        (
            commands[6],
            work / "04_CROSS_CAMPAIGN_SUMMARY",
            "04_cross_summary.log",
        ),
    ]
    results: list[dict[str, Any]] = []
    for command, cwd, name in command_specs:
        completed = run_command(
            command,
            cwd=cwd,
            log_path=run_root / "launcher_logs" / name,
        )
        results.append(
            {
                "command": command,
                "cwd": str(cwd),
                "returncode": completed.returncode,
            }
        )
        if completed.returncode != 0:
            break
    passed = len(results) == len(command_specs) and all(
        row["returncode"] == 0 for row in results
    )
    write_json(
        run_root / "RUN_STATUS.json",
        {
            "state": "COMPLETE" if passed else "FAILED",
            "mode": "FULL",
            "commands": results,
            "results": str(work),
            "completed_utc": utc_now(),
        },
    )
    write_tree_manifest(run_root, run_root / "RUN_MANIFEST_SHA256.csv")
    return 0 if passed else 2


def audit_manifest() -> int:
    path = AUDITS / "package_manifest_sha256.csv"
    if not path.is_file():
        print(f"manifest absent: {path}", file=sys.stderr)
        return 2
    rows = read_csv(path)
    mismatches = []
    for row in rows:
        file = ROOT / row["relative_path"]
        if not file.is_file():
            mismatches.append(
                {"relative_path": row["relative_path"], "reason": "MISSING"}
            )
            continue
        actual = sha256(file)
        if actual != row["sha256"]:
            mismatches.append(
                {
                    "relative_path": row["relative_path"],
                    "reason": "HASH",
                    "expected": row["sha256"],
                    "actual": actual,
                }
            )
    payload = {
        "status": (
            "PASS_PACKAGE_MANIFEST_READBACK"
            if not mismatches
            else "FAIL_PACKAGE_MANIFEST_READBACK"
        ),
        "pass": not mismatches,
        "record_count": len(rows),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "completed_utc": utc_now(),
    }
    write_json(AUDITS / "manifest_readback_latest.json", payload)
    print(json.dumps(payload, indent=2), flush=True)
    return 0 if payload["pass"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("preflight", "quick-verify", "full", "full-dry-run", "audit"),
    )
    args = parser.parse_args()
    if args.command == "preflight":
        payload = preflight()
        print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
        return 0 if payload["pass"] else 2
    if args.command == "quick-verify":
        return quick_verify()
    if args.command == "full":
        return full_run(False)
    if args.command == "full-dry-run":
        return full_run(True)
    return audit_manifest()


if __name__ == "__main__":
    raise SystemExit(main())
