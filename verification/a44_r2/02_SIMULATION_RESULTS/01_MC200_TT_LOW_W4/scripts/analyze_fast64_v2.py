#!/usr/bin/env python3
"""Aggregate FAST64 V2 jobs and enforce method, numerical, and result gates."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from fast64_v2_common import (
    BRIDGE_CASES,
    CSV_DIR,
    ENOB_HARD_MIN_BIT,
    MAIN_SEEDS,
    MANIFEST_DIR,
    METHOD_ID,
    NFFT,
    RESULT_DIR,
    ROOT,
    SNDR_HARD_MIN_DB,
    STEADY_METHOD_ID,
    code_checksum,
    phase_aligned_rows,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


JOB_RESULT_DIR = RESULT_DIR / "jobs"
JOB_CODE_DIR = CSV_DIR / "job_codes"
JOB_PATH_DIR = CSV_DIR / "job_paths"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def integer(value: object, default: int | None = None) -> int | None:
    text = str(value).strip()
    return default if text == "" else int(text)


def number(value: object, default: float = math.nan) -> float:
    text = str(value).strip()
    return default if text == "" else float(text)


def load_job_summaries() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not JOB_RESULT_DIR.is_dir():
        return rows
    for path in sorted(JOB_RESULT_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_result_path"] = path.relative_to(ROOT).as_posix()
        rows.append(payload)
    return rows


def load_job_codes(job_id: str) -> list[dict[str, str]]:
    return read_csv(JOB_CODE_DIR / f"{job_id}.csv")


def load_job_paths(job_id: str) -> list[dict[str, str]]:
    return read_csv(JOB_PATH_DIR / f"{job_id}.csv")


def phase_key(row: Mapping[str, object]) -> tuple[int, str]:
    seed = integer(row.get("mismatch_seed"), 0)
    return int(seed or 0), str(row["band"])


def analyze_warmup(
    summaries: list[dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    qualifying = [
        row
        for row in summaries
        if row.get("phase") == "P2_WARMUP_QUALIFICATION"
    ]
    grouped: dict[tuple[int, str], dict[int, dict[str, object]]] = defaultdict(dict)
    for row in qualifying:
        grouped[phase_key(row)][int(row["warmup_frames"])] = row
    comparison_rows: list[dict[str, object]] = []
    for key, variants in sorted(grouped.items()):
        seed, band = key
        w4 = variants.get(4)
        w8 = variants.get(8)
        if w4 is None or w8 is None:
            comparison_rows.append(
                {
                    "mismatch_seed": "" if seed == 0 else seed,
                    "band": band,
                    "pair_complete": False,
                    "canonical_code_match_count": 0,
                    "completion_flag_match_count": 0,
                    "missing_or_duplicate_or_invalid": 1,
                    "pass": False,
                    "status": "WARMUP4_NOT_QUALIFIED",
                }
            )
            continue
        w4_codes = phase_aligned_rows(
            row for row in load_job_codes(str(w4["job_id"])) if truth(row["retained"])
        )
        w8_codes = phase_aligned_rows(
            row for row in load_job_codes(str(w8["job_id"])) if truth(row["retained"])
        )
        code_matches = sum(
            int(left["code"]) == int(right["code"])
            and int(left["phase_index"]) == int(right["phase_index"])
            for left, right in zip(w4_codes, w8_codes)
        )
        completion_matches = sum(
            truth(left["valid"]) == truth(right["valid"])
            for left, right in zip(w4_codes, w8_codes)
        )
        clean = all(
            (
                len(w4_codes) == 64,
                len(w8_codes) == 64,
                truth(w4.get("protocol_clean")),
                truth(w8.get("protocol_clean")),
                number(w4.get("steady_state_clipping_count")) == 0,
                number(w8.get("steady_state_clipping_count")) == 0,
            )
        )
        passed = clean and code_matches == 64 and completion_matches == 64
        comparison_rows.append(
            {
                "mismatch_seed": "" if seed == 0 else seed,
                "band": band,
                "w4_job_id": w4["job_id"],
                "w8_job_id": w8["job_id"],
                "pair_complete": True,
                "w4_retained_count": len(w4_codes),
                "w8_retained_count": len(w8_codes),
                "canonical_code_match_count": code_matches,
                "completion_flag_match_count": completion_matches,
                "missing_or_duplicate_or_invalid": 0 if clean else 1,
                "w4_code_checksum_phase_aligned": code_checksum(
                    [int(row["code"]) for row in w4_codes]
                )
                if len(w4_codes) == 64
                else "",
                "w8_code_checksum_phase_aligned": code_checksum(
                    [int(row["code"]) for row in w8_codes]
                )
                if len(w8_codes) == 64
                else "",
                "pass": passed,
                "status": "WARMUP4_QUALIFIED"
                if passed
                else "WARMUP4_NOT_QUALIFIED",
            }
        )
    expected_pairs = 6
    passed = (
        len(comparison_rows) == expected_pairs
        and all(bool(row["pass"]) for row in comparison_rows)
    )
    payload = {
        "status": "WARMUP4_QUALIFIED" if passed else "WARMUP4_NOT_QUALIFIED",
        "pass": passed,
        "method_id": METHOD_ID,
        "comparison_pairs": len(comparison_rows),
        "required_pairs": expected_pairs,
        "all_64_codes_exact": passed,
        "promoted_candidate_status": "NOT_APPLICABLE_NO_DISTINCT_PROMOTED_CANDIDATE",
        "completed_utc": utc_now(),
    }
    return payload, comparison_rows


def selected_path_code(
    row: Mapping[str, object], layer: str, driver_code: int
) -> tuple[object, str]:
    if layer == "comparator":
        direct = integer(row["comparator_direct_code"])
        inverse = integer(row["comparator_inverse_code"])
    elif layer == "dctrl":
        lsb = driver_code & 1
        direct7 = integer(row["dctrl_direct_code_7_to_1"])
        inverse7 = integer(row["dctrl_inverse_code_7_to_1"])
        direct = (int(direct7 or 0) | lsb) if direct7 is not None else None
        inverse = (int(inverse7 or 0) | lsb) if inverse7 is not None else None
    else:
        raise ValueError(layer)
    direct_match = direct == driver_code
    inverse_match = inverse == driver_code
    if direct_match and not inverse_match:
        return direct, "DIRECT"
    if inverse_match and not direct_match:
        return inverse, "INVERSE"
    if direct_match and inverse_match:
        return direct, "AMBIGUOUS_BOTH_MATCH"
    return "", "NO_MATCH"


def enrich_path_rows(
    summaries: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    output: list[dict[str, object]] = []
    by_job: dict[str, dict[str, object]] = {}
    for summary in summaries:
        job_id = str(summary["job_id"])
        rows = load_job_paths(job_id)
        enriched: list[dict[str, object]] = []
        for row in rows:
            driver = int(row["driver_dout_code_480"])
            comparator, comparator_mapping = selected_path_code(
                row, "comparator", driver
            )
            dctrl, dctrl_mapping = selected_path_code(row, "dctrl", driver)
            analog = int(row["analog_dout_code_480"])
            path_pass = all(
                (
                    int(row.get("comparator_valid_decision_count", 0)) == 8,
                    int(row.get("dctrl_valid_update_count", 0)) == 7,
                    comparator == driver,
                    dctrl == driver,
                    truth(row["driver_analog_match_480"]),
                    truth(row["dout_stable_470_to_480"]),
                )
            )
            item: dict[str, object] = {
                **row,
                "phase": summary.get("phase", ""),
                "role": summary.get("role", ""),
                "mismatch_seed": summary.get("mismatch_seed", ""),
                "noise_mode": summary.get("noise_mode", ""),
                "noise_seed": summary.get("noise_seed", ""),
                "band": summary.get("band", ""),
                "comparator_selected_code": comparator,
                "comparator_mapping": comparator_mapping,
                "dctrl_selected_code": dctrl,
                "dctrl_mapping": dctrl_mapping,
                "behavioral_digital_dout_code": driver,
                "behavioral_digital_observation": (
                    "INFERRED_FROM_DAC_BRIDGE_OUTPUT; "
                    "ngspice analog measurement cannot independently observe the d_cosim digital node"
                ),
                "driver_dout_code": driver,
                "analog_dout_code": analog,
                "path_pass": path_pass,
            }
            enriched.append(item)
            output.append(item)
        frame_rows = {int(row["frame_index"]): row for row in enriched}
        frame0 = frame_rows.get(0)
        frame64 = frame_rows.get(64)
        path_pass = bool(frame0 and frame0["path_pass"])
        deterministic_path_match: object = ""
        if str(summary.get("noise_mode")) == "OFF":
            deterministic_path_match = bool(
                frame0
                and frame64
                and frame0["comparator_selected_code"]
                == frame64["comparator_selected_code"]
                and frame0["dctrl_selected_code"] == frame64["dctrl_selected_code"]
                and frame0["driver_dout_code"] == frame64["driver_dout_code"]
                and frame0["analog_dout_code"] == frame64["analog_dout_code"]
            )
        by_job[job_id] = {
            "path_pass": path_pass,
            "deterministic_path_match": deterministic_path_match,
            "path_row_count": len(enriched),
            "expected_path_row_count": 2 * int(summary.get("warmup_frames", 0)),
            "path_complete": len(enriched)
            == 2 * int(summary.get("warmup_frames", 0)),
        }
    return output, by_job


def analyze_numerical(
    summaries: list[dict[str, object]],
    path_status: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    candidates = [
        row
        for row in summaries
        if row.get("role") == "QUALIFICATION"
        and int(row.get("warmup_frames", -1)) == 4
    ]
    grouped: dict[tuple[int, str], dict[int, dict[str, object]]] = defaultdict(dict)
    for row in candidates:
        grouped[phase_key(row)][round(number(row["maxstep_ns"]) * 1000)] = row
    rows: list[dict[str, object]] = []
    for (seed, band), variants in sorted(grouped.items()):
        strict = variants.get(50)
        bulk = variants.get(100)
        if strict is None or bulk is None:
            rows.append(
                {
                    "mismatch_seed": "" if seed == 0 else seed,
                    "band": band,
                    "pair_complete": False,
                    "n1_f0_status": "N1_F0_INCOMPLETE",
                    "n1_ss_status": "N1_SS_INCOMPLETE",
                    "pass": False,
                }
            )
            continue
        strict_codes = load_job_codes(str(strict["job_id"]))
        bulk_codes = load_job_codes(str(bulk["job_id"]))
        strict_by_frame = {int(row["frame_index"]): row for row in strict_codes}
        bulk_by_frame = {int(row["frame_index"]): row for row in bulk_codes}
        strict_retained = phase_aligned_rows(
            row for row in strict_codes if truth(row["retained"])
        )
        bulk_retained = phase_aligned_rows(
            row for row in bulk_codes if truth(row["retained"])
        )
        ss_matches = sum(
            int(left["code"]) == int(right["code"])
            and truth(left["valid"]) == truth(right["valid"])
            for left, right in zip(strict_retained, bulk_retained)
        )
        strict_path = path_status.get(str(strict["job_id"]), {})
        bulk_path = path_status.get(str(bulk["job_id"]), {})
        f0_pass = all(
            (
                0 in strict_by_frame,
                0 in bulk_by_frame,
                int(strict_by_frame.get(0, {}).get("code", -1))
                == int(bulk_by_frame.get(0, {}).get("code", -2)),
                truth(strict_by_frame.get(0, {}).get("valid", False))
                == truth(bulk_by_frame.get(0, {}).get("valid", False)),
                bool(strict_path.get("path_pass")),
                bool(bulk_path.get("path_pass")),
            )
        )
        ss_pass = all(
            (
                len(strict_retained) == 64,
                len(bulk_retained) == 64,
                ss_matches == 64,
                truth(strict.get("protocol_clean")),
                truth(bulk.get("protocol_clean")),
            )
        )
        rows.append(
            {
                "mismatch_seed": "" if seed == 0 else seed,
                "band": band,
                "strict_job_id": strict["job_id"],
                "bulk_job_id": bulk["job_id"],
                "pair_complete": True,
                "frame0_strict_code": strict_by_frame.get(0, {}).get("code", ""),
                "frame0_bulk_code": bulk_by_frame.get(0, {}).get("code", ""),
                "n1_f0_path_strict_pass": strict_path.get("path_pass", False),
                "n1_f0_path_bulk_pass": bulk_path.get("path_pass", False),
                "n1_f0_status": "N1_F0_PASS" if f0_pass else "N1_F0_FAIL",
                "steady_state_code_match_count": ss_matches,
                "steady_state_sndr_delta_db": number(
                    bulk.get("steady_state_sndr_db")
                )
                - number(strict.get("steady_state_sndr_db")),
                "n1_ss_status": "N1_SS_PASS" if ss_pass else "N1_SS_FAIL",
                "pass": f0_pass and ss_pass,
            }
        )
    expected = 6
    passed = len(rows) == expected and all(bool(row["pass"]) for row in rows)
    payload = {
        "status": "PASS_NUMERICAL_SPLIT_QUALIFICATION"
        if passed
        else "FAIL_NUMERICAL_SPLIT_QUALIFICATION",
        "pass": passed,
        "comparison_pairs": len(rows),
        "required_pairs": expected,
        "n1_f0_pass_count": sum(row.get("n1_f0_status") == "N1_F0_PASS" for row in rows),
        "n1_ss_pass_count": sum(row.get("n1_ss_status") == "N1_SS_PASS" for row in rows),
        "formal_maxstep_ps": 50,
        "bulk_maxstep_ps": 100,
        "bulk_use_boundary": "QUALIFICATION_EVIDENCE_ONLY; FORMAL_MC10_REMAINS_50_PS",
        "completed_utc": utc_now(),
    }
    return payload, rows


def startup_pairs(
    summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for summary in summaries:
        codes = {
            int(row["frame_index"]): row
            for row in load_job_codes(str(summary["job_id"]))
        }
        warmup = int(summary.get("warmup_frames", 0))
        for cold_index in range(warmup):
            warm_index = cold_index + 64
            cold = codes.get(cold_index)
            warm = codes.get(warm_index)
            rows.append(
                {
                    "job_id": summary["job_id"],
                    "phase": summary.get("phase", ""),
                    "role": summary.get("role", ""),
                    "mismatch_seed": summary.get("mismatch_seed", ""),
                    "noise_mode": summary.get("noise_mode", ""),
                    "noise_seed": summary.get("noise_seed", ""),
                    "band": summary.get("band", ""),
                    "warmup_frames": warmup,
                    "cold_frame": cold_index,
                    "warm_same_phase_frame": warm_index,
                    "cold_code": cold["code"] if cold else "",
                    "warm_code": warm["code"] if warm else "",
                    "code_match": bool(
                        cold and warm and int(cold["code"]) == int(warm["code"])
                    ),
                    "cold_valid": cold["valid"] if cold else False,
                    "warm_valid": warm["valid"] if warm else False,
                }
            )
    return rows


def final_first_conversion_rows(
    summaries: list[dict[str, object]],
    path_status: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for summary in summaries:
        job_id = str(summary["job_id"])
        path = path_status.get(job_id, {})
        noise_off = str(summary.get("noise_mode")) == "OFF"
        deterministic = (
            bool(path.get("deterministic_path_match"))
            and truth(summary.get("first_conversion_deterministic_pair_pass"))
            if noise_off
            else True
        )
        passed = all(
            (
                truth(summary.get("first_conversion_protocol_pass")),
                bool(path.get("path_pass")),
                bool(path.get("path_complete")),
                deterministic,
            )
        )
        if passed:
            status = (
                "PASS_FIRST_CONVERSION_DETERMINISTIC"
                if noise_off
                else "PASS_FIRST_CONVERSION_PROTOCOL_PATH_NOISE_ON"
            )
        elif not truth(summary.get("first_conversion_protocol_pass")):
            status = "FAIL_FIRST_CONVERSION_PROTOCOL_OR_TIMING"
        elif not bool(path.get("path_pass")):
            status = "SAR_CAPTURE_OR_DOUT_COMMIT_DIVERGENCE"
        else:
            status = "FIRST_CONVERSION_HISTORY_DIVERGENCE"
        output.append(
            {
                "job_id": job_id,
                "phase": summary.get("phase", ""),
                "role": summary.get("role", ""),
                "mismatch_seed": summary.get("mismatch_seed", ""),
                "noise_mode": summary.get("noise_mode", ""),
                "noise_seed": summary.get("noise_seed", ""),
                "band": summary.get("band", ""),
                "frame0_code": summary.get("first_conversion_code", ""),
                "frame64_code": summary.get("same_phase_reference_code", ""),
                "protocol_timing_pass": summary.get(
                    "first_conversion_protocol_pass", False
                ),
                "path_pass": path.get("path_pass", False),
                "path_complete": path.get("path_complete", False),
                "deterministic_pair_required": noise_off,
                "deterministic_pair_pass": deterministic if noise_off else "",
                "first_conversion_pass": passed,
                "first_conversion_status": status,
            }
        )
    return output


def reference_index(path: Path) -> dict[tuple[int, str], dict[str, str]]:
    return {
        (int(row["mismatch_seed"]), row["band"]): row for row in read_csv(path)
    }


def method_transition_rows(
    summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    current = reference_index(ROOT / "references/current_mc200_target_master.csv")
    old_mc10 = reference_index(
        ROOT / "references/later_mc10_v10_original/csv__dynamic_master.csv"
    )
    rows: list[dict[str, object]] = []
    for summary in summaries:
        if summary.get("role") != "MAIN_MC10" or summary.get("noise_mode") != "ON":
            continue
        key = (int(summary["mismatch_seed"]), str(summary["band"]))
        current_row = current.get(key, {})
        old_mc10_row = old_mc10.get(key, {})
        rows.append(
            {
                "mismatch_seed": key[0],
                "band": key[1],
                "historical_method_id": "FAST64_STARTUP_INCLUSIVE_W0",
                "new_method_id": STEADY_METHOD_ID,
                "historical_current_mc200_sndr_db": current_row.get("sndr_db", ""),
                "historical_mc10_w0_sndr_db": old_mc10_row.get("sndr_db", ""),
                "same_run_w0_replay_sndr_db": summary["w0_replay_sndr_db"],
                "new_steady_state_w4_sndr_db": summary["steady_state_sndr_db"],
                "delta_w4_minus_same_run_w0_sndr_db": summary["delta_sndr_db"],
                "same_run_w0_matches_current_mc200_codes": (
                    summary["w0_replay_codes_checksum"]
                    == current_row.get("compact_code_checksum_sha256")
                ),
                "same_run_w0_matches_historical_mc10_codes": (
                    summary["w0_replay_codes_checksum"]
                    == old_mc10_row.get("compact_code_checksum_sha256")
                ),
                "comparison_status": "METHOD_TRANSITION_DIAGNOSTIC_COMPARISON",
                "strict_reproduction_claim_allowed": False,
            }
        )
    return rows


def bridge_comparison_rows(
    summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_job_key = {
        (int(row["mismatch_seed"]), str(row["band"]), str(row["noise_mode"])): row
        for row in summaries
        if str(row.get("role", "")).startswith("BRIDGE_")
    }
    v7 = reference_index(ROOT / "references/baseline_mc200/dynamic_master.csv")
    current = reference_index(ROOT / "references/current_mc200_target_master.csv")
    old_mc10 = reference_index(
        ROOT / "references/later_mc10_v10_original/csv__dynamic_master.csv"
    )
    fixed41 = reference_index(
        ROOT / "references/fixed50_41_compact/data/fixed50_target_master.csv"
    )
    rows: list[dict[str, object]] = []
    for role, seed, band in BRIDGE_CASES:
        on = by_job_key.get((seed, band, "ON"), {})
        off = by_job_key.get((seed, band, "OFF"), {})
        key = (seed, band)
        rows.append(
            {
                "bridge_role": role,
                "mismatch_seed": seed,
                "band": band,
                "historical_v7_mc200_w0_sndr_db": v7.get(key, {}).get("sndr_db", ""),
                "historical_current_mc200_w0_sndr_db": current.get(key, {}).get(
                    "sndr_db", ""
                ),
                "historical_mc10_w0_sndr_db": old_mc10.get(key, {}).get("sndr_db", ""),
                "fixed50_41_w0_sndr_db": fixed41.get(key, {}).get("sndr_db", ""),
                "same_run_w0_replay_sndr_db": on.get("w0_replay_sndr_db", ""),
                "new_ss_w4_sndr_db": on.get("steady_state_sndr_db", ""),
                "noise_off_ss_w4_sndr_db": off.get("steady_state_sndr_db", ""),
                "event_noise_job_id": on.get("job_id", ""),
                "noise_off_job_id": off.get("job_id", ""),
                "included_in_main_mc10_population": False,
                "comparison_status": "METHOD_TRANSITION_DIAGNOSTIC_COMPARISON",
            }
        )
    return rows


def aggregate_code_views(
    summaries: list[dict[str, object]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    all_68: list[dict[str, str]] = []
    retained: list[dict[str, str]] = []
    for summary in summaries:
        codes = load_job_codes(str(summary["job_id"]))
        if int(summary.get("total_frames", 0)) == 68:
            all_68.extend(codes)
        retained.extend(row for row in codes if truth(row.get("retained")))
    return all_68, retained


def main_master_rows(
    summaries: list[dict[str, object]],
    first_rows: list[dict[str, object]],
    numerical: Mapping[str, object],
) -> list[dict[str, object]]:
    first_by_job = {str(row["job_id"]): row for row in first_rows}
    output: list[dict[str, object]] = []
    for summary in summaries:
        if summary.get("role") != "MAIN_MC10" or summary.get("noise_mode") != "ON":
            continue
        first = first_by_job.get(str(summary["job_id"]), {})
        first_pass = bool(first.get("first_conversion_pass"))
        steady_pass = truth(summary.get("steady_state_hard_dynamic_pass"))
        protocol_pass = truth(summary.get("protocol_clean"))
        if not protocol_pass:
            overall = "FAIL_PROTOCOL_OR_COMPLETION"
        elif not first_pass:
            overall = "FAIL_FIRST_CONVERSION_ONLY"
        elif not steady_pass:
            overall = "FAIL_STEADY_STATE_DYNAMIC"
        else:
            overall = "PASS_FAST64_COMPLETE"
        output.append(
            {
                **{
                    key: value
                    for key, value in summary.items()
                    if not str(key).startswith("_")
                },
                "first_conversion_status": first.get(
                    "first_conversion_status", "INCOMPLETE"
                ),
                "first_conversion_pass": first_pass,
                "warmup_qualified": "",
                "n1_f0_status": "N1_F0_PASS"
                if int(numerical.get("n1_f0_pass_count", 0)) == 6
                else "N1_F0_FAIL_OR_INCOMPLETE",
                "n1_ss_status": "N1_SS_PASS"
                if int(numerical.get("n1_ss_pass_count", 0)) == 6
                else "N1_SS_FAIL_OR_INCOMPLETE",
                "overall_status": overall,
            }
        )
    output.sort(key=lambda row: (int(row["mismatch_seed"]), str(row["band"])))
    return output


def execution_status(
    summaries: list[dict[str, object]],
    main_master: list[dict[str, object]],
    warmup: Mapping[str, object],
    numerical: Mapping[str, object],
) -> dict[str, object]:
    matrix = read_csv(MANIFEST_DIR / "job_matrix.csv")
    formal_summaries = [
        row for row in summaries if row.get("phase") != "P1_SMOKE"
    ]
    state_counts = Counter(row.get("state", "") for row in matrix)
    required = len(matrix) == 68
    terminal = all(
        row.get("state")
        in {"COMPLETE", "COMPLETE_WITH_FAIL", "SIM_ERROR_UNRESOLVED", "MEASUREMENT_BLOCKED"}
        for row in matrix
    )
    execution_clean = (
        required
        and terminal
        and state_counts.get("SIM_ERROR_UNRESOLVED", 0) == 0
        and state_counts.get("MEASUREMENT_BLOCKED", 0) == 0
        and len(formal_summaries) == 68
        and len(main_master) == 20
    )
    resource = read_csv(CSV_DIR / "resource_trace.csv")
    max_processes = max(
        (int(row["ngspice_process_count"]) for row in resource), default=0
    )
    max_threads = max(
        (int(row["ngspice_thread_count"]) for row in resource), default=0
    )
    resource_pass = max_processes <= 4 and max_threads <= 16
    return {
        "status": "PASS_MC10_FAST64_V2_EXECUTION"
        if execution_clean and resource_pass
        else "MC10_FAST64_V2_EXECUTION_INCOMPLETE",
        "pass": execution_clean and resource_pass,
        "formal_job_count": len(matrix),
        "job_summary_count": len(formal_summaries),
        "smoke_summary_count": len(summaries) - len(formal_summaries),
        "state_counts": dict(state_counts),
        "main_event_noise_records": len(main_master),
        "main_event_noise_code_rows": sum(
            len(load_job_codes(str(row["job_id"]))) for row in main_master
        ),
        "main_event_noise_retained_rows": 64 * len(main_master),
        "warmup_qualification_pass": bool(warmup.get("pass")),
        "numerical_qualification_pass": bool(numerical.get("pass")),
        "max_ngspice_processes_observed": max_processes,
        "max_ngspice_threads_observed": max_threads,
        "resource_contract_pass": resource_pass,
        "completed_utc": utc_now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("all", "qualification", "final"),
        default="all",
    )
    args = parser.parse_args()
    summaries = load_job_summaries()
    warmup_payload, warmup_rows = analyze_warmup(summaries)
    all_path_rows, path_status = enrich_path_rows(summaries)
    numerical_payload, numerical_rows = analyze_numerical(summaries, path_status)
    pair_rows = startup_pairs(summaries)
    first_rows = final_first_conversion_rows(summaries, path_status)

    write_csv_atomic(CSV_DIR / "warmup_canonical_comparison.csv", warmup_rows)
    write_json_atomic(RESULT_DIR / "warmup_qualification.json", warmup_payload)
    write_csv_atomic(CSV_DIR / "numerical_split_comparison.csv", numerical_rows)
    write_json_atomic(RESULT_DIR / "numerical_split_audit.json", numerical_payload)
    write_csv_atomic(CSV_DIR / "startup_periodic_pairs.csv", pair_rows)
    write_csv_atomic(CSV_DIR / "first_conversion_path.csv", all_path_rows)
    write_json_atomic(
        RESULT_DIR / "first_conversion_status.json",
        {
            "status": "PASS_FIRST_CONVERSION_ALL_AVAILABLE"
            if first_rows
            and all(bool(row["first_conversion_pass"]) for row in first_rows)
            else "FAIL_OR_INCOMPLETE_FIRST_CONVERSION",
            "pass": bool(first_rows)
            and all(bool(row["first_conversion_pass"]) for row in first_rows),
            "record_count": len(first_rows),
            "pass_count": sum(bool(row["first_conversion_pass"]) for row in first_rows),
            "records": first_rows,
            "digital_observation_boundary": (
                "The d_cosim digital output node is not independently observable by "
                "the analog .measure path; behavioral digital DOUT is inferred at "
                "the DAC bridge output and explicitly labeled."
            ),
            "completed_utc": utc_now(),
        },
    )
    if args.stage == "qualification":
        print(
            json.dumps(
                {
                    "warmup": warmup_payload["status"],
                    "numerical": numerical_payload["status"],
                    "summaries": len(summaries),
                },
                sort_keys=True,
            )
        )
        return 0 if warmup_payload["pass"] else 2

    all_68, retained = aggregate_code_views(summaries)
    transition = method_transition_rows(summaries)
    bridge_master = [
        row
        for row in summaries
        if str(row.get("role", "")).startswith("BRIDGE_")
    ]
    bridge_comparison = bridge_comparison_rows(summaries)
    main_master = main_master_rows(summaries, first_rows, numerical_payload)
    for row in main_master:
        row["warmup_qualified"] = bool(warmup_payload["pass"])

    write_csv_atomic(CSV_DIR / "codes_all_68.csv", all_68)
    write_csv_atomic(CSV_DIR / "codes_fft_retained_64.csv", retained)
    write_csv_atomic(CSV_DIR / "steady_state_master_mc10.csv", main_master)
    write_csv_atomic(CSV_DIR / "method_transition_comparison.csv", transition)
    write_csv_atomic(CSV_DIR / "percentile_bridge_master.csv", bridge_master)
    write_csv_atomic(
        CSV_DIR / "percentile_bridge_comparison.csv", bridge_comparison
    )

    execution = execution_status(
        summaries, main_master, warmup_payload, numerical_payload
    )
    write_json_atomic(RESULT_DIR / "mc10_execution_status.json", execution)
    method_transition = {
        "status": "METHOD_TRANSITION_DIAGNOSTIC_COMPARISON",
        "old_method": "FAST64_STARTUP_INCLUSIVE_W0",
        "new_method": STEADY_METHOD_ID,
        "strict_current_mc200_reproduction_claim": False,
        "main_comparison_records": len(transition),
        "bridge_records": len(bridge_comparison),
        "same_run_w0_exact_current_mc200_count": sum(
            truth(row["same_run_w0_matches_current_mc200_codes"])
            for row in transition
        ),
        "completed_utc": utc_now(),
    }
    write_json_atomic(
        RESULT_DIR / "method_transition_audit.json", method_transition
    )
    write_json_atomic(
        RESULT_DIR / "fast64_steady_state_metrics.json",
        {
            "status": "COMPLETE_STEADY_STATE_METRICS"
            if len(main_master) == 20
            else "INCOMPLETE_STEADY_STATE_METRICS",
            "records": len(main_master),
            "hard_dynamic_pass_count": sum(
                truth(row["steady_state_hard_dynamic_pass"]) for row in main_master
            ),
            "snr_budget_pass_count": sum(
                truth(row["steady_state_snr_budget_pass"]) for row in main_master
            ),
            "overall_pass_count": sum(
                row["overall_status"] == "PASS_FAST64_COMPLETE"
                for row in main_master
            ),
            "thresholds": {
                "steady_state_sndr_db_min": SNDR_HARD_MIN_DB,
                "steady_state_enob_raw_min": ENOB_HARD_MIN_BIT,
            },
            "completed_utc": utc_now(),
        },
    )
    print(
        json.dumps(
            {
                "summaries": len(summaries),
                "warmup": warmup_payload["status"],
                "numerical": numerical_payload["status"],
                "main_records": len(main_master),
                "execution": execution["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
