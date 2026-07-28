#!/usr/bin/env python3
import csv
import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
TB_DIR = ROOT / "tb"
TEMPLATE = TB_DIR / "tb_actual_core_smoke_tt.spice"
JOB_DIR = ROOT / "jobs" / "behavioral_contract"
RAW_DIR = ROOT / "raw"
LOG_DIR = ROOT / "logs"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
FULL_SCALE_V = 3.4
LSB_V = FULL_SCALE_V / 256.0


def crossing_indices(values, rising=True, threshold=1.65):
    if rising:
        mask = (values[:-1] < threshold) & (values[1:] >= threshold)
    else:
        mask = (values[:-1] > threshold) & (values[1:] <= threshold)
    return mask.nonzero()[0]


def analyze(raw_path):
    frame = pd.read_csv(raw_path, sep=r"\s+")
    time_s = frame.iloc[:, 0].to_numpy()
    values = {name: frame[name].to_numpy() for name in frame.columns}
    cmp_rises = crossing_indices(values["v(cmpck)"])
    cmp_falls = crossing_indices(values["v(cmpck)"], rising=False)
    complete_rises = crossing_indices(values["v(complete)"])
    if len(cmp_rises) == 0 or len(complete_rises) == 0:
        raise ValueError("conversion did not produce CMPCK and completion events")

    first_cmp_s = time_s[cmp_rises[0]]
    complete_s = time_s[complete_rises[0]]
    adjustments = []
    dctrl_names = [
        name for name in frame.columns if "dctrlp" in name or "dctrln" in name
    ]
    for name in dctrl_names:
        for rising in (True, False):
            for index in crossing_indices(values[name], rising=rising):
                if first_cmp_s <= time_s[index] <= complete_s:
                    adjustments.append((time_s[index], name, "rise" if rising else "fall"))

    dout_names = [f"v(dout{bit}_rx)" for bit in range(7, -1, -1)]
    dout_changes = []
    for name in dout_names:
        for rising in (True, False):
            for index in crossing_indices(values[name], rising=rising):
                dout_changes.append(time_s[index])
    final_bits = [int(values[name][-1] > 1.65) for name in dout_names]
    final_code = sum(bit << (7 - index) for index, bit in enumerate(final_bits))
    update_spread_ns = 0.0
    if dout_changes:
        update_spread_ns = (max(dout_changes) - min(dout_changes)) * 1e9

    return {
        "cmpck_rise_count": len(cmp_rises),
        "cmpck_fall_count": len(cmp_falls),
        "adjustment_count": len(adjustments),
        "complete_time_ns": complete_s * 1e9,
        "final_code": final_code,
        "final_bits": "".join(str(bit) for bit in final_bits),
        "dout_update_spread_ns": update_spread_ns,
        "dout_held_until_complete": not any(
            change < complete_s - 1e-12 for change in dout_changes
        ),
        "extra_cmpck_after_complete": sum(
            time_s[index] > complete_s for index in cmp_rises
        ),
        "invalid_final_v": float(values["v(invalid0)"][-1]),
        "timeout_final_v": float(values["v(timeout0)"][-1]),
    }


def main():
    for directory in (JOB_DIR, RAW_DIR, LOG_DIR, CSV_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    cases = [
        ("negative_full_scale", -FULL_SCALE_V / 2.0),
        ("t31_32_minus_0p25lsb", -FULL_SCALE_V / 2.0 + 32 * LSB_V - 0.25 * LSB_V),
        ("t31_32_plus_0p25lsb", -FULL_SCALE_V / 2.0 + 32 * LSB_V + 0.25 * LSB_V),
        ("t63_64_minus_0p25lsb", -FULL_SCALE_V / 2.0 + 64 * LSB_V - 0.25 * LSB_V),
        ("t63_64_plus_0p25lsb", -FULL_SCALE_V / 2.0 + 64 * LSB_V + 0.25 * LSB_V),
        ("t127_128_minus_0p25lsb", -0.25 * LSB_V),
        ("zero_differential", 0.0),
        ("t127_128_plus_0p25lsb", 0.25 * LSB_V),
        ("t191_192_minus_0p25lsb", -FULL_SCALE_V / 2.0 + 192 * LSB_V - 0.25 * LSB_V),
        ("t191_192_plus_0p25lsb", -FULL_SCALE_V / 2.0 + 192 * LSB_V + 0.25 * LSB_V),
        ("positive_full_scale", FULL_SCALE_V / 2.0),
    ]
    template = TEMPLATE.read_text(encoding="ascii")
    rows = []
    for case_id, vid_v in cases:
        vinp_v = 1.65 + vid_v / 2.0
        vinn_v = 1.65 - vid_v / 2.0
        raw_name = f"behavioral_contract_{case_id}.csv"
        deck_text = template.replace(
            ".param VINP_DC=1.65 VINN_DC=1.65",
            f".param VINP_DC={vinp_v:.12g} VINN_DC={vinn_v:.12g}",
        ).replace("tb_actual_core_smoke_tt.csv", raw_name)
        deck_path = JOB_DIR / f"{case_id}.spice"
        log_path = LOG_DIR / f"behavioral_contract_{case_id}.log"
        raw_path = RAW_DIR / raw_name
        deck_path.write_text(deck_text, encoding="ascii")
        if raw_path.exists():
            raw_path.unlink()
        completed = subprocess.run(
            ["ngspice", "-b", "-o", str(log_path), str(deck_path)],
            cwd=TB_DIR,
            check=False,
        )
        row = {
            "case_id": case_id,
            "vid_v": vid_v,
            "vinp_v": vinp_v,
            "vinn_v": vinn_v,
            "ngspice_returncode": completed.returncode,
        }
        try:
            row.update(analyze(raw_path))
            row["case_status"] = "PASS" if all(
                (
                    completed.returncode == 0,
                    row["cmpck_rise_count"] == 8,
                    row["cmpck_fall_count"] == 8,
                    row["adjustment_count"] == 7,
                    row["dout_held_until_complete"],
                    row["dout_update_spread_ns"] <= 0.05,
                    row["extra_cmpck_after_complete"] == 0,
                    row["invalid_final_v"] < 1.65,
                    row["timeout_final_v"] < 1.65,
                )
            ) else "FAIL"
        except Exception as exc:
            row["case_status"] = "FAIL"
            row["analysis_error"] = str(exc)
        rows.append(row)

    valid_rows = [row for row in rows if row["case_status"] == "PASS"]
    monotonic = len(valid_rows) == len(rows) and all(
        left["final_code"] <= right["final_code"]
        for left, right in zip(valid_rows, valid_rows[1:])
    )
    overall = "PASS" if len(valid_rows) == len(rows) and monotonic else "FAIL"

    fieldnames = sorted({key for row in rows for key in row})
    with (CSV_DIR / "behavioral_contract_smoke.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": overall,
        "cases_total": len(rows),
        "cases_passed": len(valid_rows),
        "code_monotonic_with_vid": monotonic,
        "lsb_v": LSB_V,
        "full_scale_vpp_diff": FULL_SCALE_V,
        "maxstep_ns": 0.05,
    }
    (REPORT_DIR / "behavioral_contract_smoke.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if overall == "PASS" else 2)


if __name__ == "__main__":
    main()
