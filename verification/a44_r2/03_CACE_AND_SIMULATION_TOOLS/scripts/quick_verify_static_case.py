#!/usr/bin/env python3
"""Re-run the first five FULL255 transition brackets for one frozen case."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--transition-count", type=int, default=5)
    args = parser.parse_args()

    case_root = args.case_root.resolve()
    output = args.output.resolve()
    sys.path.insert(0, str(case_root / "scripts"))

    import run_paired_static as runner  # type: ignore

    baseline_path = (
        case_root / "csv" / "current_s116_transitions_up.csv"
    )
    baseline = read_csv(baseline_path)[: args.transition_count]
    if len(baseline) != args.transition_count:
        raise SystemExit(
            f"{case_root.name}: baseline has {len(baseline)} transition rows"
        )
    frames_per_point = int(float(baseline[0]["frames_per_point"]))
    if any(
        int(float(row["frames_per_point"])) != frames_per_point
        for row in baseline
    ):
        raise SystemExit(f"{case_root.name}: mixed frames_per_point")

    points: list[dict[str, Any]] = []
    for row in baseline:
        target = int(float(row["target_transition"]))
        points.extend(
            [
                {
                    "target": target,
                    "role": "low",
                    "vid_v": float(row["lower_v"]),
                },
                {
                    "target": target,
                    "role": "high",
                    "vid_v": float(row["upper_v"]),
                },
            ]
        )

    vids: list[float] = []
    for point in points:
        vids.extend([float(point["vid_v"])] * frames_per_point)
    deck = runner.build_variant_deck("CURRENT", vids)
    run = runner.common.run_deck(
        deck,
        f"{case_root.name.lower()}_first5_brackets",
        output / "jobs",
        output / "logs",
        timeout_s=1800,
        cache_completed_failure=False,
    )
    frames = runner.common.decode_frames(
        run,
        len(vids),
        runner.common.PVT_CASES[runner.PVT]["vdd_v"],
        runner.common.FRAME_DEFAULT_S,
    )

    actual_by_target: dict[int, dict[str, Any]] = {}
    for point_index, point in enumerate(points):
        start = point_index * frames_per_point
        selected = frames[start : start + frames_per_point]
        actual_by_target.setdefault(point["target"], {})[point["role"]] = {
            "code": int(selected[-1]["code"]),
            "valid": all(bool(frame["valid"]) for frame in selected),
            "conditioning_codes": [
                int(frame["code"]) for frame in selected[:-1]
            ],
            "formal_bits": selected[-1]["bits"],
            "formal_stable_margin_ns": (
                float(selected[-1]["stable_margin_s"]) * 1e9
            ),
        }

    rows: list[dict[str, Any]] = []
    for reference in baseline:
        target = int(float(reference["target_transition"]))
        actual = actual_by_target[target]
        expected_low = int(float(reference["lower_code"]))
        expected_high = int(float(reference["upper_code"]))
        low_code = int(actual["low"]["code"])
        high_code = int(actual["high"]["code"])
        low_match = low_code == expected_low
        high_match = high_code == expected_high
        bracket_valid = low_code < target <= high_code
        valid = bool(actual["low"]["valid"]) and bool(actual["high"]["valid"])
        row_pass = (
            int(run["returncode"]) == 0
            and not bool(run.get("simulation_aborted"))
            and valid
            and low_match
            and high_match
            and bracket_valid
        )
        rows.append(
            {
                "case": case_root.name,
                "pvt": runner.PVT,
                "mismatch_seed": runner.SEED,
                "target_transition": target,
                "baseline_status": reference["status"],
                "lower_v": float(reference["lower_v"]),
                "upper_v": float(reference["upper_v"]),
                "baseline_transition_v": float(reference["transition_v"]),
                "expected_lower_code": expected_low,
                "actual_lower_code": low_code,
                "lower_code_match": low_match,
                "expected_upper_code": expected_high,
                "actual_upper_code": high_code,
                "upper_code_match": high_match,
                "actual_bracket_valid": bracket_valid,
                "all_frames_valid": valid,
                "returncode": int(run["returncode"]),
                "simulation_aborted": bool(run.get("simulation_aborted")),
                "row_pass": row_pass,
                "early_stop": "STOP_AFTER_FIRST_5_TRANSITION_BRACKETS",
                "deck": str(run["deck"]),
                "log": str(run["log"]),
            }
        )

    passed = all(row["row_pass"] for row in rows)
    write_csv(output / "static_first5_comparison.csv", rows)
    summary = {
        "status": (
            "PASS_STATIC_FIRST5_REPRODUCIBLE"
            if passed
            else "FAIL_STATIC_FIRST5_REPRODUCIBILITY"
        ),
        "pass": passed,
        "case": case_root.name,
        "pvt": runner.PVT,
        "mismatch_seed": runner.SEED,
        "transition_count": len(rows),
        "matching_transition_count": sum(
            bool(row["row_pass"]) for row in rows
        ),
        "frames_per_bracket_point": frames_per_point,
        "returncode": int(run["returncode"]),
        "elapsed_s": float(run["elapsed_s"]),
        "early_stop_method": (
            "The exact historical lower/upper bracket points for transitions "
            "1-5 are replayed. Once both decision codes match, transitions "
            "6-255 are not scheduled for quick verification."
        ),
        "completed_utc": utc_now(),
    }
    write_json(output / "static_first5_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
