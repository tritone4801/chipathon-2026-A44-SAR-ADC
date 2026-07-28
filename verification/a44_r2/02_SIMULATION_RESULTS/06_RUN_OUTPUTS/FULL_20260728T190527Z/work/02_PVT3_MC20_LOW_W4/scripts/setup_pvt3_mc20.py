#!/usr/bin/env python3
"""Freeze the four-device comparator resize PVT3 MC20 campaign before execution."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
CSV = ROOT / "csv"
MANIFESTS = ROOT / "manifests"
RESULTS = ROOT / "results"
BASELINE = Path(
    "/foss/designs/"
    "A44_CMP_IN_A2P25_W_T1P000_PVT3_MC20_LOW_FAST64_SS_W4_FIXED50PS_20260726_R1"
)
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice")

CAMPAIGN = ROOT.name
CANDIDATE_ID = "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587"
METHOD_ID = "FAST64_V2_FIRST_CONVERSION_SEPARATED"
STEADY_METHOD_ID = "FAST64_SS_W4"
BASELINE_COMPARATOR_SHA256 = "e30b2055a880b83176f9389c8b79a13201fdd0e689ca46f3dc3f32b19436f303"
CANDIDATE_COMPARATOR_SHA256 = "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"
RESIZE_WIDTHS_UM = {
    5: (1.56, 8.2524),
    6: (1.56, 8.2524),
    7: (4.67, 16.8587),
    11: (4.67, 16.8587),
}
SEEDS = (44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96)
SEED_GROUPS = {
    "DEEP_TAIL": (44, 26, 65, 21, 36, 2, 12, 182),
    "MIDDLE_TAIL": (86, 80, 128, 189),
    "MARGINAL_DIAGNOSTIC": (116, 190, 45, 188),
    "REFERENCE_CONTROL": (142, 53, 132, 96),
}
PVT = (
    {
        "pvt": "TT_3P3_27C",
        "phase": "P4_PVT_TT_MC20_LOW",
        "model_section": "typical",
        "mim_section": "mimcap_typical",
        "vdd_v": 3.3,
        "temp_c": 27,
        "result_label": "ANALOG_TT_3P3_27C_WITH_FIXED_TT_LOGIC_TIMING",
    },
    {
        "pvt": "SS_3P0_125C",
        "phase": "P5_PVT_SS_MC20_LOW",
        "model_section": "ss",
        "mim_section": "mimcap_ss",
        "vdd_v": 3.0,
        "temp_c": 125,
        "result_label": "ANALOG_SS_3P0_125C_WITH_FIXED_TT_LOGIC_TIMING",
    },
    {
        "pvt": "FF_3P6_M40C",
        "phase": "P6_PVT_FF_MC20_LOW",
        "model_section": "ff",
        "mim_section": "mimcap_ff",
        "vdd_v": 3.6,
        "temp_c": -40,
        "result_label": "ANALOG_FF_3P6_M40C_WITH_FIXED_TT_LOGIC_TIMING",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def seed_group(seed: int) -> str:
    return next(name for name, values in SEED_GROUPS.items() if seed in values)


def job_row(case: dict[str, object], seed: int) -> dict[str, object]:
    return {
        "job_id": f"PVT3_{case['pvt']}_{CANDIDATE_ID}_S{seed:03d}_LOW_W4",
        "phase": case["phase"],
        "role": f"{CANDIDATE_ID}_PVT3_MC20_LOW",
        "category": seed_group(seed),
        "mismatch_seed": seed,
        "noise_mode": "ON",
        "noise_seed": 100_000 + seed,
        "band": "LOW",
        "pvt": case["pvt"],
        "warmup_frames": 4,
        "total_frames": 68,
        "retained_frame_start": 4,
        "retained_frame_end": 67,
        "nfft": 64,
        "bin": 7,
        "fin_hz": 218750.0,
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "required": True,
        "state": "PENDING",
        "returncode": "",
        "elapsed_s": "",
        "overall_status": "",
        "completed_utc": "",
    }


def smoke_row(case: dict[str, object], seed: int | None) -> dict[str, object]:
    nominal = seed is None
    token = "NOMINAL_OFF" if nominal else f"S{seed:03d}_ON"
    return {
        "job_id": f"SMOKE_{case['pvt']}_{token}_LOW_W4",
        "phase": "P1_SMOKE",
        "role": "PVT3_BINDING_SMOKE",
        "category": "NOMINAL_NOISE_OFF" if nominal else seed_group(int(seed)),
        "mismatch_seed": "" if nominal else seed,
        "noise_mode": "OFF" if nominal else "ON",
        "noise_seed": "" if nominal else 100_000 + int(seed),
        "band": "LOW",
        "pvt": case["pvt"],
        "warmup_frames": 4,
        "total_frames": 68,
        "retained_frame_start": 4,
        "retained_frame_end": 67,
        "nfft": 64,
        "bin": 7,
        "fin_hz": 218750.0,
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "required": True,
        "state": "PENDING",
        "returncode": "",
        "elapsed_s": "",
        "overall_status": "",
        "completed_utc": "",
    }


def copy_reference_subset() -> dict[str, object]:
    source = BASELINE / "csv" / "pvt3_mc20_master.csv"
    with source.open(newline="", encoding="utf-8") as stream:
        rows = [
            row
            for row in csv.DictReader(stream)
            if int(row["mismatch_seed"]) in SEEDS
        ]
    pvt_order = {case["pvt"]: index for index, case in enumerate(PVT)}
    rows.sort(
        key=lambda row: (
            pvt_order[row["pvt"]],
            SEEDS.index(int(row["mismatch_seed"])),
        )
    )
    destination = ROOT / "references" / "baseline_t1p000_pvt3_mc20_reference.csv"
    write_csv(destination, rows)
    return {
        "source": str(source),
        "source_sha256": sha256_file(source),
        "destination": str(destination.relative_to(ROOT)),
        "destination_sha256": sha256_file(destination),
        "row_count": len(rows),
    }


def comparator_resize_audit(candidate_text: str) -> dict[str, object]:
    baseline_path = BASELINE / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    baseline_text = baseline_path.read_text(encoding="utf-8")
    expected = baseline_text
    replacements: list[dict[str, object]] = []
    for device, (old_width, new_width) in RESIZE_WIDTHS_UM.items():
        pattern = rf"(?m)^(XM{device}\b.*?\bW=){old_width:g}u\b"
        expected, count = re.subn(pattern, rf"\g<1>{new_width:g}u", expected, count=1)
        replacements.append(
            {
                "device": f"XM{device}",
                "old_width_um": old_width,
                "new_width_um": new_width,
                "replacement_count": count,
            }
        )
    return {
        "baseline_path": str(baseline_path),
        "baseline_sha256": sha256_file(baseline_path),
        "candidate_sha256": sha256_file(
            ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
        ),
        "replacements": replacements,
        "exact_four_width_changes_only": expected == candidate_text,
        "pass": (
            sha256_file(baseline_path) == BASELINE_COMPARATOR_SHA256
            and all(row["replacement_count"] == 1 for row in replacements)
            and expected == candidate_text
        ),
    }


def unchanged_source_audit() -> dict[str, object]:
    paths = (
        "scripts/dynamic_analysis.py",
        "scripts/fast64_v2_common.py",
        "scripts/run_fast64_v2.py",
        "scripts/sar_campaign_common.py",
        "scripts/sar_event_noise.py",
        "netlists/core/subckts/CDAC_native_extracted.subckt.spice",
        "netlists/core/subckts/SWITCH_BOOT_SP_native_extracted.subckt.spice",
        "models/SAR_LOGIC_BEH_TT_3P3_27C.so",
        "models/no_r6_equivalent_loads.inc",
        "config/frozen_dynamic_config.yaml",
        "config/timing_tt_3p3_27c.json",
        "config/noise_model.yaml",
        "config/plot_contract.json",
        "config/plot_style.yaml",
        "config/ngspice_userinit/.spiceinit",
        "csv/cdac_mismatch_weights.csv",
    )
    records = []
    for relative in paths:
        baseline_path = BASELINE / relative
        candidate_path = ROOT / relative
        baseline_hash = sha256_file(baseline_path)
        candidate_hash = sha256_file(candidate_path)
        records.append(
            {
                "relative_path": relative,
                "baseline_sha256": baseline_hash,
                "candidate_sha256": candidate_hash,
                "match": baseline_hash == candidate_hash,
            }
        )
    return {
        "baseline_package": str(BASELINE),
        "records": records,
        "pass": all(row["match"] for row in records),
    }


def pdk_audit() -> dict[str, object]:
    text = PDK.read_text(encoding="utf-8", errors="replace")
    checks = {}
    for section in ("typical", "ss", "ff"):
        match = re.search(
            rf"(?ims)^\s*\.lib\s+{section}\s*$"
            rf"(.*?)^\s*\.endl(?:\s+{section})?\s*$",
            text,
        )
        body = "" if match is None else match.group(1)
        checks[section] = {
            "section_found": match is not None,
            "includes_fets_mm": bool(re.search(r"(?im)^\s*\.lib\s+['\"]?sm141064\.ngspice['\"]?\s+fets_mm\s*$", body)),
        }
    return {
        "pdk": str(PDK),
        "pdk_sha256": sha256_file(PDK),
        "corner_checks": checks,
        "pass": all(
            row["section_found"] and row["includes_fets_mm"]
            for row in checks.values()
        ),
    }


def input_manifest() -> list[dict[str, object]]:
    paths = (
        "scripts/dynamic_analysis.py",
        "scripts/fast64_v2_common.py",
        "scripts/run_fast64_v2.py",
        "scripts/sar_campaign_common.py",
        "scripts/sar_event_noise.py",
        "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice",
        "netlists/core/subckts/CDAC_native_extracted.subckt.spice",
        "netlists/core/subckts/SWITCH_BOOT_SP_native_extracted.subckt.spice",
        "models/SAR_LOGIC_BEH_TT_3P3_27C.so",
        "models/no_r6_equivalent_loads.inc",
        "config/timing_tt_3p3_27c.json",
        "config/noise_model.yaml",
        "config/plot_contract.json",
        "config/plot_style.yaml",
        "config/ngspice_userinit/.spiceinit",
        "csv/cdac_mismatch_weights.csv",
    )
    return [
        {
            "relative_path": relative,
            "bytes": (ROOT / relative).stat().st_size,
            "sha256": sha256_file(ROOT / relative),
        }
        for relative in paths
    ]


def main() -> int:
    for directory in (CONFIG, CSV, MANIFESTS, RESULTS, ROOT / "references"):
        directory.mkdir(parents=True, exist_ok=True)

    comparator = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    comparator_text = comparator.read_text(encoding="utf-8")
    resize_audit = comparator_resize_audit(comparator_text)
    unchanged_audit = unchanged_source_audit()
    pin_order_ok = (
        ".subckt Comparator_StrongARM CLK DCMPP VINP DCMPN VINN VDD GND"
        in comparator_text
    )
    width_ok = all(
        re.search(rf"(?im)^XM{device}\b.*\bW=3\.51u\b", comparator_text)
        for device in (3, 4)
    )
    comparator_hash = sha256_file(comparator)
    logic_hash = sha256_file(ROOT / "models/SAR_LOGIC_BEH_TT_3P3_27C.so")
    pdk = pdk_audit()
    reference = copy_reference_subset()
    rng_search_path = RESULTS / "rng_burn_search.json"
    rng_search = (
        json.loads(rng_search_path.read_text(encoding="utf-8"))
        if rng_search_path.is_file()
        else {}
    )
    legacy_rng_alignment_ok = rng_search.get("matches") == [19]

    formal = [job_row(case, seed) for case in PVT for seed in SEEDS]
    smoke = [smoke_row(case, seed) for case in PVT for seed in (None, 44, 96)]
    write_csv(MANIFESTS / "job_matrix.csv", formal)
    write_csv(MANIFESTS / "smoke_job_matrix.csv", smoke)
    write_csv(MANIFESTS / "frozen_input_manifest.csv", input_manifest())

    contract = {
        "campaign": CAMPAIGN,
        "created_utc": utc_now(),
        "status": "FROZEN_BEFORE_EXECUTION",
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "baseline_candidate_id": "CMP_IN_A2P25_W_T1P000",
            "baseline_comparator_sha256": BASELINE_COMPARATOR_SHA256,
            "resized_devices": ["XM5", "XM6", "XM7", "XM11"],
            "xm5_xm6_width_um": 8.2524,
            "xm7_xm11_width_um": 16.8587,
            "xm3_xm4_width_um": 3.51,
            "xm1_tail_width_um": 1.56,
            "comparator_sha256": comparator_hash,
            "logic_so_sha256": logic_hash,
            "pin_order": "CLK DCMPP VINP DCMPN VINN VDD GND",
        },
        "method": {
            "method_id": METHOD_ID,
            "steady_state_method_id": STEADY_METHOD_ID,
            "band": "LOW",
            "sample_rate_hz": 2_000_000.0,
            "fin_hz": 218_750.0,
            "coherent_bin": 7,
            "input_vpp_diff": 3.0,
            "input_phase_rad": 0.7853981633974483,
            "total_frames": 68,
            "frame0_independent_gate": True,
            "startup_diagnostic_frames": [1, 3],
            "retained_frames": [4, 67],
            "nfft": 64,
            "window": "rectangular",
            "maxstep_ps": 50,
            "solver_profile": "ROBUST_GEAR",
            "noise_seed_rule": "100000_plus_mismatch_seed",
        },
        "gates": {
            "protocol_clean": True,
            "clipping_count_max": 0,
            "sndr_min_db": 46.91,
            "enob_raw_min_bit": 7.50,
            "snr_budget_min_db": 48.14,
        },
        "population": {
            "selected_diagnostic_sample_not_yield": True,
            "seeds": list(SEEDS),
            "seed_groups": {key: list(value) for key, value in SEED_GROUPS.items()},
            "corner_count": 3,
            "formal_record_count": 60,
            "all_frame_code_rows": 4080,
            "retained_fft_code_rows": 3840,
        },
        "pvt": list(PVT),
        "process_mismatch_binding": {
            "sw_stat_global": 0,
            "sw_stat_mismatch": 1,
            "model_binding": "DETERMINISTIC_PROCESS_CORNER_PLUS_FETS_MM_LOCAL_MISMATCH",
            "statistical_section_for_formal_jobs": False,
            "legacy_statistical_global_rng_draws_consumed": 19,
            "legacy_seed_mapping_probe": "results/rng_burn_search.json",
            "paired_delta_requires_pairing_audit_pass": True,
        },
        "resource_contract": {
            "workers_max": 4,
            "num_threads_per_ngspice": 4,
            "total_ngspice_threads_max": 16,
            "performance_early_stop": False,
        },
        "style": {
            "percentile_method": "LINEAR_TYPE7",
            "ecdf": "SORTED_OBSERVATIONS_I_OVER_N_STEP",
            "spectrum": "DISCRETE_FFT_BINS_NO_SMOOTHING",
            "no_tail_clipping": True,
            "png_dpi": 300,
            "vector_format": "PDF",
        },
        "reference": reference,
        "non_claims": [
            "Selected MC20 records are not a statistical yield population.",
            "PVT MC20 is a paired diagnostic comparison against the fixed T1P000 PVT3 MC20 baseline.",
            "PVT MC20 does not replace or extend an MC200 yield population.",
            "No promotion, layout, PEX, silicon, production-yield, or signoff claim is made.",
        ],
    }
    write_json(CONFIG / "pvt3_mc20_contract.json", contract)

    setup_checks = {
        "candidate_comparator_hash": comparator_hash
        == CANDIDATE_COMPARATOR_SHA256,
        "baseline_comparator_hash": resize_audit["baseline_sha256"]
        == BASELINE_COMPARATOR_SHA256,
        "exact_four_resize_changes_only": resize_audit["pass"],
        "unchanged_dynamic_sources_match_baseline": unchanged_audit["pass"],
        "logic_so_hash": logic_hash
        == "e6f8341531b50a0d59e1f2f2be60f501a43d84e887b7e6226f5cd4d9c431ea0c",
        "pin_order": pin_order_ok,
        "xm3_xm4_width": width_ok,
        "pdk_corner_sections_include_local_mismatch": pdk["pass"],
        "legacy_seed_mapping_19_draw_alignment": legacy_rng_alignment_ok,
        "formal_job_count_60": len(formal) == 60,
        "smoke_job_count_9": len(smoke) == 9,
        "reference_row_count_60": reference["row_count"] == 60,
        "seed_rule": all(int(row["noise_seed"]) == 100_000 + int(row["mismatch_seed"]) for row in formal),
        "fixed_w4_50ps": all(
            int(row["warmup_frames"]) == 4
            and int(row["total_frames"]) == 68
            and int(row["maxstep_ps"]) == 50
            for row in formal
        ),
    }
    write_json(
        RESULTS / "pvt_binding_static_audit.json",
        {
            "completed_utc": utc_now(),
            "pdk": pdk,
            "comparator_resize_audit": resize_audit,
            "unchanged_source_audit": unchanged_audit,
            "model_include_implementation": "scripts/sar_campaign_common.py",
            "checks": setup_checks,
            "pass": all(setup_checks.values()),
        },
    )
    write_json(
        RESULTS / "setup_audit.json",
        {
            "campaign": CAMPAIGN,
            "completed_utc": utc_now(),
            "checks": setup_checks,
            "pass": all(setup_checks.values()),
        },
    )
    print(json.dumps({"pass": all(setup_checks.values()), "checks": setup_checks}, indent=2))
    return 0 if all(setup_checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
