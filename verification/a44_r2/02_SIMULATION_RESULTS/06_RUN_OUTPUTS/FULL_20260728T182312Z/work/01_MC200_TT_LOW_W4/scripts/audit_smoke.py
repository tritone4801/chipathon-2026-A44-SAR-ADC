#!/usr/bin/env python3
"""Audit anchor records and exact overlap with the sealed fixed50-41 reference."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sar_campaign_common import ROOT


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    master = read_csv(ROOT / "csv" / "dynamic_master.csv")
    codes = read_csv(ROOT / "csv" / "dynamic_codes.csv")
    ref_root = ROOT / "references" / "fixed50_41_compact"
    ref_master = read_csv(ref_root / "data" / "fixed50_target_master.csv")
    ref_codes = read_csv(ref_root / "data" / "fixed50_target_codes.csv")
    requested = {1, 21, 44, 74, 183}
    master_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in master
    }
    code_by_key = {}
    for row in codes:
        code_by_key.setdefault((int(row["mismatch_seed"]), row["band"]), []).append(row)
    ref_master_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in ref_master
    }
    ref_code_by_key = {}
    for row in ref_codes:
        ref_code_by_key.setdefault(
            (int(row["mismatch_seed"]), row["band"]), []
        ).append(row)
    overlap = sorted(set(master_by_key) & set(ref_master_by_key))
    comparisons = []
    for key in overlap:
        current_stream = [
            int(row["code"])
            for row in sorted(code_by_key[key], key=lambda row: int(row["frame_index"]))
        ]
        reference_stream = [
            int(row["code"])
            for row in sorted(
                ref_code_by_key[key], key=lambda row: int(row["frame_index"])
            )
        ]
        comparisons.append(
            {
                "mismatch_seed": key[0],
                "band": key[1],
                "code_exact": current_stream == reference_stream,
                "frame_count": len(current_stream),
                "metric_exact": all(
                    abs(float(master_by_key[key][metric]) - float(ref_master_by_key[key][metric]))
                    <= 1e-12
                    for metric in ("snr_db", "sndr_db", "enob_raw", "sfdr_dbc", "thd_db")
                ),
                "state_exact": master_by_key[key]["state"]
                == ref_master_by_key[key]["state"],
            }
        )
    checks = {
        "ten_anchor_records": len(master) == 10
        and {int(row["mismatch_seed"]) for row in master} == requested,
        "all_anchor_records_valid": all(
            row["state"] in {"VALID_PASS", "VALID_FAIL"} for row in master
        ),
        "all_anchor_records_50ps": all(
            float(row["maxstep_ns"]) == 0.05 for row in master
        ),
        "all_anchor_records_robust_gear": all(
            row["measurement_solver_profile"] == "ROBUST_GEAR" for row in master
        ),
        "all_640_codes_present": len(codes) == 640
        and all(len(rows) == 64 for rows in code_by_key.values()),
        "four_fixed50_reference_overlaps": len(comparisons) == 4,
        "overlap_code_exact": all(row["code_exact"] for row in comparisons),
        "overlap_metric_exact": all(row["metric_exact"] for row in comparisons),
        "overlap_state_exact": all(row["state_exact"] for row in comparisons),
    }
    result = {
        "status": "PASS_ANCHOR_SMOKE" if all(checks.values()) else "FAIL_ANCHOR_SMOKE",
        "pass": all(checks.values()),
        "checks": checks,
        "reference_comparisons": comparisons,
    }
    (ROOT / "results" / "anchor_smoke_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
