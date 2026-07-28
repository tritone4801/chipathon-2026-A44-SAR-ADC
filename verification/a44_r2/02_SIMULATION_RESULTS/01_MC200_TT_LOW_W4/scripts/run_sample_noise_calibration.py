#!/usr/bin/env python3
import csv
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
JOB_DIR = ROOT / "jobs" / "sample_noise_calibration"
LOG_DIR = ROOT / "logs" / "sample_noise_calibration"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice")
SWITCH = ROOT / "netlists" / "core" / "subckts" / "SWITCH_BOOT_SP_native_extracted.subckt.spice"
CDAC = ROOT / "netlists" / "core" / "subckts" / "CDAC_native_extracted.subckt.spice"
NGSPICE = Path("/foss/tools/bin/ngspice")

BOLTZMANN = 1.380649e-23
UNIT_CAP_F = 2.0e-15 * 6.855 * 6.855
ARRAY_UNITS = 128
SOURCE_R_OHM = 105.0
INPUT_LOAD_F = 1.7e-12
OUTPUT_LOAD_F = 20e-15
FMAX_VALUES = (1.0e8, 1.0e9, 1.0e10)
ULTRAWIDE_STRESS_FMAX_HZ = 1.0e12
COMPARATOR_EVENT_NOISE_DIFF_V = 1.5e-3
TOTAL_ANALOG_NOISE_TARGET_DIFF_V = 2.0e-3
EVENT_TRIALS = 128
EVENT_SAMPLE_TIME_S = 150e-9

PVT_CASES = (
    {
        "pvt": "TT_3P3_27C",
        "model_section": "typical",
        "mim_section": "mimcap_typical",
        "vdd_v": 3.3,
        "temp_c": 27,
        "mim_corner_factor": 1.0,
    },
    {
        "pvt": "SS_3P0_125C",
        "model_section": "ss",
        "mim_section": "mimcap_ss",
        "vdd_v": 3.0,
        "temp_c": 125,
        "mim_corner_factor": 1.1,
    },
)
VIN_VALUES = (0.90, 1.65, 2.40)
NOISE_TOTAL_RE = re.compile(
    r"(?im)^\s*(inoise_total|onoise_total)\s*=\s*([-+0-9.eE]+)"
)
EVENT_MEASURE_RE = re.compile(r"(?im)^\s*h(\d{3})\s*=\s*([-+0-9.eE]+)")


def run_ngspice(deck_path, log_path, timeout=120):
    completed = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log_path), str(deck_path)],
        cwd=JOB_DIR,
        check=False,
        timeout=timeout,
    )
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"ngspice failed for {deck_path.name}: rc={completed.returncode}")
    return text


def noise_deck(case, vin_v, fmax_hz):
    return f"""* Actual sampler plus CDAC track-state small-signal noise calibration.
.include {PDK / 'design.ngspice'}
.lib {PDK / 'sm141064.ngspice'} {case['model_section']}
.lib {PDK / 'sm141064.ngspice'} {case['mim_section']}
.include {SWITCH}
.include {CDAC}
.temp {case['temp_c']}
VVDD vdd 0 {case['vdd_v']:.12g}
VREFP vrefp 0 2.5
VREFN vrefn 0 0.8
VCLKS clks 0 {case['vdd_v']:.12g}
VDCTRL dctrl 0 {case['vdd_v']:.12g}
VVIN src 0 DC {vin_v:.12g} AC 1
RDRV src vin {SOURCE_R_OHM:.12g}
CIN vin 0 {INPUT_LOAD_F:.12g}
XCDAC vin clks vtop dctrl dctrl dctrl dctrl dctrl dctrl dctrl vrefp vdd 0 vrefn CDAC
CLOAD vtop 0 {OUTPUT_LOAD_F:.12g}
.noise v(vtop) VVIN dec 40 1 {fmax_hz:.12g}
.control
set noaskquit
run
print inoise_total onoise_total
quit
.endc
.end
"""


def run_noise_case(case, vin_v, fmax_hz):
    vin_label = f"{vin_v:.2f}".replace(".", "p")
    fmax_label = f"{fmax_hz:.0e}".replace("+", "").replace(".", "p")
    stem = f"noise_{case['pvt'].lower()}_vin{vin_label}_fmax{fmax_label}"
    deck_path = JOB_DIR / f"{stem}.spice"
    log_path = LOG_DIR / f"{stem}.log"
    deck = noise_deck(case, vin_v, fmax_hz)
    if not (
        deck_path.exists()
        and log_path.exists()
        and deck_path.read_text(encoding="ascii") == deck
    ):
        deck_path.write_text(deck, encoding="ascii")
        log_text = run_ngspice(deck_path, log_path)
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    values = {name: float(value) for name, value in NOISE_TOTAL_RE.findall(log_text)}
    if set(values) != {"inoise_total", "onoise_total"}:
        raise ValueError(f"noise totals missing for {stem}: {values}")
    return values, deck_path, log_path


def event_draws(seed, sigma_v):
    seed_sequence = np.random.SeedSequence([0xA44, 0x5A4D, seed])
    rng = np.random.Generator(np.random.PCG64(seed_sequence))
    return rng.normal(0.0, sigma_v, EVENT_TRIALS)


def event_deck(case, vin_v, draws):
    instances = []
    measures = []
    for index, draw in enumerate(draws):
        source_v = vin_v + float(draw)
        instances.extend(
            (
                f"VS{index:03d} src{index:03d} 0 {source_v:.17g}",
                f"RS{index:03d} src{index:03d} vin{index:03d} {SOURCE_R_OHM:.12g}",
                f"CI{index:03d} vin{index:03d} 0 {INPUT_LOAD_F:.12g}",
                f"XD{index:03d} vin{index:03d} clks top{index:03d} dctrl dctrl dctrl "
                f"dctrl dctrl dctrl dctrl vrefp vdd 0 vrefn CDAC",
                f"CO{index:03d} top{index:03d} 0 {OUTPUT_LOAD_F:.12g}",
                f"RL{index:03d} top{index:03d} 0 1T",
            )
        )
        measures.append(
            f".meas tran h{index:03d} FIND v(top{index:03d}) AT={EVENT_SAMPLE_TIME_S:.12g}"
        )
    return f"""* Actual sampler plus CDAC frozen one-draw-per-frame event calibration.
.include {PDK / 'design.ngspice'}
.lib {PDK / 'sm141064.ngspice'} {case['model_section']}
.lib {PDK / 'sm141064.ngspice'} {case['mim_section']}
.include {SWITCH}
.include {CDAC}
.temp {case['temp_c']}
.options klu method=gear reltol=1e-4 abstol=1e-12 vntol=1e-6 trtol=7 maxord=2
VVDD vdd 0 {case['vdd_v']:.12g}
VREFP vrefp 0 2.5
VREFN vrefn 0 0.8
VDCTRL dctrl 0 {case['vdd_v']:.12g}
VCLKS clks 0 PULSE(0 {case['vdd_v']:.12g} 20n 5n 5n 100n 200n)
{chr(10).join(instances)}
.tran 50p 170n 0 50p
{chr(10).join(measures)}
.end
"""


def run_event_case(case, vin_v, sigma_v, seed, suffix=""):
    draws = event_draws(seed, sigma_v)
    stem = f"event_{case['pvt'].lower()}_seed{seed}{suffix}"
    deck_path = JOB_DIR / f"{stem}.spice"
    log_path = LOG_DIR / f"{stem}.log"
    deck = event_deck(case, vin_v, draws)
    if not (
        deck_path.exists()
        and log_path.exists()
        and deck_path.read_text(encoding="ascii") == deck
    ):
        deck_path.write_text(deck, encoding="ascii")
        log_text = run_ngspice(deck_path, log_path, timeout=600)
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    measured = {int(index): float(value) for index, value in EVENT_MEASURE_RE.findall(log_text)}
    if len(measured) != EVENT_TRIALS:
        raise ValueError(f"expected {EVENT_TRIALS} event measures, found {len(measured)}")
    outputs = np.array([measured[index] for index in range(EVENT_TRIALS)])
    return draws, outputs, deck_path, log_path


def write_csv(path, rows):
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    for directory in (JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    sweep_rows = []
    final_rows = []
    final_lookup = {}
    for case in PVT_CASES:
        temperature_k = case["temp_c"] + 273.15
        effective_cap_f = (
            ARRAY_UNITS * UNIT_CAP_F * case["mim_corner_factor"] + OUTPUT_LOAD_F
        )
        ktc_leg_v = math.sqrt(BOLTZMANN * temperature_k / effective_cap_f)
        for vin_v in VIN_VALUES:
            by_fmax = {}
            for fmax_hz in FMAX_VALUES:
                values, deck_path, log_path = run_noise_case(case, vin_v, fmax_hz)
                by_fmax[fmax_hz] = values
                sweep_rows.append(
                    {
                        "pvt": case["pvt"],
                        "model_section": case["model_section"],
                        "mim_section": case["mim_section"],
                        "vdd_v": case["vdd_v"],
                        "temp_c": case["temp_c"],
                        "vin_v": vin_v,
                        "fmax_hz": fmax_hz,
                        "onoise_leg_v_rms": f"{values['onoise_total']:.17g}",
                        "inoise_v_rms": f"{values['inoise_total']:.17g}",
                        "deck": str(deck_path.relative_to(ROOT)),
                        "log": str(log_path.relative_to(ROOT)),
                        "classification": "CALIBRATION_BAND",
                    }
                )
            final = by_fmax[FMAX_VALUES[-1]]
            convergence = abs(final["onoise_total"] - by_fmax[FMAX_VALUES[-2]]["onoise_total"]) / final["onoise_total"]
            differential_noise = math.sqrt(2.0) * final["onoise_total"]
            stress_values, stress_deck_path, stress_log_path = run_noise_case(
                case, vin_v, ULTRAWIDE_STRESS_FMAX_HZ
            )
            sweep_rows.append(
                {
                    "pvt": case["pvt"],
                    "model_section": case["model_section"],
                    "mim_section": case["mim_section"],
                    "vdd_v": case["vdd_v"],
                    "temp_c": case["temp_c"],
                    "vin_v": vin_v,
                    "fmax_hz": ULTRAWIDE_STRESS_FMAX_HZ,
                    "onoise_leg_v_rms": f"{stress_values['onoise_total']:.17g}",
                    "inoise_v_rms": f"{stress_values['inoise_total']:.17g}",
                    "deck": str(stress_deck_path.relative_to(ROOT)),
                    "log": str(stress_log_path.relative_to(ROOT)),
                    "classification": "ULTRAWIDE_MODEL_SENSITIVITY",
                }
            )
            stress_differential_noise = math.sqrt(2.0) * stress_values["onoise_total"]
            combined_noise = math.hypot(COMPARATOR_EVENT_NOISE_DIFF_V, differential_noise)
            combined_stress_noise = math.hypot(
                COMPARATOR_EVENT_NOISE_DIFF_V, stress_differential_noise
            )
            row = {
                "pvt": case["pvt"],
                "model_section": case["model_section"],
                "mim_section": case["mim_section"],
                "vdd_v": case["vdd_v"],
                "temp_c": case["temp_c"],
                "vin_v": vin_v,
                "integration_fmin_hz": 1.0,
                "integration_fmax_hz": FMAX_VALUES[-1],
                "sampled_noise_leg_v_rms": final["onoise_total"],
                "sampled_noise_diff_v_rms": differential_noise,
                "ultrawide_stress_fmax_hz": ULTRAWIDE_STRESS_FMAX_HZ,
                "ultrawide_stress_noise_leg_v_rms": stress_values["onoise_total"],
                "ultrawide_stress_noise_diff_v_rms": stress_differential_noise,
                "combined_comparator_sample_noise_diff_v_rms": combined_noise,
                "combined_ultrawide_stress_noise_diff_v_rms": combined_stress_noise,
                "total_analog_noise_target_diff_v_rms": TOTAL_ANALOG_NOISE_TARGET_DIFF_V,
                "ktc_leg_v_rms": ktc_leg_v,
                "ktc_diff_v_rms": math.sqrt(2.0) * ktc_leg_v,
                "measured_to_ktc_ratio": final["onoise_total"] / ktc_leg_v,
                "fmax_1g_to_10g_change_fraction": convergence,
                "bandwidth_endpoint_status": (
                    "CONVERGED" if convergence <= 0.15 else "OPEN_MODEL_BANDWIDTH_SENSITIVITY"
                ),
                "status": (
                    "PASS"
                    if combined_stress_noise <= TOTAL_ANALOG_NOISE_TARGET_DIFF_V
                    else "FAIL"
                ),
                "evidence_tier": "T0_BLOCK_NOISE_PLUS_T1_KTC",
            }
            final_rows.append(row)
            final_lookup[(case["pvt"], vin_v)] = row

    event_rows = []
    event_trial_rows = []
    replay_exact = False
    for case_index, case in enumerate(PVT_CASES):
        electrical = final_lookup[(case["pvt"], 1.65)]
        sigma_leg = float(electrical["sampled_noise_leg_v_rms"])
        seed = 320001 + case_index
        draws, outputs, deck_path, log_path = run_event_case(case, 1.65, sigma_leg, seed)
        slope, intercept = np.polyfit(draws, outputs, 1)
        measured_sigma = float(np.std(outputs - np.mean(outputs), ddof=1))
        realized_draw_sigma = float(np.std(draws, ddof=1))
        expected_output_sigma = abs(float(slope)) * realized_draw_sigma
        calibration_error = abs(measured_sigma - expected_output_sigma) / expected_output_sigma
        finite_sample_target_error = abs(realized_draw_sigma - sigma_leg) / sigma_leg
        calibrated_input_sigma = measured_sigma / abs(float(slope))
        if case_index == 0:
            replay_draws, replay_outputs, _, _ = run_event_case(
                case, 1.65, sigma_leg, seed, suffix="_replay"
            )
            replay_exact = np.array_equal(draws, replay_draws) and np.array_equal(
                outputs, replay_outputs
            )
        event_rows.append(
            {
                "pvt": case["pvt"],
                "noise_seed": seed,
                "trials": EVENT_TRIALS,
                "electrical_target_leg_v_rms": sigma_leg,
                "event_input_leg_v_rms": sigma_leg,
                "measured_output_leg_v_rms": measured_sigma,
                "realized_input_draw_v_rms": realized_draw_sigma,
                "fitted_dc_gain": slope,
                "fitted_intercept_v": intercept,
                "expected_output_from_gain_v_rms": expected_output_sigma,
                "calibrated_input_leg_v_rms": calibrated_input_sigma,
                "calibration_error_fraction": calibration_error,
                "finite_sample_target_error_fraction": finite_sample_target_error,
                "status": "PASS" if calibration_error <= 0.15 else "FAIL",
                "deck": str(deck_path.relative_to(ROOT)),
                "log": str(log_path.relative_to(ROOT)),
                "evidence_tier": "T2_EVENT_MODEL_ON_ACTUAL_BLOCK",
            }
        )
        for index, (draw, output) in enumerate(zip(draws, outputs)):
            event_trial_rows.append(
                {
                    "pvt": case["pvt"],
                    "noise_seed": seed,
                    "trial": index,
                    "event_input_draw_v": f"{float(draw):.17g}",
                    "sampled_output_v": f"{float(output):.17g}",
                }
            )

    tt_values = [
        float(row["sampled_noise_diff_v_rms"])
        for row in final_rows
        if row["pvt"] == "TT_3P3_27C"
    ]
    ss_values = [
        float(row["sampled_noise_diff_v_rms"])
        for row in final_rows
        if row["pvt"] == "SS_3P0_125C"
    ]
    input_dependence = (max(tt_values) - min(tt_values)) / np.mean(tt_values)
    pvt_change = (
        final_lookup[("SS_3P0_125C", 1.65)]["sampled_noise_diff_v_rms"]
        / final_lookup[("TT_3P3_27C", 1.65)]["sampled_noise_diff_v_rms"]
        - 1.0
    )
    worst_diff_noise = max(tt_values + ss_values)
    worst_ultrawide_stress_noise = max(
        float(row["ultrawide_stress_noise_diff_v_rms"]) for row in final_rows
    )
    worst_combined_noise = max(
        float(row["combined_comparator_sample_noise_diff_v_rms"])
        for row in final_rows
    )
    worst_combined_stress_noise = max(
        float(row["combined_ultrawide_stress_noise_diff_v_rms"])
        for row in final_rows
    )
    all_final_pass = all(row["status"] == "PASS" for row in final_rows)
    all_event_pass = all(row["status"] == "PASS" for row in event_rows)
    status = "PASS" if all_final_pass and all_event_pass and replay_exact else "FAIL"

    write_csv(CSV_DIR / "sample_noise_frequency_sweep.csv", sweep_rows)
    write_csv(CSV_DIR / "sample_noise.csv", final_rows)
    write_csv(CSV_DIR / "sample_noise_event_validation.csv", event_rows)
    write_csv(CSV_DIR / "sample_noise_event_trials.csv", event_trial_rows)

    payload = {
        "status": status,
        "electrical_evidence": "actual sampler plus 128-unit CDAC track-state .noise",
        "event_model": "one Gaussian draw per frame held through conversion",
        "source_resistance_ohm_included": SOURCE_R_OHM,
        "input_amplitude_dependence_fraction_tt": float(input_dependence),
        "ss125c_vs_tt27c_midscale_change_fraction": float(pvt_change),
        "worst_sample_noise_diff_v_rms": float(worst_diff_noise),
        "worst_ultrawide_stress_sample_noise_diff_v_rms": worst_ultrawide_stress_noise,
        "worst_combined_comparator_sample_noise_diff_v_rms": worst_combined_noise,
        "worst_combined_ultrawide_stress_noise_diff_v_rms": worst_combined_stress_noise,
        "total_analog_noise_target_diff_v_rms": TOTAL_ANALOG_NOISE_TARGET_DIFF_V,
        "same_seed_exact_replay": replay_exact,
        "reference_noise_model": "EXCLUDED; ideal reference sources with deterministic recorded impedance and decoupling",
        "final_rows": final_rows,
        "event_validation": event_rows,
        "claim_boundary": (
            "T0 stationary block .noise plus T1 kT/C and T2 event-model calibration; "
            "not compact-device native transient noise"
        ),
    }
    (RESULT_DIR / "sample_noise_calibration.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Sample and CDAC Noise Calibration",
        "",
        f"- Status: `{status}`",
        "- Electrical block: actual bootstrapped sampler plus actual 128-unit CDAC",
        f"- Input source resistance included: `{SOURCE_R_OHM:.0f} ohm`",
        f"- Worst measured differential sample noise: `{worst_diff_noise * 1e6:.6f} uVrms`",
        f"- Worst 1 THz model-sensitivity sample noise: `{worst_ultrawide_stress_noise * 1e6:.6f} uVrms,diff`",
        f"- Worst comparator-plus-sample noise: `{worst_combined_noise * 1e3:.6f} mVrms,diff`",
        f"- Worst comparator-plus-1 THz sensitivity: `{worst_combined_stress_noise * 1e3:.6f} mVrms,diff`",
        f"- TT input-amplitude dependence: `{input_dependence * 100:.3f}%`",
        f"- SS/125C versus TT/27C midscale change: `{pvt_change * 100:.3f}%`",
        f"- Same-seed event replay: `{'PASS' if replay_exact else 'FAIL'}`",
        "",
        "## Electrical and kT/C Results",
        "",
        "| PVT | VIN (V) | Electrical diff noise (uV) | 1 THz sensitivity (uV) | kT/C diff (uV) | 1G-to-10G change | Bandwidth status | Gate |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in final_rows:
        lines.append(
            f"| {row['pvt']} | {row['vin_v']:.2f} | {row['sampled_noise_diff_v_rms'] * 1e6:.6f} | "
            f"{row['ultrawide_stress_noise_diff_v_rms'] * 1e6:.6f} | "
            f"{row['ktc_diff_v_rms'] * 1e6:.6f} | "
            f"{row['fmax_1g_to_10g_change_fraction'] * 100:.3f}% | "
            f"{row['bandwidth_endpoint_status']} | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "## Frozen Event-Model Validation",
            "",
            "| PVT | Trials | Target leg noise (uV) | Realized draw sigma (uV) | Measured output sigma (uV) | Gain | Transfer error | Status |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        )
    )
    for row in event_rows:
        lines.append(
            f"| {row['pvt']} | {row['trials']} | {row['electrical_target_leg_v_rms'] * 1e6:.6f} | "
            f"{row['realized_input_draw_v_rms'] * 1e6:.6f} | "
            f"{row['measured_output_leg_v_rms'] * 1e6:.6f} | {row['fitted_dc_gain']:.6f} | "
            f"{row['calibration_error_fraction'] * 100:.3f}% | {row['status']} |"
        )
    lines.extend(
        (
            "",
            "## Boundary",
            "",
            "The stationary `.noise` analysis uses GF180 compact-device noise in the",
            "actual track-state block. The kT/C values are first-order T1 checks. The",
            "1 Hz to 10 GHz endpoint is the recorded calibration band. Its upper-band",
            "sensitivity is explicitly not classified as converged. A separate 1 THz",
            "compact-model extrapolation is retained only as a conservative stress",
            "envelope; even that envelope remains below the 2 mVrms,diff total budget",
            "when combined in quadrature with the 1.5 mVrms,diff comparator model. The",
            "bulk event model uses one frozen Gaussian sample draw per frame. ngspice",
            "compact devices do not generate native transient noise, so no native MOS",
            "transient-noise claim is made. Reference temporal noise is excluded; the",
            "recorded deterministic reference impedance and decoupling remain in the",
            "top-level fixture.",
            "",
        )
    )
    (REPORT_DIR / "sample_noise_calibration.md").write_text(
        "\n".join(lines), encoding="ascii"
    )
    print(json.dumps({"status": status, "worst_diff_noise_v": worst_diff_noise}, sort_keys=True))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
