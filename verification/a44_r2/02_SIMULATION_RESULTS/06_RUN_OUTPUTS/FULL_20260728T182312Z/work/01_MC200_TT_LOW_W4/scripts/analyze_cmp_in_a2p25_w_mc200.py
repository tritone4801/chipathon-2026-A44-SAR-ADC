#!/usr/bin/env python3
"""Paired baseline/candidate analysis for the 2.25x LOW W4 MC200."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from fast64_v2_common import (
    CSV_DIR,
    RESULT_DIR,
    ROOT,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


BASELINE_DIR = ROOT / "references/baseline_mc200_low_w4"
EXPECTED_SEEDS = set(range(1, 201))


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q, method="linear"))


def metric_percentiles(
    rows: dict[int, dict[str, str]], field: str
) -> dict[str, float]:
    values = [float(rows[seed][field]) for seed in sorted(rows)]
    return {
        f"P{q}": percentile(values, q)
        for q in (0, 1, 5, 10, 50, 90, 95, 99, 100)
    }


def main() -> int:
    candidate_rows = {
        int(row["mismatch_seed"]): row
        for row in read_csv(CSV_DIR / "steady_state_master_mc200_low_w4.csv")
    }
    baseline_rows = {
        int(row["mismatch_seed"]): row
        for row in read_csv(BASELINE_DIR / "steady_state_master_mc200_low_w4.csv")
    }
    candidate_codes = {
        (int(row["mismatch_seed"]), int(row["frame_index"])): row
        for row in read_csv(CSV_DIR / "codes_all_13600.csv")
    }
    baseline_codes = {
        (int(row["mismatch_seed"]), int(row["frame_index"])): row
        for row in read_csv(BASELINE_DIR / "codes_all_13600.csv")
    }
    failures: list[dict[str, object]] = []
    if set(candidate_rows) != EXPECTED_SEEDS:
        failures.append(
            {
                "gate": "CANDIDATE_SEED_SET",
                "observed": sorted(candidate_rows),
            }
        )
    if set(baseline_rows) != EXPECTED_SEEDS:
        failures.append(
            {
                "gate": "BASELINE_SEED_SET",
                "observed": sorted(baseline_rows),
            }
        )
    if len(candidate_codes) != 13_600:
        failures.append(
            {"gate": "CANDIDATE_CODE_ROWS", "observed": len(candidate_codes)}
        )
    if len(baseline_codes) != 13_600:
        failures.append(
            {"gate": "BASELINE_CODE_ROWS", "observed": len(baseline_codes)}
        )
    if failures:
        write_json_atomic(
            RESULT_DIR / "cmp_in_a2p25_w_mc200_scorecard.json",
            {
                "status": "ANALYSIS_BLOCKED_INCOMPLETE_INPUT",
                "pass": False,
                "failures": failures,
                "checked_utc": utc_now(),
            },
        )
        return 2

    paired: list[dict[str, object]] = []
    candidate_frame0_failures: list[int] = []
    candidate_frame0_same_phase_code_mismatches: list[int] = []
    mismatch_input_match_count = 0
    noise_input_match_count = 0

    for seed in range(1, 201):
        baseline = baseline_rows[seed]
        candidate = candidate_rows[seed]
        all_differing = [
            frame
            for frame in range(68)
            if int(baseline_codes[(seed, frame)]["code"])
            != int(candidate_codes[(seed, frame)]["code"])
        ]
        retained_differing = [frame for frame in all_differing if 4 <= frame <= 67]
        baseline_hard = truth(baseline["steady_state_hard_dynamic_pass"])
        candidate_hard = truth(candidate["steady_state_hard_dynamic_pass"])
        baseline_budget = truth(baseline["steady_state_snr_budget_pass"])
        candidate_budget = truth(candidate["steady_state_snr_budget_pass"])
        candidate_frame0 = truth(candidate["first_conversion_protocol_pass"])
        if not candidate_frame0:
            candidate_frame0_failures.append(seed)
        if int(candidate_codes[(seed, 0)]["code"]) != int(
            candidate_codes[(seed, 64)]["code"]
        ):
            candidate_frame0_same_phase_code_mismatches.append(seed)
        if candidate["mismatch_checksum"] == baseline["mismatch_checksum"]:
            mismatch_input_match_count += 1
        if (
            candidate["noise_prefix_checksum_0_63"]
            == baseline["noise_prefix_checksum_0_63"]
        ):
            noise_input_match_count += 1
        paired.append(
            {
                "mismatch_seed": seed,
                "noise_seed": int(candidate["noise_seed"]),
                "baseline_w4_snr_db": float(baseline["steady_state_snr_db"]),
                "candidate_w4_snr_db": float(candidate["steady_state_snr_db"]),
                "delta_snr_db": float(candidate["steady_state_snr_db"])
                - float(baseline["steady_state_snr_db"]),
                "baseline_w4_sndr_db": float(baseline["steady_state_sndr_db"]),
                "candidate_w4_sndr_db": float(candidate["steady_state_sndr_db"]),
                "delta_sndr_db": float(candidate["steady_state_sndr_db"])
                - float(baseline["steady_state_sndr_db"]),
                "baseline_w4_enob_raw": float(baseline["steady_state_enob_raw"]),
                "candidate_w4_enob_raw": float(candidate["steady_state_enob_raw"]),
                "delta_enob_raw": float(candidate["steady_state_enob_raw"])
                - float(baseline["steady_state_enob_raw"]),
                "baseline_w4_sfdr_dbc": float(baseline["steady_state_sfdr_dbc"]),
                "candidate_w4_sfdr_dbc": float(candidate["steady_state_sfdr_dbc"]),
                "delta_sfdr_dbc": float(candidate["steady_state_sfdr_dbc"])
                - float(baseline["steady_state_sfdr_dbc"]),
                "baseline_hard_dynamic_pass": baseline_hard,
                "candidate_hard_dynamic_pass": candidate_hard,
                "hard_dynamic_recovered": (not baseline_hard) and candidate_hard,
                "hard_dynamic_regressed": baseline_hard and (not candidate_hard),
                "baseline_snr_budget_pass": baseline_budget,
                "candidate_snr_budget_pass": candidate_budget,
                "candidate_first_conversion_protocol_pass": candidate_frame0,
                "baseline_first_conversion_code": int(
                    baseline_codes[(seed, 0)]["code"]
                ),
                "candidate_first_conversion_code": int(
                    candidate_codes[(seed, 0)]["code"]
                ),
                "candidate_same_phase_frame64_code": int(
                    candidate_codes[(seed, 64)]["code"]
                ),
                "all_code_exact": not all_differing,
                "all_differing_frame_count": len(all_differing),
                "all_differing_frames": "/".join(map(str, all_differing)),
                "retained_code_exact": not retained_differing,
                "retained_differing_frame_count": len(retained_differing),
                "retained_differing_frames": "/".join(
                    map(str, retained_differing)
                ),
                "mismatch_checksum_match": (
                    candidate["mismatch_checksum"] == baseline["mismatch_checksum"]
                ),
                "noise_prefix_checksum_match": (
                    candidate["noise_prefix_checksum_0_63"]
                    == baseline["noise_prefix_checksum_0_63"]
                ),
            }
        )

    write_csv_atomic(
        CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv", paired
    )
    candidate_hard_count = sum(
        truth(row["steady_state_hard_dynamic_pass"])
        for row in candidate_rows.values()
    )
    baseline_hard_count = sum(
        truth(row["steady_state_hard_dynamic_pass"])
        for row in baseline_rows.values()
    )
    candidate_budget_count = sum(
        truth(row["steady_state_snr_budget_pass"])
        for row in candidate_rows.values()
    )
    baseline_budget_count = sum(
        truth(row["steady_state_snr_budget_pass"])
        for row in baseline_rows.values()
    )
    recovered = [
        int(row["mismatch_seed"]) for row in paired if row["hard_dynamic_recovered"]
    ]
    regressed = [
        int(row["mismatch_seed"]) for row in paired if row["hard_dynamic_regressed"]
    ]
    deltas = [float(row["delta_sndr_db"]) for row in paired]
    negative_delta_rows = [
        row for row in paired if float(row["delta_sndr_db"]) < 0.0
    ]
    baseline_fail_deltas = [
        float(row["delta_sndr_db"])
        for row in paired
        if not bool(row["baseline_hard_dynamic_pass"])
    ]
    minimum_delta_row = min(
        paired,
        key=lambda row: (float(row["delta_sndr_db"]), int(row["mismatch_seed"])),
    )
    data_complete = all(
        (
            len(candidate_rows) == 200,
            len(candidate_codes) == 13_600,
            mismatch_input_match_count == 200,
            noise_input_match_count == 200,
        )
    )
    performance_pass = candidate_hard_count >= 190
    frame0_pass = not candidate_frame0_failures
    scorecard = {
        "campaign": ROOT.name,
        "candidate_id": "CMP_IN_A2P25_W",
        "width_multiplier": 2.25,
        "scope": "MC200_LOW_ONLY",
        "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        "steady_state_method_id": "FAST64_SS_W4",
        "fixed_step_ps": 50,
        "population_count": 200,
        "data_complete": data_complete,
        "input_pairing": {
            "mismatch_checksum_match_count": mismatch_input_match_count,
            "noise_prefix_checksum_match_count": noise_input_match_count,
            "pass": mismatch_input_match_count == 200
            and noise_input_match_count == 200,
        },
        "frame0": {
            "status": (
                "PASS_FIRST_CONVERSION_PROTOCOL_POPULATION"
                if frame0_pass
                else "FAIL_FIRST_CONVERSION_PROTOCOL_POPULATION"
            ),
            "pass": frame0_pass,
            "pass_count": 200 - len(candidate_frame0_failures),
            "fail_count": len(candidate_frame0_failures),
            "failure_seeds": candidate_frame0_failures,
            "frame0_frame64_code_mismatch_count_diagnostic_only": len(
                candidate_frame0_same_phase_code_mismatches
            ),
            "frame0_frame64_code_mismatch_seeds_diagnostic_only": (
                candidate_frame0_same_phase_code_mismatches
            ),
        },
        "performance": {
            "status": (
                "MC200_LOW_W4_PERFORMANCE_PASS"
                if performance_pass
                else "MC200_LOW_W4_PERFORMANCE_FAIL"
            ),
            "pass": performance_pass,
            "required_hard_pass_count": 190,
            "baseline_hard_dynamic_pass_count": baseline_hard_count,
            "candidate_hard_dynamic_pass_count": candidate_hard_count,
            "baseline_snr_budget_pass_count": baseline_budget_count,
            "candidate_snr_budget_pass_count": candidate_budget_count,
            "hard_dynamic_recovered_count": len(recovered),
            "hard_dynamic_recovered_seeds": recovered,
            "hard_dynamic_regressed_count": len(regressed),
            "hard_dynamic_regressed_seeds": regressed,
            "median_delta_sndr_db": float(np.median(deltas)),
            "baseline_fail_median_delta_sndr_db": float(
                np.median(baseline_fail_deltas)
            ),
            "negative_delta_seed_count": len(negative_delta_rows),
            "minimum_delta_sndr_db": float(minimum_delta_row["delta_sndr_db"]),
            "minimum_delta_seed": int(minimum_delta_row["mismatch_seed"]),
        },
        "candidate_percentiles": {
            metric: metric_percentiles(candidate_rows, field)
            for metric, field in (
                ("SNR_dB", "steady_state_snr_db"),
                ("SNDR_dB", "steady_state_sndr_db"),
                ("ENOB_raw_bit", "steady_state_enob_raw"),
                ("SFDR_dBc", "steady_state_sfdr_dbc"),
            )
        },
        "baseline_percentiles": {
            metric: metric_percentiles(baseline_rows, field)
            for metric, field in (
                ("SNR_dB", "steady_state_snr_db"),
                ("SNDR_dB", "steady_state_sndr_db"),
                ("ENOB_raw_bit", "steady_state_enob_raw"),
                ("SFDR_dBc", "steady_state_sfdr_dbc"),
            )
        },
        "code_comparison": {
            "all_68_code_exact_seed_count": sum(
                bool(row["all_code_exact"]) for row in paired
            ),
            "retained_64_code_exact_seed_count": sum(
                bool(row["retained_code_exact"]) for row in paired
            ),
            "comparison_is_performance_diagnostic_not_equivalence_gate": True,
        },
        "status": (
            "COMPLETE_MC200_LOW_W4_PERFORMANCE_MEASUREMENT"
            if data_complete
            else "INCOMPLETE_MC200_LOW_W4_PERFORMANCE_MEASUREMENT"
        ),
        "pass": data_complete,
        "non_claims": [
            "LOW-only MC200 is not a LOW/NEAR two-band die-level yield.",
            "Frame0 remains an independent protocol/path gate and is excluded from the W4 FFT.",
            "Paired code differences are expected for a changed DUT and are not an equivalence failure.",
            "Performance completion does not close existing block or nominal four-phase gates.",
            "No layout, PEX, silicon, tapeout, production-yield, or signoff claim is made.",
        ],
        "checked_utc": utc_now(),
    }
    write_json_atomic(
        RESULT_DIR / "cmp_in_a2p25_w_mc200_scorecard.json", scorecard
    )
    print(json.dumps(scorecard, indent=2, sort_keys=True))
    return 0 if data_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
