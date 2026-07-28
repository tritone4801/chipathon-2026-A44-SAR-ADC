#!/usr/bin/env python3
"""Run and time the V8 MC12+2 quick-regression validation."""

import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from v7_common import CSV_DIR, REPORT_DIR, RESULT_DIR, ROOT, read_csv, write_json_atomic


CORE_SEEDS = (1, 21, 25, 44, 48, 64, 115, 129, 140, 166, 170, 183)
OPTIONAL_SEEDS = (13, 167)
OPTIONAL_ADMISSION_S = 42 * 60
NO_NEW_SIMULATION_S = 50 * 60
SIMULATION_HARD_STOP_S = 55 * 60
ONE_HOUR_S = 60 * 60
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}


def parse_utc(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def proc_status(pid):
    values = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text(
            encoding="ascii", errors="replace"
        ).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key] = value.strip()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    return values


def ngspice_processes():
    result = []
    for comm_path in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm_path.read_text(encoding="ascii").strip() != "ngspice":
                continue
            pid = int(comm_path.parent.name)
            status = proc_status(pid)
            if status is None:
                continue
            result.append(
                {
                    "pid": pid,
                    "threads": int(status.get("Threads", "0")),
                    "rss_kb": int(status.get("VmRSS", "0 kB").split()[0]),
                    "hwm_kb": int(status.get("VmHWM", "0 kB").split()[0]),
                }
            )
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
    return sorted(result, key=lambda item: item["pid"])


class ResourceMonitor:
    def __init__(self, validation_started):
        self.validation_started = validation_started
        self.phase = "IDLE"
        self.rows = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _run(self):
        while not self.stop_event.is_set():
            processes = ngspice_processes()
            now = datetime.now(timezone.utc)
            self.rows.append(
                {
                    "timestamp_utc": now.isoformat(),
                    "elapsed_from_validation_start_s": (
                        now - self.validation_started
                    ).total_seconds(),
                    "phase": self.phase,
                    "process_count": len(processes),
                    "total_threads": sum(item["threads"] for item in processes),
                    "max_threads_per_process": max(
                        (item["threads"] for item in processes), default=0
                    ),
                    "total_rss_kb": sum(item["rss_kb"] for item in processes),
                    "max_hwm_kb": max(
                        (item["hwm_kb"] for item in processes), default=0
                    ),
                    "pids": ";".join(str(item["pid"]) for item in processes),
                }
            )
            self.stop_event.wait(2.0)


def write_resource_trace(rows):
    path = CSV_DIR / "runtime_resource_trace.csv"
    fields = [
        "timestamp_utc",
        "elapsed_from_validation_start_s",
        "phase",
        "process_count",
        "total_threads",
        "max_threads_per_process",
        "total_rss_kb",
        "max_hwm_kb",
        "pids",
    ]
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def complete_records(seeds):
    master_path = CSV_DIR / "dynamic_master.csv"
    if not master_path.is_file():
        return 0
    rows = read_csv(master_path)
    wanted = set(seeds)
    return sum(
        int(row["mismatch_seed"]) in wanted and row["state"] in VALID_STATES
        for row in rows
    )


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def run_phase(label, seeds, workers, validation_started, monitor):
    overall_elapsed = (
        datetime.now(timezone.utc) - validation_started
    ).total_seconds()
    if overall_elapsed >= NO_NEW_SIMULATION_S:
        return {
            "label": label,
            "launched": False,
            "reason": "NO_NEW_SIMULATION_AFTER_50_MIN",
            "returncode": None,
            "elapsed_s": 0.0,
        }
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_v7.py"),
        "--stage",
        "formal",
        "--seeds",
        ",".join(str(seed) for seed in seeds),
        "--workers",
        str(workers),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts")
    log_path = ROOT / "logs" / f"runtime_validation_{label.lower()}.log"
    started = datetime.now(timezone.utc)
    monitor.phase = label
    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        timed_out = False
        while process.poll() is None:
            overall_elapsed = (
                datetime.now(timezone.utc) - validation_started
            ).total_seconds()
            if overall_elapsed >= SIMULATION_HARD_STOP_S:
                timed_out = True
                terminate_group(process)
                break
            time.sleep(2)
        returncode = process.returncode
    finished = datetime.now(timezone.utc)
    monitor.phase = "IDLE"
    return {
        "label": label,
        "launched": True,
        "seeds": list(seeds),
        "workers": workers,
        "command": command,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "elapsed_s": (finished - started).total_seconds(),
        "returncode": returncode,
        "timed_out": timed_out,
        "log": str(log_path.relative_to(ROOT)).replace("\\", "/"),
    }


def compact_manifest():
    excluded = {
        "manifests/compact_manifest_sha256.csv",
        "results/compact_manifest_audit.json",
        "results/runtime_validation_timing.json",
        "results/final_metadata_sha256.json",
        "reports/FINAL_MC12_PLUS2_ONE_HOUR_REPORT.md",
    }
    rows = []
    for path in sorted(candidate for candidate in ROOT.rglob("*") if candidate.is_file()):
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        if relative in excluded:
            continue
        rows.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    path = ROOT / "manifests" / "compact_manifest_sha256.csv"
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("relative_path", "size_bytes", "sha256"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    failures = []
    for row in rows:
        live = ROOT / row["relative_path"]
        if (
            not live.is_file()
            or live.stat().st_size != int(row["size_bytes"])
            or sha256_file(live) != row["sha256"]
        ):
            failures.append(row["relative_path"])
    audit = {
        "pass": not failures,
        "declared_files": len(rows),
        "matching_files": len(rows) - len(failures),
        "failures": failures,
        "manifest_sha256": sha256_file(path),
    }
    write_json_atomic(RESULT_DIR / "compact_manifest_audit.json", audit)
    return audit


def append_timing_to_report(timing):
    path = REPORT_DIR / "FINAL_MC12_PLUS2_ONE_HOUR_REPORT.md"
    text = path.read_text(encoding="ascii")
    lines = [
        "",
        "## Actual Timing Validation",
        "",
        f"- Package copy elapsed: `{timing['copy_elapsed_s']:.3f} s`",
        f"- Preflight audit elapsed: `{timing['preflight_audit_elapsed_s']:.3f} s`",
        f"- Mandatory MC12 elapsed: `{timing['core_phase']['elapsed_s']:.3f} s`",
        f"- Optional pair admitted: `{timing['optional_admitted']}`",
        f"- Optional pair elapsed: `{timing['optional_phase']['elapsed_s']:.3f} s`",
        f"- Quick finalization elapsed: `{timing['quick_finalize_elapsed_s']:.3f} s`",
        f"- Compact seal elapsed: `{timing['compact_seal_elapsed_s']:.3f} s`",
        f"- End-to-end elapsed: `{timing['end_to_end_elapsed_s']:.3f} s`",
        f"- End-to-end under 60 minutes: `{timing['under_60_minutes']}`",
        f"- Maximum concurrent ngspice processes: `{timing['resource_summary']['max_process_count']}`",
        f"- Maximum observed ngspice threads: `{timing['resource_summary']['max_total_threads']}`",
        "",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines), encoding="ascii")


def main():
    preflight = json.loads(
        (RESULT_DIR / "preflight_audit.json").read_text(encoding="ascii")
    )
    if not preflight["pass"]:
        raise RuntimeError("preflight audit did not pass")
    validation_started = parse_utc(preflight["validation_started_utc"])
    monitor = ResourceMonitor(validation_started)
    monitor.start()

    core_phase = run_phase(
        "CORE_MC12", CORE_SEEDS, 4, validation_started, monitor
    )
    core_valid_records = complete_records(CORE_SEEDS)
    elapsed_after_core = (
        datetime.now(timezone.utc) - validation_started
    ).total_seconds() + float(preflight["copy_elapsed_s"])
    optional_admitted = (
        core_phase.get("returncode") == 0
        and core_valid_records == 24
        and elapsed_after_core <= OPTIONAL_ADMISSION_S
    )
    if optional_admitted:
        optional_phase = run_phase(
            "OPTIONAL_2", OPTIONAL_SEEDS, 2, validation_started, monitor
        )
    else:
        optional_phase = {
            "label": "OPTIONAL_2",
            "launched": False,
            "reason": "CORE_FINISHED_AFTER_42_MIN_OR_INCOMPLETE",
            "returncode": None,
            "elapsed_s": 0.0,
        }

    monitor.phase = "QUICK_FINALIZE"
    finalize_started = datetime.now(timezone.utc)
    finalize_log = ROOT / "logs" / "runtime_validation_finalize.log"
    with finalize_log.open("w", encoding="utf-8") as log_handle:
        finalize = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "quick_finalize_v8.py")],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")},
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finalize_finished = datetime.now(timezone.utc)
    monitor.phase = "COMPACT_SEAL"
    seal_started = datetime.now(timezone.utc)
    manifest_audit = compact_manifest()
    seal_finished = datetime.now(timezone.utc)
    monitor.stop()
    write_resource_trace(monitor.rows)

    resource_summary = {
        "sample_count": len(monitor.rows),
        "max_process_count": max(
            (int(row["process_count"]) for row in monitor.rows), default=0
        ),
        "max_total_threads": max(
            (int(row["total_threads"]) for row in monitor.rows), default=0
        ),
        "max_threads_per_process": max(
            (int(row["max_threads_per_process"]) for row in monitor.rows),
            default=0,
        ),
        "max_total_rss_kb": max(
            (int(row["total_rss_kb"]) for row in monitor.rows), default=0
        ),
        "concurrency_limit_respected": all(
            int(row["process_count"]) <= 4 for row in monitor.rows
        ),
    }
    validation_finished = datetime.now(timezone.utc)
    continuous_elapsed_s = (
        validation_finished - validation_started
    ).total_seconds()
    end_to_end_s = float(preflight["copy_elapsed_s"]) + continuous_elapsed_s
    timing = {
        "validation_id": "A44_FAST64_D3_MC12_PLUS2_1H_V8",
        "validation_started_utc": validation_started.isoformat(),
        "validation_finished_utc": validation_finished.isoformat(),
        "copy_elapsed_s": preflight["copy_elapsed_s"],
        "preflight_audit_elapsed_s": preflight["preflight_audit_elapsed_s"],
        "operational_preflight_elapsed_s": preflight[
            "operational_preflight_elapsed_s"
        ],
        "core_phase": core_phase,
        "core_valid_records": core_valid_records,
        "elapsed_after_core_s": elapsed_after_core,
        "optional_admission_threshold_s": OPTIONAL_ADMISSION_S,
        "optional_admitted": optional_admitted,
        "optional_phase": optional_phase,
        "optional_valid_records": complete_records(OPTIONAL_SEEDS),
        "quick_finalize_returncode": finalize.returncode,
        "quick_finalize_elapsed_s": (
            finalize_finished - finalize_started
        ).total_seconds(),
        "compact_seal_elapsed_s": (seal_finished - seal_started).total_seconds(),
        "compact_manifest_audit": manifest_audit,
        "resource_summary": resource_summary,
        "end_to_end_elapsed_s": end_to_end_s,
        "end_to_end_elapsed_min": end_to_end_s / 60.0,
        "continuous_elapsed_after_copy_s": continuous_elapsed_s,
        "under_60_minutes": end_to_end_s < ONE_HOUR_S,
    }
    write_json_atomic(RESULT_DIR / "runtime_validation_timing.json", timing)
    append_timing_to_report(timing)
    quick_status_path = RESULT_DIR / "quick_status.json"
    if quick_status_path.is_file():
        quick_status = json.loads(quick_status_path.read_text(encoding="ascii"))
        quick_status["runtime_validation_under_60_minutes"] = timing[
            "under_60_minutes"
        ]
        quick_status["end_to_end_elapsed_s"] = timing["end_to_end_elapsed_s"]
        quick_status["concurrency_limit_respected"] = resource_summary[
            "concurrency_limit_respected"
        ]
        write_json_atomic(quick_status_path, quick_status)

    metadata_paths = {
        "timing": RESULT_DIR / "runtime_validation_timing.json",
        "report": REPORT_DIR / "FINAL_MC12_PLUS2_ONE_HOUR_REPORT.md",
        "quick_status": RESULT_DIR / "quick_status.json",
        "quick_audit": RESULT_DIR / "quick_audit.json",
        "compact_manifest": ROOT / "manifests" / "compact_manifest_sha256.csv",
        "compact_manifest_audit": RESULT_DIR / "compact_manifest_audit.json",
    }
    write_json_atomic(
        RESULT_DIR / "final_metadata_sha256.json",
        {
            key: {
                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for key, path in metadata_paths.items()
            if path.is_file()
        },
    )
    print(
        "VALIDATION_DONE total_min={:.3f} under_60={} core_s={:.3f} "
        "optional={} optional_s={:.3f} max_processes={}".format(
            timing["end_to_end_elapsed_min"],
            timing["under_60_minutes"],
            core_phase["elapsed_s"],
            optional_admitted,
            optional_phase["elapsed_s"],
            resource_summary["max_process_count"],
        ),
        flush=True,
    )
    success = all(
        (
            core_phase.get("returncode") == 0,
            core_valid_records == 24,
            finalize.returncode == 0,
            manifest_audit["pass"],
            resource_summary["concurrency_limit_respected"],
            timing["under_60_minutes"],
        )
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
