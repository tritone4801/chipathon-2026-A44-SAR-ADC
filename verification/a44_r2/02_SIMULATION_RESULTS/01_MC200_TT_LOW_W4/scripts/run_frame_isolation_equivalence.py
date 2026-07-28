#!/usr/bin/env python3
import csv
import json
import math

from dynamic_analysis import coherent_values
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    LSB_DIFF_V,
    PVT_CASES,
    ROOT,
    TRACK_FALL_OFFSET_S,
    decode_frames,
    ensure_directories,
    load_cdac_weights,
    run_deck,
    write_csv,
)
from sar_event_noise import run_event_frames_isolated


SOURCE_JOB_DIR = ROOT / "jobs" / "dynamic_mc200_fast64"
SOURCE_LOG_DIR = ROOT / "logs" / "dynamic_mc200_fast64"
JOB_DIR = ROOT / "jobs" / "frame_isolation_equivalence"
LOG_DIR = ROOT / "logs" / "frame_isolation_equivalence"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"
SOURCE_STEM = "fast64_s001_n100001_solver_profile_equivalence_robust50"


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


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    source_deck = (SOURCE_JOB_DIR / f"{SOURCE_STEM}.spice").read_text(
        encoding="ascii"
    )
    continuous = run_deck(
        source_deck,
        SOURCE_STEM,
        SOURCE_JOB_DIR,
        SOURCE_LOG_DIR,
        timeout_s=7200,
    )
    continuous_frames = decode_frames(
        continuous, 64, PVT_CASES["TT_3P3_27C"]["vdd_v"], FRAME_DEFAULT_S
    )
    ideal_values = coherent_values(
        64,
        7,
        1.5,
        selected_phase(),
        TRACK_FALL_OFFSET_S,
        2.0e6,
    )
    isolated = run_event_frames_isolated(
        "frame_isolation_equivalence_s001_low_n100001",
        ideal_values,
        100001,
        timing,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=50e-12,
        pvt_name="TT_3P3_27C",
        mismatch_seed=1,
        grouped_weights=load_cdac_weights(),
        timeout_s=900,
        max_workers=4,
    )
    rows = []
    for continuous_frame, isolated_frame in zip(
        continuous_frames, isolated["frames"]
    ):
        sampled_delta_lsb = (
            isolated_frame["sampled_diff_v"]
            - continuous_frame["sampled_diff_v"]
        ) / LSB_DIFF_V
        complete_delta_ps = (
            isolated_frame["complete_time_s"]
            - continuous_frame["complete_time_s"]
        ) * 1e12
        rows.append(
            {
                "frame_index": continuous_frame["frame_index"],
                "continuous_code": continuous_frame["code"],
                "isolated_code": isolated_frame["code"],
                "code_match": continuous_frame["code"] == isolated_frame["code"],
                "continuous_valid": continuous_frame["valid"],
                "isolated_valid": isolated_frame["valid"],
                "sampled_delta_lsb": sampled_delta_lsb,
                "complete_time_delta_ps": complete_delta_ps,
                "isolated_measurement_stem": isolated_frame["measurement_stem"],
                "isolated_solver_profile": isolated_frame[
                    "measurement_solver_profile"
                ],
                "isolated_attempt_count": isolated_frame["attempt_count"],
            }
        )
    write_csv(CSV_DIR / "frame_isolation_equivalence_fast64.csv", rows)
    sampled = [
        abs(float(row["sampled_delta_lsb"]))
        for row in rows
        if math.isfinite(float(row["sampled_delta_lsb"]))
    ]
    complete = [
        abs(float(row["complete_time_delta_ps"]))
        for row in rows
        if math.isfinite(float(row["complete_time_delta_ps"]))
    ]
    payload = {
        "status": (
            "PASS"
            if continuous["returncode"] == 0
            and all(row["continuous_valid"] and row["isolated_valid"] for row in rows)
            and all(row["code_match"] for row in rows)
            and max(sampled, default=float("inf")) <= 0.01
            and max(complete, default=float("inf")) <= 100.0
            else "FAIL"
        ),
        "frames": len(rows),
        "code_mismatch_count": sum(not row["code_match"] for row in rows),
        "continuous_invalid_count": sum(not row["continuous_valid"] for row in rows),
        "isolated_invalid_count": sum(not row["isolated_valid"] for row in rows),
        "max_abs_sampled_delta_lsb": max(sampled, default=float("inf")),
        "max_abs_complete_time_delta_ps": max(complete, default=float("inf")),
        "continuous_stem": SOURCE_STEM,
        "isolated_stem": isolated["measurement_stem"],
        "isolated_attempt_count": isolated["attempt_count"],
        "isolated_measurement_maxstep_ps": isolated["measurement_maxstep_s"] * 1e12,
        "isolated_solver_profile": isolated["measurement_solver_profile"],
    }
    (RESULT_DIR / "frame_isolation_equivalence.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Frame-Isolation Equivalence",
        "",
        f"- Status: `{payload['status']}`",
        f"- Frames: `{payload['frames']}`",
        f"- Code mismatches: `{payload['code_mismatch_count']}`",
        f"- Maximum sampled-input delta: `{payload['max_abs_sampled_delta_lsb']:.9g} LSB`",
        f"- Maximum completion-time delta: `{payload['max_abs_complete_time_delta_ps']:.9g} ps`",
        "- Continuous reference: `ROBUST_GEAR`, strict 0.05 ns maxstep.",
        "- Isolated replay: same physical frame, mismatch seed, event draws, and strict maxstep.",
    ]
    (REPORT_DIR / "frame_isolation_equivalence.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    print(json.dumps(payload, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
