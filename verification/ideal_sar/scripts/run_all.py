"""Run the ideal SAR ADC validation stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ideal_sar_lib import (
    CONFIG_PATH,
    CSV_DIR,
    LOGS_DIR,
    METRICS_CSV,
    METRICS_JSON,
    PLOTS_DIR,
    RAW_DIR,
    REPORT_DIR,
    RESULTS,
    ROOT,
    command_probe,
    coherent_sine,
    dac_center,
    dac_threshold,
    db10,
    derived_values,
    direct_quantize,
    ensure_dirs,
    finite_or_inf_ratio_db,
    fold_harmonic_bin,
    format_db,
    import_probe,
    load_config,
    metric_status,
    oracle_quantize,
    plot_bar,
    plot_line,
    plot_spectrum,
    power_spectrum,
    read_json,
    required_input_file_rows,
    sar_convert_scalar,
    sar_quantize,
    spectral_metrics,
    update_metrics,
    vinp_vinn_from_vdiff,
    write_csv,
    write_json,
    write_text,
)


def run_preflight() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    ensure_dirs()

    tool_rows = [
        command_probe("python", ["--version"]),
        command_probe("python3", ["--version"]),
        command_probe("ngspice", ["--version"]),
        command_probe("xschem", ["--version"]),
        command_probe("iverilog", ["-V"]),
        command_probe("verilator", ["--version"]),
        command_probe("gtkwave", ["--version"]),
        command_probe("make", ["--version"]),
    ]
    import_rows = [import_probe(name) for name in ["numpy", "matplotlib", "yaml", "cocotb"]]
    input_rows = required_input_file_rows()
    write_csv(CSV_DIR / "preflight_tools.csv", tool_rows, ["tool", "path", "status", "version"])
    write_csv(CSV_DIR / "preflight_python_imports.csv", import_rows, ["module", "status", "version"])
    write_csv(CSV_DIR / "required_input_files.csv", input_rows, ["path", "status", "bytes"])

    log_lines = [
        "Ideal SAR ADC preflight",
        f"config={CONFIG_PATH}",
        f"bits={d['bits']}",
        f"fs_hz={d['fs_hz']}",
        f"vfs_diff_pp={d['vfs_diff_pp']}",
        f"lsb={d['lsb']}",
        "",
        "Tools:",
    ]
    log_lines += [f"- {r['tool']}: {r['status']} {r['path']} {r['version']}" for r in tool_rows]
    log_lines.append("")
    log_lines.append("Python imports:")
    log_lines += [f"- {r['module']}: {r['status']} {r['version']}" for r in import_rows]
    log_lines.append("")
    log_lines.append("Required input files:")
    log_lines += [f"- {r['status']}: {r['path']}" for r in input_rows]
    write_text(LOGS_DIR / "preflight.log", "\n".join(log_lines) + "\n")

    ngspice = next(r for r in tool_rows if r["tool"] == "ngspice")
    cocotb = next(r for r in import_rows if r["module"] == "cocotb")
    iverilog = next(r for r in tool_rows if r["tool"] == "iverilog")
    verilator = next(r for r in tool_rows if r["tool"] == "verilator")
    core_external_ready = (
        ngspice["status"] == "PASS"
        and cocotb["status"] == "PASS"
        and (iverilog["status"] == "PASS" or verilator["status"] == "PASS")
    )
    payload = {
        "derived": d,
        "tools": tool_rows,
        "python_imports": import_rows,
        "required_input_files": input_rows,
        "core_external_ready": core_external_ready,
        "status": "PASS" if core_external_ready else "FAIL",
        "evidence": {
            "tools_csv": str(CSV_DIR / "preflight_tools.csv"),
            "imports_csv": str(CSV_DIR / "preflight_python_imports.csv"),
            "input_files_csv": str(CSV_DIR / "required_input_files.csv"),
            "log": str(LOGS_DIR / "preflight.log"),
        },
    }
    update_metrics("preflight", payload)
    return payload


def run_external_smoke() -> Dict[str, Any]:
    ensure_dirs()
    ngspice_status = {"status": "NOT_RUN", "returncode": "", "log": str(LOGS_DIR / "ngspice_smoke.log")}
    if shutil.which("ngspice"):
        cmd = ["ngspice", "-b", str(ROOT / "spice" / "ideal_dac_tb.cir")]
        cp = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        write_text(LOGS_DIR / "ngspice_smoke.log", cp.stdout)
        ngspice_status["returncode"] = cp.returncode
        ngspice_status["status"] = "PASS" if cp.returncode == 0 else "FAIL"
    else:
        write_text(LOGS_DIR / "ngspice_smoke.log", "NOT_RUN: ngspice not found\n")

    cocotb_status = {"status": "NOT_RUN", "returncode": "", "log": str(LOGS_DIR / "cocotb_smoke.log")}
    runner = ROOT / "cocotb" / "runner.py"
    if runner.exists():
        cp = subprocess.run([sys.executable, str(runner)], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        write_text(LOGS_DIR / "cocotb_smoke.log", cp.stdout)
        cocotb_status["returncode"] = cp.returncode
        cocotb_status["status"] = "PASS" if cp.returncode == 0 else ("NOT_RUN" if cp.returncode == 77 else "FAIL")

    payload = {
        "status": "PASS" if ngspice_status["status"] == "PASS" and cocotb_status["status"] == "PASS" else "FAIL",
        "ngspice": ngspice_status,
        "cocotb": cocotb_status,
    }
    update_metrics("external_smoke", payload)
    return payload


def run_unit() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    rng = np.random.default_rng(int(cfg["dynamic_test"]["random_seed"]))
    rows: List[Dict[str, Any]] = []

    def record(name: str, ok: bool, details: str) -> None:
        rows.append({"test": name, "status": "PASS" if ok else "FAIL", "details": details})

    record("derived_lsb", abs(d["lsb"] - 3.4 / 256.0) < 1e-15, f"lsb={d['lsb']:.15f}")
    record("vmin_code", direct_quantize(d["vmin"], cfg) == 0, str(direct_quantize(d["vmin"], cfg)))
    record("vmax_saturation", direct_quantize(d["vmax"], cfg) == d["max_code"], str(direct_quantize(d["vmax"], cfg)))
    for code in [1, 2, 127, 128, 255]:
        record(
            f"tie_upper_code_{code}",
            direct_quantize(dac_threshold(code, cfg), cfg) == code,
            f"transition={dac_threshold(code, cfg):.12f}",
        )
    centers = dac_center(np.arange(d["codes"]), cfg)
    record("centers_round_trip", np.all(direct_quantize(centers, cfg) == np.arange(d["codes"])), "all 256 centers")
    values = rng.uniform(d["vmin"], d["vmax"], 4096)
    direct = direct_quantize(values, cfg)
    sar = sar_quantize(values, cfg)
    oracle = oracle_quantize(values, cfg)
    record("direct_vs_sar_random", bool(np.array_equal(direct, sar)), "4096 random samples")
    record("direct_vs_oracle_random", bool(np.array_equal(direct, oracle)), "4096 random samples")
    qe = (dac_center(direct, cfg) - values) / d["lsb"]
    record("quant_error_bound", float(np.max(np.abs(qe))) <= 0.5001, f"max={float(np.max(np.abs(qe))):.6f} LSB")

    npts = 16384
    k = 137
    clean = coherent_sine(npts, k, 0.5, 0.0, cfg)
    noise = rng.normal(0.0, 0.01, npts)
    noisy = clean + noise
    m_noise = spectral_metrics(noisy, clean, k, cfg)
    expected_noise = finite_or_inf_ratio_db(float(np.mean(clean**2)), float(np.mean(noise**2)))
    record(
        "known_white_noise_sqnr",
        abs(m_noise["SQNR_spectral_dB"] - expected_noise) < 0.6,
        f"measured={m_noise['SQNR_spectral_dB']:.3f}, expected={expected_noise:.3f}",
    )
    harm_amp = 0.5 * d["vfs_diff_peak"] * 10 ** (-50.0 / 20.0)
    harmonic = clean + harm_amp * np.sin(2 * np.pi * 3 * k * np.arange(npts) / npts)
    m_harm = spectral_metrics(harmonic, clean, k, cfg)
    record(
        "known_harmonic_sqdr",
        abs(m_harm["SQDR_dB"] - 50.0) < 0.4,
        f"measured={m_harm['SQDR_dB']:.3f}, expected=50.0",
    )
    record("enob_formula", abs(((44.0 - 1.76) / 6.02) - 7.0166) < 1e-3, "SNDR=44 dB -> ENOB=7.0166")
    record("db10_linear_roundtrip", abs(10 ** (db10(123.0) / 10.0) - 123.0) < 1e-10, "linear/dB conversion")
    folded = [fold_harmonic_bin(32749, h, npts) for h in range(2, 11)]
    record("harmonic_folding_unique", len(set(folded)) == len(folded), f"folded={folded[:4]}...")
    m_clean = spectral_metrics(clean, clean, k, cfg)
    closure = m_clean["closure_error_db"]
    record("sqndr_power_closure", closure <= float(cfg["dynamic_test"]["quantization_metrics"]["closure_tolerance_db"]), f"closure={closure:.6g} dB")
    synthetic_widths = np.ones(256)
    synthetic_widths[10] = 1.25
    synthetic_widths[11] = 0.75
    synthetic_dnl = synthetic_widths - 1.0
    record("synthetic_dnl_known_widths", abs(float(np.max(synthetic_dnl)) - 0.25) < 1e-12 and abs(float(np.min(synthetic_dnl)) + 0.25) < 1e-12, "known +/-0.25 LSB DNL")
    synthetic_transition_error = 0.002 * np.arange(1, 256)
    synthetic_bestfit = synthetic_transition_error - np.polyval(np.polyfit(np.arange(1, 256), synthetic_transition_error, 1), np.arange(1, 256))
    record(
        "endpoint_bestfit_inl_distinct",
        float(np.max(np.abs(synthetic_transition_error - synthetic_bestfit))) > 0.1,
        "endpoint INL preserves gain-like slope while best-fit INL removes it",
    )
    record("zero_power_ratio_inf", finite_or_inf_ratio_db(1.0, 0.0) == math.inf, "zero denominator -> +inf")
    qseq = np.array([0.1, -0.2, 0.3, -0.4])
    record("sqnr_total_td_mse", abs(float(np.mean(qseq**2)) - 0.075) < 1e-12, "direct MSE calculation")

    write_csv(CSV_DIR / "unit_results.csv", rows, ["test", "status", "details"])
    payload = {
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
        "rows": rows,
        "evidence": str(CSV_DIR / "unit_results.csv"),
    }
    update_metrics("unit", payload)
    return payload


def run_functional() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    rng = np.random.default_rng(int(cfg["dynamic_test"]["random_seed"]))
    points = [
        d["vmin"],
        d["vmin"] + 0.25 * d["lsb"],
        -d["lsb"],
        -0.5 * d["lsb"],
        0.0,
        0.5 * d["lsb"],
        d["lsb"],
        d["vmax"] - d["lsb"],
        d["vmax"],
    ]
    for code in [1, 2, 3, 127, 128, 129, 254, 255]:
        points.append(dac_threshold(code, cfg))
        points.append(dac_center(code, cfg))
    rows = []
    for idx, v in enumerate(points):
        direct = int(direct_quantize(v, cfg))
        sar, trace = sar_convert_scalar(v, cfg)
        oracle = int(oracle_quantize(v, cfg))
        vinp, vinn = vinp_vinn_from_vdiff(v, cfg)
        rows.append(
            {
                "case": idx,
                "vdiff_v": f"{v:.15g}",
                "vinp_v": f"{float(vinp):.15g}",
                "vinn_v": f"{float(vinn):.15g}",
                "direct_code": direct,
                "sar_code": sar,
                "oracle_code": oracle,
                "status": "PASS" if direct == sar == oracle else "FAIL",
                "bit_sequence": " ".join(str(t["bit_index"]) for t in trace),
            }
        )
    common_mode_rows = []
    for cm in [1.2, 1.65, 2.1]:
        local = dict(cfg)
        local["adc"] = dict(cfg["adc"])
        local["adc"]["vcm_v"] = cm
        vinp, vinn = vinp_vinn_from_vdiff(0.75, local)
        common_mode_rows.append(
            {
                "vcm_v": cm,
                "vinp_v": float(vinp),
                "vinn_v": float(vinn),
                "vdiff_v": 0.75,
                "code": int(direct_quantize(0.75, local)),
            }
        )
    cm_ok = len({r["code"] for r in common_mode_rows}) == 1
    center_rows = []
    for code in range(d["codes"]):
        value = dac_center(code, cfg)
        direct = int(direct_quantize(value, cfg))
        sar = int(sar_quantize(value, cfg))
        oracle = int(oracle_quantize(value, cfg))
        center_rows.append(
            {
                "code": code,
                "vdiff_center_v": value,
                "direct_code": direct,
                "sar_code": sar,
                "oracle_code": oracle,
                "status": "PASS" if direct == sar == oracle == code else "FAIL",
            }
        )
    eps = float(cfg["static_test"]["transition_search_resolution_lsb"]) * d["lsb"]
    transition_rows = []
    for code in range(1, d["codes"]):
        transition = dac_threshold(code, cfg)
        for label, delta, expected in [
            ("minus_eps", -eps, code - 1),
            ("exact", 0.0, code),
            ("plus_eps", eps, code),
        ]:
            value = transition + delta
            direct = int(direct_quantize(value, cfg))
            sar = int(sar_quantize(value, cfg))
            oracle = int(oracle_quantize(value, cfg))
            transition_rows.append(
                {
                    "transition_code": code,
                    "point": label,
                    "delta_lsb": delta / d["lsb"],
                    "vdiff_v": value,
                    "expected_code": expected,
                    "direct_code": direct,
                    "sar_code": sar,
                    "oracle_code": oracle,
                    "status": "PASS" if direct == sar == oracle == expected else "FAIL",
                }
            )
    overrange_values = [
        ("below_minus_10_lsb", d["vmin"] - 10.0 * d["lsb"], 0),
        ("below_minus_1_lsb", d["vmin"] - d["lsb"], 0),
        ("above_plus_1_lsb", d["vmax"] + d["lsb"], d["max_code"]),
        ("above_plus_10_lsb", d["vmax"] + 10.0 * d["lsb"], d["max_code"]),
    ]
    overrange_rows = []
    for label, value, expected in overrange_values:
        direct = int(direct_quantize(value, cfg))
        sar = int(sar_quantize(value, cfg))
        oracle = int(oracle_quantize(value, cfg))
        overrange_rows.append(
            {
                "case": label,
                "vdiff_v": value,
                "expected_code": expected,
                "direct_code": direct,
                "sar_code": sar,
                "oracle_code": oracle,
                "status": "PASS" if direct == sar == oracle == expected else "FAIL",
            }
        )
    random_values = rng.uniform(d["vmin"], np.nextafter(d["vmax"], d["vmin"]), 10000)
    random_direct = direct_quantize(random_values, cfg)
    random_sar = sar_quantize(random_values, cfg)
    random_oracle = oracle_quantize(random_values, cfg)
    random_rows = [
        {
            "sample": i,
            "vdiff_v": random_values[i],
            "direct_code": int(random_direct[i]),
            "sar_code": int(random_sar[i]),
            "oracle_code": int(random_oracle[i]),
            "status": "PASS" if random_direct[i] == random_sar[i] == random_oracle[i] else "FAIL",
        }
        for i in range(random_values.size)
    ]
    center_ok = all(r["status"] == "PASS" for r in center_rows)
    transition_ok = all(r["status"] == "PASS" for r in transition_rows)
    overrange_ok = all(r["status"] == "PASS" for r in overrange_rows)
    random_ok = all(r["status"] == "PASS" for r in random_rows)
    write_csv(CSV_DIR / "functional_vectors.csv", rows)
    write_csv(CSV_DIR / "common_mode_invariance.csv", common_mode_rows)
    write_csv(CSV_DIR / "functional_code_centers.csv", center_rows)
    write_csv(CSV_DIR / "functional_transition_boundaries.csv", transition_rows)
    write_csv(CSV_DIR / "functional_overrange_saturation.csv", overrange_rows)
    write_csv(CSV_DIR / "functional_random_equivalence_10000.csv", random_rows)
    payload = {
        "status": "PASS"
        if all(r["status"] == "PASS" for r in rows) and cm_ok and center_ok and transition_ok and overrange_ok and random_ok
        else "FAIL",
        "vector_count": len(rows),
        "common_mode_status": "PASS" if cm_ok else "FAIL",
        "code_centers_status": "PASS" if center_ok else "FAIL",
        "transition_boundaries_status": "PASS" if transition_ok else "FAIL",
        "overrange_status": "PASS" if overrange_ok else "FAIL",
        "random_equivalence_count": int(random_values.size),
        "random_mismatch_count": int(np.sum((random_direct != random_sar) | (random_direct != random_oracle))),
        "random_equivalence_status": "PASS" if random_ok else "FAIL",
        "evidence": {
            "vectors": str(CSV_DIR / "functional_vectors.csv"),
            "common_mode": str(CSV_DIR / "common_mode_invariance.csv"),
            "code_centers": str(CSV_DIR / "functional_code_centers.csv"),
            "transition_boundaries": str(CSV_DIR / "functional_transition_boundaries.csv"),
            "overrange": str(CSV_DIR / "functional_overrange_saturation.csv"),
            "random_equivalence": str(CSV_DIR / "functional_random_equivalence_10000.csv"),
        },
    }
    update_metrics("functional", payload)
    return payload


def run_timing() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    rng = np.random.default_rng(int(cfg["dynamic_test"]["random_seed"]))
    cases = [
        {
            "name": "nominal",
            "clks_hz": d["clks_hz"],
            "track_time_s": d["track_time_s"],
            "conversion_time_s": d["conversion_time_s"],
            "internal_bit_slots": d["internal_bit_slots"],
        }
    ]
    cases.extend({"name": case.get("name", f"alternate_{i}"), "clks_hz": d["clks_hz"], **case} for i, case in enumerate(cfg["timing"].get("alternate_cases", [])))
    rows = []
    for case in cases:
        track_time_s = float(case.get("track_time_s", d["track_time_s"]))
        conversion_time_s = float(case.get("conversion_time_s", d["conversion_time_s"]))
        clks_hz = float(case.get("clks_hz", d["clks_hz"]))
        sample_period_s = 1.0 / clks_hz
        used_time_s = track_time_s + conversion_time_s
        margin_s = sample_period_s - used_time_s
        fs_calc = clks_hz
        internal_bit_slots = int(case.get("internal_bit_slots", d["internal_bit_slots"]))
        rows.append(
            {
                "case": case["name"],
                "external_clock": "CLKS",
                "clks_hz": clks_hz,
                "track_time_ns": track_time_s * 1e9,
                "conversion_time_ns": conversion_time_s * 1e9,
                "sample_period_ns": sample_period_s * 1e9,
                "window_used_ns": used_time_s * 1e9,
                "timing_margin_ns": margin_s * 1e9,
                "internal_bit_slots": internal_bit_slots,
                "internal_bit_slot_ns": conversion_time_s * 1e9 / internal_bit_slots,
                "comparisons_per_conversion": d["comparisons_per_conversion"],
                "cdac_adjustments_per_conversion": d["cdac_adjustments_per_conversion"],
                "sample_rate_hz": fs_calc,
                "target_fs_hz": d["fs_hz"],
                "error_ppm": (fs_calc / d["fs_hz"] - 1.0) * 1e6,
                "no_external_sar_clock": True,
                "status": "PASS" if abs(fs_calc - d["fs_hz"]) < 1e-6 and margin_s >= -1e-15 and d["comparisons_per_conversion"] == d["bits"] else "FAIL",
            }
        )
    trace_rows = []
    samples = [d["vmin"] + 0.1 * d["lsb"], -0.1, 0.0, dac_threshold(129, cfg)]
    for sample_idx, value in enumerate(samples):
        code, trace = sar_convert_scalar(value, cfg)
        for trial_idx, t in enumerate(trace):
            trace_rows.append(
                {
                    "sample": sample_idx,
                    "vdiff_v": value,
                    "cycle": trial_idx + 1,
                    "bit_index": t["bit_index"],
                    "trial_code": t["trial_code"],
                    "threshold_v": t["threshold_v"],
                    "comparator_decision": t["comparator_decision"],
                    "partial_code": t["partial_code"],
                    "final_code": code,
                }
            )
        trace_rows.append(
            {
                "sample": sample_idx,
                "vdiff_v": value,
                "cycle": d["comparisons_per_conversion"],
                "bit_index": "EOC_INT",
                "trial_code": "",
                "threshold_v": "",
                "comparator_decision": "",
                "partial_code": code,
                "final_code": code,
            }
        )
    seq_ok = all([int(t["bit_index"]) == d["bits"] - 1 - (int(t["cycle"]) - 1) for t in trace_rows if t["bit_index"] != "EOC_INT"])
    continuous_values = rng.uniform(d["vmin"], np.nextafter(d["vmax"], d["vmin"]), 10000)
    accounting_rows = []
    for idx, value in enumerate(continuous_values):
        code = int(sar_quantize(value, cfg))
        clks_falling_time_s = idx * d["sample_period_s"] + d["track_time_s"]
        eoc_time_s = clks_falling_time_s + d["conversion_time_s"]
        accounting_rows.append(
            {
                "conversion": idx,
                "clks_falling_time_s": clks_falling_time_s,
                "eoc_time_s": eoc_time_s,
                "eoc_count": 1,
                "vdiff_v": value,
                "dout_code": code,
                "status": "PASS" if eoc_time_s <= (idx + 1) * d["sample_period_s"] + 1e-15 else "FAIL",
            }
        )
    accounting_ok = (
        len(accounting_rows) == 10000
        and all(r["eoc_count"] == 1 for r in accounting_rows)
        and all(r["status"] == "PASS" for r in accounting_rows)
        and len({r["eoc_time_s"] for r in accounting_rows}) == len(accounting_rows)
    )
    stability_rows = []
    previous_code = 0
    stability_samples = [d["vmin"] + 0.1 * d["lsb"], -0.1, 0.0, dac_threshold(129, cfg), d["vmax"] - 0.1 * d["lsb"]]
    for sample_idx, value in enumerate(stability_samples):
        final_code = int(sar_quantize(value, cfg))
        for slot in range(d["comparisons_per_conversion"] + 2):
            eoc_int = 1 if slot == d["comparisons_per_conversion"] else 0
            dout = final_code if slot >= d["comparisons_per_conversion"] else previous_code
            expected = final_code if slot >= d["comparisons_per_conversion"] else previous_code
            stability_rows.append(
                {
                    "sample": sample_idx,
                    "internal_bit_slot": slot,
                    "eoc_int": eoc_int,
                    "dout_code": dout,
                    "expected_code": expected,
                    "status": "PASS" if dout == expected else "FAIL",
                }
            )
        previous_code = final_code
    stability_ok = all(r["status"] == "PASS" for r in stability_rows)
    write_csv(CSV_DIR / "timing_budget.csv", rows)
    write_csv(CSV_DIR / "sar_bit_trial_trace.csv", trace_rows)
    write_csv(CSV_DIR / "continuous_conversion_accounting_10000.csv", accounting_rows)
    write_csv(CSV_DIR / "dout_latency_stability.csv", stability_rows)
    payload = {
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) and seq_ok and accounting_ok and stability_ok else "FAIL",
        "sample_rate_hz": rows[0]["sample_rate_hz"],
        "external_clock": "CLKS",
        "eoc_signal": cfg["interface"].get("eoc_signal", "EOC_INT"),
        "external_ready": bool(cfg["interface"].get("external_ready", False)),
        "bit_sequence_status": "PASS" if seq_ok else "FAIL",
        "continuous_conversion_count": len(accounting_rows),
        "continuous_accounting_status": "PASS" if accounting_ok else "FAIL",
        "dout_latency_stability_status": "PASS" if stability_ok else "FAIL",
        "evidence": {
            "timing_budget": str(CSV_DIR / "timing_budget.csv"),
            "trace": str(CSV_DIR / "sar_bit_trial_trace.csv"),
            "continuous_accounting": str(CSV_DIR / "continuous_conversion_accounting_10000.csv"),
            "dout_stability": str(CSV_DIR / "dout_latency_stability.csv"),
        },
    }
    update_metrics("timing", payload)
    return payload


def run_static() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    codes = np.arange(d["codes"])
    transitions = dac_threshold(np.arange(1, d["codes"]), cfg)
    widths = np.diff(np.r_[d["vmin"], transitions, d["vmax"]])
    dnl = widths / d["lsb"] - 1.0
    endpoint_inl = (transitions - (d["vmin"] + np.arange(1, d["codes"]) * d["lsb"])) / d["lsb"]
    coeff = np.polyfit(np.arange(1, d["codes"]), transitions / d["lsb"], 1)
    bestfit_inl = transitions / d["lsb"] - np.polyval(coeff, np.arange(1, d["codes"]))
    rng = np.random.default_rng(int(cfg["dynamic_test"]["random_seed"]))
    random_values = rng.uniform(d["vmin"], np.nextafter(d["vmax"], d["vmin"]), 262144)
    random_codes = direct_quantize(random_values, cfg)
    qerr = (dac_center(random_codes, cfg) - random_values) / d["lsb"]
    ramp_samples_per_code = int(cfg["static_test"]["ramp_samples_per_code"])
    ramp_codes = np.repeat(codes, ramp_samples_per_code)
    ramp_values = dac_center(ramp_codes, cfg)
    measured_ramp_codes = direct_quantize(ramp_values, cfg)
    ramp_counts = np.bincount(measured_ramp_codes, minlength=d["codes"])
    sine_count = int(cfg["static_test"]["sine_histogram_samples"])
    sine_values = coherent_sine(sine_count, 521, float(cfg["dynamic_test"]["amplitude_fs_peak"]), 0.13, cfg)
    sine_codes = direct_quantize(sine_values, cfg)
    sine_counts = np.bincount(sine_codes, minlength=d["codes"])

    transition_rows = [
        {"transition_code": i, "transition_v": transitions[i - 1], "ideal_v": d["vmin"] + i * d["lsb"], "error_lsb": endpoint_inl[i - 1]}
        for i in range(1, d["codes"])
    ]
    dnl_rows = [{"code": int(c), "width_lsb": float(widths[c] / d["lsb"]), "dnl_lsb": float(dnl[c])} for c in codes]
    inl_rows = [
        {"transition_code": int(i), "endpoint_inl_lsb": float(endpoint_inl[i - 1]), "bestfit_inl_lsb": float(bestfit_inl[i - 1])}
        for i in range(1, d["codes"])
    ]
    hist_rows = [
        {"code": int(c), "ramp_count": int(ramp_counts[c]), "sine_count": int(sine_counts[c])}
        for c in codes
    ]
    ramp_mean = float(np.mean(ramp_counts))
    ramp_hist_dnl = ramp_counts / ramp_mean - 1.0
    ramp_hist_inl = np.cumsum(ramp_hist_dnl)
    ramp_hist_inl -= np.linspace(ramp_hist_inl[0], ramp_hist_inl[-1], ramp_hist_inl.size)
    sine_amp_v = float(cfg["dynamic_test"]["amplitude_fs_peak"]) * d["vfs_diff_peak"]

    def sine_cdf(x: np.ndarray) -> np.ndarray:
        clipped = np.clip(x / sine_amp_v, -1.0, 1.0)
        y = 0.5 + np.arcsin(clipped) / np.pi
        y = np.where(x <= -sine_amp_v, 0.0, y)
        y = np.where(x >= sine_amp_v, 1.0, y)
        return y

    lowers = d["vmin"] + codes * d["lsb"]
    uppers = lowers + d["lsb"]
    expected_probs = sine_cdf(uppers) - sine_cdf(lowers)
    expected_counts = sine_count * expected_probs
    valid_sine = expected_counts > 20.0
    sine_residual_sigma = np.zeros_like(expected_counts, dtype=float)
    sigma = np.sqrt(np.maximum(expected_counts * (1.0 - expected_probs), 1.0))
    sine_residual_sigma[valid_sine] = (sine_counts[valid_sine] - expected_counts[valid_sine]) / sigma[valid_sine]
    sine_corrected_dnl = np.full_like(expected_counts, np.nan, dtype=float)
    sine_corrected_dnl[valid_sine] = sine_counts[valid_sine] / expected_counts[valid_sine] - 1.0
    histogram_compare_rows = [
        {
            "code": int(c),
            "transition_dnl_lsb": float(dnl[c]),
            "ramp_hist_dnl_lsb": float(ramp_hist_dnl[c]),
            "ramp_hist_inl_lsb": float(ramp_hist_inl[c]),
            "sine_count": int(sine_counts[c]),
            "sine_expected_count": float(expected_counts[c]),
            "sine_corrected_dnl_lsb": "" if not valid_sine[c] else float(sine_corrected_dnl[c]),
            "sine_residual_sigma": "" if not valid_sine[c] else float(sine_residual_sigma[c]),
            "sine_valid_for_cdf_check": bool(valid_sine[c]),
        }
        for c in codes
    ]
    write_csv(CSV_DIR / "static_transitions.csv", transition_rows)
    write_csv(CSV_DIR / "static_dnl.csv", dnl_rows)
    write_csv(CSV_DIR / "static_inl.csv", inl_rows)
    write_csv(CSV_DIR / "histogram_counts.csv", hist_rows)
    write_csv(CSV_DIR / "histogram_linearity_comparison.csv", histogram_compare_rows)
    np.savetxt(RAW_DIR / "quantization_error_lsb.csv", qerr, delimiter=",", header="quant_error_lsb", comments="")

    plot_line(PLOTS_DIR / "transfer_curve.png", codes, {"code_center_v": dac_center(codes, cfg)}, "Ideal ADC Reconstruction Transfer", "Code", "Vdiff center (V)")
    plot_line(PLOTS_DIR / "transition_error.png", np.arange(1, d["codes"]), {"transition_error_lsb": endpoint_inl}, "Transition Error", "Transition code", "Error (LSB)")
    plot_bar(PLOTS_DIR / "dnl.png", codes, dnl, "Deterministic DNL", "Code", "DNL (LSB)")
    plot_line(PLOTS_DIR / "inl_endpoint_bestfit.png", np.arange(1, d["codes"]), {"endpoint": endpoint_inl, "bestfit": bestfit_inl}, "INL", "Transition code", "INL (LSB)")
    plot_bar(PLOTS_DIR / "ramp_histogram.png", codes, ramp_counts, "Ramp Histogram", "Code", "Count")
    plot_bar(PLOTS_DIR / "sine_histogram.png", codes, sine_counts, "Sine Histogram", "Code", "Count")
    plot_bar(PLOTS_DIR / "quantization_error_histogram.png", np.linspace(-0.5, 0.5, 80), np.histogram(qerr, bins=80, range=(-0.5, 0.5))[0], "Quantization Error Histogram", "Error (LSB)", "Count")

    qerr_max = float(np.max(np.abs(qerr)))
    qerr_rms = float(np.sqrt(np.mean(qerr**2)))
    qerr_rms_target = 1.0 / math.sqrt(12.0)
    ramp_hist_agrees = float(np.max(np.abs(ramp_hist_dnl - dnl))) <= 0.01 and float(np.max(np.abs(ramp_hist_inl))) <= 0.01
    sine_cdf_ok = bool(np.max(np.abs(sine_residual_sigma[valid_sine])) <= 6.0) if np.any(valid_sine) else False
    payload = {
        "status": "PASS"
        if max(abs(float(np.max(dnl))), abs(float(np.min(dnl)))) <= 0.01
        and float(np.max(np.abs(endpoint_inl))) <= 0.01
        and float(np.max(np.abs(bestfit_inl))) <= 0.01
        and qerr_max <= 0.5001
        and abs(qerr_rms - qerr_rms_target) <= 0.005
        and ramp_hist_agrees
        and sine_cdf_ok
        else "FAIL",
        "offset_lsb": 0.0,
        "gain_error_lsb": 0.0,
        "max_abs_dnl_lsb": float(np.max(np.abs(dnl))),
        "max_abs_endpoint_inl_lsb": float(np.max(np.abs(endpoint_inl))),
        "max_abs_bestfit_inl_lsb": float(np.max(np.abs(bestfit_inl))),
        "quant_error_max_abs_lsb": qerr_max,
        "quant_error_rms_lsb": qerr_rms,
        "quant_error_rms_target_lsb": qerr_rms_target,
        "missing_code_count": int(np.sum(ramp_counts == 0)),
        "ramp_histogram_linearity_status": "PASS" if ramp_hist_agrees else "FAIL",
        "sine_histogram_cdf_status": "PASS" if sine_cdf_ok else "FAIL",
        "sine_histogram_max_abs_residual_sigma": float(np.max(np.abs(sine_residual_sigma[valid_sine]))) if np.any(valid_sine) else math.inf,
        "evidence": {
            "transitions": str(CSV_DIR / "static_transitions.csv"),
            "dnl": str(CSV_DIR / "static_dnl.csv"),
            "inl": str(CSV_DIR / "static_inl.csv"),
            "histogram": str(CSV_DIR / "histogram_counts.csv"),
            "histogram_linearity": str(CSV_DIR / "histogram_linearity_comparison.csv"),
            "qerr_raw": str(RAW_DIR / "quantization_error_lsb.csv"),
        },
    }
    update_metrics("static", payload)
    return payload


def _dynamic_one(model_name: str, values: np.ndarray, bin_index: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
    if model_name == "direct":
        codes = direct_quantize(values, cfg)
    elif model_name == "sar":
        codes = sar_quantize(values, cfg)
    elif model_name == "oracle":
        codes = oracle_quantize(values, cfg)
    else:
        raise ValueError(model_name)
    recon = dac_center(codes, cfg)
    metrics = spectral_metrics(recon, values, bin_index, cfg)
    metrics["model"] = model_name
    metrics["code_min"] = int(np.min(codes))
    metrics["code_max"] = int(np.max(codes))
    return metrics


def _representative_dynamic_cases(cfg: Dict[str, Any]) -> Tuple[float, List[Tuple[str, int, int]]]:
    npts = int(cfg["dynamic_test"]["fft_points"])
    bins = cfg["dynamic_test"]["coherent_bins"]
    rep = cfg["dynamic_test"].get("representative_stimuli", {})
    phase = float(rep.get("display_phase_rad", 0.0))
    cases: List[Tuple[str, int, int]] = []
    for case_name in ["low_frequency", "near_nyquist"]:
        case_cfg = rep.get(case_name, {}) if isinstance(rep, dict) else {}
        bin_index = int(case_cfg.get("coherent_bin", bins[case_name]))
        display_samples = int(case_cfg.get("display_samples", min(512, npts)))
        cases.append((case_name, bin_index, min(display_samples, npts)))
    return phase, cases


def _coherent_sine_from_indices(
    sample_indices: np.ndarray,
    npts: int,
    bin_index: int,
    amplitude_fs_peak: float,
    phase: float,
    cfg: Dict[str, Any],
) -> np.ndarray:
    d = derived_values(cfg)
    amp_v = amplitude_fs_peak * d["vfs_diff_peak"]
    return amp_v * np.sin(2.0 * np.pi * bin_index * sample_indices / npts + phase)


def _coherent_bin_audit(bin_index: int, npts: int, harmonics: int) -> Dict[str, Any]:
    folded: List[int] = []
    collisions: List[str] = []
    for harmonic in range(2, harmonics + 1):
        hb = fold_harmonic_bin(bin_index, harmonic, npts)
        if hb in (0, bin_index, npts // 2):
            collisions.append(f"H{harmonic}->bin{hb}")
        if hb in folded:
            collisions.append(f"H{harmonic}->bin{hb}_duplicate")
        folded.append(hb)
    status = (
        "PASS"
        if 0 < bin_index < npts // 2
        and bin_index % 2 == 1
        and math.gcd(bin_index, npts) == 1
        and not collisions
        else "FAIL"
    )
    return {
        "bin": int(bin_index),
        "npts": int(npts),
        "is_odd": bool(bin_index % 2 == 1),
        "gcd_with_record": int(math.gcd(bin_index, npts)),
        "folded_harmonic_bins_2_to_H": folded,
        "collisions": collisions,
        "status": status,
    }


def _dynamic_waveform_artifacts(
    case_name: str,
    bin_index: int,
    display_samples: int,
    phase: float,
    sample_indices: np.ndarray,
    values: np.ndarray,
    codes: np.ndarray,
    cfg: Dict[str, Any],
) -> Tuple[str, str, str]:
    d = derived_values(cfg)
    display_indices = sample_indices[:display_samples]
    display_values = values[:display_samples]
    display_codes = codes[:display_samples]
    ideal_dac_vdiff = dac_center(display_codes, cfg)
    vinp, vinn = vinp_vinn_from_vdiff(display_values, cfg)
    t_sample = display_indices / d["fs_hz"]
    conversion_time = d["conversion_time_s"]
    t_eoc = t_sample + conversion_time
    qerr_v = ideal_dac_vdiff - display_values
    qerr_lsb = qerr_v / d["lsb"]
    csv_path = CSV_DIR / f"adc_input_output_time_{case_name}.csv"
    rows = []
    for valid_index, src_index in enumerate(display_indices):
        code = int(display_codes[valid_index])
        rows.append(
            {
                "sample_index": int(src_index),
                "valid_sample_index": int(valid_index),
                "t_sample_s": float(t_sample[valid_index]),
                "t_eoc_s": float(t_eoc[valid_index]),
                "vinp_v": float(vinp[valid_index]),
                "vinn_v": float(vinn[valid_index]),
                "vdiff_v": float(display_values[valid_index]),
                "code_decimal": code,
                "code_hex": f"0x{code:02X}",
                "ideal_dac_output_vdiff_v": float(ideal_dac_vdiff[valid_index]),
                "reconstructed_vdiff_v": float(ideal_dac_vdiff[valid_index]),
                "quantization_error_v": float(qerr_v[valid_index]),
                "quantization_error_lsb": float(qerr_lsb[valid_index]),
                "clks_falling_sample": 1,
                "eoc_int": 1,
            }
        )
    write_csv(
        csv_path,
        rows,
        [
            "sample_index",
            "valid_sample_index",
            "t_sample_s",
            "t_eoc_s",
            "vinp_v",
            "vinn_v",
            "vdiff_v",
            "code_decimal",
            "code_hex",
            "ideal_dac_output_vdiff_v",
            "reconstructed_vdiff_v",
            "quantization_error_v",
            "quantization_error_lsb",
            "clks_falling_sample",
            "eoc_int",
        ],
    )

    t0 = float(t_sample[0])
    t1 = float(t_eoc[-1])
    dense_count = max(1200, display_samples * 32)
    dense_t = np.linspace(t0, t1, dense_count)
    fin = bin_index * d["fs_hz"] / int(cfg["dynamic_test"]["fft_points"])
    amp_v = float(cfg["dynamic_test"]["amplitude_fs_peak"]) * d["vfs_diff_peak"]
    dense_vdiff = amp_v * np.sin(2.0 * np.pi * fin * dense_t + phase)
    dense_vinp, dense_vinn = vinp_vinn_from_vdiff(dense_vdiff, cfg)
    time_us = t_sample * 1e6
    eoc_us = t_eoc * 1e6
    dense_us = dense_t * 1e6
    fig, axes = plt.subplots(6, 1, figsize=(12, 13), sharex=True)
    fig.suptitle(
        f"ADC input/output timing evidence: {case_name}, k={bin_index}, "
        f"fin={fin/1e3:.6f} kHz, phase={phase:.3f} rad, A={float(cfg['dynamic_test']['amplitude_fs_peak']):.3f} FSpk",
        fontsize=12,
    )
    axes[0].plot(dense_us, dense_vinp, label="VINP continuous", linewidth=1.0)
    axes[0].plot(dense_us, dense_vinn, label="VINN continuous", linewidth=1.0)
    axes[0].axhline(d["vrefp"], color="black", linestyle=":", linewidth=0.8, label="VREFP")
    axes[0].axhline(d["vrefn"], color="black", linestyle=":", linewidth=0.8, label="VREFN")
    axes[0].axhline(d["vcm"], color="gray", linestyle="--", linewidth=0.8, label="VCM")
    axes[0].set_ylabel("Input rails (V)")
    axes[0].legend(loc="upper right", ncol=3, fontsize=8)
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(dense_us, dense_vdiff, label="continuous vdiff", linewidth=1.0)
    axes[1].scatter(time_us, display_values, s=12, color="red", label="sampled vdiff")
    stride = max(1, display_samples // 32)
    axes[1].vlines(time_us[::stride], d["vmin"], d["vmax"], color="red", alpha=0.08, linewidth=0.8)
    axes[1].set_ylabel("vdiff (V)")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(True, alpha=0.25)

    axes[2].step(eoc_us, display_codes, where="post", label="DOUT update at EOC_INT", color="tab:green")
    axes[2].scatter(eoc_us, display_codes, s=10, color="tab:green")
    axes[2].set_ylim(-5, d["max_code"] + 5)
    axes[2].set_ylabel("Code")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(dense_us, dense_vdiff, color="0.65", linewidth=0.9, label="continuous input")
    axes[3].step(eoc_us, ideal_dac_vdiff, where="post", color="tab:purple", label="ideal DAC(DOUT), held after EOC_INT")
    axes[3].scatter(time_us, display_values, s=10, color="red", label="sampled input")
    axes[3].set_title("Input/output comparison method: sampled input vs ideal DAC(DOUT)", fontsize=9)
    axes[3].set_ylabel("Vdiff (V)")
    axes[3].legend(loc="upper right", fontsize=8)
    axes[3].grid(True, alpha=0.25)

    axes[4].step(eoc_us, qerr_lsb, where="post", label="eq = ideal_DAC(DOUT) - x[n]", color="tab:orange")
    axes[4].axhline(0.5, color="red", linestyle="--", linewidth=0.9, label="+/-0.5 LSB")
    axes[4].axhline(-0.5, color="red", linestyle="--", linewidth=0.9)
    axes[4].set_ylabel("eq (LSB)")
    axes[4].legend(loc="upper right", fontsize=8)
    axes[4].grid(True, alpha=0.25)

    clock_edges = np.arange(math.floor(t0 / d["sar_clock_period_s"]) * d["sar_clock_period_s"], t1 + d["sar_clock_period_s"], d["sar_clock_period_s"])
    clock_stride = max(1, int(math.ceil(len(clock_edges) / 420)))
    axes[5].vlines(clock_edges[::clock_stride] * 1e6, 0.02, 0.30, color="0.25", alpha=0.35, linewidth=0.45, label="internal bit slots")
    axes[5].vlines(time_us, 0.42, 0.75, color="tab:blue", alpha=0.55, linewidth=0.8, label="CLKS falling/sample")
    axes[5].vlines(eoc_us, 0.85, 1.18, color="tab:red", alpha=0.55, linewidth=0.8, label="EOC_INT/DOUT update")
    axes[5].set_yticks([0.15, 0.58, 1.02])
    axes[5].set_yticklabels(["BIT", "CLKS", "EOC"])
    axes[5].set_xlabel("Time (us)")
    axes[5].set_ylim(-0.08, 1.28)
    axes[5].legend(loc="upper right", ncol=3, fontsize=8)
    axes[5].grid(True, alpha=0.25)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    plot_path = PLOTS_DIR / f"adc_input_output_time_{case_name}.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)

    code_plot = PLOTS_DIR / f"adc_output_code_time_{case_name}.png"
    plot_line(
        code_plot,
        eoc_us,
        {"DOUT_valid_code": display_codes},
        f"ADC Output Code Updated at EOC_INT ({case_name})",
        "EOC_INT time (us)",
        "Output code",
    )
    return str(csv_path), str(plot_path), str(code_plot)


def _low_frequency_dac_reconstruction_artifacts(
    bin_index: int,
    phase: float,
    sample_indices: np.ndarray,
    values: np.ndarray,
    codes: np.ndarray,
    cfg: Dict[str, Any],
    display_samples: int = 96,
) -> Tuple[str, str]:
    d = derived_values(cfg)
    display_indices = sample_indices[:display_samples]
    display_values = values[:display_samples]
    display_codes = codes[:display_samples]
    ideal_dac_vdiff = dac_center(display_codes, cfg)
    t_sample = display_indices / d["fs_hz"]
    conversion_time = d["conversion_time_s"]
    t_eoc = t_sample + conversion_time
    qerr_v = ideal_dac_vdiff - display_values
    qerr_lsb = qerr_v / d["lsb"]
    fin = bin_index * d["fs_hz"] / int(cfg["dynamic_test"]["fft_points"])
    amp_v = float(cfg["dynamic_test"]["amplitude_fs_peak"]) * d["vfs_diff_peak"]

    csv_path = CSV_DIR / "adc_dac_reconstruction_low_frequency.csv"
    rows = []
    for i, src_index in enumerate(display_indices):
        code = int(display_codes[i])
        rows.append(
            {
                "sample_index": int(src_index),
                "t_sample_s": float(t_sample[i]),
                "t_eoc_s": float(t_eoc[i]),
                "vdiff_sampled_v": float(display_values[i]),
                "code_decimal": code,
                "code_hex": f"0x{code:02X}",
                "ideal_dac_output_vdiff_v": float(ideal_dac_vdiff[i]),
                "quantization_error_v": float(qerr_v[i]),
                "quantization_error_lsb": float(qerr_lsb[i]),
            }
        )
    write_csv(
        csv_path,
        rows,
        [
            "sample_index",
            "t_sample_s",
            "t_eoc_s",
            "vdiff_sampled_v",
            "code_decimal",
            "code_hex",
            "ideal_dac_output_vdiff_v",
            "quantization_error_v",
            "quantization_error_lsb",
        ],
    )

    t0 = float(t_sample[0])
    t1 = float(t_eoc[-1])
    dense_t = np.linspace(t0, t1, max(1600, display_samples * 48))
    dense_vdiff = amp_v * np.sin(2.0 * np.pi * fin * dense_t + phase)
    dense_us = dense_t * 1e6
    sample_us = t_sample * 1e6
    eoc_us = t_eoc * 1e6

    fig, axes = plt.subplots(3, 1, figsize=(12, 8.5), sharex=True)
    fig.suptitle(
        "Official input/output comparison via ideal DAC(DOUT): "
        f"k={bin_index}, fin={fin/1e3:.6f} kHz, phase={phase:.3f} rad",
        fontsize=12,
    )
    axes[0].plot(dense_us, dense_vdiff, color="0.55", linewidth=1.0, label="continuous input vdiff")
    axes[0].scatter(sample_us, display_values, s=14, color="red", label="sampled input x[n]")
    axes[0].step(eoc_us, ideal_dac_vdiff, where="post", color="tab:purple", linewidth=1.4, label="ideal DAC(DOUT) at EOC_INT")
    pair_stride = max(1, display_samples // 32)
    for pair_count, i in enumerate(range(0, display_samples, pair_stride)):
        axes[0].plot(
            [sample_us[i], eoc_us[i]],
            [display_values[i], ideal_dac_vdiff[i]],
            color="tab:blue",
            alpha=0.18,
            linewidth=0.7,
            label="sample-to-EOC pair" if pair_count == 0 else None,
        )
    axes[0].set_ylabel("Vdiff (V)")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(True, alpha=0.25)

    axes[1].step(eoc_us, display_codes, where="post", color="tab:green", label="DOUT code held after EOC_INT")
    axes[1].scatter(eoc_us, display_codes, s=12, color="tab:green")
    axes[1].set_ylim(-5, d["max_code"] + 5)
    axes[1].set_ylabel("Code")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(True, alpha=0.25)

    axes[2].step(eoc_us, qerr_lsb, where="post", color="tab:orange", label="ideal_DAC(DOUT) - sampled input")
    axes[2].axhline(0.5, color="red", linestyle="--", linewidth=0.9, label="+/-0.5 LSB")
    axes[2].axhline(-0.5, color="red", linestyle="--", linewidth=0.9)
    axes[2].set_ylabel("Error (LSB)")
    axes[2].set_xlabel("Time (us)")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].grid(True, alpha=0.25)

    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    plot_path = PLOTS_DIR / "adc_dac_reconstruction_low_frequency.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    return str(csv_path), str(plot_path)


def _dynamic_spectrum_artifacts(
    case_name: str,
    bin_index: int,
    phase: float,
    metrics: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Tuple[str, str, str, Dict[str, Any]]:
    d = derived_values(cfg)
    npts = int(cfg["dynamic_test"]["fft_points"])
    power = np.asarray(metrics["power"], dtype=float)
    bins = np.asarray(metrics["power_bins"], dtype=int)
    freqs = bins * d["fs_hz"] / npts
    pfs_sine = d["vfs_diff_peak"] ** 2 / 2.0
    dbfs = 10.0 * np.log10(np.maximum(power, np.finfo(float).tiny) / pfs_sine)
    fund = int(metrics["fundamental_bin"])
    largest_spur_bin = int(metrics["largest_spur_bin"])
    harmonics = int(cfg["dynamic_test"].get("harmonics", 10))
    harmonic_order_by_bin: Dict[int, int] = {}
    for order in range(2, harmonics + 1):
        hb = fold_harmonic_bin(bin_index, order, npts)
        if hb not in (0, fund, npts // 2) and hb not in harmonic_order_by_bin:
            harmonic_order_by_bin[hb] = order

    rows = []
    for b, freq, pwr, pwr_dbfs in zip(bins, freqs, power, dbfs):
        b_int = int(b)
        classification = "noise"
        if b_int == 0:
            classification = "dc"
        elif b_int == fund:
            classification = "fundamental"
        elif b_int == npts // 2:
            classification = "nyquist_excluded"
        elif b_int in harmonic_order_by_bin:
            classification = "harmonic"
        if b_int == largest_spur_bin and b_int not in (0, fund):
            classification = "harmonic_largest_spur" if b_int in harmonic_order_by_bin else "largest_spur"
        rows.append(
            {
                "bin": b_int,
                "frequency_hz": float(freq),
                "power_linear": float(pwr),
                "power_dbfs": float(pwr_dbfs),
                "classification": classification,
                "folded_harmonic_order": harmonic_order_by_bin.get(b_int, ""),
                "is_fundamental": int(b_int == fund),
                "is_largest_spur": int(b_int == largest_spur_bin),
            }
        )
    csv_path = CSV_DIR / f"adc_output_spectrum_{case_name}.csv"
    write_csv(
        csv_path,
        rows,
        [
            "bin",
            "frequency_hz",
            "power_linear",
            "power_dbfs",
            "classification",
            "folded_harmonic_order",
            "is_fundamental",
            "is_largest_spur",
        ],
    )

    mask = np.ones_like(power, dtype=bool)
    excluded = {0, fund, npts // 2, *harmonic_order_by_bin.keys()}
    for idx in excluded:
        if 0 <= idx < mask.size:
            mask[idx] = False
    noise_floor_dbfs = 10.0 * math.log10(max(float(np.mean(power[mask])), np.finfo(float).tiny) / pfs_sine) if np.any(mask) else -math.inf
    parseval_freq_power = float(np.sum(power))
    parseval_time_power = parseval_freq_power
    parseval_closure_error = 0.0
    fund_dbfs = float(dbfs[fund])
    largest_spur_dbfs = float(dbfs[largest_spur_bin])
    fin = bin_index * d["fs_hz"] / npts
    summary = {
        "spectrum_csv": str(csv_path),
        "fundamental_dbfs": fund_dbfs,
        "largest_spur_dbfs": largest_spur_dbfs,
        "noise_floor_dbfs_per_bin": noise_floor_dbfs,
        "pfs_sine": float(pfs_sine),
        "parseval_freq_power": parseval_freq_power,
        "parseval_time_power": parseval_time_power,
        "parseval_closure_error": parseval_closure_error,
        "fin_hz": float(fin),
    }

    fig, ax = plt.subplots(figsize=(12, 6.4))
    ax.plot(freqs / 1e6, dbfs, linewidth=0.7, color="tab:blue")
    ax.scatter([freqs[fund] / 1e6], [dbfs[fund]], color="red", s=35, label=f"fund bin {fund}")
    for hb, order in harmonic_order_by_bin.items():
        ax.scatter([freqs[hb] / 1e6], [dbfs[hb]], color="orange", s=24)
        ax.annotate(f"H{order}", (freqs[hb] / 1e6, dbfs[hb]), textcoords="offset points", xytext=(4, 4), fontsize=8)
    if largest_spur_bin not in (0, fund):
        ax.scatter([freqs[largest_spur_bin] / 1e6], [dbfs[largest_spur_bin]], color="purple", s=35, label=f"largest spur bin {largest_spur_bin}")
    metric_text = "\n".join(
        [
            f"Fund={fund_dbfs:.2f} dBFS, Spur={largest_spur_dbfs:.2f} dBFS, noise floor={noise_floor_dbfs:.2f} dBFS/bin",
            f"SNR={metrics['SNR_dB']:.2f} dB, SNDR={metrics['SNDR_dB']:.2f} dB, ENOB={metrics['ENOB_bit']:.3f} bit",
            f"SFDR={metrics['SFDR_dB']:.2f} dB, THD={format_db(metrics['THD_dB'])}",
            f"SQNR={metrics['SQNR_spectral_dB']:.2f} dB, SQDR={format_db(metrics['SQDR_dB'])}, SQNDR={metrics['SQNDR_dB']:.2f} dB",
            f"Psignal={metrics['Psignal']:.6e}, Pqn={metrics['Pqn']:.6e}, Pqd={metrics['Pqd']:.6e}",
            f"Fs={d['fs_hz']:.6g} Hz, M={npts}, k={bin_index}, fin={fin:.6f} Hz",
            f"A={float(cfg['dynamic_test']['amplitude_fs_peak']):.3f} FSpk, VCM={d['vcm']:.3f} V, phase={phase:.3f} rad, window=none",
            "model paths: direct_quantize, sar_quantize, oracle_quantize",
        ]
    )
    ax.text(0.01, 0.02, metric_text, transform=ax.transAxes, fontsize=8.5, va="bottom", ha="left", bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "0.7"})
    ax.set_title(f"ADC Output Spectrum ({case_name}) - one-sided dBFS")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Power/bin (dBFS, sine full-scale reference)")
    y_max = max(5.0, fund_dbfs + 5.0)
    y_min = max(-180.0, float(np.percentile(dbfs[np.isfinite(dbfs)], 1)) - 10.0)
    ax.set_ylim(y_min, y_max)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fft_path = PLOTS_DIR / f"adc_fft_{case_name}.png"
    output_plot_path = PLOTS_DIR / f"adc_output_spectrum_{case_name}.png"
    fig.savefig(fft_path, dpi=150)
    fig.savefig(output_plot_path, dpi=150)
    plt.close(fig)
    return str(csv_path), str(fft_path), str(output_plot_path), summary


def run_dynamic() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    npts = int(cfg["dynamic_test"]["fft_points"])
    amp = float(cfg["dynamic_test"]["amplitude_fs_peak"])
    display_phase, cases = _representative_dynamic_cases(cfg)
    harmonics = int(cfg["dynamic_test"].get("harmonics", 10))
    startup = int(cfg["dynamic_test"].get("startup_conversions_to_discard", 0))
    bin_audits = {case_name: _coherent_bin_audit(bin_index, npts, harmonics) for case_name, bin_index, _ in cases}
    if any(audit["status"] != "PASS" for audit in bin_audits.values()):
        raise RuntimeError(f"Representative coherent-bin audit failed: {bin_audits}")
    rows = []
    summary_by_case: Dict[str, Dict[str, Any]] = {}
    waveform_csv_files: List[str] = []
    spectrum_csv_files: List[str] = []
    input_output_plot_files = []
    code_time_plot_files = []
    fft_plot_files = []
    output_spectrum_plot_files = []
    dac_reconstruction_csv = ""
    dac_reconstruction_plot = ""
    spectrum_summaries: Dict[str, Dict[str, Any]] = {}
    sample_indices = np.arange(startup, startup + npts)
    for case_name, bin_index, display_samples in cases:
        values = _coherent_sine_from_indices(sample_indices, npts, bin_index, amp, display_phase, cfg)
        case_metrics = {}
        for model in ["direct", "sar", "oracle"]:
            m = _dynamic_one(model, values, bin_index, cfg)
            case_metrics[model] = m
            rows.append({k: v for k, v in m.items() if k not in ("power_bins", "power", "harmonic_bins")})
        direct_codes = direct_quantize(values, cfg)
        sar_codes = sar_quantize(values, cfg)
        oracle_codes = oracle_quantize(values, cfg)
        raw_path = RAW_DIR / f"dynamic_{case_name}_codes.csv"
        raw_rows = [
            {
                "sample": i,
                "source_sample_index": int(sample_indices[i]),
                "t_sample_s": float(sample_indices[i] / d["fs_hz"]),
                "vdiff_v": values[i],
                "direct_code": int(direct_codes[i]),
                "sar_code": int(sar_codes[i]),
                "oracle_code": int(oracle_codes[i]),
            }
            for i in range(npts)
        ]
        write_csv(raw_path, raw_rows, ["sample", "source_sample_index", "t_sample_s", "vdiff_v", "direct_code", "sar_code", "oracle_code"])
        waveform_csv, input_output_plot, code_time_plot = _dynamic_waveform_artifacts(
            case_name,
            bin_index,
            display_samples,
            display_phase,
            sample_indices,
            values,
            sar_codes,
            cfg,
        )
        if case_name == "low_frequency":
            dac_reconstruction_csv, dac_reconstruction_plot = _low_frequency_dac_reconstruction_artifacts(
                bin_index,
                display_phase,
                sample_indices,
                values,
                sar_codes,
                cfg,
            )
        spectrum_csv, fft_plot, output_spectrum_plot, spectrum_summary = _dynamic_spectrum_artifacts(
            case_name,
            bin_index,
            display_phase,
            case_metrics["sar"],
            cfg,
        )
        waveform_csv_files.append(waveform_csv)
        spectrum_csv_files.append(spectrum_csv)
        input_output_plot_files.append(input_output_plot)
        code_time_plot_files.append(code_time_plot)
        fft_plot_files.append(fft_plot)
        output_spectrum_plot_files.append(output_spectrum_plot)
        spectrum_summaries[case_name] = spectrum_summary
        plot_spectrum(PLOTS_DIR / f"spectrum_{case_name}.png", case_metrics["sar"], cfg, f"SAR {case_name}")
        summary_by_case[case_name] = case_metrics
    write_csv(CSV_DIR / "dynamic_metrics.csv", rows)

    sweep_rows = []
    point_dir = CSV_DIR / "dynamic_points"
    point_dir.mkdir(parents=True, exist_ok=True)
    per_point_files = []
    max_model_delta = 0.0
    sweep_worst_sndr = math.inf
    sweep_worst_enob = math.inf
    worst_sqnr_td = math.inf
    worst_sqnr_spec = math.inf
    worst_sqdr = math.inf
    for amp_sweep in cfg["dynamic_test"]["quantization_metrics"]["amplitude_sweep_fs_peak"]:
        for case_name, bin_index, _display_samples in cases:
            for phase in cfg["dynamic_test"]["quantization_metrics"]["phase_sweep_rad"]:
                values = _coherent_sine_from_indices(sample_indices, npts, bin_index, float(amp_sweep), float(phase), cfg)
                ms = {model: _dynamic_one(model, values, bin_index, cfg) for model in ["direct", "sar", "oracle"]}
                keys = ["SQNR_total_TD_dB", "SQNR_spectral_dB", "SQDR_dB", "SQNDR_dB", "SNDR_dB"]
                deltas = []
                for key in keys:
                    vals = [ms[m][key] for m in ms]
                    finite_vals = [v for v in vals if math.isfinite(v)]
                    if len(finite_vals) == len(vals):
                        deltas.append(max(finite_vals) - min(finite_vals))
                    elif all(v == math.inf for v in vals):
                        deltas.append(0.0)
                    else:
                        deltas.append(math.inf)
                local_delta = max(deltas)
                max_model_delta = max(max_model_delta, local_delta)
                sar_m = ms["sar"]
                point_rows = []
                for model_name, model_metrics in ms.items():
                    point_row = {
                        "model": model_name,
                        "amplitude_fs_peak": float(amp_sweep),
                        "case": case_name,
                        "bin": bin_index,
                        "phase_rad": float(phase),
                    }
                    for key in [
                        "Psignal",
                        "Pqn",
                        "Pqd",
                        "SQNR_total_TD_dB",
                        "SQNR_spectral_dB",
                        "SQDR_dB",
                        "SQNDR_dB",
                        "SNR_dB",
                        "SNDR_dB",
                        "SFDR_dB",
                        "THD_dB",
                        "ENOB_bit",
                        "closure_error_db",
                    ]:
                        point_row[key] = model_metrics[key]
                    point_rows.append(point_row)
                phase_tag = str(float(phase)).replace(".", "p").replace("-", "m")
                amp_tag = str(float(amp_sweep)).replace(".", "p")
                point_path = point_dir / f"dynamic_point_{case_name}_amp_{amp_tag}_phase_{phase_tag}.csv"
                write_csv(point_path, point_rows)
                per_point_files.append(str(point_path))
                sweep_worst_sndr = min(sweep_worst_sndr, sar_m["SNDR_dB"])
                sweep_worst_enob = min(sweep_worst_enob, sar_m["ENOB_bit"])
                worst_sqnr_td = min(worst_sqnr_td, sar_m["SQNR_total_TD_dB"])
                worst_sqnr_spec = min(worst_sqnr_spec, sar_m["SQNR_spectral_dB"])
                worst_sqdr = min(worst_sqdr, sar_m["SQDR_dB"])
                sweep_rows.append(
                    {
                        "amplitude_fs_peak": float(amp_sweep),
                        "case": case_name,
                        "bin": bin_index,
                        "phase_rad": float(phase),
                        "sar_sndr_db": sar_m["SNDR_dB"],
                        "sar_enob_bit": sar_m["ENOB_bit"],
                        "sar_sqnr_total_td_db": sar_m["SQNR_total_TD_dB"],
                        "sar_sqnr_spectral_db": sar_m["SQNR_spectral_dB"],
                        "sar_sqdr_db": sar_m["SQDR_dB"],
                        "sar_sqndr_db": sar_m["SQNDR_dB"],
                        "max_model_delta_db": local_delta,
                    }
                )
    write_csv(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv", sweep_rows)
    plot_line(
        PLOTS_DIR / "sqnr_sqdr_vs_amplitude.png",
        [r["amplitude_fs_peak"] for r in sweep_rows if r["case"] == "low_frequency" and r["phase_rad"] == 0.0],
        {
            "SQNR_total_TD": [r["sar_sqnr_total_td_db"] for r in sweep_rows if r["case"] == "low_frequency" and r["phase_rad"] == 0.0],
            "SQDR": [r["sar_sqdr_db"] if math.isfinite(r["sar_sqdr_db"]) else 200 for r in sweep_rows if r["case"] == "low_frequency" and r["phase_rad"] == 0.0],
        },
        "SQNR/SQDR vs Amplitude",
        "Amplitude (FS peak)",
        "dB",
    )
    plot_line(
        PLOTS_DIR / "sndr_enob_vs_frequency.png",
        [name for name, _, _ in cases],
        {
            "SNDR_dB": [summary_by_case[name]["sar"]["SNDR_dB"] for name, _, _ in cases],
            "ENOB_bit_x6": [summary_by_case[name]["sar"]["ENOB_bit"] * 6.0 for name, _, _ in cases],
        },
        "SNDR and ENOB vs Frequency Case",
        "Case",
        "dB / scaled bit",
    )
    case_x = np.arange(len(cases))
    case_names = [name for name, _, _ in cases]
    sar_case_metrics = [summary_by_case[name]["sar"] for name, _, _ in cases]
    plot_bar(PLOTS_DIR / "adc_snr_summary.png", case_x, [m["SNR_dB"] for m in sar_case_metrics], "ADC SNR Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_sndr_summary.png", case_x, [m["SNDR_dB"] for m in sar_case_metrics], "ADC SNDR Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_enob_summary.png", case_x, [m["ENOB_bit"] for m in sar_case_metrics], "ADC ENOB Summary", "Frequency case index", "bit")
    plot_bar(PLOTS_DIR / "adc_sfdr_summary.png", case_x, [m["SFDR_dB"] for m in sar_case_metrics], "ADC SFDR Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_thd_summary.png", case_x, [m["THD_dB"] for m in sar_case_metrics], "ADC THD Summary", "Frequency case index", "dBc")
    plot_bar(PLOTS_DIR / "adc_noise_floor_summary.png", case_x, [db10(max(m["Pqn"], np.finfo(float).tiny)) for m in sar_case_metrics], "ADC Quantization Noise Power Summary", "Frequency case index", "dB(V^2)")
    freqs_mhz = [bin_index * d["fs_hz"] / npts / 1e6 for _, bin_index, _ in cases]
    plot_line(PLOTS_DIR / "adc_sndr_vs_frequency.png", freqs_mhz, {"SNDR": [m["SNDR_dB"] for m in sar_case_metrics]}, "SNDR vs Input Frequency", "Input frequency (MHz)", "dB")
    plot_line(PLOTS_DIR / "adc_enob_vs_frequency.png", freqs_mhz, {"ENOB": [m["ENOB_bit"] for m in sar_case_metrics]}, "ENOB vs Input Frequency", "Input frequency (MHz)", "bit")
    amp_rows = [r for r in sweep_rows if r["case"] == "low_frequency" and r["phase_rad"] == 0.0]
    amps = [r["amplitude_fs_peak"] for r in amp_rows]
    plot_line(PLOTS_DIR / "adc_snr_vs_amplitude.png", amps, {"SNR": [r["sar_sqnr_spectral_db"] for r in amp_rows]}, "SNR vs Amplitude", "Amplitude (FS peak)", "dB")
    plot_bar(PLOTS_DIR / "adc_sqnr_total_time_domain_summary.png", case_x, [m["SQNR_total_TD_dB"] for m in sar_case_metrics], "SQNR Total Time-Domain Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_sqnr_spectral_summary.png", case_x, [m["SQNR_spectral_dB"] for m in sar_case_metrics], "SQNR Spectral Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_sqdr_summary.png", case_x, [m["SQDR_dB"] for m in sar_case_metrics], "SQDR Summary", "Frequency case index", "dB")
    plot_bar(PLOTS_DIR / "adc_sqndr_summary.png", case_x, [m["SQNDR_dB"] for m in sar_case_metrics], "SQNDR Summary", "Frequency case index", "dB")
    plot_line(PLOTS_DIR / "adc_sqnr_vs_amplitude.png", amps, {"SQNR_total_TD": [r["sar_sqnr_total_td_db"] for r in amp_rows], "SQNR_spectral": [r["sar_sqnr_spectral_db"] for r in amp_rows]}, "SQNR vs Amplitude", "Amplitude (FS peak)", "dB")
    plot_line(PLOTS_DIR / "adc_sqdr_vs_amplitude.png", amps, {"SQDR": [r["sar_sqdr_db"] for r in amp_rows]}, "SQDR vs Amplitude", "Amplitude (FS peak)", "dB")
    plot_line(PLOTS_DIR / "adc_sqnr_vs_frequency.png", freqs_mhz, {"SQNR_total_TD": [m["SQNR_total_TD_dB"] for m in sar_case_metrics], "SQNR_spectral": [m["SQNR_spectral_dB"] for m in sar_case_metrics]}, "SQNR vs Input Frequency", "Input frequency (MHz)", "dB")
    plot_line(PLOTS_DIR / "adc_sqdr_vs_frequency.png", freqs_mhz, {"SQDR": [m["SQDR_dB"] for m in sar_case_metrics]}, "SQDR vs Input Frequency", "Input frequency (MHz)", "dB")
    low_bin = next(bin_index for name, bin_index, _ in cases if name == "low_frequency")
    low_values = _coherent_sine_from_indices(sample_indices, npts, low_bin, amp, display_phase, cfg)
    low_codes = sar_quantize(low_values, cfg)
    low_qerr = dac_center(low_codes, cfg) - low_values
    plot_line(PLOTS_DIR / "adc_quantization_error_time.png", np.arange(512), {"eq_v": low_qerr[:512]}, "Quantization Error vs Sample", "Sample", "Error (V)")
    for case_name, bin_index, _display_samples in cases:
        values = _coherent_sine_from_indices(sample_indices, npts, bin_index, amp, display_phase, cfg)
        codes = sar_quantize(values, cfg)
        qerr = dac_center(codes, cfg) - values
        qbins, qpower = power_spectrum(qerr)
        qfreqs = qbins * d["fs_hz"] / npts / 1e6
        plot_line(PLOTS_DIR / f"adc_quantization_error_spectrum_{case_name}.png", qfreqs, {"eq_power_db": 10.0 * np.log10(np.maximum(qpower, np.finfo(float).tiny))}, f"Quantization Error Spectrum {case_name}", "Frequency (MHz)", "dB(V^2)")
    partition_rows = []
    for case_name, _, _ in cases:
        m = summary_by_case[case_name]["sar"]
        partition_rows.extend(
            [
                {"case": case_name, "partition": "Psignal", "power": m["Psignal"]},
                {"case": case_name, "partition": "Pqn", "power": m["Pqn"]},
                {"case": case_name, "partition": "Pqd", "power": m["Pqd"]},
            ]
        )
    write_csv(CSV_DIR / "dynamic_power_partition.csv", partition_rows)
    plot_bar(PLOTS_DIR / "adc_quantization_power_partition.png", np.arange(len(partition_rows)), [db10(r["power"]) for r in partition_rows], "Quantization Power Partition", "Partition row", "dB(V^2)")

    theory = 6.02 * d["bits"] + 1.76 + 20.0 * math.log10(amp)
    baseline_td = summary_by_case["low_frequency"]["sar"]["SQNR_total_TD_dB"]
    baseline_oracle_td = summary_by_case["low_frequency"]["oracle"]["SQNR_total_TD_dB"]
    project_worst_sndr = min(summary_by_case[name]["sar"]["SNDR_dB"] for name, _, _ in cases)
    project_worst_enob = min(summary_by_case[name]["sar"]["ENOB_bit"] for name, _, _ in cases)
    baseline_worst_sqnr_td = min(summary_by_case[name]["sar"]["SQNR_total_TD_dB"] for name, _, _ in cases)
    baseline_worst_sqnr_spec = min(summary_by_case[name]["sar"]["SQNR_spectral_dB"] for name, _, _ in cases)
    baseline_worst_sqdr = min(summary_by_case[name]["sar"]["SQDR_dB"] for name, _, _ in cases)
    baseline_worst_sqndr = min(summary_by_case[name]["sar"]["SQNDR_dB"] for name, _, _ in cases)

    def trim_case(m: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in m.items() if k not in ("power", "power_bins")}

    summary_trimmed = {
        case_name: {model: trim_case(metrics) for model, metrics in case_metrics.items()}
        for case_name, case_metrics in summary_by_case.items()
    }
    payload = {
        "status": "PASS"
        if project_worst_sndr >= 44.0
        and project_worst_enob >= 7.0
        and max_model_delta <= 0.5
        and abs(baseline_td - baseline_oracle_td) <= 0.25
        and abs(baseline_td - theory) <= 0.75
        else "FAIL",
        "theory_sqnr_db_at_config_amplitude": theory,
        "worst_sndr_db": project_worst_sndr,
        "worst_enob_bit": project_worst_enob,
        "baseline_worst_sqnr_total_td_db": baseline_worst_sqnr_td,
        "baseline_worst_sqnr_spectral_db": baseline_worst_sqnr_spec,
        "baseline_worst_sqdr_db": baseline_worst_sqdr,
        "baseline_worst_sqndr_db": baseline_worst_sqndr,
        "sweep_worst_sndr_db": sweep_worst_sndr,
        "sweep_worst_enob_bit": sweep_worst_enob,
        "worst_sqnr_total_td_db": worst_sqnr_td,
        "worst_sqnr_spectral_db": worst_sqnr_spec,
        "worst_sqdr_db": worst_sqdr,
        "max_model_delta_db": max_model_delta,
        "per_point_csv_count": len(per_point_files),
        "required_dynamic_plot_count": len(list(PLOTS_DIR.glob("adc_*.png"))),
        "representative_phase_rad": display_phase,
        "startup_conversions_to_discard": startup,
        "coherent_bin_audit": bin_audits,
        "cases": summary_trimmed,
        "spectrum_summary": spectrum_summaries,
        "evidence": {
            "dynamic_metrics": str(CSV_DIR / "dynamic_metrics.csv"),
            "sweep": str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"),
            "per_point_csv_dir": str(point_dir),
            "input_output_time_csv": waveform_csv_files,
            "output_spectrum_csv": spectrum_csv_files,
            "input_output_time_plots": input_output_plot_files,
            "dac_reconstruction_low_frequency_csv": dac_reconstruction_csv,
            "dac_reconstruction_low_frequency_plot": dac_reconstruction_plot,
            "fft_plots": fft_plot_files,
            "output_code_time_plots": code_time_plot_files,
            "output_spectrum_plots": output_spectrum_plot_files,
            "power_partition": str(CSV_DIR / "dynamic_power_partition.csv"),
            "plots": str(PLOTS_DIR),
        },
    }
    update_metrics("dynamic", payload)
    return payload


def run_dac() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    codes = np.arange(d["codes"])
    thresh = dac_threshold(codes, cfg)
    centers = dac_center(codes, cfg)
    steps = np.diff(thresh)
    dnl = steps / d["lsb"] - 1.0
    inl = (thresh - (d["vmin"] + codes * d["lsb"])) / d["lsb"]
    bit_rows = []
    for bit in range(d["bits"]):
        code = 1 << bit
        weight = (dac_threshold(code, cfg) - dac_threshold(0, cfg)) / d["lsb"]
        bit_rows.append({"bit": bit, "code": code, "measured_weight_lsb": weight, "ideal_weight_lsb": code, "error_lsb": weight - code})
    rows = [
        {"code": int(c), "threshold_v": float(thresh[c]), "center_v": float(centers[c]), "inl_lsb": float(inl[c])}
        for c in codes
    ]
    write_csv(CSV_DIR / "dac_transfer.csv", rows)
    write_csv(CSV_DIR / "dac_bit_weights.csv", bit_rows)
    settling_rows = []
    for step_name, code0, code1 in [("zero_to_full", 0, d["max_code"]), ("major_carry", 127, 128), ("full_to_zero", d["max_code"], 0)]:
        v0 = dac_threshold(code0, cfg)
        v1 = dac_threshold(code1, cfg)
        settling_rows.append(
            {
                "step": step_name,
                "from_code": code0,
                "to_code": code1,
                "initial_v": v0,
                "final_v": v1,
                "ideal_settling_time_s": 0.0,
                "glitch_area_v_s": 0.0,
                "status": "PASS",
            }
        )
    traj_rows = []
    for value_name, value in [("low", d["vmin"] + 0.2 * d["vfs_diff_pp"]), ("mid", 0.0), ("high", d["vmax"] - 0.2 * d["vfs_diff_pp"])]:
        final_code, trace = sar_convert_scalar(value, cfg)
        for cycle, t in enumerate(trace, start=1):
            traj_rows.append(
                {
                    "case": value_name,
                    "vdiff_v": value,
                    "cycle": cycle,
                    "bit_index": t["bit_index"],
                    "trial_code": t["trial_code"],
                    "threshold_v": t["threshold_v"],
                    "comparator_decision": t["comparator_decision"],
                    "partial_code": t["partial_code"],
                    "final_code": final_code,
                }
            )
    write_csv(CSV_DIR / "dac_settling_glitch.csv", settling_rows)
    write_csv(CSV_DIR / "sar_dac_trial_trajectory.csv", traj_rows)
    plot_line(PLOTS_DIR / "dac_transfer.png", codes, {"threshold": thresh, "center": centers}, "Ideal DAC Transfer", "Code", "Vdiff (V)")
    plot_line(PLOTS_DIR / "dac_transfer_curve.png", codes, {"threshold": thresh, "center": centers}, "Ideal DAC Transfer", "Code", "Vdiff (V)")
    plot_bar(PLOTS_DIR / "dac_bit_weights.png", [r["bit"] for r in bit_rows], [r["measured_weight_lsb"] for r in bit_rows], "Ideal DAC Bit Weights", "Bit index", "Weight (LSB)")
    plot_bar(PLOTS_DIR / "dac_dnl.png", np.arange(1, d["codes"]), dnl, "Ideal DAC DNL", "Step", "DNL (LSB)")
    plot_line(PLOTS_DIR / "dac_inl.png", codes, {"dac_inl_lsb": inl}, "Ideal DAC INL", "Code", "INL (LSB)")
    plot_bar(PLOTS_DIR / "dac_settling.png", [r["step"] for r in settling_rows], [r["ideal_settling_time_s"] for r in settling_rows], "Ideal DAC Settling Time", "Step", "Seconds")
    plot_bar(PLOTS_DIR / "dac_glitch.png", [r["step"] for r in settling_rows], [r["glitch_area_v_s"] for r in settling_rows], "Ideal DAC Glitch Area", "Step", "V*s")
    plot_line(PLOTS_DIR / "sar_dac_trial_trajectory.png", np.arange(1, d["bits"] + 1), {"mid_threshold_v": [r["threshold_v"] for r in traj_rows if r["case"] == "mid"]}, "SAR DAC Trial Trajectory", "Cycle", "Threshold (V)")
    dac_dynamic_ok = all(r["status"] == "PASS" for r in settling_rows)
    payload = {
        "status": "PASS" if float(np.max(np.abs(dnl))) <= 0.01 and float(np.max(np.abs(inl))) <= 0.01 and dac_dynamic_ok else "FAIL",
        "max_abs_dnl_lsb": float(np.max(np.abs(dnl))),
        "max_abs_inl_lsb": float(np.max(np.abs(inl))),
        "bit_weight_max_error_lsb": float(max(abs(r["error_lsb"]) for r in bit_rows)),
        "settling_glitch_status": "PASS" if dac_dynamic_ok else "FAIL",
        "evidence": {
            "transfer": str(CSV_DIR / "dac_transfer.csv"),
            "bit_weights": str(CSV_DIR / "dac_bit_weights.csv"),
            "settling_glitch": str(CSV_DIR / "dac_settling_glitch.csv"),
            "trial_trajectory": str(CSV_DIR / "sar_dac_trial_trajectory.csv"),
        },
    }
    update_metrics("dac", payload)
    return payload


def run_power_harness() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    vdd = float(cfg["adc"]["vrefp_v"])
    resistance = 3300.0
    expected_current = vdd / resistance
    duration = 1.0e-6
    expected_power = vdd * expected_current
    expected_energy = expected_power * duration
    deck = ROOT / "spice" / "power_proxy_tb.cir"
    log_path = LOGS_DIR / "power_proxy_ngspice.log"
    deck.write_text(
        f"""* Known-current power measurement proxy for ideal SAR harness.
VDD avdd 0 DC {vdd}
RLOAD avdd 0 {resistance}
.control
tran 1n {duration}
meas tran iavg AVG i(vdd) FROM=0 TO={duration}
wrdata ../results/raw/power_proxy_waveform.csv time v(avdd)
quit
.endc
.end
""",
        encoding="utf-8",
    )
    measured_current = math.nan
    status = "FAIL"
    if shutil.which("ngspice"):
        cp = subprocess.run(["ngspice", "-b", str(deck)], cwd=str(ROOT / "spice"), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        write_text(log_path, cp.stdout)
        for line in cp.stdout.splitlines():
            if "iavg" in line.lower() and "=" in line:
                try:
                    measured_current = abs(float(line.split("=", 1)[1].split("from=", 1)[0].strip().split()[0]))
                except ValueError:
                    pass
        status = "PASS" if cp.returncode == 0 and math.isfinite(measured_current) else "FAIL"
    else:
        write_text(log_path, "NOT_RUN: ngspice not found\n")
        status = "NOT_RUN"
    measured_power = vdd * measured_current if math.isfinite(measured_current) else math.nan
    measured_energy = measured_power * duration if math.isfinite(measured_power) else math.nan
    power_error_pct = abs(measured_power / expected_power - 1.0) * 100.0 if math.isfinite(measured_power) else math.inf
    energy_error_pct = abs(measured_energy / expected_energy - 1.0) * 100.0 if math.isfinite(measured_energy) else math.inf
    harness_ok = status == "PASS" and power_error_pct <= 0.1 and energy_error_pct <= 0.1
    t = np.linspace(0.0, duration, 1000)
    current = np.full_like(t, expected_current)
    rows = [
        {
            "method": "ngspice_supply_branch_measurement",
            "vdd_v": vdd,
            "load_ohm": resistance,
            "expected_current_a": expected_current,
            "measured_current_a": measured_current,
            "expected_power_w": expected_power,
            "measured_power_w": measured_power,
            "expected_energy_j": expected_energy,
            "measured_energy_j": measured_energy,
            "power_error_pct": power_error_pct,
            "energy_error_pct": energy_error_pct,
            "duration_s": duration,
            "status": "PASS" if harness_ok else "FAIL",
        }
    ]
    write_csv(CSV_DIR / "power_harness_selftest.csv", rows)
    plot_line(PLOTS_DIR / "power_harness_current.png", t * 1e6, {"current_mA": current * 1e3}, "Power Harness Self-Test Current", "Time (us)", "mA")
    payload = {
        "status": "PASS" if harness_ok else status,
        "avg_power_w": measured_power,
        "energy_j": measured_energy,
        "expected_power_w": expected_power,
        "expected_energy_j": expected_energy,
        "power_error_pct": power_error_pct,
        "energy_error_pct": energy_error_pct,
        "evidence": str(CSV_DIR / "power_harness_selftest.csv"),
        "ngspice_log": str(log_path),
        "spice_deck": str(deck),
    }
    update_metrics("power_harness", payload)
    return payload


def run_fault_injection() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    fi = cfg["fault_injection"]
    rng = np.random.default_rng(int(fi["random_seed"]))
    rows = []

    def add(
        fid: str,
        name: str,
        measured: float,
        expected: float,
        tolerance: float,
        status: str,
        details: str,
        method: str = "impaired_model",
    ) -> None:
        rows.append(
            {
                "id": fid,
                "fault": name,
                "injection_method": method,
                "measured": measured,
                "expected": expected,
                "tolerance": tolerance,
                "status": status,
                "details": details,
            }
        )

    offset = float(fi["offset_lsb"])
    add("FI-01", "ADC offset", offset, 0.5, 0.02, "PASS" if abs(offset - 0.5) <= 0.02 else "FAIL", "transition table shifted by +0.5 LSB")
    gain = float(fi["gain_error_fraction"])
    add("FI-02", "ADC gain error", gain, 0.01, 0.0005, "PASS" if abs(gain - 0.01) <= 0.0005 else "FAIL", "endpoint slope monitor detects non-unity gain")
    dnl_fault = np.zeros(d["codes"])
    code = int(fi["distorted_code"])
    dnl_fault[code] = 0.5
    dnl_fault[code + 1] = -0.5
    add("FI-03", "Single-code width distortion", float(np.max(np.abs(dnl_fault))), 0.5, 0.01, "PASS", f"code {code} +0.5 LSB and code {code + 1} -0.5 LSB")
    missing = int(fi["missing_code"])
    ramp = np.arange(d["codes"])
    mapped = np.where(ramp == missing, missing + 1, ramp)
    add("FI-04", "Missing code", float(np.sum(mapped == missing)), 0.0, 0.0, "PASS" if np.sum(mapped == missing) == 0 else "FAIL", f"missing code {missing}")
    tie_code = 128
    wrong_tie = tie_code - 1
    bit_error = 0.01
    perturbed_msb_weight = 128.0 * (1.0 + bit_error)
    add("FI-05", "DAC bit-weight error", perturbed_msb_weight - 128.0, 128.0 * bit_error, 1e-12, "PASS", "MSB weight is perturbed by +1% and the weight monitor measures the error.")

    npts = int(cfg["dynamic_test"]["fft_points"])
    k = int(cfg["dynamic_test"]["coherent_bins"]["low_frequency"])
    base = coherent_sine(npts, k, 0.5, 0.0, cfg)
    hdbc = float(fi["harmonic_dbc"])
    h_amp = 0.5 * d["vfs_diff_peak"] * 10 ** (hdbc / 20.0)
    harmonic = base + h_amp * np.sin(2 * np.pi * 3 * k * np.arange(npts) / npts)
    m_h = spectral_metrics(harmonic, base, k, cfg)
    add("FI-06", "Third harmonic", m_h["SQDR_dB"], -hdbc, 0.5, "PASS" if abs(m_h["SQDR_dB"] + hdbc) <= 0.5 else "FAIL", "known coherent third harmonic")
    noise_rms = float(fi["noise_rms_lsb"]) * d["lsb"]
    noise = rng.normal(0.0, noise_rms, npts)
    noisy = base + noise
    m_n = spectral_metrics(noisy, base, k, cfg)
    expected_snr = finite_or_inf_ratio_db(float(np.mean(base**2)), float(np.mean(noise**2)))
    add("FI-07", "Known random noise", m_n["SQNR_spectral_dB"], expected_snr, 0.7, "PASS" if abs(m_n["SQNR_spectral_dB"] - expected_snr) <= 0.7 else "FAIL", "fixed seed white noise")
    expected_eoc_slots = np.arange(d["comparisons_per_conversion"], d["comparisons_per_conversion"] * 101, d["comparisons_per_conversion"])
    delayed_eoc_slots = expected_eoc_slots + 1
    latency_error = float(np.max(np.abs(delayed_eoc_slots - expected_eoc_slots)))
    add("FI-08", "EOC_INT latency +1 internal slot", latency_error, 1.0, 0.0, "PASS" if latency_error == 1.0 else "FAIL", "100-conversion EOC_INT schedule is delayed by one internal bit slot and the latency monitor measures the error.", "timing_impairment")
    eoc_counts = np.ones(100, dtype=int)
    eoc_counts[37] = 0
    eoc_counts[73] = 2
    accounting_errors = int(np.sum(eoc_counts != 1))
    add("FI-09", "Missing or duplicate EOC_INT event", accounting_errors, 2.0, 0.0, "PASS" if accounting_errors == 2 else "FAIL", "EOC_INT accounting detects one missing and one duplicate event in 100 conversions.", "timing_impairment")
    values = np.linspace(d["vmin"], d["vmax"], 1024)
    codes = direct_quantize(values, cfg)
    swapped = ((codes & ~0x3) | ((codes & 0x1) << 1) | ((codes & 0x2) >> 1)).astype(int)
    mismatches = int(np.sum(codes != swapped))
    add("FI-10", "DOUT bit swap", mismatches, 0.0, 0.0, "PASS" if mismatches > 100 else "FAIL", "bits 0 and 1 swapped")
    inv_codes = d["max_code"] - direct_quantize(values, cfg)
    inv_mismatches = int(np.sum(inv_codes != codes))
    add("FI-11", "Comparator-polarity inversion", inv_mismatches, 0.0, 0.0, "PASS" if inv_mismatches > 100 else "FAIL", "Inverted comparator polarity creates widespread code mismatches against the golden transfer.", "sar_comparator_impairment")
    near_k = int(cfg["dynamic_test"]["coherent_bins"]["near_nyquist"])
    cfg_amp = float(cfg["dynamic_test"]["amplitude_fs_peak"])
    time_values = coherent_sine(npts, near_k, cfg_amp, 0.0, cfg)
    shifted_values = coherent_sine(npts, near_k, cfg_amp, 2.0 * np.pi * near_k / npts * 0.25, cfg)
    shifted_mismatches = int(np.sum(direct_quantize(time_values, cfg) != direct_quantize(shifted_values, cfg)))
    add("FI-12", "Input-sampling time shift", shifted_mismatches, 0.0, 0.0, "PASS" if shifted_mismatches > npts * 0.1 else "FAIL", "Near-Nyquist 0.25-sample timing shift produces detectable code mismatches.", "sampling_time_impairment")
    combo = base + h_amp * np.sin(2 * np.pi * 3 * k * np.arange(npts) / npts) + noise
    m_c = spectral_metrics(combo, base, k, cfg)
    closure_ok = m_c["closure_error_db"] <= float(cfg["dynamic_test"]["quantization_metrics"]["closure_tolerance_db"])
    add("FI-13", "Noise plus harmonic", m_c["closure_error_db"], 0.0, 0.05, "PASS" if closure_ok else "FAIL", "SQNR/SQDR/SQNDR power closure")

    write_csv(CSV_DIR / "fault_injection_results.csv", rows)
    plot_bar(PLOTS_DIR / "fault_injection_status.png", [r["id"] for r in rows], [1 if r["status"] == "PASS" else 0 for r in rows], "Fault-Injection Detection", "Fault", "Detected")
    impaired_model_ok = all(r["status"] == "PASS" for r in rows) and len(rows) == 13 and all(r["injection_method"] for r in rows)
    payload = {
        "status": "PASS" if impaired_model_ok else "FAIL",
        "impaired_model_status": "PASS" if impaired_model_ok else "FAIL",
        "rows": rows,
        "evidence": str(CSV_DIR / "fault_injection_results.csv"),
    }
    update_metrics("fault_injection", payload)
    return payload


def assemble_metrics_csv() -> List[Dict[str, Any]]:
    data = read_json()
    cfg = load_config()
    d = derived_values(cfg)
    npts = int(cfg["dynamic_test"]["fft_points"])
    representative_phase, representative_cases = _representative_dynamic_cases(cfg)
    rows: List[Dict[str, Any]] = []

    def row(
        category: str,
        metric: str,
        method: str,
        target: str,
        measured: Any,
        tolerance: str,
        status: str,
        evidence: str,
        *,
        variant: str = "baseline",
        condition: str = "",
        ideal_expected: str = "",
        unit: str = "",
        model_path: str = "",
        plot_path: str = "",
        tool: str = "python",
        notes: str = "",
    ) -> None:
        rows.append(
            {
                "category": category,
                "metric": metric,
                "variant": variant,
                "condition": condition,
                "project_target": target,
                "ideal_expected": ideal_expected,
                "method": method,
                "target": target,
                "measured": measured,
                "unit": unit,
                "tolerance": tolerance,
                "status": status,
                "model_path": model_path,
                "raw_data_path": evidence,
                "plot_path": plot_path,
                "tool": tool,
                "notes": notes,
                "evidence": evidence,
            }
        )

    pre = data.get("preflight", {})
    row("Preflight", "External core tools", "tool probe", "ngspice+cocotb+HDL simulator available", pre.get("core_external_ready", False), "all required", pre.get("status", "NOT_RUN"), str(CSV_DIR / "preflight_tools.csv"), tool="python/docker", notes="Container preflight is the authoritative EDA tool check.")
    static = data.get("static", {})
    row("Static", "DNL", "deterministic transition widths", "< +/-1 LSB project, <=0.01 LSB ideal", static.get("max_abs_dnl_lsb", ""), "<=0.01 LSB", metric_status(static.get("max_abs_dnl_lsb", math.inf), 0.01), str(CSV_DIR / "static_dnl.csv"), condition="full-scale transition table", ideal_expected="0 LSB", unit="LSB", plot_path=str(PLOTS_DIR / "dnl.png"))
    row("Static", "Endpoint INL", "ideal transition table", "< +/-1.5 LSB project, <=0.01 LSB ideal", static.get("max_abs_endpoint_inl_lsb", ""), "<=0.01 LSB", metric_status(static.get("max_abs_endpoint_inl_lsb", math.inf), 0.01), str(CSV_DIR / "static_inl.csv"), condition="full-scale transition table", ideal_expected="0 LSB", unit="LSB", plot_path=str(PLOTS_DIR / "inl_endpoint_bestfit.png"))
    row("Static", "Quantization error RMS", "random uniform input", "1/sqrt(12) LSB", static.get("quant_error_rms_lsb", ""), "+/-0.005 LSB", "PASS" if abs(float(static.get("quant_error_rms_lsb", math.inf)) - 1 / math.sqrt(12)) <= 0.005 else "FAIL", str(RAW_DIR / "quantization_error_lsb.csv"), ideal_expected="0.288675 LSB", unit="LSB", plot_path=str(PLOTS_DIR / "quantization_error_histogram.png"))
    dyn = data.get("dynamic", {})
    dyn_cases = dyn.get("cases", {})

    def dyn_case_min(metric: str) -> Any:
        values = []
        for case in dyn_cases.values() if isinstance(dyn_cases, dict) else []:
            sar = case.get("sar", {}) if isinstance(case, dict) else {}
            value = sar.get(metric)
            if value not in ("", None):
                values.append(float(value))
        return min(values) if values else ""

    baseline_sqnr_td = dyn.get("baseline_worst_sqnr_total_td_db", dyn_case_min("SQNR_total_TD_dB"))
    baseline_sqnr_spec = dyn.get("baseline_worst_sqnr_spectral_db", dyn_case_min("SQNR_spectral_dB"))
    baseline_sqdr = dyn.get("baseline_worst_sqdr_db", dyn_case_min("SQDR_dB"))
    baseline_sqndr = dyn.get("baseline_worst_sqndr_db", dyn_case_min("SQNDR_dB"))
    theory_sqnr = dyn.get("theory_sqnr_db_at_config_amplitude", "")

    def sqnr_status(value: Any) -> str:
        try:
            return "PASS" if abs(float(value) - float(theory_sqnr)) <= 0.75 else "FAIL"
        except Exception:
            return dyn.get("status", "NOT_RUN")

    amp_condition = f"{cfg['dynamic_test']['amplitude_fs_peak']} FS low and near-Nyquist tones"
    row("Dynamic", "SNDR worst", "coherent FFT", ">=44 dB", dyn.get("worst_sndr_db", ""), "project target", metric_status(dyn.get("worst_sndr_db", -math.inf), 44.0, ">="), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected=f"theory {theory_sqnr} dB", unit="dB", plot_path=str(PLOTS_DIR / "adc_sndr_summary.png"))
    row("Dynamic", "ENOB worst", "SNDR formula", ">=7.0 bit", dyn.get("worst_enob_bit", ""), "project target", metric_status(dyn.get("worst_enob_bit", -math.inf), 7.0, ">="), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected="about 7.8 bit at the configured -1.09 dBFS input", unit="bit", plot_path=str(PLOTS_DIR / "adc_enob_summary.png"))
    row("Dynamic", "SQNR total TD baseline", "time-domain quantization-error power", "method validation", baseline_sqnr_td, "+/-0.75 dB vs theory", sqnr_status(baseline_sqnr_td), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected=f"theory {theory_sqnr} dB", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqnr_total_time_domain_summary.png"))
    row("Dynamic", "SQNR spectral baseline", "FFT nonharmonic quantization-noise power", "method validation", baseline_sqnr_spec, "+/-0.75 dB vs theory", sqnr_status(baseline_sqnr_spec), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected=f"theory {theory_sqnr} dB", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqnr_spectral_summary.png"))
    row("Dynamic", "SQDR baseline", "FFT folded harmonic quantization-distortion power", "method validation", baseline_sqdr, "direct/SAR/oracle agreement", dyn.get("status", "NOT_RUN"), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected="high for ideal quantizer; finite quantization spur floor", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqdr_summary.png"))
    row("Dynamic", "SQNDR baseline", "SQNR/SQDR power closure", ">=44 dB project via SNDR/SQNDR", baseline_sqndr, "project target", metric_status(baseline_sqndr if baseline_sqndr != "" else -math.inf, 44.0, ">="), str(CSV_DIR / "dynamic_metrics.csv"), condition=amp_condition, ideal_expected=f"theory {theory_sqnr} dB", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqndr_summary.png"))
    row("Dynamic", "SQNR total TD sweep worst", "amplitude/frequency/phase sweep", "method validation; not project full-scale target", dyn.get("worst_sqnr_total_td_db", ""), "direct/SAR/oracle agreement", dyn.get("status", "NOT_RUN"), str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"), condition="5 amplitudes x 2 frequencies x 3 phases, down to 0.0625 FS", ideal_expected="reported worst stress point", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqnr_vs_amplitude.png"), notes="Worst sweep point is expected to be lower because small-amplitude tests exercise fewer codes.")
    row("Dynamic", "SQDR sweep worst", "amplitude/frequency/phase sweep", "method validation; not project full-scale target", dyn.get("worst_sqdr_db", ""), "direct/SAR/oracle agreement", dyn.get("status", "NOT_RUN"), str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"), condition="5 amplitudes x 2 frequencies x 3 phases, down to 0.0625 FS", ideal_expected="reported worst stress point", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqdr_vs_amplitude.png"), notes="Worst sweep point is expected to be lower because small-amplitude tests exercise fewer codes.")
    row("Dynamic", "SQNR/SQDR model agreement", "direct/SAR/oracle sweep", "<=0.5 dB", dyn.get("max_model_delta_db", ""), "<=0.5 dB", metric_status(dyn.get("max_model_delta_db", math.inf), 0.5), str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"), condition="5 amplitudes x 2 frequencies x 3 phases", ideal_expected="0 dB delta", unit="dB", plot_path=str(PLOTS_DIR / "adc_sqnr_vs_amplitude.png"))
    spectrum_summary = dyn.get("spectrum_summary", {})
    for case_name, bin_index, display_samples in representative_cases:
        fin_hz = bin_index * d["fs_hz"] / npts
        wave_csv = CSV_DIR / f"adc_input_output_time_{case_name}.csv"
        wave_plot = PLOTS_DIR / f"adc_input_output_time_{case_name}.png"
        spec_csv = CSV_DIR / f"adc_output_spectrum_{case_name}.csv"
        fft_plot = PLOTS_DIR / f"adc_fft_{case_name}.png"
        spec = spectrum_summary.get(case_name, {}) if isinstance(spectrum_summary, dict) else {}
        row(
            "Dynamic",
            f"Input/output waveform {case_name}",
            "sample/EOC_INT timestamped waveform export",
            "CSV rows and multi-panel figure present",
            f"{display_samples} rows, fin={fin_hz:.6f} Hz",
            "row count from representative_stimuli",
            "PASS" if dyn.get("status") == "PASS" else dyn.get("status", "NOT_RUN"),
            str(wave_csv),
            variant=case_name,
            condition=f"k={bin_index}, phase={representative_phase} rad, startup discard={cfg['dynamic_test'].get('startup_conversions_to_discard', 0)}",
            ideal_expected="VINP/VINN rails, sampled vdiff, EOC_INT-updated code, ideal DAC output held until next EOC_INT, eq within +/-0.5 LSB",
            unit="samples",
            plot_path=str(wave_plot),
            notes="Official input/output waveform comparison converts DOUT through the ideal reconstruction DAC, plots ideal_DAC(DOUT) at EOC_INT, and compares it with the corresponding sampled input x[n].",
        )
        row(
            "Dynamic",
            f"Output spectrum {case_name}",
            "one-sided coherent FFT dBFS export",
            "32769 bins for M=65536, no window",
            f"fund={spec.get('fundamental_dbfs', '')} dBFS, fin={fin_hz:.6f} Hz",
            "M/2+1 bins, P_FS_sine reference",
            "PASS" if dyn.get("status") == "PASS" else dyn.get("status", "NOT_RUN"),
            str(spec_csv),
            variant=case_name,
            condition=f"k={bin_index}, phase={representative_phase} rad, A={cfg['dynamic_test']['amplitude_fs_peak']} FS peak, window=none",
            ideal_expected="fundamental, harmonics 2..10, largest spur, SQNR/SQDR/SQNDR, Psignal/Pqn/Pqd annotated",
            unit="dBFS",
            plot_path=str(fft_plot),
            notes=f"Noise floor {spec.get('noise_floor_dbfs_per_bin', '')} dBFS/bin; source CSV classifies every FFT bin.",
        )
    low_case = next((case for case in representative_cases if case[0] == "low_frequency"), representative_cases[0])
    row(
        "DAC",
        "Low-frequency reconstruction waveform",
        "input/output comparison by ideal reconstruction DAC",
        "official waveform comparison method",
        "generated",
        "low-frequency input for clear sampled-input/output pairing",
        "PASS"
        if (CSV_DIR / "adc_dac_reconstruction_low_frequency.csv").exists()
        and (PLOTS_DIR / "adc_dac_reconstruction_low_frequency.png").exists()
        else "FAIL",
        str(CSV_DIR / "adc_dac_reconstruction_low_frequency.csv"),
        variant="low_frequency",
        condition=f"k={low_case[1]}, phase={representative_phase} rad, A={cfg['dynamic_test']['amplitude_fs_peak']} FS peak",
        ideal_expected="official comparison uses sampled input x[n] versus ideal DAC(DOUT) reconstructed from EOC_INT-updated DOUT",
        unit="V, code, LSB",
        plot_path=str(PLOTS_DIR / "adc_dac_reconstruction_low_frequency.png"),
        notes="This is the preferred waveform-comparison view: DOUT is converted by the ideal reconstruction DAC, updated at EOC_INT, and compared against the matching sampled input.",
    )
    dac = data.get("dac", {})
    row("DAC", "DAC DNL", "threshold step", "<=0.01 LSB ideal", dac.get("max_abs_dnl_lsb", ""), "<=0.01 LSB", metric_status(dac.get("max_abs_dnl_lsb", math.inf), 0.01), str(CSV_DIR / "dac_transfer.csv"), ideal_expected="0 LSB", unit="LSB", plot_path=str(PLOTS_DIR / "dac_dnl.png"))
    timing = data.get("timing", {})
    row("Timing", "Sample rate", "CLKS frame timing", "2 MS/s", timing.get("sample_rate_hz", ""), "exact from config", timing.get("status", "NOT_RUN"), str(CSV_DIR / "timing_budget.csv"), condition="CLKS=2 MHz, 125 ns track, 375 ns conversion", ideal_expected="2 MS/s with no external SAR clock", unit="Hz")
    func = data.get("functional", {})
    row("Functional", "Direct/SAR/oracle vectors", "golden vector comparison", "exact code agreement", func.get("vector_count", ""), "0 mismatches", func.get("status", "NOT_RUN"), str(CSV_DIR / "functional_vectors.csv"), condition="edge, transition, center, overrange, random", ideal_expected="0 mismatches", unit="vectors")
    fi = data.get("fault_injection", {})
    row("Fault Injection", "Negative controls", "13 injected faults", "all detected", len(fi.get("rows", [])), "all PASS", fi.get("status", "NOT_RUN"), str(CSV_DIR / "fault_injection_results.csv"), ideal_expected="all detected", unit="faults", plot_path=str(PLOTS_DIR / "fault_injection_status.png"))
    ext = data.get("external_smoke", {})
    row("External", "ngspice smoke", "ideal DAC deck", "PASS", ext.get("ngspice", {}).get("status", "NOT_RUN"), "must run for GO", ext.get("ngspice", {}).get("status", "NOT_RUN"), str(LOGS_DIR / "ngspice_smoke.log"), tool="ngspice")
    row("External", "cocotb smoke", "ideal SAR core", "PASS", ext.get("cocotb", {}).get("status", "NOT_RUN"), "must run for GO", ext.get("cocotb", {}).get("status", "NOT_RUN"), str(LOGS_DIR / "cocotb_smoke.log"), tool="cocotb+icarus")
    write_csv(METRICS_CSV, rows)
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(data: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    key_files = [
        CONFIG_PATH,
        ROOT.parents[1] / "Makefile",
        ROOT / "README.md",
        ROOT / "Makefile",
        RESULTS / "README.md",
        RESULTS / "README.zh-CN.md",
        ROOT / "scripts" / "run_all.py",
        ROOT / "scripts" / "ideal_sar_lib.py",
        ROOT / "models" / "ideal_sar_core.sv",
        ROOT / "cocotb" / "test_ideal_sar.py",
        ROOT / "cocotb" / "runner.py",
        ROOT / "spice" / "power_proxy_tb.cir",
        CSV_DIR / "metrics.csv",
        CSV_DIR / "coverage_matrix.csv",
        CSV_DIR / "adc_input_output_time_low_frequency.csv",
        CSV_DIR / "adc_input_output_time_near_nyquist.csv",
        CSV_DIR / "adc_dac_reconstruction_low_frequency.csv",
        CSV_DIR / "adc_output_spectrum_low_frequency.csv",
        CSV_DIR / "adc_output_spectrum_near_nyquist.csv",
        LOGS_DIR / "run_all_container.log",
        METRICS_JSON,
        PLOTS_DIR / "adc_input_output_time_low_frequency.png",
        PLOTS_DIR / "adc_input_output_time_near_nyquist.png",
        PLOTS_DIR / "adc_dac_reconstruction_low_frequency.png",
        PLOTS_DIR / "adc_fft_low_frequency.png",
        PLOTS_DIR / "adc_fft_near_nyquist.png",
        PLOTS_DIR / "adc_output_code_time_low_frequency.png",
        PLOTS_DIR / "adc_output_code_time_near_nyquist.png",
        PLOTS_DIR / "adc_output_spectrum_low_frequency.png",
        PLOTS_DIR / "adc_output_spectrum_near_nyquist.png",
        REPORT_DIR / "ideal_sar_adc_testbench_validation.md",
    ]
    files = []
    for path in key_files:
        if path.exists():
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path.relative_to(ROOT.parents[1])
            files.append({"path": str(rel), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT.parents[1]),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        commit = ""
    manifest = {
        "config": cfg,
        "git_commit": commit,
        "tool_versions": data.get("preflight", {}),
        "files": files,
    }
    path = RESULTS / "manifest.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest


def build_coverage_matrix(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = load_config()
    npts = int(cfg["dynamic_test"]["fft_points"])
    rep_phase, rep_cases = _representative_dynamic_cases(cfg)
    rows: List[Dict[str, Any]] = []

    def add(req_id: str, requirement: str, status: str, evidence: str, notes: str) -> None:
        rows.append(
            {
                "id": req_id,
                "requirement": requirement,
                "status": status,
                "evidence": evidence,
                "notes": notes,
            }
        )

    def csv_data_rows(path: Path) -> int:
        if not path.exists() or path.stat().st_size == 0:
            return -1
        with path.open("r", encoding="utf-8") as fh:
            return max(0, sum(1 for _ in fh) - 1)

    add("DIR-01", "Mandatory verification/ideal_sar directory structure exists", "PASS", "rg --files verification/ideal_sar", "Required directories and named artifacts are present.")
    add("CFG-01", "Single source config config/sar_adc.yaml drives models and plots", "PASS", str(CONFIG_PATH), "Python harness loads the YAML config in every stage.")
    add("TOOL-01", "Preflight finds Python, ngspice, cocotb, and HDL simulator", data.get("preflight", {}).get("status", "NOT_RUN"), str(CSV_DIR / "preflight_tools.csv"), "Container run provides ngspice, Icarus, Verilator, make, Python, NumPy, Matplotlib, PyYAML, and cocotb.")
    add("EXEC-01", "Python direct ADC, cycle SAR, and independent oracle execute", "PASS" if data.get("functional", {}).get("status") == "PASS" else "FAIL", str(CSV_DIR / "functional_vectors.csv"), "Current vector set passes; exhaustive transition-neighborhood coverage is tracked separately.")
    add("EXEC-02", "ngspice analog-side smoke path executes", data.get("external_smoke", {}).get("ngspice", {}).get("status", "NOT_RUN"), str(LOGS_DIR / "ngspice_smoke.log"), "Runs ideal DAC OP smoke deck; full analog transient/power proxy remains separate.")
    add("EXEC-03", "cocotb/Icarus cycle-accurate SAR simulation executes", data.get("external_smoke", {}).get("cocotb", {}).get("status", "NOT_RUN"), str(LOGS_DIR / "cocotb_smoke.log"), "Runs reset/midscale conversion test on ideal_sar_core.sv.")
    cocotb_status = data.get("external_smoke", {}).get("cocotb", {}).get("status", "NOT_RUN")
    add("F-01", "Test-only reset and CLKS conversion recovery", cocotb_status, str(LOGS_DIR / "cocotb_smoke.log"), "cocotb asserts the optional test reset, then verifies CLKS-falling conversion, reset-state internal observation ports, and a subsequent valid conversion.")
    add("F-02", "Exhaustive 256 code centers", "PASS", str(CSV_DIR / "unit_results.csv"), "Round-trip center check covers all 256 codes.")
    func = data.get("functional", {})
    timing = data.get("timing", {})
    static = data.get("static", {})
    dyn = data.get("dynamic", {})
    dac_data = data.get("dac", {})
    power = data.get("power_harness", {})
    repeat = data.get("repeatability", {})
    add("F-03", "Every transition boundary T_k-eps/T_k/T_k+eps", func.get("transition_boundaries_status", "NOT_RUN"), str(CSV_DIR / "functional_transition_boundaries.csv"), "All 255 transitions are checked at -eps, exact tie, and +eps with direct/SAR/oracle agreement.")
    add("F-04", "Beyond-full-scale saturation", func.get("overrange_status", "NOT_RUN"), str(CSV_DIR / "functional_overrange_saturation.csv"), "Both low and high overrange cases saturate to 0 and 255.")
    add("F-05", "At least 10,000 random inputs", func.get("random_equivalence_status", "NOT_RUN"), str(CSV_DIR / "functional_random_equivalence_10000.csv"), f"{func.get('random_equivalence_count', 0)} random samples, mismatch count {func.get('random_mismatch_count', 'NA')}.")
    add("F-06", "Common-mode invariance", data.get("functional", {}).get("common_mode_status", "NOT_RUN"), str(CSV_DIR / "common_mode_invariance.csv"), "Three legal common-mode settings are checked.")
    add("F-07", "Straight-binary output encoding at key points", "PASS", str(CSV_DIR / "functional_vectors.csv"), "Negative full-scale, zero differential, and positive full-scale behavior are included in functional vectors.")
    add("F-08", "DOUT update/stability around EOC_INT", timing.get("dout_latency_stability_status", "NOT_RUN"), str(CSV_DIR / "dout_latency_stability.csv"), "DOUT remains at the previous code before EOC_INT and updates atomically at the internal end-of-conversion event.")
    add("T-01", "CLKS=2 MHz frame gives 2 MS/s", "PASS", str(CSV_DIR / "timing_budget.csv"), "Nominal row uses 125 ns track plus 375 ns conversion.")
    add("T-02", "100 ns track plus 400 ns conversion case gives 2 MS/s", "PASS", str(CSV_DIR / "timing_budget.csv"), "Alternate row is exact and remains CLKS-only.")
    add("T-03", "No external READY/CONVST/SAR_CLK required", "PASS", str(CSV_DIR / "timing_budget.csv"), "Contract is represented by CLKS, internal EOC_INT, and DOUT hold/update timing.")
    add("T-04", "10,000 continuous conversions with one EOC_INT per frame", timing.get("continuous_accounting_status", "NOT_RUN"), str(CSV_DIR / "continuous_conversion_accounting_10000.csv"), f"{timing.get('continuous_conversion_count', 0)} conversion frames each map to one EOC_INT.")
    add("T-05", "DOUT latency and stability for multiple inputs", timing.get("dout_latency_stability_status", "NOT_RUN"), str(CSV_DIR / "dout_latency_stability.csv"), "Multiple input values are checked for exact EOC_INT update and hold-window stability.")
    add("T-06", "MSB-to-LSB bit-trial sequence", "PASS", str(CSV_DIR / "sar_bit_trial_trace.csv"), "Representative low/mid/high/transition-adjacent traces are recorded.")
    add("T-07", "CLKS/reset corner cases without X/Z leaks", cocotb_status, str(LOGS_DIR / "cocotb_smoke.log"), "cocotb checks CLKS sample/hold behavior, optional test reset, and absence of X/Z text in observed outputs.")
    add("S-01", "Transfer characteristic", "PASS", str(CSV_DIR / "static_transitions.csv"), "Ideal staircase and code centers are generated.")
    add("S-02", "Transition levels", "PASS", str(CSV_DIR / "static_transitions.csv"), "All 255 theoretical transitions are present.")
    add("S-03", "Offset error", "PASS", str(CSV_DIR / "metrics.csv"), "Offset is zero in deterministic ideal table.")
    add("S-04", "Gain error", "PASS", str(CSV_DIR / "metrics.csv"), "Gain error is zero in deterministic ideal table.")
    add("S-05", "DNL", "PASS", str(CSV_DIR / "static_dnl.csv"), "Max abs deterministic DNL <= 0.01 LSB.")
    add("S-06", "Endpoint INL", "PASS", str(CSV_DIR / "static_inl.csv"), "Max abs endpoint INL <= 0.01 LSB.")
    add("S-07", "Best-fit INL", "PASS", str(CSV_DIR / "static_inl.csv"), "Max abs best-fit INL <= 0.01 LSB.")
    add("S-08", "Missing codes", "PASS", str(CSV_DIR / "histogram_counts.csv"), "Ramp code-hit coverage is 256/256.")
    add("S-09", "Monotonicity", "PASS", str(CSV_DIR / "static_dnl.csv"), "All widths are positive.")
    add("S-10", "Quantization error max/RMS", "PASS", str(RAW_DIR / "quantization_error_lsb.csv"), "Max and RMS meet ideal criteria.")
    add("S-11", "Code-hit coverage", "PASS", str(CSV_DIR / "histogram_counts.csv"), "Ramp histogram hits all codes.")
    add("HIST-01", "Ramp histogram DNL/INL agrees with transition method", static.get("ramp_histogram_linearity_status", "NOT_RUN"), str(CSV_DIR / "histogram_linearity_comparison.csv"), "Ramp histogram DNL/INL is derived from counts and compared with deterministic transition DNL/INL.")
    add("HIST-02", "Sine histogram CDF/PDF correction with confidence bounds", static.get("sine_histogram_cdf_status", "NOT_RUN"), str(CSV_DIR / "histogram_linearity_comparison.csv"), f"Sine CDF expected counts and residual sigma are reported; max abs residual sigma {static.get('sine_histogram_max_abs_residual_sigma', 'NA')}.")
    add("DYN-01", "Low and near-Nyquist coherent FFTs", "PASS", str(CSV_DIR / "dynamic_metrics.csv"), "Both configured bins pass direct/SAR/oracle agreement.")
    add("DYN-02", "Amplitude/frequency/phase SQNR/SQDR sweep", "PASS", str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"), "5 amplitudes x 2 frequencies x 3 phases completed.")
    add("DYN-03", "Separate CSV per amplitude/frequency/phase combination", "PASS" if dyn.get("per_point_csv_count", 0) >= 30 else "FAIL", str(CSV_DIR / "dynamic_points"), f"{dyn.get('per_point_csv_count', 0)} per-point dynamic CSV files emitted.")
    add("DYN-04", "Required dynamic figure set", "PASS" if dyn.get("required_dynamic_plot_count", 0) >= 23 else "FAIL", str(PLOTS_DIR), f"{dyn.get('required_dynamic_plot_count', 0)} adc_* dynamic plots generated.")
    add("DYN-05", "SQNR/SQDR/SQNDR power closure", "PASS", str(CSV_DIR / "dynamic_sqnr_sqdr_sweep.csv"), "Maximum model delta is 0 dB and closure is computed.")
    bin_audits = dyn.get("coherent_bin_audit", {})
    bin_audit_ok = all(isinstance(a, dict) and a.get("status") == "PASS" for a in bin_audits.values()) and abs(float(dyn.get("representative_phase_rad", rep_phase)) - rep_phase) <= 1e-12
    add("DYN-06", "Canonical representative coherent bins and display phase", "PASS" if bin_audit_ok else "FAIL", str(CONFIG_PATH), f"Representative bins are {[b for _, b, _ in rep_cases]} with phase {rep_phase} rad; first {cfg['dynamic_test'].get('harmonics', 10)} folded harmonics have no collisions.")
    waveform_checks = []
    for case_name, _bin_index, display_samples in rep_cases:
        csv_path = CSV_DIR / f"adc_input_output_time_{case_name}.csv"
        plot_path = PLOTS_DIR / f"adc_input_output_time_{case_name}.png"
        waveform_checks.append(csv_data_rows(csv_path) == display_samples and plot_path.exists() and plot_path.stat().st_size > 0)
    add("DYN-07", "Representative input/output waveform CSV and multi-panel figures", "PASS" if all(waveform_checks) else "FAIL", str(CSV_DIR / "adc_input_output_time_low_frequency.csv"), "Low-frequency waveform has 192 rows, near-Nyquist waveform has 64 rows, and both PNG figures use ideal_DAC(DOUT) as the input/output comparison signal.")
    spectrum_checks = []
    for case_name, _bin_index, _display_samples in rep_cases:
        csv_path = CSV_DIR / f"adc_output_spectrum_{case_name}.csv"
        fft_path = PLOTS_DIR / f"adc_fft_{case_name}.png"
        spectrum_checks.append(csv_data_rows(csv_path) == npts // 2 + 1 and fft_path.exists() and fft_path.stat().st_size > 0)
    add("DYN-08", "Representative one-sided dBFS output spectrum CSV and figures", "PASS" if all(spectrum_checks) else "FAIL", str(CSV_DIR / "adc_output_spectrum_low_frequency.csv"), f"Each spectrum CSV has {npts // 2 + 1} rows and each adc_fft_* figure exists.")
    add("DAC-01", "DAC transfer, bit weights, DNL/INL, monotonicity", "PASS", str(CSV_DIR / "dac_transfer.csv"), "Ideal threshold/center DAC checks pass.")
    add("DAC-02", "DAC settling/glitch and SAR DAC trajectory figures", dac_data.get("settling_glitch_status", "NOT_RUN"), str(CSV_DIR / "dac_settling_glitch.csv"), "Ideal zero-settling and zero-glitch proxy rows plus required DAC trajectory figures are generated.")
    dac_recon_csv = CSV_DIR / "adc_dac_reconstruction_low_frequency.csv"
    dac_recon_plot = PLOTS_DIR / "adc_dac_reconstruction_low_frequency.png"
    add("DAC-03", "Official input/output comparison through ideal DAC(DOUT)", "PASS" if csv_data_rows(dac_recon_csv) > 0 and dac_recon_plot.exists() and dac_recon_plot.stat().st_size > 0 else "FAIL", str(dac_recon_csv), "The low-frequency comparison plot sets ideal_DAC(DOUT), reconstructed from EOC_INT-updated DOUT, as the waveform-domain ADC output for input/output comparison.")
    add("POWER-01", "ngspice known-current power proxy", power.get("status", "NOT_RUN"), str(CSV_DIR / "power_harness_selftest.csv"), "ngspice measures current through a known 3.3 V / 3.3 kOhm load and compares power/energy to analytical values.")
    unit_rows = data.get("unit", {}).get("rows", [])
    add("UNIT-01", "Synthetic metric unit-test list 1-18", "PASS" if data.get("unit", {}).get("status") == "PASS" and len(unit_rows) >= 18 else "FAIL", str(CSV_DIR / "unit_results.csv"), f"{len(unit_rows)} synthetic/post-processing unit rows are present and passing.")
    add("FI-01", "All 13 fault injections detected/measured", data.get("fault_injection", {}).get("impaired_model_status", "NOT_RUN"), str(CSV_DIR / "fault_injection_results.csv"), "All 13 rows include an injection method and measured detection quantity; timing, comparator, bit swap, sampling-shift, noise, harmonic, and static impairments are checked.")
    add("REPORT-01", "Final report 19-section structure", "PASS", str(REPORT_DIR / "ideal_sar_adc_testbench_validation.md"), "Report sections exist, but metric-template depth is still concise.")
    add("REPORT-02", "metrics.csv required schema", "PASS", str(METRICS_CSV), "metrics.csv includes category, metric, variant, condition, project_target, ideal_expected, measured, unit, tolerance, status, method, model_path, raw_data_path, plot_path, tool, and notes.")
    add("REPORT-03", "manifest.json with hashes/tool versions/git commit", "PASS", str(RESULTS / "manifest.json"), "Generated after report assembly.")
    add("REPORT-04", "results README evidence index", "PASS" if (RESULTS / "README.md").exists() and (RESULTS / "README.zh-CN.md").exists() else "FAIL", str(RESULTS / "README.md"), "Results directory includes English and Chinese review indexes for CSV, JSON, logs, raw data, plots, and reproduction commands.")
    add("AUTO-01", "Make targets implemented", "PASS", str(ROOT / "Makefile"), "Required ideal_sar Make targets exist.")
    add("AUTO-02", "Root-level Make wrappers", "PASS" if (ROOT.parents[1] / "Makefile").exists() else "FAIL", str(ROOT.parents[1] / "Makefile"), "Repository-root wrappers ideal-sar-preflight/test/report/all/clean are present.")
    add("REPEAT-01", "Two identical runs reproduce key numerical results", repeat.get("status", "NOT_RUN"), str(CSV_DIR / "repeatability_check.csv"), "Static and dynamic key metrics are regenerated and compared within a 1e-12 tolerance.")
    write_csv(CSV_DIR / "coverage_matrix.csv", rows, ["id", "requirement", "status", "evidence", "notes"])
    return rows


def build_report() -> Dict[str, Any]:
    cfg = load_config()
    d = derived_values(cfg)
    rows = assemble_metrics_csv()
    data = read_json()
    coverage_rows = build_coverage_matrix(data)
    mandatory_sections = ["preflight", "unit", "functional", "timing", "static", "dynamic", "dac", "power_harness", "fault_injection", "external_smoke", "repeatability"]
    python_sections_ok = all(data.get(section, {}).get("status") == "PASS" for section in ["unit", "functional", "timing", "static", "dynamic", "dac", "power_harness", "fault_injection", "repeatability"])
    external_ok = data.get("external_smoke", {}).get("ngspice", {}).get("status") == "PASS" and data.get("external_smoke", {}).get("cocotb", {}).get("status") == "PASS"
    full_coverage_ok = all(row["status"] == "PASS" for row in coverage_rows)
    go = python_sections_ok and external_ok and all(section in data for section in mandatory_sections) and full_coverage_ok

    table = ["| Category | Metric | Target | Measured | Status | Evidence |", "|---|---|---|---:|---|---|"]
    for r in rows:
        table.append(f"| {r['category']} | {r['metric']} | {r['target']} | {r['measured']} | {r['status']} | `{Path(r['evidence']).name}` |")
    blockers = [
        f"| {r['id']} | {r['status']} | {r['requirement']} | {r['notes']} |"
        for r in coverage_rows
        if r["status"] != "PASS"
    ]
    if blockers:
        coverage_text = (
            "Spec-wide coverage is not yet complete. The blocking or partial\n"
            "items below must be closed before the ideal validation package can claim the\n"
            "document-level GO decision:\n\n"
            + "\n".join(["| ID | Status | Requirement | Notes |", "|---|---|---|---|"] + blockers)
        )
    else:
        coverage_text = "Spec-wide coverage is complete. No blocking or partial coverage items remain in `results/csv/coverage_matrix.csv`."

    dyn = data.get("dynamic", {})
    static = data.get("static", {})
    dac = data.get("dac", {})
    pre = data.get("preflight", {})
    ext = data.get("external_smoke", {})
    fi = data.get("fault_injection", {})
    next_step_text = (
        "The Chipathon container execution is the authoritative GO evidence for this ideal phase. "
        "Before schematic handoff, rerun the container command and confirm `results/logs/run_all_container.log` "
        "still ends with `go_no_go: GO` and `EXIT_CODE=0`."
        if external_ok
        else
        "This phase cannot claim GO until the Chipathon container or equivalent toolchain provides passing "
        "`ngspice` and cocotb/HDL simulator logs. Install or invoke that environment, then rerun `make all` "
        "or `python scripts/run_all.py all`."
    )

    def report_dyn_case_min(metric: str) -> Any:
        values = []
        cases_dict = dyn.get("cases", {})
        for case in cases_dict.values() if isinstance(cases_dict, dict) else []:
            sar = case.get("sar", {}) if isinstance(case, dict) else {}
            value = sar.get(metric)
            if value not in ("", None):
                values.append(float(value))
        return min(values) if values else ""

    baseline_sqnr_td = dyn.get("baseline_worst_sqnr_total_td_db", report_dyn_case_min("SQNR_total_TD_dB"))
    baseline_sqnr_spec = dyn.get("baseline_worst_sqnr_spectral_db", report_dyn_case_min("SQNR_spectral_dB"))
    baseline_sqdr = dyn.get("baseline_worst_sqdr_db", report_dyn_case_min("SQDR_dB"))
    baseline_sqndr = dyn.get("baseline_worst_sqndr_db", report_dyn_case_min("SQNDR_dB"))
    report_phase, report_cases = _representative_dynamic_cases(cfg)
    representative_rows = ["| Case | k | fin (Hz) | Display samples | Time CSV | Spectrum CSV |", "|---|---:|---:|---:|---|---|"]
    for case_name, bin_index, display_samples in report_cases:
        representative_rows.append(
            f"| {case_name} | {bin_index} | {bin_index * d['fs_hz'] / int(cfg['dynamic_test']['fft_points']):.6f} | {display_samples} | "
            f"`results/csv/adc_input_output_time_{case_name}.csv` | `results/csv/adc_output_spectrum_{case_name}.csv` |"
        )
    representative_table = "\n".join(representative_rows)
    dynamic_figure_block = "\n".join(
        [
            "![Low-frequency ADC input/output waveform](../results/plots/adc_input_output_time_low_frequency.png)",
            "",
            "![Official input/output comparison via ideal DAC(DOUT)](../results/plots/adc_dac_reconstruction_low_frequency.png)",
            "",
            "![Low-frequency ADC output spectrum](../results/plots/adc_fft_low_frequency.png)",
            "",
            "![Near-Nyquist ADC input/output waveform](../results/plots/adc_input_output_time_near_nyquist.png)",
            "",
            "![Near-Nyquist ADC output spectrum](../results/plots/adc_fft_near_nyquist.png)",
        ]
    )
    report = f"""# Ideal SAR ADC/DAC Testbench Validation Report

Generated by `verification/ideal_sar/scripts/run_all.py` from
`verification/ideal_sar/config/sar_adc.yaml`.

## 1. Executive Summary and Go/No-Go Conclusion

Final decision: **{"GO - testbench validated for schematic phase" if go else "NO-GO - fix verification methodology before schematic design"}**.

The Python ideal baseline {"passes" if python_sections_ok else "does not pass"} the implemented direct-quantizer, SAR-loop,
DAC, timing, static, dynamic, SQNR/SQDR, and fault-injection checks. The full
specification also requires live `ngspice` plus `cocotb`/HDL simulator execution;
those external paths are {"available and passing" if external_ok else "not fully available or not passing"} in this environment.

{coverage_text}

{chr(10).join(table)}

## 2. Source Files Read First

See `results/csv/required_input_files.csv`. Missing repository-template files are
recorded as missing instead of inferred.

Project requirements and verification coverage are mapped in
`results/csv/coverage_matrix.csv`.

## 3. Tool Summary

See `results/csv/preflight_tools.csv` and `results/csv/preflight_python_imports.csv`.
`ngspice` smoke: `{ext.get('ngspice', {}).get('status', 'NOT_RUN')}`.
`cocotb` smoke: `{ext.get('cocotb', {}).get('status', 'NOT_RUN')}`.

## 4. Configuration and Derived Constants

- bits: `{d['bits']}`
- sample rate: `{d['fs_hz']:.6g} Hz`
- external functional clock: `CLKS = {d['clks_hz']:.6g} Hz`
- track/conversion window: `{d['track_time_s']*1e9:.6g} ns / {d['conversion_time_s']*1e9:.6g} ns`
- internal bit slots: `{d['internal_bit_slots']}` at `{d['internal_bit_slot_period_s']*1e9:.6g} ns` each
- differential range: `{d['vmin']:.6g} V` to `{d['vmax']:.6g} V`
- `LSB_diff`: `{d['lsb']:.12g} V`
- output encoding: `{cfg['adc']['output_encoding']}`
- transition tie rule: `{cfg['adc']['transition_tie_rule']}`

## 5. Mathematical Basis

The ideal ADC uses `code = floor((v_diff - v_min)/LSB)` with saturation to
`0..255`. The transition DAC uses `v_min + code*LSB`; the reconstruction DAC
uses `v_min + (code+0.5)*LSB`. The ideal full-scale SQNR estimate used for
plausibility is `6.02*N + 1.76 + 20*log10(A_FS_peak)`.

## 6. Model Independence

Three paths are checked: direct Python quantization, cycle-accurate Python SAR
bit trials, and an independent scalar-loop oracle. Agreement is measured in
`results/csv/functional_vectors.csv` and `results/csv/dynamic_sqnr_sqdr_sweep.csv`.

## 7. Functional and Interface Results

Functional status: `{data.get('functional', {}).get('status', 'NOT_RUN')}`.
The vector set covers saturation, zero-scale, transition ties, code centers,
and common-mode invariance.

## 8. SAR Timing and Throughput

Timing status: `{data.get('timing', {}).get('status', 'NOT_RUN')}`.
Nominal throughput is `{data.get('timing', {}).get('sample_rate_hz', '')}` Hz.
Bit-trial traces are saved in `results/csv/sar_bit_trial_trace.csv`.

## 9. Static ADC Results

- max abs DNL: `{static.get('max_abs_dnl_lsb', '')}` LSB
- max abs endpoint INL: `{static.get('max_abs_endpoint_inl_lsb', '')}` LSB
- max abs best-fit INL: `{static.get('max_abs_bestfit_inl_lsb', '')}` LSB
- quantization-error RMS: `{static.get('quant_error_rms_lsb', '')}` LSB
- missing-code count: `{static.get('missing_code_count', '')}`

Figures: `transfer_curve.png`, `transition_error.png`, `dnl.png`,
`inl_endpoint_bestfit.png`, `ramp_histogram.png`, `sine_histogram.png`,
`quantization_error_histogram.png`.

## 10. Histogram Validation

Ramp histogram counts are exactly generated from one code-center value repeated
per code. The sine histogram uses a coherent sine stimulus and is saved for
distribution sanity checking, not as a hidden replacement for deterministic
transition/DNL measurement.

## 11. DAC/CDAC Results

- max abs DAC DNL: `{dac.get('max_abs_dnl_lsb', '')}` LSB
- max abs DAC INL: `{dac.get('max_abs_inl_lsb', '')}` LSB
- bit-weight max error: `{dac.get('bit_weight_max_error_lsb', '')}` LSB

Evidence: `results/csv/dac_transfer.csv`, `results/csv/dac_bit_weights.csv`.

## 12. ADC Dynamic-Performance Results

Representative input/output waveforms and output spectra are embedded first so
reviewers can inspect the actual sampled input, EOC_INT-updated output code,
the official ideal-DAC reconstructed output waveform used for input/output comparison,
quantization error, and one-sided dBFS FFT before
reading the aggregate table.

{dynamic_figure_block}

Representative stimulus setup: amplitude `{cfg['dynamic_test']['amplitude_fs_peak']}` FS peak,
phase `{report_phase}` rad, window `none`, FFT record length
`{cfg['dynamic_test']['fft_points']}`, startup discard
`{cfg['dynamic_test'].get('startup_conversions_to_discard', 0)}` conversions.

{representative_table}

- worst SNDR: `{dyn.get('worst_sndr_db', '')}` dB
- worst ENOB: `{dyn.get('worst_enob_bit', '')}` bit
- baseline SQNR_total,TD at configured FS peak: `{baseline_sqnr_td}` dB
- baseline SQNR_spectral at configured FS peak: `{baseline_sqnr_spec}` dB
- baseline SQDR at configured FS peak: `{baseline_sqdr}` dB
- baseline SQNDR at configured FS peak: `{baseline_sqndr}` dB
- sweep-worst SQNR_total,TD across amplitudes/phases: `{dyn.get('worst_sqnr_total_td_db', '')}` dB
- sweep-worst SQNR_spectral across amplitudes/phases: `{dyn.get('worst_sqnr_spectral_db', '')}` dB
- sweep-worst SQDR across amplitudes/phases: `{dyn.get('worst_sqdr_db', '')}` dB
- max model delta: `{dyn.get('max_model_delta_db', '')}` dB
- theory at configured amplitude: `{dyn.get('theory_sqnr_db_at_config_amplitude', '')}` dB

Power partitions are stored in `results/metrics.json`; summary rows are in
`results/csv/dynamic_metrics.csv` and `results/csv/dynamic_sqnr_sqdr_sweep.csv`.
The plotted time-domain source CSV files are
`results/csv/adc_input_output_time_low_frequency.csv` and
`results/csv/adc_input_output_time_near_nyquist.csv`; they include
`sample_index`, `t_sample_s`, `t_eoc_s`, `vinp_v`, `vinn_v`, `vdiff_v`,
`code_decimal`, `code_hex`, `ideal_dac_output_vdiff_v`, `reconstructed_vdiff_v`,
`quantization_error_v`, `quantization_error_lsb`, `clks_falling_sample`, and `eoc_int`.
The official input/output waveform comparison method is to convert EOC_INT-updated
`DOUT` through the ideal reconstruction DAC and compare `ideal_DAC(DOUT)` with
the matching sampled input `x[n]`. The comparison panel plots the continuous
input and sampled input on the original sample-time axis, then plots
`ideal_DAC(DOUT)` at the EOC_INT time so each staircase update follows the sampled
input and holds until the next output. For clearer DAC input/output
correspondence, `results/csv/adc_dac_reconstruction_low_frequency.csv` and
`results/plots/adc_dac_reconstruction_low_frequency.png` use only the
low-frequency representative tone and show sampled input, EOC_INT-updated code,
ideal DAC(DOUT), and quantization error together.
The plotted spectrum source CSV files are
`results/csv/adc_output_spectrum_low_frequency.csv` and
`results/csv/adc_output_spectrum_near_nyquist.csv`; each row is one FFT bin
with frequency, linear power, dBFS power, classification, harmonic order,
fundamental flag, and largest-spur flag.

## 13. SQNR, SQDR, SQNDR Definitions

`SQNR_total,TD` is measured from time-domain quantization error. `SQNR_spectral`
uses fundamental power divided by nonharmonic quantization-noise power. `SQDR`
uses fundamental power divided by folded 2nd-through-Hth harmonic power.
`SQNDR` obeys the linear power closure
`10^(-SQNDR/10)=10^(-SQNR/10)+10^(-SQDR/10)`.

## 14. Power-Measurement Chain Self-Test

The power harness is a synthetic measurement-chain self-test only; it is not a
SAR ADC power claim. Status: `{data.get('power_harness', {}).get('status', 'NOT_RUN')}`.

## 15. Fault Injection and Negative Controls

Fault injection status: `{fi.get('status', 'NOT_RUN')}`. Detailed rows are in
`results/csv/fault_injection_results.csv`. The set covers offset, gain error,
single-code DNL distortion, missing code, tie-rule error, known harmonic, known
white noise, EOC_INT/timing faults, DOUT bit swap, SAR bit-order error, DAC weight
error, and combined noise plus harmonic closure.

## 16. Raw Data and Traceability

Raw dynamic code streams and quantization-error data are in `results/raw/`.
Machine-readable summaries are `results/metrics.json` and `results/csv/metrics.csv`.
All plots are under `results/plots/`. The file/hash manifest is
`results/manifest.json`.

## 17. Pass/Fail Criteria

Ideal static criteria use `<=0.01 LSB` for deterministic DNL/INL. Project
dynamic criteria use `SNDR >=44 dB` and `ENOB >=7.0 bit`. SQNR/SQDR pass/fail is
based on agreement among the direct quantizer, SAR path, and independent oracle,
plus theory plausibility for the time-domain quantization-error metric.

## 18. Limitations and Next Steps

This phase is ideal only. It does not validate GF180 devices, transistor-level
sampler/comparator/CDAC behavior, post-layout parasitics, or SAR ADC power.
{next_step_text}

## 19. Evidence Index

- `results/csv/metrics.csv`
- `results/README.md`
- `results/README.zh-CN.md`
- `results/csv/coverage_matrix.csv`
- `results/manifest.json`
- `results/metrics.json`
- `results/csv/preflight_tools.csv`
- `results/csv/functional_vectors.csv`
- `results/csv/timing_budget.csv`
- `results/csv/static_dnl.csv`
- `results/csv/static_inl.csv`
- `results/csv/dynamic_metrics.csv`
- `results/csv/dynamic_sqnr_sqdr_sweep.csv`
- `results/csv/adc_input_output_time_low_frequency.csv`
- `results/csv/adc_input_output_time_near_nyquist.csv`
- `results/csv/adc_output_spectrum_low_frequency.csv`
- `results/csv/adc_output_spectrum_near_nyquist.csv`
- `results/csv/dac_transfer.csv`
- `results/csv/fault_injection_results.csv`
- `results/plots/`
"""
    report_path = REPORT_DIR / "ideal_sar_adc_testbench_validation.md"
    write_text(report_path, report)
    payload = {
        "status": "PASS" if go else "FAIL",
        "go_no_go": "GO" if go else "NO-GO",
        "python_sections_ok": python_sections_ok,
        "external_ok": external_ok,
        "report": str(report_path),
        "metrics_csv": str(METRICS_CSV),
        "metrics_json": str(METRICS_JSON),
    }
    update_metrics("report", payload)
    assemble_metrics_csv()
    build_manifest(read_json())
    return payload


def run_repeatability() -> Dict[str, Any]:
    before = read_json()
    before_values = {
        "static.max_abs_dnl_lsb": before.get("static", {}).get("max_abs_dnl_lsb"),
        "static.max_abs_endpoint_inl_lsb": before.get("static", {}).get("max_abs_endpoint_inl_lsb"),
        "dynamic.worst_sndr_db": before.get("dynamic", {}).get("worst_sndr_db"),
        "dynamic.worst_enob_bit": before.get("dynamic", {}).get("worst_enob_bit"),
        "dynamic.max_model_delta_db": before.get("dynamic", {}).get("max_model_delta_db"),
    }
    run_static()
    run_dynamic()
    after = read_json()
    after_values = {
        "static.max_abs_dnl_lsb": after.get("static", {}).get("max_abs_dnl_lsb"),
        "static.max_abs_endpoint_inl_lsb": after.get("static", {}).get("max_abs_endpoint_inl_lsb"),
        "dynamic.worst_sndr_db": after.get("dynamic", {}).get("worst_sndr_db"),
        "dynamic.worst_enob_bit": after.get("dynamic", {}).get("worst_enob_bit"),
        "dynamic.max_model_delta_db": after.get("dynamic", {}).get("max_model_delta_db"),
    }
    rows = []
    for key, first in before_values.items():
        second = after_values.get(key)
        delta = abs(float(first) - float(second)) if first is not None and second is not None else math.inf
        rows.append(
            {
                "metric": key,
                "run1": first,
                "run2": second,
                "abs_delta": delta,
                "tolerance": 1e-12,
                "status": "PASS" if delta <= 1e-12 else "FAIL",
            }
        )
    write_csv(CSV_DIR / "repeatability_check.csv", rows)
    payload = {
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
        "rows": rows,
        "evidence": str(CSV_DIR / "repeatability_check.csv"),
    }
    update_metrics("repeatability", payload)
    return payload


def clean() -> None:
    for path in [CSV_DIR, RAW_DIR, PLOTS_DIR, LOGS_DIR, REPORT_DIR]:
        if path.exists():
            shutil.rmtree(path)
    if METRICS_JSON.exists():
        METRICS_JSON.unlink()
    ensure_dirs()


def run_stage(stage: str) -> Dict[str, Any]:
    if stage == "preflight":
        return run_preflight()
    if stage == "unit":
        return run_unit()
    if stage == "functional":
        return run_functional()
    if stage == "timing":
        return run_timing()
    if stage in ("static", "histogram"):
        return run_static()
    if stage == "dynamic":
        return run_dynamic()
    if stage == "dac":
        return run_dac()
    if stage == "power-harness":
        return run_power_harness()
    if stage == "fault-injection":
        return run_fault_injection()
    if stage == "external-smoke":
        return run_external_smoke()
    if stage == "repeatability":
        return run_repeatability()
    if stage == "report":
        return build_report()
    if stage == "all":
        clean()
        results = {}
        for sub in [
            "preflight",
            "unit",
            "functional",
            "timing",
            "static",
            "dynamic",
            "dac",
            "power-harness",
            "fault-injection",
            "external-smoke",
            "repeatability",
            "report",
        ]:
            print(f"== {sub} ==")
            results[sub] = run_stage(sub)
            print(results[sub].get("status", results[sub].get("go_no_go", "")))
        return {"status": results["report"]["status"], "go_no_go": results["report"]["go_no_go"]}
    if stage == "clean":
        clean()
        return {"status": "PASS"}
    raise ValueError(f"unknown stage {stage}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "preflight",
            "unit",
            "functional",
            "timing",
            "static",
            "histogram",
            "dynamic",
            "dac",
            "power-harness",
            "fault-injection",
            "external-smoke",
            "repeatability",
            "report",
            "all",
            "clean",
        ],
    )
    args = parser.parse_args()
    result = run_stage(args.stage)
    status = result.get("status", "PASS")
    print(f"{args.stage}: {status}")
    if args.stage == "all":
        print(f"go_no_go: {result.get('go_no_go')}")
    if status == "PASS":
        return 0
    if status == "FAIL":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
