#!/usr/bin/env python3
import json
import math

import numpy as np

from dynamic_analysis import fft_metrics
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    FULL_SCALE_DIFF_V,
    LSB_DIFF_V,
    PVT_CASES,
    ROOT,
    ensure_directories,
    run_frames,
    write_csv,
)


JOB_DIR = ROOT / "jobs" / "pvt_screen"
LOG_DIR = ROOT / "logs" / "pvt_screen"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"

PVT_ORDER = ("TT_3P3_27C", "SS_3P0_125C", "FF_3P6_M40C")
MAJOR_TRANSITIONS = (32, 64, 128, 192, 224)
FAST64_CASES = ((7, 218750.0, "LOW"), (29, 906250.0, "NEAR_NYQUIST"))
SAMPLE_RATE_HZ = 2.0e6


def transition_center(code):
    return -FULL_SCALE_DIFF_V / 2.0 + code * LSB_DIFF_V


def estimate_transition(rows, target):
    valid = [row for row in rows if row["valid"]]
    lower = [row for row in valid if row["code"] < target]
    upper = [row for row in valid if row["code"] >= target]
    if not lower or not upper:
        return None
    low = max(lower, key=lambda row: row["vid_v"])
    high = min(upper, key=lambda row: row["vid_v"])
    if low["vid_v"] >= high["vid_v"]:
        return None
    return 0.5 * (low["vid_v"] + high["vid_v"]), low, high


def run_static_corner(pvt_name, runtime_rows, output_rows):
    vids = [-FULL_SCALE_DIFF_V / 2.0, 0.0, FULL_SCALE_DIFF_V / 2.0]
    meta = [
        ("ENDPOINT", None, None, 0),
        ("MID", None, None, 128),
        ("ENDPOINT", None, None, 255),
    ]
    for target in MAJOR_TRANSITIONS:
        for offset in (-0.75, 0.0, 0.75):
            vids.append(transition_center(target) + offset * LSB_DIFF_V)
            meta.append(("MAJOR_TRANSITION", target, offset, target if offset >= 0 else target - 1))
    stem = f"pvt_static_{pvt_name.lower()}"
    result = run_frames(
        stem,
        {"kind": "static_sequence", "vid_values": vids},
        len(vids),
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=100e-12,
        pvt_name=pvt_name,
    )
    runtime_rows.append(
        {
            "category": "pvt_static",
            "pvt": pvt_name,
            "job": stem,
            "frames": len(vids),
            "elapsed_s": result["elapsed_s"],
            "cached": result.get("cached", False),
            "returncode": result["returncode"],
        }
    )
    corner_rows = []
    for frame, vid, (point_type, target, offset, expected) in zip(
        result["frames"], vids, meta
    ):
        row = {
            "pvt": pvt_name,
            "point_type": point_type,
            "target_transition": target,
            "offset_lsb": offset,
            "vid_v": vid,
            "expected_code_proxy": expected,
            **frame,
        }
        corner_rows.append(row)

    transition_estimates = {}
    transition_rows = []
    for target in MAJOR_TRANSITIONS:
        selected = [row for row in corner_rows if row["target_transition"] == target]
        estimate = estimate_transition(selected, target)
        if estimate is None:
            transition_rows.append(
                {
                    "target": target,
                    "status": "NOT_BRACKETED_IN_REQUIRED_THREE_POINTS",
                    "estimate_v": None,
                    "displacement_lsb": None,
                    "bracket_width_lsb": None,
                }
            )
            continue
        value, low, high = estimate
        transition_estimates[target] = value
        transition_rows.append(
            {
                "target": target,
                "status": "BRACKETED",
                "estimate_v": value,
                "displacement_lsb": (value - transition_center(target)) / LSB_DIFF_V,
                "bracket_width_lsb": (high["vid_v"] - low["vid_v"]) / LSB_DIFF_V,
            }
        )

    sorted_rows = sorted(corner_rows, key=lambda row: row["vid_v"])
    monotonic = all(
        left["code"] <= right["code"] for left, right in zip(sorted_rows, sorted_rows[1:])
    )
    all_valid = all(row["valid"] for row in corner_rows)
    endpoint_low = corner_rows[0]["code"]
    mid_code = corner_rows[1]["code"]
    endpoint_high = corner_rows[2]["code"]
    gain_proxy = (endpoint_high - endpoint_low) / 255.0
    offset_proxy_lsb = mid_code - 127.5
    displacement_values = [
        abs(row["displacement_lsb"])
        for row in transition_rows
        if row["displacement_lsb"] is not None
    ]
    local_width_proxies = []
    sorted_targets = sorted(transition_estimates)
    for left, right in zip(sorted_targets, sorted_targets[1:]):
        actual_span = transition_estimates[right] - transition_estimates[left]
        ideal_span = (right - left) * LSB_DIFF_V
        local_width_proxies.append(actual_span / ideal_span - 1.0)
    unbracketed = sum(row["status"] != "BRACKETED" for row in transition_rows)
    summary = {
        "pvt": pvt_name,
        "status": "PASS" if all_valid and monotonic else "FAIL",
        "all_frames_valid": all_valid,
        "tested_point_monotonic": monotonic,
        "endpoint_low_code": endpoint_low,
        "mid_code": mid_code,
        "endpoint_high_code": endpoint_high,
        "coarse_gain_proxy": gain_proxy,
        "coarse_offset_proxy_lsb": offset_proxy_lsb,
        "major_transition_unbracketed_count": unbracketed,
        "max_abs_transition_displacement_lsb": (
            max(displacement_values) if displacement_values else float("inf")
        ),
        "max_abs_selected_local_width_proxy": (
            max(abs(value) for value in local_width_proxies)
            if local_width_proxies
            else float("inf")
        ),
        "transition_estimates": transition_rows,
        "max_conversion_time_ns": max(
            (row["complete_time_s"] - row["frame_index"] * FRAME_DEFAULT_S - 50e-9)
            * 1e9
            for row in corner_rows
            if math.isfinite(row["complete_time_s"])
        ),
    }
    for row in corner_rows:
        row.update(
            {
                "corner_status": summary["status"],
                "tested_point_monotonic": monotonic,
                "coarse_gain_proxy": gain_proxy,
                "coarse_offset_proxy_lsb": offset_proxy_lsb,
                "major_transition_unbracketed_count": unbracketed,
                "max_abs_transition_displacement_lsb": summary[
                    "max_abs_transition_displacement_lsb"
                ],
                "max_abs_selected_local_width_proxy": summary[
                    "max_abs_selected_local_width_proxy"
                ],
            }
        )
    output_rows.extend(corner_rows)
    return summary


def run_dynamic_corner(pvt_name, bin_index, frequency_hz, band, runtime_rows):
    stem = f"pvt_dynamic_{pvt_name.lower()}_k{bin_index}"
    result = run_frames(
        stem,
        {
            "kind": "sine",
            "frequency_hz": frequency_hz,
            "amplitude_diff_v": 1.5,
            "phase_rad": 0.0,
        },
        64,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=100e-12,
        pvt_name=pvt_name,
    )
    runtime_rows.append(
        {
            "category": "pvt_dynamic",
            "pvt": pvt_name,
            "job": stem,
            "frames": 64,
            "elapsed_s": result["elapsed_s"],
            "cached": result.get("cached", False),
            "returncode": result["returncode"],
        }
    )
    frames = result["frames"]
    codes = [row["code"] for row in frames]
    metrics = fft_metrics(codes, bin_index, SAMPLE_RATE_HZ)
    valid_count = sum(row["valid"] for row in frames)
    invalid_count = sum(
        math.isfinite(row["invalid_v"])
        and row["invalid_v"] > PVT_CASES[pvt_name]["vdd_v"] / 2.0
        for row in frames
    )
    timeout_count = sum(
        math.isfinite(row["timeout_v"])
        and row["timeout_v"] > PVT_CASES[pvt_name]["vdd_v"] / 2.0
        for row in frames
    )
    conversion_times = [
        (row["complete_time_s"] - row["frame_index"] * FRAME_DEFAULT_S - 50e-9)
        * 1e9
        for row in frames
        if math.isfinite(row["complete_time_s"])
    ]
    summary = {
        "pvt": pvt_name,
        "band": band,
        "nfft": 64,
        "fundamental_bin": bin_index,
        "input_frequency_hz": frequency_hz,
        "valid_frames": valid_count,
        "valid_frame_count": valid_count,
        "invalid_count": invalid_count,
        "invalid_decision_count": invalid_count,
        "timeout_count": timeout_count,
        "missing_frame_count": 64 - valid_count,
        "duplicate_frame_count": 64 - len({row["frame_index"] for row in frames}),
        "mean_conversion_time_ns": float(np.mean(conversion_times)),
        "max_conversion_time_ns": max(conversion_times),
        "returncode": result["returncode"],
        "cached": result.get("cached", False),
        "measurement_stem": stem,
        "measurement_maxstep_ps": 100.0,
        "measurement_solver_profile": "DEFAULT",
        **metrics,
    }
    summary["status"] = (
        "PASS"
        if valid_count == 64 and invalid_count == 0 and timeout_count == 0
        else "FAIL"
    )
    summary["performance_status"] = (
        "PASS"
        if summary["status"] == "PASS"
        and metrics["sndr_db"] >= 44.0
        and metrics["enob_bit"] >= 7.0
        and metrics["clipping_count"] == 0
        else "FAIL"
    )
    code_rows = [
        {
            "pvt": pvt_name,
            "band": band,
            "fundamental_bin": bin_index,
            "input_frequency_hz": frequency_hz,
            "frame_index": frame["frame_index"],
            "code": frame["code"],
            "valid": frame["valid"],
            "sampled_diff_v": frame["sampled_diff_v"],
            "input_diff_v": frame["input_diff_v"],
            "complete_time_s": frame["complete_time_s"],
            "measurement_stem": stem,
            "measurement_maxstep_ps": 100.0,
            "measurement_solver_profile": "DEFAULT",
        }
        for frame in frames
    ]
    return summary, code_rows


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    runtime_rows = []
    static_rows = []
    static_summaries = [
        run_static_corner(pvt, runtime_rows, static_rows) for pvt in PVT_ORDER
    ]
    dynamic_rows = []
    dynamic_code_rows = []
    for pvt in PVT_ORDER:
        for bin_index, frequency_hz, band in FAST64_CASES:
            dynamic_row, code_rows = run_dynamic_corner(
                pvt, bin_index, frequency_hz, band, runtime_rows
            )
            dynamic_rows.append(dynamic_row)
            dynamic_code_rows.extend(code_rows)

    dynamic_worst_row = min(
        dynamic_rows,
        key=lambda row: row["sndr_db"] if row["status"] == "PASS" else float("-inf"),
    )
    max_unbracketed = max(
        row["major_transition_unbracketed_count"] for row in static_summaries
    )
    dnl_peak = max(
        row["max_abs_selected_local_width_proxy"]
        for row in static_summaries
        if row["major_transition_unbracketed_count"] == max_unbracketed
    )
    inl_peak = max(
        row["max_abs_transition_displacement_lsb"]
        for row in static_summaries
        if row["major_transition_unbracketed_count"] == max_unbracketed
    )
    static_dnl_ties = [
        row["pvt"]
        for row in static_summaries
        if row["major_transition_unbracketed_count"] == max_unbracketed
        and abs(row["max_abs_selected_local_width_proxy"] - dnl_peak) <= 1e-12
    ]
    static_inl_ties = [
        row["pvt"]
        for row in static_summaries
        if row["major_transition_unbracketed_count"] == max_unbracketed
        and abs(row["max_abs_transition_displacement_lsb"] - inl_peak) <= 1e-12
    ]
    static_dnl_worst = (
        dynamic_worst_row["pvt"]
        if dynamic_worst_row["pvt"] in static_dnl_ties
        else static_dnl_ties[0]
    )
    static_inl_worst = (
        dynamic_worst_row["pvt"]
        if dynamic_worst_row["pvt"] in static_inl_ties
        else static_inl_ties[0]
    )
    overall_status = "PASS" if all(
        row["status"] == "PASS" for row in static_summaries + dynamic_rows
    ) else "FAIL"

    write_csv(CSV_DIR / "pvt_static_screen.csv", static_rows)
    write_csv(CSV_DIR / "pvt_dynamic_fast64.csv", dynamic_rows)
    write_csv(CSV_DIR / "pvt_dynamic_fast64_codes.csv", dynamic_code_rows)
    write_csv(CSV_DIR / "pvt_screen_runtime.csv", runtime_rows)
    payload = {
        "status": overall_status,
        "pvt_static_worst_dnl": static_dnl_worst,
        "pvt_static_worst_inl": static_inl_worst,
        "pvt_static_worst_dnl_tied_candidates": static_dnl_ties,
        "pvt_static_worst_inl_tied_candidates": static_inl_ties,
        "pvt_dynamic_worst": dynamic_worst_row["pvt"],
        "pvt_dynamic_worst_band": dynamic_worst_row["band"],
        "static": static_summaries,
        "dynamic": dynamic_rows,
        "runtime_fresh_s": sum(row["elapsed_s"] for row in runtime_rows),
    }
    (RESULT_DIR / "pvt_screen.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )

    lines = [
        "# Analog PVT Screen",
        "",
        f"- Status: `{overall_status}`",
        "- Logic timing: `fixed TT_3P3_27C timed behavioral controller`",
        f"- PVT_STATIC_WORST_DNL: `{static_dnl_worst}`",
        f"- PVT_STATIC_WORST_INL: `{static_inl_worst}`",
        f"- Static DNL proxy tie candidates: `{', '.join(static_dnl_ties)}`",
        f"- Static INL proxy tie candidates: `{', '.join(static_inl_ties)}`",
        "- Static tie-break rule: select the dynamic-worst corner for conservative exact PVT extraction",
        f"- PVT_DYNAMIC_WORST: `{dynamic_worst_row['pvt']}` / `{dynamic_worst_row['band']}`",
        "",
        "## Packed Static",
        "",
        "| PVT | Valid | Monotonic | Gain proxy | Offset (LSB) | Unbracketed | Max displacement (LSB) | Local width proxy | Max conversion (ns) | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in static_summaries:
        lines.append(
            f"| {row['pvt']} | {row['all_frames_valid']} | {row['tested_point_monotonic']} | "
            f"{row['coarse_gain_proxy']:.6f} | {row['coarse_offset_proxy_lsb']:.3f} | "
            f"{row['major_transition_unbracketed_count']} | "
            f"{row['max_abs_transition_displacement_lsb']:.6f} | "
            f"{row['max_abs_selected_local_width_proxy']:.6f} | "
            f"{row['max_conversion_time_ns']:.6f} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "## FAST64 Dynamic",
            "",
            "| PVT | Band | fin (Hz) | SNDR (dB) | ENOB | SFDR (dB) | THD (dB) | Valid | Max conversion (ns) | Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        )
    )
    for row in dynamic_rows:
        lines.append(
            f"| {row['pvt']} | {row['band']} | {row['input_frequency_hz']:.1f} | "
            f"{row['sndr_db']:.6f} | {row['enob_bit']:.6f} | {row['sfdr_dbc']:.6f} | "
            f"{row['thd_db']:.6f} | {row['valid_frames']}/64 | "
            f"{row['max_conversion_time_ns']:.6f} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "The packed static results are screening proxies, not final DNL/INL.",
            "Unbracketed required three-point transitions remain explicit and are",
            "resolved by the geometric exact search in Phase E.",
            "",
        )
    )
    (REPORT_DIR / "pvt_screen.md").write_text(
        "\n".join(lines), encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": overall_status,
                "static_worst_dnl": static_dnl_worst,
                "static_worst_inl": static_inl_worst,
                "dynamic_worst": dynamic_worst_row["pvt"],
                "fresh_runtime_s": payload["runtime_fresh_s"],
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if overall_status == "PASS" else 2)


if __name__ == "__main__":
    main()
