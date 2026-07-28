#!/usr/bin/env python3
"""Run disjoint FULL255 case queues with durable status checkpoints."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_status(queue: str, payload: dict) -> None:
    path = ROOT / "results" / f"queue_{queue}_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_step(case_root: Path, script: str, *args: str) -> int:
    command = [sys.executable, str(case_root / "scripts" / script), *args]
    completed = subprocess.run(command, cwd=case_root, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("case", nargs="+")
    args = parser.parse_args()
    payload = {
        "queue": args.queue,
        "cases": args.case,
        "started_utc": utc_now(),
        "completed_utc": None,
        "state": "RUNNING",
        "case_status": {},
    }
    write_status(args.queue, payload)
    for case_name in args.case:
        case_root = CASES / case_name
        status = {
            "started_utc": utc_now(),
            "pilot": "PENDING",
            "transitions": "PENDING",
            "analysis": "PENDING",
        }
        payload["case_status"][case_name] = status
        write_status(args.queue, payload)
        setup = read_json(case_root / "results/setup_audit.json")
        if not setup.get("pass"):
            status["pilot"] = "BLOCKED_SETUP_AUDIT"
            status["transitions"] = "BLOCKED_SETUP_AUDIT"
            status["analysis"] = "BLOCKED_SETUP_AUDIT"
            status["completed_utc"] = utc_now()
            write_status(args.queue, payload)
            continue
        pilot = read_json(case_root / "results/runtime_pilot.json")
        if pilot.get("status") != "PASS":
            status["pilot_returncode"] = run_step(
                case_root, "run_paired_static.py", "pilot"
            )
            pilot = read_json(case_root / "results/runtime_pilot.json")
        status["pilot"] = pilot.get("status", "MISSING")
        write_status(args.queue, payload)
        transitions = read_json(case_root / "results/full_transition_execution.json")
        if transitions.get("status") != "PASS":
            status["transition_returncode"] = run_step(
                case_root, "run_paired_static.py", "transitions"
            )
            transitions = read_json(
                case_root / "results/full_transition_execution.json"
            )
        status["transitions"] = transitions.get("status", "MISSING")
        write_status(args.queue, payload)
        if status["transitions"] == "PASS":
            status["analysis_returncode"] = run_step(
                case_root, "analyze_current_full255.py"
            )
            analysis = read_json(case_root / "results/current_full255_summary.json")
            status["analysis"] = (
                "PASS_COMPLETE"
                if status["analysis_returncode"] == 0 and analysis
                else "FAIL"
            )
            status["absolute_static_status"] = analysis.get(
                "absolute_static_status", "MISSING"
            )
        else:
            status["analysis"] = "BLOCKED_TRANSITION_EXECUTION"
        status["completed_utc"] = utc_now()
        write_status(args.queue, payload)
    payload["completed_utc"] = utc_now()
    payload["state"] = (
        "COMPLETE"
        if all(
            status.get("analysis") == "PASS_COMPLETE"
            for status in payload["case_status"].values()
        )
        else "COMPLETE_WITH_BLOCKS"
    )
    write_status(args.queue, payload)
    return 0 if payload["state"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
