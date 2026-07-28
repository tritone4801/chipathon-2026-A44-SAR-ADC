#!/usr/bin/env python3
import csv
import json
import re
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
TB_DIR = ROOT / "tb"
TEMPLATE = TB_DIR / "tb_cosim_unit.spice"
JOB_DIR = ROOT / "jobs" / "fault_flags"
RAW_DIR = ROOT / "raw"
LOG_DIR = ROOT / "logs"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"


def crossings(values, rising=True, threshold=1.65):
    if rising:
        mask = (values[:-1] < threshold) & (values[1:] >= threshold)
    else:
        mask = (values[:-1] > threshold) & (values[1:] <= threshold)
    return mask.nonzero()[0]


def analyze(raw_path):
    frame = pd.read_csv(raw_path, sep=r"\s+")
    values = {name: frame[name].to_numpy() for name in frame.columns}
    return {
        "cmpck_rise_count": len(crossings(values["v(cmpck)"])),
        "complete_final_v": float(values["v(complete)"][-1]),
        "invalid_final_v": float(values["v(invalid0)"][-1]),
        "timeout_final_v": float(values["v(timeout0)"][-1]),
    }


def main():
    for directory in (JOB_DIR, RAW_DIR, LOG_DIR, CSV_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    base = TEMPLATE.read_text(encoding="ascii")
    control_template = """.control
set wr_singlescale
set wr_vecnames
tran 0.05n 420n 0 0.05n
wrdata ../raw/__RAW_NAME__ time v(clks) v(cmpck) v(dcmpp) v(dcmpn) v(eoc) v(complete) v(invalid0) v(timeout0) v(dout7) v(dout0)
quit
.endc"""
    cases = [
        {
            "case_id": "both_high_invalid",
            "dcmpp": "BDCMPP dcmpp 0 V=3.3*u(v(cmpck)-1.65)",
            "dcmpn": "BDCMPN dcmpn 0 V=3.3*u(v(cmpck)-1.65)",
            "clock": "VCLKS clks 0 PULSE(3.3 0 100n 0.25n 0.25n 300n 500n)",
            "expected_flag": "invalid",
        },
        {
            "case_id": "both_low_timeout",
            "dcmpp": "VDCMPP dcmpp 0 0",
            "dcmpn": "VDCMPN dcmpn 0 0",
            "clock": "VCLKS clks 0 PULSE(3.3 0 100n 0.25n 0.25n 300n 500n)",
            "expected_flag": "timeout",
        },
        {
            "case_id": "early_sample_abort",
            "dcmpp": "BDCMPP dcmpp 0 V=3.3*u(v(cmpck)-1.65)",
            "dcmpn": "VDCMPN dcmpn 0 0",
            "clock": "VCLKS clks 0 PULSE(3.3 0 100n 0.25n 0.25n 50n 500n)",
            "expected_flag": "timeout",
        },
    ]
    rows = []
    for case in cases:
        case_id = case["case_id"]
        raw_name = f"fault_flag_{case_id}.csv"
        text = re.sub(r"^VCLKS .*?$", case["clock"], base, flags=re.MULTILINE)
        text = re.sub(r"^BDCMPP .*?$", case["dcmpp"], text, flags=re.MULTILINE)
        text = re.sub(r"^VDCMPN .*?$", case["dcmpn"], text, flags=re.MULTILINE)
        text = re.sub(
            r"\.control.*?\.endc",
            control_template.replace("__RAW_NAME__", raw_name),
            text,
            flags=re.DOTALL,
        )
        deck_path = JOB_DIR / f"{case_id}.spice"
        raw_path = RAW_DIR / raw_name
        log_path = LOG_DIR / f"fault_flag_{case_id}.log"
        deck_path.write_text(text, encoding="ascii")
        if raw_path.exists():
            raw_path.unlink()
        completed = subprocess.run(
            ["ngspice", "-b", "-o", str(log_path), str(deck_path)],
            cwd=TB_DIR,
            check=False,
        )
        row = {
            "case_id": case_id,
            "expected_flag": case["expected_flag"],
            "ngspice_returncode": completed.returncode,
        }
        try:
            row.update(analyze(raw_path))
            invalid_high = row["invalid_final_v"] > 1.65
            timeout_high = row["timeout_final_v"] > 1.65
            expected_high = invalid_high if case["expected_flag"] == "invalid" else timeout_high
            other_low = not timeout_high if case["expected_flag"] == "invalid" else not invalid_high
            row["case_status"] = "PASS" if all(
                (
                    completed.returncode == 0,
                    expected_high,
                    other_low,
                    row["complete_final_v"] < 1.65,
                    row["cmpck_rise_count"] >= 1,
                    row["cmpck_rise_count"] < 8,
                )
            ) else "FAIL"
        except Exception as exc:
            row["case_status"] = "FAIL"
            row["analysis_error"] = str(exc)
        rows.append(row)

    fieldnames = sorted({key for row in rows for key in row})
    with (CSV_DIR / "fault_flag_smoke.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["case_status"] == "PASS" for row in rows)
    summary = {
        "status": "PASS" if passed == len(rows) else "FAIL",
        "cases_total": len(rows),
        "cases_passed": passed,
        "maxstep_ns": 0.05,
    }
    (REPORT_DIR / "fault_flag_smoke.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if summary["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
