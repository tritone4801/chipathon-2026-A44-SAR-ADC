#!/usr/bin/env python3
import csv
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from run_comparator_equivalent_noise_calibration import fit_probit, wilson_interval
from run_exact_static import static_metrics
from sar_campaign_common import LSB_DIFF_V, ROOT, ensure_directories, load_cdac_weights, write_csv
from sar_event_noise import (
    COMPARATOR_SIGMA_V,
    SAMPLE_SIGMA_V,
    run_event_frames_isolated,
)


JOB_DIR = ROOT / "jobs" / "top_transition_probability"
LOG_DIR = ROOT / "logs" / "top_transition_probability"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

POINT_OFFSETS_LSB = (-0.30, -0.15, 0.0, 0.15, 0.30)
TRIALS_PER_POINT = 64
MAX_WORKERS = 3


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def transition_lookup(path):
    return {
        int(row["target_transition"]): float(row["transition_v"])
        for row in read_csv(path)
    }


def select_cases():
    summaries = read_csv(CSV_DIR / "static_mc200_reconstructed_summary.csv")
    worst = max(summaries, key=lambda row: float(row["static_risk_score"]))
    worst_seed = int(worst["mismatch_seed"])
    nominal = transition_lookup(CSV_DIR / "transitions_tt_nominal_up.csv")
    exact_path = CSV_DIR / f"transitions_mc_seed{worst_seed:03d}_up.csv"
    if not exact_path.exists():
        raise RuntimeError(
            f"worst-static seed {worst_seed} requires exact Phase F replay before noise testing"
        )
    exact_rows = read_csv(exact_path)
    exact_metrics = static_metrics(exact_rows)
    if exact_metrics["transition_count"] != 255:
        raise RuntimeError(
            f"worst-static seed {worst_seed} exact curve is incomplete"
        )
    worst_target = int(exact_metrics["worst_dnl_width_lower_transition"])
    targets = sorted({64, 128, worst_target})
    exact = transition_lookup(exact_path)
    cases = []
    for die_name, seed, lookup in (
        ("NOMINAL", None, nominal),
        ("WORST_STATIC", worst_seed, exact),
    ):
        for target in targets:
            cases.append(
                {
                    "die": die_name,
                    "mismatch_seed": seed,
                    "target_transition": target,
                    "expected_t50_v": lookup[target],
                    "noise_seed": 410000 + (0 if seed is None else seed * 1000) + target,
                    "worst_seed_specific_target": target == worst_target,
                }
            )
    return cases, worst_seed, worst_target


def run_case(case, grouped, timing):
    ideal_values = []
    point_mapping = []
    for point_index, offset_lsb in enumerate(POINT_OFFSETS_LSB):
        value = case["expected_t50_v"] + offset_lsb * LSB_DIFF_V
        for trial in range(TRIALS_PER_POINT):
            ideal_values.append(value)
            point_mapping.append((point_index, offset_lsb, trial))
    label = "nom" if case["mismatch_seed"] is None else f"s{case['mismatch_seed']:03d}"
    stem = f"top_prob_{label}_t{case['target_transition']:03d}_n{case['noise_seed']}"
    result = run_event_frames_isolated(
        stem,
        ideal_values,
        case["noise_seed"],
        timing,
        JOB_DIR,
        LOG_DIR,
        maxstep_s=50e-12,
        mismatch_seed=case["mismatch_seed"],
        grouped_weights=grouped,
        timeout_s=900,
        max_workers=1,
    )
    frame_rows = []
    probability_rows = []
    fit_rows = []
    for frame, mapping, ideal, command, sample_draw, comparator_draws in zip(
        result["frames"],
        point_mapping,
        result["ideal_vid_values"],
        result["commanded_vid_values"],
        result["noise"]["sample_draws_v"],
        result["noise"]["comparator_draws_v"],
    ):
        point_index, offset_lsb, trial = mapping
        decision_one = int(frame["code"] >= case["target_transition"])
        frame_rows.append(
            {
                **case,
                "point_index": point_index,
                "offset_lsb": offset_lsb,
                "trial": trial,
                "frame_index": frame["frame_index"],
                "ideal_vid_v": ideal,
                "commanded_vid_v": command,
                "sample_noise_draw_v": sample_draw,
                "comparator_noise_draws_v": "/".join(
                    f"{value:.9g}" for value in comparator_draws
                ),
                "code": frame["code"],
                "decision_one": decision_one,
                "valid": frame["valid"],
                "conversion_time_ns": (
                    frame["complete_time_s"]
                    - frame["frame_index"] * 500e-9
                    - 50e-9
                )
                * 1e9,
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
        )
    for point_index, offset_lsb in enumerate(POINT_OFFSETS_LSB):
        selected = [
            row for row in frame_rows if row["point_index"] == point_index and row["valid"]
        ]
        ones = sum(row["decision_one"] for row in selected)
        ci_low, ci_high = wilson_interval(ones, len(selected))
        probability_rows.append(
            {
                **case,
                "point_index": point_index,
                "offset_lsb": offset_lsb,
                "nominal_vid_v": offset_lsb * LSB_DIFF_V,
                "absolute_vid_v": case["expected_t50_v"] + offset_lsb * LSB_DIFF_V,
                "trials": TRIALS_PER_POINT,
                "valid_count": len(selected),
                "decision_one_count": ones,
                "decision_one_probability": ones / len(selected) if selected else float("nan"),
                "probability_ci95_low": ci_low,
                "probability_ci95_high": ci_high,
            }
        )
        fit_rows.append(probability_rows[-1])
    fit = fit_probit(fit_rows)
    expected_sigma = math.hypot(COMPARATOR_SIGMA_V, SAMPLE_SIGMA_V)
    summary = {
        **case,
        "fitted_t50_v": case["expected_t50_v"] + fit["vos_v"],
        "t50_error_lsb": abs(fit["vos_v"]) / LSB_DIFF_V,
        "fitted_sigma_v": fit["sigma_v"],
        "expected_sigma_v": expected_sigma,
        "sigma_error_fraction": abs(fit["sigma_v"] - expected_sigma) / expected_sigma,
        "sigma_ci95_low_v": fit["sigma_ci95_low_v"],
        "sigma_ci95_high_v": fit["sigma_ci95_high_v"],
        "valid_count": sum(row["valid"] for row in frame_rows),
        "invalid_or_timeout_count": sum(not row["valid"] for row in frame_rows),
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
    }
    summary["status"] = (
        "PASS"
        if summary["valid_count"] == len(frame_rows)
        and summary["sigma_error_fraction"] <= 0.15
        and summary["t50_error_lsb"] <= 0.10
        else "FAIL"
    )
    return summary, probability_rows, frame_rows


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    grouped = load_cdac_weights()
    timing = json.loads((CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii"))
    cases, worst_seed, worst_target = select_cases()
    summaries = []
    probabilities = []
    frames = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_case, case, grouped, timing): case for case in cases}
        for future in as_completed(futures):
            summary, point_rows, frame_rows = future.result()
            summaries.append(summary)
            probabilities.extend(point_rows)
            frames.extend(frame_rows)
            print(
                f"TOP_PROB die={summary['die']} target={summary['target_transition']} "
                f"sigma={summary['fitted_sigma_v']*1e3:.4f}mV "
                f"t50={summary['t50_error_lsb']:.4f}LSB status={summary['status']}",
                flush=True,
            )
    summaries.sort(key=lambda row: (row["die"], int(row["target_transition"])))
    probabilities.sort(
        key=lambda row: (row["die"], int(row["target_transition"]), int(row["point_index"]))
    )
    frames.sort(
        key=lambda row: (row["die"], int(row["target_transition"]), int(row["frame_index"]))
    )
    write_csv(CSV_DIR / "top_transition_probability.csv", probabilities)
    write_csv(CSV_DIR / "top_transition_probability_summary.csv", summaries)
    write_csv(CSV_DIR / "top_transition_probability_frames.csv", frames)
    status = "PASS" if all(row["status"] == "PASS" for row in summaries) else "FAIL"
    payload = {
        "status": status,
        "model_class": "T2_TARGET_CALIBRATED_EVENT_NOISE",
        "worst_static_seed": worst_seed,
        "worst_static_transition": worst_target,
        "sample_sigma_v": SAMPLE_SIGMA_V,
        "comparator_sigma_v": COMPARATOR_SIGMA_V,
        "cases": summaries,
    }
    (RESULT_DIR / "top_transition_probability.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Top-Level Selected-Transition Probability",
        "",
        f"- Status: `{status}`",
        "- Evidence class: `T2_TARGET_CALIBRATED_EVENT_NOISE`",
        f"- Worst-static fixed die: `{worst_seed}`",
        f"- Seed-specific worst-DNL transition: `{worst_target}`",
        f"- Sample draw sigma: `{SAMPLE_SIGMA_V*1e6:.6f} uVrms,diff` once per frame",
        f"- Comparator draw sigma: `{COMPARATOR_SIGMA_V*1e3:.6f} mVrms,diff` once per bit aperture",
        "",
        "| Die | Seed | Target | Sigma (mV) | Sigma error | T50 error (LSB) | Valid | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['die']} | {row['mismatch_seed']} | {row['target_transition']} | "
            f"{row['fitted_sigma_v']*1e3:.6f} | {row['sigma_error_fraction']:.3%} | "
            f"{row['t50_error_lsb']:.6f} | {row['valid_count']}/{len(POINT_OFFSETS_LSB)*TRIALS_PER_POINT} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "The injected event draws are an approved T2 engineering model. They are not native compact-device transient-noise evidence.",
        )
    )
    (REPORT_DIR / "top_transition_noise.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )

    comparator = json.loads((RESULT_DIR / "comparator_noise_calibration.json").read_text(encoding="ascii"))
    sample = json.loads((RESULT_DIR / "sample_noise_calibration.json").read_text(encoding="ascii"))
    calibration_lines = [
        "# Noise Calibration",
        "",
        f"- Overall Phase G status: `{status}`",
        f"- Comparator calibration: `{comparator['status']}`",
        f"- Sample/CDAC calibration: `{sample['status']}`",
        f"- Top selected-transition probability: `{status}`",
        "- Native MOS transient-noise claim: `NO`",
        "- Evidence tier: `T2_TARGET_CALIBRATED_EVENT_NOISE`",
        "",
        "Comparator probability covers TT VICM 1.6500/1.8625/2.0750 V and the SS noise-worst point. Sample/CDAC evidence covers TT/SS and input-amplitude dependence; the 1 THz result remains an explicit bandwidth sensitivity, not a claim-bearing integration band.",
    ]
    (REPORT_DIR / "noise_calibration.md").write_text(
        "\n".join(calibration_lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
