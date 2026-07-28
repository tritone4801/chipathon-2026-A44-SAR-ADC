#!/usr/bin/env python3
"""Analyze the frozen seed116 BASELINE/A2P25 paired static experiment."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "csv"
RESULTS = ROOT / "results"
PLOTS = ROOT / "plots"
REPORTS = ROOT / "reports"
MANIFESTS = ROOT / "manifests"
QNOM_V = 3.4 / 256.0
VARIANTS = {
    "BASELINE": "baseline",
    "A2P25": "a2p25",
}
MAJOR_CARRIES = (32, 64, 96, 128, 160, 192, 224)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_transitions(stem: str) -> dict[str, np.ndarray]:
    rows = read_csv(CSV_DIR / f"{stem}_s116_transitions_up.csv")
    rows.sort(key=lambda row: int(row["target_transition"]))
    if len(rows) != 255 or any(row["status"] != "PASS" for row in rows):
        raise RuntimeError(f"{stem}: transition execution is not 255/255 PASS")
    targets = np.asarray([int(row["target_transition"]) for row in rows])
    if not np.array_equal(targets, np.arange(1, 256)):
        raise RuntimeError(f"{stem}: transition targets are incomplete")
    return {
        "k": targets.astype(float),
        "lower": np.asarray([float(row["lower_v"]) for row in rows]),
        "upper": np.asarray([float(row["upper_v"]) for row in rows]),
        "center": np.asarray([float(row["transition_v"]) for row in rows]),
        "bracket_lsb": np.asarray(
            [float(row["final_bracket_width_lsb"]) for row in rows]
        ),
    }


def endpoint_inl(t: np.ndarray, q: float) -> np.ndarray:
    k = np.arange(1, 256, dtype=float)
    return (t - (t[0] + (k - 1.0) * q)) / q


def best_fit_metrics(t: np.ndarray) -> tuple[float, float, np.ndarray, np.ndarray]:
    k = np.arange(1, 256, dtype=float)
    slope, intercept = np.polyfit(k, t, 1)
    inl = (t - (intercept + slope * k)) / slope
    dnl = np.diff(t) / slope - 1.0
    return float(slope), float(intercept), dnl, inl


def interval_metrics(data: dict[str, np.ndarray]) -> dict[str, Any]:
    lo = data["lower"]
    hi = data["upper"]
    center = data["center"]
    widths = np.diff(center)
    width_lo = lo[1:] - hi[:-1]
    width_hi = hi[1:] - lo[:-1]
    q_ep = (center[-1] - center[0]) / 254.0
    q_ep_lo = (lo[-1] - hi[0]) / 254.0
    q_ep_hi = (hi[-1] - lo[0]) / 254.0
    dnl_ep = widths / q_ep - 1.0
    dnl_ep_lo = width_lo / q_ep_hi - 1.0
    dnl_ep_hi = width_hi / q_ep_lo - 1.0
    inl_ep = endpoint_inl(center, q_ep)
    slope_bf, intercept_bf, dnl_bf, inl_bf = best_fit_metrics(center)
    dnl_nom = widths / QNOM_V - 1.0

    classifications = np.full(254, "NUMERICALLY_INCONCLUSIVE", dtype=object)
    classifications[width_lo > 0.0] = "DEFINITELY_PRESENT"
    classifications[width_hi < 0.0] = "DEFINITELY_MISSING"

    dnl_gate = (
        "PASS"
        if np.all(dnl_ep_lo > -1.0) and np.all(dnl_ep_hi < 1.0)
        else "FAIL"
    )
    inl_gate = "PASS" if np.max(np.abs(inl_ep)) < 1.5 else "FAIL"
    absolute = "PASS" if dnl_gate == "PASS" and inl_gate == "PASS" else "FAIL"

    width_rows: list[dict[str, Any]] = []
    for index, code in enumerate(range(1, 255)):
        width_rows.append(
            {
                "code": code,
                "width_center_v": widths[index],
                "width_lower_v": width_lo[index],
                "width_upper_v": width_hi[index],
                "width_center_mV": widths[index] * 1e3,
                "width_nominal_lsb": widths[index] / QNOM_V,
                "classification": classifications[index],
                "dnl_ep_center_lsb": dnl_ep[index],
                "dnl_ep_lower_lsb": dnl_ep_lo[index],
                "dnl_ep_upper_lsb": dnl_ep_hi[index],
                "dnl_nom_center_lsb": dnl_nom[index],
                "dnl_bf_center_lsb": dnl_bf[index],
            }
        )

    transition_rows: list[dict[str, Any]] = []
    for index, code in enumerate(range(1, 256)):
        transition_rows.append(
            {
                "transition": code,
                "lower_v": lo[index],
                "center_v": center[index],
                "upper_v": hi[index],
                "inl_ep_center_lsb": inl_ep[index],
                "inl_bf_center_lsb": inl_bf[index],
            }
        )

    summary = {
        "transition_count": 255,
        "max_final_bracket_lsb": float(np.max(data["bracket_lsb"])),
        "q_ep_v": q_ep,
        "q_ep_lower_v": q_ep_lo,
        "q_ep_upper_v": q_ep_hi,
        "q_ep_mV": q_ep * 1e3,
        "q_nom_v": QNOM_V,
        "best_fit_slope_v": slope_bf,
        "best_fit_intercept_v": intercept_bf,
        "definitely_present_code_count": int(
            np.sum(classifications == "DEFINITELY_PRESENT")
        ),
        "definitely_missing_code_count": int(
            np.sum(classifications == "DEFINITELY_MISSING")
        ),
        "numerically_inconclusive_code_count": int(
            np.sum(classifications == "NUMERICALLY_INCONCLUSIVE")
        ),
        "definitely_missing_codes": [
            int(code)
            for code, value in zip(range(1, 255), classifications)
            if value == "DEFINITELY_MISSING"
        ],
        "numerically_inconclusive_codes": [
            int(code)
            for code, value in zip(range(1, 255), classifications)
            if value == "NUMERICALLY_INCONCLUSIVE"
        ],
        "min_dnl_ep_center_lsb": float(np.min(dnl_ep)),
        "max_dnl_ep_center_lsb": float(np.max(dnl_ep)),
        "max_abs_dnl_ep_center_lsb": float(np.max(np.abs(dnl_ep))),
        "max_abs_dnl_ep_interval_bound_lsb": float(
            max(np.max(np.abs(dnl_ep_lo)), np.max(np.abs(dnl_ep_hi)))
        ),
        "max_abs_inl_ep_center_lsb": float(np.max(np.abs(inl_ep))),
        "max_abs_dnl_bf_center_lsb": float(np.max(np.abs(dnl_bf))),
        "max_abs_inl_bf_center_lsb": float(np.max(np.abs(inl_bf))),
        "dnl_ep_open_gate": dnl_gate,
        "inl_ep_abs_lt_1p5_gate": inl_gate,
        "absolute_static_status": absolute,
    }
    return {
        "summary": summary,
        "width_rows": width_rows,
        "transition_rows": transition_rows,
        "width_center": widths,
        "dnl_ep": dnl_ep,
        "dnl_nom": dnl_nom,
        "dnl_bf": dnl_bf,
        "inl_ep": inl_ep,
        "inl_bf": inl_bf,
    }


def load_midpoint(stem: str) -> dict[str, Any]:
    rows = read_csv(CSV_DIR / f"{stem}_s116_midpoint_decode.csv")
    failed = [
        {
            "point_id": row["point_id"],
            "vid_v": float(row["vid_v"]),
            "expected_code": int(float(row["expected_code"])),
            "formal_code": int(float(row["formal_code"])),
            "all_frames_valid": row["all_frames_valid"] == "True",
            "formal_valid": row["formal_valid"] == "True",
            "job": row["job"],
        }
        for row in rows
        if row["decode_pass"] != "True"
    ]
    overrange = read_csv(CSV_DIR / f"{stem}_s116_overrange.csv")
    overrange_pass = sum(
        row["all_frames_valid"] == "True"
        and row["formal_valid"] == "True"
        and int(float(row["formal_code"])) == int(float(row["target"]))
        for row in overrange
    )
    return {
        "midpoint_count": len(rows),
        "midpoint_pass_count": len(rows) - len(failed),
        "midpoint_fail_count": len(failed),
        "midpoint_failures": failed,
        "overrange_count": len(overrange),
        "overrange_pass_count": overrange_pass,
    }


def ramp_correlation(
    stem: str, transition: dict[str, np.ndarray]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = read_csv(CSV_DIR / f"{stem}_s116_upward_ramp.csv")
    commanded = np.asarray([float(row["commanded_vid_v"]) for row in rows])
    codes = np.asarray([int(float(row["formal_code"])) for row in rows])
    all_valid = all(
        row["all_frames_valid"] == "True" and row["formal_valid"] == "True"
        for row in rows
    )
    step = float(np.max(np.diff(commanded)))
    output_rows: list[dict[str, Any]] = []
    pass_count = 0
    unavailable: list[int] = []
    for index, code in enumerate(range(1, 256)):
        positions = np.flatnonzero(codes >= code)
        if not len(positions):
            unavailable.append(code)
            continue
        crossing = commanded[positions[0]]
        center = transition["center"][index]
        exact_half_width = 0.5 * (
            transition["upper"][index] - transition["lower"][index]
        )
        tolerance = step + exact_half_width
        error = crossing - center
        passed = abs(error) <= tolerance + 1e-15
        pass_count += int(passed)
        output_rows.append(
            {
                "transition": code,
                "exact_transition_center_v": center,
                "ramp_first_commanded_v_at_or_above_code": crossing,
                "error_v": error,
                "ramp_step_v": step,
                "exact_half_bracket_v": exact_half_width,
                "tolerance_v": tolerance,
                "correlation_pass": passed,
            }
        )
    summary = {
        "point_count": len(rows),
        "all_frames_valid": all_valid,
        "endpoint_codes": [int(codes[0]), int(codes[-1])],
        "monotonic": bool(np.all(np.diff(codes) >= 0)),
        "observed_code_count": int(len(np.unique(codes))),
        "ramp_step_v": step,
        "correlated_transition_count": len(output_rows),
        "correlation_pass_count": pass_count,
        "unavailable_transition_codes": unavailable,
        "max_abs_correlation_error_v": float(
            max(abs(row["error_v"]) for row in output_rows)
        ),
        "status": (
            "PASS"
            if all_valid
            and np.all(np.diff(codes) >= 0)
            and pass_count == len(output_rows) == 255
            else "FAIL"
        ),
    }
    return summary, output_rows


def paired_metrics(
    base_t: dict[str, np.ndarray],
    cand_t: dict[str, np.ndarray],
    base_m: dict[str, Any],
    cand_m: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    k = np.arange(1, 256, dtype=float)
    delta = cand_t["center"] - base_t["center"]
    delta_lo = cand_t["lower"] - base_t["upper"]
    delta_hi = cand_t["upper"] - base_t["lower"]
    x = k - 128.0
    b, a = np.polyfit(x, delta, 1)
    residual = delta - (a + b * x)
    worst_index = int(np.argmax(np.abs(residual)))

    transition_rows: list[dict[str, Any]] = []
    for index, code in enumerate(range(1, 256)):
        transition_rows.append(
            {
                "transition": code,
                "delta_t_lower_v": delta_lo[index],
                "delta_t_center_v": delta[index],
                "delta_t_upper_v": delta_hi[index],
                "fit_v": a + b * x[index],
                "residual_v": residual[index],
                "delta_inl_ep_lsb": cand_m["inl_ep"][index]
                - base_m["inl_ep"][index],
                "delta_inl_bf_lsb": cand_m["inl_bf"][index]
                - base_m["inl_bf"][index],
            }
        )

    width_rows: list[dict[str, Any]] = []
    for index, code in enumerate(range(1, 255)):
        width_rows.append(
            {
                "code": code,
                "delta_width_v": cand_m["width_center"][index]
                - base_m["width_center"][index],
                "delta_dnl_ep_lsb": cand_m["dnl_ep"][index]
                - base_m["dnl_ep"][index],
                "delta_dnl_nom_lsb": cand_m["dnl_nom"][index]
                - base_m["dnl_nom"][index],
                "delta_dnl_bf_lsb": cand_m["dnl_bf"][index]
                - base_m["dnl_bf"][index],
            }
        )

    carry_rows: list[dict[str, Any]] = []
    for carry in MAJOR_CARRIES:
        selected = [
            row for row in width_rows if carry - 1 <= int(row["code"]) <= carry + 1
        ]
        dnl_delta = np.asarray([row["delta_dnl_ep_lsb"] for row in selected])
        carry_rows.append(
            {
                "carry": carry,
                "codes": ",".join(str(row["code"]) for row in selected),
                "delta_dnl_ep_peak_abs_lsb": float(np.max(np.abs(dnl_delta))),
                "delta_dnl_ep_rms_lsb": float(np.sqrt(np.mean(dnl_delta**2))),
                "delta_dnl_ep_signed_integral_lsb": float(np.sum(dnl_delta)),
            }
        )

    base_s = base_m["summary"]
    cand_s = cand_m["summary"]
    improvements = {
        "definitely_missing_code_count": cand_s["definitely_missing_code_count"]
        < base_s["definitely_missing_code_count"],
        "max_abs_dnl_ep": cand_s["max_abs_dnl_ep_center_lsb"]
        < base_s["max_abs_dnl_ep_center_lsb"] - 0.02,
        "max_abs_inl_ep": cand_s["max_abs_inl_ep_center_lsb"]
        < base_s["max_abs_inl_ep_center_lsb"] - 0.02,
        "max_abs_inl_bf": cand_s["max_abs_inl_bf_center_lsb"]
        < base_s["max_abs_inl_bf_center_lsb"] - 0.02,
    }
    regressions = {
        "definitely_missing_code_count": cand_s["definitely_missing_code_count"]
        > base_s["definitely_missing_code_count"],
        "max_abs_dnl_ep": cand_s["max_abs_dnl_ep_center_lsb"]
        > base_s["max_abs_dnl_ep_center_lsb"] + 0.02,
        "max_abs_inl_ep": cand_s["max_abs_inl_ep_center_lsb"]
        > base_s["max_abs_inl_ep_center_lsb"] + 0.02,
        "max_abs_inl_bf": cand_s["max_abs_inl_bf_center_lsb"]
        > base_s["max_abs_inl_bf_center_lsb"] + 0.02,
    }
    if any(improvements.values()) and not any(regressions.values()):
        status = "IMPROVEMENT_CONFIRMED"
    elif any(improvements.values()) and any(regressions.values()):
        status = "TRADEOFF"
    elif not any(improvements.values()) and not any(regressions.values()):
        status = "NUMERICALLY_EQUIVALENT"
    else:
        status = "INCONCLUSIVE"

    summary = {
        "paired_effect_status": status,
        "improvement_flags": improvements,
        "regression_flags": regressions,
        "delta_transition_fit": {
            "a_v_at_k128": float(a),
            "a_nominal_lsb": float(a / QNOM_V),
            "b_v_per_code": float(b),
            "b_nominal_lsb_per_code": float(b / QNOM_V),
            "residual_rms_v": float(np.sqrt(np.mean(residual**2))),
            "residual_rms_nominal_lsb": float(
                np.sqrt(np.mean(residual**2)) / QNOM_V
            ),
            "residual_max_abs_v": float(np.max(np.abs(residual))),
            "residual_max_abs_nominal_lsb": float(
                np.max(np.abs(residual)) / QNOM_V
            ),
            "worst_residual_transition": worst_index + 1,
            "worst_residual_v": float(residual[worst_index]),
        },
        "delta_max_abs_dnl_ep_lsb": cand_s["max_abs_dnl_ep_center_lsb"]
        - base_s["max_abs_dnl_ep_center_lsb"],
        "delta_max_abs_inl_ep_lsb": cand_s["max_abs_inl_ep_center_lsb"]
        - base_s["max_abs_inl_ep_center_lsb"],
        "delta_max_abs_inl_bf_lsb": cand_s["max_abs_inl_bf_center_lsb"]
        - base_s["max_abs_inl_bf_center_lsb"],
        "delta_definitely_missing_code_count": cand_s[
            "definitely_missing_code_count"
        ]
        - base_s["definitely_missing_code_count"],
        "major_carry_bands": carry_rows,
    }
    return summary, transition_rows, width_rows


def save_plots(
    base_t: dict[str, np.ndarray],
    cand_t: dict[str, np.ndarray],
    base_m: dict[str, Any],
    cand_m: dict[str, Any],
    paired_transition_rows: list[dict[str, Any]],
    paired_width_rows: list[dict[str, Any]],
    ramp_rows: dict[str, list[dict[str, Any]]],
) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    codes = np.arange(1, 255)
    transitions = np.arange(1, 256)

    def finish(name: str) -> None:
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(PLOTS / name, dpi=220)
        plt.close()

    plt.figure(figsize=(11, 5))
    plt.plot(codes, base_m["dnl_ep"], label="Baseline")
    plt.plot(codes, cand_m["dnl_ep"], label="A2P25")
    plt.axhline(1, color="red", linestyle="--", linewidth=0.8)
    plt.axhline(-1, color="red", linestyle="--", linewidth=0.8)
    plt.xlabel("Code")
    plt.ylabel("Endpoint DNL (LSB)")
    plt.title("Seed116 paired endpoint DNL")
    finish("paired_dnl_overlay.png")

    plt.figure(figsize=(11, 5))
    plt.plot(transitions, base_m["inl_ep"], label="Baseline EP")
    plt.plot(transitions, cand_m["inl_ep"], label="A2P25 EP")
    plt.plot(transitions, base_m["inl_bf"], label="Baseline BF", alpha=0.65)
    plt.plot(transitions, cand_m["inl_bf"], label="A2P25 BF", alpha=0.65)
    plt.axhline(1.5, color="red", linestyle="--", linewidth=0.8)
    plt.axhline(-1.5, color="red", linestyle="--", linewidth=0.8)
    plt.xlabel("Transition")
    plt.ylabel("INL (LSB)")
    plt.title("Seed116 paired INL")
    finish("paired_inl_overlay.png")

    plt.figure(figsize=(11, 5))
    plt.plot(codes, base_m["width_center"] * 1e3, label="Baseline")
    plt.plot(codes, cand_m["width_center"] * 1e3, label="A2P25")
    plt.axhline(0, color="red", linestyle="--", linewidth=0.8)
    plt.xlabel("Code")
    plt.ylabel("Code width (mV)")
    plt.title("Seed116 paired code widths")
    finish("paired_code_width.png")

    delta = np.asarray([row["delta_t_center_v"] for row in paired_transition_rows])
    fit = np.asarray([row["fit_v"] for row in paired_transition_rows])
    residual = np.asarray([row["residual_v"] for row in paired_transition_rows])
    plt.figure(figsize=(11, 5))
    plt.plot(transitions, delta / QNOM_V, label="Delta Tk")
    plt.plot(transitions, fit / QNOM_V, label="Linear fit")
    plt.xlabel("Transition")
    plt.ylabel("A2P25 - Baseline (nominal LSB)")
    plt.title("Paired transition shift and fit")
    finish("paired_delta_transition_fit.png")

    plt.figure(figsize=(11, 5))
    plt.plot(transitions, residual / QNOM_V, label="Fit residual")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Transition")
    plt.ylabel("Residual (nominal LSB)")
    plt.title("Paired transition-fit residual")
    finish("paired_delta_transition_residual.png")

    plt.figure(figsize=(11, 5))
    delta_dnl = np.asarray(
        [row["delta_dnl_ep_lsb"] for row in paired_width_rows]
    )
    plt.plot(codes, delta_dnl, label="Delta endpoint DNL")
    for carry in MAJOR_CARRIES:
        plt.axvspan(carry - 1, carry + 1, color="orange", alpha=0.15)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Code")
    plt.ylabel("A2P25 - Baseline (LSB)")
    plt.title("Major-carry local paired DNL change")
    finish("major_carry_detail.png")

    plt.figure(figsize=(11, 5))
    for variant, rows in ramp_rows.items():
        x = [row["exact_transition_center_v"] for row in rows]
        y = [row["ramp_first_commanded_v_at_or_above_code"] for row in rows]
        plt.scatter(x, y, s=8, label=variant, alpha=0.65)
    limits = [-1.75, 1.75]
    plt.plot(limits, limits, color="black", linestyle="--", linewidth=0.8)
    plt.xlabel("Exact transition center (V)")
    plt.ylabel("Ramp first crossing (V)")
    plt.title("Ramp-to-exact transition correlation")
    finish("ramp_correlation.png")


def build_report(payload: dict[str, Any]) -> str:
    base = payload["variants"]["BASELINE"]
    cand = payload["variants"]["A2P25"]
    paired = payload["paired"]
    midpoint = payload["midpoint_overrange"]
    ramp = payload["ramp_correlation"]
    fit = paired["delta_transition_fit"]
    lines = [
        "# Seed116 BASELINE vs A2P25 paired static result",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"- Paired effect: **{paired['paired_effect_status']}**.",
        f"- Baseline absolute static status: **{base['absolute_static_status']}**.",
        f"- A2P25 absolute static status: **{cand['absolute_static_status']}**.",
        "- Scope is one historical P95-selection realization (seed116), not a current P95 estimate.",
        "",
        "## Frozen experiment",
        "",
        "- TT / 3.3 V / 27 C; mismatch seed116; temporal/event noise disabled.",
        "- BASELINE comparator input pair XM3/XM4 W=1.56 um.",
        "- A2P25 comparator input pair XM3/XM4 W=3.51 um.",
        "- L=0.28 um, m=4, nf=1 unchanged; all other devices and the CDAC mismatch realization are paired.",
        "- Upward T1..T255 transition search, two frames per point, 50 ps maxstep.",
        "- Symmetric strict replay and dense scan were explicitly excluded and were not run.",
        "",
        "## Static metrics",
        "",
        "| Metric | BASELINE | A2P25 |",
        "|---|---:|---:|",
        f"| QEP (mV) | {base['q_ep_mV']:.6f} | {cand['q_ep_mV']:.6f} |",
        f"| Max abs endpoint DNL (LSB) | {base['max_abs_dnl_ep_center_lsb']:.6f} | {cand['max_abs_dnl_ep_center_lsb']:.6f} |",
        f"| Max abs endpoint INL (LSB) | {base['max_abs_inl_ep_center_lsb']:.6f} | {cand['max_abs_inl_ep_center_lsb']:.6f} |",
        f"| Max abs best-fit INL (LSB) | {base['max_abs_inl_bf_center_lsb']:.6f} | {cand['max_abs_inl_bf_center_lsb']:.6f} |",
        f"| Definitely missing internal codes | {base['definitely_missing_code_count']} | {cand['definitely_missing_code_count']} |",
        f"| Numerically inconclusive widths | {base['numerically_inconclusive_code_count']} | {cand['numerically_inconclusive_code_count']} |",
        f"| DNL open gate (-1,+1) | {base['dnl_ep_open_gate']} | {cand['dnl_ep_open_gate']} |",
        f"| abs(INL_EP)<1.5 gate | {base['inl_ep_abs_lt_1p5_gate']} | {cand['inl_ep_abs_lt_1p5_gate']} |",
        "",
        "The code-width classification uses the measured bounds:",
        "`Wmin = L(k+1)-H(k)` and `Wmax = H(k+1)-L(k)`.",
        "",
        "## Paired effect",
        "",
        f"- Change in definitely missing-code count: {paired['delta_definitely_missing_code_count']:+d}.",
        f"- Change in max abs endpoint DNL: {paired['delta_max_abs_dnl_ep_lsb']:+.6f} LSB.",
        f"- Change in max abs endpoint INL: {paired['delta_max_abs_inl_ep_lsb']:+.6f} LSB.",
        f"- Change in max abs best-fit INL: {paired['delta_max_abs_inl_bf_lsb']:+.6f} LSB.",
        f"- Delta-T fit offset a: {fit['a_nominal_lsb']:+.6f} nominal LSB.",
        f"- Delta-T fit slope b: {fit['b_nominal_lsb_per_code']:+.9f} nominal LSB/code.",
        f"- Fit residual RMS/max: {fit['residual_rms_nominal_lsb']:.6f} / {fit['residual_max_abs_nominal_lsb']:.6f} nominal LSB.",
        f"- Worst residual transition: T{fit['worst_residual_transition']}.",
        "",
        "## Protocol, midpoint, endpoints and ramp",
        "",
        f"- BASELINE midpoint: {midpoint['BASELINE']['midpoint_pass_count']}/254 pass.",
        f"- A2P25 midpoint: {midpoint['A2P25']['midpoint_pass_count']}/254 pass.",
        f"- Overrange: BASELINE {midpoint['BASELINE']['overrange_pass_count']}/2, A2P25 {midpoint['A2P25']['overrange_pass_count']}/2.",
        "- Baseline code225 midpoint failed twice at identical settings because ngspice aborted with timestep-too-small; it is an execution failure, not a decoded-code observation.",
        f"- Ramp correlation: BASELINE {ramp['BASELINE']['correlation_pass_count']}/255, A2P25 {ramp['A2P25']['correlation_pass_count']}/255; both are monotonic with valid endpoints.",
        "",
        "## Claim boundary",
        "",
        "This campaign supports only a paired conclusion for the retained historical seed116 realization.",
        "It does not establish nominal performance, a current population P95, Monte Carlo pass rate, production yield, or resizing signoff.",
        "The midpoint stage is not a clean campaign PASS because of valid code mismatches and the Baseline code225 numerical abort.",
        "",
        "## Key artifacts",
        "",
        "- `results/paired_static_analysis.json`",
        "- `csv/*_code_width_metrics.csv` and `csv/paired_*.csv`",
        "- `plots/*.png`",
        "- `results/completion_audit.json`",
        "- `manifests/package_manifest_sha256.csv`",
        "",
    ]
    return "\n".join(lines)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for directory in (RESULTS, PLOTS, REPORTS, MANIFESTS):
        directory.mkdir(parents=True, exist_ok=True)

    transition_data: dict[str, dict[str, np.ndarray]] = {}
    metrics: dict[str, dict[str, Any]] = {}
    midpoint: dict[str, dict[str, Any]] = {}
    ramp_summary: dict[str, dict[str, Any]] = {}
    ramp_rows: dict[str, list[dict[str, Any]]] = {}

    for variant, stem in VARIANTS.items():
        transition_data[variant] = load_transitions(stem)
        metrics[variant] = interval_metrics(transition_data[variant])
        midpoint[variant] = load_midpoint(stem)
        ramp_summary[variant], ramp_rows[variant] = ramp_correlation(
            stem, transition_data[variant]
        )
        write_csv(
            CSV_DIR / f"{stem}_s116_code_width_metrics.csv",
            metrics[variant]["width_rows"],
        )
        write_csv(
            CSV_DIR / f"{stem}_s116_transition_metrics.csv",
            metrics[variant]["transition_rows"],
        )
        write_csv(
            CSV_DIR / f"{stem}_s116_ramp_correlation.csv",
            ramp_rows[variant],
        )

    paired, paired_transition_rows, paired_width_rows = paired_metrics(
        transition_data["BASELINE"],
        transition_data["A2P25"],
        metrics["BASELINE"],
        metrics["A2P25"],
    )
    write_csv(CSV_DIR / "paired_transition_delta.csv", paired_transition_rows)
    write_csv(CSV_DIR / "paired_code_width_delta.csv", paired_width_rows)
    write_csv(CSV_DIR / "major_carry_local_metrics.csv", paired["major_carry_bands"])

    save_plots(
        transition_data["BASELINE"],
        transition_data["A2P25"],
        metrics["BASELINE"],
        metrics["A2P25"],
        paired_transition_rows,
        paired_width_rows,
        ramp_rows,
    )

    payload = {
        "campaign": ROOT.name,
        "generated_utc": utc_now(),
        "scope": "HISTORICAL_P95_SELECTION_CASE_S116_PAIRED_STATIC_ONLY",
        "variants": {
            variant: metrics[variant]["summary"] for variant in VARIANTS
        },
        "paired": paired,
        "midpoint_overrange": midpoint,
        "ramp_correlation": ramp_summary,
        "execution": {
            "qualification": "PASS_TWO_FRAME",
            "pilot": "PASS",
            "transitions": "PASS",
            "midpoint_overrange": "FAIL",
            "ramp": "PASS",
            "full_transition_curve_complete": True,
        },
        "excluded_by_user": ["symmetric strict replay", "dense scan"],
        "nonclaims": [
            "nominal performance",
            "current population P95",
            "Monte Carlo pass rate",
            "production yield",
            "resizing signoff",
        ],
    }
    write_json(RESULTS / "paired_static_analysis.json", payload)
    (REPORTS / "STATIC_PAIRED_REPORT.md").write_text(
        build_report(payload), encoding="utf-8"
    )

    status = {
        "campaign": ROOT.name,
        "updated_utc": utc_now(),
        "state": "COMPLETE_WITH_MIDPOINT_FAILURE",
        "full_curve_execution_complete": True,
        "stages": payload["execution"],
        "paired_effect_status": paired["paired_effect_status"],
        "baseline_absolute_static_status": payload["variants"]["BASELINE"][
            "absolute_static_status"
        ],
        "a2p25_absolute_static_status": payload["variants"]["A2P25"][
            "absolute_static_status"
        ],
        "excluded_by_user": payload["excluded_by_user"],
        "nonclaims": payload["nonclaims"],
    }
    write_json(ROOT / "STATUS.json", status)

    required = [
        ROOT / "config" / "paired_static_contract.json",
        ROOT / "config" / "seed116_selection_provenance.json",
        RESULTS / "source_binding_audit.json",
        RESULTS / "mismatch_pairing_audit.json",
        RESULTS / "mismatch_parameter_probe.json",
        RESULTS / "conditioning_method_qualification.json",
        RESULTS / "runtime_pilot.json",
        RESULTS / "full_transition_execution.json",
        RESULTS / "midpoint_overrange_execution.json",
        RESULTS / "ramp_execution.json",
        RESULTS / "paired_static_analysis.json",
        REPORTS / "STATIC_PAIRED_REPORT.md",
    ]
    required += sorted(PLOTS.glob("*.png"))
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    completion = {
        "completed_utc": utc_now(),
        "status": "PASS" if not missing else "FAIL",
        "required_artifact_count": len(required),
        "missing_required_artifacts": missing,
        "simulation_execution_complete": True,
        "full_transition_curve_complete": True,
        "midpoint_stage_status": "FAIL",
        "campaign_state": "COMPLETE_WITH_MIDPOINT_FAILURE",
        "strict_replay_executed": False,
        "dense_scan_executed": False,
    }
    write_json(RESULTS / "completion_audit.json", completion)

    manifest_rows: list[dict[str, Any]] = []
    excluded_roots = {"generated", "logs"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative.parts[0] in excluded_roots:
            continue
        if relative.as_posix() == "manifests/package_manifest_sha256.csv":
            continue
        manifest_rows.append(
            {
                "relative_path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hash_file(path),
            }
        )
    write_csv(MANIFESTS / "package_manifest_sha256.csv", manifest_rows)
    print(json.dumps(status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
