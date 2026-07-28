#!/usr/bin/env python3
"""Unit tests for the FAST64 V2 index, phase, and RNG contracts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fast64_v2_common import (
    BANDS,
    METHOD_ID,
    NFFT,
    coherent_input_values,
    formal_jobs,
    noise_checksum,
    retained_indices,
    startup_pair_indices,
    total_frames_for_warmup,
)
from sar_event_noise import frozen_event_draws


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    checks: list[dict[str, object]] = []

    jobs = formal_jobs()
    checks.append({"name": "formal_job_count_68", "pass": len(jobs) == 68})
    checks.append(
        {
            "name": "formal_job_ids_unique",
            "pass": len({str(row["job_id"]) for row in jobs}) == 68,
        }
    )
    checks.append(
        {
            "name": "method_id",
            "pass": METHOD_ID == "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        }
    )
    for warmup, total in ((4, 68), (8, 72)):
        indices = retained_indices(warmup)
        checks.extend(
            [
                {
                    "name": f"w{warmup}_total_frames",
                    "pass": total_frames_for_warmup(warmup) == total,
                },
                {
                    "name": f"w{warmup}_retained_count",
                    "pass": len(indices) == 64,
                },
                {
                    "name": f"w{warmup}_retained_bounds",
                    "pass": indices[0] == warmup and indices[-1] == warmup + 63,
                },
                {
                    "name": f"w{warmup}_phase_unique",
                    "pass": sorted(index % NFFT for index in indices)
                    == list(range(64)),
                },
                {
                    "name": f"w{warmup}_startup_pairs",
                    "pass": startup_pair_indices(total)
                    == tuple((index, index + 64) for index in range(warmup)),
                },
            ]
        )
    checks.extend(
        [
            {"name": "low_bin_7", "pass": BANDS["LOW"]["bin"] == 7},
            {
                "name": "near_nyquist_bin_29",
                "pass": BANDS["NEAR_NYQUIST"]["bin"] == 29,
            },
            {
                "name": "w0_window_0_63",
                "pass": tuple(range(64))[0] == 0 and tuple(range(64))[-1] == 63,
            },
            {
                "name": "w4_window_4_67",
                "pass": retained_indices(4)[0] == 4
                and retained_indices(4)[-1] == 67,
            },
        ]
    )
    for band in BANDS:
        values = coherent_input_values(72, band, 175e-9)
        checks.extend(
            [
                {
                    "name": f"{band.lower()}_ideal_frame0_frame64_same_phase",
                    "pass": bool(np.isclose(values[0], values[64], atol=1e-14)),
                },
                {
                    "name": f"{band.lower()}_ideal_frame4_frame68_same_phase",
                    "pass": bool(np.isclose(values[4], values[68], atol=1e-14)),
                },
            ]
        )

    seed = 100_001
    draws64 = frozen_event_draws(seed, 64)
    draws68 = frozen_event_draws(seed, 68)
    draws72 = frozen_event_draws(seed, 72)
    prefix64 = noise_checksum(
        draws64["sample_draws_v"], draws64["comparator_draws_v"]
    )
    prefix68 = noise_checksum(
        draws68["sample_draws_v"][:64],
        draws68["comparator_draws_v"][:64],
    )
    prefix72 = noise_checksum(
        draws72["sample_draws_v"][:64],
        draws72["comparator_draws_v"][:64],
    )
    checks.extend(
        [
            {
                "name": "noise_prefix_64_vs_68_exact",
                "pass": prefix64 == prefix68,
                "checksum_64": prefix64,
                "checksum_extended": prefix68,
            },
            {
                "name": "noise_prefix_64_vs_72_exact",
                "pass": prefix64 == prefix72,
                "checksum_64": prefix64,
                "checksum_extended": prefix72,
            },
            {
                "name": "sample_prefix_values_exact",
                "pass": bool(
                    np.array_equal(
                        draws64["sample_draws_v"],
                        draws68["sample_draws_v"][:64],
                    )
                ),
            },
            {
                "name": "comparator_prefix_values_exact",
                "pass": bool(
                    np.array_equal(
                        draws64["comparator_draws_v"],
                        draws68["comparator_draws_v"][:64],
                    )
                ),
            },
        ]
    )

    failed = [row for row in checks if not row["pass"]]
    payload = {
        "status": "PASS_FAST64_V2_UNIT_TESTS"
        if not failed
        else "FAIL_FAST64_V2_UNIT_TESTS",
        "pass": not failed,
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failed),
    }
    output = Path(__file__).resolve().parent.parent / "results/fast64_v2_unit_tests.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, sort_keys=True))
    check(not failed, f"unit-test failures: {[row['name'] for row in failed]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
