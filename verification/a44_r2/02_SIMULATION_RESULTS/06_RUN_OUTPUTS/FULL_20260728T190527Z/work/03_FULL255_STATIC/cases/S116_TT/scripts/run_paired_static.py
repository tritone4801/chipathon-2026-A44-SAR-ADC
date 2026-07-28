#!/usr/bin/env python3
"""Run one frozen current-resizing full-code static case.

The user explicitly excluded symmetric strict replay and dense scans. This
runner uses one frozen 50 ps profile throughout and never schedules either.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

import sar_campaign_common as common


ROOT = Path(__file__).resolve().parents[1]
CASE_CONFIG = json.loads(
    (ROOT / "config" / "current_static_case.json").read_text(encoding="utf-8")
)
SEED = int(CASE_CONFIG["mismatch_seed"])
PVT = str(CASE_CONFIG["pvt"])
MAXSTEP_S = 50e-12
FINAL_WIDTH_LSB = 0.02
SHARD_SIZE = 32
MAX_WORKERS = 2
TIMEOUT_S = 7200
LSB = common.LSB_DIFF_V
VARIANTS = {
    "CURRENT": ROOT
    / "netlists"
    / "candidate"
    / "Comparator_StrongARM_CURRENT.subckt.spice",
}
PILOT_TARGETS = (
    1,
    2,
    16,
    31,
    32,
    33,
    48,
    63,
    64,
    65,
    80,
    95,
    96,
    97,
    112,
    127,
    128,
    129,
    144,
    159,
    160,
    161,
    176,
    190,
    191,
    192,
    193,
    208,
    223,
    224,
    225,
    255,
)
QUAL_TARGETS = (1, 64, 128, 192, 255)
EXPANSION_HALF_WIDTHS_LSB = (0.75, 2.0, 4.0, 8.0, 16.0)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def append_runtime(rows: list[dict[str, Any]]) -> None:
    path = ROOT / "csv" / "runtime_resource_trace.csv"
    old = read_csv(path)
    keyed: dict[str, dict[str, Any]] = {row["job"]: row for row in old}
    for row in rows:
        keyed[str(row["job"])] = row
    write_csv(path, list(keyed.values()))


def chunks(values: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def ideal_center(target: int) -> float:
    return -common.FULL_SCALE_DIFF_V / 2.0 + target * LSB


def build_variant_deck(
    variant: str,
    vids: list[float],
    *,
    kind: str = "static_sequence",
    instrument_protocol: bool = False,
) -> str:
    deck = common.build_deck(
        input_spec={"kind": kind, "vid_values": vids},
        total_frames=len(vids),
        frame_s=common.FRAME_DEFAULT_S,
        maxstep_s=MAXSTEP_S,
        pvt_name=PVT,
        mismatch_seed=SEED,
        grouped_weights=common.load_cdac_weights(),
        comparator_path=VARIANTS[variant],
    )
    if not instrument_protocol:
        return deck
    save_anchor = ".control\n"
    protocol_save = "\n".join(
        (
            ".save v(dctrlp7) v(dctrlp6) v(dctrlp5) v(dctrlp4) v(dctrlp3) v(dctrlp2) v(dctrlp1)",
            "+ v(dctrln7) v(dctrln6) v(dctrln5) v(dctrln4) v(dctrln3) v(dctrln2) v(dctrln1)",
        )
    )
    if deck.count(save_anchor) != 1:
        raise RuntimeError("unexpected .control count")
    deck = deck.replace(save_anchor, protocol_save + "\n" + save_anchor, 1)
    measures: list[str] = []
    for frame in range(len(vids)):
        at_s = frame * common.FRAME_DEFAULT_S + 470e-9
        for bit in range(7, -1, -1):
            measures.append(
                f"meas tran q_f{frame:03d}_d{bit}_470 "
                f"find v(dout{bit}_rx) at={at_s:.12g}"
            )
    anchor = "\nquit\n.endc"
    if deck.count(anchor) != 1:
        raise RuntimeError("unexpected quit count")
    return deck.replace(anchor, "\n" + "\n".join(measures) + anchor, 1)


def point_vid_sequence(points: list[dict[str, Any]], frames_per_point: int) -> list[float]:
    vids: list[float] = []
    for point in points:
        vids.extend([float(point["vid_v"])] * frames_per_point)
    return vids


def run_shard(
    *,
    variant: str,
    label: str,
    shard_index: int,
    points: list[dict[str, Any]],
    frames_per_point: int,
    retry: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    vids = point_vid_sequence(points, frames_per_point)
    stem = (
        f"{variant.lower()}_{label}_f{frames_per_point}_sh{shard_index:03d}"
        + ("_retry" if retry else "")
    )
    started = utc_now()
    result = common.run_deck(
        build_variant_deck(variant, vids),
        stem,
        ROOT / "generated" / "jobs" / label,
        ROOT / "logs" / label,
        timeout_s=TIMEOUT_S,
    )
    frames = common.decode_frames(
        result, len(vids), common.PVT_CASES[PVT]["vdd_v"], common.FRAME_DEFAULT_S
    )
    output: list[dict[str, Any]] = []
    for point_index, point in enumerate(points):
        start = point_index * frames_per_point
        selected = frames[start : start + frames_per_point]
        formal = selected[-1]
        output.append(
            {
                **point,
                "variant": variant,
                "label": label,
                "frames_per_point": frames_per_point,
                "conditioning_codes": "/".join(
                    str(frame["code"]) for frame in selected[:-1]
                ),
                "formal_code": formal["code"],
                "all_frames_valid": all(frame["valid"] for frame in selected),
                "formal_valid": formal["valid"],
                "formal_bits": formal["bits"],
                "formal_complete_v": formal["complete_v"],
                "formal_invalid_v": formal["invalid_v"],
                "formal_timeout_v": formal["timeout_v"],
                "formal_complete_time_s": formal["complete_time_s"],
                "formal_stable_margin_ns": formal["stable_margin_s"] * 1e9,
                "sampled_diff_v": formal["sampled_diff_v"],
                "input_diff_v": formal["input_diff_v"],
                "job": stem,
            }
        )
    runtime = {
        "utc_started": started,
        "job": stem,
        "variant": variant,
        "stage": label,
        "points": len(points),
        "frames": len(vids),
        "frames_per_point": frames_per_point,
        "maxstep_ps": 50,
        "elapsed_s": result["elapsed_s"],
        "peak_rss_kb": result["peak_rss_kb"],
        "returncode": result["returncode"],
        "cached": result["cached"],
        "timed_out": result["timed_out"],
        "simulation_aborted": result["simulation_aborted"],
        "retry": retry,
    }
    return output, runtime


def evaluate_points(
    *,
    variant: str,
    label: str,
    points: list[dict[str, Any]],
    frames_per_point: int,
    shard_size: int = SHARD_SIZE,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not points:
        return {}, [], []
    shards = list(chunks(points, shard_size))
    rows: list[dict[str, Any]] = []
    runtimes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(shards))) as executor:
        futures = [
            executor.submit(
                run_shard,
                variant=variant,
                label=label,
                shard_index=index,
                points=shard,
                frames_per_point=frames_per_point,
            )
            for index, shard in enumerate(shards)
        ]
        for future in as_completed(futures):
            shard_rows, runtime = future.result()
            rows.extend(shard_rows)
            runtimes.append(runtime)
    failed = [row for row in rows if not row["all_frames_valid"]]
    if failed:
        retry_points = [
            {
                key: row[key]
                for key in ("point_id", "target", "role", "vid_v")
                if key in row
            }
            for row in failed
        ]
        retry_rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(retry_points))
        ) as executor:
            futures = [
                executor.submit(
                    run_shard,
                    variant=variant,
                    label=label,
                    shard_index=1000 + index,
                    points=[point],
                    frames_per_point=frames_per_point,
                    retry=True,
                )
                for index, point in enumerate(retry_points)
            ]
            for future in as_completed(futures):
                one_rows, runtime = future.result()
                retry_rows.extend(one_rows)
                runtimes.append(runtime)
        retry_lookup = {row["point_id"]: row for row in retry_rows}
        rows = [
            retry_lookup.get(row["point_id"], row)
            if not row["all_frames_valid"]
            else row
            for row in rows
        ]
    append_runtime(runtimes)
    return {str(row["point_id"]): row for row in rows}, rows, runtimes


def search_transitions(
    *,
    variant: str,
    stage: str,
    targets: Iterable[int],
    centers: dict[int, float],
    frames_per_point: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    states: dict[int, dict[str, Any]] = {
        int(target): {
            "target": int(target),
            "center_v": float(centers[int(target)]),
            "lower_v": None,
            "upper_v": None,
            "lower_code": None,
            "upper_code": None,
            "expansion_half_width_lsb": None,
            "bisection_rounds": 0,
            "valid": False,
            "reason": "NOT_BRACKETED",
        }
        for target in targets
    }
    evaluations: list[dict[str, Any]] = []
    unresolved = set(states)
    for expansion_index, half_width_lsb in enumerate(EXPANSION_HALF_WIDTHS_LSB):
        points: list[dict[str, Any]] = []
        for target in sorted(unresolved):
            center = states[target]["center_v"]
            for role, sign in (("low", -1.0), ("high", 1.0)):
                points.append(
                    {
                        "point_id": f"t{target:03d}_{role}",
                        "target": target,
                        "role": role,
                        "vid_v": center + sign * half_width_lsb * LSB,
                    }
                )
        values, rows, _ = evaluate_points(
            variant=variant,
            label=f"{stage}_expand{expansion_index}",
            points=points,
            frames_per_point=frames_per_point,
        )
        evaluations.extend(rows)
        newly: list[int] = []
        for target in sorted(unresolved):
            low = values.get(f"t{target:03d}_low")
            high = values.get(f"t{target:03d}_high")
            if low is None or high is None:
                states[target]["reason"] = "MISSING_EVALUATION"
                continue
            if not low["all_frames_valid"] or not high["all_frames_valid"]:
                states[target]["reason"] = "INVALID_EXPANSION_SAMPLE"
                continue
            if low["formal_code"] < target and high["formal_code"] >= target:
                states[target].update(
                    {
                        "lower_v": low["vid_v"],
                        "upper_v": high["vid_v"],
                        "lower_code": low["formal_code"],
                        "upper_code": high["formal_code"],
                        "expansion_half_width_lsb": half_width_lsb,
                        "valid": True,
                        "reason": "BRACKETED",
                    }
                )
                newly.append(target)
        unresolved.difference_update(newly)
        if not unresolved:
            break
    for round_index in range(12):
        pending = [
            target
            for target, state in states.items()
            if state["valid"]
            and (state["upper_v"] - state["lower_v"]) / LSB > FINAL_WIDTH_LSB
        ]
        if not pending:
            break
        points = [
            {
                "point_id": f"t{target:03d}_mid",
                "target": target,
                "role": "mid",
                "vid_v": 0.5
                * (states[target]["lower_v"] + states[target]["upper_v"]),
            }
            for target in sorted(pending)
        ]
        values, rows, _ = evaluate_points(
            variant=variant,
            label=f"{stage}_bis{round_index:02d}",
            points=points,
            frames_per_point=frames_per_point,
        )
        evaluations.extend(rows)
        for target in pending:
            state = states[target]
            row = values.get(f"t{target:03d}_mid")
            state["bisection_rounds"] += 1
            if row is None or not row["all_frames_valid"]:
                state["valid"] = False
                state["reason"] = "INVALID_BISECTION_SAMPLE"
                continue
            if row["formal_code"] < target:
                state["lower_v"] = row["vid_v"]
                state["lower_code"] = row["formal_code"]
            else:
                state["upper_v"] = row["vid_v"]
                state["upper_code"] = row["formal_code"]
    output: list[dict[str, Any]] = []
    for target in sorted(states):
        state = states[target]
        if state["lower_v"] is not None and state["upper_v"] is not None:
            width_lsb = (state["upper_v"] - state["lower_v"]) / LSB
            midpoint = 0.5 * (state["lower_v"] + state["upper_v"])
        else:
            width_lsb = math.inf
            midpoint = math.nan
        passed = state["valid"] and width_lsb <= FINAL_WIDTH_LSB
        output.append(
            {
                "variant": variant,
                "mismatch_seed": SEED,
                "target_transition": target,
                "lower_v": state["lower_v"],
                "upper_v": state["upper_v"],
                "transition_v": midpoint,
                "lower_code": state["lower_code"],
                "upper_code": state["upper_code"],
                "final_bracket_width_lsb": width_lsb,
                "center_v": state["center_v"],
                "expansion_half_width_lsb": state["expansion_half_width_lsb"],
                "bisection_rounds": state["bisection_rounds"],
                "frames_per_point": frames_per_point,
                "maxstep_ps": 50,
                "status": "PASS" if passed else "FAIL",
                "reason": state["reason"],
            }
        )
    return output, evaluations


def protocol_raw_audit(
    variant: str,
    frames_per_point: int,
    vids: list[float],
) -> dict[str, Any]:
    from spicelib import RawRead

    expanded: list[float] = []
    for vid in vids:
        expanded.extend([vid] * frames_per_point)
    label = f"conditioning_protocol_{variant.lower()}_f{frames_per_point}"
    raw_path = ROOT / "generated" / "raw" / f"{label}.raw"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    deck = build_variant_deck(
        variant, expanded, instrument_protocol=True
    )
    write_anchor = "\nquit\n.endc"
    raw_traces = " ".join(
        ["v(cmpck)"]
        + [f"v(dctrlp{bit})" for bit in range(7, 0, -1)]
        + [f"v(dctrln{bit})" for bit in range(7, 0, -1)]
    )
    if deck.count(write_anchor) != 1:
        raise RuntimeError("unexpected protocol raw write anchor")
    deck = deck.replace(
        write_anchor,
        f"\nwrite {raw_path} {raw_traces}" + write_anchor,
        1,
    )
    result = common.run_deck(
        deck,
        label,
        ROOT / "generated" / "jobs" / "conditioning_protocol",
        ROOT / "logs" / "conditioning_protocol",
        timeout_s=TIMEOUT_S,
    )
    frames = common.decode_frames(
        result,
        len(expanded),
        common.PVT_CASES[PVT]["vdd_v"],
        common.FRAME_DEFAULT_S,
    )
    raw = RawRead(raw_path, verbose=False)
    names = {name.lower(): name for name in raw.get_trace_names()}

    def wave(name: str) -> np.ndarray:
        key = names.get(name.lower())
        if key is None:
            raise KeyError(f"raw trace absent: {name}; available={list(names)[:20]}")
        return np.asarray(raw.get_trace(key).get_wave(), dtype=float)

    # Some spicelib builds do not attach the RAW time trace as the plot axis
    # when ngspice writes an explicit trace list. The time vector is still
    # present as a normal trace and is authoritative.
    times = wave("time")
    cmpck = wave("v(cmpck)")
    threshold = 1.65
    cmp_rise_times = times[1:][(cmpck[:-1] < threshold) & (cmpck[1:] >= threshold)]
    timing = read_json(ROOT / "config" / "timing_tt_3p3_27c.json")
    cmpck_high = {
        bit: float(timing["cmpck_high"][7 - bit]) for bit in range(8)
    }
    cmpck_low = {
        bit: float(timing["cmpck_low_guard_bits_7_to_1"][7 - bit])
        for bit in range(1, 8)
    }
    dctrl_edges: list[float] = []
    for side in ("p", "n"):
        for bit in range(7, 0, -1):
            values = wave(f"v(dctrl{side}{bit})")
            changed = (values[:-1] < threshold) != (values[1:] < threshold)
            dctrl_edges.extend(times[1:][changed].tolist())
    dctrl_edges.sort()
    rows = []
    protocol_pass = True
    vdd = common.PVT_CASES[PVT]["vdd_v"]
    measures = result["measures"]
    for frame_index, frame in enumerate(frames):
        start = frame_index * common.FRAME_DEFAULT_S
        stop = (frame_index + 1) * common.FRAME_DEFAULT_S
        cmp_count = int(np.count_nonzero((cmp_rise_times >= start) & (cmp_rise_times < stop)))
        local_edges = [
            value for value in dctrl_edges if start <= value < stop
        ]
        clusters: list[float] = []
        for value in local_edges:
            if not clusters or value - clusters[-1] > 1e-9:
                clusters.append(value)
        update_observation_s: dict[int, float] = {}
        rise_s = (
            start
            + common.TRACK_FALL_OFFSET_S
            + float(timing["t_clks_fall_to_first_cmpck_rise"]) * 1e-9
        )
        for bit in range(7, 0, -1):
            update_observation_s[bit] = (
                rise_s + (cmpck_high[bit] + cmpck_low[bit] - 1.0) * 1e-9
            )
            rise_s += (cmpck_high[bit] + cmpck_low[bit]) * 1e-9
        dctrl_valid_updates = 0
        dctrl_samples: list[str] = []
        for bit in range(7, 0, -1):
            at_s = update_observation_s[bit]
            p = float(np.interp(at_s, times, wave(f"v(dctrlp{bit})")))
            n = float(np.interp(at_s, times, wave(f"v(dctrln{bit})")))
            valid_update = (p > threshold and n < threshold) or (
                p < threshold and n > threshold
            )
            dctrl_valid_updates += int(valid_update)
            dctrl_samples.append(f"{bit}:{p:.9g}/{n:.9g}")
        bits_470 = []
        for bit in range(7, -1, -1):
            value = measures.get(f"q_f{frame_index:03d}_d{bit}_470", math.nan)
            bits_470.append(int(math.isfinite(value) and value > vdd / 2.0))
        code_470 = sum(bit << (7 - offset) for offset, bit in enumerate(bits_470))
        stable = code_470 == frame["code"]
        row_pass = all(
            (
                frame["valid"],
                cmp_count == 8,
                dctrl_valid_updates == 7,
                stable,
            )
        )
        protocol_pass = protocol_pass and row_pass
        rows.append(
            {
                "variant": variant,
                "frames_per_point": frames_per_point,
                "frame_index": frame_index,
                "point_index": frame_index // frames_per_point,
                "frame_role": (
                    "FORMAL"
                    if frame_index % frames_per_point == frames_per_point - 1
                    else (
                        "CONDITIONING"
                        if frame_index % frames_per_point == frames_per_point - 2
                        else "COLD_DISCARD"
                    )
                ),
                "vid_v": expanded[frame_index],
                "code_470": code_470,
                "code_480": frame["code"],
                "dout_stable_470_480": stable,
                "comparator_rise_count": cmp_count,
                "dctrl_valid_update_count": dctrl_valid_updates,
                "dctrl_edge_cluster_count_diagnostic_only": len(clusters),
                "dctrl_update_samples_bit_p_n": ";".join(dctrl_samples),
                "complete_v": frame["complete_v"],
                "invalid_v": frame["invalid_v"],
                "timeout_v": frame["timeout_v"],
                "valid": frame["valid"],
                "protocol_pass": row_pass,
            }
        )
    write_csv(
        ROOT
        / "csv"
        / f"conditioning_protocol_{variant.lower()}_f{frames_per_point}.csv",
        rows,
    )
    append_runtime(
        [
            {
                "utc_started": utc_now(),
                "job": label,
                "variant": variant,
                "stage": "conditioning_protocol",
                "points": len(vids),
                "frames": len(expanded),
                "frames_per_point": frames_per_point,
                "maxstep_ps": 50,
                "elapsed_s": result["elapsed_s"],
                "peak_rss_kb": result["peak_rss_kb"],
                "returncode": result["returncode"],
                "cached": result["cached"],
                "timed_out": result["timed_out"],
                "simulation_aborted": result["simulation_aborted"],
                "retry": False,
            }
        ]
    )
    return {
        "variant": variant,
        "frames_per_point": frames_per_point,
        "input_point_count": len(vids),
        "frame_count": len(expanded),
        "all_protocol_frames_pass": protocol_pass,
        "all_measurement_frames_valid": all(row["valid"] for row in rows),
        "comparator_decisions_expected": 8,
        "dctrl_updates_expected": 7,
        "dout_stability_window_ns": [470, 480],
        "raw": str(raw_path.relative_to(ROOT)),
        "log": str(result["log"].relative_to(ROOT)),
    }


def run_qualification() -> dict[str, Any]:
    all_search: dict[str, dict[int, list[dict[str, Any]]]] = {}
    all_eval: list[dict[str, Any]] = []
    centers = {target: ideal_center(target) for target in QUAL_TARGETS}
    for variant in VARIANTS:
        all_search[variant] = {}
        for frames_per_point in (2, 3):
            rows, evaluations = search_transitions(
                variant=variant,
                stage=f"qualification_f{frames_per_point}",
                targets=QUAL_TARGETS,
                centers=centers,
                frames_per_point=frames_per_point,
            )
            all_search[variant][frames_per_point] = rows
            all_eval.extend(evaluations)
            write_csv(
                ROOT
                / "csv"
                / f"qualification_{variant.lower()}_f{frames_per_point}_transitions.csv",
                rows,
            )
    write_csv(ROOT / "csv" / "qualification_evaluations.csv", all_eval)
    shared_vids: list[float] = []
    comparisons: list[dict[str, Any]] = []
    thresholds: dict[tuple[str, int], dict[int, float]] = {}
    two_frame_threshold_pass = True
    three_frame_search_pass = True
    for variant in VARIANTS:
        lookups = {
            frames: {
                int(row["target_transition"]): row
                for row in all_search[variant][frames]
            }
            for frames in (2, 3)
        }
        thresholds[(variant, 2)] = {
            target: float(row["transition_v"])
            for target, row in lookups[2].items()
            if row["status"] == "PASS"
        }
        thresholds[(variant, 3)] = {
            target: float(row["transition_v"])
            for target, row in lookups[3].items()
            if row["status"] == "PASS"
        }
        for target in QUAL_TARGETS:
            row2 = lookups[2][target]
            row3 = lookups[3][target]
            pass2 = row2["status"] == "PASS"
            pass3 = row3["status"] == "PASS"
            delta_lsb = (
                abs(float(row2["transition_v"]) - float(row3["transition_v"])) / LSB
                if pass2 and pass3
                else math.inf
            )
            comparisons.append(
                {
                    "variant": variant,
                    "target_transition": target,
                    "two_frame_status": row2["status"],
                    "three_frame_status": row3["status"],
                    "two_frame_transition_v": row2["transition_v"],
                    "three_frame_transition_v": row3["transition_v"],
                    "abs_delta_lsb": delta_lsb,
                    "threshold_method_pass": pass2
                    and pass3
                    and delta_lsb <= FINAL_WIDTH_LSB,
                }
            )
            two_frame_threshold_pass = two_frame_threshold_pass and (
                pass2 and pass3 and delta_lsb <= FINAL_WIDTH_LSB
            )
            three_frame_search_pass = three_frame_search_pass and pass3
    for target in QUAL_TARGETS:
        available = [
            thresholds[(variant, 2)].get(target)
            for variant in VARIANTS
            if thresholds[(variant, 2)].get(target) is not None
        ]
        center = float(np.mean(available)) if available else ideal_center(target)
        shared_vids.extend((center - 0.25 * LSB, center + 0.25 * LSB))
    protocol_results = []
    for variant in VARIANTS:
        for frames_per_point in (2, 3):
            protocol_results.append(
                protocol_raw_audit(variant, frames_per_point, shared_vids)
            )
    two_frame_protocol_pass = all(
        result["all_protocol_frames_pass"]
        for result in protocol_results
        if result["frames_per_point"] == 2
    )
    three_frame_protocol_pass = all(
        result["all_protocol_frames_pass"]
        for result in protocol_results
        if result["frames_per_point"] == 3
    )
    if two_frame_threshold_pass and two_frame_protocol_pass:
        selected_frames = 2
        status = "PASS_TWO_FRAME"
    elif three_frame_search_pass and three_frame_protocol_pass:
        selected_frames = 3
        status = "PASS_THREE_FRAME_FALLBACK"
    else:
        selected_frames = None
        status = "FAIL"
    write_csv(ROOT / "csv" / "conditioning_threshold_comparison.csv", comparisons)
    payload = {
        "status": status,
        "selected_frames_per_point": selected_frames,
        "two_frame_threshold_pass": two_frame_threshold_pass,
        "two_frame_protocol_pass": two_frame_protocol_pass,
        "three_frame_search_pass": three_frame_search_pass,
        "three_frame_protocol_pass": three_frame_protocol_pass,
        "threshold_tolerance_lsb": FINAL_WIDTH_LSB,
        "qualification_targets": list(QUAL_TARGETS),
        "shared_protocol_vids_v": shared_vids,
        "protocol_results": protocol_results,
        "completed_utc": utc_now(),
    }
    write_json(ROOT / "results" / "conditioning_method_qualification.json", payload)
    write_json(
        ROOT / "config" / "frame_method_resolution.json",
        {
            "status": status,
            "frames_per_point": selected_frames,
            "applies_symmetrically_to": list(VARIANTS),
            "source": "results/conditioning_method_qualification.json",
        },
    )
    if selected_frames is None:
        raise SystemExit("conditioning qualification failed")
    return payload


def selected_frames() -> int:
    path = ROOT / "config" / "frame_method_resolution.json"
    if not path.is_file():
        return int(run_qualification()["selected_frames_per_point"])
    payload = read_json(path)
    if payload["frames_per_point"] not in (2, 3):
        raise RuntimeError("invalid frame-method resolution")
    return int(payload["frames_per_point"])


def predicted_centers(anchor_rows: list[dict[str, Any]]) -> dict[int, float]:
    lookup = {int(row["target_transition"]): row for row in anchor_rows}
    if set(lookup) != {1, 128, 255} or any(
        row["status"] != "PASS" for row in lookup.values()
    ):
        raise RuntimeError("anchor search incomplete")
    t1 = float(lookup[1]["transition_v"])
    t255 = float(lookup[255]["transition_v"])
    qrough = (t255 - t1) / 254.0
    return {target: t1 + (target - 1) * qrough for target in range(1, 256)}


def run_pilot() -> dict[str, Any]:
    frames = selected_frames()
    started = time.monotonic()
    summaries: dict[str, Any] = {}
    runtime_before = {
        row["job"]: row for row in read_csv(ROOT / "csv" / "runtime_resource_trace.csv")
    }
    for variant in VARIANTS:
        anchors, eval_anchor = search_transitions(
            variant=variant,
            stage="pilot_anchor",
            targets=(1, 128, 255),
            centers={target: ideal_center(target) for target in (1, 128, 255)},
            frames_per_point=frames,
        )
        centers = predicted_centers(anchors)
        remaining = [target for target in PILOT_TARGETS if target not in (1, 128, 255)]
        rows, evaluations = search_transitions(
            variant=variant,
            stage="pilot_full",
            targets=remaining,
            centers=centers,
            frames_per_point=frames,
        )
        combined = sorted(
            anchors + rows, key=lambda row: int(row["target_transition"])
        )
        write_csv(
            ROOT / "csv" / f"pilot_{variant.lower()}_transitions.csv", combined
        )
        write_csv(
            ROOT / "csv" / f"pilot_{variant.lower()}_evaluations.csv",
            eval_anchor + evaluations,
        )
        summaries[variant] = {
            "transition_count": len(combined),
            "pass_count": sum(row["status"] == "PASS" for row in combined),
            "anchors": anchors,
        }
    runtime_after = {
        row["job"]: row for row in read_csv(ROOT / "csv" / "runtime_resource_trace.csv")
    }
    new_rows = [
        row for job, row in runtime_after.items() if job not in runtime_before
    ]
    elapsed_sum = sum(float(row["elapsed_s"]) for row in new_rows)
    frames_sum = sum(int(float(row["frames"])) for row in new_rows)
    payload = {
        "status": (
            "PASS"
            if all(item["pass_count"] == len(PILOT_TARGETS) for item in summaries.values())
            else "FAIL"
        ),
        "frames_per_point": frames,
        "target_count_per_variant": len(PILOT_TARGETS),
        "targets": list(PILOT_TARGETS),
        "summaries": summaries,
        "wall_elapsed_s": time.monotonic() - started,
        "summed_job_elapsed_s": elapsed_sum,
        "simulated_frames": frames_sum,
        "seconds_per_frame_job_sum": elapsed_sum / frames_sum if frames_sum else None,
        "peak_rss_kb_max": max(
            (int(float(row["peak_rss_kb"])) for row in new_rows), default=0
        ),
        "worker_limit": MAX_WORKERS,
        "packing_size": SHARD_SIZE,
        "completed_utc": utc_now(),
    }
    write_json(ROOT / "results" / "runtime_pilot.json", payload)
    if payload["status"] != "PASS":
        raise SystemExit("runtime pilot did not produce all transitions")
    return payload


def load_pilot(variant: str) -> list[dict[str, Any]]:
    path = ROOT / "csv" / f"pilot_{variant.lower()}_transitions.csv"
    if not path.is_file():
        run_pilot()
    rows = read_csv(path)
    numeric_fields = (
        "target_transition",
        "lower_v",
        "upper_v",
        "transition_v",
        "lower_code",
        "upper_code",
        "final_bracket_width_lsb",
        "center_v",
        "expansion_half_width_lsb",
        "bisection_rounds",
        "frames_per_point",
        "maxstep_ps",
    )
    output = []
    for raw in rows:
        row: dict[str, Any] = dict(raw)
        for field in numeric_fields:
            if row.get(field, "") != "":
                row[field] = float(row[field])
        row["target_transition"] = int(float(row["target_transition"]))
        output.append(row)
    return output


def run_full_transitions() -> dict[str, Any]:
    frames = selected_frames()
    payload: dict[str, Any] = {
        "frames_per_point": frames,
        "variants": {},
        "completed_utc": None,
    }
    for variant in VARIANTS:
        pilot = load_pilot(variant)
        anchors = [
            row for row in pilot if int(row["target_transition"]) in (1, 128, 255)
        ]
        centers = predicted_centers(anchors)
        existing = {int(row["target_transition"]) for row in pilot}
        remaining = [target for target in range(1, 256) if target not in existing]
        rows, evaluations = search_transitions(
            variant=variant,
            stage="full_transition",
            targets=remaining,
            centers=centers,
            frames_per_point=frames,
        )
        combined = sorted(
            pilot + rows, key=lambda row: int(row["target_transition"])
        )
        write_csv(
            ROOT / "csv" / f"{variant.lower()}_s116_transitions_up.csv", combined
        )
        write_csv(
            ROOT / "csv" / f"{variant.lower()}_s116_full_evaluations.csv",
            evaluations,
        )
        payload["variants"][variant] = {
            "transition_count": len(combined),
            "pass_count": sum(row["status"] == "PASS" for row in combined),
            "fail_targets": [
                int(row["target_transition"])
                for row in combined
                if row["status"] != "PASS"
            ],
        }
    payload["status"] = (
        "PASS"
        if all(
            item["transition_count"] == 255 and item["pass_count"] == 255
            for item in payload["variants"].values()
        )
        else "FAIL"
    )
    payload["completed_utc"] = utc_now()
    write_json(ROOT / "results" / "full_transition_execution.json", payload)
    if payload["status"] != "PASS":
        raise SystemExit("full-transition execution incomplete")
    return payload


def load_transition_rows(variant: str) -> list[dict[str, Any]]:
    path = ROOT / "csv" / f"{variant.lower()}_s116_transitions_up.csv"
    if not path.is_file():
        run_full_transitions()
    rows = read_csv(path)
    output: list[dict[str, Any]] = []
    for raw in rows:
        row: dict[str, Any] = dict(raw)
        for field in (
            "target_transition",
            "lower_v",
            "upper_v",
            "transition_v",
            "final_bracket_width_lsb",
        ):
            row[field] = float(row[field])
        row["target_transition"] = int(row["target_transition"])
        output.append(row)
    return output


def run_midpoint_and_overrange() -> dict[str, Any]:
    frames = selected_frames()
    payload: dict[str, Any] = {"frames_per_point": frames, "variants": {}}
    for variant in VARIANTS:
        transitions = load_transition_rows(variant)
        lookup = {row["target_transition"]: row for row in transitions}
        points = []
        for code in range(1, 255):
            midpoint = 0.5 * (
                float(lookup[code]["transition_v"])
                + float(lookup[code + 1]["transition_v"])
            )
            points.append(
                {
                    "point_id": f"code_{code:03d}",
                    "target": code,
                    "role": "midpoint_decode",
                    "vid_v": midpoint,
                }
            )
        _, midpoint_rows, _ = evaluate_points(
            variant=variant,
            label="midpoint_decode",
            points=points,
            frames_per_point=frames,
        )
        for row in midpoint_rows:
            row["expected_code"] = int(row["target"])
            row["decode_pass"] = (
                row["all_frames_valid"]
                and int(row["formal_code"]) == int(row["expected_code"])
            )
        overrange_points = [
            {
                "point_id": "overrange_negative",
                "target": 0,
                "role": "overrange",
                "vid_v": -1.8,
            },
            {
                "point_id": "overrange_positive",
                "target": 255,
                "role": "overrange",
                "vid_v": 1.8,
            },
        ]
        _, overrange_rows, _ = evaluate_points(
            variant=variant,
            label="overrange",
            points=overrange_points,
            frames_per_point=frames,
        )
        for row in overrange_rows:
            row["expected_code"] = int(row["target"])
            row["decode_pass"] = (
                row["all_frames_valid"]
                and int(row["formal_code"]) == int(row["expected_code"])
            )
        write_csv(
            ROOT / "csv" / f"{variant.lower()}_s116_midpoint_decode.csv",
            midpoint_rows,
        )
        write_csv(
            ROOT / "csv" / f"{variant.lower()}_s116_overrange.csv",
            overrange_rows,
        )
        payload["variants"][variant] = {
            "midpoint_count": len(midpoint_rows),
            "midpoint_pass_count": sum(
                bool(row["decode_pass"]) for row in midpoint_rows
            ),
            "overrange_count": len(overrange_rows),
            "overrange_pass_count": sum(
                bool(row["decode_pass"]) for row in overrange_rows
            ),
        }
    payload["status"] = (
        "PASS"
        if all(
            item["midpoint_count"] == 254
            and item["midpoint_pass_count"] == 254
            and item["overrange_count"] == 2
            and item["overrange_pass_count"] == 2
            for item in payload["variants"].values()
        )
        else "FAIL"
    )
    payload["completed_utc"] = utc_now()
    write_json(ROOT / "results" / "midpoint_overrange_execution.json", payload)
    return payload


def run_ramp() -> dict[str, Any]:
    frames_per_point = selected_frames()
    ramp_vids = np.linspace(-1.8, 1.8, 1089).tolist()
    payload: dict[str, Any] = {
        "frames_per_point": frames_per_point,
        "points_per_variant": len(ramp_vids),
        "variants": {},
    }
    for variant in VARIANTS:
        expanded = [-1.8]
        for vid in ramp_vids:
            expanded.extend([vid] * frames_per_point)
        stem = f"{variant.lower()}_upward_ramp_1089_f{frames_per_point}"
        result = common.run_deck(
            build_variant_deck(variant, expanded, kind="linear_sequence"),
            stem,
            ROOT / "generated" / "jobs" / "ramp",
            ROOT / "logs" / "ramp",
            timeout_s=14400,
        )
        frames = common.decode_frames(
            result,
            len(expanded),
            common.PVT_CASES[PVT]["vdd_v"],
            common.FRAME_DEFAULT_S,
        )
        rows = []
        for point_index, vid in enumerate(ramp_vids):
            start = 1 + point_index * frames_per_point
            selected = frames[start : start + frames_per_point]
            formal = selected[-1]
            rows.append(
                {
                    "variant": variant,
                    "point_index": point_index,
                    "commanded_vid_v": vid,
                    "conditioning_codes": "/".join(
                        str(frame["code"]) for frame in selected[:-1]
                    ),
                    "formal_code": formal["code"],
                    "all_frames_valid": all(frame["valid"] for frame in selected),
                    "formal_valid": formal["valid"],
                    "sampled_diff_v": formal["sampled_diff_v"],
                }
            )
        write_csv(ROOT / "csv" / f"{variant.lower()}_s116_upward_ramp.csv", rows)
        codes = [int(row["formal_code"]) for row in rows]
        payload["variants"][variant] = {
            "returncode": result["returncode"],
            "all_frames_valid": all(row["all_frames_valid"] for row in rows),
            "monotonic": all(left <= right for left, right in zip(codes, codes[1:])),
            "code_coverage": len(set(codes)),
            "endpoint_codes": [codes[0], codes[-1]],
            "elapsed_s": result["elapsed_s"],
            "peak_rss_kb": result["peak_rss_kb"],
            "cached": result["cached"],
        }
        append_runtime(
            [
                {
                    "utc_started": utc_now(),
                    "job": stem,
                    "variant": variant,
                    "stage": "ramp",
                    "points": len(ramp_vids),
                    "frames": len(expanded),
                    "frames_per_point": frames_per_point,
                    "maxstep_ps": 50,
                    "elapsed_s": result["elapsed_s"],
                    "peak_rss_kb": result["peak_rss_kb"],
                    "returncode": result["returncode"],
                    "cached": result["cached"],
                    "timed_out": result["timed_out"],
                    "simulation_aborted": result["simulation_aborted"],
                    "retry": False,
                }
            ]
        )
    payload["status"] = (
        "PASS"
        if all(
            item["returncode"] == 0
            and item["all_frames_valid"]
            and item["monotonic"]
            and item["endpoint_codes"] == [0, 255]
            for item in payload["variants"].values()
        )
        else "FAIL"
    )
    payload["completed_utc"] = utc_now()
    write_json(ROOT / "results" / "ramp_execution.json", payload)
    return payload


def update_status() -> None:
    paths = {
        "qualification": ROOT / "results" / "conditioning_method_qualification.json",
        "pilot": ROOT / "results" / "runtime_pilot.json",
        "transitions": ROOT / "results" / "full_transition_execution.json",
        "midpoint_overrange": ROOT / "results" / "midpoint_overrange_execution.json",
        "ramp": ROOT / "results" / "ramp_execution.json",
    }
    stages = {
        name: read_json(path) if path.is_file() else None
        for name, path in paths.items()
    }
    complete = all(
        stages[name] is not None
        for name in ("qualification", "pilot", "transitions", "midpoint_overrange", "ramp")
    )
    payload = {
        "campaign": ROOT.name,
        "updated_utc": utc_now(),
        "state": (
            "SIMULATION_EXECUTION_COMPLETE_AWAITING_ANALYSIS"
            if complete
            else "SIMULATION_EXECUTION_IN_PROGRESS"
        ),
        "stages": {
            name: stage.get("status") if stage is not None else "NOT_RUN"
            for name, stage in stages.items()
        },
        "full_curve_execution_complete": bool(
            stages["transitions"]
            and stages["transitions"].get("status") == "PASS"
        ),
        "paired_effect_status": "NOT_EVALUATED",
        "excluded_by_user": ["symmetric strict replay", "dense scan"],
        "nonclaims": [
            "nominal performance",
            "current population P95",
            "Monte Carlo pass rate",
            "production yield",
        ],
    }
    write_json(ROOT / "STATUS.json", payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("qualify", "pilot", "transitions", "midpoint", "ramp", "all"),
    )
    args = parser.parse_args()
    if args.stage in ("qualify", "all"):
        run_qualification()
        update_status()
    if args.stage in ("pilot", "all"):
        run_pilot()
        update_status()
    if args.stage in ("transitions", "all"):
        run_full_transitions()
        update_status()
    if args.stage in ("midpoint", "all"):
        run_midpoint_and_overrange()
        update_status()
    if args.stage in ("ramp", "all"):
        run_ramp()
        update_status()
    print((ROOT / "STATUS.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
