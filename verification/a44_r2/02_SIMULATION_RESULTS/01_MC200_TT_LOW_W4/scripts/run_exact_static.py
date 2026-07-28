#!/usr/bin/env python3
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sar_campaign_common import (
    FRAME_DEFAULT_S,
    FULL_SCALE_DIFF_V,
    LSB_DIFF_V,
    PVT_CASES,
    ROOT,
    build_deck,
    decode_frames,
    ensure_directories,
    load_cdac_weights,
    run_deck,
    run_frames,
    write_csv,
)
from sar_event_noise import apply_solver_profile


JOB_DIR = ROOT / "jobs" / "exact_static"
LOG_DIR = ROOT / "logs" / "exact_static"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
PLOT_DIR = ROOT / "plots"

MAX_WORKERS = 4
SHARD_SIZE = 32
FINAL_WIDTH_LSB = 0.02
BULK_MAXSTEP_S = 100e-12
STRICT_MAXSTEP_S = 50e-12
PACKED_TIMEOUT_S = 7200
REPLAY_TIMEOUT_S = 1800
TT_PVT = "TT_3P3_27C"
WORST_PVT = "SS_3P0_125C"


def transition_center(target):
    return -FULL_SCALE_DIFF_V / 2.0 + target * LSB_DIFF_V


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def evaluate_points(
    campaign,
    pvt_name,
    direction,
    round_label,
    points,
    maxstep_s,
    grouped,
    runtime_rows,
    evaluation_rows,
    mismatch_seed=None,
    shard_size=SHARD_SIZE,
):
    if not points:
        return {}
    reverse = direction == "down"
    targets = sorted({point["target"] for point in points}, reverse=reverse)
    point_lookup = {}
    for point in points:
        point_lookup.setdefault(point["target"], []).append(point)
    target_shards = list(chunks(targets, shard_size))

    def run_shard(shard_index, shard_targets):
        shard_points = []
        for target in shard_targets:
            selected = point_lookup[target]
            role_order = {"low": 0, "mid": 1, "high": 2}
            selected = sorted(
                selected,
                key=lambda point: role_order.get(point["role"], 1),
                reverse=reverse,
            )
            shard_points.extend(selected)
        vids = [point["vid_v"] for point in shard_points]
        stem = (
            f"{campaign}_s{int(mismatch_seed):03d}_" if mismatch_seed is not None else f"{campaign}_"
        ) + (
            f"{pvt_name.lower()}_{direction}_{round_label}_"
            f"sh{shard_index:02d}"
        )
        result = run_frames(
            stem,
            {"kind": "static_sequence", "vid_values": vids},
            len(vids),
            JOB_DIR,
            LOG_DIR,
            frame_s=FRAME_DEFAULT_S,
            maxstep_s=maxstep_s,
            pvt_name=pvt_name,
            mismatch_seed=mismatch_seed,
            grouped_weights=grouped,
            timeout_s=PACKED_TIMEOUT_S,
            cache_completed_failure=True,
        )
        return shard_index, stem, shard_points, result

    completed_shards = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(target_shards))) as executor:
        futures = [
            executor.submit(run_shard, index, shard_targets)
            for index, shard_targets in enumerate(target_shards)
        ]
        for future in as_completed(futures):
            completed_shards.append(future.result())

    values = {}
    failed_points = []
    for _, stem, shard_points, result in sorted(completed_shards):
        runtime_rows.append(
            {
                "campaign": campaign,
                "pvt": pvt_name,
                "mismatch_seed": mismatch_seed,
                "direction": direction,
                "round": round_label,
                "job": stem,
                "points": len(shard_points),
                "maxstep_s": maxstep_s,
                "elapsed_s": result["elapsed_s"],
                "cached": result.get("cached", False),
                "returncode": result["returncode"],
            }
        )
        for point, frame in zip(shard_points, result["frames"]):
            key = (point["target"], point["role"])
            row = {
                "campaign": campaign,
                "pvt": pvt_name,
                "mismatch_seed": mismatch_seed,
                "direction": direction,
                "round": round_label,
                "target": point["target"],
                "role": point["role"],
                "vid_v": point["vid_v"],
                "maxstep_s": maxstep_s,
                "code": frame["code"],
                "valid": frame["valid"],
                "stable_margin_ns": frame["stable_margin_s"] * 1e9,
                "job": stem,
            }
            evaluation_rows.append(row)
            if frame["valid"]:
                values[key] = row
            else:
                failed_points.append(point)

    if failed_points:
        def replay(point):
            base_stem = (
                f"{campaign}_s{int(mismatch_seed):03d}_" if mismatch_seed is not None else f"{campaign}_"
            ) + (
                f"{pvt_name.lower()}_{direction}_{round_label}_"
                f"replay_t{point['target']:03d}_{point['role']}"
            )
            first = run_frames(
                base_stem,
                {"kind": "static_sequence", "vid_values": [point["vid_v"]]},
                1,
                JOB_DIR,
                LOG_DIR,
                frame_s=FRAME_DEFAULT_S,
                maxstep_s=STRICT_MAXSTEP_S,
                pvt_name=pvt_name,
                mismatch_seed=mismatch_seed,
                grouped_weights=grouped,
                timeout_s=REPLAY_TIMEOUT_S,
            )
            attempts = [(base_stem, "DEFAULT", first)]
            if not first["frames"][0]["valid"]:
                for profile in ("ROBUST_GEAR", "ULTRA_ROBUST_GEAR"):
                    stem = f"{base_stem}_{profile.lower()}"
                    deck = build_deck(
                        input_spec={
                            "kind": "static_sequence",
                            "vid_values": [point["vid_v"]],
                        },
                        total_frames=1,
                        frame_s=FRAME_DEFAULT_S,
                        maxstep_s=STRICT_MAXSTEP_S,
                        pvt_name=pvt_name,
                        mismatch_seed=mismatch_seed,
                        grouped_weights=grouped,
                    )
                    result = run_deck(
                        apply_solver_profile(deck, profile),
                        stem,
                        JOB_DIR,
                        LOG_DIR,
                        timeout_s=REPLAY_TIMEOUT_S,
                    )
                    result["frames"] = decode_frames(
                        result,
                        1,
                        PVT_CASES[pvt_name]["vdd_v"],
                        FRAME_DEFAULT_S,
                    )
                    attempts.append((stem, profile, result))
                    if result["frames"][0]["valid"]:
                        break
            return point, attempts

        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(failed_points))) as executor:
            futures = [executor.submit(replay, point) for point in failed_points]
            for future in as_completed(futures):
                point, attempts = future.result()
                for stem, profile, result in attempts:
                    frame = result["frames"][0]
                    replay_round = f"{round_label}_replay_{profile.lower()}"
                    runtime_rows.append(
                        {
                            "campaign": campaign,
                            "pvt": pvt_name,
                            "mismatch_seed": mismatch_seed,
                            "direction": direction,
                            "round": replay_round,
                            "job": stem,
                            "points": 1,
                            "maxstep_s": STRICT_MAXSTEP_S,
                            "elapsed_s": result["elapsed_s"],
                            "cached": result.get("cached", False),
                            "returncode": result["returncode"],
                        }
                    )
                    row = {
                        "campaign": campaign,
                        "pvt": pvt_name,
                        "mismatch_seed": mismatch_seed,
                        "direction": direction,
                        "round": replay_round,
                        "target": point["target"],
                        "role": point["role"],
                        "vid_v": point["vid_v"],
                        "maxstep_s": STRICT_MAXSTEP_S,
                        "code": frame["code"],
                        "valid": frame["valid"],
                        "stable_margin_ns": frame["stable_margin_s"] * 1e9,
                        "job": stem,
                    }
                    evaluation_rows.append(row)
                    if frame["valid"]:
                        values[(point["target"], point["role"])] = row
                        break
    return values


def exact_search(
    campaign,
    pvt_name,
    direction,
    targets,
    grouped,
    runtime_rows,
    evaluation_rows,
    mismatch_seed=None,
    shard_size=SHARD_SIZE,
    center_overrides=None,
    initial_half_lsb=0.5,
    max_expansions=6,
):
    if center_overrides is None:
        center_overrides = {}
    states = {
        target: {
            "target": target,
            "center_v": center_overrides.get(target, transition_center(target)),
            "low_v": None,
            "high_v": None,
            "low_code": None,
            "high_code": None,
            "expansion_rounds": 0,
            "bisection_rounds": 0,
            "valid": False,
            "reason": "NOT_BRACKETED",
        }
        for target in targets
    }
    unresolved = set(targets)
    for expansion in range(max_expansions):
        half_lsb = initial_half_lsb * (2**expansion)
        expansion_maxstep_s = (
            STRICT_MAXSTEP_S if 2.0 * half_lsb <= 0.08 else BULK_MAXSTEP_S
        )
        points = []
        for target in sorted(unresolved):
            center = states[target]["center_v"]
            points.extend(
                (
                    {
                        "target": target,
                        "role": "low",
                        "vid_v": center - half_lsb * LSB_DIFF_V,
                    },
                    {
                        "target": target,
                        "role": "high",
                        "vid_v": center + half_lsb * LSB_DIFF_V,
                    },
                )
            )
        values = evaluate_points(
            campaign,
            pvt_name,
            direction,
            f"expand{expansion}",
            points,
            expansion_maxstep_s,
            grouped,
            runtime_rows,
            evaluation_rows,
            mismatch_seed,
            shard_size,
        )
        newly_bracketed = []
        for target in sorted(unresolved):
            low = values.get((target, "low"))
            high = values.get((target, "high"))
            states[target]["expansion_rounds"] = expansion + 1
            if low is None or high is None:
                states[target]["reason"] = "INVALID_EXPANSION_POINT"
                continue
            if low["code"] < target and high["code"] >= target:
                states[target].update(
                    {
                        "low_v": low["vid_v"],
                        "high_v": high["vid_v"],
                        "low_code": low["code"],
                        "high_code": high["code"],
                        "valid": True,
                        "reason": "BRACKETED",
                    }
                )
                newly_bracketed.append(target)
        unresolved.difference_update(newly_bracketed)
        if not unresolved:
            break

    active = {
        target
        for target, state in states.items()
        if state["valid"] and state["high_v"] > state["low_v"]
    }
    for round_index in range(16):
        pending = [
            target
            for target in active
            if (states[target]["high_v"] - states[target]["low_v"]) / LSB_DIFF_V
            > FINAL_WIDTH_LSB
        ]
        if not pending:
            break
        bulk_points = []
        strict_points = []
        for target in sorted(pending):
            state = states[target]
            width_lsb = (state["high_v"] - state["low_v"]) / LSB_DIFF_V
            point = {
                "target": target,
                "role": "mid",
                "vid_v": 0.5 * (state["low_v"] + state["high_v"]),
            }
            if width_lsb <= 0.08:
                strict_points.append(point)
            else:
                bulk_points.append(point)
        values = {}
        values.update(
            evaluate_points(
                campaign,
                pvt_name,
                direction,
                f"bis{round_index:02d}_bulk",
                bulk_points,
                BULK_MAXSTEP_S,
                grouped,
                runtime_rows,
                evaluation_rows,
                mismatch_seed,
                shard_size,
            )
        )
        values.update(
            evaluate_points(
                campaign,
                pvt_name,
                direction,
                f"bis{round_index:02d}_strict",
                strict_points,
                STRICT_MAXSTEP_S,
                grouped,
                runtime_rows,
                evaluation_rows,
                mismatch_seed,
                shard_size,
            )
        )
        for target in pending:
            state = states[target]
            value = values.get((target, "mid"))
            state["bisection_rounds"] += 1
            if value is None:
                state["valid"] = False
                state["reason"] = "INVALID_BISECTION_POINT"
                active.discard(target)
                continue
            if value["code"] < target:
                state["low_v"] = value["vid_v"]
                state["low_code"] = value["code"]
            else:
                state["high_v"] = value["vid_v"]
                state["high_code"] = value["code"]

    rows = []
    for target in sorted(states):
        state = states[target]
        width_lsb = (
            (state["high_v"] - state["low_v"]) / LSB_DIFF_V
            if state["low_v"] is not None and state["high_v"] is not None
            else float("inf")
        )
        passed = state["valid"] and width_lsb <= FINAL_WIDTH_LSB
        rows.append(
            {
                "pvt": pvt_name,
                "mismatch_seed": mismatch_seed,
                "direction": direction,
                "target_transition": target,
                "lower_v": state["low_v"],
                "upper_v": state["high_v"],
                "transition_v": (
                    0.5 * (state["low_v"] + state["high_v"])
                    if state["low_v"] is not None and state["high_v"] is not None
                    else None
                ),
                "lower_code": state["low_code"],
                "upper_code": state["high_code"],
                "final_bracket_width_lsb": width_lsb,
                "expansion_rounds": state["expansion_rounds"],
                "bisection_rounds": state["bisection_rounds"],
                "final_two_rounds_maxstep_s": STRICT_MAXSTEP_S,
                "status": "PASS" if passed else "FAIL",
                "reason": state["reason"],
            }
        )
    return rows


def static_metrics(transition_rows):
    passed = [row for row in transition_rows if row["status"] == "PASS"]
    if len(passed) != len(transition_rows):
        return {"status": "FAIL_SEARCH", "rows": [], "transition_count": len(passed)}
    targets = np.asarray([row["target_transition"] for row in passed], dtype=float)
    transitions = np.asarray([row["transition_v"] for row in passed], dtype=float)
    if len(targets) != 255:
        return {"status": "PARTIAL", "rows": [], "transition_count": len(targets)}
    endpoint_lsb = (transitions[-1] - transitions[0]) / 254.0
    widths = np.diff(transitions)
    dnl = widths / endpoint_lsb - 1.0
    endpoint_ideal = transitions[0] + (targets - 1.0) * endpoint_lsb
    inl_ep = (transitions - endpoint_ideal) / endpoint_lsb
    slope, intercept = np.polyfit(targets, transitions, 1)
    best_fit = intercept + slope * targets
    inl_bf = (transitions - best_fit) / slope
    rows = []
    for index, (target, transition, ep, bf) in enumerate(
        zip(targets.astype(int), transitions, inl_ep, inl_bf)
    ):
        rows.append(
            {
                "target_transition": int(target),
                "transition_v": transition,
                "endpoint_lsb_v": endpoint_lsb,
                "best_fit_lsb_v": slope,
                "dnl_to_next_lsb": dnl[index] if index < len(dnl) else None,
                "inl_endpoint_lsb": ep,
                "inl_best_fit_lsb": bf,
            }
        )
    max_abs_dnl = float(np.max(np.abs(dnl)))
    max_abs_inl_ep = float(np.max(np.abs(inl_ep)))
    max_abs_inl_bf = float(np.max(np.abs(inl_bf)))
    worst_dnl_index = int(np.argmax(np.abs(dnl)))
    worst_inl_index = int(np.argmax(np.abs(inl_ep)))
    missing_codes = int(np.count_nonzero(widths <= 0.0))
    status = "PASS" if all(
        (
            max_abs_dnl <= 1.0,
            max_abs_inl_ep <= 1.5,
            missing_codes == 0,
        )
    ) else "FAIL"
    return {
        "status": status,
        "transition_count": len(targets),
        "endpoint_lsb_v": endpoint_lsb,
        "best_fit_lsb_v": slope,
        "max_abs_dnl_lsb": max_abs_dnl,
        "max_abs_inl_endpoint_lsb": max_abs_inl_ep,
        "max_abs_inl_best_fit_lsb": max_abs_inl_bf,
        "missing_codes": missing_codes,
        "worst_dnl_width_lower_transition": int(targets[worst_dnl_index]),
        "worst_dnl_width_upper_transition": int(targets[worst_dnl_index + 1]),
        "worst_inl_transition": int(targets[worst_inl_index]),
        "rows": rows,
    }


def plot_metrics(metrics, prefix, title):
    targets = [row["target_transition"] for row in metrics["rows"]]
    dnl_targets = targets[:-1]
    dnl = [row["dnl_to_next_lsb"] for row in metrics["rows"][:-1]]
    inl_ep = [row["inl_endpoint_lsb"] for row in metrics["rows"]]
    inl_bf = [row["inl_best_fit_lsb"] for row in metrics["rows"]]
    plt.figure(figsize=(9, 4.8))
    plt.plot(dnl_targets, dnl, color="#1565c0", linewidth=1.2)
    plt.axhline(1.0, color="#c62828", linestyle="--", linewidth=0.9)
    plt.axhline(-1.0, color="#c62828", linestyle="--", linewidth=0.9)
    plt.xlabel("Lower transition index")
    plt.ylabel("DNL (LSB)")
    plt.title(f"{title} DNL")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / f"dnl_{prefix}.png", dpi=160)
    plt.close()
    plt.figure(figsize=(9, 4.8))
    plt.plot(targets, inl_ep, label="Endpoint", color="#2e7d32", linewidth=1.2)
    plt.plot(targets, inl_bf, label="Best fit", color="#6a1b9a", linewidth=1.0)
    plt.axhline(1.5, color="#c62828", linestyle="--", linewidth=0.9)
    plt.axhline(-1.5, color="#c62828", linestyle="--", linewidth=0.9)
    plt.xlabel("Transition index")
    plt.ylabel("INL (LSB)")
    plt.title(f"{title} INL")
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / f"inl_{prefix}.png", dpi=160)
    plt.close()


def run_ramp(grouped, runtime_rows):
    up_vids = np.linspace(
        -FULL_SCALE_DIFF_V / 2.0 + 0.5 * LSB_DIFF_V,
        FULL_SCALE_DIFF_V / 2.0 - 0.5 * LSB_DIFF_V,
        256,
    )
    down_vids = up_vids[::-1]
    vids = np.concatenate((up_vids, down_vids))
    stem = "tt_nominal_triangular_ramp_512"
    result = run_frames(
        stem,
        {"kind": "linear_sequence", "vid_values": vids},
        len(vids),
        JOB_DIR,
        LOG_DIR,
        frame_s=FRAME_DEFAULT_S,
        maxstep_s=BULK_MAXSTEP_S,
        pvt_name=TT_PVT,
        grouped_weights=grouped,
        timeout_s=1800,
    )
    runtime_rows.append(
        {
            "campaign": "ramp",
            "pvt": TT_PVT,
            "direction": "up_down",
            "round": "continuous_512",
            "job": stem,
            "points": len(vids),
            "maxstep_s": BULK_MAXSTEP_S,
            "elapsed_s": result["elapsed_s"],
            "cached": result.get("cached", False),
            "returncode": result["returncode"],
        }
    )
    rows = []
    for index, (vid, frame) in enumerate(zip(vids, result["frames"])):
        direction = "up" if index < 256 else "down"
        rows.append(
            {
                "frame_index": index,
                "direction": direction,
                "commanded_vid_v": vid,
                "code": frame["code"],
                "valid": frame["valid"],
                "sampled_diff_v": frame["sampled_diff_v"],
            }
        )
    up_codes = [row["code"] for row in rows[:256]]
    down_codes = [row["code"] for row in rows[256:]]
    status = "PASS" if all(
        (
            all(row["valid"] for row in rows),
            all(left <= right for left, right in zip(up_codes, up_codes[1:])),
            all(left >= right for left, right in zip(down_codes, down_codes[1:])),
            len(set(up_codes + down_codes)) == 256,
        )
    ) else "FAIL"
    return rows, {
        "status": status,
        "all_frames_valid": all(row["valid"] for row in rows),
        "up_monotonic": all(left <= right for left, right in zip(up_codes, up_codes[1:])),
        "down_monotonic": all(left >= right for left, right in zip(down_codes, down_codes[1:])),
        "code_coverage": len(set(up_codes + down_codes)),
        "up_endpoint_codes": [up_codes[0], up_codes[-1]],
        "down_endpoint_codes": [down_codes[0], down_codes[-1]],
    }


def main():
    ensure_directories(
        JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR, PLOT_DIR
    )
    grouped = load_cdac_weights()
    runtime_rows = []
    evaluation_rows = []

    tt_up = exact_search(
        "tt_full", TT_PVT, "up", list(range(1, 256)), grouped, runtime_rows, evaluation_rows
    )
    tt_down = exact_search(
        "tt_full", TT_PVT, "down", list(range(1, 256)), grouped, runtime_rows, evaluation_rows
    )
    pvt_up = exact_search(
        "pvt_full", WORST_PVT, "up", list(range(1, 256)), grouped, runtime_rows, evaluation_rows
    )
    tt_metrics = static_metrics(tt_up)
    pvt_metrics = static_metrics(pvt_up)

    selected_down_targets = sorted(
        {
            32,
            64,
            128,
            192,
            224,
            pvt_metrics.get("worst_dnl_width_lower_transition", 128),
            pvt_metrics.get("worst_dnl_width_upper_transition", 129),
            pvt_metrics.get("worst_inl_transition", 128),
        }
    )
    pvt_down_selected = exact_search(
        "pvt_selected",
        WORST_PVT,
        "down",
        selected_down_targets,
        grouped,
        runtime_rows,
        evaluation_rows,
    )
    pvt_up_lookup = {row["target_transition"]: row for row in pvt_up}
    selected_hysteresis = [
        {
            "target_transition": row["target_transition"],
            "up_transition_v": pvt_up_lookup[row["target_transition"]]["transition_v"],
            "down_transition_v": row["transition_v"],
            "delta_lsb": abs(
                pvt_up_lookup[row["target_transition"]]["transition_v"]
                - row["transition_v"]
            )
            / LSB_DIFF_V,
            "status": (
                "PASS"
                if row["status"] == "PASS"
                and pvt_up_lookup[row["target_transition"]]["status"] == "PASS"
                else "FAIL"
            ),
        }
        for row in pvt_down_selected
    ]
    selected_hysteresis_max = max(row["delta_lsb"] for row in selected_hysteresis)
    full_pvt_down_triggered = selected_hysteresis_max > 0.10
    pvt_down_full = None
    if full_pvt_down_triggered:
        pvt_down_full = exact_search(
            "pvt_full",
            WORST_PVT,
            "down",
            list(range(1, 256)),
            grouped,
            runtime_rows,
            evaluation_rows,
        )

    tt_down_lookup = {row["target_transition"]: row for row in tt_down}
    tt_hysteresis = [
        abs(row["transition_v"] - tt_down_lookup[row["target_transition"]]["transition_v"])
        / LSB_DIFF_V
        for row in tt_up
    ]
    ramp_rows, ramp_summary = run_ramp(grouped, runtime_rows)

    write_csv(CSV_DIR / "transitions_tt_nominal_up.csv", tt_up)
    write_csv(CSV_DIR / "transitions_tt_nominal_down.csv", tt_down)
    write_csv(CSV_DIR / "transitions_pvt_worst_up.csv", pvt_up)
    write_csv(CSV_DIR / "transitions_pvt_worst_down_selected.csv", pvt_down_selected)
    if pvt_down_full is not None:
        write_csv(CSV_DIR / "transitions_pvt_worst_down.csv", pvt_down_full)
    write_csv(CSV_DIR / "dnl_inl_tt_nominal.csv", tt_metrics.get("rows", []))
    write_csv(CSV_DIR / "dnl_inl_pvt_worst.csv", pvt_metrics.get("rows", []))
    write_csv(CSV_DIR / "exact_static_evaluations.csv", evaluation_rows)
    write_csv(CSV_DIR / "exact_static_runtime.csv", runtime_rows)
    write_csv(CSV_DIR / "ramp_correlation_tt_nominal.csv", ramp_rows)
    write_csv(CSV_DIR / "pvt_selected_hysteresis.csv", selected_hysteresis)

    if tt_metrics.get("rows"):
        plot_metrics(tt_metrics, "tt_nominal", "TT nominal")
    if pvt_metrics.get("rows"):
        plot_metrics(pvt_metrics, "pvt_worst", f"{WORST_PVT} static worst")

    search_pass = all(
        row["status"] == "PASS" for row in tt_up + tt_down + pvt_up + pvt_down_selected
    )
    if pvt_down_full is not None:
        search_pass = search_pass and all(row["status"] == "PASS" for row in pvt_down_full)
    overall_status = "PASS" if all(
        (
            search_pass,
            tt_metrics.get("status") == "PASS",
            pvt_metrics.get("status") == "PASS",
            ramp_summary["status"] == "PASS",
            max(tt_hysteresis) <= 0.10,
            selected_hysteresis_max <= 0.10 or full_pvt_down_triggered,
        )
    ) else "FAIL"
    payload = {
        "status": overall_status,
        "tt_metrics": {key: value for key, value in tt_metrics.items() if key != "rows"},
        "pvt_metrics": {key: value for key, value in pvt_metrics.items() if key != "rows"},
        "tt_max_hysteresis_lsb": max(tt_hysteresis),
        "pvt_selected_max_hysteresis_lsb": selected_hysteresis_max,
        "pvt_full_down_triggered": full_pvt_down_triggered,
        "pvt_selected_down_targets": selected_down_targets,
        "ramp": ramp_summary,
        "runtime_fresh_s": sum(row["elapsed_s"] for row in runtime_rows),
        "runtime_job_count": len(runtime_rows),
        "max_workers": MAX_WORKERS,
        "shard_size": SHARD_SIZE,
    }
    (RESULT_DIR / "exact_static.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )

    lines = [
        "# Exact Static Characterization",
        "",
        f"- Status: `{overall_status}`",
        f"- TT full up/down transitions: `{sum(row['status'] == 'PASS' for row in tt_up)}/255` / `{sum(row['status'] == 'PASS' for row in tt_down)}/255`",
        f"- {WORST_PVT} full up transitions: `{sum(row['status'] == 'PASS' for row in pvt_up)}/255`",
        f"- Final bracket requirement: `<= {FINAL_WIDTH_LSB:.2f} LSB`",
        f"- TT max up/down delta: `{max(tt_hysteresis):.6f} LSB`",
        f"- PVT selected max up/down delta: `{selected_hysteresis_max:.6f} LSB`",
        f"- PVT full down triggered: `{full_pvt_down_triggered}`",
        f"- Triangular-ramp code coverage: `{ramp_summary['code_coverage']}/256`",
        "",
        "## Static Metrics",
        "",
        "| Curve | Max |DNL| | Max |INL EP| | Max |INL BF| | Missing | QEP (mV) | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for label, metrics in (("TT nominal", tt_metrics), (WORST_PVT, pvt_metrics)):
        lines.append(
            f"| {label} | {metrics.get('max_abs_dnl_lsb', float('nan')):.6f} | "
            f"{metrics.get('max_abs_inl_endpoint_lsb', float('nan')):.6f} | "
            f"{metrics.get('max_abs_inl_best_fit_lsb', float('nan')):.6f} | "
            f"{metrics.get('missing_codes', -1)} | "
            f"{metrics.get('endpoint_lsb_v', float('nan')) * 1e3:.6f} | "
            f"{metrics.get('status')} |"
        )
    lines.extend(
        (
            "",
            "## Ramp Correlation",
            "",
            f"- Status: `{ramp_summary['status']}`",
            f"- Up monotonic: `{ramp_summary['up_monotonic']}`",
            f"- Down monotonic: `{ramp_summary['down_monotonic']}`",
            f"- Code coverage: `{ramp_summary['code_coverage']}/256`",
            "",
        )
    )
    (REPORT_DIR / "static_exact.md").write_text(
        "\n".join(lines), encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": overall_status,
                "tt_max_abs_dnl": tt_metrics.get("max_abs_dnl_lsb"),
                "tt_max_abs_inl": tt_metrics.get("max_abs_inl_endpoint_lsb"),
                "pvt_max_abs_dnl": pvt_metrics.get("max_abs_dnl_lsb"),
                "pvt_max_abs_inl": pvt_metrics.get("max_abs_inl_endpoint_lsb"),
                "ramp_status": ramp_summary["status"],
                "fresh_runtime_s": payload["runtime_fresh_s"],
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if overall_status == "PASS" else 2)


if __name__ == "__main__":
    main()
