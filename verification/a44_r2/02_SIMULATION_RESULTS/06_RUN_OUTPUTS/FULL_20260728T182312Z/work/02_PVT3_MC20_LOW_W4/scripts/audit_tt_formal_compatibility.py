#!/usr/bin/env python3
"""Gate SS/FF release on strict TT compatibility for all selected seeds."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SEEDS = (44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    reference = {
        int(row["mismatch_seed"]): row
        for row in read_csv(ROOT / "references/tt_mc200_selected20_reference.csv")
    }
    rows = []
    for seed in SEEDS:
        job_id = f"PVT3_TT_3P3_27C_CMP_IN_A2P25_W_T1P000_S{seed:03d}_LOW_W4"
        path = ROOT / "results/jobs" / f"{job_id}.json"
        result = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        ref = reference[seed]
        checks = {
            "result_present": path.is_file(),
            "terminal": result.get("state") in {"COMPLETE", "COMPLETE_WITH_FAIL"},
            "returncode_zero": int(result.get("returncode", -1)) == 0,
            "protocol_clean": bool(result.get("protocol_clean")),
            "frame_count_68": int(result.get("valid_frame_count", -1)) == 68,
            "all_68_checksum_match": result.get("codes_all_checksum") == ref["codes_all_checksum"],
            "w4_checksum_match": result.get("codes_retained_checksum") == ref["codes_retained_checksum"],
            "sndr_exact_match": abs(
                float(result.get("steady_state_sndr_db", float("nan")))
                - float(ref["steady_state_sndr_db"])
            )
            < 1e-12,
        }
        rows.append({"mismatch_seed": seed, "job_id": job_id, "checks": checks, "pass": all(checks.values())})
    payload = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(rows),
        "pass_count": sum(row["pass"] for row in rows),
        "fail_count": sum(not row["pass"] for row in rows),
        "pass": len(rows) == 20 and all(row["pass"] for row in rows),
        "rows": rows,
    }
    out = ROOT / "results/tt_formal_compatibility_gate.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("record_count", "pass_count", "fail_count", "pass")}, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
