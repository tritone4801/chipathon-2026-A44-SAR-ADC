#!/usr/bin/env python3
"""Read-only validation for the A44 Chipathon 2026 DRC dry-run package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import klayout.db as kdb


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOP = "A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    manifest_rows: list[dict[str, object]] = []

    for line in (HERE / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            failures.append(f"malformed manifest line: {line}")
            continue
        expected, relative = match.groups()
        path = (HERE / relative).resolve()
        if not path.is_relative_to(ROOT):
            failures.append(f"manifest path escapes repository: {relative}")
            continue
        actual = sha256(path) if path.is_file() else None
        passed = actual == expected
        if not passed:
            failures.append(f"manifest mismatch: {relative}")
        manifest_rows.append(
            {"path": relative, "expected": expected, "actual": actual, "pass": passed}
        )

    config = json.loads((ROOT / "lvs_config.json").read_text(encoding="utf-8"))
    expected_config = {
        "TOP_SOURCE": TOP,
        "TOP_LAYOUT": "$TOP_SOURCE",
        "LAYOUT_FILE": "$UPRJ_ROOT/gds/$TOP_LAYOUT.gds",
    }
    for key, expected in expected_config.items():
        if config.get(key) != expected:
            failures.append(f"lvs_config {key} mismatch")

    spice_relative = "netlists/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.spice"
    if config.get("LVS_SPICE_FILES") != [f"$UPRJ_ROOT/{spice_relative}"]:
        failures.append("lvs_config LVS_SPICE_FILES mismatch")

    info_text = (ROOT / "info.yaml").read_text(encoding="utf-8")
    if not re.search(r'^\s*lvs_config:\s*"lvs_config\.json"\s*$', info_text, re.MULTILINE):
        failures.append("info.yaml does not bind root lvs_config.json")

    spice_text = (ROOT / spice_relative).read_text(encoding="utf-8", errors="strict")
    spice_header = re.search(
        rf"^\.subckt\s+{re.escape(TOP)}\s+(.+?)\n(?=\S)",
        spice_text,
        re.MULTILINE | re.DOTALL,
    )
    if spice_header is None:
        failures.append("SPICE top subcircuit missing")

    lef_text = (ROOT / f"lef/{TOP}.lef").read_text(encoding="utf-8")
    if f"MACRO {TOP}" not in lef_text or "SIZE 1000.000 BY 1000.000" not in lef_text:
        failures.append("LEF macro name or size mismatch")

    layout = kdb.Layout()
    layout.read(str(ROOT / f"gds/{TOP}.gds"))
    top_names = sorted(cell.name for cell in layout.top_cells())
    cell = layout.cell(TOP)
    bbox = cell.bbox() if cell is not None else None
    expected_bbox = kdb.Box(0, 0, 1_000_000, 1_000_000)
    if top_names != [TOP]:
        failures.append(f"unexpected GDS top cells: {top_names}")
    if layout.dbu != 0.001:
        failures.append(f"unexpected GDS DBU: {layout.dbu}")
    if bbox != expected_bbox:
        failures.append(f"unexpected GDS bbox: {bbox}")

    receipt = json.loads((HERE / "SUBMISSION.json").read_text(encoding="utf-8"))
    if receipt.get("design", {}).get("top_layout") != TOP:
        failures.append("SUBMISSION.json top layout mismatch")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "manifest": manifest_rows,
        "top_cell": top_names,
        "dbu_um": layout.dbu,
        "bbox_dbu": None if bbox is None else [bbox.left, bbox.bottom, bbox.right, bbox.top],
        "failures": failures,
        "claim_boundary": "Read-only package consistency check; not organizer DRC/LVS acceptance or signoff.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
