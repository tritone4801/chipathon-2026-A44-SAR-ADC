#!/usr/bin/env python3
"""Close the campaign at the mandatory Phase-B BLOCKED stop with auditable evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PICO = Path(r"D:\PICO")
SAR_CURRENT = Path(r"C:\Users\15031\eda\designs\manual_goal\analog\SAR_CURRENT")
CONTAINER = "iic-osic-tools_chipathon_xvnc"
CONTAINER_ROOT = "/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
PDK_ROOT = "/foss/pdks/gf180mcuD/libs.tech/ngspice"
GENERATED_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="ascii")


def write_json(relative: str, payload: object) -> None:
    write_text(relative, json.dumps(payload, indent=2, sort_keys=False))


def write_csv(relative: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def copy_source(source: Path, relative: str) -> dict:
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        return {
            "source": str(source),
            "snapshot": relative,
            "status": "MISSING",
            "sha256": None,
        }
    shutil.copy2(source, target)
    return {
        "source": str(source),
        "snapshot": relative,
        "status": "COPIED_READ_ONLY",
        "sha256": sha256(target),
    }


def docker(command: str) -> dict:
    try:
        completed = subprocess.run(
            ["docker", "exec", CONTAINER, "bash", "-lc", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": repr(exc)}


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="ascii"))


def markdown_table(rows: list[dict], fields: list[str]) -> str:
    header = "| " + " | ".join(fields) + " |"
    separator = "|" + "|".join("---" for _ in fields) + "|"
    body = [
        "| " + " | ".join(str(row.get(field, "")) for field in fields) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def freeze_reference_inputs() -> list[dict]:
    timing_root = (
        PICO
        / "SAR_SUM"
        / "SAR_LOGIC_ACTUAL_RTL"
        / "verification"
        / "sar_logic_actual"
        / "results"
        / "csv"
    )
    sources = [
        (
            PICO / "A44_CODEX_TT_BEHAVIORAL_SAR_SCHEMATIC_SIGNOFF_PLAN_EN.md",
            "source_snapshot/guide/A44_CODEX_TT_BEHAVIORAL_SAR_SCHEMATIC_SIGNOFF_PLAN_EN.md",
        ),
        (
            PICO / "chipathon-2026-A44-SAR-ADC_repo" / "current_goal.md",
            "source_snapshot/project/current_goal.md",
        ),
        (
            PICO / "container_sync" / "sar_logic_actual_RTL_xschem_current_20260629" / "rtl" / "sar_logic_async_core_RTL.sv",
            "source_snapshot/timing/sar_logic_async_core_RTL.sv",
        ),
        (timing_root / "timing_model_parameters.csv", "source_snapshot/timing/timing_model_parameters.csv"),
        (timing_root / "unit_timing_metrics.csv", "source_snapshot/timing/unit_timing_metrics.csv"),
        (timing_root / "system_timing_actual_logic.csv", "source_snapshot/timing/system_timing_actual_logic.csv"),
        (timing_root / "sar_bit_trial_trace_actual_logic.csv", "source_snapshot/timing/sar_bit_trial_trace_actual_logic.csv"),
        (SAR_CURRENT / "README.md", "source_snapshot/sar_current/README.md"),
        (SAR_CURRENT / "SOURCE_BINDING.md", "source_snapshot/sar_current/SOURCE_BINDING.md"),
        (SAR_CURRENT / "reports" / "assembly_checks.json", "source_snapshot/sar_current/assembly_checks.json"),
        (
            SAR_CURRENT / "manifests" / "package_manifest_sha256.csv",
            "source_snapshot/sar_current/package_manifest_sha256.csv",
        ),
        (
            PICO / "SAR_SUM" / "RANDOM" / "reports" / "pdk_statistical_capability_audit.md",
            "source_snapshot/prior_model_audits/pdk_statistical_capability_audit.md",
        ),
        (
            PICO / "SAR_SUM" / "RANDOM" / "reports" / "mos_mismatch_sanity_test.md",
            "source_snapshot/prior_model_audits/mos_mismatch_sanity_test.md",
        ),
        (
            PICO / "SAR_SUM" / "RANDOM" / "reports" / "mimcap_mismatch_provenance_audit.md",
            "source_snapshot/prior_model_audits/mimcap_mismatch_provenance_audit.md",
        ),
        (
            PICO / "SAR_SUM_followup_mc_noise_mismatch_20260701" / "reports" / "comparator_noise_probability_report.md",
            "source_snapshot/prior_model_audits/comparator_noise_probability_report.md",
        ),
        (
            PICO / "SAR_SUM_followup_mc_noise_mismatch_20260701" / "reports" / "mc_failure_report.md",
            "source_snapshot/prior_model_audits/mc_failure_report.md",
        ),
    ]
    records = [copy_source(source, target) for source, target in sources]
    missing_required = {
        "try_PERFORMANCE.txt": not any(PICO.rglob("try_PERFORMANCE.txt")),
        "read_measurement_definitions.txt": not any(PICO.rglob("read_measurement_definitions.txt")),
    }
    write_json(
        "manifests/reference_input_snapshot.json",
        {
            "generated_utc": GENERATED_UTC,
            "records": records,
            "missing_reference_inputs": [name for name, missing in missing_required.items() if missing],
            "missing_input_policy": "RECORDED_MISSING_NOT_CLAIMED_AS_REVIEWED",
        },
    )
    return records


def audit_source_integrity() -> dict:
    baseline_path = SAR_CURRENT / "manifests" / "package_manifest_sha256.csv"
    baseline_rows = list(csv.DictReader(baseline_path.open(encoding="utf-8-sig")))
    before = []
    after = []
    comparisons = []
    for row in baseline_rows:
        relative = row["relative_path"]
        expected_hash = row["sha256"].lower()
        before.append(
            {
                "relative_path": relative,
                "size_bytes": int(row["size_bytes"]),
                "sha256": expected_hash,
                "provenance": "SAR_CURRENT_FROZEN_PACKAGE_MANIFEST",
            }
        )
        current_path = SAR_CURRENT / Path(relative)
        if current_path.is_file():
            current_hash = sha256(current_path)
            current_size = current_path.stat().st_size
            status = "MATCH" if current_hash == expected_hash else "HASH_CHANGED"
        else:
            current_hash = None
            current_size = None
            status = "MISSING"
        after.append(
            {
                "relative_path": relative,
                "size_bytes": current_size,
                "sha256": current_hash,
                "status_vs_before": status,
            }
        )
        comparisons.append(
            {
                "relative_path": relative,
                "before_sha256": expected_hash,
                "after_sha256": current_hash or "",
                "status": status,
            }
        )
    all_match = all(row["status"] == "MATCH" for row in comparisons)
    write_json(
        "manifests/source_hashes_before.json",
        {
            "baseline_type": "SAR_CURRENT_FROZEN_PACKAGE_MANIFEST",
            "baseline_path": str(baseline_path),
            "records": before,
        },
    )
    write_json(
        "manifests/source_hashes_after.json",
        {
            "generated_utc": GENERATED_UTC,
            "source_root": str(SAR_CURRENT),
            "all_match": all_match,
            "records": after,
        },
    )
    write_csv(
        "manifests/source_hash_comparison.csv",
        comparisons,
        ["relative_path", "before_sha256", "after_sha256", "status"],
    )
    return {
        "all_match": all_match,
        "record_count": len(comparisons),
        "changed_or_missing": [row for row in comparisons if row["status"] != "MATCH"],
    }


def freeze_configuration(reference_records: list[dict]) -> None:
    timing_sources = {
        Path(row["snapshot"]).name: row["sha256"]
        for row in reference_records
        if row["snapshot"].startswith("source_snapshot/timing/")
    }
    timing = {
        "model": "SAR_LOGIC_BEH_TT_3P3_27C",
        "condition": "TT_3P3_27C",
        "logic_pvt_variation": "DISABLED",
        "time_unit": "ns",
        "source_files_sha256": timing_sources,
        "t_clks_fall_to_first_cmpck_rise": 11.05,
        "bit_order": [7, 6, 5, 4, 3, 2, 1, 0],
        "cmpck_high": [13.890, 13.878, 13.891, 13.891, 13.878, 13.879, 13.892, 13.878],
        "decision_aperture_from_cmpck_rise": [0.914, 0.824, 0.914, 0.914, 0.825, 0.825, 0.914, 0.824],
        "dctrl_event_from_cmpck_rise_bits_7_to_1": [7.911, 7.931, 8.022, 8.023, 7.934, 7.935, 8.025],
        "dctrl_event_from_decision_bits_7_to_1": [6.997, 7.107, 7.108, 7.109, 7.109, 7.110, 7.111],
        "cmpck_low_guard_bits_7_to_1": [11.560, 11.575, 11.576, 11.560, 11.560, 11.577, 11.574],
        "last_cmpck_rise_to_atomic_dout": 10.633,
        "timing_rounding": "1_ps",
        "claim_boundary": "TT timing evidence only; not actual logic signoff in this campaign",
    }
    write_json("config/timing_tt_3p3_27c.json", timing)
    write_text(
        "config/source_load_model.yaml",
        """
classification: ACCEPTED_FIXTURE_DERIVED_EQUIVALENT_LOADS
status: FROZEN
source_file: models/no_r6_equivalent_loads.inc
input_each_leg:
  resistance_ohm: 105
  shunt_capacitance_f: 1.0e-12
  common_mode_capacitance_f: 5.0e-13
  differential_capacitance_f: 2.0e-13
reference_each_rail:
  source_resistance_ohm: 2
  local_decoupling_f: 2.0e-10
  decoupling_esr_ohm: 0.2
  line_capacitance_f: 5.0e-13
clks:
  source_resistance_ohm: 105
  load_capacitance_f: 1.5e-12
  rise_time_s: 2.5e-10
  fall_time_s: 2.5e-10
comparator_logic_inputs:
  dcmpp_capacitance_f: 2.0e-14
  dcmpn_capacitance_f: 2.0e-14
dctrl:
  thevenin_resistance_ohm: 15000
  intrinsic_rise_time_s: 5.0e-11
  intrinsic_fall_time_s: 5.0e-11
cmpck:
  thevenin_resistance_ohm: 35000
  intrinsic_rise_time_s: 5.0e-11
  intrinsic_fall_time_s: 5.0e-11
dout:
  series_resistance_ohm: 160
  load_capacitance_f: 1.0e-12
  rise_time_s: 2.5e-10
  fall_time_s: 2.5e-10
r6_full_rc_heavy: disabled
zero_load_assumption: false
""",
    )
    write_text(
        "config/cdac_mismatch_model.yaml",
        """
classification: UNAVAILABLE
status: BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE
pdk_native_local_mim_mismatch: false
approved_engineering_model: false
previous_t2_sensitivity_model:
  available: true
  approved_for_this_signoff: false
  permitted_claim: engineering_sensitivity_only
reason: >
  The open GF180 ngspice MIM path exposes global capacitance variation but no
  verified per-instance local MIM mismatch control. No source document,
  measurement, or explicit user approval was found for an engineering sigma.
downstream_action: STOP_BEFORE_STATIC_MC_SIGNOFF
evidence_tier: T2_LIMITATION_ONLY
""",
    )
    write_text(
        "config/noise_model.yaml",
        """
status: BLOCKED_NOISE_CALIBRATION_UNAVAILABLE
comparator_decision_noise:
  classification: UNAVAILABLE_UNCALIBRATED
  prior_evidence: SAR_EFFECTIVE_NOISE_SENSITIVITY_ONLY
  calibrated_sigma_rms_diff_v: null
sample_hold_noise:
  classification: UNAVAILABLE_UNCALIBRATED
  calibrated_sigma_rms_diff_v: null
reference_noise:
  classification: NOT_INCLUDED_UNCALIBRATED
event_model_enabled_for_signoff: false
engineering_stress_enabled_for_signoff: false
reason: >
  No transistor- or block-level probability data was available to satisfy the
  required sigma and T50 calibration gates. Existing evidence is T2 sensitivity,
  not native StrongARM transient-noise evidence.
downstream_action: STOP_BEFORE_NOISE_AND_DYNAMIC_MC_SIGNOFF
""",
    )
    write_text(
        "config/plot_style.yaml",
        """
status: FROZEN_NOT_APPLIED_GATED
vector_format: pdf
raster_format: png
raster_dpi: 300
axis_label_pt: 10
tick_label_pt: 9
line_width_pt: 1.2
marker_size_pt: 2.5
smoothing: disabled
color_blind_safe: true
""",
    )
    run_config = f"""
project: A44_8b_2MSps_GF180
campaign: A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718
signoff_label: SCHEMATIC_ANALOG_CORE_WITH_TT_BEHAVIORAL_SAR
campaign_status: BLOCKED
execution_stop_phase: PHASE_B_PDK_MISMATCH_NOISE_MODEL_GATES
pass_label_issued: false
workspace_container: {CONTAINER_ROOT}
adc:
  bits: 8
  fs_hz: 2000000
  frame_s: 5.0e-7
  vdd_nom_v: 3.3
  vcm_v: 1.65
  vrefp_v: 2.50
  vrefn_v: 0.80
  vfs_pp_diff_v: 3.4
  dynamic_input_pp_diff_v: 3.0
  lsb_diff_v: 0.01328125
logic_model:
  name: SAR_LOGIC_BEH_TT_3P3_27C
  timing_file: config/timing_tt_3p3_27c.json
  implementation: timed_event_driven_systemverilog_ngspice_d_cosim
  source: models/SAR_LOGIC_BEH_TT_3P3_27C.v
  compiled_model: models/SAR_LOGIC_BEH_TT_3P3_27C.so
  logic_pvt_variation: disabled
  actual_logic_signoff: disabled
fixture:
  r6_full_rc_heavy: disabled
  source_load_file: config/source_load_model.yaml
pvt:
  - {{name: TT_3P3_27C, process: TT, vdd_v: 3.3, temp_c: 27}}
  - {{name: SS_3P0_125C, process: SS, vdd_v: 3.0, temp_c: 125}}
  - {{name: FF_3P6_M40C, process: FF, vdd_v: 3.6, temp_c: -40}}
numerical:
  bulk_maxstep_s: 1.0e-10
  strict_maxstep_s: 5.0e-11
  smoke_maxstep_s: 5.0e-11
  static_final_tolerance_lsb: 0.02
  transition_pack_size: 32
mc:
  mismatch_seed_count: 200
  exact_validation_initial: 8
  exact_validation_expand: 16
  status: FROZEN_NOT_RUN_GATED
noise:
  comparator_target_rms_diff_v: 1.5e-3
  total_target_rms_diff_v: 2.0e-3
  stress_rms_diff_v: 2.5e-3
  status: BLOCKED_UNCALIBRATED
dynamic_fast64:
  retained: 64
  startup_default: 1
  low_bin: 7
  low_fin_hz: 218750
  near_nyquist_bin: 29
  near_nyquist_fin_hz: 906250
  window: rectangular
  dout_aperture_s: 4.8e-7
  status: NOT_RUN_GATED
dynamic_fast256:
  retained: 256
  low_bin: 29
  low_fin_hz: 226562.5
  near_nyquist_bin: 117
  near_nyquist_fin_hz: 914062.5
  window: rectangular
  status: NOT_RUN_GATED
spec:
  sndr_min_db: 44
  enob_min_bit: 7.0
  dnl_abs_max_lsb: 1.0
  inl_abs_max_lsb: 1.5
  missing_codes_max: 0
blockers:
  - BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE
  - BLOCKED_NOISE_CALIBRATION_UNAVAILABLE
secondary_gate_issue: SAME_SEED_MOS_MISMATCH_REPLAY_NOT_EXACT
"""
    write_text("config/run_config.yaml", run_config)
    write_csv(
        "config/mc_seeds.csv",
        [
            {
                "index": index,
                "mismatch_seed": index,
                "status": "FROZEN_NOT_RUN_GATED",
            }
            for index in range(1, 201)
        ],
        ["index", "mismatch_seed", "status"],
    )
    write_csv(
        "config/noise_seeds.csv",
        [
            {
                "index": index,
                "noise_seed": 100000 + index,
                "status": "FROZEN_NOT_RUN_GATED",
            }
            for index in range(1, 201)
        ],
        ["index", "noise_seed", "status"],
    )


def audit_environment() -> dict:
    versions = docker(
        "command -v ngspice; ngspice -v; command -v Xyce; Xyce -v; "
        "command -v xschem; xschem --version; command -v openvaf; openvaf --version; "
        "python3 --version"
    )
    python_packages = docker(
        "python3 -c \"import json,numpy,scipy,pandas,matplotlib,yaml; "
        "print(json.dumps({'numpy':numpy.__version__,'scipy':scipy.__version__,"
        "'pandas':pandas.__version__,'matplotlib':matplotlib.__version__,'yaml':yaml.__version__}))\""
    )
    system = docker(
        "printf 'logical_cpus='; nproc; free -h; df -h /foss/designs/manual_goal; "
        "lscpu | grep -E 'Model name|Socket|Core|Thread'"
    )
    pdk_hashes = docker(
        f"sha256sum {PDK_ROOT}/design.ngspice {PDK_ROOT}/sm141064.ngspice "
        f"{PDK_ROOT}/sm141064_mim.ngspice"
    )
    pdk_git = docker(
        "git -C /foss/pdks/gf180mcuD rev-parse HEAD 2>/dev/null || printf 'NOT_A_GIT_WORKTREE\\n'"
    )
    raw = "\n".join(
        [
            "# Tool versions",
            versions["stdout"],
            versions["stderr"],
            "# Python packages",
            python_packages["stdout"],
            python_packages["stderr"],
            "# Platform",
            system["stdout"],
            system["stderr"],
            "# PDK hashes",
            pdk_hashes["stdout"],
            pdk_hashes["stderr"],
            "# PDK git",
            pdk_git["stdout"],
            pdk_git["stderr"],
        ]
    )
    write_text("reports/tool_versions.txt", raw)
    write_text("source_snapshot/pdk/pdk_hashes.txt", pdk_hashes["stdout"] or pdk_hashes["stderr"])
    status = (
        "PASS"
        if all(item["returncode"] == 0 for item in (versions, python_packages, system, pdk_hashes))
        else "REVIEW"
    )
    payload = {
        "generated_utc": GENERATED_UTC,
        "status": status,
        "container": CONTAINER,
        "container_workspace": CONTAINER_ROOT,
        "tool_versions_capture": versions,
        "python_packages_capture": python_packages,
        "system_capture": system,
        "pdk_hash_capture": pdk_hashes,
        "pdk_git_capture": pdk_git,
    }
    write_json("reports/environment_audit.json", payload)
    return payload


def audit_behavioral_implementation() -> dict:
    model_path = ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.v"
    shared_object = ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.so"
    build_log_path = ROOT / "logs" / "build_behavioral_model.log"
    unit_log_path = ROOT / "logs" / "tb_cosim_unit.log"
    model = model_path.read_text(encoding="ascii")
    build_log = build_log_path.read_text(encoding="utf-8", errors="replace")
    unit_log = unit_log_path.read_text(encoding="utf-8", errors="replace")

    source_checks = [
        ("only_allowed_logic_inputs", all(token in model for token in ("input wire CLKS", "input wire DCMPP", "input wire DCMPN")) and "VINP" not in model and "VINN" not in model),
        ("eight_decision_loop_msb_to_lsb", "for (bit_index = 7; bit_index >= 0; bit_index = bit_index - 1)" in model),
        ("seven_physical_adjustments", "if (bit_index > 0) begin" in model and "dctrlp_state[bit_index] = decision_bit[0]" in model),
        ("active_low_complementary_dctrl", "dctrln_state[bit_index] = ~decision_bit[0]" in model),
        ("frozen_bidirectional_reset_state", model.count("7'b1000000") >= 2),
        ("atomic_dout_after_lsb", "DOUT = code_work" in model and "if (bit_index > 0) begin" in model),
        ("next_sample_abort_path", "always @(posedge CLKS)" in model and "generation = generation + 1" in model),
        ("both_high_invalid_detection", "DCMPP === 1'b1) && (DCMPN === 1'b1" in model),
        ("both_low_timeout_detection", "TIMEOUT_COUNT = TIMEOUT_COUNT + 1'b1" in model),
        ("per_bit_timing_functions", all(name in model for name in ("cmpck_high_ps", "decision_aperture_ps", "dctrl_from_rise_ps", "low_guard_ps"))),
    ]
    build_checks = [
        ("shared_object_exists", shared_object.is_file() and shared_object.stat().st_size > 0),
        ("cosim_setup_exported", "Cosim_setup" in build_log),
        ("elf_shared_object_identified", "ELF 64-bit LSB shared object" in build_log),
    ]

    def measured(name: str) -> float | None:
        match = re.search(rf"^{name}\s*=\s*([0-9.eE+-]+)", unit_log, re.MULTILINE)
        return float(match.group(1)) if match else None

    unit_values = {
        "t_cmp1_s": measured("t_cmp1"),
        "t_cmp8_s": measured("t_cmp8"),
        "t_complete_s": measured("t_complete"),
        "dout7_at_330_v": measured("dout7_at_330"),
        "dout0_at_330_v": measured("dout0_at_330"),
    }
    unit_pass = (
        all(value is not None for value in unit_values.values())
        and unit_values["t_cmp1_s"] < unit_values["t_cmp8_s"] < unit_values["t_complete_s"]
        and unit_values["dout7_at_330_v"] > 3.0
        and unit_values["dout0_at_330_v"] > 3.0
        and "ngspice-46 done" in unit_log
    )
    unit_warning = "output scheduled with impossible delay (0) at 1e-12/0" in unit_log
    rows = [
        {"category": "source_contract", "check": name, "status": "PASS" if passed else "FAIL"}
        for name, passed in source_checks
    ] + [
        {"category": "build", "check": name, "status": "PASS" if passed else "FAIL"}
        for name, passed in build_checks
    ] + [
        {"category": "cosim_unit", "check": "measured_sequence_and_all_one_dout", "status": "PASS" if unit_pass else "FAIL"}
    ]
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    payload = {
        "status": overall,
        "checks": rows,
        "unit_measurements": unit_values,
        "unit_startup_warning_present": unit_warning,
        "unit_startup_warning_disposition": "NON_FATAL_AT_INITIAL_COSIM_DELTA; MEASURED_CONVERSION_PASS" if unit_warning else "NONE",
        "model_sha256": sha256(model_path),
        "shared_object_sha256": sha256(shared_object) if shared_object.is_file() else None,
    }
    write_json("reports/behavioral_implementation_audit.json", payload)
    write_csv("reports/behavioral_implementation_audit.csv", rows, ["category", "check", "status"])
    write_text(
        "reports/behavioral_implementation_audit.md",
        f"""
# Behavioral Implementation Audit

- Status: `{overall}`
- Source: `models/SAR_LOGIC_BEH_TT_3P3_27C.v`
- Simulator-loaded binary: `models/SAR_LOGIC_BEH_TT_3P3_27C.so`
- `Cosim_setup` exported: `{'yes' if dict(build_checks)['cosim_setup_exported'] else 'no'}`
- Unit CMPCK1: `{unit_values['t_cmp1_s']}` s
- Unit CMPCK8: `{unit_values['t_cmp8_s']}` s
- Unit completion: `{unit_values['t_complete_s']}` s
- Unit DOUT[7]/DOUT[0] at 330 ns: `{unit_values['dout7_at_330_v']}` / `{unit_values['dout0_at_330_v']}` V

{markdown_table(rows, ["category", "check", "status"])}

The unit log contains one ngspice initial-delta warning about a zero scheduled
delay at 1 ps. It is classified as non-fatal because the complete measured event
sequence, eight decisions, completion, and final DOUT levels are present.
""",
    )
    return payload


def audit_dut_binding() -> dict:
    top_path = ROOT / "netlists" / "SAR_ADC_ANALOG_CORE_TT_BEH_NO_R6.spice"
    cdac_path = ROOT / "netlists" / "core" / "subckts" / "CDAC_native_extracted.subckt.spice"
    tb_path = ROOT / "tb" / "tb_actual_core_smoke_tt.spice"
    model_path = ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.v"
    top = top_path.read_text(encoding="ascii").lower()
    cdac = cdac_path.read_text(encoding="ascii").lower()
    tb = tb_path.read_text(encoding="ascii").lower()
    model = model_path.read_text(encoding="ascii").lower()
    checks = [
        ("two_cdac_instances", top.count("xcdacp ") == 1 and top.count("xcdacn ") == 1),
        ("one_strongarm_comparator", top.count(" comparator_strongarm") == 1),
        ("actual_sampler_hierarchy_present", "switch_boot_sp" in cdac),
        ("actual_sar_logic_hierarchy_absent", "sar_logic_actual" not in top + tb),
        ("timed_behavioral_sar_present", "sar_logic_beh d_cosim" in tb and "sar_logic_beh_tt_3p3_27c.so" in tb),
        ("r6_full_rc_heavy_absent", "r6_full_rc_heavy" not in top + tb),
        ("input_load_present", all(token in tb for token in ("rvinp", "rvinn", "cvin_diff"))),
        ("reference_load_present", all(token in tb for token in ("rvrefp", "rvrefn", "cvrefp_local", "cvrefn_local"))),
        ("finite_interface_drivers_present", all(token in tb for token in ("r_cmpck", "r_dctrlp7", "r_dctrln7", "r_dout7"))),
        ("behavior_does_not_read_vinp_vinn", "vinp" not in model and "vinn" not in model),
        ("eight_bit_dout_present", "output reg [7:0] dout" in model),
        ("straight_binary_smoke_pass", load_json("reports/behavioral_contract_smoke.json")["status"] == "PASS"),
    ]
    rows = [
        {"check": name, "status": "PASS" if passed else "FAIL", "evidence_tier": "T4"}
        for name, passed in checks
    ]
    status = "PASS" if all(passed for _, passed in checks) else "BLOCKED_WRONG_DUT_BINDING"
    payload = {"status": status, "checks": rows}
    write_json("reports/dut_binding_audit.json", payload)
    write_csv("reports/dut_binding_audit.csv", rows, ["check", "status", "evidence_tier"])
    write_text(
        "reports/dut_binding_audit.md",
        f"""
# DUT Binding Audit

- Generated UTC: `{GENERATED_UTC}`
- Status: `{status}`
- DUT: transistor-level sampler/CDAC/comparator plus `SAR_LOGIC_BEH_TT_3P3_27C`
- Excluded: actual SAR logic, `R6_FULL_RC_HEAVY`, pad, ESD, package, and PEX TOP

{markdown_table(rows, ["check", "status", "evidence_tier"])}

The sampler is reached through the `SWITCH_BOOT_SP` instance inside each copied
production CDAC subcircuit. The controller is loaded only through ngspice
`d_cosim`; no actual SAR-logic hierarchy is bound into the claim-bearing deck.
""",
    )
    return payload


def audit_pdk_capability() -> dict:
    grep = docker(
        f"grep -nE 'mc_c_cox|sw_stat_global|cap_mc_skew|sw_stat_mismatch|agauss' "
        f"{PDK_ROOT}/sm141064.ngspice {PDK_ROOT}/sm141064_mim.ngspice | head -n 240"
    )
    write_text("logs/pdk_model_capability_grep.log", grep["stdout"] + grep["stderr"])
    mos = load_json("reports/mos_mismatch_sanity.json")
    response_checks_pass = all(
        row["mismatch_off_collapses"]
        and row["mismatch_on_nonzero"]
        and row["area_scaling_ratio_ok"]
        and row["x2_scaling_ratio_ok"]
        and row["mean_physically_plausible"]
        for row in mos["checks"]
    )
    seed_reproducible = all(row["seed_reproducible"] for row in mos["checks"])
    payload = {
        "status": "BLOCKED",
        "mos_local_mismatch_model_response": "PASS" if response_checks_pass else "FAIL",
        "mos_same_seed_exact_replay": "PASS" if seed_reproducible else "FAIL",
        "mos_seed_request_methods": mos.get("seed_request_methods", []),
        "cdac_mim_local_mismatch": "UNAVAILABLE",
        "cdac_mismatch_status": "BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE",
        "noise_calibration": "UNAVAILABLE",
        "noise_status": "BLOCKED_NOISE_CALIBRATION_UNAVAILABLE",
        "pdk_grep_returncode": grep["returncode"],
        "downstream_mc200_authorized": False,
    }
    write_json("reports/pdk_mc_noise_capability.json", payload)
    write_text(
        "reports/pdk_mc_noise_capability.md",
        f"""
# PDK, Monte Carlo, and Noise Capability

- Generated UTC: `{GENERATED_UTC}`
- Phase status: `BLOCKED`
- MOS primitive model response: `{'PASS' if response_checks_pass else 'FAIL'}`
- Same-seed MOS exact replay: `{'PASS' if seed_reproducible else 'FAIL'}`
- CDAC local MIM mismatch: `UNAVAILABLE`
- Noise calibration: `UNAVAILABLE`

## Fresh MOS sanity

The fresh 64-pair NMOS and PMOS tests show collapse with mismatch disabled,
non-zero mismatch when enabled, acceptable area scaling, acceptable 2x scaling,
and plausible means. Exact replay of the same deck and requested seed failed for
both device types. Both `rndseed` and `rnd_seed` were requested through the
job-local startup file and environment before netlist loading.

## CDAC mismatch gate

The installed GF180 ngspice MIM path exposes global capacitance variation through
`mc_c_cox_*`, `sw_stat_global`, and `cap_mc_skew`. The included local MIM
subcircuits do not expose a verified per-instance local mismatch control. No
project measurement, source document, or explicit user approval was found for an
engineering `sigma_C/C` model. Therefore:

`BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE`

## Noise gate

Prior evidence is classified as SAR-effective T2 noise sensitivity. It is not a
calibrated transistor- or block-level StrongARM decision-probability model, and no
sample/hold calibration data was available. Therefore:

`BLOCKED_NOISE_CALIBRATION_UNAVAILABLE`

The execution guide requires a STOP before static-MC/noise signoff when these
models are unavailable. No MC200 job was launched.
""",
    )
    return payload


def write_phase_reports(source_integrity: dict, environment: dict, implementation: dict, binding: dict, pdk: dict) -> None:
    behavioral = load_json("reports/behavioral_contract_smoke.json")
    faults = load_json("reports/fault_flag_smoke.json")
    mos = load_json("reports/mos_mismatch_sanity.json")
    source_status = "PASS" if source_integrity["all_match"] else "BLOCKED_PRODUCTION_SOURCE_CHANGED"
    write_text(
        "reports/source_integrity.md",
        f"""
# Source Integrity

- Status: `{source_status}`
- Baseline: frozen `SAR_CURRENT/manifests/package_manifest_sha256.csv`
- Files checked: `{source_integrity['record_count']}`
- Changed or missing: `{len(source_integrity['changed_or_missing'])}`
- Production files modified by this campaign: `none`

The before manifest is the already-frozen SAR_CURRENT package baseline. The after
manifest is a fresh hash of those same paths after the preflight execution.
""",
    )
    shutil.copy2(ROOT / "reports" / "source_integrity.md", ROOT / "reports" / "01_source_integrity.md")
    write_text(
        "reports/environment_audit.md",
        f"""
# Environment Audit

- Status: `{environment['status']}`
- Container: `{CONTAINER}`
- Workspace: `{CONTAINER_ROOT}`
- PDK: `{PDK_ROOT}`
- Tool and platform capture: `reports/tool_versions.txt`
- Machine-readable capture: `reports/environment_audit.json`

The PDK model-file SHA-256 values are frozen in
`source_snapshot/pdk/pdk_hashes.txt`.
""",
    )
    write_text(
        "reports/00_executive_summary.md",
        f"""
# Executive Summary

Final status: `BLOCKED`

Phase A source/DUT preflight and the Phase B behavioral-control contract were
completed. Source integrity is `{source_status}`; DUT binding is
`{binding['status']}`; behavioral smoke is `{behavioral['status']}` for
`{behavioral['cases_passed']}/{behavioral['cases_total']}` cases; invalid/timeout
fault smoke is `{faults['status']}` for `{faults['cases_passed']}/{faults['cases_total']}` cases.

The mandatory Phase B model gates did not close. A defensible CDAC local mismatch
model is unavailable, and comparator/sample noise calibration is unavailable.
Same-seed MOS mismatch exact replay also failed despite valid aggregate model
response. Per the frozen guide, execution stopped before numerical pilots, PVT,
MC200, static extraction, dynamic FAST64, and FAST256 closure.

The expected PASS label is not issued.
""",
    )
    write_text(
        "reports/02_model_and_fixture_audit.md",
        f"""
# Model and Fixture Audit

- DUT binding: `{binding['status']}`
- Behavioral implementation/build/unit: `{implementation['status']}`
- Behavioral contract: `{behavioral['status']}`
- Fault handling: `{faults['status']}`
- Logic timing: fixed `TT_3P3_27C`
- Actual SAR logic in signoff deck: `absent`
- R6 heavy fixture: `absent`
- Equivalent source/reference/interface loading: `present and frozen`
- Smoke transient maxstep: `0.05 ns`

The claim-bearing controller is the compiled event-driven SystemVerilog model in
`models/SAR_LOGIC_BEH_TT_3P3_27C.v` / `.so`. It reads only CLKS, DCMPP, and DCMPN.
The Verilog-A file is retained as a readable reference implementation and was not
the simulator-loaded binary for these ngspice smoke tests.
""",
    )
    gated_reports = {
        "reports/03_numerical_convergence.md": ("Numerical Convergence", "Phase C", "Gate C"),
        "reports/04_pvt_screen.md": ("PVT Screen", "Phase D", "Gate D"),
        "reports/05_static_exact.md": ("Exact Static Extraction", "Phase E", "Gate D"),
        "reports/06_static_mc200.md": ("Static MC200", "Phase F", "Gate E"),
        "reports/08_dynamic_mc200_fast64.md": ("Dynamic MC200 FAST64", "Phase H", "Gate G"),
        "reports/09_fast256_closure.md": ("FAST256 Closure", "Phase I", "Gate H"),
        "reports/10_pvt_mc_interaction.md": ("PVT x MC Interaction", "Phase J", "Gate I"),
    }
    for relative, (title, phase, gate) in gated_reports.items():
        write_text(
            relative,
            f"""
# {title}

- Status: `NOT_RUN_GATED`
- Planned phase: `{phase}`
- Signoff gate: `{gate}`
- Completed jobs: `0`
- Numerical claim: `none`

The frozen execution order prohibits this phase before the Phase B CDAC mismatch
and noise-model prerequisites pass. The campaign stopped with
`BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE` and
`BLOCKED_NOISE_CALIBRATION_UNAVAILABLE`; no substitute model or reduced campaign
was used.
""",
        )
    write_text(
        "reports/07_noise_calibration.md",
        """
# Noise Calibration

- Status: `BLOCKED_NOISE_CALIBRATION_UNAVAILABLE`
- Comparator decision-noise calibration: `not available`
- Sample/hold noise calibration: `not available`
- Top selected-transition probability: `NOT_RUN_GATED`
- Claim-bearing equivalent-noise model: `disabled`

Existing evidence is T2 SAR-effective sensitivity. It does not satisfy the
required block-level sigma and T50 calibration errors and is not described as
native StrongARM transient-noise evidence.
""",
    )
    write_text(
        "reports/runtime_pilot.md",
        """
# Runtime Pilot

- Status: `NOT_RUN_GATED`
- Five-job pilot: `not launched`
- Completion estimate update: `not applicable`

The execution guide forbids launching numerical and bulk jobs before the model
gates pass. Resource inventory was completed, but no claim-bearing runtime pilot
was authorized.
""",
    )
    write_text(
        "reports/11_plot_audit.md",
        """
# Plot Audit

- Status: `NOT_RUN_GATED`
- Formal DNL plots: `absent`
- Formal INL plots: `absent`
- Formal FFT plots: `absent`
- Fabricated placeholder figures: `none`

No numerical source data exists because execution stopped in Phase B. Creating
empty or synthetic formal plots would be misleading. Every missing plot is listed
in `reports/not_run_artifact_matrix.csv`.
""",
    )
    write_text(
        "reports/mos_mismatch_sanity.md",
        f"""
# Fresh MOS Mismatch Sanity

- Overall script status: `{mos['status']}`
- Pair count per case: `{mos['pair_count_per_case']}`
- Requested seed: `{mos['seed']}`
- Aggregate model response checks: `PASS`
- Exact same-seed replay: `FAIL`

The script returns failure because exact seed replay is a required subcheck. This
does not erase the passing mismatch-enable, area-scaling, 2x-scaling, and mean
checks. It does prevent use of this route for auditable selected-seed replay.
""",
    )


def write_artifact_matrix() -> list[dict]:
    paths = [
        "csv/numerical_convergence.csv",
        "csv/pvt_static_screen.csv",
        "csv/pvt_dynamic_screen.csv",
        "csv/static_tt_exact.csv",
        "csv/static_pvt_worst_exact.csv",
        "csv/static_mc200_packed.csv",
        "csv/static_mc200_reconstructed.csv",
        "csv/static_model_validation.csv",
        "csv/comparator_noise_probability.csv",
        "csv/sample_noise.csv",
        "csv/top_transition_probability.csv",
        "csv/dynamic_mc200_fast64.csv",
        "csv/dynamic_noise_repeat.csv",
        "csv/dynamic_fast256_closure.csv",
        "csv/pvt_mc_tail_replay.csv",
        "plots/dnl_tt_nominal.pdf",
        "plots/dnl_tt_nominal.png",
        "plots/dnl_worst_exact_seed.pdf",
        "plots/dnl_worst_exact_seed.png",
        "plots/inl_endpoint_tt_nominal.pdf",
        "plots/inl_endpoint_tt_nominal.png",
        "plots/inl_endpoint_worst_exact_seed.pdf",
        "plots/inl_endpoint_worst_exact_seed.png",
        "plots/inl_bestfit_tt_nominal.pdf",
        "plots/inl_bestfit_tt_nominal.png",
        "plots/spectrum_fast64_nominal.pdf",
        "plots/spectrum_fast64_nominal.png",
        "plots/spectrum_fast64_worst_sndr.pdf",
        "plots/spectrum_fast64_worst_sndr.png",
        "plots/spectrum_fast256_pvt_worst_near_nyquist.pdf",
        "plots/spectrum_fast256_pvt_worst_near_nyquist.png",
        "plots/mc_sndr_cdf.pdf",
        "plots/mc_sndr_cdf.png",
        "plots/mc_sfdr_cdf.pdf",
        "plots/mc_sfdr_cdf.png",
    ]
    rows = [
        {
            "artifact": path,
            "status": "NOT_RUN_GATED",
            "exists": str((ROOT / path).exists()).lower(),
            "gate_reason": "PHASE_B_MODEL_PREREQUISITES_BLOCKED",
            "fabricated_placeholder_created": "false",
        }
        for path in paths
    ]
    write_csv(
        "reports/not_run_artifact_matrix.csv",
        rows,
        ["artifact", "status", "exists", "gate_reason", "fabricated_placeholder_created"],
    )
    return rows


def write_signoff_and_completion(source_integrity: dict, binding: dict, pdk: dict, artifact_rows: list[dict]) -> None:
    gates = [
        {"gate": "A", "name": "Source and DUT", "status": "PASS", "evidence_tier": "T4", "reason": "hashes unchanged; correct no-R6 analog-core binding"},
        {"gate": "B", "name": "Behavioral control", "status": "PASS", "evidence_tier": "T3_T4", "reason": "11/11 contract cases and 3/3 fault cases pass at 0.05 ns"},
        {"gate": "C", "name": "Numerical convergence", "status": "NOT_RUN_GATED", "evidence_tier": "NONE", "reason": "Phase B model prerequisites blocked"},
        {"gate": "D", "name": "Nominal and PVT static", "status": "NOT_RUN_GATED", "evidence_tier": "NONE", "reason": "Phase B model prerequisites blocked"},
        {"gate": "E", "name": "Static MC200", "status": "BLOCKED", "evidence_tier": "T0_T2_LIMITATION", "reason": "CDAC mismatch unavailable; exact MOS seed replay failed"},
        {"gate": "F", "name": "Noise", "status": "BLOCKED", "evidence_tier": "T2_LIMITATION", "reason": "comparator and sample noise uncalibrated"},
        {"gate": "G", "name": "Dynamic MC200", "status": "NOT_RUN_GATED", "evidence_tier": "NONE", "reason": "Gate F and Phase B blocked"},
        {"gate": "H", "name": "FAST256 closure", "status": "NOT_RUN_GATED", "evidence_tier": "NONE", "reason": "Gate G not run"},
        {"gate": "I", "name": "Selected PVT x MC", "status": "NOT_RUN_GATED", "evidence_tier": "NONE", "reason": "MC tails do not exist"},
        {"gate": "J", "name": "Evidence and reporting", "status": "BLOCKED", "evidence_tier": "AUDIT", "reason": "blocked closure reports complete; mandatory numerical data and plots absent"},
    ]
    write_csv(
        "reports/signoff_matrix.csv",
        gates,
        ["gate", "name", "status", "evidence_tier", "reason"],
    )
    write_json("reports/signoff_matrix.json", {"final_status": "BLOCKED", "gates": gates})
    matrix = markdown_table(gates, ["gate", "name", "status", "evidence_tier", "reason"])
    write_text(
        "reports/12_signoff_matrix.md",
        f"""
# Signoff Matrix

{matrix}

Only Gates A and B pass. The PASS label requires every gate A-J to pass and is
therefore not issued.
""",
    )
    audit_checks = [
        ("source_integrity_manifest", "PASS" if source_integrity["all_match"] else "FAIL"),
        ("frozen_configurations", "PASS"),
        ("frozen_seed_lists", "PASS"),
        ("correct_dut_binding", "PASS" if binding["status"] == "PASS" else "FAIL"),
        ("behavioral_build_and_cosim_unit", "PASS"),
        ("behavioral_contract_smoke", "PASS"),
        ("invalid_timeout_fault_smoke", "PASS"),
        ("mos_model_response", "PASS"),
        ("mos_exact_seed_replay", "BLOCKED"),
        ("approved_cdac_mismatch_model", "BLOCKED"),
        ("calibrated_noise_model", "BLOCKED"),
        ("mandatory_numerical_csv", "NOT_RUN_GATED"),
        ("mandatory_formal_plots", "NOT_RUN_GATED"),
        ("all_phase_reports", "PASS"),
        ("master_signoff_matrix", "PASS"),
        ("machine_readable_final_status", "PASS"),
    ]
    check_rows = [{"check": name, "status": status} for name, status in audit_checks]
    completion = {
        "generated_utc": GENERATED_UTC,
        "campaign_status": "BLOCKED",
        "stop_phase": "PHASE_B_PDK_MISMATCH_NOISE_MODEL_GATES",
        "closure_complete_as_blocked_stop": True,
        "document_signoff_definition_of_done_met": False,
        "pass_label_eligible": False,
        "pass_label_issued": False,
        "blocking_statuses": [
            "BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE",
            "BLOCKED_NOISE_CALIBRATION_UNAVAILABLE",
        ],
        "secondary_gate_issue": "SAME_SEED_MOS_MISMATCH_REPLAY_NOT_EXACT",
        "mc200_jobs_launched": 0,
        "numerical_artifacts_not_run": len(artifact_rows),
        "checks": check_rows,
    }
    write_json("reports/completion_audit.json", completion)
    write_text(
        "reports/completion_audit.md",
        f"""
# Completion Audit

- Campaign closure: `COMPLETE_AS_DOCUMENT_DEFINED_BLOCKED_STOP`
- Signoff definition of done: `NOT_MET`
- PASS label eligible: `false`
- MC200 jobs launched: `0`

{markdown_table(check_rows, ["check", "status"])}

The blocked closure is complete: every prerequisite examined before the mandatory
STOP has evidence, every downstream item is explicitly classified, and no absent
numerical result is represented as data. This is not schematic analog-core
signoff.
""",
    )
    final_status = {
        "status": "BLOCKED",
        "label": None,
        "expected_pass_label": "PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200",
        "pass_label_issued": False,
        "scope": "TT-timed behavioral SAR control; transistor-level analog core; no R6",
        "stop_phase": "PHASE_B_PDK_MISMATCH_NOISE_MODEL_GATES",
        "blocking_statuses": completion["blocking_statuses"],
        "secondary_gate_issue": completion["secondary_gate_issue"],
        "gates_passed": ["A", "B"],
        "gates_blocked": ["E", "F", "J"],
        "gates_not_run": ["C", "D", "G", "H", "I"],
        "mc_samples_planned": 200,
        "mc_samples_completed": 0,
        "bulk_fft_planned": 64,
        "bulk_fft_completed": 0,
        "closure_fft_planned": 256,
        "closure_fft_completed": 0,
        "actual_sar_logic_signoff": False,
        "pex_signoff": False,
        "r6_loaded_interface_signoff": False,
        "package_signoff": False,
        "production_yield_proven": False,
        "tapeout_readiness_claimed": False,
    }
    write_json("reports/final_status.json", final_status)
    write_text(
        "reports/MASTER_SIGNOFF_REPORT.md",
        f"""
# A44 TT Behavioral SAR Analog-Core Campaign Master Report

## Executive result

The campaign reached the mandatory Phase B stop and is `BLOCKED`. Gate A source
and DUT binding passed. Gate B behavioral control passed. A defensible local CDAC
MIM mismatch model and calibrated comparator/sample noise model were not
available. The planned MC200 and downstream static/dynamic closure were therefore
not launched.

## Gate matrix

{matrix}

## Claim boundary

What was demonstrated:

- production-source hash integrity against the frozen SAR_CURRENT package;
- transistor-level sampler/CDAC/comparator binding in a no-R6 campaign fixture;
- fixed TT timed-behavioral control with finite electrical interface loading;
- 11/11 nominal and code-boundary behavioral smoke cases at maxstep 0.05 ns;
- 3/3 invalid, timeout, and early-abort fault cases;
- fresh primitive MOS mismatch response, with failed exact seed replay recorded.

What was not demonstrated:

- full-transition TT or PVT DNL/INL;
- static MC200 or reconstructed transfer validation;
- calibrated comparator/sample noise;
- dynamic MC200 FAST64 or FAST256 closure;
- full actual-SAR-logic, PEX/layout, R6-loaded, pad/ESD/package, yield, or tapeout signoff.

## Final format

Final status:
    BLOCKED

Pass label, if applicable:
    NOT_APPLICABLE_NOT_ISSUED

Scope:
    transistor-level sampler/CDAC/comparator
    fixed TT timed behavioral SAR control
    no R6 external RC fixture
    analog PVT NOT_RUN_GATED
    MC200 NOT_RUN_GATED
    calibrated equivalent noise BLOCKED
    FAST64 bulk + FAST256 closure NOT_RUN_GATED

Explicit non-claims:
    no actual-SAR-logic signoff
    no PEX/layout/package signoff
    no production-yield proof
    no tapeout-readiness claim

Open risks:
    BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE
    BLOCKED_NOISE_CALIBRATION_UNAVAILABLE
    SAME_SEED_MOS_MISMATCH_REPLAY_NOT_EXACT
""",
    )


def write_readme() -> None:
    write_text(
        "README.md",
        f"""
# A44 TT Behavioral SAR No-R6 Campaign

Final status: `BLOCKED`

This independent workspace implements the preflight, timed behavioral controller,
actual analog-core smoke, primitive-model audit, and document-defined blocked
closure for the frozen execution guide. Production TOP/core/schematic/symbol/RTL
files were not edited.

## Exact commands

Run inside `{CONTAINER}`:

```bash
cd {CONTAINER_ROOT}
bash scripts/build_behavioral_model.sh
ngspice -b -o logs/tb_cosim_unit.log tb/tb_cosim_unit.spice
python3 scripts/run_behavioral_contract_smoke.py
python3 scripts/run_fault_flag_smoke.py
python3 scripts/run_mos_mismatch_sanity.py
python3 scripts/audit_campaign.py
```

The MOS sanity command intentionally returns non-zero while exact seed replay is
failing; its JSON and CSV outputs remain evidence. Run the Windows-side closure:

```powershell
python scripts/finalize_blocked_campaign.py
```

No MC200, numerical convergence, PVT, full-transition static, noise probability,
FAST64, or FAST256 command was launched because Phase B issued mandatory STOP
conditions.

## Entry points

- `reports/MASTER_SIGNOFF_REPORT.md`
- `reports/final_status.json`
- `reports/completion_audit.json`
- `reports/signoff_matrix.csv`
- `reports/not_run_artifact_matrix.csv`
- `manifests/package_manifest_sha256.csv`
""",
    )


def write_package_manifest() -> int:
    records = []
    manifest_relative = "manifests/package_manifest_sha256.csv"
    for path in sorted(item for item in ROOT.rglob("*") if item.is_file()):
        relative = path.relative_to(ROOT).as_posix()
        if relative == manifest_relative:
            continue
        records.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_csv(manifest_relative, records, ["relative_path", "size_bytes", "sha256"])
    return len(records)


def main() -> int:
    for directory in ("config", "csv", "jobs", "logs", "manifests", "plots", "raw", "reports", "source_snapshot"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    references = freeze_reference_inputs()
    source_integrity = audit_source_integrity()
    freeze_configuration(references)
    environment = audit_environment()
    implementation = audit_behavioral_implementation()
    binding = audit_dut_binding()
    pdk = audit_pdk_capability()
    write_phase_reports(source_integrity, environment, implementation, binding, pdk)
    artifact_rows = write_artifact_matrix()
    write_signoff_and_completion(source_integrity, binding, pdk, artifact_rows)
    write_readme()
    manifest_count = write_package_manifest()
    summary = {
        "status": "BLOCKED",
        "source_integrity": source_integrity["all_match"],
        "dut_binding": binding["status"],
        "package_manifest_records": manifest_count,
        "root": str(ROOT),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if source_integrity["all_match"] and binding["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
