#!/usr/bin/env python3
"""Build the union of all seed-band records explicitly marked non-reproducible."""

import csv
import json
import sys
from pathlib import Path


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: build_target_contract.py CROSS_RUN_AUDIT OUTPUT_DIR"
        )
    audit = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    sources = {
        "EARLY_MC200_VS_V7_LOW_CODE_MISMATCH": (
            audit / "data" / "baseline_vs_v7_low_seed_comparison.csv"
        ),
        "MC10_VS_V7_CODE_MISMATCH": (
            audit / "data" / "selected_rerun_comparison_v10_v11.csv"
        ),
        "EXTREME_TAIL_HISTORICAL_CODE_NOT_REPRODUCED": (
            audit / "data" / "tail_r1_replay_consistency.csv"
        ),
    }
    records = {}

    for row in read_csv(sources["EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"]):
        if row["code_stream_match"] == "False":
            key = (int(row["seed"]), "LOW")
            records.setdefault(key, set()).add(
                "EARLY_MC200_VS_V7_LOW_CODE_MISMATCH"
            )

    for row in read_csv(sources["MC10_VS_V7_CODE_MISMATCH"]):
        if row["code_checksum_match"] == "False":
            key = (int(row["seed"]), row["band"])
            records.setdefault(key, set()).add("MC10_VS_V7_CODE_MISMATCH")

    for row in read_csv(
        sources["EXTREME_TAIL_HISTORICAL_CODE_NOT_REPRODUCED"]
    ):
        if row["role"] == "TAIL":
            key = (int(row["seed"]), row["band"])
            records.setdefault(key, set()).add(
                "EXTREME_TAIL_HISTORICAL_CODE_NOT_REPRODUCED"
            )

    rows = []
    for (seed, band), reasons in sorted(records.items()):
        rows.append(
            {
                "target_id": f"S{seed:03d}_{band}",
                "mismatch_seed": seed,
                "noise_seed": 100000 + seed,
                "band": band,
                "maxstep_ps": 50,
                "solver_profile": "ROBUST_GEAR",
                "nfft": 64,
                "reasons": ";".join(sorted(reasons)),
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    contract_path = output / "fixed50_target_contract.csv"
    with contract_path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    role_counts = {
        role: sum(role in row["reasons"] for row in rows) for role in sources
    }
    summary = {
        "status": "FROZEN_BEFORE_EXECUTION",
        "target_record_count": len(rows),
        "unique_seed_count": len({row["mismatch_seed"] for row in rows}),
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "nfft": 64,
        "role_counts": role_counts,
        "source_paths": {key: str(value) for key, value in sources.items()},
    }
    (output / "fixed50_target_contract.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    if len(rows) != 41:
        raise RuntimeError(f"expected 41 union records, found {len(rows)}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
