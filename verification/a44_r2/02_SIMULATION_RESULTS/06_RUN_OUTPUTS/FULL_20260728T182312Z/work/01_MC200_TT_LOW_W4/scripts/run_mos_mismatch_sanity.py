#!/usr/bin/env python3
import csv
import json
import os
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
JOB_DIR = ROOT / "jobs" / "mos_mismatch"
RAW_DIR = ROOT / "raw" / "mos_mismatch"
LOG_DIR = ROOT / "logs" / "mos_mismatch"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
PAIR_COUNT = 64
SEED = 20260718
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice")
NGSPICE = Path("/foss/tools/bin/ngspice")


def make_deck(device, mismatch_scale, area_factor, output_path):
    model = "nfet_03v3" if device == "nmos" else "pfet_03v3"
    width = 2e-6 * area_factor
    lines = [
        f"* Fresh MOS mismatch sanity: {device}, scale={mismatch_scale}, area={area_factor}",
        f".option seed={SEED}",
        f".include {PDK / 'design.ngspice'}",
        ".options savecurrents",
        f".param sw_stat_global=0 sw_stat_mismatch={mismatch_scale} mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".lib {PDK / 'sm141064.ngspice'} statistical",
        "VDD vdd 0 3.3",
        "VG gate 0 1.65",
    ]
    for index in range(PAIR_COUNT):
        lines.extend(
            (
                f"VDA{index} da{index} 0 1.65",
                f"VDB{index} db{index} 0 1.65",
            )
        )
        if device == "nmos":
            lines.extend(
                (
                    f"XA{index} da{index} gate 0 0 {model} w={width:.12g} l=2.8e-7 nf=1",
                    f"XB{index} db{index} gate 0 0 {model} w={width:.12g} l=2.8e-7 nf=1",
                )
            )
        else:
            lines.extend(
                (
                    f"XA{index} da{index} gate vdd vdd {model} w={width:.12g} l=2.8e-7 nf=1",
                    f"XB{index} db{index} gate vdd vdd {model} w={width:.12g} l=2.8e-7 nf=1",
                )
            )
    vectors = " ".join(
        item for index in range(PAIR_COUNT) for item in (f"i(vda{index})", f"i(vdb{index})")
    )
    lines.extend(
        (
            ".control",
            "set noaskquit",
            "op",
            f"wrdata {output_path} {vectors}",
            "quit",
            ".endc",
            ".end",
        )
    )
    return "\n".join(lines) + "\n"


def read_currents(path):
    values = np.fromstring(path.read_text(encoding="ascii"), sep=" ")
    if values.size != PAIR_COUNT * 4:
        raise ValueError(f"unexpected wrdata value count {values.size}")
    currents = values[1::2]
    return currents


def metrics(currents):
    current_a = np.abs(currents[0::2])
    current_b = np.abs(currents[1::2])
    relative = 2.0 * (current_a - current_b) / (current_a + current_b)
    return {
        "mean_relative_delta": float(np.mean(relative)),
        "sigma_relative_delta": float(np.std(relative, ddof=1)),
        "max_abs_relative_delta": float(np.max(np.abs(relative))),
        "mean_abs_current_a": float(np.mean(current_a)),
    }


def run_case(device, name, mismatch_scale, area_factor, replay_index=0):
    stem = f"{device}_{name}_replay{replay_index}"
    deck_path = JOB_DIR / f"{stem}.spice"
    raw_path = RAW_DIR / f"{stem}.txt"
    log_path = LOG_DIR / f"{stem}.log"
    deck_path.write_text(
        make_deck(device, mismatch_scale, area_factor, raw_path), encoding="ascii"
    )
    if raw_path.exists():
        raw_path.unlink()
    environment = os.environ.copy()
    environment["HOME"] = str(JOB_DIR)
    completed = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log_path), str(deck_path)],
        cwd=JOB_DIR,
        env=environment,
        check=False,
    )
    if completed.returncode != 0 or not raw_path.exists():
        raise RuntimeError(f"ngspice failed for {stem}: rc={completed.returncode}")
    return read_currents(raw_path)


def main():
    for directory in (JOB_DIR, RAW_DIR, LOG_DIR, CSV_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    (JOB_DIR / ".spiceinit").write_text(
        (
            "echo A44_JOB_LOCAL_SPICEINIT_LOADED\n"
            "set noaskquit\n"
        ),
        encoding="ascii",
    )

    rows = []
    arrays = {}
    case_defs = (
        ("mismatch_off_area1", 0, 1),
        ("mismatch_on_area1", 1, 1),
        ("mismatch_on_area4", 1, 4),
        ("mismatch_x2_area1", 2, 1),
    )
    for device in ("nmos", "pmos"):
        for name, scale, area in case_defs:
            current = run_case(device, name, scale, area)
            arrays[(device, name)] = current
            row = {
                "device": device,
                "case": name,
                "mismatch_scale": scale,
                "area_factor": area,
                "pair_count": PAIR_COUNT,
                "seed": SEED,
            }
            row.update(metrics(current))
            rows.append(row)

    reproducibility = {}
    checks = []
    for device in ("nmos", "pmos"):
        replay = run_case(device, "mismatch_on_area1", 1, 1, replay_index=1)
        baseline = arrays[(device, "mismatch_on_area1")]
        max_diff = float(np.max(np.abs(replay - baseline)))
        reproducibility[device] = {
            "exact_equal": bool(np.array_equal(replay, baseline)),
            "max_abs_current_diff_a": max_diff,
        }
        lookup = {
            row["case"]: row for row in rows if row["device"] == device
        }
        sigma_off = lookup["mismatch_off_area1"]["sigma_relative_delta"]
        sigma_1x = lookup["mismatch_on_area1"]["sigma_relative_delta"]
        sigma_area4 = lookup["mismatch_on_area4"]["sigma_relative_delta"]
        sigma_2x = lookup["mismatch_x2_area1"]["sigma_relative_delta"]
        device_checks = {
            "mismatch_off_collapses": sigma_off < 1e-12,
            "mismatch_on_nonzero": sigma_1x > 1e-5,
            "area_scaling_ratio_ok": 0.30 <= sigma_area4 / sigma_1x <= 0.75,
            "x2_scaling_ratio_ok": 1.5 <= sigma_2x / sigma_1x <= 2.5,
            "mean_physically_plausible": all(
                abs(lookup[name]["mean_relative_delta"]) < 0.02 for name, _, _ in case_defs
            ),
            "seed_reproducible": reproducibility[device]["exact_equal"],
        }
        checks.append({"device": device, **device_checks})

    with (CSV_DIR / "mos_mismatch_sanity.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (CSV_DIR / "mos_mismatch_checks.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows(checks)
    passed = all(all(value for key, value in row.items() if key != "device") for row in checks)
    summary = {
        "status": "PASS" if passed else "FAIL",
        "pair_count_per_case": PAIR_COUNT,
        "seed": SEED,
        "seed_applied_before_statistical_parameter_expansion": True,
        "ngspice_executable": str(NGSPICE),
        "seed_request_methods": [
            f"netlist option: .option seed={SEED}",
        ],
        "reproducibility": reproducibility,
        "checks": checks,
    }
    (REPORT_DIR / "mos_mismatch_sanity.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
