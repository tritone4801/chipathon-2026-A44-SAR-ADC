#!/usr/bin/env python3
"""Close the campaign as an evidence-backed Gate-E FAIL_DNL."""

from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

import finalize_blocked_campaign as foundation


ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
CONFIG_PATH = ROOT / "config" / "run_config.yaml"
GENERATED_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
FINAL_STATUS = "FAIL"
FAILURE_STATUS = "FAIL_DNL"
STOP_PHASE = "PHASE_F_STATIC_MC200_EXACT_FAILURE"
PASS_LABEL = "PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="ascii"))


def read_csv(path: Path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="ascii")


def write_json(path: Path, payload):
    write_text(path, json.dumps(payload, indent=2, sort_keys=False))


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows, fields):
    lines = [
        "| " + " | ".join(fields) + " |",
        "|" + "|".join("---" for _ in fields) + "|",
    ]
    lines.extend(
        "| " + " | ".join(str(row.get(field, "")) for field in fields) + " |"
        for row in rows
    )
    return "\n".join(lines)


def update_config(screen_count, reconstructed_count):
    raw = CONFIG_PATH.read_text(encoding="ascii")
    try:
        config = yaml.safe_load(raw)
    except yaml.YAMLError:
        lines = raw.splitlines()
        normalized = []
        in_pvt = False
        inserted_cases = False
        for line in lines:
            if line == "pvt:":
                in_pvt = True
                inserted_cases = False
                normalized.append(line)
                continue
            if in_pvt and line and not line.startswith(" "):
                in_pvt = False
            if in_pvt and line.startswith("  - "):
                if not inserted_cases:
                    normalized.append("  cases:")
                    inserted_cases = True
                normalized.append("  " + line)
            else:
                normalized.append(line)
        config = yaml.safe_load("\n".join(normalized) + "\n")
    config["campaign_status"] = FAILURE_STATUS
    config["execution_stop_phase"] = STOP_PHASE
    config["current_phase"] = "COMPLETE_AS_EVIDENCE_BACKED_FAIL_GATE"
    config["pass_label_issued"] = False
    config["mc"].update(
        {
            "status": "FAIL_DNL_EXACT_SEED_2_GATE_CLOSED",
            "packed_screen_completed": screen_count,
            "transfer_reconstruction_completed": reconstructed_count,
            "exact_failure_seed": 2,
            "full_exact_validation_completed": 0,
        }
    )
    config["noise"]["status"] = (
        "CALIBRATION_PASS_TOP_PROBABILITY_NOT_RUN_GATE_CLOSED"
    )
    config["dynamic_fast64"]["status"] = "NOT_RUN_GATE_CLOSED"
    config["dynamic_fast256"]["status"] = "NOT_RUN_GATE_CLOSED"
    config["blockers"] = []
    config["failures"] = [
        {
            "status": FAILURE_STATUS,
            "gate": "E",
            "mismatch_seed": 2,
            "pvt": "TT_3P3_27C",
            "noise": "OFF",
            "evidence": "results/static_mc_failure_confirmation.json",
        }
    ]
    CONFIG_PATH.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="ascii"
    )


def audit_event_noise_smoke():
    deck = ROOT / "jobs" / "event_noise_smoke" / "event_noise_syntax_smoke.spice"
    log = ROOT / "logs" / "event_noise_smoke" / "event_noise_syntax_smoke.log"
    deck_text = deck.read_text(encoding="ascii") if deck.is_file() else ""
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""

    def measured(name):
        match = re.search(rf"^{name}\s*=\s*([-+0-9.eE]+)", log_text, re.MULTILINE)
        return float(match.group(1)) if match else None

    bits = [measured(f"f000_d{bit}") for bit in range(7, -1, -1)]
    code = None
    if all(value is not None for value in bits):
        code = sum((1 << (7 - index)) for index, value in enumerate(bits) if value > 1.65)
    checks = {
        "deck_present": deck.is_file(),
        "log_present": log.is_file(),
        "t2_event_noise_marker": "T2_EVENT_NOISE" in deck_text,
        "complete_high": (measured("f000_complete") or 0.0) > 1.65,
        "invalid_low": measured("f000_invalid") == 0.0,
        "timeout_low": measured("f000_timeout") == 0.0,
        "code_is_128": code == 128,
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "purpose": "SYNTAX_AND_BINDING_SMOKE_ONLY",
        "evidence_tier": "T2_EVENT_MODEL_ADAPTER_SMOKE",
        "noise_seed": 499001,
        "frames": 1,
        "maxstep_s": 5.0e-11,
        "code": code,
        "checks": checks,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
        "claim_boundary": "not selected-transition probability and not Gate F closure",
    }
    write_json(RESULT_DIR / "event_noise_syntax_smoke.json", payload)
    write_text(
        REPORT_DIR / "event_noise_syntax_smoke.md",
        f"""# Event Noise Syntax Smoke

- Status: `{payload['status']}`
- Purpose: `SYNTAX_AND_BINDING_SMOKE_ONLY`
- Noise seed: `499001`
- Frame count: `1`
- Maxstep: `0.05 ns`
- Decoded code: `{code}`
- Complete/invalid/timeout: `{checks['complete_high']}/{not checks['invalid_low']}/{not checks['timeout_low']}`
- Evidence tier: `T2_EVENT_MODEL_ADAPTER_SMOKE`

This check proves that the campaign-local event-noise deck parses, runs, and binds to the actual analog core. It is not a selected-transition probability test and does not close Gate F.
""",
    )
    return payload


def write_source_reports(source_integrity):
    status = "PASS" if source_integrity["all_match"] else "BLOCKED"
    content = f"""# Source Integrity

- Status: `{status}`
- Frozen production package: `SAR_CURRENT`
- Records compared: `{source_integrity['record_count']}`
- Changed or missing production files: `{len(source_integrity['changed_or_missing'])}`
- Before manifest: `manifests/source_hashes_before.json`
- Fresh after manifest: `manifests/source_hashes_after.json`
- Comparison: `manifests/source_hash_comparison.csv`

The campaign workspace contains copied netlists, models, testbenches, scripts, jobs, logs, and reports. No production TOP/core schematic, symbol, RTL, layout, or current-goal file was edited.
"""
    write_text(REPORT_DIR / "source_integrity.md", content)
    write_text(REPORT_DIR / "01_source_integrity.md", content)


def write_not_run_matrix(screen_count, reconstructed_count):
    rows = [
        {
            "item": "static_mc200_packed_screen",
            "artifact": "csv/static_mc200_screen_summary.csv",
            "planned": 200,
            "completed": screen_count,
            "status": "PARTIAL_GATE_CLOSED",
            "reason": "pre-declared seed 2 exact electrical FAIL_DNL",
        },
        {
            "item": "static_mc200_reconstruction",
            "artifact": "csv/static_mc200_reconstructed.csv",
            "planned": 200,
            "completed": reconstructed_count,
            "status": "PARTIAL_GATE_CLOSED",
            "reason": "pre-declared seed 2 exact electrical FAIL_DNL",
        },
        {
            "item": "static_mc_full_exact_validation",
            "artifact": "csv/static_mc_exact_validation.csv",
            "planned": 8,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "targeted exact replay already proved a static specification failure",
        },
        {
            "item": "top_selected_transition_probability",
            "artifact": "csv/top_transition_probability.csv",
            "planned": 1,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "item": "dynamic_mc200_fast64",
            "artifact": "csv/dynamic_mc200_fast64.csv",
            "planned": 200,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "item": "dynamic_noise_repeat_diagnostic",
            "artifact": "csv/dynamic_noise_repeat_diagnostic.csv",
            "planned": 32,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "item": "fast256_closure",
            "artifact": "csv/dynamic_fast256_closure.csv",
            "planned": 1,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "item": "pvt_x_mc_tail_closure",
            "artifact": "csv/pvt_mc_interaction.csv",
            "planned": 1,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "item": "formal_dynamic_fft_and_mc_cdf_plots",
            "artifact": "plots/spectrum_*.pdf; plots/mc_*_cdf.pdf",
            "planned": 5,
            "completed": 0,
            "status": "NOT_RUN_GATE_CLOSED",
            "reason": "no dynamic claim-bearing data after Gate E failure",
        },
    ]
    fields = ["item", "artifact", "planned", "completed", "status", "reason"]
    write_csv(REPORT_DIR / "not_run_artifact_matrix.csv", rows, fields)
    write_csv(CSV_DIR / "not_run_artifact_matrix.csv", rows, fields)
    return rows


def write_phase_reports(data):
    exact = data["exact"]
    pvt = data["pvt"]
    failure = data["failure"]
    comparator = data["comparator"]
    sample = data["sample"]
    screen_count = data["screen_count"]
    reconstructed_count = data["reconstructed_count"]
    valid_evaluations = data["valid_evaluations"]

    proven = [row for row in failure["comparisons"] if row["dnl_failure_proven"]]
    failure_table = []
    for row in failure["comparisons"]:
        failure_table.append(
            {
                "code": row["code"],
                "nominal_width_lsb": f"{row['width_lsb_nominal']:.6f}",
                "min_width_lsb": f"{row['min_width_lsb']:.6f}",
                "max_width_lsb": f"{row['max_width_lsb']:.6f}",
                "dnl_fail_proven": row["dnl_failure_proven"],
                "strict_missing": row["missing_code_strictly_proven"],
            }
        )

    write_text(
        REPORT_DIR / "00_executive_summary.md",
        f"""# Executive Summary

- Final status: `FAIL`
- Failure status: `FAIL_DNL`
- Stop phase: `{STOP_PHASE}`
- Pass label issued: `NO`

Phases A through E passed source, behavioral, model-prerequisite, numerical, PVT-screen, and deterministic full-static gates. During Phase F, pre-declared mismatch seed 2 produced exact strict electrical DNL failure at TT, with noise off. Code 63 has conservative width `[3.798437, 3.828437] LSB`; code 191 has `[3.754965, 3.784965] LSB`. Both intervals imply DNL above `+1 LSB`, so the circuit violates the frozen static specification.

The result is a circuit-performance `FAIL`, not an evidence `BLOCKED`. Downstream probability, MC200 FAST64, FAST256, and PVT x MC work is `NOT_RUN_GATE_CLOSED`; no pass label is eligible.
""",
    )

    write_text(
        REPORT_DIR / "02_model_and_fixture_audit.md",
        f"""# Model and Fixture Audit

- Gate A source/DUT: `PASS`
- Gate B behavioral control: `PASS`
- DUT: transistor-level sampler, P/N CDACs, StrongARM comparator, and output buffers
- Control: fixed `SAR_LOGIC_BEH_TT_3P3_27C`
- Actual SAR logic: `ABSENT_BY_SCOPE`
- R6_FULL_RC_HEAVY: `ABSENT_BY_SCOPE`
- Finite source/reference/interface loads: `PRESENT`
- CDAC mismatch: `APPROVED_ENGINEERING_MODEL`, evidence tier `T2`
- Comparator equivalent noise calibration: `{comparator['status']}`, evidence tier `T2`
- Sample/CDAC noise calibration: `{sample['status']}`, mixed `T0/T1/T2` with explicit transient-noise boundary

No PDK-native MIM mismatch or native MOS transient-noise claim is made.
""",
    )

    numerical_body = (REPORT_DIR / "numerical_convergence.md").read_text(encoding="ascii")
    write_text(REPORT_DIR / "03_numerical_convergence.md", numerical_body)
    pvt_body = (REPORT_DIR / "pvt_screen.md").read_text(encoding="ascii")
    write_text(REPORT_DIR / "04_pvt_screen.md", pvt_body)
    static_body = (REPORT_DIR / "static_exact.md").read_text(encoding="ascii")
    write_text(REPORT_DIR / "05_static_exact.md", static_body)

    static_mc = f"""# Static MC200

- Gate E: `FAIL`
- Failure status: `FAIL_DNL`
- Planned mismatch seeds: `200`
- Packed electrical screens completed before gate closure: `{screen_count}/200`
- Reconstructed transfers completed before gate closure: `{reconstructed_count}/200`
- Exact full 8-seed validation: `NOT_RUN_GATE_CLOSED`
- Exact failure replay: seed `2`, TT, noise `OFF`, final maxstep `0.05 ns`
- Exact targets: `63, 64, 65, 191, 192, 193`
- Exact-search status: `6/6 PASS`
- Valid electrical evaluation frames: `{valid_evaluations}`

{markdown_table(failure_table, ['code', 'nominal_width_lsb', 'min_width_lsb', 'max_width_lsb', 'dnl_fail_proven', 'strict_missing'])}

The formal DNL limit is `< +/-1 LSB`, corresponding to normalized code width strictly inside `(0, 2) LSB`. Codes 63 and 191 have conservative minimum widths above `3.75 LSB`; their DNL failures are therefore proven even after accounting for every final transition bracket.

Codes 64 and 192 are extremely narrow risk indicators, but their finite intervals cross the zero-width boundary. They are not used to claim mathematically zero width, and this package does not issue `FAIL_MISSING_CODE`.

Because a pre-declared die has a T4 exact electrical static-specification failure, Gate E cannot pass. Completing the remaining population cannot restore signoff eligibility, so later work is recorded as `NOT_RUN_GATE_CLOSED` rather than fabricated.
"""
    write_text(REPORT_DIR / "static_mc200.md", static_mc)
    write_text(REPORT_DIR / "06_static_mc200.md", static_mc)

    write_text(
        REPORT_DIR / "transfer_model_validation.md",
        f"""# Transfer Model Validation

- Status: `INCOMPLETE_GATE_CLOSED_BY_EXACT_ELECTRICAL_FAIL`
- Packed/reconstructed seeds available: `{reconstructed_count}`
- Exact five-major-transition calibration performed for seeds: `1, 2`
- Full 8-seed validation matrix: `NOT_RUN_GATE_CLOSED`
- Exact model-independent failure replay: `PASS_AS_FAILURE_EVIDENCE`

The reconstruction predicted seed 2 static risk and was used only to select exact targets. Final `FAIL_DNL` is based on transistor-level electrical replay, not on reconstructed DNL. No model-validation pass or 200-die yield claim is made.
""",
    )

    comparator_pass = sum(case["status"] == "PASS" for case in comparator["cases"])
    write_text(
        REPORT_DIR / "07_noise_calibration.md",
        f"""# Noise Calibration

- Standalone comparator calibration: `{comparator['status']}`
- Comparator passing fitted cases: `{comparator_pass}`
- Comparator target sigma: `{comparator['sigma_target_v_rms_diff']:.7f} V_rms,diff`
- Sample/CDAC calibration: `{sample['status']}`
- Worst sample noise: `{sample['worst_sample_noise_diff_v_rms']:.9f} V_rms,diff`
- Worst combined comparator plus sample noise: `{sample['worst_combined_comparator_sample_noise_diff_v_rms']:.9f} V_rms,diff`
- Event-noise adapter single-frame syntax/binding smoke: `{data['event_smoke']['status']}`
- Top selected-transition probability: `NOT_RUN_GATE_CLOSED`
- Gate F: `NOT_RUN_GATE_CLOSED`

The event model is T2 engineering evidence. Native compact-device transient noise is not claimed.
""",
    )

    gated = {
        "08_dynamic_mc200_fast64.md": (
            "Dynamic MC200 FAST64",
            "Gate G",
            "0/200 FAST64 jobs; nominal and noise-repeat matrices not launched",
        ),
        "09_fast256_closure.md": (
            "FAST256 Closure",
            "Gate H",
            "TT, PVT-worst, median, and tail FAST256 cases not launched",
        ),
        "10_pvt_mc_interaction.md": (
            "PVT x MC Interaction",
            "Gate I",
            "tail roles were not established after Gate E closed",
        ),
    }
    for filename, (title, gate, detail) in gated.items():
        write_text(
            REPORT_DIR / filename,
            f"""# {title}

- Status: `NOT_RUN_GATE_CLOSED`
- Gate: `{gate}`
- Upstream close condition: `Gate E FAIL_DNL`
- Completion: `{detail}`

No numerical metric, pass result, or signoff claim is inferred for this phase.
""",
        )

    return proven


def gate_matrix():
    return [
        {
            "gate": "A",
            "name": "Source and DUT",
            "status": "PASS",
            "evidence_tier": "T4_AUDIT",
            "reason": "fresh hashes unchanged; correct no-R6 analog-core binding",
        },
        {
            "gate": "B",
            "name": "Behavioral control",
            "status": "PASS",
            "evidence_tier": "T3_T4",
            "reason": "11 contract cases and 3 fault cases pass at 0.05 ns",
        },
        {
            "gate": "C",
            "name": "Numerical convergence",
            "status": "PASS",
            "evidence_tier": "T4",
            "reason": "100 ps bulk and 50 ps strict gate, 500 ns frame, startup 0",
        },
        {
            "gate": "D",
            "name": "Nominal and PVT static",
            "status": "PASS",
            "evidence_tier": "T4",
            "reason": "TT 255 up/down and SS-worst 255 up exact curves pass",
        },
        {
            "gate": "E",
            "name": "Static MC200",
            "status": "FAIL",
            "evidence_tier": "T4_FAILURE",
            "reason": "seed 2 exact strict code 63 and 191 DNL lower bounds exceed +1 LSB",
        },
        {
            "gate": "F",
            "name": "Noise",
            "status": "NOT_RUN_GATE_CLOSED",
            "evidence_tier": "T2_CALIBRATION_ONLY",
            "reason": "calibrations pass; top transition probability not run after Gate E fail",
        },
        {
            "gate": "G",
            "name": "Dynamic MC200",
            "status": "NOT_RUN_GATE_CLOSED",
            "evidence_tier": "NONE",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "gate": "H",
            "name": "FAST256 closure",
            "status": "NOT_RUN_GATE_CLOSED",
            "evidence_tier": "NONE",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "gate": "I",
            "name": "Selected PVT x MC",
            "status": "NOT_RUN_GATE_CLOSED",
            "evidence_tier": "NONE",
            "reason": "Gate E FAIL_DNL",
        },
        {
            "gate": "J",
            "name": "Evidence and reporting",
            "status": "PASS",
            "evidence_tier": "AUDIT",
            "reason": "fail evidence, applicable plots, hashes, reports, non-claims, and gated matrix complete",
        },
    ]


def write_signoff(gates, data, not_run_rows, source_integrity):
    fields = ["gate", "name", "status", "evidence_tier", "reason"]
    write_csv(REPORT_DIR / "signoff_matrix.csv", gates, fields)
    write_csv(CSV_DIR / "signoff_matrix.csv", gates, fields)
    signoff_payload = {"final_status": FINAL_STATUS, "failure_status": FAILURE_STATUS, "gates": gates}
    write_json(REPORT_DIR / "signoff_matrix.json", signoff_payload)
    write_json(RESULT_DIR / "signoff_matrix.json", signoff_payload)
    matrix_md = "# Signoff Matrix\n\n" + markdown_table(gates, fields)
    write_text(REPORT_DIR / "12_signoff_matrix.md", matrix_md)

    final_status = {
        "generated_utc": GENERATED_UTC,
        "status": FINAL_STATUS,
        "failure_status": FAILURE_STATUS,
        "label": None,
        "expected_pass_label": PASS_LABEL,
        "pass_label_issued": False,
        "closure_class": "COMPLETE_AS_EVIDENCE_BACKED_FAIL_GATE",
        "scope": "TT-timed behavioral SAR control; transistor-level analog core; no R6",
        "stop_phase": STOP_PHASE,
        "failure_evidence": {
            "mismatch_seed": 2,
            "pvt": "TT_3P3_27C",
            "noise": "OFF",
            "maxstep_final_s": 5.0e-11,
            "final_bracket_requirement_lsb": 0.02,
            "proven_dnl_failure_codes": [63, 191],
            "artifact": "results/static_mc_failure_confirmation.json",
        },
        "gates_passed": ["A", "B", "C", "D", "J"],
        "gates_failed": ["E"],
        "gates_not_run_gate_closed": ["F", "G", "H", "I"],
        "mc_samples_planned": 200,
        "mc_packed_screen_completed": data["screen_count"],
        "mc_reconstructed_completed": data["reconstructed_count"],
        "mc_full_exact_validation_completed": 0,
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
    write_json(REPORT_DIR / "final_status.json", final_status)
    write_json(RESULT_DIR / "final_status.json", final_status)

    checks = [
        {"check": "source_integrity_manifest", "status": "PASS" if source_integrity["all_match"] else "BLOCKED"},
        {"check": "frozen_configurations_and_seed_lists", "status": "PASS"},
        {"check": "gate_a_source_and_dut", "status": "PASS"},
        {"check": "gate_b_behavioral_control", "status": "PASS"},
        {"check": "gate_c_numerical_convergence", "status": "PASS"},
        {"check": "gate_d_nominal_pvt_static", "status": "PASS"},
        {"check": "gate_e_exact_dnl_failure_proof", "status": "PASS_AS_FAILURE_EVIDENCE"},
        {"check": "full_static_mc200_population", "status": "NOT_RUN_GATE_CLOSED"},
        {"check": "noise_top_probability", "status": "NOT_RUN_GATE_CLOSED"},
        {"check": "dynamic_fast64_fast256_pvt_mc", "status": "NOT_RUN_GATE_CLOSED"},
        {"check": "applicable_formal_static_plots", "status": data["plot"]["status"]},
        {"check": "fft_and_mc_cdf_plots", "status": "NOT_RUN_GATE_CLOSED"},
        {"check": "all_phase_reports", "status": "PASS"},
        {"check": "master_signoff_matrix", "status": "PASS"},
        {"check": "machine_readable_final_status", "status": "PASS"},
        {"check": "explicit_non_claims", "status": "PASS"},
    ]
    completion = {
        "generated_utc": GENERATED_UTC,
        "campaign_status": FINAL_STATUS,
        "failure_status": FAILURE_STATUS,
        "stop_phase": STOP_PHASE,
        "closure_complete_as_evidence_backed_fail_gate": True,
        "document_pass_definition_of_done_met": False,
        "pass_label_eligible": False,
        "pass_label_issued": False,
        "not_run_gate_closed_items": len(not_run_rows),
        "checks": checks,
    }
    write_json(REPORT_DIR / "completion_audit.json", completion)
    write_text(
        REPORT_DIR / "completion_audit.md",
        "# Completion Audit\n\n"
        f"- Campaign status: `{FINAL_STATUS}`\n"
        f"- Failure status: `{FAILURE_STATUS}`\n"
        "- Closure class: `COMPLETE_AS_EVIDENCE_BACKED_FAIL_GATE`\n"
        "- Pass definition of done met: `NO`\n"
        "- Pass label eligible/issued: `NO/NO`\n\n"
        + markdown_table(checks, ["check", "status"]),
    )

    master = f"""# A44 TT Behavioral SAR Analog-Core Campaign Master Report

## Executive Result

Final campaign status is `FAIL`, with failure code `FAIL_DNL`. Source, DUT, behavioral-control, numerical, PVT-screen, and deterministic exact-static gates passed. During the Phase F mismatch pilot, pre-declared seed 2 produced a T4 exact electrical DNL violation at TT with noise off.

The decisive bounds are:

- code 63 normalized width `[3.798437, 3.828437] LSB`, so DNL is at least `+2.798437 LSB`;
- code 191 normalized width `[3.754965, 3.784965] LSB`, so DNL is at least `+2.754965 LSB`.

Both exceed the frozen `< +/-1 LSB` DNL requirement even under conservative transition-bracket uncertainty. The result is model-independent: reconstruction selected the risk region, but final classification uses transistor-level sampler/CDAC/comparator replay with fixed TT timed behavioral control, `maxstep=0.05 ns`, noise off, and final transition brackets `<=0.02 LSB`.

No strict zero-width missing-code claim is made. Codes 64 and 192 remain extreme narrow-width risks, but finite brackets do not prove zero mathematical width.

## Gate Matrix

{markdown_table(gates, fields)}

## Completed Evidence

- production-source hash integrity refreshed at closure;
- correct transistor-level no-R6 analog-core binding and TT timed behavioral controller;
- behavioral contract and fault handling at strict maxstep;
- MOS/CDAC mismatch prerequisites and comparator/sample equivalent-noise calibrations;
- numerical convergence, startup, frame length, and runtime pilot;
- TT exact 255-transition up/down, SS-worst exact 255-transition up, selected reverse checks, and 256-code triangular-ramp coverage;
- seed 2 exact strict static-failure confirmation with 68/68 valid electrical evaluation frames;
- seven applicable formal static plots in PDF, 300 dpi PNG, and source CSV;
- explicit gated-artifact matrix and package SHA-256 manifest.

## Gate-Closed Work

The MC200 packed screen and reconstruction stopped at `{data['screen_count']}/200` and `{data['reconstructed_count']}/200`. Full 8-seed exact model validation, top transition probability, MC200 FAST64, FAST256, and selected PVT x MC closure were not run after the decisive Gate E failure. These omissions are classified `NOT_RUN_GATE_CLOSED`, not PASS and not BLOCKED.

## Claim Boundary

This package supports only an evidence-backed schematic analog-core `FAIL_DNL` under transistor-level sampler/CDAC/comparator, fixed TT timed behavioral SAR control, explicit no-R6 fixture loads, TT analog condition, mismatch seed 2, and noise off.

Final status:
    FAIL

Pass label, if applicable:
    NOT_APPLICABLE_NOT_ISSUED

Scope:
    transistor-level sampler/CDAC/comparator
    fixed TT timed behavioral SAR control
    no R6 external RC fixture
    analog PVT screen and deterministic exact static completed
    MC200 population PARTIAL_GATE_CLOSED
    calibrated equivalent noise completed at block level; top probability NOT_RUN_GATE_CLOSED
    FAST64 bulk + FAST256 closure NOT_RUN_GATE_CLOSED

Explicit non-claims:
    no actual-SAR-logic signoff
    no PEX/layout/package signoff
    no R6-loaded interface signoff
    no native-MIM mismatch claim
    no native MOS transient-noise claim
    no 200-die yield or production-yield proof
    no tapeout-readiness claim

Open risks:
    root cause of seed 2 common-mode/carry DNL failure is not isolated to a production design change
    full MC200 incidence and tail distribution are not measured after the fail gate
    codes 64 and 192 are extreme narrow-width risks but zero width is not strictly proven
    dynamic, FAST256, and PVT x MC performance remain unmeasured
"""
    write_text(REPORT_DIR / "MASTER_SIGNOFF_REPORT.md", master)


def write_readme(data):
    write_text(
        ROOT / "README.md",
        f"""# A44 TT Behavioral SAR No-R6 Campaign

Final status: `FAIL_DNL`

Closure class: `COMPLETE_AS_EVIDENCE_BACKED_FAIL_GATE`

The campaign reached an exact strict static failure on pre-declared mismatch seed 2. Production TOP/core/schematic/symbol/RTL files were not edited. Downstream work is explicitly `NOT_RUN_GATE_CLOSED`; no pass label, MC200 yield, FFT closure, or tapeout claim is made.

## Decisive Evidence

- `results/static_mc_failure_confirmation.json`
- `csv/static_mc_failure_confirmation.csv`
- `csv/static_mc_failure_widths.csv`
- `reports/static_mc_failure_confirmation.md`
- `plots/dnl_seed002_failure_bounds.pdf`

## Reproduction Commands

Run inside `iic-osic-tools_chipathon_xvnc`:

```bash
cd /foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718
python3 scripts/run_static_failure_confirmation.py
PYTHONPATH=scripts python3 scripts/make_static_fail_plots.py
```

Run the final source-integrity and package audit on Windows:

```powershell
python scripts/finalize_static_fail_campaign.py
```

## Entry Points

- `reports/MASTER_SIGNOFF_REPORT.md`
- `reports/final_status.json`
- `reports/completion_audit.json`
- `reports/signoff_matrix.csv`
- `reports/not_run_artifact_matrix.csv`
- `manifests/package_manifest_sha256.csv`

Population completion before gate closure: packed screen `{data['screen_count']}/200`, reconstructed transfer `{data['reconstructed_count']}/200`, full exact validation `0/8`. Targeted exact failure replay is complete and is the basis for `FAIL_DNL`.
""",
    )


def main():
    for directory in (CSV_DIR, REPORT_DIR, RESULT_DIR, ROOT / "manifests"):
        directory.mkdir(parents=True, exist_ok=True)

    source_integrity = foundation.audit_source_integrity()
    if not source_integrity["all_match"]:
        raise RuntimeError("production source integrity changed; FAIL_DNL closure is invalid")

    screen_rows = read_csv(CSV_DIR / "static_mc200_screen_summary.csv")
    reconstructed_rows = read_csv(CSV_DIR / "static_mc200_reconstructed.csv")
    evaluation_rows = read_csv(CSV_DIR / "static_mc_failure_confirmation_evaluations.csv")
    screen_count = len(
        {
            int(row["mismatch_seed"])
            for row in screen_rows
            if 1 <= int(row["mismatch_seed"]) <= 200
        }
    )
    reconstructed_count = len(
        {
            int(row["mismatch_seed"])
            for row in reconstructed_rows
            if 1 <= int(row["mismatch_seed"]) <= 200
        }
    )
    valid_evaluations = sum(row["valid"] == "True" for row in evaluation_rows)

    update_config(screen_count, reconstructed_count)
    event_smoke = audit_event_noise_smoke()
    if event_smoke["status"] != "PASS":
        raise RuntimeError("event-noise syntax smoke evidence is inconsistent")

    data = {
        "numerical": load_json(RESULT_DIR / "numerical_convergence.json"),
        "pvt": load_json(RESULT_DIR / "pvt_screen.json"),
        "exact": load_json(RESULT_DIR / "exact_static.json"),
        "failure": load_json(RESULT_DIR / "static_mc_failure_confirmation.json"),
        "comparator": load_json(RESULT_DIR / "comparator_noise_calibration.json"),
        "sample": load_json(RESULT_DIR / "sample_noise_calibration.json"),
        "plot": load_json(RESULT_DIR / "plot_audit.json"),
        "event_smoke": event_smoke,
        "screen_count": screen_count,
        "reconstructed_count": reconstructed_count,
        "valid_evaluations": valid_evaluations,
    }
    if data["failure"]["status"] != "FAIL_DNL_BOUND":
        raise RuntimeError("decisive exact failure result is absent")
    if data["failure"]["proven_dnl_failure_count"] < 1:
        raise RuntimeError("no conservative DNL failure bound is present")
    if valid_evaluations != len(evaluation_rows):
        raise RuntimeError("not every exact failure evaluation frame is valid")

    write_source_reports(source_integrity)
    not_run_rows = write_not_run_matrix(screen_count, reconstructed_count)
    write_phase_reports(data)
    gates = gate_matrix()
    write_signoff(gates, data, not_run_rows, source_integrity)
    write_readme(data)

    manifest_count = foundation.write_package_manifest()
    print(
        f"STATIC_FAIL_FINAL status={FAILURE_STATUS} source_hashes={source_integrity['record_count']} "
        f"manifest_files={manifest_count}",
        flush=True,
    )


if __name__ == "__main__":
    main()
