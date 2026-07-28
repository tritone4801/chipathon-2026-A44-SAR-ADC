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
from sar_event_noise import (
    COMPARATOR_SIGMA_V,
    SAMPLE_SIGMA_V,
    run_event_frames_isolated,
)


JOB_DIR = ROOT / "jobs" / "dynamic_fast128_tail_upgrade"
LOG_DIR = ROOT / "logs" / "dynamic_fast128_tail_upgrade"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

NFFT = 128
SAMPLE_RATE_HZ = 2.0e6
AMPLITUDE_DIFF_V = 1.5
MAXSTEP_S = 50e-12
MAX_WORKERS = 4
TAIL_FRACTION = 0.05
BANDS = (
    {"band": "LOW", "bin": 14, "frequency_hz": 218750.0},
    {"band": "NEAR_NYQUIST", "bin": 58, "frequency_hz": 906250.0},
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


def select_tail_cohort():
    rows = read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    tail_count = max(1, math.ceil(len(rows) * TAIL_FRACTION))
    sndr_order = sorted(rows, key=lambda row: float(row["sndr_db"]))
    sfdr_order = sorted(rows, key=lambda row: float(row["sfdr_dbc"]))
    thd_order = sorted(rows, key=lambda row: float(row["thd_db"]), reverse=True)

    orders = {
        "sndr": sndr_order,
        "sfdr": sfdr_order,
        "thd": thd_order,
    }
    ranks = {
        metric: {
            int(row["mismatch_seed"]): rank
            for rank, row in enumerate(order, start=1)
        }
        for metric, order in orders.items()
    }
    selected = {
        int(row["mismatch_seed"])
        for order in orders.values()
        for row in order[:tail_count]
    }
    cohort = []
    for seed in sorted(selected):
        source = next(row for row in rows if int(row["mismatch_seed"]) == seed)
        cohort.append(
            {
                "mismatch_seed": seed,
                "noise_seed": int(source["noise_seed"]),
                "fast64_sndr_db": float(source["sndr_db"]),
                "fast64_sfdr_dbc": float(source["sfdr_dbc"]),
                "fast64_thd_db": float(source["thd_db"]),
                "sndr_rank_low": ranks["sndr"][seed],
                "sfdr_rank_low": ranks["sfdr"][seed],
                "thd_rank_high": ranks["thd"][seed],
                "in_sndr_p5": seed in {
                    int(row["mismatch_seed"]) for row in sndr_order[:tail_count]
                },
                "in_sfdr_p5": seed in {
                    int(row["mismatch_seed"]) for row in sfdr_order[:tail_count]
                },
                "in_thd_worst_p5": seed in {
                    int(row["mismatch_seed"]) for row in thd_order[:tail_count]
                },
            }
        )
    thresholds = {
        "population_count": len(rows),
        "tail_fraction": TAIL_FRACTION,
        "tail_count_per_metric": tail_count,
        "sndr_p5_inclusive_db": float(sndr_order[tail_count - 1]["sndr_db"]),
        "sfdr_p5_inclusive_dbc": float(sfdr_order[tail_count - 1]["sfdr_dbc"]),
        "thd_worst_p5_inclusive_db": float(thd_order[tail_count - 1]["thd_db"]),
        "union_seed_count": len(cohort),
        "union_seeds": [row["mismatch_seed"] for row in cohort],
    }
    return cohort, thresholds


def build_cases(cohort):
    return [
        {
            **band,
            **member,
            "role": "MC_TAIL_UPGRADE",
            "pvt": "TT_3P3_27C",
        }
        for member in cohort
        for band in BANDS
    ]


def load_required_closure_cache():
    summary_path = CSV_DIR / "dynamic_fast256_closure.csv"
    codes_path = CSV_DIR / "dynamic_fast256_closure_codes.csv"
    if not summary_path.exists() or not codes_path.exists():
        return {}, []
    rows = read_csv(summary_path)
    codes = read_csv(codes_path)
    cache = {}
    for row in rows:
        seed_text = row.get("mismatch_seed", "")
        if not seed_text:
            continue
        key = (int(seed_text), row["band"])
        cache.setdefault(key, row)
    return cache, codes


def reuse_required_case(case, cached_rows, cached_codes):
    key = (case["mismatch_seed"], case["band"])
    source = cached_rows.get(key)
    if source is None:
        return None
    source_role = source["role"]
    row = {
        **source,
        **case,
        "source_role": source_role,
        "result_source": "REUSED_IDENTICAL_REQUIRED_CLOSURE",
        "cached": True,
    }
    codes = []
    for code in cached_codes:
        if (
            code.get("mismatch_seed") == str(case["mismatch_seed"])
            and code.get("band") == case["band"]
            and code.get("role") == source_role
        ):
            codes.append(
                {
                    **code,
                    "role": case["role"],
                    "source_role": source_role,
                    "result_source": "REUSED_IDENTICAL_REQUIRED_CLOSURE",
                }
            )
    if len(codes) != NFFT:
        return None
    return row, codes


def run_case(case, grouped, timing, phase_rad):
    values = coherent_values(
        NFFT,
        case["bin"],
        AMPLITUDE_DIFF_V,
        phase_rad,
        TRACK_FALL_OFFSET_S,
        SAMPLE_RATE_HZ,
    )
    stem = (
        f"fast128_tail_s{case['mismatch_seed']:03d}_{case['band'].lower()}_"
        f"n{case['noise_seed']}"
    )
    result = run_event_frames_isolated(
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
        timeout_s=900,
        max_workers=1,
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
    row = {
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
        "wall_elapsed_s": result["wall_elapsed_s"],
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
        "source_role": "",
        "result_source": (
            "REUSED_CACHED_FRAME_ISOLATED_TAIL_JOB"
            if result.get("cached", False)
            else "SIMULATED_FRAME_ISOLATED"
        ),
    }
    row["absolute_status"] = (
        "PASS"
        if valid == NFFT
        and invalid == 0
        and timeout == 0
        and row["sndr_db"] >= 44.0
        and row["enob_bit"] >= 7.0
        and row["clipping_count"] == 0
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
            "source_role": "",
            "result_source": row["result_source"],
            "measurement_stem": frame.get(
                "measurement_stem", result["measurement_stem"]
            ),
            "measurement_maxstep_ps": frame.get(
                "measurement_maxstep_s", result["measurement_maxstep_s"]
            )
            * 1e12,
            "measurement_solver_profile": frame.get(
                "measurement_solver_profile", result["measurement_solver_profile"]
            ),
            "attempt_count": frame.get("attempt_count"),
            "attempt_stems": frame.get("attempt_stems"),
            "attempt_solver_profiles": frame.get("attempt_solver_profiles"),
            "attempt_returncodes": frame.get("attempt_returncodes"),
            "attempt_simulation_aborted": frame.get(
                "attempt_simulation_aborted"
            ),
            "attempt_elapsed_s": frame.get("attempt_elapsed_s"),
        }
        for frame, ideal, command in zip(
            frames, result["ideal_vid_values"], result["commanded_vid_values"]
        )
    ]
    return row, code_rows


def add_closure_comparisons(rows):
    for row in rows:
        row["fast64_reference"] = (
            "DIRECT_CLOSE_FREQUENCY"
            if row["band"] == "LOW"
            else "NOT_DIRECTLY_COMPARABLE"
        )
        if row["band"] != "LOW":
            row["sndr_delta_db"] = None
            row["sfdr_delta_db"] = None
            row["closure_status"] = row["absolute_status"]
            continue
        row["sndr_delta_db"] = abs(
            float(row["sndr_db"]) - float(row["fast64_sndr_db"])
        )
        row["sfdr_delta_db"] = abs(
            float(row["sfdr_dbc"]) - float(row["fast64_sfdr_dbc"])
        )
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
    cohort, thresholds = select_tail_cohort()
    cases = build_cases(cohort)
    cached_rows, cached_codes = load_required_closure_cache()

    rows = []
    codes = []
    pending = []
    for case in cases:
        reused = reuse_required_case(case, cached_rows, cached_codes)
        if reused is None:
            pending.append(case)
        else:
            row, code_rows = reused
            rows.append(row)
            codes.extend(code_rows)
            print(
                f"FAST256 tail seed={case['mismatch_seed']} band={case['band']} "
                "source=required-closure",
                flush=True,
            )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_case, case, grouped, timing, phase): case
            for case in pending
        }
        for future in as_completed(futures):
            row, code_rows = future.result()
            rows.append(row)
            codes.extend(code_rows)
            print(
                f"FAST256 tail seed={row['mismatch_seed']} band={row['band']} "
                f"SNDR={row['sndr_db']:.3f} SFDR={row['sfdr_dbc']:.3f} "
                f"status={row['absolute_status']}",
                flush=True,
            )

    add_closure_comparisons(rows)
    rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["band"]))
    codes.sort(
        key=lambda row: (
            int(row["mismatch_seed"]),
            row["band"],
            int(row["frame_index"]),
        )
    )
    write_csv(CSV_DIR / "dynamic_fast128_tail_upgrade.csv", rows)
    write_csv(CSV_DIR / "dynamic_fast128_tail_upgrade_codes.csv", codes)

    payload = {
        **thresholds,
        "status": "PASS" if all(row["closure_status"] == "PASS" for row in rows) else "FAIL",
        "case_count": len(rows),
        "expected_case_count": len(cohort) * len(BANDS),
        "simulated_case_count": sum(
            row["result_source"] == "SIMULATED_FRAME_ISOLATED" for row in rows
        ),
        "reused_required_case_count": sum(
            row["result_source"] == "REUSED_IDENTICAL_REQUIRED_CLOSURE" for row in rows
        ),
        "valid_case_count": sum(int(row["valid_frame_count"]) == NFFT for row in rows),
        "absolute_pass_count": sum(row["absolute_status"] == "PASS" for row in rows),
        "closure_pass_count": sum(row["closure_status"] == "PASS" for row in rows),
    }
    (RESULT_DIR / "dynamic_fast128_tail_upgrade.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )

    lines = [
        "# Dynamic FAST128 Tail Upgrade",
        "",
        f"- Status: `{payload['status']}`",
        f"- FAST64 population: `{thresholds['population_count']}`",
        f"- Per-metric 5% tail count: `{thresholds['tail_count_per_metric']}`",
        f"- Union die count: `{thresholds['union_seed_count']}`",
        f"- FAST128 cases: `{len(rows)}` (two bands per die)",
        f"- Newly simulated: `{payload['simulated_case_count']}`",
        f"- Reused identical required-closure cases: `{payload['reused_required_case_count']}`",
        "- SFDR boundary cohort: empirical lowest 5% SFDR.",
        "- THD boundary cohort: empirical highest (least negative) 5% THD.",
        "- Guide-permitted expansion record: `FAST128`",
        "- Coherent bins: `k=14` low frequency and `k=58` near Nyquist.",
        "- Frequencies match the FAST64 low and near-Nyquist settings exactly.",
        "- Execution: frame-isolated replay validated by a 64/64 code-equivalence gate.",
        "- Superseded FAST256 solver-pathology attempts are retained in their original jobs/logs directories.",
        "- Strict maxstep: `0.05 ns`",
        "",
        "| Seed | Band | SNDR rank | SFDR rank | THD rank | FAST128 SNDR | ENOB | SFDR | dSNDR | dSFDR | Source | Status |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        dsndr = "N/A" if row["sndr_delta_db"] is None else f"{row['sndr_delta_db']:.6f}"
        dsfdr = "N/A" if row["sfdr_delta_db"] is None else f"{row['sfdr_delta_db']:.6f}"
        lines.append(
            f"| {row['mismatch_seed']} | {row['band']} | {row['sndr_rank_low']} | "
            f"{row['sfdr_rank_low']} | {row['thd_rank_high']} | {float(row['sndr_db']):.6f} | "
            f"{float(row['enob_bit']):.6f} | {float(row['sfdr_dbc']):.6f} | {dsndr} | "
            f"{dsfdr} | {row['result_source']} | {row['closure_status']} |"
        )
    (REPORT_DIR / "dynamic_fast128_tail_upgrade.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
