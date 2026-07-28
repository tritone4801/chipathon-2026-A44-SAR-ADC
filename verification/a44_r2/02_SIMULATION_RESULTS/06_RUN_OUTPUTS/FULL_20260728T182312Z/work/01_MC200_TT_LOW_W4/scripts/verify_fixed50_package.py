#!/usr/bin/env python3
"""Verify the compact fixed-50-ps reproduction evidence package."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    execution = load_json(root / "results" / "fixed50_execution_status.json")
    preflight = load_json(root / "results" / "fixed50_preflight.json")
    contract = load_json(root / "config" / "fixed50_target_contract.json")
    comparison = load_json(root / "comparisons" / "comparison_summary.json")

    with (root / "config" / "fixed50_target_contract.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        target_rows = list(csv.DictReader(handle))
    with (root / "data" / "fixed50_target_master.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        master_rows = list(csv.DictReader(handle))
    with (root / "data" / "fixed50_target_codes.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        code_rows = list(csv.DictReader(handle))

    ref = comparison["reference_summary"]
    reasons = comparison["reason_summary"]
    profile = {
        (float(row["early_maxstep_ps"]), row["early_solver_profile"]): row
        for row in comparison["early_mismatch_profile_partition"]
    }

    checks = {
        "execution_pass": execution["pass"] is True
        and execution["status"] == "PASS_FIXED50_EXECUTION",
        "all_execution_checks_true": all(execution["checks"].values()),
        "preflight_pass": preflight["pass"] is True
        and preflight["dependencies"]["matching"] == 20
        and preflight["production_source"]["matching"] == 113,
        "contract_frozen_41": contract["status"] == "FROZEN_BEFORE_EXECUTION"
        and contract["target_record_count"] == 41
        and contract["unique_seed_count"] == 41,
        "contract_fixed_profile": contract["maxstep_ps"] == 50
        and contract["solver_profile"] == "ROBUST_GEAR"
        and contract["nfft"] == 64,
        "csv_row_counts": len(target_rows) == 41
        and len(master_rows) == 41
        and len(code_rows) == 2624,
        "execution_file_hashes": sha256(root / "data" / "fixed50_target_master.csv")
        == execution["master_sha256"]
        and sha256(root / "data" / "fixed50_target_codes.csv")
        == execution["codes_sha256"],
        "comparison_complete": comparison["status"] == "COMPARISON_COMPLETE"
        and comparison["target_records"] == 41,
        "early_reference_counts": ref["EARLY_MC200"]["comparable_records"] == 34
        and ref["EARLY_MC200"]["code_exact_records"] == 9
        and ref["EARLY_MC200"]["code_different_records"] == 25
        and ref["EARLY_MC200"]["different_frames"] == 27,
        "v7_reference_counts": ref["V7_MC200"]["comparable_records"] == 41
        and ref["V7_MC200"]["code_exact_records"] == 24
        and ref["V7_MC200"]["code_different_records"] == 17
        and ref["V7_MC200"]["different_frames"] == 17,
        "v10_reference_exact": ref["V10_MC10"]["comparable_records"] == 5
        and ref["V10_MC10"]["code_exact_records"] == 5
        and ref["V10_MC10"]["different_frames"] == 0,
        "v11_reference_exact": ref["V11_MC10"]["comparable_records"] == 4
        and ref["V11_MC10"]["code_exact_records"] == 4
        and ref["V11_MC10"]["different_frames"] == 0,
        "later_mc10_unique_exact": comparison["targets_with_later_mc10_reference"] == 8
        and comparison["targets_matching_any_later_mc10"] == 8,
        "early_v7_mismatch_partition": reasons[
            "EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"
        ]["records"]
        == 33
        and reasons["EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"]["matches_early_mc200"]
        == 9
        and reasons["EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"]["matches_v7_mc200"]
        == 24,
        "mc10_v7_mismatch_supports_mc10": reasons["MC10_VS_V7_CODE_MISMATCH"][
            "records"
        ]
        == 6
        and reasons["MC10_VS_V7_CODE_MISMATCH"]["matches_later_mc10"] == 6
        and reasons["MC10_VS_V7_CODE_MISMATCH"]["matches_v7_mc200"] == 0,
        "tail_frames_support_r1": comparison["r1_tail_target_frames"] == 17
        and comparison["r1_target_frames_matching_fixed50_rerun"] == 17
        and comparison["v7_formal_target_frames_matching_fixed50_rerun"] == 0,
        "profile_partition_50_default": profile[(50.0, "DEFAULT")]["records"] == 6
        and profile[(50.0, "DEFAULT")]["fixed50_matches_early"] == 0
        and profile[(50.0, "DEFAULT")]["fixed50_matches_v7"] == 6,
        "profile_partition_50_robust": profile[(50.0, "ROBUST_GEAR")]["records"]
        == 10
        and profile[(50.0, "ROBUST_GEAR")]["fixed50_matches_early"] == 5
        and profile[(50.0, "ROBUST_GEAR")]["fixed50_matches_v7"] == 5,
        "profile_partition_100_default": profile[(100.0, "DEFAULT")]["records"]
        == 17
        and profile[(100.0, "DEFAULT")]["fixed50_matches_early"] == 4
        and profile[(100.0, "DEFAULT")]["fixed50_matches_v7"] == 13,
    }

    result = {
        "status": "PASS_COMPLETION_AUDIT" if all(checks.values()) else "FAIL_COMPLETION_AUDIT",
        "pass": all(checks.values()),
        "checks": checks,
        "checked_root": str(root),
        "target_records": len(target_rows),
        "master_records": len(master_rows),
        "code_rows": len(code_rows),
        "nonclaims": {
            "full_mc200_rerun": False,
            "full_mc200_dynamic_percentiles_recomputed": False,
            "signoff": False,
        },
    }
    output = root / "results" / "completion_audit.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
