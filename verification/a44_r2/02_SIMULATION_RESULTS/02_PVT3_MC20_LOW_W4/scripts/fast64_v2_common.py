#!/usr/bin/env python3
"""Shared constants and deterministic I/O for FAST64 V2."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
METHOD_ID = "FAST64_V2_FIRST_CONVERSION_SEPARATED"
STEADY_METHOD_ID = "FAST64_SS_W4"
HISTORICAL_METHOD_ID = "FAST64_STARTUP_INCLUSIVE_W0"

SAMPLE_RATE_HZ = 2_000_000.0
FRAME_PERIOD_S = 500e-9
NFFT = 64
PHASE_RAD = float(np.pi / 4.0)
INPUT_VPP_DIFF_V = 3.0
INPUT_AMPLITUDE_DIFF_V = INPUT_VPP_DIFF_V / 2.0
DOUT_APERTURE_NS = 480.0

BANDS = {
    "LOW": {"bin": 7, "fin_hz": 218_750.0},
    "NEAR_NYQUIST": {"bin": 29, "fin_hz": 906_250.0},
}
MAIN_SEEDS = (1, 2, 3, 47, 53, 71, 74, 109, 110, 195)
BRIDGE_CASES = (
    ("V7_P1", 21, "LOW"),
    ("V7_P5", 129, "LOW"),
    ("V7_P10", 183, "NEAR_NYQUIST"),
    ("CURRENT_P5", 19, "LOW"),
    ("CURRENT_P10", 182, "LOW"),
)
QUALIFICATION_SEEDS = (None, 44, 96)

SNDR_HARD_MIN_DB = 46.91
ENOB_HARD_MIN_BIT = 7.50
SNR_BUDGET_MIN_DB = 48.14
SNDR_PREFERRED_DB = 47.75
ENOB_PREFERRED_BIT = 7.64

CSV_DIR = ROOT / "csv"
CONFIG_DIR = ROOT / "config"
JOB_DIR = ROOT / "jobs" / "fast64_v2"
LOG_DIR = ROOT / "logs" / "fast64_v2"
MANIFEST_DIR = ROOT / "manifests"
PLOT_DIR = ROOT / "plots"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
RAW_DIR = ROOT / "raw"


def ensure_directories() -> None:
    for directory in (
        CSV_DIR,
        CONFIG_DIR,
        JOB_DIR,
        LOG_DIR,
        MANIFEST_DIR,
        PLOT_DIR,
        REPORT_DIR,
        RESULT_DIR,
        RAW_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_hash(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return sha256_bytes(encoded)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _atomic_path(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    return Path(temporary)


def write_csv_atomic(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    fieldnames: Sequence[str] | None = None,
) -> None:
    if fieldnames is None:
        ordered: list[str] = []
        for row in rows:
            for key in row:
                if key not in ordered:
                    ordered.append(key)
        fieldnames = ordered
    temporary = _atomic_path(path)
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(fieldnames),
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, payload: object) -> None:
    temporary = _atomic_path(path)
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_resource_rows(rows: Sequence[Mapping[str, object]]) -> None:
    path = CSV_DIR / "resource_trace.csv"
    existing = read_csv(path)
    combined: list[Mapping[str, object]] = [*existing, *rows]
    write_csv_atomic(path, combined)


def total_frames_for_warmup(warmup_frames: int) -> int:
    if warmup_frames not in (0, 4, 8):
        raise ValueError(f"unsupported warmup {warmup_frames}")
    return NFFT + warmup_frames


def retained_indices(warmup_frames: int) -> tuple[int, ...]:
    return tuple(range(warmup_frames, warmup_frames + NFFT))


def startup_pair_indices(total_frames: int) -> tuple[tuple[int, int], ...]:
    warmup_frames = total_frames - NFFT
    if warmup_frames not in (4, 8):
        raise ValueError(
            f"startup-pair contract requires 68 or 72 frames, got {total_frames}"
        )
    return tuple((index, index + NFFT) for index in range(warmup_frames))


def coherent_input_values(
    total_frames: int, band: str, sample_offset_s: float
) -> np.ndarray:
    """Generate the frozen 64-phase tone while extending the transient length."""
    if band not in BANDS:
        raise ValueError(f"unsupported band {band}")
    times = np.arange(total_frames, dtype=float) * FRAME_PERIOD_S + sample_offset_s
    return INPUT_AMPLITUDE_DIFF_V * np.sin(
        2.0 * np.pi * float(BANDS[band]["fin_hz"]) * times + PHASE_RAD
    )


def phase_aligned_rows(
    code_rows: Iterable[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    rows = list(code_rows)
    return sorted(rows, key=lambda row: int(row["frame_index"]) % NFFT)


def code_checksum(codes: Sequence[int]) -> str:
    return sha256_bytes(bytes(int(code) & 0xFF for code in codes))


def noise_checksum(sample: np.ndarray, comparator: np.ndarray) -> str:
    payload = bytearray()
    payload.extend(np.asarray(sample, dtype="<f8").tobytes())
    payload.extend(np.asarray(comparator, dtype="<f8").tobytes())
    return sha256_bytes(bytes(payload))


def qualification_jobs() -> list[dict[str, object]]:
    jobs: list[dict[str, object]] = []
    for seed in QUALIFICATION_SEEDS:
        seed_label = "NOM" if seed is None else f"S{seed:03d}"
        for band in BANDS:
            for warmup in (4, 8):
                jobs.append(
                    {
                        "job_id": f"QUAL_STRICT_{seed_label}_{band}_W{warmup}",
                        "phase": "P2_WARMUP_QUALIFICATION",
                        "role": "QUALIFICATION",
                        "mismatch_seed": "" if seed is None else seed,
                        "noise_mode": "OFF",
                        "noise_seed": "",
                        "band": band,
                        "pvt": "TT_3P3_27C",
                        "warmup_frames": warmup,
                        "total_frames": total_frames_for_warmup(warmup),
                        "maxstep_ps": 50,
                        "state": "PENDING",
                    }
                )
            jobs.append(
                {
                    "job_id": f"QUAL_BULK_{seed_label}_{band}_W4",
                    "phase": "P3_NUMERICAL_QUALIFICATION",
                    "role": "QUALIFICATION",
                    "mismatch_seed": "" if seed is None else seed,
                    "noise_mode": "OFF",
                    "noise_seed": "",
                    "band": band,
                    "pvt": "TT_3P3_27C",
                    "warmup_frames": 4,
                    "total_frames": 68,
                    "maxstep_ps": 100,
                    "state": "PENDING",
                }
            )
    return jobs


def main_jobs() -> list[dict[str, object]]:
    jobs: list[dict[str, object]] = []
    for seed in MAIN_SEEDS:
        for band in BANDS:
            for noise_mode, phase in (
                ("OFF", "P4_FIRST_CONVERSION_COMPANION"),
                ("ON", "P5_EVENT_NOISE_MC10"),
            ):
                jobs.append(
                    {
                        "job_id": f"MAIN_{noise_mode}_S{seed:03d}_{band}_W4",
                        "phase": phase,
                        "role": "MAIN_MC10",
                        "mismatch_seed": seed,
                        "noise_mode": noise_mode,
                        "noise_seed": "" if noise_mode == "OFF" else 100_000 + seed,
                        "band": band,
                        "pvt": "TT_3P3_27C",
                        "warmup_frames": 4,
                        "total_frames": 68,
                        "maxstep_ps": 50,
                        "state": "PENDING",
                    }
                )
    return jobs


def bridge_jobs() -> list[dict[str, object]]:
    jobs: list[dict[str, object]] = []
    for bridge_role, seed, band in BRIDGE_CASES:
        for noise_mode in ("OFF", "ON"):
            jobs.append(
                {
                    "job_id": f"BRIDGE_{bridge_role}_{noise_mode}_S{seed:03d}_{band}_W4",
                    "phase": "P6_PERCENTILE_BRIDGE",
                    "role": f"BRIDGE_{bridge_role}",
                    "mismatch_seed": seed,
                    "noise_mode": noise_mode,
                    "noise_seed": "" if noise_mode == "OFF" else 100_000 + seed,
                    "band": band,
                    "pvt": "TT_3P3_27C",
                    "warmup_frames": 4,
                    "total_frames": 68,
                    "maxstep_ps": 50,
                    "state": "PENDING",
                }
            )
    return jobs


def formal_jobs() -> list[dict[str, object]]:
    jobs = [*qualification_jobs(), *main_jobs(), *bridge_jobs()]
    if len(jobs) != 68:
        raise AssertionError(f"formal job count is {len(jobs)}, expected 68")
    if len({str(job["job_id"]) for job in jobs}) != 68:
        raise AssertionError("formal job IDs are not unique")
    return jobs


def smoke_jobs() -> list[dict[str, object]]:
    return [
        {
            "job_id": f"SMOKE_NOM_{band}_W4",
            "phase": "P1_SMOKE",
            "role": "SMOKE",
            "mismatch_seed": "",
            "noise_mode": "OFF",
            "noise_seed": "",
            "band": band,
            "pvt": "TT_3P3_27C",
            "warmup_frames": 4,
            "total_frames": 68,
            "maxstep_ps": 50,
            "state": "PENDING",
        }
        for band in BANDS
    ]
