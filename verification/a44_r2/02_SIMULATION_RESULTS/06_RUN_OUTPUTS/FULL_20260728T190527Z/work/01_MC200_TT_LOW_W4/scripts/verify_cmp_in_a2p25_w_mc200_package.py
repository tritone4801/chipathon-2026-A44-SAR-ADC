#!/usr/bin/env python3
"""Final consistency verification for the 2.25x LOW W4 MC200 package."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fast64_v2_common import CSV_DIR, MANIFEST_DIR, RESULT_DIR, ROOT, read_csv, sha256_file, write_json_atomic


def load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    status = load("STATUS.json")
    completion = load("results/completion_audit.json")
    setup = load("results/setup_audit.json")
    execution = load("results/execution_audit_mc200_low_w4.json")
    scorecard = load("results/cmp_in_a2p25_w_mc200_scorecard.json")
    formal_plots = load("results/plot_audit_mc200_low_w4.json")
    comparison_plots = load("results/comparison_plot_audit.json")
    visual = load("results/visual_review_cmp_in_a2p25_w_mc200.json")
    frozen = read_csv(MANIFEST_DIR / "input_manifest_sha256.csv")
    frozen_ok = all(
        (ROOT / row["relative_path"]).is_file()
        and sha256_file(ROOT / row["relative_path"]) == row["sha256"]
        for row in frozen
    )
    checks = {
        "delivery_complete": status.get("delivery_status") == "DELIVERY_COMPLETE",
        "execution_complete": execution.get("pass") is True,
        "completion_audit_pass": completion.get("pass") is True,
        "setup_pass": setup.get("pass") is True,
        "candidate_binding_pass": setup.get("candidate_binding_pass") is True,
        "candidate_hash_correct": setup.get("candidate_comparator_sha256")
        == "e30b2055a880b83176f9389c8b79a13201fdd0e689ca46f3dc3f32b19436f303",
        "scorecard_complete": scorecard.get("pass") is True,
        "formal_records_200": len(
            read_csv(CSV_DIR / "steady_state_master_mc200_low_w4.csv")
        )
        == 200,
        "all_codes_13600": len(read_csv(CSV_DIR / "codes_all_13600.csv"))
        == 13_600,
        "retained_codes_12800": len(
            read_csv(CSV_DIR / "codes_fft_retained_12800.csv")
        )
        == 12_800,
        "paired_rows_200": len(
            read_csv(CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv")
        )
        == 200,
        "fixed_step_50ps": status.get("fixed_step_ps") == 50,
        "method_fast64_ss_w4": status.get("steady_state_method_id")
        == "FAST64_SS_W4",
        "frame0_classified": status.get("frame0_status")
        in {
            "PASS_FIRST_CONVERSION_PROTOCOL_POPULATION",
            "FAIL_FIRST_CONVERSION_PROTOCOL_POPULATION",
        },
        "performance_classified": status.get("dynamic_performance_status")
        in {
            "MC200_LOW_W4_PERFORMANCE_PASS",
            "MC200_LOW_W4_PERFORMANCE_FAIL",
        },
        "formal_plot_audit_pass": formal_plots.get("pass") is True,
        "comparison_plot_audit_pass": comparison_plots.get("pass") is True,
        "manual_visual_review_pass": visual.get("pass") is True,
        "frozen_input_manifest_unchanged": frozen_ok,
        "existing_gates_unchanged_fail": status.get(
            "existing_block_and_four_phase_gates"
        )
        == "UNCHANGED_FAIL",
        "promotion_not_claimed": status.get("promotion_status") == "NOT_PROMOTED",
        "signoff_not_claimed": status.get("signoff_status")
        == "SIGNOFF_NOT_CLAIMED",
    }
    failures = [name for name, value in checks.items() if not value]
    payload = {
        "status": (
            "PASS_FINAL_PACKAGE_VERIFICATION"
            if not failures
            else "FAIL_FINAL_PACKAGE_VERIFICATION"
        ),
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "performance_is_classification_not_completion_gate": True,
        "frame0_is_classification_not_completion_gate": True,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(RESULT_DIR / "final_verification.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
