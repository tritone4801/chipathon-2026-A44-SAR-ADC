#!/usr/bin/env python3
"""Audit current-resizing MC200 smoke execution and binding."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "manifests/smoke_job_matrix.csv"


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def main() -> None:
    with MATRIX.open(encoding="utf-8", newline="") as stream:
        matrix = list(csv.DictReader(stream))
    candidate = str(
        ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    )
    rows = []
    for job in matrix:
        path = ROOT / "results/jobs" / f"{job['job_id']}.json"
        result = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        deck_path = ROOT / str(result.get("deck", ""))
        deck = (
            deck_path.read_text(encoding="utf-8", errors="replace")
            if deck_path.is_file()
            else ""
        )
        checks = {
            "result_present": path.is_file(),
            "returncode_zero": int(result.get("returncode", -1)) == 0,
            "protocol_clean": truth(result.get("protocol_clean")),
            "candidate_comparator_bound": candidate in deck,
            "mismatch_seed_bound": f".option seed={job['mismatch_seed']}" in deck,
            "noise_seed_bound": str(job["noise_seed"])
            == str(result.get("noise_seed", "")),
            "fixed_tt_low_w4_50ps": result.get("pvt") == "TT_3P3_27C"
            and result.get("band") == "LOW"
            and int(result.get("retained_frame_start", -1)) == 4
            and int(result.get("retained_frame_end", -1)) == 67
            and abs(float(result.get("maxstep_ns", -1.0)) - 0.05) < 1e-12,
        }
        rows.append(
            {
                "job_id": job["job_id"],
                "mismatch_seed": int(job["mismatch_seed"]),
                "performance_status": result.get("overall_status", "MISSING"),
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    checks = {
        "smoke_record_count_3": len(rows) == 3,
        "all_execution_protocol_binding_pass": all(row["pass"] for row in rows),
    }
    payload = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "pass": all(checks.values()),
        "performance_is_not_a_smoke_gate": True,
        "rows": rows,
    }
    out = ROOT / "results/smoke_audit_current_mc200.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
