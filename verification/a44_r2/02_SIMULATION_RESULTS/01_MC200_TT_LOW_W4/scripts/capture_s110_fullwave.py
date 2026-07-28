#!/usr/bin/env python3
"""Capture the required independent full-waveform audit for seed 110 LOW."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from run_v7 import run_record
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import CONFIG_DIR, load_manifest_checksums


def write_csv(path: Path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    row, codes = run_record(
        grouped,
        timing,
        110,
        "LOW",
        50,
        "s110_fullwave_audit",
        "REPEATABILITY_FULLWAVE_S110",
        mismatch_checksums,
        noise_checksums,
        preserve_raw=True,
    )
    output = ROOT / "diagnostics" / "s110_fullwave"
    write_csv(output / "fullwave_master.csv", [row])
    write_csv(output / "fullwave_codes.csv", codes)
    result = {
        "status": (
            "PASS_S110_FULLWAVE_CAPTURE"
            if row["state"] in {"VALID_PASS", "VALID_FAIL"}
            and row["full_waveform_audit"] is True
            and row["raw_path"]
            and row["raw_sha256"]
            else "FAIL_S110_FULLWAVE_CAPTURE"
        ),
        "pass": row["state"] in {"VALID_PASS", "VALID_FAIL"}
        and row["full_waveform_audit"] is True
        and bool(row["raw_path"])
        and bool(row["raw_sha256"]),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 110,
        "band": "LOW",
        "maxstep_ps": 50,
        "solver_profile": row["measurement_solver_profile"],
        "state": row["state"],
        "sndr_db": row["sndr_db"],
        "frame0_code": codes[0]["code"],
        "raw_path": row["raw_path"],
        "raw_sha256": row["raw_sha256"],
        "main_population_was_not_modified": True,
    }
    (ROOT / "results" / "s110_fullwave_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
