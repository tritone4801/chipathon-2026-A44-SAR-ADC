#!/usr/bin/env python3
"""Run the frozen non-reproducible seed-band union at fixed 50 ps."""

import csv
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from run_v7 import merge_rows, run_die
from sar_campaign_common import ROOT, load_cdac_weights
from v7_common import (
    CONFIG_DIR,
    load_manifest_checksums,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


TARGET_PATH = ROOT / "config" / "fixed50_target_contract.csv"
MASTER_PATH = ROOT / "csv" / "fixed50_target_master.csv"
CODE_PATH = ROOT / "csv" / "fixed50_target_codes.csv"
TRACE_PATH = ROOT / "csv" / "fixed50_resource_trace.csv"
STATUS_PATH = ROOT / "results" / "fixed50_execution_status.json"
MAXSTEP_PS = 50
WORKERS = 4
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ngspice_snapshot():
    processes = []
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text(encoding="ascii").strip() != "ngspice":
                continue
            status = {}
            for line in (comm.parent / "status").read_text(
                encoding="ascii"
            ).splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    status[key] = value.strip()
            processes.append(
                {
                    "pid": int(comm.parent.name),
                    "threads": int(status.get("Threads", "0")),
                    "rss_kb": int(
                        status.get("VmRSS", "0 kB").split()[0]
                    ),
                }
            )
        except (FileNotFoundError, ProcessLookupError, ValueError):
            continue
    return processes


class Monitor:
    def __init__(self):
        self.rows = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop_event.is_set():
            processes = ngspice_snapshot()
            self.rows.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "process_count": len(processes),
                    "total_threads": sum(p["threads"] for p in processes),
                    "total_rss_kb": sum(p["rss_kb"] for p in processes),
                    "pids": ";".join(str(p["pid"]) for p in processes),
                }
            )
            self.stop_event.wait(2)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)


def verify_dependencies():
    source_root = Path(
        "/foss/designs/manual_goal/verification/"
        "A44_FAST64_D3_ONLY_MC200_V7"
    )
    record = json.loads(
        (ROOT / "config" / "dependency_hashes.json").read_text(
            encoding="ascii"
        )
    )
    failures = []
    for item in record["dependencies"]:
        source = Path(item["path"])
        try:
            relative = source.relative_to(source_root)
            live = ROOT / relative
        except ValueError:
            live = source
        if (
            not live.is_file()
            or live.stat().st_size != int(item["size_bytes"])
            or sha256(live) != item["sha256"]
        ):
            failures.append(
                {"role": item["role"], "live_path": str(live)}
            )
    return {
        "pass": not failures and len(record["dependencies"]) == 20,
        "declared": len(record["dependencies"]),
        "matching": len(record["dependencies"]) - len(failures),
        "failures": failures,
    }


def verify_production_source():
    production = Path("/foss/designs/manual_goal/analog/SAR_CURRENT")
    rows = read_csv(ROOT / "manifests" / "production_source_integrity.csv")
    failures = []
    for row in rows:
        live = production / row["relative_path"]
        if (
            not live.is_file()
            or live.stat().st_size != int(row["expected_size_bytes"])
            or sha256(live) != row["expected_sha256"]
        ):
            failures.append(row["relative_path"])
    return {
        "pass": not failures and len(rows) == 113,
        "declared": len(rows),
        "matching": len(rows) - len(failures),
        "failures": failures,
    }


def write_trace(rows):
    fields = (
        "timestamp_utc",
        "process_count",
        "total_threads",
        "total_rss_kb",
        "pids",
    )
    with TRACE_PATH.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = "1"

    targets = read_csv(TARGET_PATH)
    target_keys = {
        (int(row["mismatch_seed"]), row["band"]) for row in targets
    }
    if len(targets) != 41 or len(target_keys) != 41:
        raise RuntimeError("target contract is not the frozen 41-key union")
    if any(
        int(row["maxstep_ps"]) != MAXSTEP_PS
        or row["solver_profile"] != "ROBUST_GEAR"
        or int(row["nfft"]) != 64
        for row in targets
    ):
        raise RuntimeError("target method contract is not fixed 50 ps")

    cache = json.loads(
        (CONFIG_DIR / "qualification_cache.json").read_text(
            encoding="ascii"
        )
    )
    method_checks = {
        "qualification_complete": all(
            (
                cache.get("fixed_pilot_complete"),
                cache.get("numerical_qualification_pass"),
                cache.get("session_equivalence_complete"),
                cache.get("resource_admission_pass"),
            )
        ),
        "selected_formal_maxstep_50ps": int(
            cache.get("selected_formal_maxstep_ps", 0)
        )
        == MAXSTEP_PS,
        "separate_process_fallback": cache.get("session_execution_mode")
        == "SEPARATE_PROCESS_FALLBACK",
        "admitted_workers_at_least_4": int(
            cache.get("resource", {}).get("selected_formal_workers", 0)
        )
        >= WORKERS,
        "no_active_ngspice_at_start": not ngspice_snapshot(),
    }
    dependencies = verify_dependencies()
    production_source = verify_production_source()
    preflight = {
        "pass": (
            all(method_checks.values())
            and dependencies["pass"]
            and production_source["pass"]
        ),
        "checks": method_checks,
        "dependencies": dependencies,
        "production_source": production_source,
        "target_records": len(targets),
    }
    write_json_atomic(ROOT / "results" / "fixed50_preflight.json", preflight)
    if not preflight["pass"]:
        raise RuntimeError("fixed50 preflight failed")
    if "--preflight-only" in sys.argv[1:]:
        print(json.dumps(preflight, indent=2), flush=True)
        return

    existing_master = read_csv(MASTER_PATH) if MASTER_PATH.is_file() else []
    existing_codes = read_csv(CODE_PATH) if CODE_PATH.is_file() else []
    terminal = {
        (int(row["mismatch_seed"]), row["band"])
        for row in existing_master
        if row["state"] in VALID_STATES
    }
    work = [
        (int(row["mismatch_seed"]), row["band"])
        for row in targets
        if (int(row["mismatch_seed"]), row["band"]) not in terminal
    ]
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(
            encoding="ascii"
        )
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()

    started_utc = datetime.now(timezone.utc)
    started = time.monotonic()
    monitor = Monitor()
    monitor.start()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(
                run_die,
                grouped,
                timing,
                seed,
                MAXSTEP_PS,
                mismatch_checksums,
                noise_checksums,
                [band],
            ): (seed, band)
            for seed, band in work
        }
        for future in as_completed(futures):
            seed, band = futures[future]
            rows, codes = future.result()
            existing_master = merge_rows(
                MASTER_PATH,
                rows,
                ("mismatch_seed", "band"),
            )
            existing_master.sort(
                key=lambda row: (int(row["mismatch_seed"]), row["band"])
            )
            write_csv_atomic(MASTER_PATH, existing_master)
            existing_codes = merge_rows(
                CODE_PATH,
                codes,
                ("mismatch_seed", "band", "frame_index"),
            )
            existing_codes.sort(
                key=lambda row: (
                    int(row["mismatch_seed"]),
                    row["band"],
                    int(row["frame_index"]),
                )
            )
            write_csv_atomic(CODE_PATH, existing_codes)
            row = rows[0]
            print(
                "TARGET_DONE seed={} band={} state={} sndr_db={}".format(
                    seed, band, row["state"], row.get("sndr_db", "")
                ),
                flush=True,
            )
    monitor.stop()
    elapsed_s = time.monotonic() - started
    write_trace(monitor.rows)

    final_master = read_csv(MASTER_PATH)
    final_codes = read_csv(CODE_PATH)
    final_keys = {
        (int(row["mismatch_seed"]), row["band"]) for row in final_master
    }
    valid_records = [
        row for row in final_master if row["state"] in VALID_STATES
    ]
    checks = {
        "all_41_target_keys_present": final_keys == target_keys,
        "all_41_records_valid": len(valid_records) == 41,
        "all_2624_codes_present": len(final_codes) == 41 * 64,
        "all_records_50ps": all(
            float(row["maxstep_ns"]) == 0.05 for row in final_master
        ),
        "all_records_robust_gear": all(
            row["measurement_solver_profile"] == "ROBUST_GEAR"
            for row in final_master
        ),
        "all_noise_checksums_match": all(
            row["noise_draw_checksum_match"] == "True"
            for row in final_master
        ),
        "no_timeouts": all(
            row["timed_out"] == "False" for row in final_master
        ),
        "no_simulation_aborts": all(
            row["simulation_aborted"] == "False" for row in final_master
        ),
        "max_four_ngspice_processes": max(
            (int(row["process_count"]) for row in monitor.rows), default=0
        )
        <= WORKERS,
    }
    status = {
        "status": (
            "PASS_FIXED50_EXECUTION"
            if all(checks.values())
            else "FAIL_FIXED50_EXECUTION"
        ),
        "pass": all(checks.values()),
        "checks": checks,
        "preflight": preflight,
        "requested_target_records": len(targets),
        "valid_records": len(valid_records),
        "code_rows": len(final_codes),
        "maxstep_ps": MAXSTEP_PS,
        "solver_profile": "ROBUST_GEAR",
        "workers": WORKERS,
        "started_utc": started_utc.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed_s,
        "max_ngspice_processes": max(
            (int(row["process_count"]) for row in monitor.rows), default=0
        ),
        "master_sha256": sha256(MASTER_PATH),
        "codes_sha256": sha256(CODE_PATH),
    }
    write_json_atomic(STATUS_PATH, status)
    print(json.dumps(status, indent=2), flush=True)
    raise SystemExit(0 if status["pass"] else 1)


if __name__ == "__main__":
    main()
