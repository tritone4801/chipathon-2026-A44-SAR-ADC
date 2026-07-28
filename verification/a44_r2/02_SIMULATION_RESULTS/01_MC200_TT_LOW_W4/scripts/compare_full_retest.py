#!/usr/bin/env python3
"""Compare the full fixed50 MC200 against early MC200, V7, fixed50-41, V10 and V11."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


METRICS = ("snr_db", "sndr_db", "enob", "sfdr_dbc", "thd_db")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else [])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def dataset(label, root, master_rel, codes_rel, early=False):
    root = Path(root)
    master_path = root / master_rel
    codes_path = root / codes_rel
    master_rows = read_csv(master_path)
    code_rows = read_csv(codes_path)
    master = {
        (int(row["mismatch_seed"]), "LOW" if early else row["band"]): row
        for row in master_rows
    }
    codes = {
        (
            int(row["mismatch_seed"]),
            "LOW" if early else row["band"],
            int(row["frame_index"]),
        ): row
        for row in code_rows
    }
    return {
        "label": label,
        "root": str(root),
        "master_path": str(master_path),
        "codes_path": str(codes_path),
        "master_sha256": sha256(master_path),
        "codes_sha256": sha256(codes_path),
        "early": early,
        "master": master,
        "codes": codes,
    }


def metric(row, name, early=False):
    if name == "enob":
        return float(row["enob_bit" if early else "enob_raw"])
    return float(row[name])


def bool_text(value):
    return "True" if value else "False"


def compare(current, reference, key):
    current_master = current["master"][key]
    reference_master = reference["master"][key]
    current_stream = [
        current["codes"][(key[0], key[1], frame)]["code"] for frame in range(64)
    ]
    reference_stream = [
        reference["codes"][(key[0], key[1], frame)]["code"] for frame in range(64)
    ]
    differing = [
        frame
        for frame, (left, right) in enumerate(zip(current_stream, reference_stream))
        if left != right
    ]
    early = reference["early"]
    deltas = {
        name: metric(current_master, name) - metric(reference_master, name, early)
        for name in METRICS
    }
    metric_exact = all(
        math.isclose(value, 0.0, rel_tol=0.0, abs_tol=1e-12)
        for value in deltas.values()
    )
    current_step = float(current_master["maxstep_ns"]) * 1000.0
    reference_step = (
        float(reference_master["measurement_maxstep_ps"])
        if early
        else float(reference_master["maxstep_ns"]) * 1000.0
    )
    current_profile = current_master["measurement_solver_profile"]
    reference_profile = reference_master["measurement_solver_profile"]
    result = {
        "mismatch_seed": key[0],
        "band": key[1],
        "reference": reference["label"],
        "code_exact": bool_text(not differing),
        "differing_frame_count": len(differing),
        "differing_frames": ";".join(str(frame) for frame in differing),
        "metric_exact": bool_text(metric_exact),
        "electrical_exact": bool_text(not differing and metric_exact),
        "current_state": current_master["state"],
        "reference_state": reference_master["status"] if early else reference_master["state"],
        "state_comparable": bool_text(not early),
        "state_exact": ""
        if early
        else bool_text(current_master["state"] == reference_master["state"]),
        "current_maxstep_ps": current_step,
        "reference_maxstep_ps": reference_step,
        "current_solver_profile": current_profile,
        "reference_solver_profile": reference_profile,
        "same_execution_profile": bool_text(
            current_step == reference_step and current_profile == reference_profile
        ),
        "mismatch_checksum_match": ""
        if early
        else bool_text(
            current_master["mismatch_checksum_sha256"]
            == reference_master["mismatch_checksum_sha256"]
        ),
        "noise_checksum_match": ""
        if early
        else bool_text(
            current_master["noise_draw_checksum_sha256"]
            == reference_master["noise_draw_checksum_sha256"]
        ),
    }
    for name in METRICS:
        result[f"current_{name}"] = metric(current_master, name)
        result[f"reference_{name}"] = metric(reference_master, name, early)
        result[f"delta_{name}"] = deltas[name]
    frame_rows = [
        {
            "mismatch_seed": key[0],
            "band": key[1],
            "reference": reference["label"],
            "frame_index": frame,
            "current_code": current_stream[frame],
            "reference_code": reference_stream[frame],
            "delta_code": int(current_stream[frame]) - int(reference_stream[frame]),
        }
        for frame in differing
    ]
    return result, frame_rows


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: compare_full_retest.py VERIFICATION_ROOT FULL_RETEST_ROOT")
    verification = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    output = root / "comparisons"
    output.mkdir(parents=True, exist_ok=True)
    current = dataset(
        "FULL_FIXED50_MC200",
        root,
        "csv/dynamic_master.csv",
        "csv/dynamic_codes.csv",
    )
    references = [
        dataset(
            "EARLY_MC200",
            verification / "A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718",
            "csv/dynamic_mc200_fast64.csv",
            "csv/dynamic_mc200_fast64_codes.csv",
            early=True,
        ),
        dataset(
            "V7_MC200",
            verification / "A44_FAST64_D3_ONLY_MC200_V7",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
        dataset(
            "FIXED50_41",
            root / "references" / "fixed50_41_compact",
            "data/fixed50_target_master.csv",
            "data/fixed50_target_codes.csv",
        ),
        dataset(
            "V10_MC10",
            verification / "A44_FAST64_D3_MC10_1H_V10",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
        dataset(
            "V11_MC10",
            verification / "A44_FAST64_D3_MC10_EXCL3_REPRO_V11",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
    ]
    current_keys = set(current["master"])
    comparisons = []
    frame_differences = []
    by_key = {key: {} for key in current_keys}
    for reference in references:
        comparable = sorted(current_keys & set(reference["master"]))
        for key in comparable:
            if any((key[0], key[1], frame) not in reference["codes"] for frame in range(64)):
                raise RuntimeError(f"{reference['label']} missing code frame for {key}")
            row, differences = compare(current, reference, key)
            comparisons.append(row)
            frame_differences.extend(differences)
            by_key[key][reference["label"]] = row
    write_csv(output / "comparison_by_reference.csv", comparisons)
    write_csv(
        output / "frame_code_differences.csv",
        frame_differences,
        fields=(
            "mismatch_seed",
            "band",
            "reference",
            "frame_index",
            "current_code",
            "reference_code",
            "delta_code",
        ),
    )

    classifications = []
    for key in sorted(current_keys):
        available = by_key[key]
        unavailable = [
            f"{reference['label']}:REFERENCE_KEY_ABSENT"
            for reference in references
            if reference["label"] not in available
        ]
        exact = sorted(
            label for label, row in available.items() if row["code_exact"] == "True"
        )
        classifications.append(
            {
                "mismatch_seed": key[0],
                "band": key[1],
                "reference_sets_available": ";".join(sorted(available)),
                "exact_reference_sets": ";".join(exact),
                "matches_early_mc200": available.get("EARLY_MC200", {}).get("code_exact", ""),
                "matches_v7_mc200": available.get("V7_MC200", {}).get("code_exact", ""),
                "matches_fixed50_41": available.get("FIXED50_41", {}).get("code_exact", ""),
                "matches_v10_mc10": available.get("V10_MC10", {}).get("code_exact", ""),
                "matches_v11_mc10": available.get("V11_MC10", {}).get("code_exact", ""),
                "unavailable_reference_reasons": ";".join(unavailable),
                "new_vs_all_available_references": bool_text(bool(available) and not exact),
            }
        )
    write_csv(output / "key_classification.csv", classifications)

    reference_summary = {}
    for reference in references:
        rows = [row for row in comparisons if row["reference"] == reference["label"]]
        reference_summary[reference["label"]] = {
            "reference_records": len(reference["master"]),
            "comparable_records": len(rows),
            "not_comparable_current_records": len(current_keys) - len(rows),
            "not_comparable_reason": "REFERENCE_KEY_ABSENT",
            "code_exact_records": sum(row["code_exact"] == "True" for row in rows),
            "code_different_records": sum(row["code_exact"] == "False" for row in rows),
            "exact_frames": 64 * len(rows)
            - sum(int(row["differing_frame_count"]) for row in rows),
            "different_frames": sum(int(row["differing_frame_count"]) for row in rows),
            "metric_exact_records": sum(row["metric_exact"] == "True" for row in rows),
            "state_exact_records": sum(row["state_exact"] == "True" for row in rows),
            "same_execution_profile_records": sum(
                row["same_execution_profile"] == "True" for row in rows
            ),
        }

    fixed_rows = [
        row for row in comparisons if row["reference"] == "FIXED50_41"
    ]
    fixed_checks = {
        "all_41_records_comparable": len(fixed_rows) == 41,
        "all_41_records_code_exact": sum(
            row["code_exact"] == "True" for row in fixed_rows
        )
        == 41,
        "all_2624_frames_exact": sum(
            int(row["differing_frame_count"]) for row in fixed_rows
        )
        == 0,
        "all_41_metrics_exact": sum(
            row["metric_exact"] == "True" for row in fixed_rows
        )
        == 41,
        "all_41_states_exact": sum(
            row["state_exact"] == "True" for row in fixed_rows
        )
        == 41,
        "all_41_profiles_exact": sum(
            row["same_execution_profile"] == "True" for row in fixed_rows
        )
        == 41,
    }
    repeatability = {
        "status": "PASS_FIXED50_41_REPEATABILITY"
        if all(fixed_checks.values())
        else "FAIL_FIXED50_41_REPEATABILITY",
        "pass": all(fixed_checks.values()),
        "checks": fixed_checks,
        "reference_summary": reference_summary["FIXED50_41"],
    }
    (root / "results" / "repeatability_audit.json").write_text(
        json.dumps(repeatability, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "status": "COMPARISON_COMPLETE",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "current_records": len(current["master"]),
        "current_code_rows": len(current["codes"]),
        "reference_summary": reference_summary,
        "fixed50_41_repeatability": repeatability,
        "keys_matching_no_available_reference": sum(
            row["new_vs_all_available_references"] == "True"
            for row in classifications
        ),
        "bindings": {
            data["label"]: {
                "root": data["root"],
                "master_path": data["master_path"],
                "codes_path": data["codes_path"],
                "master_sha256": data["master_sha256"],
                "codes_sha256": data["codes_sha256"],
            }
            for data in [current, *references]
        },
    }
    (output / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if repeatability["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
