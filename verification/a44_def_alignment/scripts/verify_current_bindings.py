#!/usr/bin/env python3
"""Verify the repository's active layout paths and GDS top/bbox bindings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_def_alignment import parse_gds


def close(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    current = json.loads((repo / "layout/CURRENT_LAYOUT.json").read_text(encoding="utf-8"))
    lvs = json.loads((repo / "lvs_config.json").read_text(encoding="utf-8"))

    entries = [
        {
            "role": "PROJECT_TOP",
            "gds": current["repository_top"]["gds"],
            "top": current["repository_top"]["design"],
            "bbox_um": current["repository_top"]["bbox_um"],
        },
        {
            "role": "CORE",
            "gds": current["embedded_core"]["public_gds"],
            "top": current["embedded_core"]["contract_cell"],
            "bbox_um": current["embedded_core"]["bbox_um"],
        },
        *current["components"],
    ]

    records = []
    for entry in entries:
        path = repo / entry["gds"]
        parsed = parse_gds(path, entry["top"])
        bbox_ok = all(
            close(actual, expected)
            for actual, expected in zip(parsed["bbox_um"], entry["bbox_um"])
        )
        records.append(
            {
                "role": entry["role"],
                "path": entry["gds"],
                "file_exists": path.is_file(),
                "top": entry["top"],
                "bbox_um": parsed["bbox_um"],
                "bbox_exact": bbox_ok,
            }
        )

    expected_root_gds = {"A44_A.gds", "A44_SAR_ADC_CORE_1000.gds"}
    expected_component_gds = {
        Path(entry["gds"]).name for entry in current["components"]
    }
    actual_root_gds = {path.name for path in (repo / "gds").glob("*.gds")}
    actual_component_gds = {
        path.name for path in (repo / "gds/components").glob("*.gds")
    }
    expected_images = expected_component_gds | {"A44_SAR_ADC_CORE_1000.gds"}
    expected_images = {Path(name).with_suffix(".png").name for name in expected_images}
    actual_images = {path.name for path in (repo / "layout/images").glob("*.png")}

    checks = {
        "lvs_top_source_a44_a": lvs.get("TOP_SOURCE") == "A44_A",
        "lvs_top_layout_follows_source": lvs.get("TOP_LAYOUT") == "$TOP_SOURCE",
        "lvs_gds_path_current": lvs.get("LAYOUT_FILE") == "$UPRJ_ROOT/gds/A44_A.gds",
        "lvs_reference_path_current": lvs.get("LVS_SPICE_FILES")
        == ["$UPRJ_ROOT/verification/a44_def_alignment/spice/A44_A_lvs_reference.spice"],
        "all_declared_files_exist": all(record["file_exists"] for record in records),
        "all_declared_bboxes_exact": all(record["bbox_exact"] for record in records),
        "active_root_gds_set_exact": actual_root_gds == expected_root_gds,
        "active_component_gds_set_exact": actual_component_gds == expected_component_gds,
        "active_layout_image_set_exact": actual_images == expected_images,
        "top_def_exists": (repo / current["repository_top"]["def"]).is_file(),
        "top_lef_exists": (repo / current["repository_top"]["lef"]).is_file(),
        "top_mag_exists": (repo / current["repository_top"]["mag"]).is_file(),
    }
    result = {
        "schema": "a44-current-layout-binding-verification-v1",
        "status": "PASS_CURRENT_BINDINGS" if all(checks.values()) else "FAIL_CURRENT_BINDINGS",
        "pass": all(checks.values()),
        "checks": checks,
        "gds_records": records,
        "active_sets": {
            "root_gds": sorted(actual_root_gds),
            "component_gds": sorted(actual_component_gds),
            "layout_images": sorted(actual_images),
        },
        "notes": [
            "Active repository paths are checked separately from preserved legacy and verification evidence.",
            "No file hashes and no circuit simulations are used by this check."
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
