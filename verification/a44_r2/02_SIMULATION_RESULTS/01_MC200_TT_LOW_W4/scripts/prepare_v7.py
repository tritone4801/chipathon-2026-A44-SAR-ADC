#!/usr/bin/env python3
"""Freeze V7 configuration, deterministic seeds, bindings, and dependency hashes."""

import csv
import json
import subprocess
from pathlib import Path

import yaml

from sar_campaign_common import ROOT
from v7_common import (
    BANDS,
    CAMPAIGN_ID,
    CONFIG_DIR,
    CSV_DIR,
    EVIDENCE_CLASS,
    MANIFEST_DIR,
    NFFT,
    PHASE_RAD,
    REQUIRED_DIES,
    RESULT_DIR,
    canonical_json_hash,
    ensure_v7_directories,
    mismatch_checksums,
    noise_draw_checksum,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


PRODUCTION_ROOT = Path("/foss/designs/manual_goal/analog/SAR_CURRENT")
PDK_ROOT = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice")
NGSPICE = Path("/foss/tools/bin/ngspice")


FROZEN_CONFIG = {
    "campaign": {
        "id": CAMPAIGN_ID,
        "dynamic_only": True,
        "performance_early_stop": False,
        "formal_categories": ["D3_ONLY"],
        "dynamic_method": "FAST64_ONLY",
        "primary_lane": "TT_TIMED_BEHAVIORAL_SAR_NO_R6",
        "evidence_class": EVIDENCE_CLASS,
    },
    "system": {
        "resolution_bit": 8,
        "sample_rate_hz": 2_000_000,
        "frame_period_ns": 500,
        "startup_frames": 0,
        "dout_aperture_ns": 480,
        "vcm_v": 1.65,
        "vrefp_v": 2.50,
        "vrefn_v": 0.80,
        "nominal_full_scale_vpp_diff": 3.4,
        "input_vpp_diff": 3.0,
        "input_phase_rad": float(PHASE_RAD),
    },
    "numerical": {
        "formal_maxstep_ns_if_cache_valid": 0.10,
        "strict_maxstep_ns": 0.05,
        "rescan_frame": False,
        "rescan_startup": False,
        "rescan_aperture": False,
        "rescan_phase": False,
        "rescan_fft_length": False,
    },
    "fast64": {
        "nfft": NFFT,
        "window": "rectangular",
        "bands": BANDS,
        "harmonics": [2, 3, 4, 5],
        "require_parseval_check": True,
    },
    "noise_model": {
        "sample_sigma_v_rms_diff": 6.4681023032e-5,
        "comparator_sigma_v_rms_diff": 1.5e-3,
        "sample_draws_per_frame": 1,
        "comparator_draws_per_decision": 1,
        "qualification_required": True,
        "claim": "T2_TARGET_CALIBRATED_EVENT_NOISE_NOT_NATIVE_MOS_TRANSIENT_NOISE",
    },
    "matrix": {
        "D3": {
            "category": "NOISE_PLUS_MISMATCH_MC200",
            "pvt": "TT_3P3_27C",
            "mismatch_seeds": REQUIRED_DIES,
            "noise_seed_rule": "100000_plus_mismatch_seed",
            "records_per_die": 2,
        }
    },
    "metrics": {
        "mandatory": ["SNR", "SNDR", "ENOB_RAW", "SFDR", "THD", "HD2", "HD3"],
        "snr_budget_target_db": 48.14,
        "sndr_hard_min_db": 46.91,
        "enob_raw_hard_min_bit": 7.50,
        "sndr_preferred_nominal_db": 47.75,
        "enob_raw_preferred_nominal_bit": 7.64,
    },
    "acceptance": {
        "D3_required_valid_dies": 200,
        "D3_minimum_pass_count": 190,
        "D3_minimum_observed_pass_rate": 0.95,
        "require_both_bands": True,
        "require_clean_protocol_flags": True,
        "snr_budget_is_separate_gate": True,
    },
    "execution": {
        "session_mode": "SEPARATE_PROCESS_FALLBACK",
        "solver_profile": "ROBUST_GEAR",
        "one_die_per_scheduler_task": True,
        "destroy_vectors_after_each_record": True,
        "infrastructure_retry_max": 1,
        "performance_retry": False,
    },
    "memory_32gb": {
        "physical_ram_gb_nominal": 32,
        "ngspice_token_budget_gb_nominal": 22,
        "token_quantum_gb": 0.5,
        "token_rss_margin": 1.25,
        "memavailable_pause_gb": 5,
        "swap_pause_mb": 512,
        "threads_per_process": 1,
    },
    "completion": {
        "no_failed_job_dropping": True,
        "unresolved_required_job_means_blocked": True,
    },
}


def production_source_audit():
    source_manifest = PRODUCTION_ROOT / "manifests" / "package_manifest_sha256.csv"
    rows = []
    for expected in read_csv(source_manifest):
        path = PRODUCTION_ROOT / expected["relative_path"]
        actual_hash = sha256_file(path) if path.is_file() else ""
        rows.append(
            {
                "relative_path": expected["relative_path"],
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": path.stat().st_size if path.is_file() else "",
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_hash,
                "status": (
                    "MATCH"
                    if path.is_file()
                    and path.stat().st_size == int(expected["size_bytes"])
                    and actual_hash == expected["sha256"]
                    else "MISMATCH"
                ),
            }
        )
    write_csv_atomic(MANIFEST_DIR / "production_source_integrity.csv", rows)
    return {
        "manifest_path": str(source_manifest),
        "manifest_sha256": sha256_file(source_manifest),
        "declared_files": len(rows),
        "matching_files": sum(row["status"] == "MATCH" for row in rows),
        "all_match": all(row["status"] == "MATCH" for row in rows),
    }


def dependency_hashes(source_audit):
    dependencies = []

    def add(role, path):
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        dependencies.append(
            {
                "role": role,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    add(
        "production_analog_package_manifest",
        PRODUCTION_ROOT / "manifests" / "package_manifest_sha256.csv",
    )
    for path in (
        ROOT / "netlists" / "SAR_ADC_ANALOG_CORE_TT_BEH_NO_R6.spice",
        ROOT / "netlists" / "core" / "subckts" / "SWITCH_BOOT_SP_native_extracted.subckt.spice",
        ROOT / "netlists" / "core" / "subckts" / "CDAC_native_extracted.subckt.spice",
        ROOT
        / "netlists"
        / "core"
        / "subckts"
        / "Comparator_StrongARM_extracted.subckt.spice",
    ):
        add("campaign_analog_netlist", path)
    for path in (
        PDK_ROOT / "design.ngspice",
        PDK_ROOT / "sm141064.ngspice",
        PDK_ROOT / "sm141064_mim.ngspice",
    ):
        add("pdk_model", path)
    for path in (
        ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.v",
        ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.so",
    ):
        add("behavioral_sar_controller", path)
    add("noise_adapter", ROOT / "scripts" / "sar_event_noise.py")
    add("testbench_template_and_solver", ROOT / "scripts" / "sar_campaign_common.py")
    add("fft_analyzer", ROOT / "scripts" / "dynamic_analysis.py")
    add("v7_seed_and_io_contract", ROOT / "scripts" / "v7_common.py")
    add("v7_runner", ROOT / "scripts" / "run_v7.py")
    add("timing_model", ROOT / "config" / "timing_tt_3p3_27c.json")
    add("mismatch_model", CSV_DIR / "cdac_mismatch_weights.csv")
    add("noise_model_config", ROOT / "config" / "noise_model.yaml")
    add(
        "solver_profile_prior_equivalence",
        ROOT
        / "source_snapshot"
        / "prior_model_audits"
        / "solver_profile_equivalence.md",
    )
    add(
        "measurement_plan",
        ROOT
        / "references"
        / "v7_inputs"
        / "A44_CODEX_FAST64_D3_ONLY_32GB_ONE_DAY_PLAN_V7.md",
    )
    ngspice_version = subprocess.run(
        [str(NGSPICE), "-v"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    version_text = (ngspice_version.stdout + ngspice_version.stderr).strip()
    key_payload = {
        "dependencies": dependencies,
        "ngspice_version": version_text,
        "solver_profile": "ROBUST_GEAR_FIXED",
        "source_manifest_sha256": source_audit["manifest_sha256"],
    }
    return {
        **key_payload,
        "cache_key_sha256": canonical_json_hash(key_payload),
        "source_integrity": source_audit,
    }


def seed_manifests():
    weights_path = CSV_DIR / "cdac_mismatch_weights.csv"
    weights_rows = read_csv(weights_path)
    mismatch = mismatch_checksums(weights_rows)
    if sorted(mismatch) != list(range(1, REQUIRED_DIES + 1)):
        raise RuntimeError("mismatch model does not contain exactly seeds 1..200")
    mismatch_rows = [
        {
            "mismatch_seed": seed,
            "virtual_die": seed,
            "branch": "CLAIM_BASELINE_3SIGMA_CONVERSION",
            "parameter_rows": sum(
                row["branch"] == "CLAIM_BASELINE_3SIGMA_CONVERSION"
                and int(row["mismatch_seed"]) == seed
                for row in weights_rows
            ),
            "mismatch_checksum_sha256": mismatch[seed],
            "status": "FROZEN",
        }
        for seed in range(1, REQUIRED_DIES + 1)
    ]
    noise_rows = []
    for seed in range(1, REQUIRED_DIES + 1):
        noise_seed = 100_000 + seed
        noise_rows.append(
            {
                "mismatch_seed": seed,
                "noise_seed": noise_seed,
                "sample_draw_count": NFFT,
                "comparator_draw_count": NFFT * 8,
                "noise_draw_checksum_sha256": noise_draw_checksum(noise_seed),
                "same_sequence_low_and_near": True,
                "status": "FROZEN",
            }
        )
    job_rows = []
    for seed in range(1, REQUIRED_DIES + 1):
        for band, band_config in BANDS.items():
            job_rows.append(
                {
                    "job_id": f"D3_S{seed:03d}_{band}",
                    "category": "D3_NOISE_PLUS_MISMATCH_MC200",
                    "pvt": "TT_3P3_27C",
                    "mismatch_seed": seed,
                    "noise_seed": 100_000 + seed,
                    "band": band,
                    "nfft": NFFT,
                    "bin": band_config["bin"],
                    "fin_hz": band_config["fin_hz"],
                    "required": True,
                    "state": "PENDING",
                    "attempt_count": 0,
                }
            )
    write_csv_atomic(MANIFEST_DIR / "mismatch_seed_manifest.csv", mismatch_rows)
    write_csv_atomic(MANIFEST_DIR / "noise_seed_manifest.csv", noise_rows)
    write_csv_atomic(MANIFEST_DIR / "job_matrix.csv", job_rows)


def qualification_state(dependencies):
    noise_config = yaml.safe_load(
        (ROOT / "config" / "noise_model.yaml").read_text(encoding="ascii")
    )
    noise_qualified = all(
        (
            noise_config.get("status") == "PASS_CALIBRATED_EQUIVALENT_NOISE",
            bool(noise_config.get("event_model_enabled_for_signoff")),
            abs(
                float(
                    noise_config["sample_hold_noise"]["signoff_sigma_rms_diff_v"]
                )
                - 6.4681023032e-5
            )
            <= 1e-16,
            abs(
                float(
                    noise_config["comparator_decision_noise"]["sigma_rms_diff_v"]
                )
                - 1.5e-3
            )
            <= 1e-16,
        )
    )
    return {
        "campaign_id": CAMPAIGN_ID,
        "cache_key_sha256": dependencies["cache_key_sha256"],
        "cache_reused": False,
        "fixed_pilot_required": True,
        "fixed_pilot_complete": False,
        "numerical_qualification_pass": False,
        "selected_formal_maxstep_ps": None,
        "noise_model_qualified": noise_qualified,
        "noise_model_class": "T2_TARGET_CALIBRATED_EVENT_NOISE",
        "noise_model_native_mos_transient_noise_claim": False,
        "prior_phase_g_system_gate_status": "FAIL",
        "prior_phase_g_note": (
            "Retained explicitly; V7 qualification is limited to the frozen "
            "target-calibrated event-model enablement and remains model-conditional."
        ),
        "parsed_ngspice_session_implemented": False,
        "session_execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "session_equivalence_complete": False,
        "resource_admission_complete": False,
        "resource_admission_pass": False,
    }


def main():
    ensure_v7_directories()
    (CONFIG_DIR / "frozen_dynamic_config.yaml").write_text(
        yaml.safe_dump(FROZEN_CONFIG, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    seed_manifests()
    source_audit = production_source_audit()
    dependencies = dependency_hashes(source_audit)
    write_json_atomic(CONFIG_DIR / "dependency_hashes.json", dependencies)
    write_json_atomic(
        CONFIG_DIR / "qualification_cache.json", qualification_state(dependencies)
    )
    summary = {
        "campaign_id": CAMPAIGN_ID,
        "source_integrity": source_audit,
        "dependency_count": len(dependencies["dependencies"]),
        "cache_key_sha256": dependencies["cache_key_sha256"],
        "mismatch_seeds": REQUIRED_DIES,
        "noise_seeds": REQUIRED_DIES,
        "formal_jobs": REQUIRED_DIES * len(BANDS),
    }
    write_json_atomic(RESULT_DIR / "preparation_audit.json", summary)
    if not source_audit["all_match"]:
        raise SystemExit("production source integrity mismatch")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
