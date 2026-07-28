#!/usr/bin/env python3
import csv
import json
import math
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from run_comparator_equivalent_noise_calibration import fit_probit, wilson_interval
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
INITIAL_TRIALS = 64
ADDITIONAL_TRIALS = 64
FINAL_TRIALS = INITIAL_TRIALS + ADDITIONAL_TRIALS
MAX_WORKERS = 3
NOISE_SEED_OFFSET = 50_000_000


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def truth(value):
    return str(value).strip().lower() in ("1", "true", "yes")


def archive_initial_outputs():
    names = (
        "top_transition_probability.csv",
        "top_transition_probability_summary.csv",
        "top_transition_probability_frames.csv",
    )
    for name in names:
        source = CSV_DIR / name
        target = CSV_DIR / name.replace(".csv", "_initial64.csv")
        if not target.exists():
            shutil.copyfile(source, target)
    result_source = RESULT_DIR / "top_transition_probability.json"
    result_target = RESULT_DIR / "top_transition_probability_initial64.json"
    if not result_target.exists():
        shutil.copyfile(result_source, result_target)
    report_source = REPORT_DIR / "top_transition_noise.md"
    report_target = REPORT_DIR / "top_transition_noise_initial64.md"
    if not report_target.exists():
        shutil.copyfile(report_source, report_target)


def initial_paths():
    return (
        CSV_DIR / "top_transition_probability_initial64.csv",
        CSV_DIR / "top_transition_probability_summary_initial64.csv",
        CSV_DIR / "top_transition_probability_frames_initial64.csv",
    )


def sigma_confidence_adequate(row):
    expected = float(row["expected_sigma_v"])
    accept_low = 0.85 * expected
    accept_high = 1.15 * expected
    ci_low = float(row["sigma_ci95_low_v"])
    ci_high = float(row["sigma_ci95_high_v"])
    point_pass = float(row["sigma_error_fraction"]) <= 0.15
    if point_pass:
        return ci_low >= accept_low and ci_high <= accept_high
    return ci_high < accept_low or ci_low > accept_high


def case_key(row):
    return row["die"], int(row["target_transition"])


def parse_seed(value):
    return None if value in ("", None, "None") else int(float(value))


def run_additional_case(case, grouped, timing):
    ideal_values = []
    mapping = []
    expected_t50 = float(case["expected_t50_v"])
    for point_index, offset_lsb in enumerate(POINT_OFFSETS_LSB):
        value = expected_t50 + offset_lsb * LSB_DIFF_V
        for trial in range(ADDITIONAL_TRIALS):
            ideal_values.append(value)
            mapping.append((point_index, offset_lsb, trial + INITIAL_TRIALS))
    mismatch_seed = parse_seed(case.get("mismatch_seed"))
    label = "nom" if mismatch_seed is None else f"s{mismatch_seed:03d}"
    noise_seed = int(float(case["noise_seed"])) + NOISE_SEED_OFFSET
    stem = f"top_prob_adapt_{label}_t{int(case['target_transition']):03d}_n{noise_seed}"
    result = run_event_frames_isolated(
        stem,
        ideal_values,
        noise_seed,
        timing,
        JOB_DIR,
        LOG_DIR,
        maxstep_s=50e-12,
        mismatch_seed=mismatch_seed,
        grouped_weights=grouped,
        timeout_s=900,
        max_workers=1,
    )
    rows = []
    target = int(case["target_transition"])
    for frame, point, ideal, command, sample_draw, comparator_draws in zip(
        result["frames"],
        mapping,
        result["ideal_vid_values"],
        result["commanded_vid_values"],
        result["noise"]["sample_draws_v"],
        result["noise"]["comparator_draws_v"],
    ):
        point_index, offset_lsb, trial = point
        rows.append(
            {
                **case,
                "mismatch_seed": mismatch_seed,
                "point_index": point_index,
                "offset_lsb": offset_lsb,
                "trial": trial,
                "frame_index": point_index * FINAL_TRIALS + trial,
                "source_frame_index": frame["frame_index"],
                "sampling_stage": "ADAPTIVE_ADDITIONAL64",
                "adaptive_noise_seed": noise_seed,
                "ideal_vid_v": ideal,
                "commanded_vid_v": command,
                "sample_noise_draw_v": sample_draw,
                "comparator_noise_draws_v": "/".join(
                    f"{value:.9g}" for value in comparator_draws
                ),
                "code": frame["code"],
                "decision_one": int(frame["code"] >= target),
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
                "attempt_simulation_aborted": frame.get("attempt_simulation_aborted"),
                "attempt_elapsed_s": frame.get("attempt_elapsed_s"),
            }
        )
    return rows, result


def normalize_initial_frames(rows):
    output = []
    for row in rows:
        normalized = dict(row)
        point_index = int(row["point_index"])
        trial = int(row["trial"])
        normalized["source_frame_index"] = int(row["frame_index"])
        normalized["frame_index"] = point_index * FINAL_TRIALS + trial
        normalized["sampling_stage"] = "INITIAL64"
        normalized["adaptive_noise_seed"] = ""
        output.append(normalized)
    return output


def fit_case(case, frames, expanded, additional_result=None):
    target = int(case["target_transition"])
    expected_t50 = float(case["expected_t50_v"])
    probabilities = []
    for point_index, offset_lsb in enumerate(POINT_OFFSETS_LSB):
        selected = [
            row
            for row in frames
            if int(row["point_index"]) == point_index and truth(row["valid"])
        ]
        ones = sum(int(float(row["decision_one"])) for row in selected)
        ci_low, ci_high = wilson_interval(ones, len(selected))
        probabilities.append(
            {
                **case,
                "point_index": point_index,
                "offset_lsb": offset_lsb,
                "nominal_vid_v": offset_lsb * LSB_DIFF_V,
                "absolute_vid_v": expected_t50 + offset_lsb * LSB_DIFF_V,
                "trials": FINAL_TRIALS if expanded else INITIAL_TRIALS,
                "valid_count": len(selected),
                "decision_one_count": ones,
                "decision_one_probability": ones / len(selected) if selected else float("nan"),
                "probability_ci95_low": ci_low,
                "probability_ci95_high": ci_high,
                "adaptive_expansion": expanded,
            }
        )
    fit = fit_probit(probabilities)
    expected_sigma = math.hypot(COMPARATOR_SIGMA_V, SAMPLE_SIGMA_V)
    valid_count = sum(truth(row["valid"]) for row in frames)
    trials_per_point = FINAL_TRIALS if expanded else INITIAL_TRIALS
    summary = {
        **case,
        "mismatch_seed": parse_seed(case.get("mismatch_seed")),
        "fitted_t50_v": expected_t50 + fit["vos_v"],
        "t50_error_lsb": abs(fit["vos_v"]) / LSB_DIFF_V,
        "t50_ci95_low_lsb": fit["vos_ci95_low_v"] / LSB_DIFF_V,
        "t50_ci95_high_lsb": fit["vos_ci95_high_v"] / LSB_DIFF_V,
        "fitted_sigma_v": fit["sigma_v"],
        "expected_sigma_v": expected_sigma,
        "sigma_error_fraction": abs(fit["sigma_v"] - expected_sigma) / expected_sigma,
        "sigma_ci95_low_v": fit["sigma_ci95_low_v"],
        "sigma_ci95_high_v": fit["sigma_ci95_high_v"],
        "valid_count": valid_count,
        "invalid_or_timeout_count": len(frames) - valid_count,
        "trials_per_point": trials_per_point,
        "adaptive_expansion": expanded,
        "initial_valid_count": sum(
            truth(row["valid"]) and row["sampling_stage"] == "INITIAL64"
            for row in frames
        ),
        "adaptive_additional_valid_count": sum(
            truth(row["valid"])
            and row["sampling_stage"] == "ADAPTIVE_ADDITIONAL64"
            for row in frames
        ),
        "measurement_maxstep_ps": max(
            float(row["measurement_maxstep_ps"]) for row in frames
        ),
        "measurement_solver_profile": "FRAME_ISOLATED_COMBINED",
    }
    if additional_result is not None:
        summary.update(
            {
                "additional_measurement_stem": additional_result["measurement_stem"],
                "additional_elapsed_s": additional_result["elapsed_s"],
                "additional_wall_elapsed_s": additional_result["wall_elapsed_s"],
                "additional_attempt_count": additional_result["attempt_count"],
            }
        )
    summary["status"] = (
        "PASS"
        if valid_count == len(frames)
        and summary["sigma_error_fraction"] <= 0.15
        and summary["t50_error_lsb"] <= 0.10
        else "FAIL"
    )
    sigma_low = 0.85 * expected_sigma
    sigma_high = 1.15 * expected_sigma
    pass_confirmed = (
        summary["sigma_ci95_low_v"] >= sigma_low
        and summary["sigma_ci95_high_v"] <= sigma_high
        and summary["t50_ci95_low_lsb"] >= -0.10
        and summary["t50_ci95_high_lsb"] <= 0.10
    )
    fail_confirmed = (
        summary["sigma_ci95_high_v"] < sigma_low
        or summary["sigma_ci95_low_v"] > sigma_high
        or summary["t50_ci95_high_lsb"] < -0.10
        or summary["t50_ci95_low_lsb"] > 0.10
    )
    summary["confidence_classification"] = (
        "PASS_CONFIRMED"
        if pass_confirmed
        else "FAIL_CONFIRMED"
        if fail_confirmed
        else "INDETERMINATE_AT_ADAPTIVE_LIMIT"
    )
    summary["confidence_interval_adequate"] = pass_confirmed or fail_confirmed
    return summary, probabilities


def write_reports(summaries):
    status = "PASS" if all(row["status"] == "PASS" for row in summaries) else "FAIL"
    lines = [
        "# Top-Level Selected-Transition Probability",
        "",
        f"- Status: `{status}`",
        "- Evidence class: `T2_TARGET_CALIBRATED_EVENT_NOISE`",
        "- Adaptive policy: initial 64 conversions/point; add 64 when the 95% sigma CI cannot resolve the +/-15% gate.",
        "- Final adaptive ceiling: `128 conversions/point`",
        "",
        "| Die | Seed | Target | Trials/point | Sigma (mV) | Sigma CI95 (mV) | T50 error (LSB) | Confidence | Status |",
        "|---|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['die']} | {row['mismatch_seed']} | {row['target_transition']} | "
            f"{row['trials_per_point']} | {row['fitted_sigma_v']*1e3:.6f} | "
            f"[{row['sigma_ci95_low_v']*1e3:.6f}, {row['sigma_ci95_high_v']*1e3:.6f}] | "
            f"{row['t50_error_lsb']:.6f} | {row['confidence_classification']} | {row['status']} |"
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
    comparator = json.loads(
        (RESULT_DIR / "comparator_noise_calibration.json").read_text(encoding="ascii")
    )
    sample = json.loads(
        (RESULT_DIR / "sample_noise_calibration.json").read_text(encoding="ascii")
    )
    calibration_lines = [
        "# Noise Calibration",
        "",
        f"- Overall Phase G status: `{status}`",
        f"- Comparator calibration: `{comparator['status']}`",
        f"- Sample/CDAC calibration: `{sample['status']}`",
        f"- Top selected-transition probability: `{status}`",
        "- Top probability adaptive sampling: `128 conversions/point for every CI-inadequate case`",
        "- Native MOS transient-noise claim: `NO`",
        "- Evidence tier: `T2_TARGET_CALIBRATED_EVENT_NOISE`",
    ]
    (REPORT_DIR / "noise_calibration.md").write_text(
        "\n".join(calibration_lines) + "\n", encoding="ascii"
    )
    return status


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    archive_initial_outputs()
    _, summary_path, frame_path = initial_paths()
    initial_summaries = read_csv(summary_path)
    initial_frames = normalize_initial_frames(read_csv(frame_path))
    triggers = {
        case_key(row) for row in initial_summaries if not sigma_confidence_adequate(row)
    }
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    additional_by_case = {}
    results_by_case = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_additional_case, row, grouped, timing): row
            for row in initial_summaries
            if case_key(row) in triggers
        }
        for future in as_completed(futures):
            case = futures[future]
            rows, result = future.result()
            key = case_key(case)
            additional_by_case[key] = rows
            results_by_case[key] = result
            print(
                f"TOP_PROB_ADAPT die={key[0]} target={key[1]} "
                f"valid={sum(truth(row['valid']) for row in rows)}/{len(rows)}",
                flush=True,
            )

    frames = []
    summaries = []
    probabilities = []
    for case in initial_summaries:
        key = case_key(case)
        case_frames = [row for row in initial_frames if case_key(row) == key]
        expanded = key in triggers
        if expanded:
            case_frames.extend(additional_by_case[key])
        summary, point_rows = fit_case(
            case, case_frames, expanded, results_by_case.get(key)
        )
        frames.extend(case_frames)
        summaries.append(summary)
        probabilities.extend(point_rows)

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
    status = write_reports(summaries)
    payload = {
        "status": status,
        "model_class": "T2_TARGET_CALIBRATED_EVENT_NOISE",
        "adaptive_expansion_triggered": bool(triggers),
        "adaptive_trigger_case_count": len(triggers),
        "initial_trials_per_point": INITIAL_TRIALS,
        "adaptive_additional_trials_per_point": ADDITIONAL_TRIALS,
        "adaptive_ceiling_trials_per_point": FINAL_TRIALS,
        "sample_sigma_v": SAMPLE_SIGMA_V,
        "comparator_sigma_v": COMPARATOR_SIGMA_V,
        "cases": summaries,
    }
    (RESULT_DIR / "top_transition_probability.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
