#!/usr/bin/env python3
"""Run four isolated, concurrent repeats of seed 110 LOW without touching master CSVs."""

from __future__ import annotations

import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from run_v7 import run_record
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import CONFIG_DIR, load_manifest_checksums


SEED = 110
BAND = "LOW"
REPEATS = 4
CATEGORY = "REPEATABILITY_DIAGNOSTIC_S110"
OUT = ROOT / "diagnostics" / "s110_repeatability"
REF = ROOT / "references" / "fixed50_41_compact" / "data"


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def checksum(codes) -> str:
    return hashlib.sha256(bytes(int(code) for code in codes)).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()

    def one(repeat_index):
        row, codes = run_record(
            grouped,
            timing,
            SEED,
            BAND,
            50,
            f"s110_repeat_r{repeat_index}",
            CATEGORY,
            mismatch_checksums,
            noise_checksums,
        )
        for code in codes:
            code["repeat_index"] = repeat_index
        row["repeat_index"] = repeat_index
        return row, codes

    rows = []
    code_rows = []
    with ThreadPoolExecutor(max_workers=REPEATS) as executor:
        futures = {executor.submit(one, index): index for index in range(1, REPEATS + 1)}
        for future in as_completed(futures):
            row, codes = future.result()
            rows.append(row)
            code_rows.extend(codes)
    rows.sort(key=lambda row: int(row["repeat_index"]))
    code_rows.sort(
        key=lambda row: (int(row["repeat_index"]), int(row["frame_index"]))
    )
    write_csv(OUT / "repeat_master.csv", rows)
    write_csv(OUT / "repeat_codes.csv", code_rows)

    current_selected = [
        row
        for row in read_csv(ROOT / "csv" / "dynamic_codes.csv")
        if int(row["mismatch_seed"]) == SEED and row["band"] == BAND
    ]
    reference_selected = [
        row
        for row in read_csv(REF / "fixed50_target_codes.csv")
        if int(row["mismatch_seed"]) == SEED and row["band"] == BAND
    ]
    current_codes = [
        int(row["code"])
        for row in sorted(current_selected, key=lambda row: int(row["frame_index"]))
    ]
    reference_codes = [
        int(row["code"])
        for row in sorted(
            reference_selected, key=lambda row: int(row["frame_index"])
        )
    ]
    repeats = []
    for index in range(1, REPEATS + 1):
        stream = [
            int(row["code"])
            for row in code_rows
            if int(row["repeat_index"]) == index
        ]
        repeats.append(
            {
                "repeat_index": index,
                "state": rows[index - 1]["state"],
                "sndr_db": float(rows[index - 1]["sndr_db"]),
                "frame0_code": stream[0],
                "checksum_sha256": checksum(stream),
                "matches_full_run": stream == current_codes,
                "matches_fixed50_reference": stream == reference_codes,
                "differing_frames_vs_full": [
                    frame
                    for frame, pair in enumerate(zip(stream, current_codes))
                    if pair[0] != pair[1]
                ],
                "differing_frames_vs_reference": [
                    frame
                    for frame, pair in enumerate(zip(stream, reference_codes))
                    if pair[0] != pair[1]
                ],
            }
        )
    result = {
        "status": "S110_REPEATABILITY_DIAGNOSTIC_COMPLETE",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "band": BAND,
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "concurrent_repeats": REPEATS,
        "full_run_frame0_code": current_codes[0],
        "fixed50_reference_frame0_code": reference_codes[0],
        "full_run_checksum_sha256": checksum(current_codes),
        "fixed50_reference_checksum_sha256": checksum(reference_codes),
        "repeats": repeats,
        "all_repeats_valid": all(
            row["state"] in {"VALID_PASS", "VALID_FAIL"} for row in rows
        ),
        "repeat_checksums": sorted({item["checksum_sha256"] for item in repeats}),
        "interpretation": (
            "NUMERICAL_BRANCH_NONDETERMINISM"
            if len({item["checksum_sha256"] for item in repeats}) > 1
            or (
                any(item["matches_full_run"] for item in repeats)
                and any(item["matches_fixed50_reference"] for item in repeats)
            )
            else "STABLE_REPEAT_OUTCOME"
        ),
        "main_population_was_not_modified": True,
    }
    (ROOT / "results" / "s110_repeatability_diagnostic.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["all_repeats_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
