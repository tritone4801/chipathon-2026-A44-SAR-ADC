#!/usr/bin/env python3
import csv
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
JOB_DIR = ROOT / "jobs" / "comparator_noise_calibration"
LOG_DIR = ROOT / "logs" / "comparator_noise_calibration"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice")
COMPARATOR = ROOT / "netlists" / "core" / "subckts" / "Comparator_StrongARM_extracted.subckt.spice"
NGSPICE = Path("/foss/tools/bin/ngspice")

LSB_V = 3.4 / 256.0
SIGMA_TARGET_V = 1.5e-3
TRIALS_PER_POINT = 128
VID_POINTS_LSB = (-0.30, -0.15, 0.0, 0.15, 0.30)
SAMPLE_TIME_S = 45e-9
CASES = (
    {
        "case": "TT_VICM_1P6500",
        "model_section": "typical",
        "vdd_v": 3.3,
        "temp_c": 27,
        "vicm_v": 1.6500,
        "noise_seed": 310001,
        "noise_worst_pvt": False,
    },
    {
        "case": "TT_VICM_1P8625",
        "model_section": "typical",
        "vdd_v": 3.3,
        "temp_c": 27,
        "vicm_v": 1.8625,
        "noise_seed": 310002,
        "noise_worst_pvt": False,
    },
    {
        "case": "TT_VICM_2P0750",
        "model_section": "typical",
        "vdd_v": 3.3,
        "temp_c": 27,
        "vicm_v": 2.0750,
        "noise_seed": 310003,
        "noise_worst_pvt": False,
    },
    {
        "case": "SS_3P0_125C_VICM_2P0750",
        "model_section": "ss",
        "vdd_v": 3.0,
        "temp_c": 125,
        "vicm_v": 2.0750,
        "noise_seed": 310004,
        "noise_worst_pvt": True,
    },
    {
        "case": "SS_3P0_125C_VICM_2P0750_REPEAT_B",
        "model_section": "ss",
        "vdd_v": 3.0,
        "temp_c": 125,
        "vicm_v": 2.0750,
        "noise_seed": 310104,
        "noise_worst_pvt": True,
    },
    {
        "case": "SS_3P0_125C_VICM_2P0750_REPEAT_C",
        "model_section": "ss",
        "vdd_v": 3.0,
        "temp_c": 125,
        "vicm_v": 2.0750,
        "noise_seed": 310204,
        "noise_worst_pvt": True,
    },
)


MEASURE_RE = re.compile(
    r"(?im)^\s*([pn])(\d{4})\s*=\s*([-+0-9.eE]+)"
)


def frozen_draws(noise_seed):
    seed_sequence = np.random.SeedSequence([0xA44, 0xC0DE, noise_seed])
    rng = np.random.Generator(np.random.PCG64(seed_sequence))
    return rng.normal(0.0, SIGMA_TARGET_V, (len(VID_POINTS_LSB), TRIALS_PER_POINT))


def make_deck(case, draws):
    instances = []
    measures = []
    mapping = []
    index = 0
    for point_index, vid_lsb in enumerate(VID_POINTS_LSB):
        nominal_vid = vid_lsb * LSB_V
        for trial in range(TRIALS_PER_POINT):
            noise_v = float(draws[point_index, trial])
            actual_vid = nominal_vid + noise_v
            vinp = case["vicm_v"] + actual_vid / 2.0
            vinn = case["vicm_v"] - actual_vid / 2.0
            instances.extend(
                (
                    f"VP{index:04d} ip{index:04d} 0 {vinp:.17g}",
                    f"VN{index:04d} in{index:04d} 0 {vinn:.17g}",
                    f"X{index:04d} clk op{index:04d} ip{index:04d} "
                    f"on{index:04d} in{index:04d} vdd 0 Comparator_StrongARM",
                    f"CP{index:04d} op{index:04d} 0 20f",
                    f"CN{index:04d} on{index:04d} 0 20f",
                )
            )
            measures.extend(
                (
                    f".meas tran p{index:04d} FIND v(op{index:04d}) AT={SAMPLE_TIME_S:.12g}",
                    f".meas tran n{index:04d} FIND v(on{index:04d}) AT={SAMPLE_TIME_S:.12g}",
                )
            )
            mapping.append(
                {
                    "index": index,
                    "point_index": point_index,
                    "trial": trial,
                    "nominal_vid_lsb": vid_lsb,
                    "nominal_vid_v": nominal_vid,
                    "noise_draw_v": noise_v,
                    "actual_vid_v": actual_vid,
                    "vinp_v": vinp,
                    "vinn_v": vinn,
                }
            )
            index += 1
    deck = f"""* StrongARM T2 target-calibrated equivalent-noise probability deck.
.include {PDK / 'design.ngspice'}
.lib {PDK / 'sm141064.ngspice'} {case['model_section']}
.include {COMPARATOR}
.temp {case['temp_c']}
.options klu method=gear reltol=1e-4 abstol=1e-12 vntol=1e-6 trtol=7 maxord=2
VVDD vdd 0 {case['vdd_v']:.12g}
VCLK clk 0 PULSE(0 {case['vdd_v']:.12g} 20n 50p 50p 30n 80n)
{chr(10).join(instances)}
.tran 50p 50n 0 50p
{chr(10).join(measures)}
.end
"""
    return deck, mapping


def parse_measures(log_text, expected_count):
    values = {}
    for prefix, index_text, value_text in MEASURE_RE.findall(log_text):
        values[(prefix, int(index_text))] = float(value_text)
    expected = 2 * expected_count
    if len(values) != expected:
        raise ValueError(f"expected {expected} measures, found {len(values)}")
    return values


def run_case(case, draws, suffix=""):
    stem = case["case"].lower() + suffix
    deck_path = JOB_DIR / f"{stem}.spice"
    log_path = LOG_DIR / f"{stem}.log"
    deck, mapping = make_deck(case, draws)
    if (
        deck_path.exists()
        and log_path.exists()
        and deck_path.read_text(encoding="ascii") == deck
    ):
        try:
            measures = parse_measures(
                log_path.read_text(encoding="utf-8", errors="replace"), len(mapping)
            )
            return mapping, measures, deck_path, log_path
        except ValueError:
            pass
    deck_path.write_text(deck, encoding="ascii")
    completed = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log_path), str(deck_path)],
        cwd=JOB_DIR,
        check=False,
        timeout=600,
    )
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"ngspice failed for {stem}: rc={completed.returncode}")
    measures = parse_measures(log_text, len(mapping))
    return mapping, measures, deck_path, log_path


def decision(vp, vn, vdd):
    high = 0.8 * vdd
    low = 0.2 * vdd
    if vp >= high and vn <= low:
        return 1, "VALID"
    if vn >= high and vp <= low:
        return 0, "VALID"
    if vp >= high and vn >= high:
        return None, "BOTH_HIGH"
    if vp <= low and vn <= low:
        return None, "BOTH_LOW"
    return None, "NOT_AT_RAIL"


def fit_probit(point_rows):
    vids = np.array([row["nominal_vid_v"] for row in point_rows], dtype=float)
    ones = np.array([row["decision_one_count"] for row in point_rows], dtype=float)
    totals = np.array([row["valid_count"] for row in point_rows], dtype=float)

    def objective(params):
        vos, log_sigma = params
        sigma = math.exp(log_sigma)
        probabilities = np.clip(norm.cdf((vids - vos) / sigma), 1e-12, 1.0 - 1e-12)
        return -float(np.sum(ones * np.log(probabilities) + (totals - ones) * np.log(1.0 - probabilities)))

    result = minimize(
        objective,
        np.array([0.0, math.log(SIGMA_TARGET_V)]),
        method="BFGS",
        options={"gtol": 1e-10, "maxiter": 1000},
    )
    if not result.success and not np.isfinite(result.fun):
        raise RuntimeError(f"probit fit failed: {result.message}")
    vos = float(result.x[0])
    sigma = float(math.exp(result.x[1]))
    z_values = (vids - vos) / sigma
    probabilities = np.clip(norm.cdf(z_values), 1e-9, 1.0 - 1e-9)
    densities = norm.pdf(z_values)
    gradients = np.column_stack(
        (-densities / sigma, -densities * z_values)
    )
    fisher_weights = totals / (probabilities * (1.0 - probabilities))
    fisher_information = gradients.T @ (fisher_weights[:, None] * gradients)
    covariance = np.linalg.inv(fisher_information)
    se_vos = math.sqrt(max(0.0, float(covariance[0, 0])))
    se_log_sigma = math.sqrt(max(0.0, float(covariance[1, 1])))
    sigma_ci = (
        sigma * math.exp(-1.96 * se_log_sigma),
        sigma * math.exp(1.96 * se_log_sigma),
    )
    return {
        "vos_v": vos,
        "sigma_v": sigma,
        "vos_ci95_low_v": vos - 1.96 * se_vos,
        "vos_ci95_high_v": vos + 1.96 * se_vos,
        "sigma_ci95_low_v": sigma_ci[0],
        "sigma_ci95_high_v": sigma_ci[1],
        "negative_log_likelihood": float(result.fun),
        "optimizer_success": bool(result.success),
        "optimizer_message": str(result.message),
    }


def wilson_interval(successes, total):
    if total == 0:
        return float("nan"), float("nan")
    z = 1.959963984540054
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return center - half, center + half


def main():
    for directory in (JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    draw_rows = []
    trial_rows = []
    probability_rows = []
    summaries = []
    replay_exact = False

    for case_index, case in enumerate(CASES):
        draws = frozen_draws(case["noise_seed"])
        mapping, measures, deck_path, log_path = run_case(case, draws)
        measured_pairs = []
        for item in mapping:
            index = item["index"]
            vp = measures[("p", index)]
            vn = measures[("n", index)]
            measured_pairs.append((vp, vn))
            bit, state = decision(vp, vn, case["vdd_v"])
            trial_rows.append(
                {
                    "case": case["case"],
                    "model_section": case["model_section"],
                    "vdd_v": case["vdd_v"],
                    "temp_c": case["temp_c"],
                    "vicm_v": case["vicm_v"],
                    "noise_seed": case["noise_seed"],
                    "point_index": item["point_index"],
                    "trial": item["trial"],
                    "nominal_vid_lsb": item["nominal_vid_lsb"],
                    "nominal_vid_v": f"{item['nominal_vid_v']:.17g}",
                    "noise_draw_v": f"{item['noise_draw_v']:.17g}",
                    "actual_vid_v": f"{item['actual_vid_v']:.17g}",
                    "dcmpp_v": f"{vp:.17g}",
                    "dcmpn_v": f"{vn:.17g}",
                    "decision": "" if bit is None else bit,
                    "state": state,
                    "deck": str(deck_path.relative_to(ROOT)),
                    "log": str(log_path.relative_to(ROOT)),
                }
            )
            draw_rows.append(
                {
                    "case": case["case"],
                    "noise_seed": case["noise_seed"],
                    "point_index": item["point_index"],
                    "trial": item["trial"],
                    "noise_draw_v": f"{item['noise_draw_v']:.17g}",
                }
            )

        if case_index == 0:
            _, replay_measures, _, _ = run_case(case, draws, suffix="_replay")
            replay_pairs = [
                (replay_measures[("p", item["index"])], replay_measures[("n", item["index"])])
                for item in mapping
            ]
            replay_exact = measured_pairs == replay_pairs

        case_trials = [row for row in trial_rows if row["case"] == case["case"]]
        point_rows = []
        for point_index, vid_lsb in enumerate(VID_POINTS_LSB):
            selected = [row for row in case_trials if row["point_index"] == point_index]
            valid = [row for row in selected if row["state"] == "VALID"]
            ones = sum(int(row["decision"]) for row in valid)
            low, high = wilson_interval(ones, len(valid))
            point_row = {
                "case": case["case"],
                "model_section": case["model_section"],
                "vdd_v": case["vdd_v"],
                "temp_c": case["temp_c"],
                "vicm_v": case["vicm_v"],
                "noise_seed": case["noise_seed"],
                "nominal_vid_lsb": vid_lsb,
                "nominal_vid_v": vid_lsb * LSB_V,
                "trials": len(selected),
                "valid_count": len(valid),
                "decision_one_count": ones,
                "decision_one_probability": ones / len(valid) if valid else float("nan"),
                "probability_ci95_low": low,
                "probability_ci95_high": high,
                "timeout_count": len(selected) - len(valid),
            }
            point_rows.append(point_row)
            probability_rows.append(point_row)
        fit = fit_probit(point_rows)
        timeout_count = sum(row["state"] != "VALID" for row in case_trials)
        sigma_error = abs(fit["sigma_v"] - SIGMA_TARGET_V) / SIGMA_TARGET_V
        t50_error_lsb = abs(fit["vos_v"]) / LSB_V
        case_pass = sigma_error <= 0.15 and t50_error_lsb <= 0.10 and timeout_count == 0
        summaries.append(
            {
                **case,
                **fit,
                "sigma_target_v": SIGMA_TARGET_V,
                "sigma_error_fraction": sigma_error,
                "t50_error_lsb": t50_error_lsb,
                "trials": len(case_trials),
                "timeout_count": timeout_count,
                "timeout_probability": timeout_count / len(case_trials),
                "status": "PASS" if case_pass else "FAIL",
                "evidence_tier": "T2",
                "model_class": "TARGET_CALIBRATED_EQUIVALENT_NOISE",
            }
        )

    ss_cohort_names = {
        "SS_3P0_125C_VICM_2P0750",
        "SS_3P0_125C_VICM_2P0750_REPEAT_B",
        "SS_3P0_125C_VICM_2P0750_REPEAT_C",
    }
    for item in summaries:
        if item["case"] in ss_cohort_names:
            item["status"] = "PILOT_ONLY"

    combined_case_name = "SS_3P0_125C_VICM_2P0750_COMBINED384"
    combined_trials = [row for row in trial_rows if row["case"] in ss_cohort_names]
    combined_points = []
    for point_index, vid_lsb in enumerate(VID_POINTS_LSB):
        selected = [row for row in combined_trials if row["point_index"] == point_index]
        valid = [row for row in selected if row["state"] == "VALID"]
        ones = sum(int(row["decision"]) for row in valid)
        low, high = wilson_interval(ones, len(valid))
        point_row = {
            "case": combined_case_name,
            "model_section": "ss",
            "vdd_v": 3.0,
            "temp_c": 125,
            "vicm_v": 2.0750,
            "noise_seed": "310004+310104+310204",
            "nominal_vid_lsb": vid_lsb,
            "nominal_vid_v": vid_lsb * LSB_V,
            "trials": len(selected),
            "valid_count": len(valid),
            "decision_one_count": ones,
            "decision_one_probability": ones / len(valid) if valid else float("nan"),
            "probability_ci95_low": low,
            "probability_ci95_high": high,
            "timeout_count": len(selected) - len(valid),
        }
        combined_points.append(point_row)
        probability_rows.append(point_row)
    combined_fit = fit_probit(combined_points)
    combined_timeout_count = sum(row["state"] != "VALID" for row in combined_trials)
    combined_sigma_error = abs(combined_fit["sigma_v"] - SIGMA_TARGET_V) / SIGMA_TARGET_V
    combined_t50_error_lsb = abs(combined_fit["vos_v"]) / LSB_V
    combined_pass = (
        combined_sigma_error <= 0.15
        and combined_t50_error_lsb <= 0.10
        and combined_timeout_count == 0
    )
    summaries.append(
        {
            "case": combined_case_name,
            "model_section": "ss",
            "vdd_v": 3.0,
            "temp_c": 125,
            "vicm_v": 2.0750,
            "noise_seed": "310004+310104+310204",
            "noise_worst_pvt": True,
            **combined_fit,
            "sigma_target_v": SIGMA_TARGET_V,
            "sigma_error_fraction": combined_sigma_error,
            "t50_error_lsb": combined_t50_error_lsb,
            "trials": len(combined_trials),
            "timeout_count": combined_timeout_count,
            "timeout_probability": combined_timeout_count / len(combined_trials),
            "status": "PASS" if combined_pass else "FAIL",
            "evidence_tier": "T2",
            "model_class": "TARGET_CALIBRATED_EQUIVALENT_NOISE",
        }
    )

    all_case_pass = all(
        item["status"] == "PASS"
        for item in summaries
        if item["status"] != "PILOT_ONLY"
    )
    status = "PASS" if all_case_pass and replay_exact else "FAIL"

    def write_csv(path, rows):
        with path.open("w", newline="", encoding="ascii") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(CSV_DIR / "comparator_noise_draws.csv", draw_rows)
    write_csv(CSV_DIR / "comparator_noise_trials.csv", trial_rows)
    write_csv(CSV_DIR / "comparator_noise_probability.csv", probability_rows)
    write_csv(CSV_DIR / "comparator_noise_calibration_summary.csv", summaries)

    payload = {
        "status": status,
        "model_class": "T2_TARGET_CALIBRATED_EQUIVALENT_NOISE",
        "intrinsic_mos_transient_noise_claimed": False,
        "sigma_target_v_rms_diff": SIGMA_TARGET_V,
        "trials_per_point": TRIALS_PER_POINT,
        "vid_points_lsb": list(VID_POINTS_LSB),
        "same_deck_exact_replay": replay_exact,
        "cases": summaries,
        "calibration_gate": {
            "sigma_error_max_fraction": 0.15,
            "t50_error_max_lsb": 0.10,
            "timeout_allowed": 0,
        },
        "simulator_capability_boundary": (
            "ngspice v46 compact-device models do not generate native transient noise; "
            "frozen event draws are applied at the actual transistor-level comparator inputs"
        ),
    }
    (RESULT_DIR / "comparator_noise_calibration.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Comparator Equivalent-Noise Calibration",
        "",
        f"- Status: `{status}`",
        "- Model class: `T2_TARGET_CALIBRATED_EQUIVALENT_NOISE`",
        f"- Target sigma: `{SIGMA_TARGET_V * 1e3:.6f} mVrms,diff`",
        f"- Trials per voltage point: `{TRIALS_PER_POINT}`",
        f"- Same-deck independent-process exact replay: `{'PASS' if replay_exact else 'FAIL'}`",
        "- MOS-native transient-noise claim: `NO`",
        "",
        "## Block-Level Results",
        "",
        "| Case | VICM (V) | Fit sigma (mV) | Sigma error | VOS/T50 (mV) | Sigma 95% CI (mV) | Timeout | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['case']} | {item['vicm_v']:.4f} | {item['sigma_v'] * 1e3:.6f} | "
            f"{item['sigma_error_fraction'] * 100:.3f}% | {item['vos_v'] * 1e3:.6f} | "
            f"[{item['sigma_ci95_low_v'] * 1e3:.6f}, {item['sigma_ci95_high_v'] * 1e3:.6f}] | "
            f"{item['timeout_count']}/{item['trials']} | {item['status']} |"
        )
    lines.extend(
        (
            "",
            "## Method and Boundary",
            "",
            "One frozen Gaussian differential-input draw is used per comparator decision",
            "and is held through the evaluate aperture. The actual GF180 transistor-level",
            "StrongARM and its 20 fF output loads convert those draws into decisions. The",
            "probit fit must recover sigma within 15 percent and T50 within 0.10 LSB.",
            "",
            "The 1.5 mV amplitude is the campaign guardrail, not a measurement of intrinsic",
            "StrongARM device noise. ngspice v46 does not provide compact-device native",
            "transient noise, so this result is calibrated T2 equivalent-noise evidence and",
            "shall not be described as native MOS transient-noise signoff.",
            "",
        )
    )
    (REPORT_DIR / "comparator_noise_calibration.md").write_text(
        "\n".join(lines), encoding="ascii"
    )
    print(json.dumps({"status": status, "replay_exact": replay_exact}, sort_keys=True))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
