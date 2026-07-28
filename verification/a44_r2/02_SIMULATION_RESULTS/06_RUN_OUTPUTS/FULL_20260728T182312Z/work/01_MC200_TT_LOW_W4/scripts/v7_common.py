#!/usr/bin/env python3
"""Shared constants and deterministic I/O for the FAST64 D3-only V7 run."""

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from sar_campaign_common import ROOT
from sar_event_noise import frozen_event_draws


CAMPAIGN_ID = "A44_CODEX_FAST64_D3_ONLY_32GB_ONE_DAY_PLAN_V7"
EVIDENCE_CLASS = "FAST64_D3_ONLY_MC200_MODEL_CONDITIONAL"
SAMPLE_RATE_HZ = 2_000_000.0
FRAME_PERIOD_S = 500e-9
NFFT = 64
PHASE_RAD = np.pi / 4.0
INPUT_VPP_DIFF_V = 3.0
INPUT_AMPLITUDE_DIFF_V = INPUT_VPP_DIFF_V / 2.0
PVT_NAME = "TT_3P3_27C"
BANDS = {
    "LOW": {"bin": 7, "fin_hz": 218_750.0},
    "NEAR_NYQUIST": {"bin": 29, "fin_hz": 906_250.0},
}
SNDR_HARD_MIN_DB = 46.91
ENOB_HARD_MIN_BIT = 7.50
SNR_BUDGET_MIN_DB = 48.14
SNDR_PREFERRED_DB = 47.75
ENOB_PREFERRED_BIT = 7.64
REQUIRED_DIES = 200
MINIMUM_PASSING_DIES = 190
TERMINAL_STATES = {
    "VALID_PASS",
    "VALID_FAIL",
    "SIM_ERROR_UNRESOLVED",
    "MODEL_BLOCKED",
    "MEASUREMENT_BLOCKED",
}

CONFIG_DIR = ROOT / "config"
MANIFEST_DIR = ROOT / "manifests"
CSV_DIR = ROOT / "csv"
JOB_DIR = ROOT / "jobs" / "v7"
LOG_DIR = ROOT / "logs" / "v7"
PLOT_DIR = ROOT / "plots"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"


def ensure_v7_directories():
    for path in (
        CONFIG_DIR,
        MANIFEST_DIR,
        CSV_DIR,
        JOB_DIR,
        LOG_DIR,
        PLOT_DIR,
        REPORT_DIR,
        RESULT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json_hash(payload):
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return sha256_bytes(serialized)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_atomic(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with temporary_path.open("w", newline="", encoding="ascii") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, extrasaction="ignore"
            )
            if fieldnames:
                writer.writeheader()
                writer.writerows(rows)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def mismatch_checksums(weights_rows):
    by_seed = {}
    for row in weights_rows:
        if row["branch"] != "CLAIM_BASELINE_3SIGMA_CONVERSION":
            continue
        seed = int(row["mismatch_seed"])
        by_seed.setdefault(seed, []).append(
            {
                "side": row["side"],
                "element": row["element"],
                "nominal_units": row["nominal_units"],
                "realized_units": row["realized_units"],
                "relative_error": row["relative_error"],
            }
        )
    output = {}
    for seed, rows in by_seed.items():
        rows.sort(key=lambda item: (item["side"], item["element"]))
        output[seed] = canonical_json_hash(rows)
    return output


def noise_draw_checksum(noise_seed):
    draws = frozen_event_draws(noise_seed, NFFT)
    payload = bytearray()
    payload.extend(np.asarray(draws["sample_draws_v"], dtype="<f8").tobytes())
    payload.extend(np.asarray(draws["comparator_draws_v"], dtype="<f8").tobytes())
    return sha256_bytes(bytes(payload))


def compact_code_checksum(codes):
    values = np.asarray(codes, dtype=np.uint8)
    return sha256_bytes(values.tobytes())


def parse_seed_expression(value):
    if value == "1:200":
        return list(range(1, 201))
    seeds = sorted({int(token.strip()) for token in value.split(",") if token.strip()})
    if any(seed < 1 or seed > REQUIRED_DIES for seed in seeds):
        raise ValueError("mismatch seeds must be in the inclusive range 1..200")
    return seeds


def load_manifest_checksums():
    mismatch = {
        int(row["mismatch_seed"]): row["mismatch_checksum_sha256"]
        for row in read_csv(MANIFEST_DIR / "mismatch_seed_manifest.csv")
    }
    noise = {
        int(row["noise_seed"]): row["noise_draw_checksum_sha256"]
        for row in read_csv(MANIFEST_DIR / "noise_seed_manifest.csv")
    }
    return mismatch, noise
