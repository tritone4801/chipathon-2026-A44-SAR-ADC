#!/usr/bin/env python3
import csv
import json
import math

import numpy as np

from dynamic_analysis import coherent_values, fft_metrics
from run_exact_static import exact_search
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    FULL_SCALE_DIFF_V,
    LSB_DIFF_V,
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


CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"
JOB_DIR = ROOT / "jobs" / "pvt_mc_interaction"
LOG_DIR = ROOT / "logs" / "pvt_mc_interaction"

PVT_NAME = "SS_3P0_125C"
SAMPLE_RATE_HZ = 2.0e6
AMPLITUDE_DIFF_V = 1.5


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def select_static_roles():
    rows = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
    worst_dnl = max(rows, key=lambda row: float(row["max_abs_dnl_lsb"]))
    worst_inl = max(rows, key=lambda row: float(row["max_abs_inl_endpoint_lsb"]))
    worst_offset = max(rows, key=lambda row: abs(float(row["offset_lsb"])))
    dnl_target = int(worst_dnl["worst_dnl_lower_transition"])
    inl_target = int(worst_inl["worst_inl_transition"])
    return (
        {
            "role": "WORST_DNL",
            "mismatch_seed": int(worst_dnl["mismatch_seed"]),
            "targets": sorted({1, 32, 64, 128, 192, 224, 255, dnl_target, dnl_target + 1}),
            "focus_target": dnl_target,
        },
        {
            "role": "WORST_INL",
            "mismatch_seed": int(worst_inl["mismatch_seed"]),
            "targets": sorted(
                {1, 255, *range(max(1, inl_target - 2), min(255, inl_target + 2) + 1)}
            ),
            "focus_target": inl_target,
        },
        {
            "role": "WORST_OFFSET",
            "mismatch_seed": int(worst_offset["mismatch_seed"]),
            "targets": [1, 128, 255],
            "focus_target": 1,
        },
    )


def static_replay(role, grouped):
    runtime_rows = []
    evaluation_rows = []
    transitions = exact_search(
        f"pvt_mc_{role['role'].lower()}",
        PVT_NAME,
        "up",
        role["targets"],
        grouped,
        runtime_rows,
        evaluation_rows,
        mismatch_seed=role["mismatch_seed"],
        shard_size=4,
    )
    lookup = {int(row["target_transition"]): row for row in transitions}
    valid = all(row["status"] == "PASS" for row in transitions)
    endpoint_lsb_v = (
        (float(lookup[255]["transition_v"]) - float(lookup[1]["transition_v"])) / 254.0
        if 1 in lookup and 255 in lookup
        else None
    )
    local_dnl = []
    for target in sorted(lookup):
        if target + 1 in lookup and endpoint_lsb_v:
            local_dnl.append(
                (
                    target,
                    (float(lookup[target + 1]["transition_v"]) - float(lookup[target]["transition_v"]))
                    / endpoint_lsb_v
                    - 1.0,
                )
            )
    local_inl = []
    if endpoint_lsb_v:
        first = float(lookup[1]["transition_v"])
        for target, row in lookup.items():
            ideal = first + (target - 1) * endpoint_lsb_v
            local_inl.append((target, (float(row["transition_v"]) - ideal) / endpoint_lsb_v))
    max_dnl = max((abs(value) for _, value in local_dnl), default=0.0)
    max_inl = max((abs(value) for _, value in local_inl), default=0.0)
    offset_lsb = (
        (float(lookup[1]["transition_v"]) - (-FULL_SCALE_DIFF_V / 2.0 + LSB_DIFF_V))
        / LSB_DIFF_V
        if 1 in lookup
        else None
    )
    status = "PASS" if valid and max_dnl < 1.0 and max_inl < 1.5 else "FAIL"
    summary = {
        "category": "STATIC",
        "role": role["role"],
        "pvt": PVT_NAME,
        "mismatch_seed": role["mismatch_seed"],
        "focus_target": role["focus_target"],
        "tested_targets": "/".join(str(value) for value in role["targets"]),
        "search_pass_count": sum(row["status"] == "PASS" for row in transitions),
        "search_target_count": len(transitions),
        "endpoint_lsb_v": endpoint_lsb_v,
        "max_abs_tested_dnl_lsb": max_dnl,
        "max_abs_tested_inl_lsb": max_inl,
        "offset_lsb": offset_lsb,
        "sndr_db": None,
        "enob_bit": None,
        "sfdr_dbc": None,
        "invalid_count": 0,
        "timeout_count": 0,
        "status": status,
    }
    write_csv(
        CSV_DIR / f"pvt_mc_{role['role'].lower()}_transitions.csv", transitions
    )
    write_csv(
        CSV_DIR / f"pvt_mc_{role['role'].lower()}_runtime.csv", runtime_rows
    )
    return summary


def frozen_phase():
    row = next(
        row
        for row in read_csv(CSV_DIR / "ideal_quantizer_fast64_phase_sweep.csv")
        if row["selected"].lower() == "true"
    )
    return float(row["phase_rad"])


def run_dynamic_case(grouped, timing, seed, noise_seed, phase, band, nfft, bin_index):
    is_expansion = nfft > 64
    role = f"WORST_SNDR_{band}" + ("_FAST128_EXPANSION" if is_expansion else "")
    values = coherent_values(
        nfft,
        bin_index,
        AMPLITUDE_DIFF_V,
        phase,
        TRACK_FALL_OFFSET_S,
        SAMPLE_RATE_HZ,
    )
    suffix = "" if nfft == 64 else f"_fast{nfft}"
    stem = f"pvt_mc_worst_sndr_s{seed:03d}_{band.lower()}{suffix}"
    result = run_event_frames_isolated(
        stem,
        values,
        noise_seed,
        timing,
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=50e-12,
        pvt_name=PVT_NAME,
        mismatch_seed=seed,
        grouped_weights=grouped,
        timeout_s=900,
        max_workers=4,
    )
    frames = result["frames"]
    metrics = fft_metrics([frame["code"] for frame in frames], bin_index)
    vdd = PVT_CASES[PVT_NAME]["vdd_v"]
    invalid = sum(
        math.isfinite(frame["invalid_v"]) and frame["invalid_v"] > vdd / 2.0
        for frame in frames
    )
    timeout = sum(
        math.isfinite(frame["timeout_v"]) and frame["timeout_v"] > vdd / 2.0
        for frame in frames
    )
    valid = sum(frame["valid"] for frame in frames)
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
    missing = nfft - valid
    duplicate = nfft - len({frame["frame_index"] for frame in frames})
    failure_mechanisms = []
    if valid != nfft or invalid or timeout or missing or duplicate:
        failure_mechanisms.append("FRAME_INTEGRITY")
    if metrics["clipping_count"]:
        failure_mechanisms.append("CLIPPING")
    if metrics["sndr_db"] < 44.0:
        failure_mechanisms.append("SNDR")
    if metrics["enob_bit"] < 7.0:
        failure_mechanisms.append("ENOB")
    status = "PASS" if not failure_mechanisms else "FAIL"
    row = {
        "category": "DYNAMIC_EXPANSION" if is_expansion else "DYNAMIC",
        "role": role,
        "pvt": PVT_NAME,
        "mismatch_seed": seed,
        "focus_target": None,
        "tested_targets": None,
        "search_pass_count": None,
        "search_target_count": None,
        "endpoint_lsb_v": None,
        "max_abs_tested_dnl_lsb": None,
        "max_abs_tested_inl_lsb": None,
        "offset_lsb": None,
        "noise_seed": noise_seed,
        "nfft": nfft,
        "fundamental_bin": bin_index,
        "fundamental_frequency_hz": metrics["fundamental_frequency_hz"],
        "phase_rad": phase,
        "sample_sigma_v": SAMPLE_SIGMA_V,
        "comparator_sigma_v": COMPARATOR_SIGMA_V,
        **metrics,
        "valid_frame_count": valid,
        "invalid_count": invalid,
        "invalid_decision_count": invalid,
        "timeout_count": timeout,
        "missing_frame_count": missing,
        "duplicate_frame_count": duplicate,
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
        "failure_mechanism": "/".join(failure_mechanisms) if failure_mechanisms else "NONE",
        "triggered_by_fast64_failure": is_expansion,
        "status": status,
    }
    code_rows = [
        {
            "category": row["category"],
            "role": role,
            "pvt": PVT_NAME,
            "mismatch_seed": seed,
            "noise_seed": noise_seed,
            "nfft": nfft,
            "frame_index": frame["frame_index"],
            "ideal_vid_v": ideal,
            "commanded_vid_v": command,
            "code": frame["code"],
            "valid": frame["valid"],
            "measurement_stem": frame.get("measurement_stem", result["measurement_stem"]),
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
            "attempt_simulation_aborted": frame.get("attempt_simulation_aborted"),
            "attempt_elapsed_s": frame.get("attempt_elapsed_s"),
        }
        for frame, ideal, command in zip(
            frames, result["ideal_vid_values"], result["commanded_vid_values"]
        )
    ]
    return row, code_rows


def dynamic_replays(grouped, timing):
    dynamic = read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    worst = min(dynamic, key=lambda row: float(row["sndr_db"]))
    seed = int(worst["mismatch_seed"])
    noise_seed = int(worst["noise_seed"])
    phase = frozen_phase()
    rows = []
    code_rows = []
    expansion_rows = []
    expansion_codes = []
    bands = (("LOW", 7, 14), ("NEAR_NYQUIST", 29, 58))
    for band, fast64_bin, fast128_bin in bands:
        row, codes = run_dynamic_case(
            grouped, timing, seed, noise_seed, phase, band, 64, fast64_bin
        )
        rows.append(row)
        code_rows.extend(codes)
        print(
            f"PVT_MC {row['role']} NFFT=64 SNDR={row['sndr_db']:.3f} "
            f"ENOB={row['enob_bit']:.3f} status={row['status']}",
            flush=True,
        )
        if row["status"] == "FAIL":
            expanded, expanded_codes = run_dynamic_case(
                grouped, timing, seed, noise_seed, phase, band, 128, fast128_bin
            )
            expanded["fast64_reference_sndr_db"] = row["sndr_db"]
            expanded["fast64_reference_sfdr_dbc"] = row["sfdr_dbc"]
            expanded["sndr_delta_db"] = abs(expanded["sndr_db"] - row["sndr_db"])
            expanded["sfdr_delta_db"] = abs(expanded["sfdr_dbc"] - row["sfdr_dbc"])
            expansion_rows.append(expanded)
            expansion_codes.extend(expanded_codes)
            print(
                f"PVT_MC {expanded['role']} NFFT=128 SNDR={expanded['sndr_db']:.3f} "
                f"ENOB={expanded['enob_bit']:.3f} status={expanded['status']}",
                flush=True,
            )
    return rows, code_rows, expansion_rows, expansion_codes


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    grouped = load_cdac_weights()
    timing = json.loads((CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii"))
    rows = [static_replay(role, grouped) for role in select_static_roles()]
    dynamic_rows, dynamic_codes, expansion_rows, expansion_codes = dynamic_replays(
        grouped, timing
    )
    rows.extend(dynamic_rows)
    write_csv(CSV_DIR / "pvt_mc_tail_replay.csv", rows)
    write_csv(CSV_DIR / "pvt_mc_tail_replay_codes.csv", dynamic_codes)
    write_csv(CSV_DIR / "pvt_mc_dynamic_expansion.csv", expansion_rows)
    write_csv(CSV_DIR / "pvt_mc_dynamic_expansion_codes.csv", expansion_codes)
    all_rows = rows + expansion_rows
    status = "PASS" if all(row["status"] == "PASS" for row in all_rows) else "FAIL"
    payload = {
        "status": status,
        "cases": rows,
        "dynamic_expansion_trigger_count": len(expansion_rows),
        "dynamic_expansion_cases": expansion_rows,
    }
    (RESULT_DIR / "pvt_mc_interaction.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# PVT x MC Interaction",
        "",
        f"- Status: `{status}`",
        f"- Analog corner: `{PVT_NAME}`",
        "- Matrix policy: `MINIMUM_TARGETED_INTERACTION_ONLY`",
        "",
        "| Category | Role | Seed | Static DNL | Static INL | Offset | SNDR | ENOB | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in all_rows:
        def value(key):
            return "N/A" if row[key] is None else f"{row[key]:.6f}"

        lines.append(
            f"| {row['category']} | {row['role']} | {row['mismatch_seed']} | "
            f"{value('max_abs_tested_dnl_lsb')} | {value('max_abs_tested_inl_lsb')} | "
            f"{value('offset_lsb')} | {value('sndr_db')} | {value('enob_bit')} | {row['status']} |"
        )
    (REPORT_DIR / "pvt_mc_interaction.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
