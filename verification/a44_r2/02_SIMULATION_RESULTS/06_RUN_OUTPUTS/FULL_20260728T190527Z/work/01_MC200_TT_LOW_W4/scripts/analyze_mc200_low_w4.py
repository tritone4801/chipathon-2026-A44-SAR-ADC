#!/usr/bin/env python3
"""Aggregate and audit the 200-record LOW FAST64_SS_W4 population."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

from fast64_v2_common import (
    CSV_DIR,
    MANIFEST_DIR,
    RESULT_DIR,
    ROOT,
    code_checksum,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


JOB_RESULT_DIR = RESULT_DIR / "jobs"
JOB_CODE_DIR = CSV_DIR / "job_codes"
JOB_PATH_DIR = CSV_DIR / "job_paths"
REFERENCE_DIR = ROOT / "references/current_mc200_full"


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def as_float(value: object) -> float:
    return float(str(value).strip())


def as_int(value: object) -> int:
    return int(str(value).strip())


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile_rows(
    rows: list[dict[str, object]], fields: Iterable[str]
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    percentiles = (0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100)
    for field in fields:
        values = np.asarray([float(row[field]) for row in rows], dtype=float)
        for percentile in percentiles:
            output.append(
                {
                    "scope": "LOW",
                    "method_id": "FAST64_SS_W4",
                    "metric": field,
                    "percentile": percentile,
                    "value": float(
                        np.percentile(values, percentile, method="linear")
                    ),
                    "population_count": len(values),
                    "percentile_method": "LINEAR_TYPE7",
                }
            )
    return output


def representative_rows(
    rows: list[dict[str, object]], percentiles: list[dict[str, object]]
) -> list[dict[str, object]]:
    sndr_percentiles = {
        int(row["percentile"]): float(row["value"])
        for row in percentiles
        if row["metric"] == "steady_state_sndr_db"
    }
    roles = [
        ("WORST", min(float(row["steady_state_sndr_db"]) for row in rows)),
        ("P1", sndr_percentiles[1]),
        ("P5", sndr_percentiles[5]),
        ("P10", sndr_percentiles[10]),
        ("P50", sndr_percentiles[50]),
    ]
    output: list[dict[str, object]] = []
    used: set[int] = set()
    for role, target in roles:
        selected = min(
            rows,
            key=lambda row: (
                abs(float(row["steady_state_sndr_db"]) - target),
                int(row["mismatch_seed"]),
            ),
        )
        seed = int(selected["mismatch_seed"])
        output.append(
            {
                "role": role,
                "target_sndr_db": target,
                "mismatch_seed": seed,
                "observed_sndr_db": selected["steady_state_sndr_db"],
                "observed_snr_db": selected["steady_state_snr_db"],
                "observed_enob_raw": selected["steady_state_enob_raw"],
                "observed_sfdr_dbc": selected["steady_state_sfdr_dbc"],
                "overall_status": selected["overall_status"],
                "duplicate_representative_seed": seed in used,
                "selection_rule": "NEAREST_OBSERVED_THEN_LOWEST_SEED",
            }
        )
        used.add(seed)
    return output


def reference_indexes() -> tuple[
    dict[int, dict[str, str]], dict[tuple[int, int], dict[str, str]]
]:
    master = {
        int(row["mismatch_seed"]): row
        for row in read_csv(REFERENCE_DIR / "dynamic_master.csv")
        if row["band"] == "LOW"
    }
    codes = {
        (int(row["mismatch_seed"]), int(row["frame_index"])): row
        for row in read_csv(REFERENCE_DIR / "dynamic_codes.csv")
        if row["band"] == "LOW"
    }
    return master, codes


def main() -> int:
    matrix = read_csv(MANIFEST_DIR / "job_matrix.csv")
    formal_ids = {row["job_id"] for row in matrix}
    reference_master, reference_codes = reference_indexes()

    summaries: list[dict[str, object]] = []
    all_codes: list[dict[str, object]] = []
    retained_codes: list[dict[str, object]] = []
    all_paths: list[dict[str, object]] = []
    startup_pairs: list[dict[str, object]] = []
    transition_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for matrix_row in sorted(matrix, key=lambda row: int(row["mismatch_seed"])):
        job_id = matrix_row["job_id"]
        result_path = JOB_RESULT_DIR / f"{job_id}.json"
        code_path = JOB_CODE_DIR / f"{job_id}.csv"
        path_path = JOB_PATH_DIR / f"{job_id}.csv"
        missing = [
            path.relative_to(ROOT).as_posix()
            for path in (result_path, code_path, path_path)
            if not path.is_file()
        ]
        if missing:
            failures.append(
                {"job_id": job_id, "gate": "MISSING_JOB_ARTIFACT", "paths": missing}
            )
            continue

        summary = load_json(result_path)
        codes = read_csv(code_path)
        paths = read_csv(path_path)
        log_path = ROOT / str(summary.get("log", ""))
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_path.is_file()
            else ""
        )
        seed = int(summary["mismatch_seed"])
        frames = {int(row["frame_index"]): row for row in codes}
        if set(frames) != set(range(68)):
            failures.append(
                {
                    "job_id": job_id,
                    "gate": "FRAME_INDEX_SET",
                    "observed_count": len(frames),
                }
            )
            continue
        retained = [frames[index] for index in range(4, 68)]
        if len(retained) != 64 or not all(truth(row["retained"]) for row in retained):
            failures.append(
                {"job_id": job_id, "gate": "RETAINED_FRAME_CONTRACT"}
            )
            continue

        historical = reference_master.get(seed, {})
        differing_frames: list[int] = []
        for frame in range(64):
            old = reference_codes.get((seed, frame))
            if old is None or int(old["code"]) != int(frames[frame]["code"]):
                differing_frames.append(frame)
        historical_codes = [
            int(reference_codes[(seed, frame)]["code"]) for frame in range(64)
        ]
        w0_codes = [int(frames[frame]["code"]) for frame in range(64)]
        retained_values = [int(row["code"]) for row in retained]
        master_row: dict[str, object] = {
            **summary,
            "historical_w0_snr_db": historical.get("snr_db", ""),
            "historical_w0_sndr_db": historical.get("sndr_db", ""),
            "historical_w0_enob_raw": historical.get("enob_raw", ""),
            "historical_w0_sfdr_dbc": historical.get("sfdr_dbc", ""),
            "historical_w0_hard_dynamic_pass": historical.get(
                "hard_dynamic_pass", ""
            ),
            "historical_w0_code_checksum": code_checksum(historical_codes),
            "same_run_w0_code_checksum": code_checksum(w0_codes),
            "historical_w0_code_exact": len(differing_frames) == 0,
            "historical_w0_different_frame_count": len(differing_frames),
            "historical_w0_different_frames": "/".join(
                str(value) for value in differing_frames
            ),
            "delta_w4_minus_historical_w0_snr_db": (
                float(summary["steady_state_snr_db"])
                - float(historical["snr_db"])
            ),
            "delta_w4_minus_historical_w0_sndr_db": (
                float(summary["steady_state_sndr_db"])
                - float(historical["sndr_db"])
            ),
            "delta_w4_minus_historical_w0_enob_raw": (
                float(summary["steady_state_enob_raw"])
                - float(historical["enob_raw"])
            ),
            "delta_w4_minus_historical_w0_sfdr_dbc": (
                float(summary["steady_state_sfdr_dbc"])
                - float(historical["sfdr_dbc"])
            ),
            "retained_code_checksum_recomputed": code_checksum(retained_values),
            "retained_code_checksum_match": (
                code_checksum(retained_values)
                == summary["codes_retained_checksum"]
            ),
            "mismatch_checksum_matches_historical": (
                summary["mismatch_checksum"]
                == historical.get("mismatch_checksum_sha256")
            ),
            "noise_prefix_checksum_matches_historical": (
                summary["noise_prefix_checksum_0_63"]
                == historical.get("noise_draw_checksum_sha256")
            ),
            "ngspice_compatibility_hsa": (
                "Compatibility modes selected: hs a" in log_text
                and "No compatibility mode selected" not in log_text
            ),
        }
        summaries.append(master_row)
        all_codes.extend(codes)
        retained_codes.extend(retained)
        all_paths.extend(paths)
        for early in range(4):
            late = early + 64
            startup_pairs.append(
                {
                    "job_id": job_id,
                    "mismatch_seed": seed,
                    "noise_mode": "ON",
                    "band": "LOW",
                    "early_frame": early,
                    "same_phase_frame": late,
                    "early_code": frames[early]["code"],
                    "same_phase_code": frames[late]["code"],
                    "code_equal": frames[early]["code"] == frames[late]["code"],
                    "classification": "NOISE_ON_DIAGNOSTIC_ONLY",
                    "used_as_first_conversion_gate": False,
                }
            )
        transition_rows.append(
            {
                "mismatch_seed": seed,
                "band": "LOW",
                "historical_method_id": "FAST64_STARTUP_INCLUSIVE_W0",
                "new_method_id": "FAST64_SS_W4",
                "historical_w0_snr_db": historical["snr_db"],
                "historical_w0_sndr_db": historical["sndr_db"],
                "historical_w0_enob_raw": historical["enob_raw"],
                "new_w4_snr_db": summary["steady_state_snr_db"],
                "new_w4_sndr_db": summary["steady_state_sndr_db"],
                "new_w4_enob_raw": summary["steady_state_enob_raw"],
                "delta_sndr_db": (
                    float(summary["steady_state_sndr_db"])
                    - float(historical["sndr_db"])
                ),
                "historical_w0_code_exact": len(differing_frames) == 0,
                "historical_w0_different_frame_count": len(differing_frames),
                "historical_w0_different_frames": "/".join(
                    str(value) for value in differing_frames
                ),
                "historical_hard_dynamic_pass": historical[
                    "hard_dynamic_pass"
                ],
                "new_w4_hard_dynamic_pass": summary[
                    "steady_state_hard_dynamic_pass"
                ],
            }
        )

    summaries.sort(key=lambda row: int(row["mismatch_seed"]))
    all_codes.sort(
        key=lambda row: (int(row["mismatch_seed"]), int(row["frame_index"]))
    )
    retained_codes.sort(
        key=lambda row: (int(row["mismatch_seed"]), int(row["frame_index"]))
    )
    all_paths.sort(
        key=lambda row: (int(row["job_id"].split("_S")[1][:3]), int(row["frame_index"]))
    )
    startup_pairs.sort(
        key=lambda row: (int(row["mismatch_seed"]), int(row["early_frame"]))
    )
    transition_rows.sort(key=lambda row: int(row["mismatch_seed"]))

    percentiles = percentile_rows(
        summaries,
        (
            "steady_state_snr_db",
            "steady_state_sndr_db",
            "steady_state_enob_raw",
            "steady_state_sfdr_dbc",
        ),
    )
    representatives = representative_rows(summaries, percentiles)

    write_csv_atomic(CSV_DIR / "steady_state_master_mc200_low_w4.csv", summaries)
    write_csv_atomic(CSV_DIR / "codes_all_13600.csv", all_codes)
    write_csv_atomic(CSV_DIR / "codes_fft_retained_12800.csv", retained_codes)
    write_csv_atomic(CSV_DIR / "first_conversion_path_1600.csv", all_paths)
    write_csv_atomic(CSV_DIR / "startup_periodic_pairs_800.csv", startup_pairs)
    write_csv_atomic(
        CSV_DIR / "w0_to_w4_method_transition_mc200_low.csv",
        transition_rows,
    )
    write_csv_atomic(CSV_DIR / "population_percentiles_w4.csv", percentiles)
    write_csv_atomic(CSV_DIR / "representative_records_w4.csv", representatives)

    required_seed_set = set(range(1, 201))
    observed_seed_set = {int(row["mismatch_seed"]) for row in summaries}
    execution_checks = {
        "job_matrix_200": len(matrix) == 200,
        "job_matrix_ids_unique": len(formal_ids) == 200,
        "master_200": len(summaries) == 200,
        "seed_set_1_to_200": observed_seed_set == required_seed_set,
        "codes_all_13600": len(all_codes) == 13_600,
        "codes_retained_12800": len(retained_codes) == 12_800,
        "startup_pairs_800": len(startup_pairs) == 800,
        "first_conversion_path_1600": len(all_paths) == 1_600,
        "all_returncode_zero": all(int(row["returncode"]) == 0 for row in summaries),
        "all_protocol_clean": all(truth(row["protocol_clean"]) for row in summaries),
        "all_parseval_pass": all(
            truth(row["steady_state_parseval_pass"]) for row in summaries
        ),
        "all_ngspice_compatibility_hsa": all(
            truth(row["ngspice_compatibility_hsa"]) for row in summaries
        ),
        "all_matrix_numerics_frozen": all(
            int(row["maxstep_ps"]) == 50
            and row["solver_profile"] == "ROBUST_GEAR"
            for row in matrix
        ),
        "all_retained_checksums_match": all(
            truth(row["retained_code_checksum_match"]) for row in summaries
        ),
        "all_mismatch_checksums_match_historical": all(
            truth(row["mismatch_checksum_matches_historical"]) for row in summaries
        ),
        "all_noise_prefix_checksums_match_historical": all(
            truth(row["noise_prefix_checksum_matches_historical"])
            for row in summaries
        ),
        "no_analysis_failures": not failures,
    }
    execution_pass = all(execution_checks.values())
    write_json_atomic(
        RESULT_DIR / "execution_audit_mc200_low_w4.json",
        {
            "status": (
                "PASS_MC200_LOW_W4_EXECUTION"
                if execution_pass
                else "FAIL_MC200_LOW_W4_EXECUTION"
            ),
            "pass": execution_pass,
            "checks": execution_checks,
            "failures": failures,
        },
    )

    first_pass_seeds = [
        int(row["mismatch_seed"])
        for row in summaries
        if truth(row["first_conversion_protocol_pass"])
    ]
    hard_pass_seeds = [
        int(row["mismatch_seed"])
        for row in summaries
        if truth(row["steady_state_hard_dynamic_pass"])
    ]
    budget_pass_seeds = [
        int(row["mismatch_seed"])
        for row in summaries
        if truth(row["steady_state_snr_budget_pass"])
    ]
    combined_pass_seeds = [
        int(row["mismatch_seed"])
        for row in summaries
        if truth(row["first_conversion_protocol_pass"])
        and truth(row["steady_state_hard_dynamic_pass"])
    ]
    write_json_atomic(
        RESULT_DIR / "population_summary_mc200_low_w4.json",
        {
            "status": (
                "COMPLETE_POPULATION_SUMMARY"
                if execution_pass
                else "INCOMPLETE_POPULATION_SUMMARY"
            ),
            "method_id": "FAST64_SS_W4",
            "population_count": len(summaries),
            "first_conversion_protocol_pass_count": len(first_pass_seeds),
            "first_conversion_protocol_fail_count": 200 - len(first_pass_seeds),
            "first_conversion_failure_seeds": sorted(
                required_seed_set - set(first_pass_seeds)
            ),
            "steady_state_hard_dynamic_pass_count": len(hard_pass_seeds),
            "steady_state_hard_dynamic_fail_count": 200 - len(hard_pass_seeds),
            "steady_state_hard_dynamic_failure_seeds": sorted(
                required_seed_set - set(hard_pass_seeds)
            ),
            "steady_state_snr_budget_pass_count": len(budget_pass_seeds),
            "steady_state_snr_budget_fail_count": 200 - len(budget_pass_seeds),
            "steady_state_snr_budget_failure_seeds": sorted(
                required_seed_set - set(budget_pass_seeds)
            ),
            "combined_system_pass_count": len(combined_pass_seeds),
            "combined_system_fail_count": 200 - len(combined_pass_seeds),
            "combined_system_failure_seeds": sorted(
                required_seed_set - set(combined_pass_seeds)
            ),
            "historical_w0_exact_record_count": sum(
                truth(row["historical_w0_code_exact"]) for row in summaries
            ),
            "historical_w0_different_record_count": sum(
                not truth(row["historical_w0_code_exact"]) for row in summaries
            ),
            "historical_w0_different_frame_count": sum(
                int(row["historical_w0_different_frame_count"])
                for row in summaries
            ),
            "percentile_method": "LINEAR_TYPE7",
            "non_claims": [
                "LOW-only results are not a two-band die-level MC200 yield.",
                "W4 and W0 distributions use different measurement methods.",
                "No production, layout, PEX, silicon, or tapeout signoff claim is made.",
                "Noise-on frame0/frame64 code equality is diagnostic only.",
            ],
        },
    )
    print(
        json.dumps(
            {
                "execution_pass": execution_pass,
                "master_records": len(summaries),
                "codes_all": len(all_codes),
                "codes_retained": len(retained_codes),
                "analysis_failures": len(failures),
            },
            sort_keys=True,
        )
    )
    return 0 if execution_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
