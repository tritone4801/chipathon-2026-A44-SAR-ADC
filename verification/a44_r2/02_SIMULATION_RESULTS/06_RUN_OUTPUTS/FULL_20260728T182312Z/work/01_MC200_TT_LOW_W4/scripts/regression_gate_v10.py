#!/usr/bin/env python3
"""Strict per-record comparison gate for the MC10 V10 regression."""


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def comparison_row_pass(row):
    """Return True only when every strict comparison condition passes."""
    return all(
        (
            as_bool(row["state_match"]),
            as_bool(row["hard_pass_match"]),
            as_bool(row["mismatch_checksum_match"]),
            as_bool(row["noise_checksum_match"]),
            as_bool(row["code_checksum_match"]),
            abs(float(row["delta_sndr_db"])) <= 0.10,
            abs(float(row["delta_snr_db"])) <= 0.20,
            abs(float(row["delta_enob_bit"])) <= 0.02,
        )
    )


def comparisons_pass(rows, expected_count):
    """Apply the strict gate to every row and require exact completeness."""
    return len(rows) == expected_count and all(
        comparison_row_pass(row) for row in rows
    )


def run_self_test():
    passing = {
        "state_match": True,
        "hard_pass_match": True,
        "mismatch_checksum_match": True,
        "noise_checksum_match": True,
        "code_checksum_match": True,
        "delta_sndr_db": 0.10,
        "delta_snr_db": -0.20,
        "delta_enob_bit": 0.02,
    }
    known_v8_failure = {
        **passing,
        "state_match": False,
        "hard_pass_match": False,
        "code_checksum_match": False,
        "delta_sndr_db": 16.381362206782768,
        "delta_snr_db": 16.84226431060022,
        "delta_enob_bit": 2.7211565127546136,
    }
    cases = {
        "single_passing_row": comparisons_pass([passing], 1),
        "known_v8_mismatch_rejected": not comparisons_pass(
            [known_v8_failure], 1
        ),
        "incomplete_set_rejected": not comparisons_pass([passing], 2),
        "code_mismatch_rejected": not comparisons_pass(
            [{**passing, "code_checksum_match": False}], 1
        ),
        "metric_mismatch_rejected": not comparisons_pass(
            [{**passing, "delta_sndr_db": 0.100001}], 1
        ),
    }
    return {
        "pass": all(cases.values()),
        "cases": cases,
        "known_v8_failure": known_v8_failure,
    }
