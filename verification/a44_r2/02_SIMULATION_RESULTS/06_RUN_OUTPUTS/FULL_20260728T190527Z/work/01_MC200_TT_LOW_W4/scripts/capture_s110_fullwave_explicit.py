#!/usr/bin/env python3
"""Fallback raw capture using an explicit ngspice write command in the diagnostic deck."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sar_campaign_common import ROOT, run_deck


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    source_deck = (
        ROOT
        / "jobs"
        / "v7"
        / "repeatability_fullwave_s110"
        / "s110_fullwave_audit_s110_low_050ps.spice"
    )
    raw_path = (
        ROOT
        / "raw"
        / "full_waveform_audit"
        / "s110_low_050ps_explicit_all_vectors.raw"
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    deck = source_deck.read_text(encoding="ascii")
    marker = "quit\n.endc"
    if deck.count(marker) != 1:
        raise RuntimeError("diagnostic deck does not have one control-section quit")
    explicit_deck = deck.replace(
        marker,
        f"write {raw_path.as_posix()} all\nquit\n.endc",
    )
    result = run_deck(
        explicit_deck,
        "s110_fullwave_explicit_all_vectors",
        ROOT / "jobs" / "v7" / "repeatability_fullwave_s110",
        ROOT / "logs" / "v7" / "repeatability_fullwave_s110",
        timeout_s=7200,
    )
    with (
        ROOT
        / "diagnostics"
        / "s110_fullwave"
        / "fullwave_codes.csv"
    ).open(newline="", encoding="utf-8-sig") as handle:
        codes = list(csv.DictReader(handle))
    passed = (
        result["returncode"] == 0
        and not result["timed_out"]
        and not result["simulation_aborted"]
        and raw_path.is_file()
        and raw_path.stat().st_size > 1024
    )
    audit = {
        "status": (
            "PASS_S110_FULLWAVE_CAPTURE"
            if passed
            else "FAIL_S110_FULLWAVE_CAPTURE"
        ),
        "pass": passed,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 110,
        "band": "LOW",
        "maxstep_ps": 50,
        "solver_profile": "ROBUST_GEAR",
        "frame0_code": int(codes[0]["code"]),
        "raw_path": raw_path.relative_to(ROOT).as_posix() if raw_path.is_file() else "",
        "raw_size_bytes": raw_path.stat().st_size if raw_path.is_file() else 0,
        "raw_sha256": sha256(raw_path) if raw_path.is_file() else "",
        "explicit_deck": result["deck"].relative_to(ROOT).as_posix(),
        "explicit_log": result["log"].relative_to(ROOT).as_posix(),
        "returncode": result["returncode"],
        "timed_out": result["timed_out"],
        "simulation_aborted": result["simulation_aborted"],
        "initial_dash_r_capture_created_no_file": True,
        "fallback_method": "NGSPICE_CONTROL_WRITE_ALL",
        "main_population_was_not_modified": True,
    }
    (ROOT / "results" / "s110_fullwave_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
