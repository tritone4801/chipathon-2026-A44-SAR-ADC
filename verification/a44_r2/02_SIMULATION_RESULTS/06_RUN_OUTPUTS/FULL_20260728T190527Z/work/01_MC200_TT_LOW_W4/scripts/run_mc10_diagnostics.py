#!/usr/bin/env python3
"""Repeat every first-run mismatch and seed110 LOW without changing first-run evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from run_fixed50_subset import ngspice_snapshot
from run_v7 import run_record
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import CONFIG_DIR, load_manifest_checksums


AUDIT = ROOT / "results" / "strict_reproduction_audit.json"
OUT = ROOT / "diagnostics"
MASTER = OUT / "diagnostic_master.csv"
CODES = OUT / "diagnostic_codes.csv"
TRACE = OUT / "diagnostic_resource_trace.csv"
STATUS = ROOT / "results" / "diagnostic_status.json"
MAXSTEP_PS = 50
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}
SAVE_LOCK = threading.Lock()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else ()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Monitor:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self) -> None:
        while not self.stop_event.is_set():
            processes = ngspice_snapshot()
            self.rows.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "process_count": len(processes),
                    "total_threads": sum(item["threads"] for item in processes),
                    "total_rss_kb": sum(item["rss_kb"] for item in processes),
                    "pids": ";".join(str(item["pid"]) for item in processes),
                }
            )
            self.stop_event.wait(2)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)


def target_keys() -> list[tuple[int, str]]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    keys = {
        (int(item["mismatch_seed"]), item["band"])
        for item in audit["different_keys"]
    }
    keys.add((110, "LOW"))
    return sorted(keys, key=lambda key: (key[0], key[1]))


def existing_rows(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.is_file() else []


def save_result(row: dict, codes: list[dict], repeat: int, mode: str) -> None:
    with SAVE_LOCK:
        row = dict(row)
        row["diagnostic_repeat"] = repeat
        row["diagnostic_mode"] = mode
        key = (
            int(row["mismatch_seed"]),
            row["band"],
            repeat,
            mode,
        )
        master_rows = existing_rows(MASTER)
        master_rows = [
            item
            for item in master_rows
            if (
                int(item["mismatch_seed"]),
                item["band"],
                int(item["diagnostic_repeat"]),
                item["diagnostic_mode"],
            )
            != key
        ]
        master_rows.append(row)
        master_rows.sort(
            key=lambda item: (
                int(item["mismatch_seed"]),
                item["band"],
                int(item["diagnostic_repeat"]),
            )
        )
        write_csv(MASTER, master_rows)

        annotated_codes = []
        for code in codes:
            item = dict(code)
            item["diagnostic_repeat"] = repeat
            item["diagnostic_mode"] = mode
            annotated_codes.append(item)
        code_rows = existing_rows(CODES)
        code_rows = [
            item
            for item in code_rows
            if (
                int(item["mismatch_seed"]),
                item["band"],
                int(item["diagnostic_repeat"]),
                item["diagnostic_mode"],
            )
            != key
        ]
        code_rows.extend(annotated_codes)
        code_rows.sort(
            key=lambda item: (
                int(item["mismatch_seed"]),
                item["band"],
                int(item["diagnostic_repeat"]),
                int(item["frame_index"]),
            )
        )
        write_csv(CODES, code_rows)

        stem = row["measurement_stem"]
        run_root = OUT / "runs" / stem
        write_csv(run_root / "master.csv", [row])
        write_csv(run_root / "codes.csv", annotated_codes)


def execute_one(
    grouped,
    timing,
    mismatch_checksums,
    noise_checksums,
    seed: int,
    band: str,
    repeat: int,
    mode: str,
) -> tuple[dict, list[dict]]:
    stem_prefix = f"diag_{mode}_r{repeat}"
    row, codes = run_record(
        grouped,
        timing,
        seed,
        band,
        MAXSTEP_PS,
        stem_prefix,
        "MC10_REPRO_DIAGNOSTIC",
        mismatch_checksums,
        noise_checksums,
        preserve_raw=False,
    )
    save_result(row, codes, repeat, mode)
    print(
        f"DIAG_DONE seed={seed} band={band} repeat={repeat} mode={mode} "
        f"state={row['state']} sndr_db={row.get('sndr_db', '')}",
        flush=True,
    )
    return row, codes


def execute(phase: str) -> int:
    if ngspice_snapshot():
        raise RuntimeError("active ngspice process exists before diagnostics")
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    keys = target_keys()
    monitor = Monitor()
    monitor.start()
    try:
        if phase == "sequential":
            for repeat in (1, 2):
                for seed, band in keys:
                    execute_one(
                        grouped,
                        timing,
                        mismatch_checksums,
                        noise_checksums,
                        seed,
                        band,
                        repeat,
                        "single_worker",
                    )
        else:
            work = [
                (seed, band, repeat)
                for repeat in (3, 4)
                for seed, band in keys
            ]
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(
                        execute_one,
                        grouped,
                        timing,
                        mismatch_checksums,
                        noise_checksums,
                        seed,
                        band,
                        repeat,
                        "four_worker",
                    )
                    for seed, band, repeat in work
                ]
                for future in as_completed(futures):
                    future.result()
    finally:
        monitor.stop()
    rows = existing_rows(TRACE)
    rows.extend(monitor.rows)
    write_csv(TRACE, rows)
    return 0


def code_map(path: Path, early: bool = False):
    output = {}
    for row in read_csv(path):
        band = "LOW" if early else row["band"]
        repeat = int(row["diagnostic_repeat"]) if "diagnostic_repeat" in row else 0
        output[
            (
                int(row["mismatch_seed"]),
                band,
                repeat,
                int(row["frame_index"]),
            )
        ] = int(row["code"])
    return output


def stream(mapping, seed: int, band: str, repeat: int = 0):
    values = []
    for frame in range(64):
        key = (seed, band, repeat, frame)
        if key not in mapping:
            return None
        values.append(mapping[key])
    return tuple(values)


def analyze() -> int:
    keys = target_keys()
    master_rows = existing_rows(MASTER)
    code_rows = existing_rows(CODES)
    current = code_map(ROOT / "references" / "current_mc200_target_codes.csv")
    primary = code_map(ROOT / "csv" / "mc10_codes.csv")
    v7 = code_map(ROOT / "references" / "baseline_mc200" / "dynamic_codes.csv")
    fixed = code_map(
        ROOT
        / "references"
        / "fixed50_41_compact"
        / "data"
        / "fixed50_target_codes.csv"
    )
    early_path = (
        ROOT
        / "references"
        / "early_mc200"
        / "dynamic_mc200_fast64_codes.csv"
    )
    early = code_map(early_path, early=True)
    diagnostic = code_map(CODES)
    reference_sets = {
        "CURRENT_MC200": current,
        "V7_MC200": v7,
        "FIXED50_41": fixed,
        "EARLY_MC200": early,
    }
    repeat_rows = []
    summary_rows = []
    fullwave_targets = []
    for seed, band in keys:
        repeat_streams = []
        branch_labels = []
        for repeat in range(1, 5):
            values = stream(diagnostic, seed, band, repeat)
            repeat_streams.append(values)
            matching = [
                label
                for label, mapping in reference_sets.items()
                if stream(mapping, seed, band) == values and values is not None
            ]
            label = ";".join(matching) if matching else "THIRD_BRANCH"
            branch_labels.append(label)
            matching_master = next(
                (
                    row
                    for row in master_rows
                    if int(row["mismatch_seed"]) == seed
                    and row["band"] == band
                    and int(row["diagnostic_repeat"]) == repeat
                ),
                None,
            )
            repeat_rows.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "diagnostic_repeat": repeat,
                    "diagnostic_mode": (
                        matching_master["diagnostic_mode"]
                        if matching_master
                        else ""
                    ),
                    "state": matching_master["state"] if matching_master else "MISSING",
                    "sndr_db": matching_master["sndr_db"] if matching_master else "",
                    "frame0": values[0] if values else "",
                    "frame1": values[1] if values else "",
                    "compact_code_checksum_sha256": (
                        matching_master["compact_code_checksum_sha256"]
                        if matching_master
                        else ""
                    ),
                    "matching_branches": label if values else "MISSING",
                }
            )
        unique = {values for values in repeat_streams if values is not None}
        any_third = "THIRD_BRANCH" in branch_labels
        if any_third:
            classification = "THIRD_BRANCH"
        elif len(unique) > 1:
            classification = "INTERMITTENT_BRANCHING"
        elif all("CURRENT_MC200" in label for label in branch_labels):
            classification = "STABLE_CURRENT_MC200_BRANCH"
        elif all(
            ("V7_MC200" in label or "FIXED50_41" in label)
            for label in branch_labels
        ):
            classification = "STABLE_HISTORICAL_REFERENCE_BRANCH"
        else:
            classification = "INTERMITTENT_BRANCHING"

        reasons = []
        primary_stream = stream(primary, seed, band)
        primary_known = any(
            stream(mapping, seed, band) == primary_stream
            for mapping in reference_sets.values()
        )
        if len(unique) > 1:
            reasons.append("DIAGNOSTIC_MULTIPLE_BRANCHES")
        if any_third or not primary_known:
            reasons.append("THIRD_BRANCH_OBSERVED")
        if seed == 110 and any(
            values is not None and values[0] == 240 for values in repeat_streams
        ):
            reasons.append("SEED110_FRAME0_240_REAPPEARED")
        if seed in {53, 109, 195}:
            pairs = {
                (values[0], values[1])
                for values in repeat_streams
                if values is not None
            }
            if len(pairs) > 1:
                reasons.append("CRITICAL_FRAME0_FRAME1_UNSTABLE")
        if reasons:
            fullwave_targets.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "reasons": ";".join(reasons),
                }
            )
        summary_rows.append(
            {
                "mismatch_seed": seed,
                "band": band,
                "classification": classification,
                "unique_diagnostic_streams": len(unique),
                "repeat_branches": "|".join(branch_labels),
                "fullwave_triggered": bool(reasons),
                "fullwave_reasons": ";".join(reasons),
            }
        )
    write_csv(OUT / "diagnostic_repeat_classification.csv", repeat_rows)
    write_csv(OUT / "diagnostic_key_summary.csv", summary_rows)
    write_csv(
        OUT / "fullwave_trigger_targets.csv",
        fullwave_targets,
        ("mismatch_seed", "band", "reasons"),
    )
    trace_rows = existing_rows(TRACE)
    completed = len(master_rows) == len(keys) * 4 and len(code_rows) == len(keys) * 4 * 64
    valid = all(row["state"] in VALID_STATES for row in master_rows)
    status = {
        "status": "DIAGNOSTICS_COMPLETE" if completed and valid else "DIAGNOSTICS_INCOMPLETE",
        "pass_execution": completed and valid,
        "strict_first_run_status_unchanged": json.loads(
            AUDIT.read_text(encoding="utf-8")
        )["status"],
        "target_keys": len(keys),
        "diagnostic_records": len(master_rows),
        "diagnostic_code_rows": len(code_rows),
        "all_records_valid": valid,
        "max_ngspice_processes": max(
            (int(row["process_count"]) for row in trace_rows), default=0
        ),
        "max_total_threads": max(
            (int(row["total_threads"]) for row in trace_rows), default=0
        ),
        "max_total_rss_kb": max(
            (int(row["total_rss_kb"]) for row in trace_rows), default=0
        ),
        "master_sha256": sha256(MASTER) if MASTER.is_file() else "",
        "codes_sha256": sha256(CODES) if CODES.is_file() else "",
        "fullwave_trigger_count": len(fullwave_targets),
        "fullwave_targets": fullwave_targets,
        "analyzed_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(STATUS, status)
    print(json.dumps(status, indent=2))
    return 0 if status["pass_execution"] else 1


def main() -> int:
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = "1"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", choices=("sequential", "concurrent", "analyze"), required=True
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.phase == "analyze":
        return analyze()
    return execute(args.phase)


if __name__ == "__main__":
    raise SystemExit(main())
