#!/usr/bin/env python3
"""Freeze the seed-116 baseline-vs-A2P25 paired static campaign."""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT.name
SEED = 116
HISTORICAL_CAMPAIGN = "A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
BASELINE = ROOT / "netlists" / "baseline" / "Comparator_StrongARM_extracted.subckt.spice"
CANDIDATE = (
    ROOT
    / "netlists"
    / "candidate"
    / "Comparator_StrongARM_CMP_IN_A2P25_W.subckt.spice"
)
HISTORICAL_SUMMARY = (
    ROOT
    / "references"
    / "historical_selection"
    / "static_mc200_reconstructed_summary.csv"
)
HISTORICAL_EXACT = (
    ROOT
    / "references"
    / "historical_selection"
    / "static_mc_exact_validation.csv"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def logical_statements(text: str) -> list[list[str]]:
    statements: list[list[str]] = []
    for line in text.splitlines():
        if line.startswith("+") and statements:
            statements[-1].append(line)
        else:
            statements.append([line])
    return statements


def statement_name(statement: list[str]) -> str:
    tokens = statement[0].strip().split()
    return tokens[0].upper() if tokens else ""


def normalized_resized_statement(text: str) -> str:
    return re.sub(r"(?i)\bW=3\.51u\b", "W=1.56u", text)


def comparator_diff_audit() -> dict[str, Any]:
    baseline_text = BASELINE.read_text(encoding="utf-8")
    candidate_text = CANDIDATE.read_text(encoding="utf-8")
    baseline_statements = {
        statement_name(statement): "\n".join(statement)
        for statement in logical_statements(baseline_text)
        if statement_name(statement).startswith("XM")
    }
    candidate_statements = {
        statement_name(statement): "\n".join(statement)
        for statement in logical_statements(candidate_text)
        if statement_name(statement).startswith("XM")
    }
    names_identical = list(baseline_statements) == list(candidate_statements)
    changed = []
    unexpected = []
    for name, old in baseline_statements.items():
        new = candidate_statements.get(name)
        if new != old:
            changed.append(name)
        if name in {"XM3", "XM4"}:
            if new is None or normalized_resized_statement(new) != old:
                unexpected.append(name)
        elif new != old:
            unexpected.append(name)
    baseline_w = {
        name: re.findall(r"(?i)\bW=([0-9.]+u)\b", baseline_statements[name])[0]
        for name in ("XM3", "XM4")
    }
    candidate_w = {
        name: re.findall(r"(?i)\bW=([0-9.]+u)\b", candidate_statements[name])[0]
        for name in ("XM3", "XM4")
    }
    diff = "\n".join(
        difflib.unified_diff(
            baseline_text.splitlines(),
            candidate_text.splitlines(),
            fromfile=str(BASELINE.relative_to(ROOT)),
            tofile=str(CANDIDATE.relative_to(ROOT)),
            lineterm="",
        )
    )
    (ROOT / "candidate_netlist_diff.txt").write_text(
        diff + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "status": (
            "PASS"
            if names_identical
            and changed == ["XM3", "XM4"]
            and not unexpected
            and set(baseline_w.values()) == {"1.56u"}
            and set(candidate_w.values()) == {"3.51u"}
            else "FAIL"
        ),
        "independent_design_variable": "XM3/XM4 requested W only",
        "permitted_derived_changes": [
            "geometry-derived capacitance/current/gm",
            "geometry-dependent mismatch sigma",
            "AD/AS/PD/PS/NRD/NRS expressions evaluated from W",
        ],
        "changed_instances": changed,
        "unexpected_instances": unexpected,
        "instance_order_identical": names_identical,
        "baseline_widths": baseline_w,
        "candidate_widths": candidate_w,
        "baseline_sha256": sha256(BASELINE),
        "candidate_sha256": sha256(CANDIDATE),
    }


def seed_provenance() -> dict[str, Any]:
    with HISTORICAL_SUMMARY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: float(row["max_abs_dnl_lsb"]))
    position = 0.95 * (len(rows) - 1)
    lower_index = int(position)
    upper_index = lower_index if position.is_integer() else lower_index + 1
    fraction = position - lower_index
    lower_value = float(rows[lower_index]["max_abs_dnl_lsb"])
    upper_value = float(rows[upper_index]["max_abs_dnl_lsb"])
    p95_value = lower_value + fraction * (upper_value - lower_value)
    selected_index = next(
        index for index, row in enumerate(rows) if int(row["mismatch_seed"]) == SEED
    )
    selected = rows[selected_index]
    with HISTORICAL_EXACT.open(encoding="utf-8-sig", newline="") as handle:
        exact_rows = list(csv.DictReader(handle))
    exact = next(row for row in exact_rows if int(row["mismatch_seed"]) == SEED)
    return {
        "status": "PASS",
        "selection_label": (
            "HISTORICAL_P95_MAX_ABS_DNL_EP_NEAREST_OBSERVED_REPRESENTATIVE"
        ),
        "historical_campaign_id": HISTORICAL_CAMPAIGN,
        "source_file": str(HISTORICAL_SUMMARY.relative_to(ROOT)),
        "source_file_sha256": sha256(HISTORICAL_SUMMARY),
        "population_size": len(rows),
        "selection_metric": "max_abs_dnl_lsb",
        "selection_metric_definition": (
            "maximum absolute endpoint-referenced DNL from historical "
            "reconstructed MC200 summary"
        ),
        "inl_reference_method": "endpoint",
        "percentile_algorithm": "numpy linear default equivalent",
        "percentile": 95,
        "percentile_zero_based_position": position,
        "lower_order_seed": int(rows[lower_index]["mismatch_seed"]),
        "lower_order_value_lsb": lower_value,
        "upper_order_seed": int(rows[upper_index]["mismatch_seed"]),
        "upper_order_value_lsb": upper_value,
        "historical_p95_value_lsb": p95_value,
        "selected_seed": SEED,
        "selected_seed_rank_ascending": selected_index + 1,
        "selected_seed_metric_value_lsb": float(selected["max_abs_dnl_lsb"]),
        "distance_to_historical_p95_lsb": abs(
            float(selected["max_abs_dnl_lsb"]) - p95_value
        ),
        "historical_result_type": "RECONSTRUCTED_POPULATION",
        "exact_validation_file": str(HISTORICAL_EXACT.relative_to(ROOT)),
        "exact_validation_file_sha256": sha256(HISTORICAL_EXACT),
        "exact_validation": {
            "max_abs_dnl_lsb": float(exact["exact_max_abs_dnl_lsb"]),
            "max_abs_inl_endpoint_lsb": float(
                exact["exact_max_abs_inl_endpoint_lsb"]
            ),
            "missing_codes": int(exact["exact_missing_codes"]),
            "search_status": exact["exact_search_status"],
            "validation_status": exact["validation_status"],
        },
        "nonclaims": [
            "seed 116 is not a universal P95 for every static metric",
            "the current experiment does not remeasure a population percentile",
        ],
    }


def dependency_manifest() -> list[dict[str, Any]]:
    roots = [
        ROOT / "scripts",
        ROOT / "config",
        ROOT / "csv" / "cdac_mismatch_weights.csv",
        ROOT / "models",
        ROOT / "netlists",
        ROOT / "references",
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(path for path in root.rglob("*") if path.is_file())
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(set(files))
        if "__pycache__" not in path.parts
    ]


def main() -> None:
    diff_audit = comparator_diff_audit()
    provenance = seed_provenance()
    write_json(ROOT / "results" / "netlist_diff_audit.json", diff_audit)
    write_json(ROOT / "config" / "seed116_selection_provenance.json", provenance)
    contract = {
        "campaign": CAMPAIGN,
        "created_utc": utc_now(),
        "objective": (
            "full-code paired static comparison of baseline and A2P25 at one "
            "historically selected upper-tail realization"
        ),
        "evidence_class": (
            "STATIC_TT_PAIRED_HISTORICAL_P95_SELECTION_CASE_S116"
        ),
        "selection_role": provenance["selection_label"],
        "dut_variants": {
            "BASELINE": {
                "comparator": str(BASELINE.relative_to(ROOT)),
                "xm3_xm4_requested_w_um": 1.56,
            },
            "A2P25": {
                "comparator": str(CANDIDATE.relative_to(ROOT)),
                "xm3_xm4_requested_w_um": 3.51,
            },
        },
        "common_conditions": {
            "pvt": "TT_3P3_27C",
            "vdd_v": 3.3,
            "temperature_c": 27,
            "mismatch_seed": SEED,
            "temporal_event_noise": "OFF",
            "direction": "UPWARD_ONLY",
            "full_scale_diff_v": 3.4,
            "nominal_lsb_diff_v": 3.4 / 256.0,
            "vid_search_range_v": [-1.8, 1.8],
        },
        "search": {
            "transitions": list(range(1, 256)),
            "anchors": [1, 128, 255],
            "initial_half_bracket_lsb": 0.75,
            "expansion_half_width_lsb": [2, 4, 8, 16],
            "threshold_precision_lsb": 0.02,
            "bulk_maxstep_ps": 50,
            "frame_period_ns": 500,
            "primary_frame_method": "FRAME0_CONDITIONING_FRAME1_FORMAL",
            "fallback_frame_method": (
                "FRAME0_COLD_DISCARD_FRAME1_CONDITIONING_FRAME2_FORMAL"
            ),
        },
        "protocol": {
            "comparator_decisions": 8,
            "physical_cdac_updates": 7,
            "complete": 1,
            "invalid": 0,
            "timeout": 0,
            "dout_stable_window_ns": [470, 480],
        },
        "required_measurements_per_dut": {
            "full_upward_transitions": 255,
            "internal_midpoint_decodes": 254,
            "overrange_points": [-1.8, 1.8],
            "upward_ramp_points": 1089,
        },
        "ramp": {
            "role": "UPWARD_SEQUENCE_AND_COVERAGE_CORRELATION",
            "start_vid_v": -1.8,
            "end_vid_v": 1.8,
            "points": 1089,
            "step_v": 3.6 / 1088.0,
            "formal_dnl_inl_source": False,
        },
        "absolute_gates": {
            "dnl_endpoint_open_interval_lsb": [-1.0, 1.0],
            "max_abs_inl_endpoint_lsb": 1.5,
            "missing_code_count": 0,
            "threshold_order_error_count": 0,
            "midpoint_decode_error_count": 0,
            "unresolved_transition_count": 0,
            "protocol_failure_count": 0,
            "endpoint_codes_reachable": True,
        },
        "excluded_by_user": {
            "symmetric_strict_replay": True,
            "dense_scan": True,
            "strict_replay_maxstep_ps": None,
        },
        "forbidden_claims": [
            "nominal performance",
            "current population P95",
            "Monte Carlo pass rate",
            "production yield",
        ],
    }
    write_json(ROOT / "config" / "paired_static_contract.json", contract)
    ramp_contract = {
        "campaign": CAMPAIGN,
        "role": contract["ramp"]["role"],
        "vid_formula": "-1.8 + j*(3.6/1088), j=0..1088",
        "points": 1089,
        "noise": "OFF",
        "direction": "UPWARD_ONLY",
        "startup": "one cold-start frame at -1.8 V",
        "per_point_frames": contract["search"]["primary_frame_method"],
        "dout_aperture_ns": 480,
        "correlation_tolerance": (
            "ramp step plus exact transition bracket uncertainty"
        ),
        "formal_dnl_inl_source": False,
    }
    write_json(ROOT / "config" / "ramp_contract.json", ramp_contract)
    dependencies = dependency_manifest()
    write_json(
        ROOT / "config" / "dependency_hashes.json",
        {
            "generated_utc": utc_now(),
            "file_count": len(dependencies),
            "files": dependencies,
        },
    )
    initial_status = {
        "campaign": CAMPAIGN,
        "updated_utc": utc_now(),
        "state": "SETUP_COMPLETE_AWAITING_QUALIFICATION",
        "setup_pass": diff_audit["status"] == "PASS"
        and provenance["status"] == "PASS",
        "full_curve_execution_complete": False,
        "paired_effect_status": "NOT_EVALUATED",
        "excluded_by_user": [
            "symmetric strict replay",
            "dense scan",
        ],
        "nonclaims": contract["forbidden_claims"],
    }
    write_json(ROOT / "STATUS.json", initial_status)
    if not initial_status["setup_pass"]:
        raise SystemExit("setup audit failed")
    print(json.dumps(initial_status, indent=2))


if __name__ == "__main__":
    main()
