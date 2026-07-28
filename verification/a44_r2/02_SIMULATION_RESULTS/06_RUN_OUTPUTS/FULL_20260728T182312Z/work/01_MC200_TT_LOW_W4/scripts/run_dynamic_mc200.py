#!/usr/bin/env python3
import argparse
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from dynamic_analysis import coherent_values, fft_metrics, select_median_phase
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


JOB_DIR = ROOT / "jobs" / "dynamic_mc200_fast64"
LOG_DIR = ROOT / "logs" / "dynamic_mc200_fast64"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
PLOT_DIR = ROOT / "plots"
CONFIG_DIR = ROOT / "config"

NFFT = 64
BIN_INDEX = 7
SAMPLE_RATE_HZ = 2.0e6
INPUT_AMPLITUDE_DIFF_V = 1.5
MAXSTEP_S = 100e-12
PVT_NAME = "TT_3P3_27C"
DEFAULT_WORKERS = 4


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def parse_seeds(value):
    if value == "1:200":
        return list(range(1, 201))
    return sorted({int(token) for token in value.split(",") if token.strip()})


def dynamic_case(
    grouped,
    timing,
    mismatch_seed,
    noise_seed,
    phase_rad,
    category="MC200_MAIN",
    repeat_index=None,
):
    values = coherent_values(
        NFFT,
        BIN_INDEX,
        INPUT_AMPLITUDE_DIFF_V,
        phase_rad,
        TRACK_FALL_OFFSET_S,
        SAMPLE_RATE_HZ,
    )
    suffix = "main" if repeat_index is None else f"repeat{repeat_index:02d}"
    seed_label = "nom" if mismatch_seed is None else f"s{mismatch_seed:03d}"
    stem = f"fast64_{seed_label}_n{noise_seed}_{suffix}"
    result = run_event_frames(
        stem,
        values,
        noise_seed,
        timing,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=MAXSTEP_S,
        pvt_name=PVT_NAME,
        mismatch_seed=mismatch_seed,
        grouped_weights=grouped,
        timeout_s=7200,
    )
    frames = result["frames"]
    codes = [frame["code"] for frame in frames]
    metrics = fft_metrics(codes, BIN_INDEX, SAMPLE_RATE_HZ)
    vdd = PVT_CASES[PVT_NAME]["vdd_v"]
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
    valid_count = sum(frame["valid"] for frame in frames)
    invalid_count = sum(
        math.isfinite(frame["invalid_v"]) and frame["invalid_v"] > vdd / 2.0
        for frame in frames
    )
    timeout_count = sum(
        math.isfinite(frame["timeout_v"]) and frame["timeout_v"] > vdd / 2.0
        for frame in frames
    )
    summary = {
        "category": category,
        "mismatch_seed": mismatch_seed,
        "noise_seed": noise_seed,
        "repeat_index": repeat_index,
        "pvt": PVT_NAME,
        "nfft": NFFT,
        "fundamental_bin": BIN_INDEX,
        "input_frequency_hz": BIN_INDEX * SAMPLE_RATE_HZ / NFFT,
        "input_vpp_diff_v": 2.0 * INPUT_AMPLITUDE_DIFF_V,
        "phase_rad": phase_rad,
        "sample_sigma_v": SAMPLE_SIGMA_V,
        "comparator_sigma_v": COMPARATOR_SIGMA_V,
        **metrics,
        "mean_conversion_time_ns": float(np.mean(conversion_times)),
        "max_conversion_time_ns": max(conversion_times),
        "invalid_decision_count": invalid_count,
        "timeout_count": timeout_count,
        "missing_frame_count": NFFT - valid_count,
        "duplicate_frame_count": NFFT - len({frame["frame_index"] for frame in frames}),
        "valid_frame_count": valid_count,
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
    summary["status"] = (
        "PASS"
        if valid_count == NFFT
        and invalid_count == 0
        and timeout_count == 0
        and summary["clipping_count"] == 0
        and summary["sndr_db"] >= 44.0
        and summary["enob_bit"] >= 7.0
        else "FAIL"
    )
    frame_rows = []
    for frame, ideal, command in zip(
        frames, result["ideal_vid_values"], result["commanded_vid_values"]
    ):
        frame_rows.append(
            {
                "category": category,
                "mismatch_seed": mismatch_seed,
                "noise_seed": noise_seed,
                "repeat_index": repeat_index,
                "frame_index": frame["frame_index"],
                "ideal_vid_v": ideal,
                "commanded_vid_v": command,
                "code": frame["code"],
                "valid": frame["valid"],
                "invalid_v": frame["invalid_v"],
                "timeout_v": frame["timeout_v"],
                "complete_time_s": frame["complete_time_s"],
                "measurement_stem": result["measurement_stem"],
                "measurement_maxstep_ps": result["measurement_maxstep_s"] * 1e12,
                "measurement_solver_profile": result["measurement_solver_profile"],
            }
        )
    return summary, frame_rows


def run_population(seeds, workers, grouped, timing, phase_rad):
    summaries = []
    frames = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                dynamic_case,
                grouped,
                timing,
                seed,
                100000 + seed,
                phase_rad,
            ): seed
            for seed in seeds
        }
        for future in as_completed(futures):
            summary, frame_rows = future.result()
            summaries.append(summary)
            frames.extend(frame_rows)
            print(
                f"FAST64 seed={summary['mismatch_seed']:03d} "
                f"SNDR={summary['sndr_db']:.3f} ENOB={summary['enob_bit']:.3f} "
                f"status={summary['status']}",
                flush=True,
            )
    summaries.sort(key=lambda row: int(row["mismatch_seed"]))
    frames.sort(key=lambda row: (int(row["mismatch_seed"]), int(row["frame_index"])))
    write_csv(CSV_DIR / "dynamic_mc200_fast64.csv", summaries)
    write_csv(CSV_DIR / "dynamic_mc200_fast64_codes.csv", frames)
    return summaries, frames


def select_repeat_dies(main_rows):
    ordered = sorted(main_rows, key=lambda row: float(row["sndr_db"]))
    requested = (
        (ordered[len(ordered) // 2], "MEDIAN_DIE"),
        (ordered[max(0, int(round(0.10 * (len(ordered) - 1))))], "P10_SNDR_DIE"),
        (ordered[max(0, int(round(0.01 * (len(ordered) - 1))))], "P1_SNDR_DIE"),
        (ordered[0], "WORST_SNDR_DIE"),
    )
    selected = []
    used = set()
    for initial, role in requested:
        candidates = sorted(
            ordered,
            key=lambda row: abs(float(row["sndr_db"]) - float(initial["sndr_db"])),
        )
        row = next(row for row in candidates if int(row["mismatch_seed"]) not in used)
        used.add(int(row["mismatch_seed"]))
        selected.append((int(row["mismatch_seed"]), role))
    return selected


def run_repeats(main_rows, workers, grouped, timing, phase_rad):
    selected = select_repeat_dies(main_rows)
    summaries = []
    frames = []
    jobs = []
    for seed, role in selected:
        for repeat_index in range(8):
            noise_seed = 200000 + seed * 100 + repeat_index
            jobs.append((seed, role, repeat_index, noise_seed))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                dynamic_case,
                grouped,
                timing,
                seed,
                noise_seed,
                phase_rad,
                "NOISE_REPEAT",
                repeat_index,
            ): (seed, role, repeat_index)
            for seed, role, repeat_index, noise_seed in jobs
        }
        for future in as_completed(futures):
            seed, role, repeat_index = futures[future]
            summary, frame_rows = future.result()
            summary["selection_role"] = role
            for row in frame_rows:
                row["selection_role"] = role
            summaries.append(summary)
            frames.extend(frame_rows)
            print(
                f"REPEAT seed={seed:03d} run={repeat_index} SNDR={summary['sndr_db']:.3f}",
                flush=True,
            )
    summaries.sort(
        key=lambda row: (int(row["mismatch_seed"]), int(row["repeat_index"]))
    )
    frames.sort(
        key=lambda row: (
            int(row["mismatch_seed"]),
            int(row["repeat_index"]),
            int(row["frame_index"]),
        )
    )
    write_csv(CSV_DIR / "dynamic_noise_repeat.csv", summaries)
    write_csv(CSV_DIR / "dynamic_noise_repeat_codes.csv", frames)
    return summaries


def percentile(rows, key, q):
    return float(np.percentile([float(row[key]) for row in rows], q))


def write_report(main_rows, repeat_rows, phase):
    valid = sum(int(row["valid_frame_count"]) == NFFT for row in main_rows)
    passed = sum(row["status"] == "PASS" for row in main_rows)
    status = "PASS" if len(main_rows) == 200 and valid == 200 and passed == 200 else "FAIL"
    within_die = {}
    for row in repeat_rows:
        within_die.setdefault(int(row["mismatch_seed"]), []).append(float(row["sndr_db"]))
    within_std = [float(np.std(values, ddof=1)) for values in within_die.values()]
    die_means = [float(np.mean(values)) for values in within_die.values()]
    payload = {
        "status": status,
        "valid_jobs": valid,
        "passing_jobs": passed,
        "phase": phase,
        "sndr_p1_db": percentile(main_rows, "sndr_db", 1),
        "sndr_p10_db": percentile(main_rows, "sndr_db", 10),
        "sndr_p50_db": percentile(main_rows, "sndr_db", 50),
        "sndr_worst_db": min(float(row["sndr_db"]) for row in main_rows),
        "within_die_sndr_std_mean_db": float(np.mean(within_std)),
        "selected_die_mean_spread_db": max(die_means) - min(die_means),
    }
    (RESULT_DIR / "dynamic_mc200_fast64.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Dynamic MC200 FAST64",
        "",
        f"- Status: `{status}`",
        f"- Valid jobs: `{valid}/200`",
        f"- SNDR/ENOB passing jobs: `{passed}/200`",
        f"- Frozen ideal-quantizer median phase: `{phase['phase_rad']:.12f} rad`",
        "- Noise model: `T2_TARGET_CALIBRATED_EVENT_NOISE`",
        "",
        "| Metric | P1 | P10 | P50 | Worst |",
        "|---|---:|---:|---:|---:|",
        f"| SNDR (dB) | {percentile(main_rows, 'sndr_db', 1):.6f} | {percentile(main_rows, 'sndr_db', 10):.6f} | {percentile(main_rows, 'sndr_db', 50):.6f} | {min(float(row['sndr_db']) for row in main_rows):.6f} |",
        f"| ENOB (bit) | {percentile(main_rows, 'enob_bit', 1):.6f} | {percentile(main_rows, 'enob_bit', 10):.6f} | {percentile(main_rows, 'enob_bit', 50):.6f} | {min(float(row['enob_bit']) for row in main_rows):.6f} |",
        f"| SFDR (dBc) | {percentile(main_rows, 'sfdr_dbc', 1):.6f} | {percentile(main_rows, 'sfdr_dbc', 10):.6f} | {percentile(main_rows, 'sfdr_dbc', 50):.6f} | {min(float(row['sfdr_dbc']) for row in main_rows):.6f} |",
        "",
        "## Noise Repeat Diagnostic",
        "",
        f"- Jobs: `{len(repeat_rows)}/32`",
        f"- Mean within-die FAST64 SNDR standard deviation: `{np.mean(within_std):.6f} dB`",
        f"- Selected-die mean SNDR spread: `{max(die_means)-min(die_means):.6f} dB`",
        "",
        "The temporal-noise results are T2 target-calibrated engineering evidence, not native MOS transient-noise evidence.",
    ]
    (REPORT_DIR / "dynamic_mc200_fast64.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("main", "repeat", "all"), default="all")
    parser.add_argument("--seeds", default="1:200")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR, PLOT_DIR)
    grouped = load_cdac_weights()
    timing = json.loads((CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii"))
    phase_rows, phase = select_median_phase(
        NFFT, BIN_INDEX, INPUT_AMPLITUDE_DIFF_V, TRACK_FALL_OFFSET_S
    )
    write_csv(CSV_DIR / "ideal_quantizer_fast64_phase_sweep.csv", phase_rows)
    started = time.perf_counter()
    if args.stage in ("main", "all"):
        nominal_row, nominal_frames = dynamic_case(
            grouped,
            timing,
            None,
            100000,
            phase["phase_rad"],
            category="NOMINAL_REFERENCE",
        )
        write_csv(CSV_DIR / "dynamic_fast64_nominal.csv", [nominal_row])
        write_csv(CSV_DIR / "dynamic_fast64_nominal_codes.csv", nominal_frames)
        main_rows, _ = run_population(
            parse_seeds(args.seeds), args.workers, grouped, timing, phase["phase_rad"]
        )
    else:
        main_rows = read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    if args.stage in ("repeat", "all"):
        repeat_rows = run_repeats(
            main_rows, args.workers, grouped, timing, phase["phase_rad"]
        )
        if len(main_rows) == 200:
            status = write_report(main_rows, repeat_rows, phase)
            print(f"DYNAMIC_MC200 status={status}", flush=True)
    print(f"WALL elapsed_s={time.perf_counter()-started:.3f}", flush=True)


if __name__ == "__main__":
    main()
