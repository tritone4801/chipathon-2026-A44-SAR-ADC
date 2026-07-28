#!/usr/bin/env python3
"""Analyze one current-resizing FULL255 transition curve."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT / "config/current_static_case.json").read_text(encoding="utf-8")
)
TRANSITIONS = ROOT / "csv/current_s116_transitions_up.csv"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with TRANSITIONS.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows.sort(key=lambda row: int(row["target_transition"]))
    if len(rows) != 255 or [int(row["target_transition"]) for row in rows] != list(
        range(1, 256)
    ):
        raise SystemExit("FULL255 transition set is incomplete")
    if any(row["status"] != "PASS" for row in rows):
        raise SystemExit("FULL255 contains failed transition searches")
    t = np.asarray([float(row["transition_v"]) for row in rows])
    lower = np.asarray([float(row["lower_v"]) for row in rows])
    upper = np.asarray([float(row["upper_v"]) for row in rows])
    bracket = np.asarray([float(row["final_bracket_width_lsb"]) for row in rows])
    q_ep = (t[-1] - t[0]) / 254.0
    widths = np.diff(t)
    dnl = widths / q_ep - 1.0
    ideal = t[0] + np.arange(255) * q_ep
    inl = (t - ideal) / q_ep
    width_rows = []
    for code, width, value in zip(range(1, 255), widths, dnl):
        width_rows.append(
            {
                "code": code,
                "width_v": float(width),
                "width_mV": float(width * 1e3),
                "width_lsb": float(width / q_ep),
                "dnl_ep_lsb": float(value),
            }
        )
    transition_rows = []
    for target, lo, center, hi, value in zip(
        range(1, 256), lower, t, upper, inl
    ):
        transition_rows.append(
            {
                "target_transition": target,
                "lower_v": float(lo),
                "transition_v": float(center),
                "upper_v": float(hi),
                "inl_ep_lsb": float(value),
            }
        )
    write_csv(ROOT / "csv/current_full255_code_widths.csv", width_rows)
    write_csv(ROOT / "csv/current_full255_inl.csv", transition_rows)
    min_index = int(np.argmin(dnl))
    max_index = int(np.argmax(dnl))
    summary = {
        "case": CONFIG,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "transition_count": len(t),
        "code_width_count": len(widths),
        "q_endpoint_v": float(q_ep),
        "max_final_bracket_lsb": float(np.max(bracket)),
        "min_code_width_v": float(np.min(widths)),
        "min_width_code": min_index + 1,
        "min_dnl_ep_lsb": float(dnl[min_index]),
        "max_dnl_ep_lsb": float(dnl[max_index]),
        "max_dnl_code": max_index + 1,
        "max_abs_dnl_ep_lsb": float(np.max(np.abs(dnl))),
        "max_abs_inl_ep_lsb": float(np.max(np.abs(inl))),
        "missing_code_count_center": int(np.sum(widths <= 0.0)),
        "reversal_count_center": int(np.sum(np.diff(t) <= 0.0)),
        "static_gates": {
            "dnl_open_interval": bool(np.all(np.abs(dnl) < 1.0)),
            "inl_abs_lt_1p5": bool(np.max(np.abs(inl)) < 1.5),
            "no_missing_or_reversal": bool(np.all(widths > 0.0)),
        },
        "selected_widths": {
            str(code): width_rows[code - 1] for code in (31, 32, 63, 64, 95, 96, 127, 128, 159, 160, 191, 192, 223, 224)
        },
    }
    summary["absolute_static_status"] = (
        "PASS" if all(summary["static_gates"].values()) else "FAIL"
    )
    (ROOT / "results/current_full255_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
