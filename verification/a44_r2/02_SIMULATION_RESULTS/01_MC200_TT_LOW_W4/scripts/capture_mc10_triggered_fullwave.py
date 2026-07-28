#!/usr/bin/env python3
"""Capture full waveforms only for targets selected by the diagnostic trigger audit."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from run_v7 import run_record
from sar_campaign_common import ROOT, load_cdac_weights, run_deck
from v7_common import CONFIG_DIR, load_manifest_checksums


TARGETS = ROOT / "diagnostics" / "fullwave_trigger_targets.csv"
OUTPUT = ROOT / "diagnostics" / "fullwave"
RAW_ROOT = ROOT / "raw" / "full_waveform_audit"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    targets = read_csv(TARGETS)
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    audits = []
    for target in targets:
        seed = int(target["mismatch_seed"])
        band = target["band"]
        stem = f"triggered_fullwave_s{seed:03d}_{band.lower()}"
        row, codes = run_record(
            grouped,
            timing,
            seed,
            band,
            50,
            "triggered_fullwave",
            "MC10_TRIGGERED_FULLWAVE",
            mismatch_checksums,
            noise_checksums,
            preserve_raw=True,
        )
        run_root = OUTPUT / stem
        write_csv(run_root / "fullwave_master.csv", [row])
        write_csv(run_root / "fullwave_codes.csv", codes)

        raw_path = ROOT / row["raw_path"] if row["raw_path"] else None
        fallback_used = False
        explicit_deck = ""
        explicit_log = ""
        if raw_path is None or not raw_path.is_file():
            fallback_used = True
            raw_path = RAW_ROOT / f"{stem}_explicit_all_vectors.raw"
            source_deck = ROOT / row["deck"]
            deck = source_deck.read_text(encoding="ascii")
            marker = "quit\n.endc"
            if deck.count(marker) != 1:
                raise RuntimeError(
                    f"{source_deck} does not have one control-section quit"
                )
            explicit = deck.replace(
                marker,
                f"write {raw_path.as_posix()} all\nquit\n.endc",
            )
            result = run_deck(
                explicit,
                f"{stem}_explicit_all_vectors",
                ROOT / "jobs" / "v7" / "mc10_triggered_fullwave",
                ROOT / "logs" / "v7" / "mc10_triggered_fullwave",
                timeout_s=7200,
            )
            explicit_deck = result["deck"].relative_to(ROOT).as_posix()
            explicit_log = result["log"].relative_to(ROOT).as_posix()
            fallback_ok = (
                result["returncode"] == 0
                and not result["timed_out"]
                and not result["simulation_aborted"]
            )
        else:
            fallback_ok = True
        passed = (
            row["state"] in {"VALID_PASS", "VALID_FAIL"}
            and len(codes) == 64
            and fallback_ok
            and raw_path.is_file()
            and raw_path.stat().st_size > 1024
        )
        audits.append(
            {
                "mismatch_seed": seed,
                "band": band,
                "trigger_reasons": target["reasons"],
                "status": "PASS_FULLWAVE_CAPTURE" if passed else "FAIL_FULLWAVE_CAPTURE",
                "state": row["state"],
                "sndr_db": row["sndr_db"],
                "frame0": codes[0]["code"] if codes else "",
                "compact_code_checksum_sha256": row[
                    "compact_code_checksum_sha256"
                ],
                "raw_path": (
                    raw_path.relative_to(ROOT).as_posix()
                    if raw_path.is_file()
                    else ""
                ),
                "raw_size_bytes": raw_path.stat().st_size if raw_path.is_file() else 0,
                "raw_sha256": sha256(raw_path) if raw_path.is_file() else "",
                "fallback_explicit_write_all": fallback_used,
                "deck": row["deck"],
                "log": row["log"],
                "explicit_deck": explicit_deck,
                "explicit_log": explicit_log,
            }
        )
    write_csv(
        OUTPUT / "fullwave_index.csv",
        audits,
        (
            "mismatch_seed",
            "band",
            "trigger_reasons",
            "status",
            "state",
            "sndr_db",
            "frame0",
            "compact_code_checksum_sha256",
            "raw_path",
            "raw_size_bytes",
            "raw_sha256",
            "fallback_explicit_write_all",
            "deck",
            "log",
            "explicit_deck",
            "explicit_log",
        ),
    )
    status = {
        "status": (
            "PASS_TRIGGERED_FULLWAVE_CAPTURE"
            if all(item["status"] == "PASS_FULLWAVE_CAPTURE" for item in audits)
            else "FAIL_TRIGGERED_FULLWAVE_CAPTURE"
        ),
        "pass": bool(audits)
        and all(item["status"] == "PASS_FULLWAVE_CAPTURE" for item in audits),
        "target_count": len(targets),
        "captured_count": sum(
            item["status"] == "PASS_FULLWAVE_CAPTURE" for item in audits
        ),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "main_population_was_not_modified": True,
        "captures": audits,
    }
    (ROOT / "results" / "triggered_fullwave_audit.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, indent=2))
    return 0 if status["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
