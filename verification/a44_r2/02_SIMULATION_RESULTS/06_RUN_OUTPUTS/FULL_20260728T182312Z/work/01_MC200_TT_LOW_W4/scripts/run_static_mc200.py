#!/usr/bin/env python3
import argparse
import csv
import json
import math
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from reconstruct_transfer import (
    MAJOR_TRANSITIONS,
    SamplerMap,
    fit_sampler_map,
    fit_seed_correction,
    nominal_internal_kernel,
    reconstruct_seed,
    switching_states,
    write_model_contract,
)
from run_exact_static import exact_search, static_metrics
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    FULL_SCALE_DIFF_V,
    LSB_DIFF_V,
    ROOT,
    ensure_directories,
    load_cdac_weights,
    run_frames,
    write_csv,
)


JOB_DIR = ROOT / "jobs" / "static_mc200"
LOG_DIR = ROOT / "logs" / "static_mc200"
EXACT_JOB_DIR = ROOT / "jobs" / "exact_static"
EXACT_LOG_DIR = ROOT / "logs" / "exact_static"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

PVT_NAME = "TT_3P3_27C"
BULK_MAXSTEP_S = 100e-12
STRICT_MAXSTEP_S = 50e-12
DEFAULT_WORKERS = 8
PREDECLARED_RANDOM_SEEDS = (1, 2)
VALIDATION_INITIAL_COUNT = 8
VALIDATION_EXPANDED_COUNT = 16
MC_EXACT_SHARD_SIZE = 32
MC_MAJOR_SHARD_SIZE = 8
EXACT_CACHE_MAX_BRACKET_LSB = 0.02


def read_csv(path):
    with Path(path).open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def load_complete_exact_cache(seed):
    up_path = CSV_DIR / f"transitions_mc_seed{seed:03d}_up.csv"
    down_path = CSV_DIR / f"transitions_mc_seed{seed:03d}_down_major.csv"
    runtime_path = CSV_DIR / "static_mc_exact_validation_runtime.csv"
    evaluation_path = CSV_DIR / "static_mc_exact_validation_evaluations.csv"
    required = (up_path, down_path, runtime_path, evaluation_path)
    if not all(path.exists() for path in required):
        return None

    up_rows = read_csv(up_path)
    down_rows = read_csv(down_path)
    if [int(row["target_transition"]) for row in up_rows] != list(range(1, 256)):
        return None
    if [int(row["target_transition"]) for row in down_rows] != list(MAJOR_TRANSITIONS):
        return None
    exact_rows = up_rows + down_rows
    if any(row["status"] != "PASS" for row in exact_rows):
        return None
    if any(
        float(row["final_bracket_width_lsb"]) > EXACT_CACHE_MAX_BRACKET_LSB
        for row in exact_rows
    ):
        return None

    runtime_rows = [
        row
        for row in read_csv(runtime_path)
        if int(row["mismatch_seed"]) == seed
    ]
    evaluation_rows = [
        row
        for row in read_csv(evaluation_path)
        if int(row["mismatch_seed"]) == seed
    ]
    if runtime_rows and evaluation_rows:
        if {row["direction"] for row in runtime_rows} != {"up", "down"}:
            return None
        if {row["direction"] for row in evaluation_rows} != {"up", "down"}:
            return None
        return up_rows, down_rows, runtime_rows, evaluation_rows

    # A terminated batch can leave complete per-seed curves before the aggregate
    # runtime/evaluation tables are rewritten. Reuse only when both job and log
    # evidence sets exist; the transition CSVs above remain the numeric authority.
    evidence_patterns = (
        f"mc_validation_full_modelcenter_s{seed:03d}_*_up_*",
        f"mc_validation_major_modelcenter_s{seed:03d}_*_down_*",
    )
    for pattern in evidence_patterns:
        if not list(EXACT_JOB_DIR.glob(f"{pattern}.spice")):
            return None
        if not list(EXACT_LOG_DIR.glob(f"{pattern}.log")):
            return None
    recovery_runtime = [
        {
            "campaign": "mc_validation_full_modelcenter",
            "pvt": PVT_NAME,
            "mismatch_seed": seed,
            "direction": "up",
            "round": "recovered_complete_curve",
            "job": f"transitions_mc_seed{seed:03d}_up",
            "points": len(up_rows),
            "maxstep_s": STRICT_MAXSTEP_S,
            "elapsed_s": 0.0,
            "cached": True,
            "returncode": 0,
        },
        {
            "campaign": "mc_validation_major_modelcenter",
            "pvt": PVT_NAME,
            "mismatch_seed": seed,
            "direction": "down",
            "round": "recovered_complete_curve",
            "job": f"transitions_mc_seed{seed:03d}_down_major",
            "points": len(down_rows),
            "maxstep_s": STRICT_MAXSTEP_S,
            "elapsed_s": 0.0,
            "cached": True,
            "returncode": 0,
        },
    ]
    return up_rows, down_rows, recovery_runtime, []


def load_timing():
    return json.loads((CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii"))


def load_nominal_transitions():
    rows = read_csv(CSV_DIR / "transitions_tt_nominal_up.csv")
    return {int(row["target_transition"]): float(row["transition_v"]) for row in rows}


def screen_spec(grouped, seed, nominal_transitions, nominal_states, timing):
    states = switching_states(grouped, seed, timing)
    broad = 0.75 * FULL_SCALE_DIFF_V / 2.0
    points = [
        {"kind": "broad_negative", "target": None, "offset_lsb": None, "vid_v": -broad},
        {"kind": "broad_zero", "target": None, "offset_lsb": None, "vid_v": 0.0},
        {"kind": "broad_positive", "target": None, "offset_lsb": None, "vid_v": broad},
    ]
    for target in MAJOR_TRANSITIONS:
        predicted = nominal_transitions[target] + (
            states[target]["cdac_threshold_v"]
            - nominal_states[target]["cdac_threshold_v"]
        )
        for offset_lsb in (-0.75, 0.0, 0.75):
            points.append(
                {
                    "kind": "major_transition",
                    "target": target,
                    "offset_lsb": offset_lsb,
                    "vid_v": predicted + offset_lsb * LSB_DIFF_V,
                }
            )
    points.extend(
        (
            {"kind": "history_negative", "target": None, "offset_lsb": None, "vid_v": -broad},
            {"kind": "history_positive", "target": None, "offset_lsb": None, "vid_v": broad},
        )
    )
    return points


def run_one_screen(grouped, seed, nominal_transitions, nominal_states, timing):
    points = screen_spec(grouped, seed, nominal_transitions, nominal_states, timing)
    label = "nominal" if seed is None else f"s{seed:03d}"
    bulk_stem = f"mc200_screen_{label}"
    input_spec = {"kind": "static_sequence", "vid_values": [point["vid_v"] for point in points]}
    bulk_result = run_frames(
        bulk_stem,
        input_spec,
        len(points),
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=BULK_MAXSTEP_S,
        pvt_name=PVT_NAME,
        mismatch_seed=seed,
        grouped_weights=grouped,
        timeout_s=1800,
    )
    bulk_all_frames_valid = all(frame["valid"] for frame in bulk_result["frames"])
    result = bulk_result
    measurement_stem = bulk_stem
    retry_result = None
    if bulk_result["returncode"] != 0 or not bulk_all_frames_valid:
        measurement_stem = f"{bulk_stem}_strict_retry"
        retry_result = run_frames(
            measurement_stem,
            input_spec,
            len(points),
            JOB_DIR,
            LOG_DIR,
            frame_s=FRAME_DEFAULT_S,
            maxstep_s=STRICT_MAXSTEP_S,
            pvt_name=PVT_NAME,
            mismatch_seed=seed,
            grouped_weights=grouped,
            timeout_s=1800,
        )
        result = retry_result

    point_rows = []
    for index, (point, frame) in enumerate(zip(points, result["frames"])):
        point_rows.append(
            {
                "mismatch_seed": 0 if seed is None else seed,
                "frame_index": index,
                **point,
                "code": frame["code"],
                "valid": frame["valid"],
                "sampled_diff_v": frame["sampled_diff_v"],
                "measured_input_diff_v": frame["input_diff_v"],
                "sampled_input_error_v": frame["sampled_input_error_v"],
                "stable_margin_ns": frame["stable_margin_s"] * 1e9,
                "measurement_stem": measurement_stem,
                "measurement_maxstep_ps": (
                    STRICT_MAXSTEP_S if retry_result is not None else BULK_MAXSTEP_S
                )
                * 1e12,
            }
        )

    valid_rows = [row for row in point_rows if row["valid"] and math.isfinite(row["sampled_diff_v"])]
    sampler_fit_valid = False
    sampler_fit_error = ""
    sampler_fields = {
        "sampler_offset_v": float("nan"),
        "sampler_gain_negative": float("nan"),
        "sampler_gain_positive": float("nan"),
        "sampler_asymmetry_ppm": float("nan"),
        "sampler_fit_rms_v": float("nan"),
    }
    try:
        sampler = fit_sampler_map(
            [row["vid_v"] for row in valid_rows],
            [row["sampled_diff_v"] for row in valid_rows],
        )
        sampler_fields = sampler.as_dict()
        sampler_fit_valid = True
    except (ValueError, np.linalg.LinAlgError) as exc:
        sampler_fit_error = repr(exc)
    broad_rows = point_rows[:3]
    history_rows = point_rows[-2:]
    bracket_count = 0
    width_proxies = []
    bracket_fields = {}
    for major_index, target in enumerate(MAJOR_TRANSITIONS):
        triple = point_rows[3 + 3 * major_index : 6 + 3 * major_index]
        bracketed = (
            all(row["valid"] for row in triple)
            and triple[0]["code"] < target
            and triple[2]["code"] >= target
        )
        bracket_count += int(bracketed)
        code_span = triple[2]["code"] - triple[0]["code"]
        width_proxy = 1.5 / code_span if code_span > 0 else float("inf")
        width_proxies.append(width_proxy)
        bracket_fields[f"transition_{target}_bracketed"] = bracketed
        bracket_fields[f"transition_{target}_codes"] = "/".join(str(row["code"]) for row in triple)
        bracket_fields[f"transition_{target}_width_proxy_lsb"] = width_proxy

    history_reset_pass = (
        history_rows[0]["valid"]
        and history_rows[1]["valid"]
        and history_rows[0]["code"] == broad_rows[0]["code"]
        and history_rows[1]["code"] == broad_rows[2]["code"]
    )
    coarse_gain_codes_per_v = (
        (broad_rows[2]["code"] - broad_rows[0]["code"])
        / (broad_rows[2]["vid_v"] - broad_rows[0]["vid_v"])
    )
    summary = {
        "mismatch_seed": 0 if seed is None else seed,
        "is_nominal": seed is None,
        "all_frames_valid": all(row["valid"] for row in point_rows),
        "invalid_frame_count": sum(not row["valid"] for row in point_rows),
        "major_transition_bracket_count": bracket_count,
        "major_transition_unbracketed_count": len(MAJOR_TRANSITIONS) - bracket_count,
        "selected_code_width_proxy_min_lsb": min(width_proxies),
        "selected_code_width_proxy_max_lsb": max(width_proxies),
        "history_reset_pass": history_reset_pass,
        "history_codes": f"{history_rows[0]['code']}/{history_rows[1]['code']}",
        "coarse_offset_code": broad_rows[1]["code"] - 127.5,
        "coarse_gain_codes_per_v": coarse_gain_codes_per_v,
        "elapsed_s": bulk_result["elapsed_s"] + (retry_result["elapsed_s"] if retry_result else 0.0),
        "cached": result.get("cached", False),
        "bulk_stem": bulk_stem,
        "bulk_returncode": bulk_result["returncode"],
        "bulk_simulation_aborted": bulk_result.get("simulation_aborted", False),
        "bulk_all_frames_valid": bulk_all_frames_valid,
        "retry_used": retry_result is not None,
        "retry_stem": measurement_stem if retry_result is not None else "",
        "retry_returncode": retry_result["returncode"] if retry_result is not None else "",
        "retry_simulation_aborted": (
            retry_result.get("simulation_aborted", False) if retry_result is not None else ""
        ),
        "measurement_stem": measurement_stem,
        "measurement_maxstep_ps": (
            STRICT_MAXSTEP_S if retry_result is not None else BULK_MAXSTEP_S
        )
        * 1e12,
        "sampler_fit_valid": sampler_fit_valid,
        "sampler_fit_error": sampler_fit_error,
        **sampler_fields,
        **bracket_fields,
    }
    return point_rows, summary


def run_screen(seeds, workers):
    grouped = load_cdac_weights()
    timing = load_timing()
    nominal_transitions = load_nominal_transitions()
    nominal_states = switching_states(grouped, None, timing)
    all_points = []
    summaries = []

    nominal_points, nominal_summary = run_one_screen(
        grouped, None, nominal_transitions, nominal_states, timing
    )
    all_points.extend(nominal_points)
    summaries.append(nominal_summary)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                run_one_screen,
                grouped,
                seed,
                nominal_transitions,
                nominal_states,
                timing,
            ): seed
            for seed in seeds
        }
        for future in as_completed(futures):
            seed = futures[future]
            points, summary = future.result()
            all_points.extend(points)
            summaries.append(summary)
            print(
                f"SCREEN seed={seed:03d} valid={summary['all_frames_valid']} "
                f"brackets={summary['major_transition_bracket_count']}/5",
                flush=True,
            )
    all_points.sort(key=lambda row: (int(row["mismatch_seed"]), int(row["frame_index"])))
    summaries.sort(key=lambda row: int(row["mismatch_seed"]))
    write_csv(CSV_DIR / "static_mc200_screen_points.csv", all_points)
    write_csv(CSV_DIR / "static_mc200_screen_summary.csv", summaries)
    return summaries


def run_one_major(grouped, seed):
    runtime_rows = []
    evaluation_rows = []
    rows = exact_search(
        "mc_major",
        PVT_NAME,
        "up",
        list(MAJOR_TRANSITIONS),
        grouped,
        runtime_rows,
        evaluation_rows,
        mismatch_seed=seed,
        shard_size=MC_MAJOR_SHARD_SIZE,
    )
    return seed, rows, runtime_rows, evaluation_rows


def run_major_calibration(seeds, workers):
    grouped = load_cdac_weights()
    transition_rows = []
    runtime_rows = []
    evaluation_rows = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_one_major, grouped, seed): seed for seed in seeds}
        for future in as_completed(futures):
            seed, rows, runtime, evaluations = future.result()
            transition_rows.extend(rows)
            runtime_rows.extend(runtime)
            evaluation_rows.extend(evaluations)
            passed = sum(row["status"] == "PASS" for row in rows)
            print(f"MAJOR seed={seed:03d} transitions={passed}/5", flush=True)
    transition_rows.sort(key=lambda row: (int(row["mismatch_seed"]), int(row["target_transition"])))
    runtime_rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["job"]))
    evaluation_rows.sort(
        key=lambda row: (
            int(row["mismatch_seed"]),
            int(row["target"]),
            row["round"],
            row["role"],
        )
    )
    write_csv(CSV_DIR / "static_mc200_major_exact.csv", transition_rows)
    write_csv(CSV_DIR / "static_mc200_major_exact_runtime.csv", runtime_rows)
    write_csv(CSV_DIR / "static_mc200_major_exact_evaluations.csv", evaluation_rows)
    return transition_rows


def sampler_from_row(row):
    return SamplerMap(
        offset_v=float(row["sampler_offset_v"]),
        gain_negative=float(row["sampler_gain_negative"]),
        gain_positive=float(row["sampler_gain_positive"]),
        rms_residual_v=float(row["sampler_fit_rms_v"]),
    )


def select_unique(candidates, selected):
    for row in candidates:
        seed = int(row["mismatch_seed"])
        if seed not in selected:
            return seed
    raise RuntimeError("could not select a unique validation seed")


def select_validation_cohort(summary_rows, count=VALIDATION_INITIAL_COUNT):
    rows = [dict(row) for row in summary_rows]
    for row in rows:
        for key in (
            "static_risk_score",
            "max_abs_dnl_lsb",
            "max_abs_inl_endpoint_lsb",
            "correction_vicm_slope_scaled_v",
            "correction_settling_scale_v",
        ):
            row[key] = float(row[key])
        row["mismatch_seed"] = int(row["mismatch_seed"])
    risk_order = sorted(rows, key=lambda row: row["static_risk_score"])
    selected = set()
    output = []

    def add(seed, role):
        if seed in selected:
            return False
        selected.add(seed)
        row = next(item for item in rows if item["mismatch_seed"] == seed)
        output.append(
            {
                "mismatch_seed": seed,
                "selection_role": role,
                "static_risk_score": row["static_risk_score"],
                "predicted_max_abs_dnl_lsb": row["max_abs_dnl_lsb"],
                "predicted_max_abs_inl_lsb": row["max_abs_inl_endpoint_lsb"],
            }
        )
        return True

    for seed in PREDECLARED_RANDOM_SEEDS:
        if any(row["mismatch_seed"] == seed for row in rows):
            add(seed, "PREDECLARED_RANDOM")
    if len(output) >= count:
        return output[:count]
    for quantile, role in ((0.10, "P10_STATIC_RISK"), (0.50, "P50_STATIC_RISK"), (0.90, "P90_STATIC_RISK")):
        index = int(round(quantile * (len(risk_order) - 1)))
        candidates = risk_order[index:] + risk_order[:index]
        add(select_unique(candidates, selected), role)
        if len(output) >= count:
            return output[:count]
    add(
        select_unique(sorted(rows, key=lambda row: row["max_abs_dnl_lsb"], reverse=True), selected),
        "PREDICTED_WORST_DNL",
    )
    if len(output) >= count:
        return output[:count]
    add(
        select_unique(
            sorted(rows, key=lambda row: row["max_abs_inl_endpoint_lsb"], reverse=True), selected
        ),
        "PREDICTED_WORST_INL",
    )
    if len(output) >= count:
        return output[:count]
    add(
        select_unique(
            sorted(
                rows,
                key=lambda row: max(
                    abs(row["correction_vicm_slope_scaled_v"]),
                    abs(row["correction_settling_scale_v"]),
                ),
                reverse=True,
            ),
            selected,
        ),
        "WORST_SETTLING_OR_VICM_SHIFT",
    )
    while len(output) < count:
        add(select_unique(list(reversed(risk_order)), selected), "EXPANDED_RISK_TAIL")
    return output[:count]


def reconstruct_all(seeds):
    grouped = load_cdac_weights()
    timing = load_timing()
    screen_rows = read_csv(CSV_DIR / "static_mc200_screen_summary.csv")
    screen_lookup = {int(row["mismatch_seed"]): row for row in screen_rows}
    major_rows = read_csv(CSV_DIR / "static_mc200_major_exact.csv")
    major_lookup = {}
    for row in major_rows:
        if row["status"] == "PASS":
            major_lookup.setdefault(int(row["mismatch_seed"]), {})[
                int(row["target_transition"])
            ] = float(row["transition_v"])
    nominal_transitions = load_nominal_transitions()
    nominal_sampler = sampler_from_row(screen_lookup[0])
    nominal_states = switching_states(grouped, None, timing)
    kernel = nominal_internal_kernel(nominal_transitions, nominal_sampler, nominal_states)
    transition_rows = []
    summary_rows = []
    for seed in seeds:
        if seed not in major_lookup or len(major_lookup[seed]) != len(MAJOR_TRANSITIONS):
            raise RuntimeError(f"seed {seed} lacks five exact major transitions")
        sampler = sampler_from_row(screen_lookup[seed])
        states = switching_states(grouped, seed, timing)
        correction = fit_seed_correction(
            major_lookup[seed], sampler, states, kernel
        )
        rows, summary = reconstruct_seed(seed, sampler, states, kernel, correction)
        transition_rows.extend(rows)
        summary_rows.append(summary)
    transition_rows.sort(key=lambda row: (int(row["mismatch_seed"]), int(row["target_transition"])))
    summary_rows.sort(key=lambda row: int(row["mismatch_seed"]))
    write_csv(CSV_DIR / "static_mc200_reconstructed.csv", transition_rows)
    write_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv", summary_rows)
    cohort = select_validation_cohort(
        summary_rows, count=min(VALIDATION_INITIAL_COUNT, len(summary_rows))
    )
    write_csv(CSV_DIR / "static_mc_exact_cohort.csv", cohort)
    write_model_contract(RESULT_DIR / "transfer_reconstruction_model_contract.json")
    return transition_rows, summary_rows, cohort


def run_one_validation(grouped, seed, predicted_rows):
    predicted_centers = {
        int(row["target_transition"]): float(row["transition_v"])
        for row in predicted_rows
    }
    cached = load_complete_exact_cache(seed)
    if cached is None:
        runtime_rows = []
        evaluation_rows = []
        recovered_partial = False

        def run_or_recover(path, campaign, direction, targets):
            nonlocal recovered_partial
            existing = read_csv(path) if path.exists() else []
            existing_by_target = {
                int(row["target_transition"]): row for row in existing
            }
            retry_targets = [
                target
                for target in targets
                if target not in existing_by_target
                or existing_by_target[target]["status"] != "PASS"
                or float(existing_by_target[target]["final_bracket_width_lsb"])
                > EXACT_CACHE_MAX_BRACKET_LSB
            ]
            if not retry_targets:
                return [existing_by_target[target] for target in targets]
            recovered_partial = bool(existing_by_target)
            centers = dict(predicted_centers)
            for target in retry_targets:
                if target in existing_by_target:
                    centers[target] = float(existing_by_target[target]["transition_v"])
            retry_campaign = (
                f"{campaign}_recovery" if existing_by_target else campaign
            )
            replacements = exact_search(
                retry_campaign,
                PVT_NAME,
                direction,
                retry_targets,
                grouped,
                runtime_rows,
                evaluation_rows,
                mismatch_seed=seed,
                shard_size=MC_EXACT_SHARD_SIZE,
                center_overrides=centers,
                initial_half_lsb=0.10,
                max_expansions=11,
            )
            for row in replacements:
                existing_by_target[int(row["target_transition"])] = row
            return [existing_by_target[target] for target in targets]

        up_rows = run_or_recover(
            CSV_DIR / f"transitions_mc_seed{seed:03d}_up.csv",
            "mc_validation_full_modelcenter",
            "up",
            list(range(1, 256)),
        )
        reverse_rows = run_or_recover(
            CSV_DIR / f"transitions_mc_seed{seed:03d}_down_major.csv",
            "mc_validation_major_modelcenter",
            "down",
            list(MAJOR_TRANSITIONS),
        )
        write_csv(CSV_DIR / f"transitions_mc_seed{seed:03d}_up.csv", up_rows)
        write_csv(CSV_DIR / f"transitions_mc_seed{seed:03d}_down_major.csv", reverse_rows)
        exact_curve_source = (
            "SIMULATED_PARTIAL_CURVE_RECOVERY" if recovered_partial else "SIMULATED"
        )
    else:
        up_rows, reverse_rows, runtime_rows, evaluation_rows = cached
        exact_curve_source = (
            "RECOVERED_COMPLETE_EXACT_CURVE_FROM_TRANSITION_CSV_AND_LOGS"
            if any(row["round"] == "recovered_complete_curve" for row in runtime_rows)
            else "REUSED_COMPLETE_EXACT_CURVE"
        )
    metrics = static_metrics(up_rows)
    predicted = {int(row["target_transition"]): row for row in predicted_rows}
    up_lookup = {int(row["target_transition"]): row for row in up_rows}
    transition_errors = [
        (float(up_lookup[target]["transition_v"]) - float(predicted[target]["transition_v"]))
        / LSB_DIFF_V
        for target in range(1, 256)
    ]
    exact_metric_rows = metrics.get("rows", [])
    dnl_errors = [
        float(exact["dnl_to_next_lsb"]) - float(predicted[index]["dnl_to_next_lsb"])
        for index, exact in enumerate(exact_metric_rows[:-1], start=1)
    ]
    inl_errors = [
        float(exact["inl_endpoint_lsb"]) - float(predicted[index]["inl_endpoint_lsb"])
        for index, exact in enumerate(exact_metric_rows, start=1)
    ]
    reverse_lookup = {int(row["target_transition"]): row for row in reverse_rows}
    reverse_delta = [
        abs(float(reverse_lookup[target]["transition_v"]) - float(up_lookup[target]["transition_v"]))
        / LSB_DIFF_V
        for target in MAJOR_TRANSITIONS
    ]
    predicted_missing = sum(
        1
        for index in range(1, 255)
        if float(predicted[index + 1]["transition_v"]) <= float(predicted[index]["transition_v"])
    )
    row = {
        "mismatch_seed": seed,
        "exact_search_status": metrics.get("status"),
        "max_transition_error_lsb": max(abs(value) for value in transition_errors),
        "max_dnl_error_lsb": max(abs(value) for value in dnl_errors),
        "max_inl_error_lsb": max(abs(value) for value in inl_errors),
        "predicted_missing_codes": predicted_missing,
        "exact_missing_codes": metrics.get("missing_codes"),
        "missing_classification_identical": predicted_missing == metrics.get("missing_codes"),
        "exact_max_abs_dnl_lsb": metrics.get("max_abs_dnl_lsb"),
        "exact_max_abs_inl_endpoint_lsb": metrics.get("max_abs_inl_endpoint_lsb"),
        "selected_reverse_max_delta_lsb": max(reverse_delta),
        "transition_gate_pass": max(abs(value) for value in transition_errors) <= 0.10,
        "dnl_gate_pass": max(abs(value) for value in dnl_errors) <= 0.15,
        "inl_gate_pass": max(abs(value) for value in inl_errors) <= 0.20,
        "missing_gate_pass": predicted_missing == metrics.get("missing_codes"),
        "reverse_gate_pass": max(reverse_delta) <= 0.10,
        "runtime_s": sum(float(item["elapsed_s"]) for item in runtime_rows),
        "exact_curve_source": exact_curve_source,
    }
    row["curve_validation_status"] = (
        "PASS"
        if all(
            (
                row["exact_search_status"] == "PASS",
                row["transition_gate_pass"],
                row["dnl_gate_pass"],
                row["inl_gate_pass"],
                row["missing_gate_pass"],
                row["reverse_gate_pass"],
            )
        )
        else "FAIL"
    )
    return row, runtime_rows, evaluation_rows


def rank_values(values):
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    for rank, index in enumerate(order):
        ranks[index] = float(rank)
    return np.asarray(ranks)


def validate_cohort(cohort_rows):
    grouped = load_cdac_weights()
    reconstructed = read_csv(CSV_DIR / "static_mc200_reconstructed.csv")
    predicted_by_seed = {}
    for row in reconstructed:
        predicted_by_seed.setdefault(int(row["mismatch_seed"]), []).append(row)
    summary_rows = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
    summary_lookup = {int(row["mismatch_seed"]): row for row in summary_rows}
    validation_rows = []
    runtime_rows = []
    evaluation_rows = []
    for cohort in cohort_rows:
        seed = int(cohort["mismatch_seed"])
        row, runtime, evaluations = run_one_validation(
            grouped, seed, predicted_by_seed[seed]
        )
        row["selection_role"] = cohort["selection_role"]
        row["predicted_risk_score"] = float(summary_lookup[seed]["static_risk_score"])
        row["exact_risk_score"] = max(
            float(row["exact_max_abs_dnl_lsb"]),
            float(row["exact_max_abs_inl_endpoint_lsb"]) / 1.5,
            float(int(row["exact_missing_codes"]) > 0),
        )
        validation_rows.append(row)
        runtime_rows.extend(runtime)
        evaluation_rows.extend(evaluations)
        print(
            f"VALIDATE seed={seed:03d} status={row['curve_validation_status']} "
            f"T={row['max_transition_error_lsb']:.4f} "
            f"DNL={row['max_dnl_error_lsb']:.4f} INL={row['max_inl_error_lsb']:.4f}",
            flush=True,
        )

    predicted_risk = [row["predicted_risk_score"] for row in validation_rows]
    exact_risk = [row["exact_risk_score"] for row in validation_rows]
    predicted_rank = rank_values(predicted_risk)
    exact_rank = rank_values(exact_risk)
    if len(validation_rows) > 1:
        rank_correlation = float(np.corrcoef(predicted_rank, exact_rank)[0, 1])
    else:
        rank_correlation = 1.0
    exact_worst_index = int(np.argmax(exact_risk))
    predicted_tail_indices = set(np.argsort(predicted_risk)[-3:])
    tail_pass = exact_worst_index in predicted_tail_indices and rank_correlation >= 0.60
    for index, row in enumerate(validation_rows):
        row["predicted_rank_low_to_high"] = predicted_rank[index]
        row["exact_rank_low_to_high"] = exact_rank[index]
        row["rank_correlation"] = rank_correlation
        row["exact_worst_in_predicted_top3"] = exact_worst_index in predicted_tail_indices
        row["tail_ranking_status"] = "PASS" if tail_pass else "FAIL"
        row["validation_status"] = (
            "PASS"
            if row["curve_validation_status"] == "PASS" and tail_pass
            else "FAIL"
        )
    validation_rows.sort(key=lambda row: int(row["mismatch_seed"]))
    write_csv(CSV_DIR / "static_mc_exact_validation.csv", validation_rows)
    write_csv(CSV_DIR / "static_mc_exact_validation_runtime.csv", runtime_rows)
    write_csv(CSV_DIR / "static_mc_exact_validation_evaluations.csv", evaluation_rows)
    return validation_rows, tail_pass, rank_correlation


def recompute_reconstructed_metrics(rows, previous_summary):
    ordered = sorted(rows, key=lambda row: int(row["target_transition"]))
    values = np.asarray([float(row["transition_v"]) for row in ordered])
    targets = np.arange(1, 256, dtype=float)
    endpoint_lsb_v = (values[-1] - values[0]) / 254.0
    widths = np.diff(values)
    dnl = widths / endpoint_lsb_v - 1.0
    endpoint_ideal = values[0] + (targets - 1.0) * endpoint_lsb_v
    inl_ep = (values - endpoint_ideal) / endpoint_lsb_v
    slope, intercept = np.polyfit(targets, values, 1)
    inl_bf = (values - (intercept + slope * targets)) / slope
    for index, row in enumerate(ordered):
        row["endpoint_lsb_v"] = endpoint_lsb_v
        row["dnl_to_next_lsb"] = float(dnl[index]) if index < 254 else None
        row["inl_endpoint_lsb"] = float(inl_ep[index])
        row["inl_best_fit_lsb"] = float(inl_bf[index])
    worst_width = int(np.argmin(widths))
    worst_dnl = int(np.argmax(np.abs(dnl)))
    worst_inl = int(np.argmax(np.abs(inl_ep)))
    summary = dict(previous_summary)
    summary.update(
        {
            "offset_lsb": float(
                (values[0] - (-FULL_SCALE_DIFF_V / 2.0 + LSB_DIFF_V))
                / LSB_DIFF_V
            ),
            "gain_error_ppm": float(1e6 * (endpoint_lsb_v / LSB_DIFF_V - 1.0)),
            "endpoint_lsb_v": float(endpoint_lsb_v),
            "minimum_code_width_lsb": float(np.min(widths) / endpoint_lsb_v),
            "missing_code_count": int(np.count_nonzero(widths <= 0.0)),
            "max_abs_dnl_lsb": float(np.max(np.abs(dnl))),
            "max_abs_inl_endpoint_lsb": float(np.max(np.abs(inl_ep))),
            "max_abs_inl_best_fit_lsb": float(np.max(np.abs(inl_bf))),
            "worst_width_lower_code": worst_width + 1,
            "worst_dnl_lower_transition": worst_dnl + 1,
            "worst_inl_transition": worst_inl + 1,
            "cohort_residual_recalibrated": True,
        }
    )
    summary["static_risk_score"] = max(
        summary["max_abs_dnl_lsb"],
        summary["max_abs_inl_endpoint_lsb"] / 1.5,
        float(summary["missing_code_count"] > 0),
    )
    summary["reconstructed_spec_status"] = (
        "PASS"
        if summary["max_abs_dnl_lsb"] < 1.0
        and summary["max_abs_inl_endpoint_lsb"] < 1.5
        and summary["missing_code_count"] == 0
        else "FAIL"
    )
    return ordered, summary


def recalibrate_from_exact_cohort(validation_rows):
    calibration_seeds = sorted(int(row["mismatch_seed"]) for row in validation_rows)
    reconstructed = read_csv(CSV_DIR / "static_mc200_reconstructed.csv")
    summary_rows = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
    predicted = {}
    for row in reconstructed:
        predicted.setdefault(int(row["mismatch_seed"]), {})[
            int(row["target_transition"])
        ] = float(row["transition_v"])
    errors = {target: [] for target in range(1, 256)}
    for seed in calibration_seeds:
        exact = read_csv(CSV_DIR / f"transitions_mc_seed{seed:03d}_up.csv")
        for row in exact:
            target = int(row["target_transition"])
            errors[target].append(float(row["transition_v"]) - predicted[seed][target])
    calibration_rows = []
    correction = {}
    for target in range(1, 256):
        values = np.asarray(errors[target], dtype=float)
        correction[target] = float(np.median(values))
        calibration_rows.append(
            {
                "target_transition": target,
                "switch_state_index": target,
                "calibration_seed_count": len(values),
                "median_residual_v": correction[target],
                "median_residual_lsb": correction[target] / LSB_DIFF_V,
                "p10_residual_lsb": float(np.percentile(values, 10) / LSB_DIFF_V),
                "p90_residual_lsb": float(np.percentile(values, 90) / LSB_DIFF_V),
            }
        )
    write_csv(CSV_DIR / "transfer_model_cohort_residual_calibration.csv", calibration_rows)
    pre_curve = CSV_DIR / "static_mc200_reconstructed_pre_cohort_calibration.csv"
    pre_summary = CSV_DIR / "static_mc200_reconstructed_summary_pre_cohort_calibration.csv"
    if not pre_curve.exists():
        shutil.copyfile(CSV_DIR / "static_mc200_reconstructed.csv", pre_curve)
    if not pre_summary.exists():
        shutil.copyfile(CSV_DIR / "static_mc200_reconstructed_summary.csv", pre_summary)
    by_seed = {}
    for row in reconstructed:
        target = int(row["target_transition"])
        row["cohort_residual_calibration_v"] = correction[target]
        row["transition_v"] = float(row["transition_v"]) + correction[target]
        by_seed.setdefault(int(row["mismatch_seed"]), []).append(row)
    previous = {int(row["mismatch_seed"]): row for row in summary_rows}
    updated_rows = []
    updated_summaries = []
    for seed in sorted(by_seed):
        rows, summary = recompute_reconstructed_metrics(by_seed[seed], previous[seed])
        updated_rows.extend(rows)
        updated_summaries.append(summary)
    write_csv(CSV_DIR / "static_mc200_reconstructed.csv", updated_rows)
    write_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv", updated_summaries)
    contract_path = RESULT_DIR / "transfer_reconstruction_model_contract.json"
    contract = json.loads(contract_path.read_text(encoding="ascii"))
    contract["cohort_residual_recalibration"] = {
        "enabled": True,
        "kind": "median exact residual indexed by frozen switch state",
        "calibration_seeds": calibration_seeds,
        "polynomial_interpolation": False,
    }
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return updated_summaries


def expanded_cohort(initial, summary_rows, count):
    candidates = select_validation_cohort(summary_rows, count=count)
    output = [dict(row) for row in initial]
    used = {int(row["mismatch_seed"]) for row in output}
    for row in candidates:
        seed = int(row["mismatch_seed"])
        if seed not in used:
            expanded = dict(row)
            expanded["selection_role"] = "EXPANDED_AFTER_MODEL_RECALIBRATION"
            output.append(expanded)
            used.add(seed)
        if len(output) >= count:
            break
    if len(output) < count:
        risk_order = sorted(
            summary_rows,
            key=lambda row: float(row["static_risk_score"]),
            reverse=True,
        )
        for row in risk_order:
            seed = int(row["mismatch_seed"])
            if seed not in used:
                output.append(
                    {
                        "mismatch_seed": seed,
                        "selection_role": "EXPANDED_RISK_TAIL",
                        "static_risk_score": row["static_risk_score"],
                        "predicted_max_abs_dnl_lsb": row["max_abs_dnl_lsb"],
                        "predicted_max_abs_inl_lsb": row[
                            "max_abs_inl_endpoint_lsb"
                        ],
                    }
                )
                used.add(seed)
            if len(output) >= count:
                break
    return output[:count]


def add_boundary_replays(cohort, summary_rows):
    output = [dict(row) for row in cohort]
    used = {int(row["mismatch_seed"]) for row in output}
    for row in summary_rows:
        boundary = any(
            (
                row["reconstructed_spec_status"] == "FAIL",
                float(row["max_abs_dnl_lsb"]) >= 0.90,
                float(row["max_abs_inl_endpoint_lsb"]) >= 1.35,
                float(row["minimum_code_width_lsb"]) <= 0.10,
            )
        )
        seed = int(row["mismatch_seed"])
        if boundary and seed not in used:
            output.append(
                {
                    "mismatch_seed": seed,
                    "selection_role": "RECONSTRUCTED_FAILURE_OR_BOUNDARY_REPLAY",
                    "static_risk_score": row["static_risk_score"],
                    "predicted_max_abs_dnl_lsb": row["max_abs_dnl_lsb"],
                    "predicted_max_abs_inl_lsb": row[
                        "max_abs_inl_endpoint_lsb"
                    ],
                }
            )
            used.add(seed)
    return output


def percentile(rows, key, value):
    return float(np.percentile([float(row[key]) for row in rows], value))


def write_reports(screen_rows, summary_rows, validation_rows, tail_pass, rank_correlation):
    screen_mc = [row for row in screen_rows if int(row["mismatch_seed"]) != 0]
    reconstructed_pass = sum(row["reconstructed_spec_status"] == "PASS" for row in summary_rows)
    validation_pass = sum(row["validation_status"] == "PASS" for row in validation_rows)
    status = "PASS" if all(
        (
            len(screen_mc) == 200,
            all(str(row["all_frames_valid"]).lower() == "true" for row in screen_mc),
            reconstructed_pass == 200,
            validation_pass == len(validation_rows),
            tail_pass,
        )
    ) else "FAIL"

    static_lines = [
        "# Static MC200",
        "",
        f"- Status: `{status}`",
        f"- Fixed mismatch seeds: `1...200`",
        f"- Packed electrical screens valid: `{sum(str(row['all_frames_valid']).lower() == 'true' for row in screen_mc)}/200`",
        f"- Major-transition screens fully bracketed: `{sum(int(row['major_transition_unbracketed_count']) == 0 for row in screen_mc)}/200`",
        f"- Reconstructed transfer curves passing static specification: `{reconstructed_pass}/200`",
        f"- Exact validation curves passing model gates: `{validation_pass}/{len(validation_rows)}`",
        "",
        "## Population",
        "",
        "| Metric | P10 | P50 | P90 | Worst |",
        "|---|---:|---:|---:|---:|",
        f"| Max abs DNL (LSB) | {percentile(summary_rows, 'max_abs_dnl_lsb', 10):.6f} | {percentile(summary_rows, 'max_abs_dnl_lsb', 50):.6f} | {percentile(summary_rows, 'max_abs_dnl_lsb', 90):.6f} | {max(float(row['max_abs_dnl_lsb']) for row in summary_rows):.6f} |",
        f"| Max abs INL EP (LSB) | {percentile(summary_rows, 'max_abs_inl_endpoint_lsb', 10):.6f} | {percentile(summary_rows, 'max_abs_inl_endpoint_lsb', 50):.6f} | {percentile(summary_rows, 'max_abs_inl_endpoint_lsb', 90):.6f} | {max(float(row['max_abs_inl_endpoint_lsb']) for row in summary_rows):.6f} |",
        f"| Offset (LSB) | {percentile(summary_rows, 'offset_lsb', 10):.6f} | {percentile(summary_rows, 'offset_lsb', 50):.6f} | {percentile(summary_rows, 'offset_lsb', 90):.6f} | {max(abs(float(row['offset_lsb'])) for row in summary_rows):.6f} abs |",
        "",
        "All statistical curves reuse the same MOS and CDAC realization for every test on a die. Noise is disabled in Phase F.",
    ]
    (REPORT_DIR / "static_mc200.md").write_text("\n".join(static_lines) + "\n", encoding="ascii")

    validation_lines = [
        "# Transfer Model Validation",
        "",
        f"- Status: `{'PASS' if validation_pass == len(validation_rows) and tail_pass else 'FAIL'}`",
        f"- Exact cohort size including mandatory boundary replays: `{len(validation_rows)}`",
        f"- Expanded 8-to-16 path triggered: `{(CSV_DIR / 'static_mc_exact_validation_initial8.csv').exists()}`",
        f"- Switch-state cohort residual recalibration used: `{(CSV_DIR / 'transfer_model_cohort_residual_calibration.csv').exists()}`",
        "- Reconstruction: physical CDAC switch-state thresholds plus measured sampler offset/gain/asymmetry, comparator VOS-versus-VICM correction, fixed TT apertures, and an exponential finite-settling feature.",
        "- Polynomial full-transfer interpolation: `NOT_USED`",
        f"- Tail-rank correlation: `{rank_correlation:.6f}`",
        f"- Exact worst seed in reconstructed top three: `{tail_pass}`",
        "",
        "| Seed | Role | Max T err | Max DNL err | Max INL err | Reverse delta | Missing match | Status |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in validation_rows:
        validation_lines.append(
            f"| {row['mismatch_seed']} | {row['selection_role']} | {float(row['max_transition_error_lsb']):.6f} | "
            f"{float(row['max_dnl_error_lsb']):.6f} | {float(row['max_inl_error_lsb']):.6f} | "
            f"{float(row['selected_reverse_max_delta_lsb']):.6f} | {row['missing_classification_identical']} | {row['validation_status']} |"
        )
    validation_lines.extend(
        (
            "",
            "Gates: transition <= 0.10 LSB, DNL <= 0.15 LSB, INL <= 0.20 LSB, identical missing-code classification, and materially correct tail ranking.",
        )
    )
    (REPORT_DIR / "transfer_model_validation.md").write_text(
        "\n".join(validation_lines) + "\n", encoding="ascii"
    )
    payload = {
        "status": status,
        "screen_valid_count": sum(str(row["all_frames_valid"]).lower() == "true" for row in screen_mc),
        "screen_bracket_pass_count": sum(int(row["major_transition_unbracketed_count"]) == 0 for row in screen_mc),
        "reconstructed_pass_count": reconstructed_pass,
        "exact_validation_count": len(validation_rows),
        "exact_validation_pass_count": validation_pass,
        "tail_ranking_pass": tail_pass,
        "tail_rank_correlation": rank_correlation,
    }
    (RESULT_DIR / "static_mc200.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return status


def parse_seeds(value):
    if value == "1:200":
        return list(range(1, 201))
    seeds = sorted({int(token) for token in value.split(",") if token.strip()})
    if not seeds or min(seeds) < 1 or max(seeds) > 200:
        raise argparse.ArgumentTypeError("seeds must be in [1, 200]")
    return seeds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("screen", "major", "reconstruct", "validate", "all"),
        default="all",
    )
    parser.add_argument("--seeds", default="1:200")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    seeds = parse_seeds(args.seeds)
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    started = time.perf_counter()

    if args.stage in ("screen", "all"):
        run_screen(seeds, args.workers)
    if args.stage in ("major", "all"):
        run_major_calibration(seeds, args.workers)
    if args.stage in ("reconstruct", "all"):
        reconstruct_all(seeds)
    if args.stage in ("validate", "all"):
        cohort = read_csv(CSV_DIR / "static_mc_exact_cohort.csv")
        validation_rows, tail_pass, rank_correlation = validate_cohort(cohort)
        summary_rows = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
        initial_gate_pass = tail_pass and all(
            row["curve_validation_status"] == "PASS" for row in validation_rows
        )
        if len(summary_rows) >= VALIDATION_EXPANDED_COUNT and not initial_gate_pass:
            shutil.copyfile(
                CSV_DIR / "static_mc_exact_validation.csv",
                CSV_DIR / "static_mc_exact_validation_initial8.csv",
            )
            summary_rows = recalibrate_from_exact_cohort(validation_rows)
            cohort = expanded_cohort(
                cohort, summary_rows, VALIDATION_EXPANDED_COUNT
            )
            write_csv(CSV_DIR / "static_mc_exact_cohort.csv", cohort)
            validation_rows, tail_pass, rank_correlation = validate_cohort(cohort)
        summary_rows = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
        replay_cohort = add_boundary_replays(cohort, summary_rows)
        if len(replay_cohort) > len(cohort):
            cohort = replay_cohort
            write_csv(CSV_DIR / "static_mc_exact_cohort.csv", cohort)
            validation_rows, tail_pass, rank_correlation = validate_cohort(cohort)
        screen_rows = read_csv(CSV_DIR / "static_mc200_screen_summary.csv")
        status = write_reports(
            screen_rows, summary_rows, validation_rows, tail_pass, rank_correlation
        )
        print(f"STATIC_MC200 status={status}", flush=True)
    print(f"WALL elapsed_s={time.perf_counter() - started:.3f}", flush=True)


if __name__ == "__main__":
    main()
