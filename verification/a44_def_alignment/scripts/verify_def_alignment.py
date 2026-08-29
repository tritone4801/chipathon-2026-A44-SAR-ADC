#!/usr/bin/env python3
"""Compare the published A44_A GDS interface with the official DEF.

The check is intentionally lightweight: it does not calculate file hashes and
does not run simulations.  It verifies the logical DEF contract, every fixed
pin rectangle, its matching top-level GDS label/metal coverage, the top-level
boundary, and the frozen CORE placement.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path


def real8(data: bytes) -> float:
    if len(data) != 8 or not any(data):
        return 0.0
    sign = -1 if data[0] & 0x80 else 1
    exponent = (data[0] & 0x7F) - 64
    mantissa = int.from_bytes(data[1:], "big") / (1 << 56)
    return sign * mantissa * (16.0**exponent)


def scalar(text: str, pattern: str, label: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not match:
        raise ValueError(f"missing {label}")
    return match.group(1)


def report_path(path: Path) -> str:
    """Prefer a portable repository-relative path in published reports."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(resolved)


def def_pin_section(text: str) -> str:
    match = re.search(
        r"(?ims)^\s*PINS\s+\d+\s*;.*?^\s*END\s+PINS\s*$", text
    )
    if not match:
        raise ValueError("missing PINS section")
    return match.group(0)


def parse_def(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    units = int(
        scalar(
            text,
            r"^\s*UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;",
            "DEF units",
        )
    )
    diearea_raw = scalar(text, r"^\s*DIEAREA\s+(.+?)\s*;", "DIEAREA")
    diearea = [
        [int(x), int(y)]
        for x, y in re.findall(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)", diearea_raw)
    ]
    section = def_pin_section(text)
    entries = re.findall(r"(?ms)^\s*-\s+.*?;", section)
    pins = []
    for entry in entries:
        name_match = re.match(r"\s*-\s+(\S+)", entry)
        if not name_match:
            continue
        fixed_match = re.search(
            r"\+\s+(?:FIXED|PLACED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)",
            entry,
            re.IGNORECASE,
        )
        if not fixed_match:
            raise ValueError(f"pin {name_match.group(1)} has no fixed placement")
        fixed_x, fixed_y = int(fixed_match.group(1)), int(fixed_match.group(2))
        rects = []
        for layer, x1, y1, x2, y2 in re.findall(
            r"\+\s+LAYER\s+(\S+)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+"
            r"\(\s*(-?\d+)\s+(-?\d+)\s*\)",
            entry,
            re.IGNORECASE,
        ):
            rects.append(
                {
                    "layer": layer,
                    "rect_db": [
                        int(x1) + fixed_x,
                        int(y1) + fixed_y,
                        int(x2) + fixed_x,
                        int(y2) + fixed_y,
                    ],
                }
            )
        if not rects:
            raise ValueError(f"pin {name_match.group(1)} has no layer rectangles")
        fields = {}
        for key in ("NET", "DIRECTION", "USE"):
            match = re.search(rf"\+\s+{key}\s+(\S+)", entry, re.IGNORECASE)
            fields[key.lower()] = match.group(1) if match else None
        pins.append(
            {
                "name": name_match.group(1),
                **fields,
                "placement": [fixed_x, fixed_y, fixed_match.group(3)],
                "rects": rects,
            }
        )
    return {
        "text": text,
        "pin_section": section,
        "design": scalar(text, r"^\s*DESIGN\s+(\S+)\s*;", "DESIGN"),
        "units": units,
        "diearea_db": diearea,
        "pins": pins,
    }


def parse_gds(path: Path, top_name: str) -> dict:
    data = path.read_bytes()
    index = 0
    units = None
    structures = {}
    current = None
    element = None
    record_names = {
        3: "UNITS",
        5: "BGNSTR",
        6: "STRNAME",
        7: "ENDSTR",
        8: "BOUNDARY",
        9: "PATH",
        10: "SREF",
        11: "AREF",
        12: "TEXT",
        13: "LAYER",
        14: "DATATYPE",
        15: "WIDTH",
        16: "XY",
        17: "ENDEL",
        18: "SNAME",
        22: "TEXTTYPE",
        25: "STRING",
        26: "STRANS",
        28: "ANGLE",
    }
    while index + 4 <= len(data):
        length, record_type, _ = struct.unpack(">HBB", data[index : index + 4])
        if length < 4 or index + length > len(data):
            raise ValueError(f"bad GDS record at byte {index}")
        payload = data[index + 4 : index + length]
        name = record_names.get(record_type)
        if name == "UNITS":
            units = (real8(payload[:8]), real8(payload[8:16]))
        elif name == "BGNSTR":
            current = {"name": None, "elements": []}
        elif name == "STRNAME":
            current["name"] = payload.rstrip(b"\0").decode("ascii", "replace")
            structures[current["name"]] = current
        elif name == "ENDSTR":
            current = None
            element = None
        elif name in ("BOUNDARY", "PATH", "SREF", "AREF", "TEXT"):
            element = {
                "type": name,
                "layer": None,
                "datatype": None,
                "texttype": None,
                "width": 0,
                "xy": [],
                "sname": None,
                "string": None,
                "strans": 0,
                "angle": 0.0,
            }
            if current is not None:
                current["elements"].append(element)
        elif element is not None:
            if name == "LAYER":
                element["layer"] = struct.unpack(">h", payload[:2])[0]
            elif name == "DATATYPE":
                element["datatype"] = struct.unpack(">h", payload[:2])[0]
            elif name == "TEXTTYPE":
                element["texttype"] = struct.unpack(">h", payload[:2])[0]
            elif name == "WIDTH":
                element["width"] = struct.unpack(">i", payload[:4])[0]
            elif name == "XY":
                element["xy"] = [
                    struct.unpack(">ii", payload[offset : offset + 8])
                    for offset in range(0, len(payload) - 7, 8)
                ]
            elif name == "SNAME":
                element["sname"] = payload.rstrip(b"\0").decode("ascii", "replace")
            elif name == "STRING":
                element["string"] = payload.rstrip(b"\0").decode("ascii", "replace")
            elif name == "STRANS":
                element["strans"] = struct.unpack(">H", payload[:2])[0]
            elif name == "ANGLE":
                element["angle"] = real8(payload[:8])
            elif name == "ENDEL":
                element = None
        index += length
    if top_name not in structures:
        raise ValueError(f"GDS top {top_name} not found")
    user_unit_um = (units[0] if units else 0.001)
    top = structures[top_name]
    shapes = []
    labels = []
    refs = []
    all_points = []
    for item in top["elements"]:
        if item["type"] in ("BOUNDARY", "PATH") and item["xy"]:
            xs = [point[0] for point in item["xy"]]
            ys = [point[1] for point in item["xy"]]
            half_width = abs(item["width"]) / 2 if item["type"] == "PATH" else 0
            bbox_db = [
                min(xs) - half_width,
                min(ys) - half_width,
                max(xs) + half_width,
                max(ys) + half_width,
            ]
            shapes.append(
                {
                    "type": item["type"],
                    "layer": item["layer"],
                    "datatype": item["datatype"],
                    "bbox_um": [value * user_unit_um for value in bbox_db],
                }
            )
            all_points.extend(item["xy"])
        elif item["type"] == "TEXT" and item["xy"]:
            labels.append(
                {
                    "name": item["string"],
                    "layer": item["layer"],
                    "texttype": item["texttype"],
                    "xy_um": [
                        item["xy"][0][0] * user_unit_um,
                        item["xy"][0][1] * user_unit_um,
                    ],
                }
            )
        elif item["type"] == "SREF" and item["xy"]:
            refs.append(
                {
                    "cell": item["sname"],
                    "origin_um": [
                        item["xy"][0][0] * user_unit_um,
                        item["xy"][0][1] * user_unit_um,
                    ],
                    "angle": item["angle"],
                    "reflected": bool(item["strans"] & 0x8000),
                }
            )
    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    bbox_um = [
        min(xs) * user_unit_um,
        min(ys) * user_unit_um,
        max(xs) * user_unit_um,
        max(ys) * user_unit_um,
    ]
    return {
        "units": units,
        "structure_count": len(structures),
        "bbox_um": bbox_um,
        "shapes": shapes,
        "labels": labels,
        "refs": refs,
    }


def close(left: float, right: float, tolerance: float = 0.0011) -> bool:
    return abs(left - right) <= tolerance


def contains(outer: list[float], inner: list[float]) -> bool:
    tolerance = 0.0011
    return (
        outer[0] <= inner[0] + tolerance
        and outer[1] <= inner[1] + tolerance
        and outer[2] >= inner[2] - tolerance
        and outer[3] >= inner[3] - tolerance
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-def", required=True, type=Path)
    parser.add_argument("--final-def", required=True, type=Path)
    parser.add_argument("--gds", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    args = parser.parse_args()

    official = parse_def(args.official_def)
    final = parse_def(args.final_def)
    gds = parse_gds(args.gds, "A44_A")

    def_signature_fields = ("name", "net", "direction", "use", "placement", "rects")
    official_signatures = [tuple(json.dumps(pin[key], sort_keys=True) for key in def_signature_fields) for pin in official["pins"]]
    final_signatures = [tuple(json.dumps(pin[key], sort_keys=True) for key in def_signature_fields) for pin in final["pins"]]

    labels_by_name = defaultdict(list)
    for label in gds["labels"]:
        if label["layer"] == 36 and label["texttype"] == 10:
            labels_by_name[label["name"]].append(label)
    metal2_shapes = [shape for shape in gds["shapes"] if shape["layer"] == 36]

    die_ll, die_ur = official["diearea_db"]
    diearea_um = [
        die_ll[0] / official["units"],
        die_ll[1] / official["units"],
        die_ur[0] / official["units"],
        die_ur[1] / official["units"],
    ]
    rows = []
    for pin in official["pins"]:
        sides = set()
        matched_shapes = 0
        expected_centers = []
        for rect_entry in pin["rects"]:
            rect_db = rect_entry["rect_db"]
            rect_um = [value / official["units"] for value in rect_db]
            center = [(rect_um[0] + rect_um[2]) / 2, (rect_um[1] + rect_um[3]) / 2]
            expected_centers.append(center)
            if rect_db[0] == die_ll[0]:
                sides.add("WEST")
            if rect_db[2] == die_ur[0]:
                sides.add("EAST")
            if rect_db[1] == die_ll[1]:
                sides.add("SOUTH")
            if rect_db[3] == die_ur[1]:
                sides.add("NORTH")
            label_ok = any(
                close(label["xy_um"][0], center[0])
                and close(label["xy_um"][1], center[1])
                for label in labels_by_name[pin["name"]]
            )
            metal_ok = any(contains(shape["bbox_um"], rect_um) for shape in metal2_shapes)
            if label_ok and metal_ok:
                matched_shapes += 1
        rows.append(
            {
                "pin": pin["name"],
                "direction": pin["direction"],
                "use": pin["use"],
                "side": "+".join(sorted(sides)) or "INTERIOR",
                "def_shape_count": len(pin["rects"]),
                "gds_label_count": len(labels_by_name[pin["name"]]),
                "matched_shape_count": matched_shapes,
                "status": "PASS" if matched_shapes == len(pin["rects"]) else "FAIL",
            }
        )

    child_refs = [
        ref
        for ref in gds["refs"]
        if ref["cell"] == "A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR"
    ]
    side_counts = Counter(row["side"] for row in rows)
    checks = {
        "design_exact": official["design"] == final["design"] == "A44_A",
        "units_exact": official["units"] == final["units"] == 200,
        "diearea_exact": official["diearea_db"] == final["diearea_db"] == [[0, 0], [222000, 222000]],
        "pin_section_exact": official["pin_section"] == final["pin_section"],
        "pin_contract_exact": official_signatures == final_signatures,
        "logical_pin_count_89": len(official["pins"]) == len(final["pins"]) == 89,
        "pin_shape_count_127": sum(len(pin["rects"]) for pin in official["pins"]) == 127,
        "gds_top_bbox_exact": all(close(left, right) for left, right in zip(gds["bbox_um"], diearea_um)),
        "gds_pin_labels_127": sum(len(labels_by_name[pin["name"]]) for pin in official["pins"]) == 127,
        "all_pin_shapes_attached": all(row["status"] == "PASS" for row in rows),
        "core_single_instance": len(child_refs) == 1,
        "core_origin_55_55": len(child_refs) == 1
        and all(close(left, right) for left, right in zip(child_refs[0]["origin_um"], [55.0, 55.0])),
        "core_orientation_r0": len(child_refs) == 1
        and close(child_refs[0]["angle"], 0.0)
        and not child_refs[0]["reflected"],
    }
    result = {
        "schema": "a44-def-alignment-verification-v1",
        "status": "PASS_DEF_ALIGNED" if all(checks.values()) else "FAIL_DEF_ALIGNMENT",
        "pass": all(checks.values()),
        "authority": {
            "official_def": report_path(args.official_def),
            "final_def": report_path(args.final_def),
            "gds": report_path(args.gds),
        },
        "top": {
            "name": "A44_A",
            "origin_um": [0.0, 0.0],
            "bbox_um": gds["bbox_um"],
            "width_um": gds["bbox_um"][2] - gds["bbox_um"][0],
            "height_um": gds["bbox_um"][3] - gds["bbox_um"][1],
        },
        "pins": {
            "logical_count": len(rows),
            "shape_count": sum(row["def_shape_count"] for row in rows),
            "matched_shape_count": sum(row["matched_shape_count"] for row in rows),
            "side_counts": dict(sorted(side_counts.items())),
        },
        "core": child_refs,
        "checks": checks,
        "notes": [
            "Every official DEF pin rectangle is covered by top-level Metal2 and has a same-name GDS label at the rectangle center.",
            "No SHA-256 or full-manifest audit was performed.",
            "No conversion or performance simulation was run.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with args.out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": result["status"], "checks": checks}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
