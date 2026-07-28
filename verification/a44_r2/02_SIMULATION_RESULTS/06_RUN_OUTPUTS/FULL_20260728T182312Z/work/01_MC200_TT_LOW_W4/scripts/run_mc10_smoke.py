#!/usr/bin/env python3
"""Run a disposable seed3 LOW smoke without populating formal MC10 CSVs."""

import json
from datetime import datetime, timezone

from run_v7 import run_record
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import (
    CONFIG_DIR,
    load_manifest_checksums,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


def main() -> int:
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    row, codes = run_record(
        grouped,
        timing,
        3,
        "LOW",
        50,
        "smoke",
        "MC10_SMOKE",
        mismatch_checksums,
        noise_checksums,
    )
    reference_master = next(
        item
        for item in read_csv(
            ROOT / "references" / "current_mc200_target_master.csv"
        )
        if int(item["mismatch_seed"]) == 3 and item["band"] == "LOW"
    )
    reference_codes = [
        value
        for _, value in sorted(
            (
                int(item["frame_index"]),
                int(item["code"]),
            )
            for item in read_csv(
                ROOT / "references" / "current_mc200_target_codes.csv"
            )
            if int(item["mismatch_seed"]) == 3 and item["band"] == "LOW"
        )
    ]
    actual_codes = [
        int(item["code"])
        for item in sorted(codes, key=lambda item: int(item["frame_index"]))
    ]
    output = ROOT / "diagnostics" / "smoke"
    output.mkdir(parents=True, exist_ok=True)
    write_csv_atomic(output / "smoke_master.csv", [row])
    write_csv_atomic(output / "smoke_codes.csv", codes)
    checks = {
        "valid_state": row["state"] in {"VALID_PASS", "VALID_FAIL"},
        "fixed_50ps": float(row["maxstep_ns"]) == 0.05,
        "robust_gear": row["measurement_solver_profile"] == "ROBUST_GEAR",
        "separate_process": row["execution_mode"] == "SEPARATE_PROCESS_FALLBACK",
        "noise_checksum_match": row["noise_draw_checksum_match"] is True,
        "codes_64": len(actual_codes) == 64,
        "code_stream_matches_current_mc200": actual_codes == reference_codes,
        "checksum_matches_current_mc200": (
            row["compact_code_checksum_sha256"]
            == reference_master["compact_code_checksum_sha256"]
        ),
    }
    audit = {
        "status": "PASS_MC10_SMOKE" if all(checks.values()) else "FAIL_MC10_SMOKE",
        "pass": all(checks.values()),
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 3,
        "band": "LOW",
        "checks": checks,
        "formal_results_reused": False,
    }
    write_json_atomic(ROOT / "results" / "mc10_smoke_audit.json", audit)
    print(json.dumps(audit, indent=2))
    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
