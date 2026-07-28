#!/usr/bin/env python3
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from sar_campaign_common import (
    FRAME_DEFAULT_S,
    LSB_DIFF_V,
    NUMERICAL_TIEBREAK_DIFF_V,
    PVT_CASES,
    ROOT,
    dynamic_metrics,
    ensure_directories,
    load_cdac_weights,
    run_frames,
    select_predicted_tail_seeds,
    write_csv,
)


JOB_DIR = ROOT / "jobs" / "numerical_convergence"
LOG_DIR = ROOT / "logs" / "numerical_convergence"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"

TRANSITIONS = (64, 128, 192)
MAXSTEPS = (100e-12, 50e-12)
STATIC_COARSE_OFFSETS_LSB = np.linspace(-1.93, 2.07, 21)
STATIC_EXPANDED_OFFSETS_LSB = np.linspace(-7.93, 8.07, 41)
STATIC_FINE_POINTS = 11
FAST64_COUNT = 64
FAST64_BIN = 7
SAMPLE_RATE_HZ = 2.0e6
DYNAMIC_PEAK_DIFF_V = 1.5


def label_float(value_s):
    return f"{value_s * 1e12:.0f}ps"


def case_stem(case):
    return case["name"].lower()


def record_runtime(runtime_rows, category, stem, result, frames):
    runtime_rows.append(
        {
            "category": category,
            "job": stem,
            "frames": frames,
            "elapsed_s": result["elapsed_s"],
            "cached": result.get("cached", False),
            "returncode": result["returncode"],
            "deck": str(result["deck"].relative_to(ROOT)),
            "log": str(result["log"].relative_to(ROOT)),
        }
    )


def transition_center(code):
    return -1.7 + code * LSB_DIFF_V


def transition_from_rows(rows, target_code):
    valid = [row for row in rows if row["valid"]]
    lower = [row for row in valid if row["code"] < target_code]
    upper = [row for row in valid if row["code"] >= target_code]
    if not lower or not upper:
        return None
    low = max(lower, key=lambda row: row["vid_v"])
    high = min(upper, key=lambda row: row["vid_v"])
    if low["vid_v"] >= high["vid_v"]:
        return None
    return 0.5 * (low["vid_v"] + high["vid_v"]), low, high


def run_static_scan(
    case,
    maxstep_s,
    frame_s,
    grouped,
    runtime_rows,
    trial_rows,
    suffix="",
):
    maxstep_label = label_float(maxstep_s)
    frame_label = f"{frame_s * 1e9:.0f}ns"
    stem_base = f"static_{case_stem(case)}_{maxstep_label}_{frame_label}{suffix}"
    coarse_vids = []
    coarse_meta = []
    for target in TRANSITIONS:
        center = transition_center(target)
        for offset in STATIC_COARSE_OFFSETS_LSB:
            coarse_vids.append(center + offset * LSB_DIFF_V)
            coarse_meta.append((target, float(offset)))
    coarse_stem = f"{stem_base}_coarse"
    coarse = run_frames(
        coarse_stem,
        {"kind": "static_sequence", "vid_values": coarse_vids},
        len(coarse_vids),
        JOB_DIR,
        LOG_DIR,
        frame_s=frame_s,
        maxstep_s=maxstep_s,
        mismatch_seed=case["mismatch_seed"],
        grouped_weights=grouped,
    )
    record_runtime(runtime_rows, "static_coarse", coarse_stem, coarse, len(coarse_vids))
    coarse_grouped = {target: [] for target in TRANSITIONS}
    for frame, vid, (target, offset) in zip(coarse["frames"], coarse_vids, coarse_meta):
        row = {
            "case": case["name"],
            "mismatch_seed": case["mismatch_seed"],
            "maxstep_s": maxstep_s,
            "frame_s": frame_s,
            "scan": "coarse",
            "target_transition": target,
            "offset_lsb": offset,
            "vid_v": vid,
            **frame,
        }
        trial_rows.append(row)
        coarse_grouped[target].append(row)

    missing_targets = []
    for target in TRANSITIONS:
        estimate = transition_from_rows(coarse_grouped[target], target)
        if estimate is None:
            missing_targets.append(target)

    if missing_targets:
        expanded_vids = []
        expanded_meta = []
        for target in missing_targets:
            center = transition_center(target)
            for offset in STATIC_EXPANDED_OFFSETS_LSB:
                expanded_vids.append(center + offset * LSB_DIFF_V)
                expanded_meta.append((target, float(offset)))
        expanded_stem = f"{stem_base}_expanded"
        expanded = run_frames(
            expanded_stem,
            {"kind": "static_sequence", "vid_values": expanded_vids},
            len(expanded_vids),
            JOB_DIR,
            LOG_DIR,
            frame_s=frame_s,
            maxstep_s=maxstep_s,
            mismatch_seed=case["mismatch_seed"],
            grouped_weights=grouped,
        )
        record_runtime(
            runtime_rows, "static_expanded", expanded_stem, expanded, len(expanded_vids)
        )
        for frame, vid, (target, offset) in zip(
            expanded["frames"], expanded_vids, expanded_meta
        ):
            row = {
                "case": case["name"],
                "mismatch_seed": case["mismatch_seed"],
                "maxstep_s": maxstep_s,
                "frame_s": frame_s,
                "scan": "expanded",
                "target_transition": target,
                "offset_lsb": offset,
                "vid_v": vid,
                **frame,
            }
            trial_rows.append(row)
            coarse_grouped[target].append(row)

    brackets = {}
    for target in TRANSITIONS:
        estimate = transition_from_rows(coarse_grouped[target], target)
        if estimate is None:
            return {
                "status": "FAIL",
                "reason": f"expanded transition {target - 1}/{target} not bracketed",
                "transitions": {},
                "max_sampled_input_error_lsb": float("inf"),
                "min_stable_margin_ns": float("-inf"),
            }
        _, low, high = estimate
        brackets[target] = (low["vid_v"], high["vid_v"])

    fine_vids = []
    fine_meta = []
    for target in TRANSITIONS:
        low, high = brackets[target]
        for vid in np.linspace(low, high, STATIC_FINE_POINTS):
            fine_vids.append(float(vid))
            fine_meta.append(target)
    fine_stem = f"{stem_base}_fine"
    fine = run_frames(
        fine_stem,
        {"kind": "static_sequence", "vid_values": fine_vids},
        len(fine_vids),
        JOB_DIR,
        LOG_DIR,
        frame_s=frame_s,
        maxstep_s=maxstep_s,
        mismatch_seed=case["mismatch_seed"],
        grouped_weights=grouped,
    )
    record_runtime(runtime_rows, "static_fine", fine_stem, fine, len(fine_vids))
    fine_grouped = {target: [] for target in TRANSITIONS}
    for frame, vid, target in zip(fine["frames"], fine_vids, fine_meta):
        row = {
            "case": case["name"],
            "mismatch_seed": case["mismatch_seed"],
            "maxstep_s": maxstep_s,
            "frame_s": frame_s,
            "scan": "fine",
            "target_transition": target,
            "offset_lsb": (vid - transition_center(target)) / LSB_DIFF_V,
            "vid_v": vid,
            **frame,
        }
        trial_rows.append(row)
        fine_grouped[target].append(row)

    transitions = {}
    bracket_widths = {}
    fine_rows = []
    for target in TRANSITIONS:
        estimate = transition_from_rows(fine_grouped[target], target)
        if estimate is None:
            return {
                "status": "FAIL",
                "reason": f"fine transition {target - 1}/{target} not bracketed",
                "transitions": transitions,
                "max_sampled_input_error_lsb": float("inf"),
                "min_stable_margin_ns": float("-inf"),
            }
        value, low, high = estimate
        transitions[target] = value
        bracket_widths[target] = (high["vid_v"] - low["vid_v"]) / LSB_DIFF_V
        fine_rows.extend(fine_grouped[target])
    max_sample_error = max(abs(row["sampled_input_error_v"]) for row in fine_rows)
    min_margin = min(row["stable_margin_s"] for row in fine_rows)
    all_valid = all(row["valid"] for row in fine_rows)
    return {
        "status": "PASS" if all_valid else "FAIL",
        "reason": "all transitions bracketed" if all_valid else "invalid frame in fine scan",
        "transitions": transitions,
        "bracket_width_lsb": bracket_widths,
        "max_sampled_input_error_lsb": max_sample_error / LSB_DIFF_V,
        "min_stable_margin_ns": min_margin * 1e9,
    }


def run_dynamic_case(case, maxstep_s, startup, grouped, runtime_rows):
    maxstep_label = label_float(maxstep_s)
    stem = f"dynamic_{case_stem(case)}_{maxstep_label}_startup{startup}"
    retained = FAST64_COUNT
    total_frames = startup + retained
    frequency_hz = FAST64_BIN * SAMPLE_RATE_HZ / retained
    result = run_frames(
        stem,
        {
            "kind": "sine",
            "frequency_hz": frequency_hz,
            "amplitude_diff_v": DYNAMIC_PEAK_DIFF_V,
            "phase_rad": 0.0,
        },
        total_frames,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=maxstep_s,
        mismatch_seed=case["mismatch_seed"],
        grouped_weights=grouped,
    )
    record_runtime(runtime_rows, "dynamic_fast64", stem, result, total_frames)
    retained_rows = result["frames"][startup:]
    codes = [row["code"] for row in retained_rows]
    metrics = dynamic_metrics(codes, FAST64_BIN, SAMPLE_RATE_HZ)
    valid_count = sum(row["valid"] for row in retained_rows)
    conversion_times_ns = []
    for row in retained_rows:
        index = row["frame_index"]
        sample_edge = index * FRAME_DEFAULT_S + 50e-9
        conversion_times_ns.append((row["complete_time_s"] - sample_edge) * 1e9)
    stream_text = ",".join(str(code) for code in codes)
    return {
        "case": case["name"],
        "mismatch_seed": case["mismatch_seed"],
        "maxstep_s": maxstep_s,
        "startup_frames": startup,
        "status": "PASS" if valid_count == retained else "FAIL",
        "valid_frames": valid_count,
        "retained_frames": retained,
        "invalid_decision_count": sum(
            math.isfinite(row["invalid_v"]) and row["invalid_v"] > 1.0
            for row in retained_rows
        ),
        "timeout_count": sum(
            math.isfinite(row["timeout_v"]) and row["timeout_v"] > 1.0
            for row in retained_rows
        ),
        "mean_conversion_time_ns": float(np.mean(conversion_times_ns)),
        "max_conversion_time_ns": float(np.max(conversion_times_ns)),
        "dout_stream_sha256": hashlib.sha256(stream_text.encode("ascii")).hexdigest(),
        "codes": codes,
        **metrics,
    }


def frame_health_run(frame_s, grouped, runtime_rows):
    vids = []
    expected_codes = []
    for target in TRANSITIONS:
        center = transition_center(target)
        vids.extend((center - 0.25 * LSB_DIFF_V, center + 0.25 * LSB_DIFF_V))
        expected_codes.extend((target - 1, target))
    stem = f"frame_health_{frame_s * 1e9:.0f}ns"
    result = run_frames(
        stem,
        {"kind": "static_sequence", "vid_values": vids},
        len(vids),
        JOB_DIR,
        LOG_DIR,
        frame_s=frame_s,
        maxstep_s=50e-12,
        grouped_weights=grouped,
    )
    record_runtime(runtime_rows, "frame_health", stem, result, len(vids))
    rows = result["frames"]
    all_valid = all(row["valid"] for row in rows)
    code_match = all(row["code"] == expected for row, expected in zip(rows, expected_codes))
    max_sample_error_lsb = max(
        abs(row["sampled_input_error_v"]) / LSB_DIFF_V
        for row in rows
        if math.isfinite(row["sampled_input_error_v"])
    )
    finite_margins = [row["stable_margin_s"] * 1e9 for row in rows if math.isfinite(row["stable_margin_s"])]
    min_margin_ns = min(finite_margins) if finite_margins else float("-inf")
    health_pass = all(
        (
            all_valid,
            code_match,
            max_sample_error_lsb <= 0.01,
            min_margin_ns >= 20.0,
        )
    )
    return {
        "frame_ns": frame_s * 1e9,
        "health_status": "PASS" if health_pass else "FAIL",
        "all_frames_valid": all_valid,
        "expected_codes_match": code_match,
        "max_sampled_input_error_lsb": max_sample_error_lsb,
        "min_dout_stable_margin_ns": min_margin_ns,
        "transition_shift_lsb": None,
        "status": "PASS" if health_pass else "FAIL",
    }


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    grouped = load_cdac_weights()
    static_tail, dynamic_tail, tail_rows = select_predicted_tail_seeds(grouped)
    write_csv(CSV_DIR / "cdac_predicted_tail_ranking.csv", tail_rows)
    cases = [
        {"name": "NOMINAL", "mismatch_seed": None},
        {"name": "FIXED_SEED_001", "mismatch_seed": 1},
        {"name": "FIXED_SEED_002", "mismatch_seed": 2},
        {
            "name": f"PREDICTED_STATIC_TAIL_{static_tail['mismatch_seed']:03d}",
            "mismatch_seed": static_tail["mismatch_seed"],
        },
        {
            "name": f"PREDICTED_DYNAMIC_TAIL_{dynamic_tail['mismatch_seed']:03d}",
            "mismatch_seed": dynamic_tail["mismatch_seed"],
        },
    ]

    runtime_rows = []
    trial_rows = []
    static_results = {}
    dynamic_results = {}
    for case in cases:
        for maxstep_s in MAXSTEPS:
            static_results[(case["name"], maxstep_s)] = run_static_scan(
                case,
                maxstep_s,
                FRAME_DEFAULT_S,
                grouped,
                runtime_rows,
                trial_rows,
            )
            dynamic_results[(case["name"], maxstep_s, 1)] = run_dynamic_case(
                case, maxstep_s, 1, grouped, runtime_rows
            )

    convergence_rows = []
    for case in cases:
        bulk_static = static_results[(case["name"], 100e-12)]
        strict_static = static_results[(case["name"], 50e-12)]
        bulk_dynamic = dynamic_results[(case["name"], 100e-12, 1)]
        strict_dynamic = dynamic_results[(case["name"], 50e-12, 1)]
        transition_deltas = []
        for target in TRANSITIONS:
            if target in bulk_static["transitions"] and target in strict_static["transitions"]:
                transition_deltas.append(
                    abs(
                        bulk_static["transitions"][target]
                        - strict_static["transitions"][target]
                    )
                    / LSB_DIFF_V
                )
            else:
                transition_deltas.append(float("inf"))
        row = {
            "category": "maxstep",
            "case": case["name"],
            "mismatch_seed": case["mismatch_seed"],
            "delta_sndr_db": abs(bulk_dynamic["sndr_db"] - strict_dynamic["sndr_db"]),
            "delta_sfdr_db": abs(bulk_dynamic["sfdr_db"] - strict_dynamic["sfdr_db"]),
            "delta_thd_db": abs(bulk_dynamic["thd_db"] - strict_dynamic["thd_db"]),
            "max_transition_delta_lsb": max(transition_deltas),
            "dout_streams_identical": (
                bulk_dynamic["dout_stream_sha256"] == strict_dynamic["dout_stream_sha256"]
            ),
            "timeout_invalid_identical": (
                bulk_dynamic["timeout_count"] == strict_dynamic["timeout_count"]
                and bulk_dynamic["invalid_decision_count"]
                == strict_dynamic["invalid_decision_count"]
            ),
            "strict_static_status": strict_static["status"],
            "strict_dynamic_status": strict_dynamic["status"],
        }
        row["status"] = "PASS" if all(
            (
                row["delta_sndr_db"] <= 0.30,
                row["delta_sfdr_db"] <= 0.50,
                row["delta_thd_db"] <= 0.50,
                row["max_transition_delta_lsb"] <= 0.05,
                row["dout_streams_identical"],
                row["timeout_invalid_identical"],
                row["strict_static_status"] == "PASS",
                row["strict_dynamic_status"] == "PASS",
            )
        ) else "FAIL"
        convergence_rows.append(row)

    nominal_case = cases[0]
    reference_transitions = static_results[(nominal_case["name"], 50e-12)]["transitions"]
    frame_rows = []
    for frame_ns in (500, 320, 300, 280):
        frame_s = frame_ns * 1e-9
        row = frame_health_run(frame_s, grouped, runtime_rows)
        if row["health_status"] == "PASS" and frame_ns != 500:
            candidate_scan = run_static_scan(
                nominal_case,
                50e-12,
                frame_s,
                grouped,
                runtime_rows,
                trial_rows,
                suffix="_framegate",
            )
            shifts = [
                abs(candidate_scan["transitions"].get(target, float("inf")) - reference_transitions[target])
                / LSB_DIFF_V
                for target in TRANSITIONS
            ]
            row["transition_shift_lsb"] = max(shifts)
            row["status"] = "PASS" if candidate_scan["status"] == "PASS" and max(shifts) <= 0.02 else "FAIL"
        elif frame_ns == 500:
            row["transition_shift_lsb"] = 0.0
        frame_rows.append(row)
    passing_frames = [row["frame_ns"] for row in frame_rows if row["status"] == "PASS"]
    selected_frame_ns = min(passing_frames) if passing_frames else None

    startup_values = (0, 1, 2, 4)
    startup_results = {}
    for startup in startup_values:
        key = (nominal_case["name"], 50e-12, startup)
        if key not in dynamic_results:
            dynamic_results[key] = run_dynamic_case(
                nominal_case, 50e-12, startup, grouped, runtime_rows
            )
        startup_results[startup] = dynamic_results[key]
    startup_rows = []
    for index, startup in enumerate(startup_values):
        current = startup_results[startup]
        row = {
            "startup_frames": startup,
            "sndr_db": current["sndr_db"],
            "sfdr_db": current["sfdr_db"],
            "valid_frames": current["valid_frames"],
            "retained_frames": current["retained_frames"],
        }
        if index < len(startup_values) - 1:
            next_result = startup_results[startup_values[index + 1]]
            row["delta_sndr_to_next_db"] = abs(current["sndr_db"] - next_result["sndr_db"])
            row["delta_sfdr_to_next_db"] = abs(current["sfdr_db"] - next_result["sfdr_db"])
            row["status"] = "PASS" if all(
                (
                    current["status"] == "PASS",
                    next_result["status"] == "PASS",
                    row["delta_sndr_to_next_db"] <= 0.10,
                    row["delta_sfdr_to_next_db"] <= 0.20,
                    current["valid_frames"] == current["retained_frames"],
                )
            ) else "FAIL"
        else:
            row["delta_sndr_to_next_db"] = None
            row["delta_sfdr_to_next_db"] = None
            row["status"] = "REFERENCE"
        startup_rows.append(row)
    passing_startups = [row["startup_frames"] for row in startup_rows if row["status"] == "PASS"]
    selected_startup = min(passing_startups) if passing_startups else None

    bulk_100ps_qualified = all(row["status"] == "PASS" for row in convergence_rows)
    strict_runs_pass = all(
        static_results[(case["name"], 50e-12)]["status"] == "PASS"
        and dynamic_results[(case["name"], 50e-12, 1)]["status"] == "PASS"
        for case in cases
    )
    overall_status = "PASS" if all(
        (
            strict_runs_pass,
            selected_frame_ns is not None,
            selected_startup is not None,
        )
    ) else "FAIL"
    selected_bulk_maxstep_s = 100e-12 if bulk_100ps_qualified else 50e-12

    combined_rows = convergence_rows[:]
    combined_rows.extend({"category": "frame", **row} for row in frame_rows)
    combined_rows.extend({"category": "startup", **row} for row in startup_rows)
    write_csv(CSV_DIR / "numerical_convergence.csv", combined_rows)
    write_csv(CSV_DIR / "numerical_static_trials.csv", trial_rows)
    write_csv(CSV_DIR / "runtime_pilot.csv", runtime_rows)

    serializable_static = {
        f"{case_name}|{maxstep_s:.3e}": value
        for (case_name, maxstep_s), value in static_results.items()
    }
    payload = {
        "status": overall_status,
        "cases": cases,
        "predicted_static_tail": static_tail,
        "predicted_dynamic_tail": dynamic_tail,
        "bulk_100ps_qualified": bulk_100ps_qualified,
        "selected_bulk_maxstep_s": selected_bulk_maxstep_s,
        "strict_maxstep_s": 50e-12,
        "selected_static_frame_ns": selected_frame_ns,
        "selected_startup_frames": selected_startup,
        "numerical_tiebreak_diff_v": NUMERICAL_TIEBREAK_DIFF_V,
        "numerical_tiebreak_lsb": NUMERICAL_TIEBREAK_DIFF_V / LSB_DIFF_V,
        "convergence": convergence_rows,
        "frame_gate": frame_rows,
        "startup_gate": startup_rows,
        "static_results": serializable_static,
        "runtime_fresh_total_s": sum(row["elapsed_s"] for row in runtime_rows),
        "runtime_jobs": len(runtime_rows),
    }
    (RESULT_DIR / "numerical_convergence.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )

    lines = [
        "# Numerical Convergence",
        "",
        f"- Status: `{overall_status}`",
        f"- Predicted static-tail CDAC seed: `{static_tail['mismatch_seed']}`",
        f"- Predicted dynamic-tail CDAC seed: `{dynamic_tail['mismatch_seed']}`",
        f"- 0.10 ns bulk qualification: `{'PASS' if bulk_100ps_qualified else 'FAIL'}`",
        f"- Frozen bulk maxstep: `{selected_bulk_maxstep_s * 1e9:.2f} ns`",
        "- Frozen strict maxstep: `0.05 ns`",
        f"- Frozen static frame: `{selected_frame_ns:.0f} ns`" if selected_frame_ns is not None else "- Frozen static frame: `NONE`",
        f"- Frozen startup frames: `{selected_startup}`" if selected_startup is not None else "- Frozen startup frames: `NONE`",
        f"- Fixed external-input numerical tie-break: `{NUMERICAL_TIEBREAK_DIFF_V * 1e6:.3f} uV,diff` (`{NUMERICAL_TIEBREAK_DIFF_V / LSB_DIFF_V:.6f} LSB`)",
        "",
        "## Maxstep Comparison",
        "",
        "| Case | Seed | dSNDR (dB) | dSFDR (dB) | dTHD (dB) | Max dTransition (LSB) | DOUT identical | Status |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in convergence_rows:
        lines.append(
            f"| {row['case']} | {row['mismatch_seed']} | {row['delta_sndr_db']:.6f} | "
            f"{row['delta_sfdr_db']:.6f} | {row['delta_thd_db']:.6f} | "
            f"{row['max_transition_delta_lsb']:.6f} | {row['dout_streams_identical']} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "## Static Frame Gate",
            "",
            "| Frame (ns) | Valid | Code match | Sample error (LSB) | Stable margin (ns) | Transition shift (LSB) | Status |",
            "|---:|---|---|---:|---:|---:|---|",
        )
    )
    for row in frame_rows:
        shift = "NOT_EVALUABLE" if row["transition_shift_lsb"] is None else f"{row['transition_shift_lsb']:.6f}"
        lines.append(
            f"| {row['frame_ns']:.0f} | {row['all_frames_valid']} | {row['expected_codes_match']} | "
            f"{row['max_sampled_input_error_lsb']:.6f} | {row['min_dout_stable_margin_ns']:.6f} | {shift} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "## Startup Gate",
            "",
            "| Startup | SNDR (dB) | SFDR (dB) | dSNDR next (dB) | dSFDR next (dB) | Valid | Status |",
            "|---:|---:|---:|---:|---:|---:|---|",
        )
    )
    for row in startup_rows:
        dsndr = "N/A" if row["delta_sndr_to_next_db"] is None else f"{row['delta_sndr_to_next_db']:.6f}"
        dsfdr = "N/A" if row["delta_sfdr_to_next_db"] is None else f"{row['delta_sfdr_to_next_db']:.6f}"
        lines.append(
            f"| {row['startup_frames']} | {row['sndr_db']:.6f} | {row['sfdr_db']:.6f} | "
            f"{dsndr} | {dsfdr} | {row['valid_frames']}/{row['retained_frames']} | {row['status']} |"
        )
    (REPORT_DIR / "numerical_convergence.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )

    fresh_runtime = sum(row["elapsed_s"] for row in runtime_rows)
    runtime_lines = [
        "# Runtime Pilot",
        "",
        f"- Jobs recorded: `{len(runtime_rows)}`",
        f"- Fresh simulator wall time: `{fresh_runtime:.3f} s`",
        f"- Cached jobs: `{sum(bool(row['cached']) for row in runtime_rows)}`",
        f"- Selected bulk maxstep: `{selected_bulk_maxstep_s * 1e9:.2f} ns`",
        "",
        "| Category | Job | Frames | Wall time (s) | Cached | RC |",
        "|---|---|---:|---:|---|---:|",
    ]
    for row in runtime_rows:
        runtime_lines.append(
            f"| {row['category']} | {row['job']} | {row['frames']} | "
            f"{row['elapsed_s']:.3f} | {row['cached']} | {row['returncode']} |"
        )
    (REPORT_DIR / "runtime_pilot.md").write_text(
        "\n".join(runtime_lines) + "\n", encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": overall_status,
                "bulk_100ps_qualified": bulk_100ps_qualified,
                "selected_frame_ns": selected_frame_ns,
                "selected_startup_frames": selected_startup,
                "fresh_runtime_s": fresh_runtime,
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if overall_status == "PASS" else 2)


if __name__ == "__main__":
    main()
