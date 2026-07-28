#!/usr/bin/env python3
"""Read-only consistency and hash audit for the closed campaign package."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SAR_CURRENT = (
    Path("/foss/designs/manual_goal/analog/SAR_CURRENT")
    if os.name != "nt"
    else Path(r"C:\Users\15031\eda\designs\manual_goal\analog\SAR_CURRENT")
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="ascii"))


def csv_rows(relative: str) -> list[dict]:
    with (ROOT / relative).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    manifest_rows = csv_rows("manifests/package_manifest_sha256.csv")
    mismatches = []
    for row in manifest_rows:
        path = ROOT / Path(row["relative_path"])
        if not path.is_file():
            mismatches.append({"path": row["relative_path"], "reason": "MISSING"})
        elif path.stat().st_size != int(row["size_bytes"]):
            mismatches.append({"path": row["relative_path"], "reason": "SIZE"})
        elif sha256(path) != row["sha256"]:
            mismatches.append({"path": row["relative_path"], "reason": "SHA256"})
    check("package_manifest_hashes", not mismatches, {"records": len(manifest_rows), "mismatches": mismatches})

    required = [
        "README.md",
        "config/run_config.yaml",
        "config/timing_tt_3p3_27c.json",
        "config/source_load_model.yaml",
        "config/cdac_mismatch_model.yaml",
        "config/noise_model.yaml",
        "config/mc_seeds.csv",
        "config/noise_seeds.csv",
        "models/SAR_LOGIC_BEH_TT_3P3_27C.v",
        "models/SAR_LOGIC_BEH_TT_3P3_27C.so",
        "netlists/SAR_ADC_ANALOG_CORE_TT_BEH_NO_R6.spice",
        "reports/00_executive_summary.md",
        "reports/01_source_integrity.md",
        "reports/02_model_and_fixture_audit.md",
        "reports/03_numerical_convergence.md",
        "reports/04_pvt_screen.md",
        "reports/05_static_exact.md",
        "reports/06_static_mc200.md",
        "reports/07_noise_calibration.md",
        "reports/08_dynamic_mc200_fast64.md",
        "reports/09_fast256_closure.md",
        "reports/10_pvt_mc_interaction.md",
        "reports/11_plot_audit.md",
        "reports/12_signoff_matrix.md",
        "reports/MASTER_SIGNOFF_REPORT.md",
        "reports/final_status.json",
        "reports/completion_audit.json",
        "reports/not_run_artifact_matrix.csv",
        "manifests/source_hashes_before.json",
        "manifests/source_hashes_after.json",
        "manifests/source_hash_comparison.csv",
    ]
    missing_required = [relative for relative in required if not (ROOT / relative).is_file()]
    check("required_blocked_closure_artifacts", not missing_required, missing_required)

    final_status = load_json("reports/final_status.json")
    completion = load_json("reports/completion_audit.json")
    signoff = load_json("reports/signoff_matrix.json")
    check(
        "terminal_status_consistency",
        final_status["status"] == completion["campaign_status"] == signoff["final_status"] == "BLOCKED",
        {"final": final_status["status"], "completion": completion["campaign_status"], "matrix": signoff["final_status"]},
    )
    check(
        "pass_label_not_issued",
        final_status["label"] is None and not final_status["pass_label_issued"] and not completion["pass_label_issued"],
        {"label": final_status["label"], "issued": final_status["pass_label_issued"]},
    )
    check(
        "blocking_statuses_exact",
        final_status["blocking_statuses"]
        == ["BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE", "BLOCKED_NOISE_CALIBRATION_UNAVAILABLE"],
        final_status["blocking_statuses"],
    )
    check(
        "signoff_definition_of_done_not_overclaimed",
        not completion["document_signoff_definition_of_done_met"] and completion["closure_complete_as_blocked_stop"],
        {
            "signoff_dod": completion["document_signoff_definition_of_done_met"],
            "blocked_closure": completion["closure_complete_as_blocked_stop"],
        },
    )

    behavior = load_json("reports/behavioral_contract_smoke.json")
    faults = load_json("reports/fault_flag_smoke.json")
    implementation = load_json("reports/behavioral_implementation_audit.json")
    check("behavioral_contract", behavior["status"] == "PASS" and behavior["cases_passed"] == 11, behavior)
    check("fault_contract", faults["status"] == "PASS" and faults["cases_passed"] == 3, faults)
    check("behavioral_build_and_unit", implementation["status"] == "PASS", implementation["status"])

    mos = load_json("reports/mos_mismatch_sanity.json")
    model_response = all(
        row["mismatch_off_collapses"]
        and row["mismatch_on_nonzero"]
        and row["area_scaling_ratio_ok"]
        and row["x2_scaling_ratio_ok"]
        and row["mean_physically_plausible"]
        for row in mos["checks"]
    )
    seed_failed = all(not row["seed_reproducible"] for row in mos["checks"])
    check("mos_response_and_seed_failure_preserved", mos["status"] == "FAIL" and model_response and seed_failed, mos["checks"])

    mc_seeds = csv_rows("config/mc_seeds.csv")
    noise_seeds = csv_rows("config/noise_seeds.csv")
    check(
        "frozen_seed_tables",
        len(mc_seeds) == 200
        and len(noise_seeds) == 200
        and [int(row["mismatch_seed"]) for row in mc_seeds] == list(range(1, 201))
        and [int(row["noise_seed"]) for row in noise_seeds] == list(range(100001, 100201)),
        {"mc": len(mc_seeds), "noise": len(noise_seeds)},
    )

    not_run = csv_rows("reports/not_run_artifact_matrix.csv")
    accidental_outputs = [row["artifact"] for row in not_run if (ROOT / row["artifact"]).exists()]
    bad_not_run_rows = [row for row in not_run if row["status"] != "NOT_RUN_GATED" or row["fabricated_placeholder_created"] != "false"]
    check("no_fabricated_downstream_artifacts", not accidental_outputs and not bad_not_run_rows, {"existing": accidental_outputs, "bad_rows": bad_not_run_rows})
    check("mc200_jobs_not_launched", completion["mc200_jobs_launched"] == 0, completion["mc200_jobs_launched"])

    source_comparison = csv_rows("manifests/source_hash_comparison.csv")
    source_bad = [row for row in source_comparison if row["status"] != "MATCH"]
    check("recorded_production_source_integrity", not source_bad and len(source_comparison) == 113, {"records": len(source_comparison), "bad": source_bad})
    live_bad = []
    for row in source_comparison:
        path = SAR_CURRENT / Path(row["relative_path"])
        if not path.is_file() or sha256(path) != row["before_sha256"]:
            live_bad.append(row["relative_path"])
    check("live_production_source_integrity", not live_bad, live_bad)

    reference_snapshot = load_json("manifests/reference_input_snapshot.json")
    check(
        "missing_references_explicit",
        reference_snapshot["missing_reference_inputs"] == ["try_PERFORMANCE.txt", "read_measurement_definitions.txt"],
        reference_snapshot["missing_reference_inputs"],
    )

    gate_map = {row["gate"]: row["status"] for row in signoff["gates"]}
    check(
        "gate_matrix_consistency",
        gate_map == {
            "A": "PASS",
            "B": "PASS",
            "C": "NOT_RUN_GATED",
            "D": "NOT_RUN_GATED",
            "E": "BLOCKED",
            "F": "BLOCKED",
            "G": "NOT_RUN_GATED",
            "H": "NOT_RUN_GATED",
            "I": "NOT_RUN_GATED",
            "J": "BLOCKED",
        },
        gate_map,
    )

    failed = [row for row in checks if row["status"] != "PASS"]
    result = {
        "status": "PASS" if not failed else "FAIL",
        "campaign_terminal_status": "BLOCKED",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "package_manifest_records": len(manifest_rows),
        "checks": checks,
    }
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
