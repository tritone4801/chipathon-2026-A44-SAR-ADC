#!/usr/bin/env python3
"""Record ngspice process/thread/RSS use until the full-run exit marker appears."""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sar_campaign_common import ROOT


def snapshot():
    processes = []
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text(encoding="ascii").strip() != "ngspice":
                continue
            status = {}
            for line in (comm.parent / "status").read_text(encoding="ascii").splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    status[key] = value.strip()
            processes.append(
                {
                    "pid": int(comm.parent.name),
                    "threads": int(status.get("Threads", "0")),
                    "rss_kb": int(status.get("VmRSS", "0 kB").split()[0]),
                }
            )
        except (FileNotFoundError, ProcessLookupError, ValueError):
            continue
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "process_count": len(processes),
        "total_threads": sum(row["threads"] for row in processes),
        "total_rss_kb": sum(row["rss_kb"] for row in processes),
        "pids": ";".join(str(row["pid"]) for row in processes),
    }


def main() -> int:
    marker = ROOT / "results" / "full_mc200_exit_code.txt"
    rows = []
    while not marker.is_file():
        rows.append(snapshot())
        time.sleep(2.0)
    rows.append(snapshot())
    output = ROOT / "csv" / "full_mc200_resource_trace.csv"
    with output.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "RESOURCE_TRACE_COMPLETE",
        "samples": len(rows),
        "max_ngspice_processes": max(row["process_count"] for row in rows),
        "max_total_threads": max(row["total_threads"] for row in rows),
        "max_total_rss_kb": max(row["total_rss_kb"] for row in rows),
        "first_sample_utc": rows[0]["timestamp_utc"],
        "last_sample_utc": rows[-1]["timestamp_utc"],
    }
    (ROOT / "results" / "full_mc200_resource_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
