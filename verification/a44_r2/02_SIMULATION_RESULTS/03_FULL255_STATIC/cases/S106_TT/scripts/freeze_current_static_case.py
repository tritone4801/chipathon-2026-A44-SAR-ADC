#!/usr/bin/env python3
"""Audit and freeze one current-resizing FULL255 static case."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/current_static_case.json"
COMPARATOR = ROOT / "netlists/candidate/Comparator_StrongARM_CURRENT.subckt.spice"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    text = COMPARATOR.read_text(encoding="utf-8")
    widths = {
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
                rf"(?im)^{device}\b.*\bW={re.escape(str(width))}u\b", text
            )
        )
        for device, width in widths.items()
    }
    checks = {
        "candidate_hash_matches_declared": sha256(COMPARATOR)
        == config["candidate_comparator_sha256"],
        "all_declared_widths_match": all(width_checks.values()),
        "seed_is_positive_integer": isinstance(config["mismatch_seed"], int)
        and config["mismatch_seed"] > 0,
        "pvt_is_supported": config["pvt"]
        in {"TT_3P3_27C", "SS_3P0_125C", "FF_3P6_M40C"},
        "full255_method_frozen": config["method"]
        == "FULL_STATIC_FULL255_UPWARD_TWO_FRAME_50PS_BRACKET_0P02LSB",
        "targets_are_t1_through_t255": config["targets"] == "T1_THROUGH_T255",
    }
    payload = {
        "case": config,
        "candidate_path": str(COMPARATOR),
        "candidate_comparator_sha256": sha256(COMPARATOR),
        "width_checks": width_checks,
        "checks": checks,
        "pass": all(checks.values()),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": [
            "This is one deterministic seed/corner FULL255 curve.",
            "It is not a Monte Carlo yield population.",
        ],
    }
    path = ROOT / "results/setup_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not payload["pass"]:
        raise SystemExit("static case freeze audit failed")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
