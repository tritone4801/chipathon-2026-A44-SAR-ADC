#!/usr/bin/env python3
"""Freeze the current resized comparator MC200 LOW/W4 input set."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ID = "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587"
CANDIDATE_HASH = "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"
COMPARATOR = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
FIELDS = (
    "job_id,phase,role,category,mismatch_seed,noise_mode,noise_seed,band,pvt,"
    "warmup_frames,total_frames,retained_frame_start,retained_frame_end,nfft,"
    "bin,fin_hz,maxstep_ps,solver_profile,required,state,returncode,elapsed_s,"
    "overall_status,completed_utc"
).split(",")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row(seed: int, smoke: bool = False) -> dict[str, object]:
    prefix = "SMOKE" if smoke else "MC200"
    return {
        "job_id": f"{prefix}_{CANDIDATE_ID}_S{seed:03d}_LOW_W4",
        "phase": "P1_SMOKE" if smoke else "P4_EVENT_NOISE_MC200_LOW",
        "role": f"{prefix}_{CANDIDATE_ID}_MC200_LOW",
        "category": f"{CANDIDATE_ID}_D3_NOISE_PLUS_MISMATCH_MC200_W4"
        + ("_SMOKE" if smoke else ""),
        "mismatch_seed": seed,
        "noise_mode": "ON",
        "noise_seed": 100000 + seed,
        "band": "LOW",
        "pvt": "TT_3P3_27C",
        "warmup_frames": 4,
        "total_frames": 68,
        "retained_frame_start": 4,
        "retained_frame_end": 67,
        "nfft": 64,
        "bin": 7,
        "fin_hz": 218750.0,
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "required": True,
        "state": "PENDING",
        "returncode": "",
        "elapsed_s": "",
        "overall_status": "",
        "completed_utc": "",
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    text = COMPARATOR.read_text(encoding="utf-8")
    actual_hash = sha256(COMPARATOR)
    expected_widths = {
        "XM1": 1.56,
        "XM3": 3.51,
        "XM4": 3.51,
        "XM5": 8.2524,
        "XM6": 8.2524,
        "XM7": 16.8587,
        "XM11": 16.8587,
    }
    width_checks = {
        device: bool(
            re.search(
                rf"(?im)^{device}\b.*\bW={re.escape(str(width))}u\b",
                text,
            )
        )
        for device, width in expected_widths.items()
    }
    formal = [row(seed) for seed in range(1, 201)]
    smoke = [row(seed, smoke=True) for seed in (1, 44, 96)]
    write_csv(ROOT / "manifests/job_matrix.csv", formal)
    write_csv(ROOT / "manifests/smoke_job_matrix.csv", smoke)
    contract = {
        "campaign": ROOT.name,
        "created_utc": utc_now(),
        "status": "FROZEN_BEFORE_EXECUTION",
        "candidate_id": CANDIDATE_ID,
        "candidate_comparator_path": str(COMPARATOR),
        "candidate_comparator_sha256": actual_hash,
        "declared_candidate_comparator_sha256": CANDIDATE_HASH,
        "resizing_um": expected_widths,
        "method": {
            "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
            "steady_state_method_id": "FAST64_SS_W4",
            "population": "mismatch_seed_1_through_200",
            "corner": "TT_3P3_27C",
            "band": "LOW",
            "frames": 68,
            "formal_frames": "4_through_67",
            "maxstep_ps": 50,
            "noise_seed_rule": "100000_plus_mismatch_seed",
            "workers": 4,
        },
        "claim_boundary": [
            "MC200 is the fixed TT population result.",
            "PVT selected MC20 and FULL STATIC are reported separately.",
            "No layout, PEX, silicon, production-yield, or tapeout signoff claim.",
        ],
    }
    write_json(ROOT / "config/current_mc200_contract.json", contract)
    checks = {
        "candidate_hash_matches_declared": actual_hash == CANDIDATE_HASH,
        "all_declared_widths_match": all(width_checks.values()),
        "formal_job_count_200": len(formal) == 200,
        "formal_seeds_exact_1_to_200": [r["mismatch_seed"] for r in formal]
        == list(range(1, 201)),
        "smoke_seeds_exact": [r["mismatch_seed"] for r in smoke] == [1, 44, 96],
        "fixed_tt_low_w4_50ps": all(
            r["pvt"] == "TT_3P3_27C"
            and r["band"] == "LOW"
            and r["retained_frame_start"] == 4
            and r["retained_frame_end"] == 67
            and r["maxstep_ps"] == 50
            for r in formal
        ),
    }
    write_json(
        ROOT / "results/setup_audit.json",
        {
            "campaign": ROOT.name,
            "completed_utc": utc_now(),
            "candidate_comparator_sha256": actual_hash,
            "width_checks": width_checks,
            "checks": checks,
            "pass": all(checks.values()),
        },
    )
    if not all(checks.values()):
        raise SystemExit("MC200 freeze audit failed")
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
