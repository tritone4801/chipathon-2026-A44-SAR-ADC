#!/usr/bin/env python3
import csv
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from dynamic_analysis import coherent_values, fft_metrics
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    PVT_CASES,
    ROOT,
    SAMPLE_EDGE_OFFSET_S,
    TRACK_FALL_OFFSET_S,
    ensure_directories,
    load_cdac_weights,
    write_csv,
)
from sar_event_noise import COMPARATOR_SIGMA_V, SAMPLE_SIGMA_V, run_event_frames


JOB_DIR = ROOT / "jobs" / "dynamic_fast256"
LOG_DIR = ROOT / "logs" / "dynamic_fast256"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

NFFT = 256
SAMPLE_RATE_HZ = 2.0e6
AMPLITUDE_DIFF_V = 1.5
MAXSTEP_S = 50e-12
MAX_WORKERS = 4
BANDS = (
    {"band": "LOW", "bin": 29, "frequency_hz": 226562.5},
    {"band": "NEAR_NYQUIST", "bin": 117, "frequency_hz": 914062.5},
)


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def selected_phase():
    row = next(
        row
        for row in read_csv(CSV_DIR / "ideal_quantizer_fast64_phase_sweep.csv")
        if row["selected"].lower() == "true"
    )
    return float(row["phase_rad"])


def select_mc_seeds():
    rows = read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    sndr_order = sorted(rows, key=lambda row: float(row["sndr_db"]))
    sfdr_order = sorted(rows, key=lambda row: float(row["sfdr_dbc"]))
    return (
        (int(sndr_order[len(sndr_order) // 2]["mismatch_seed"]), "MC_MEDIAN"),
        (int(sndr_order[0]["mismatch_seed"]), "MC_WORST_SNDR"),
        (int(sfdr_order[0]["mismatch_seed"]), "MC_WORST_SFDR"),
    )


def build_cases():
    cases = []
    counter = 0
    for pvt, role in (("TT_3P3_27C", "PVT_TT"), ("SS_3P0_125C", "PVT_DYNAMIC_WORST")):
        for band in BANDS:
            counter += 1
            cases.append(
                {
                    **band,
                    "role": role,
                    "pvt": pvt,
                    "mismatch_seed": None,
                    "noise_seed": 510000 + counter,
                }
            )
    for seed, role in select_mc_seeds():
        for band in BANDS:
            counter += 1
            cases.append(
                {
                    **band,
                    "role": role,
                    "pvt": "TT_3P3_27C",
                    "mismatch_seed": seed,
                    "noise_seed": 100000 + seed,
                }
            )
    return cases


def run_case(case, grouped, timing, phase_rad):
    values = coherent_values(
        NFFT,
        case["bin"],
        AMPLITUDE_DIFF_V,
        phase_rad,
        TRACK_FALL_OFFSET_S,
        SAMPLE_RATE_HZ,
    )
    seed_label = "nom" if case["mismatch_seed"] is None else f"s{case['mismatch_seed']:03d}"
    stem = (
        f"fast256_{case['role'].lower()}_{case['band'].lower()}_"
        f"{seed_label}_n{case['noise_seed']}"
    )
    result = run_event_frames(
        stem,
        values,
        case["noise_seed"],
        timing,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=MAXSTEP_S,
        pvt_name=case["pvt"],
        mismatch_seed=case["mismatch_seed"],
        grouped_weights=grouped,
        timeout_s=14400,
    )
    frames = result["frames"]
    metrics = fft_metrics([frame["code"] for frame in frames], case["bin"])
    vdd = PVT_CASES[case["pvt"]]["vdd_v"]
    conversion_times = [
        (
            frame["complete_time_s"]
            - frame["frame_index"] * FRAME_DEFAULT_S
            - SAMPLE_EDGE_OFFSET_S
        )
        * 1e9
        for frame in frames
        if math.isfinite(frame["complete_time_s"])
    ]
    valid = sum(frame["valid"] for frame in frames)
    invalid = sum(
        math.isfinite(frame["invalid_v"]) and frame["invalid_v"] > vdd / 2.0
        for frame in frames
    )
    timeout = sum(
        math.isfinite(frame["timeout_v"]) and frame["timeout_v"] > vdd / 2.0
        for frame in frames
    )
    summary = {
        **case,
        "nfft": NFFT,
        "phase_rad": phase_rad,
        "sample_sigma_v": SAMPLE_SIGMA_V,
        "comparator_sigma_v": COMPARATOR_SIGMA_V,
        **metrics,
        "valid_frame_count": valid,
        "invalid_decision_count": invalid,
        "timeout_count": timeout,
        "missing_frame_count": NFFT - valid,
        "duplicate_frame_count": NFFT - len({frame["frame_index"] for frame in frames}),
        "mean_conversion_time_ns": float(np.mean(conversion_times)),
        "max_conversion_time_ns": max(conversion_times),
        "elapsed_s": result["elapsed_s"],
        "cached": result.get("cached", False),
        "bulk_stem": result["bulk_stem"],
        "bulk_returncode": result["bulk_returncode"],
        "bulk_simulation_aborted": result["bulk_simulation_aborted"],
        "retry_used": result["retry_used"],
        "retry_stem": result["retry_stem"],
        "retry_returncode": result["retry_returncode"],
        "retry_simulation_aborted": result["retry_simulation_aborted"],
        "measurement_stem": result["measurement_stem"],
        "measurement_maxstep_ps": result["measurement_maxstep_s"] * 1e12,
        "measurement_solver_profile": result["measurement_solver_profile"],
        "attempt_count": result["attempt_count"],
        "attempt_stems": result["attempt_stems"],
        "attempt_solver_profiles": result["attempt_solver_profiles"],
        "attempt_returncodes": result["attempt_returncodes"],
        "attempt_simulation_aborted": result["attempt_simulation_aborted"],
        "attempt_elapsed_s": result["attempt_elapsed_s"],
    }
    summary["absolute_status"] = (
        "PASS"
        if valid == NFFT
        and invalid == 0
        and timeout == 0
        and summary["sndr_db"] >= 44.0
        and summary["enob_bit"] >= 7.0
        and summary["clipping_count"] == 0
        else "FAIL"
    )
    code_rows = [
        {
            "role": case["role"],
            "band": case["band"],
            "pvt": case["pvt"],
            "mismatch_seed": case["mismatch_seed"],
            "noise_seed": case["noise_seed"],
            "frame_index": frame["frame_index"],
            "ideal_vid_v": ideal,
            "commanded_vid_v": command,
            "code": frame["code"],
            "valid": frame["valid"],
            "measurement_stem": result["measurement_stem"],
            "measurement_maxstep_ps": result["measurement_maxstep_s"] * 1e12,
            "measurement_solver_profile": result["measurement_solver_profile"],
        }
        for frame, ideal, command in zip(
            frames, result["ideal_vid_values"], result["commanded_vid_values"]
        )
    ]
    return summary, code_rows


def add_fast64_comparisons(rows):
    mc64 = {
        int(row["mismatch_seed"]): row
        for row in read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    }
    pvt64 = read_csv(CSV_DIR / "pvt_dynamic_fast64.csv")
    pvt_lookup = {(row["pvt"], row["band"]): row for row in pvt64}
    for row in rows:
        reference = None
        if row["band"] == "LOW" and row["mismatch_seed"] is not None:
            reference = mc64[int(row["mismatch_seed"])]
        elif row["mismatch_seed"] is None:
            pvt_band = "low" if row["band"] == "LOW" else "near_nyquist"
            reference = pvt_lookup.get((row["pvt"], pvt_band))
        if reference is None:
            row["fast64_reference"] = "NOT_DIRECTLY_COMPARABLE"
            row["fast64_sndr_db"] = None
            row["fast64_sfdr_dbc"] = None
            row["sndr_delta_db"] = None
            row["sfdr_delta_db"] = None
            row["closure_status"] = row["absolute_status"]
            continue
        fast64_sfdr = float(reference.get("sfdr_dbc", reference.get("sfdr_db")))
        row["fast64_reference"] = "DIRECT_CLOSE_FREQUENCY"
        row["fast64_sndr_db"] = float(reference["sndr_db"])
        row["fast64_sfdr_dbc"] = fast64_sfdr
        row["sndr_delta_db"] = abs(float(row["sndr_db"]) - float(reference["sndr_db"]))
        row["sfdr_delta_db"] = abs(float(row["sfdr_dbc"]) - fast64_sfdr)
        row["closure_status"] = (
            "PASS"
            if row["absolute_status"] == "PASS"
            and row["sndr_delta_db"] <= 0.5
            and row["sfdr_delta_db"] <= 1.0
            else "FAIL"
        )


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    grouped = load_cdac_weights()
    timing = json.loads((CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii"))
    phase = selected_phase()
    cases = build_cases()
    rows = []
    codes = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_case, case, grouped, timing, phase): case for case in cases
        }
        for future in as_completed(futures):
            row, code_rows = future.result()
            rows.append(row)
            codes.extend(code_rows)
            print(
                f"FAST256 role={row['role']} band={row['band']} "
                f"SNDR={row['sndr_db']:.3f} SFDR={row['sfdr_dbc']:.3f} "
                f"status={row['absolute_status']}",
                flush=True,
            )
    add_fast64_comparisons(rows)
    rows.sort(key=lambda row: (row["role"], row["band"]))
    codes.sort(
        key=lambda row: (row["role"], row["band"], int(row["frame_index"]))
    )
    write_csv(CSV_DIR / "dynamic_fast256_closure.csv", rows)
    write_csv(CSV_DIR / "dynamic_fast256_closure_codes.csv", codes)
    status = "PASS" if all(row["closure_status"] == "PASS" for row in rows) else "FAIL"
    payload = {
        "status": status,
        "case_count": len(rows),
        "absolute_pass_count": sum(row["absolute_status"] == "PASS" for row in rows),
        "closure_pass_count": sum(row["closure_status"] == "PASS" for row in rows),
        "max_direct_sndr_delta_db": max(
            row["sndr_delta_db"] for row in rows if row["sndr_delta_db"] is not None
        ),
        "max_direct_sfdr_delta_db": max(
            row["sfdr_delta_db"] for row in rows if row["sfdr_delta_db"] is not None
        ),
    }
    (RESULT_DIR / "dynamic_fast256_closure.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Dynamic FAST256 Closure",
        "",
        f"- Status: `{status}`",
        f"- Required cases: `{len(rows)}`",
        "- Strict maxstep: `0.05 ns`",
        "",
        "| Role | Band | PVT | Seed | SNDR | ENOB | SFDR | FAST64 dSNDR | FAST64 dSFDR | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        dsndr = "N/A" if row["sndr_delta_db"] is None else f"{row['sndr_delta_db']:.6f}"
        dsfdr = "N/A" if row["sfdr_delta_db"] is None else f"{row['sfdr_delta_db']:.6f}"
        lines.append(
            f"| {row['role']} | {row['band']} | {row['pvt']} | {row['mismatch_seed']} | "
            f"{row['sndr_db']:.6f} | {row['enob_bit']:.6f} | {row['sfdr_dbc']:.6f} | "
            f"{dsndr} | {dsfdr} | {row['closure_status']} |"
        )
    (REPORT_DIR / "dynamic_fast256_closure.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
