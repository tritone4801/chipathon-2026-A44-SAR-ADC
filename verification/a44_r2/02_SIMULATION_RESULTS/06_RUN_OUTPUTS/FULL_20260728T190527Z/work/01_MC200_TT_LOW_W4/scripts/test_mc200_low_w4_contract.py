#!/usr/bin/env python3
"""Static contract tests for the LOW-only MC200 W4 campaign."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    contract = json.loads(
        (ROOT / "config/mc200_low_w4_contract.json").read_text(encoding="utf-8")
    )
    assert contract["scope"] == "MC200_LOW_FAST64_SS_W4"
    assert contract["population"]["formal_record_count"] == 200
    assert contract["population"]["total_code_rows"] == 13_600
    assert contract["population"]["retained_code_rows"] == 12_800
    assert contract["measurement"]["band"] == "LOW"
    assert contract["measurement"]["bin"] == 7
    assert contract["measurement"]["warmup_frames"] == 4
    assert contract["measurement"]["total_frames"] == 68
    assert contract["measurement"]["retained_frames"] == [4, 67]
    assert contract["measurement"]["maxstep_ps"] == 50
    assert contract["measurement"]["solver_profile"] == "ROBUST_GEAR"
    assert contract["simulator_startup_contract"]["ngbehavior"] == "hsa"
    assert contract["simulator_startup_contract"]["expected_log_banner"] == (
        "Compatibility modes selected: hs a"
    )
    assert contract["simulator_startup_contract"]["num_threads"] == 4
    assert (
        contract["first_conversion_gate"][
            "frame0_equals_frame64_required_for_noise_on"
        ]
        is False
    )
    assert contract["equation_contract"]["enob_raw_bit"] == "(SNDR_dB-1.76)/6.02"
    assert contract["style_contract"]["spectrum_display"] == (
        "DISCRETE_FFT_BINS_NO_SMOOTHING"
    )
    print("PASS_MC200_LOW_W4_CONTRACT_TEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
