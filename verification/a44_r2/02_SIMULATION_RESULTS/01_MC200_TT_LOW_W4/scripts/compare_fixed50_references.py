#!/usr/bin/env python3
"""Compare the fixed-50-ps rerun with early MC200, V7, V10, and V11."""

import csv
import json
import math
import sys
from pathlib import Path


METRICS = ("snr_db", "sndr_db", "enob", "sfdr_dbc", "thd_db")


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def master_key(row, early=False):
    return int(row["mismatch_seed"]), "LOW" if early else row["band"]


def code_key(row, early=False):
    return (
        int(row["mismatch_seed"]),
        "LOW" if early else row["band"],
        int(row["frame_index"]),
    )


def metric(row, name, early=False):
    if name == "enob":
        return float(row["enob_bit" if early else "enob_raw"])
    return float(row[name])


def maxstep_ps(row, early=False):
    if early:
        return float(row["measurement_maxstep_ps"])
    return float(row["maxstep_ns"]) * 1000.0


def load_dataset(label, root, master_relative, codes_relative, early=False):
    root = Path(root)
    master_rows = read_csv(root / master_relative)
    code_rows = read_csv(root / codes_relative)
    return {
        "label": label,
        "root": str(root),
        "early": early,
        "master": {master_key(row, early): row for row in master_rows},
        "codes": {code_key(row, early): row for row in code_rows},
    }


def bool_text(value):
    return "True" if value else "False"


def compare_one(target, current, reference):
    key = (int(target["mismatch_seed"]), target["band"])
    current_master = current["master"][key]
    reference_master = reference["master"][key]
    current_codes = {
        frame: row
        for (seed, band, frame), row in current["codes"].items()
        if (seed, band) == key
    }
    reference_codes = {
        frame: row
        for (seed, band, frame), row in reference["codes"].items()
        if (seed, band) == key
    }
    if set(current_codes) != set(range(64)):
        raise RuntimeError(f"current code coverage is not 64 frames for {key}")
    if set(reference_codes) != set(range(64)):
        raise RuntimeError(
            f"{reference['label']} code coverage is not 64 frames for {key}"
        )
    differing = [
        frame
        for frame in range(64)
        if current_codes[frame]["code"] != reference_codes[frame]["code"]
    ]
    early = reference["early"]
    deltas = {
        name: metric(current_master, name)
        - metric(reference_master, name, early)
        for name in METRICS
    }
    metric_exact = all(
        math.isclose(value, 0.0, rel_tol=0.0, abs_tol=1e-12)
        for value in deltas.values()
    )
    current_profile = current_master["measurement_solver_profile"]
    reference_profile = reference_master["measurement_solver_profile"]
    current_step = maxstep_ps(current_master)
    reference_step = maxstep_ps(reference_master, early)
    row = {
        "target_id": target["target_id"],
        "mismatch_seed": key[0],
        "band": key[1],
        "reasons": target["reasons"],
        "reference": reference["label"],
        "code_exact": bool_text(not differing),
        "differing_frame_count": len(differing),
        "differing_frames": ";".join(map(str, differing)),
        "metric_exact": bool_text(metric_exact),
        "electrical_exact": bool_text(not differing and metric_exact),
        "current_state": current_master["state"],
        "reference_state": (
            reference_master["status"]
            if early
            else reference_master["state"]
        ),
        "state_comparable": bool_text(not early),
        "state_exact": (
            ""
            if early
            else bool_text(current_master["state"] == reference_master["state"])
        ),
        "current_maxstep_ps": current_step,
        "reference_maxstep_ps": reference_step,
        "current_solver_profile": current_profile,
        "reference_solver_profile": reference_profile,
        "same_execution_profile": bool_text(
            current_step == reference_step
            and current_profile == reference_profile
        ),
    }
    for name in METRICS:
        row[f"current_{name}"] = metric(current_master, name)
        row[f"reference_{name}"] = metric(reference_master, name, early)
        row[f"delta_{name}"] = deltas[name]
    if not early:
        row["mismatch_checksum_match"] = bool_text(
            current_master["mismatch_checksum_sha256"]
            == reference_master["mismatch_checksum_sha256"]
        )
        row["noise_checksum_match"] = bool_text(
            current_master["noise_draw_checksum_sha256"]
            == reference_master["noise_draw_checksum_sha256"]
        )
    else:
        row["mismatch_checksum_match"] = ""
        row["noise_checksum_match"] = ""
    frame_diffs = [
        {
            "target_id": target["target_id"],
            "mismatch_seed": key[0],
            "band": key[1],
            "reference": reference["label"],
            "frame_index": frame,
            "current_code": current_codes[frame]["code"],
            "reference_code": reference_codes[frame]["code"],
            "delta_code": (
                int(current_codes[frame]["code"])
                - int(reference_codes[frame]["code"])
            ),
        }
        for frame in differing
    ]
    return row, frame_diffs


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with Path(path).open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: compare_fixed50_references.py "
            "VERIFICATION_ROOT RERUN_ROOT OUTPUT_DIR"
        )
    verification = Path(sys.argv[1]).resolve()
    rerun_root = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    targets = read_csv(rerun_root / "config" / "fixed50_target_contract.csv")

    current = load_dataset(
        "FIXED50_RERUN",
        rerun_root,
        "csv/fixed50_target_master.csv",
        "csv/fixed50_target_codes.csv",
    )
    references = [
        load_dataset(
            "EARLY_MC200",
            verification
            / "A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718",
            "csv/dynamic_mc200_fast64.csv",
            "csv/dynamic_mc200_fast64_codes.csv",
            early=True,
        ),
        load_dataset(
            "V7_MC200",
            verification / "A44_FAST64_D3_ONLY_MC200_V7",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
        load_dataset(
            "V10_MC10",
            verification / "A44_FAST64_D3_MC10_1H_V10",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
        load_dataset(
            "V11_MC10",
            verification / "A44_FAST64_D3_MC10_EXCL3_REPRO_V11",
            "csv/dynamic_master.csv",
            "csv/dynamic_codes.csv",
        ),
    ]

    comparisons = []
    frame_diffs = []
    by_target = {row["target_id"]: {} for row in targets}
    for target in targets:
        key = (int(target["mismatch_seed"]), target["band"])
        for reference in references:
            if key not in reference["master"]:
                continue
            row, diffs = compare_one(target, current, reference)
            comparisons.append(row)
            frame_diffs.extend(diffs)
            by_target[target["target_id"]][reference["label"]] = row

    write_csv(output / "comparison_by_reference.csv", comparisons)
    write_csv(
        output / "frame_code_differences.csv",
        frame_diffs,
        fields=(
            "target_id",
            "mismatch_seed",
            "band",
            "reference",
            "frame_index",
            "current_code",
            "reference_code",
            "delta_code",
        ),
    )

    classification = []
    for target in targets:
        available = by_target[target["target_id"]]
        later = [
            row
            for label, row in available.items()
            if label in {"V10_MC10", "V11_MC10"}
        ]
        exact_labels = sorted(
            label
            for label, row in available.items()
            if row["code_exact"] == "True"
        )
        classification.append(
            {
                "target_id": target["target_id"],
                "mismatch_seed": target["mismatch_seed"],
                "band": target["band"],
                "reasons": target["reasons"],
                "early_available": bool_text(
                    "EARLY_MC200" in available
                ),
                "early_code_exact": (
                    available.get("EARLY_MC200", {}).get("code_exact", "")
                ),
                "v7_code_exact": available["V7_MC200"]["code_exact"],
                "later_mc10_sources": ";".join(
                    sorted(
                        label
                        for label in available
                        if label in {"V10_MC10", "V11_MC10"}
                    )
                ),
                "later_mc10_any_code_exact": (
                    ""
                    if not later
                    else bool_text(
                        any(row["code_exact"] == "True" for row in later)
                    )
                ),
                "later_mc10_all_code_exact": (
                    ""
                    if not later
                    else bool_text(
                        all(row["code_exact"] == "True" for row in later)
                    )
                ),
                "exact_reference_sets": ";".join(exact_labels),
                "no_reference_code_exact": bool_text(not exact_labels),
            }
        )
    write_csv(output / "target_classification.csv", classification)

    r1_rows = read_csv(
        verification
        / "A44_MC200_EXTREME_TAIL_ELECTRICAL_VALIDITY_30M_R1"
        / "csv"
        / "tail_electrical_record_summary.csv"
    )
    r1_comparison = []
    for row in r1_rows:
        if row["role"] != "TAIL":
            continue
        seed = int(row["seed"])
        band = row["band"]
        frame = int(row["formal_error_frame"])
        current_code = current["codes"][(seed, band, frame)]["code"]
        r1_comparison.append(
            {
                "target_id": f"S{seed:03d}_{band}",
                "mismatch_seed": seed,
                "band": band,
                "target_frame": frame,
                "v7_formal_code": row["formal_code"],
                "r1_replay_code": row["replay_code"],
                "fixed50_rerun_code": current_code,
                "matches_v7_formal": bool_text(
                    current_code == row["formal_code"]
                ),
                "matches_r1_replay": bool_text(
                    current_code == row["replay_code"]
                ),
                "r1_50ps_25ps_match": row["50ps_25ps_match"],
                "r1_numeric_stability": row["numeric_stability"],
            }
        )
    write_csv(output / "r1_target_frame_comparison.csv", r1_comparison)

    reference_summary = {}
    for reference in references:
        rows = [
            row
            for row in comparisons
            if row["reference"] == reference["label"]
        ]
        reference_summary[reference["label"]] = {
            "comparable_records": len(rows),
            "code_exact_records": sum(
                row["code_exact"] == "True" for row in rows
            ),
            "code_different_records": sum(
                row["code_exact"] == "False" for row in rows
            ),
            "exact_frames": 64 * len(rows)
            - sum(int(row["differing_frame_count"]) for row in rows),
            "different_frames": sum(
                int(row["differing_frame_count"]) for row in rows
            ),
            "metric_exact_records": sum(
                row["metric_exact"] == "True" for row in rows
            ),
            "same_execution_profile_records": sum(
                row["same_execution_profile"] == "True" for row in rows
            ),
        }
    reason_summary = {}
    for reason in (
        "EARLY_MC200_VS_V7_LOW_CODE_MISMATCH",
        "MC10_VS_V7_CODE_MISMATCH",
        "EXTREME_TAIL_HISTORICAL_CODE_NOT_REPRODUCED",
    ):
        rows = [row for row in classification if reason in row["reasons"]]
        reason_summary[reason] = {
            "records": len(rows),
            "matches_early_mc200": sum(
                row["early_code_exact"] == "True" for row in rows
            ),
            "matches_v7_mc200": sum(
                row["v7_code_exact"] == "True" for row in rows
            ),
            "later_mc10_available": sum(
                bool(row["later_mc10_sources"]) for row in rows
            ),
            "matches_later_mc10": sum(
                row["later_mc10_any_code_exact"] == "True" for row in rows
            ),
            "matches_no_full_reference": sum(
                row["no_reference_code_exact"] == "True" for row in rows
            ),
        }
    classification_by_id = {
        row["target_id"]: row for row in classification
    }
    profile_groups = {}
    for row in comparisons:
        if (
            row["reference"] != "EARLY_MC200"
            or "EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"
            not in row["reasons"]
        ):
            continue
        key = (
            float(row["reference_maxstep_ps"]),
            row["reference_solver_profile"],
        )
        group = profile_groups.setdefault(
            key,
            {
                "early_maxstep_ps": key[0],
                "early_solver_profile": key[1],
                "records": 0,
                "fixed50_matches_early": 0,
                "fixed50_matches_v7": 0,
            },
        )
        group["records"] += 1
        group["fixed50_matches_early"] += row["code_exact"] == "True"
        group["fixed50_matches_v7"] += (
            classification_by_id[row["target_id"]]["v7_code_exact"]
            == "True"
        )
    summary = {
        "status": "COMPARISON_COMPLETE",
        "target_records": len(targets),
        "reference_summary": reference_summary,
        "reason_summary": reason_summary,
        "early_mismatch_profile_partition": sorted(
            profile_groups.values(),
            key=lambda row: (
                row["early_maxstep_ps"],
                row["early_solver_profile"],
            ),
        ),
        "targets_with_early_reference": sum(
            row["early_available"] == "True" for row in classification
        ),
        "targets_with_later_mc10_reference": sum(
            bool(row["later_mc10_sources"]) for row in classification
        ),
        "targets_matching_any_later_mc10": sum(
            row["later_mc10_any_code_exact"] == "True"
            for row in classification
        ),
        "targets_matching_v7": sum(
            row["v7_code_exact"] == "True" for row in classification
        ),
        "targets_matching_early": sum(
            row["early_code_exact"] == "True" for row in classification
        ),
        "targets_matching_no_reference": sum(
            row["no_reference_code_exact"] == "True"
            for row in classification
        ),
        "r1_tail_target_frames": len(r1_comparison),
        "r1_target_frames_matching_fixed50_rerun": sum(
            row["matches_r1_replay"] == "True"
            for row in r1_comparison
        ),
        "v7_formal_target_frames_matching_fixed50_rerun": sum(
            row["matches_v7_formal"] == "True"
            for row in r1_comparison
        ),
    }
    (output / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
