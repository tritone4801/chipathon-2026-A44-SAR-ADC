#!/usr/bin/env python3
"""Freeze and strictly compare the first MC10 run against current MC200."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "csv" / "mc10_master.csv"
CODES = ROOT / "csv" / "mc10_codes.csv"
REFERENCE_MASTER = ROOT / "references" / "current_mc200_target_master.csv"
REFERENCE_CODES = ROOT / "references" / "current_mc200_target_codes.csv"
V7_ROOT = Path(
    r"C:\Users\15031\eda\designs\manual_goal\verification"
    r"\A44_FAST64_D3_ONLY_MC200_V7"
)
EARLY_ROOT = Path(
    r"C:\Users\15031\eda\designs\manual_goal\verification"
    r"\A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
)
FIXED_ROOT = ROOT / "references" / "fixed50_41_compact"
METRICS = ("snr_db", "sndr_db", "enob_raw", "sfdr_dbc", "thd_db")
FLAGS = (
    "state",
    "hard_dynamic_pass",
    "snr_budget_pass",
    "preferred_nominal_pass",
    "valid_frame_count",
    "invalid_count",
    "timeout_count",
    "missing_frame_count",
    "duplicate_frame_count",
    "clipping_count",
)
PROFILE = (
    "maxstep_ns",
    "measurement_solver_profile",
    "execution_mode",
    "mismatch_checksum_sha256",
    "noise_draw_checksum_sha256",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def master_map(rows):
    return {(int(row["mismatch_seed"]), row.get("band", "LOW")): row for row in rows}


def code_map(rows, early=False):
    output = {}
    for row in rows:
        band = "LOW" if early else row["band"]
        output[
            (
                int(row["mismatch_seed"]),
                band,
                int(row["frame_index"]),
            )
        ] = int(row["code"])
    return output


def stream(mapping, key):
    seed, band = key
    values = []
    for frame in range(64):
        frame_key = (seed, band, frame)
        if frame_key not in mapping:
            return None
        values.append(mapping[frame_key])
    return tuple(values)


def main() -> int:
    execution = json.loads(
        (ROOT / "results" / "mc10_execution_status.json").read_text(
            encoding="utf-8"
        )
    )
    current_master_rows = read_csv(MASTER)
    current_code_rows = read_csv(CODES)
    reference_master_rows = read_csv(REFERENCE_MASTER)
    reference_code_rows = read_csv(REFERENCE_CODES)
    current_master = master_map(current_master_rows)
    reference_master = master_map(reference_master_rows)
    current_codes = code_map(current_code_rows)
    reference_codes = code_map(reference_code_rows)
    v7_codes = code_map(read_csv(V7_ROOT / "csv" / "dynamic_codes.csv"))
    fixed_codes = code_map(
        read_csv(FIXED_ROOT / "data" / "fixed50_target_codes.csv")
    )
    early_codes = code_map(
        read_csv(EARLY_ROOT / "csv" / "dynamic_mc200_fast64_codes.csv"),
        early=True,
    )

    record_rows = []
    difference_rows = []
    branch_rows = []
    for key in sorted(reference_master, key=lambda item: (item[0], item[1])):
        seed, band = key
        expected = reference_master[key]
        actual = current_master.get(key)
        expected_stream = stream(reference_codes, key)
        actual_stream = stream(current_codes, key)
        differing_frames = []
        if actual_stream is not None:
            differing_frames = [
                frame
                for frame, (left, right) in enumerate(
                    zip(expected_stream, actual_stream)
                )
                if left != right
            ]
        else:
            differing_frames = list(range(64))
        metrics_exact = actual is not None and all(
            float(expected[field]) == float(actual[field]) for field in METRICS
        )
        flags_exact = actual is not None and all(
            expected[field] == actual[field] for field in FLAGS
        )
        profile_exact = actual is not None and all(
            expected[field] == actual[field] for field in PROFILE
        )
        checksum_exact = (
            actual is not None
            and expected["compact_code_checksum_sha256"]
            == actual["compact_code_checksum_sha256"]
        )
        code_exact = actual_stream == expected_stream
        record_exact = all(
            (code_exact, metrics_exact, flags_exact, profile_exact, checksum_exact)
        )
        record_rows.append(
            {
                "mismatch_seed": seed,
                "band": band,
                "record_exact": record_exact,
                "code_exact": code_exact,
                "different_frames": len(differing_frames),
                "metric_exact": metrics_exact,
                "flags_exact": flags_exact,
                "profile_exact": profile_exact,
                "checksum_exact": checksum_exact,
                "expected_state": expected["state"],
                "actual_state": actual["state"] if actual else "MISSING",
                "expected_sndr_db": expected["sndr_db"],
                "actual_sndr_db": actual["sndr_db"] if actual else "",
            }
        )
        for frame in differing_frames:
            difference_rows.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "frame_index": frame,
                    "current_mc200_code": expected_stream[frame],
                    "mc10_code": (
                        actual_stream[frame] if actual_stream is not None else ""
                    ),
                    "delta_code": (
                        actual_stream[frame] - expected_stream[frame]
                        if actual_stream is not None
                        else ""
                    ),
                }
            )

        references = {
            "CURRENT_MC200": expected_stream,
            "V7_MC200": stream(v7_codes, key),
            "FIXED50_41": stream(fixed_codes, key),
            "EARLY_MC200": stream(early_codes, key),
        }
        matching = [
            label
            for label, values in references.items()
            if values is not None and values == actual_stream
        ]
        branch_rows.append(
            {
                "mismatch_seed": seed,
                "band": band,
                "matching_branches": ";".join(matching) if matching else "THIRD_BRANCH",
                "matches_current_mc200": "CURRENT_MC200" in matching,
                "matches_v7_mc200": "V7_MC200" in matching,
                "matches_fixed50_41": "FIXED50_41" in matching,
                "matches_early_mc200": "EARLY_MC200" in matching,
            }
        )

    write_csv(
        ROOT / "comparisons" / "current_mc200_strict_comparison.csv",
        record_rows,
        (
            "mismatch_seed",
            "band",
            "record_exact",
            "code_exact",
            "different_frames",
            "metric_exact",
            "flags_exact",
            "profile_exact",
            "checksum_exact",
            "expected_state",
            "actual_state",
            "expected_sndr_db",
            "actual_sndr_db",
        ),
    )
    write_csv(
        ROOT / "comparisons" / "frame_code_differences.csv",
        difference_rows,
        (
            "mismatch_seed",
            "band",
            "frame_index",
            "current_mc200_code",
            "mc10_code",
            "delta_code",
        ),
    )
    write_csv(
        ROOT / "comparisons" / "historical_branch_classification.csv",
        branch_rows,
        (
            "mismatch_seed",
            "band",
            "matching_branches",
            "matches_current_mc200",
            "matches_v7_mc200",
            "matches_fixed50_41",
            "matches_early_mc200",
        ),
    )

    exact_records = sum(row["record_exact"] for row in record_rows)
    exact_frames = 1280 - len(difference_rows)
    checks = {
        "execution_pass": execution["pass"] is True,
        "twenty_records_compared": len(record_rows) == 20,
        "all_20_records_exact": exact_records == 20,
        "all_1280_frames_exact": exact_frames == 1280,
        "all_metrics_exact": all(row["metric_exact"] for row in record_rows),
        "all_flags_exact": all(row["flags_exact"] for row in record_rows),
        "all_profiles_exact": all(row["profile_exact"] for row in record_rows),
        "all_checksums_exact": all(row["checksum_exact"] for row in record_rows),
    }
    strict_pass = all(checks.values())
    audit = {
        "status": (
            "PASS_CURRENT_MC200_MC10_STRICT_REPRO"
            if strict_pass
            else "FAIL_CURRENT_MC200_MC10_REPRO"
        ),
        "pass": strict_pass,
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "records_compared": len(record_rows),
        "record_exact_count": exact_records,
        "record_different_count": len(record_rows) - exact_records,
        "frame_exact_count": exact_frames,
        "frame_different_count": len(difference_rows),
        "different_keys": [
            {
                "mismatch_seed": row["mismatch_seed"],
                "band": row["band"],
                "different_frames": row["different_frames"],
            }
            for row in record_rows
            if not row["record_exact"]
        ],
        "first_run_immutable_artifacts": {
            "mc10_master_sha256": sha256(MASTER),
            "mc10_codes_sha256": sha256(CODES),
            "comparison_sha256": sha256(
                ROOT / "comparisons" / "current_mc200_strict_comparison.csv"
            ),
            "frame_differences_sha256": sha256(
                ROOT / "comparisons" / "frame_code_differences.csv"
            ),
        },
        "diagnostic_results_cannot_change_this_status": True,
    }
    write_json(ROOT / "results" / "strict_reproduction_audit.json", audit)
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
