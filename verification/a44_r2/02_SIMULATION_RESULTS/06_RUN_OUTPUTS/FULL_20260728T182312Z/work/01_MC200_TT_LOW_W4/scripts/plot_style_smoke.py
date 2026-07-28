#!/usr/bin/env python3
"""Generate and audit two formal-style smoke figures from fixed50 reference data."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from dynamic_analysis import spectrum_rows
from sar_campaign_common import ROOT


REF = ROOT / "references" / "fixed50_41_compact" / "data"
OUT = ROOT / "plots" / "style_smoke"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
    }
)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows):
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save(fig, stem: str):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def style_axes(axis):
    axis.set_facecolor("#f7f7f7")
    axis.grid(True, which="major", color="#bdbdbd", linestyle=":", linewidth=0.7)
    for spine in axis.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.0)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    master = read_csv(REF / "fixed50_target_master.csv")
    codes = read_csv(REF / "fixed50_target_codes.csv")
    selected = next(
        row
        for row in master
        if int(row["mismatch_seed"]) == 1 and row["band"] == "NEAR_NYQUIST"
    )
    selected_codes = [
        int(row["code"])
        for row in sorted(
            (
                row
                for row in codes
                if int(row["mismatch_seed"]) == 1
                and row["band"] == "NEAR_NYQUIST"
            ),
            key=lambda row: int(row["frame_index"]),
        )
    ]
    source = spectrum_rows(selected_codes, int(selected["bin"]))
    spectrum_source = [
        {
            "bin": row["bin"],
            "frequency_mhz": row["freq_hz"] / 1e6,
            "amplitude_dbfs_per_bin": row["magnitude_db"],
            "display_amplitude_dbfs_per_bin": row["magnitude_db"],
            "display_clipped": False,
            "is_fundamental": row["is_fundamental"],
            "is_hd2": row["is_hd2"],
            "is_hd3": row["is_hd3"],
            "is_largest_spur": row["is_largest_spur"],
        }
        for row in source
    ]
    write_csv(OUT / "spectrum_style_smoke.csv", spectrum_source)

    x = np.array([row["frequency_mhz"] for row in spectrum_source])
    y = np.array([row["amplitude_dbfs_per_bin"] for row in spectrum_source])
    ymin = min(-100.0, math.floor(float(np.min(y)) / 10.0) * 10.0)
    fig, axis = plt.subplots(figsize=(12.0, 6.2), facecolor="#eeeeee")
    fig.subplots_adjust(right=0.68)
    style_axes(axis)
    axis.vlines(x, ymin, y, color="#0067b1", linewidth=0.9)
    axis.scatter(x, y, color="#0067b1", s=14, marker="o", zorder=3)
    labels = {
        "is_fundamental": "Fundamental",
        "is_hd2": "HD2",
        "is_hd3": "HD3",
        "is_largest_spur": "Largest spur",
    }
    offsets = {
        "is_fundamental": (0, -18),
        "is_hd2": (4, 8),
        "is_hd3": (4, 8),
        "is_largest_spur": (4, -14),
    }
    for flag, label in labels.items():
        for row in spectrum_source:
            if str(row[flag]).lower() == "true":
                annotation = axis.annotate(
                    label,
                    (row["frequency_mhz"], row["amplitude_dbfs_per_bin"]),
                    xytext=offsets[flag],
                    textcoords="offset points",
                    fontsize=8,
                )
                if flag == "is_fundamental":
                    annotation.set_ha("center")
    axis.set_xlim(0.0, 1.0)
    axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    axis.set_ylim(ymin, 0.0)
    axis.set_xlabel("Frequency [MHz]")
    axis.set_ylabel("Amplitude [dBFS/bin]")
    axis.set_title("Formal FFT Style Smoke - Seed 1 Near Nyquist", fontsize=11)
    info = (
        f"NFFT=64  Fs=2.000 MHz  fin={float(selected['fin_hz'])/1e6:.6f} MHz\n"
        "Input=3.0 Vpp,diff (-1.09 dBFS)  Window=rectangular  RBW=31.25 kHz\n"
        "PVT=TT 3.3 V 27 C  Logic=timed behavioral SAR\n"
        f"Mismatch seed=1  Noise seed={selected['noise_seed']}\n"
        "maxstep=50 ps  Solver=ROBUST_GEAR\n"
        f"SNR={float(selected['snr_db']):.2f} dB  "
        f"SNDR={float(selected['sndr_db']):.2f} dB  "
        f"ENOB={float(selected['enob_raw']):.2f} bit\n"
        f"SFDR={float(selected['sfdr_dbc']):.2f} dBc  "
        f"THD={float(selected['thd_db']):.2f} dB"
    )
    fig.text(
        0.70,
        0.88,
        info,
        ha="left",
        va="top",
        fontsize=8.0,
        bbox={"facecolor": "white", "edgecolor": "black", "linewidth": 1.0},
    )
    save(fig, "spectrum_style_smoke")

    low = sorted(
        (
            {"mismatch_seed": int(row["mismatch_seed"]), "sndr_db": float(row["sndr_db"])}
            for row in master
            if row["band"] == "LOW"
        ),
        key=lambda row: (row["sndr_db"], row["mismatch_seed"]),
    )
    for index, row in enumerate(low, start=1):
        row["empirical_cdf"] = index / len(low)
    write_csv(OUT / "low_sndr_ecdf_style_smoke.csv", low)
    fig, axis = plt.subplots(figsize=(8.0, 5.2), facecolor="#eeeeee")
    style_axes(axis)
    axis.step(
        [row["sndr_db"] for row in low],
        [row["empirical_cdf"] for row in low],
        where="post",
        color="#0067b1",
        linewidth=1.5,
        label="LOW fixed50 target subset",
    )
    axis.axvline(46.91, color="#d55e00", linestyle="--", linewidth=1.2, label="Hard SNDR 46.91 dB")
    axis.axvline(47.75, color="#009e73", linestyle="-.", linewidth=1.2, label="Preferred 47.75 dB")
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("SNDR [dB]")
    axis.set_ylabel("Empirical CDF")
    axis.set_title("Formal ECDF Style Smoke - LOW", fontsize=11)
    axis.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="black")
    save(fig, "low_sndr_ecdf_style_smoke")

    checks = {}
    for stem in ("spectrum_style_smoke", "low_sndr_ecdf_style_smoke"):
        png = OUT / f"{stem}.png"
        pdf = OUT / f"{stem}.pdf"
        csv_path = OUT / f"{stem}.csv"
        with Image.open(png) as image:
            dpi = image.info.get("dpi", (0.0, 0.0))
            checks[f"{stem}_png_300dpi"] = min(dpi) >= 299.0
            checks[f"{stem}_png_nonempty"] = image.width > 1000 and image.height > 600
        checks[f"{stem}_pdf_nonempty"] = pdf.stat().st_size > 1000
        checks[f"{stem}_csv_nonempty"] = csv_path.stat().st_size > 100
    checks["spectrum_has_33_one_sided_bins"] = len(spectrum_source) == 33
    checks["spectrum_has_no_display_clipping"] = all(
        row["display_clipped"] is False
        and row["display_amplitude_dbfs_per_bin"]
        == row["amplitude_dbfs_per_bin"]
        for row in spectrum_source
    )
    checks["ecdf_monotonic_and_ends_one"] = all(
        low[index]["empirical_cdf"] <= low[index + 1]["empirical_cdf"]
        for index in range(len(low) - 1)
    ) and low[-1]["empirical_cdf"] == 1.0
    result = {
        "status": "PASS_PLOT_STYLE_SMOKE" if all(checks.values()) else "FAIL_PLOT_STYLE_SMOKE",
        "pass": all(checks.values()),
        "checks": checks,
        "formal_axis_contract": {
            "spectrum_x": "Frequency [MHz]",
            "spectrum_y": "Amplitude [dBFS/bin]",
            "ecdf_x": "SNDR [dB]",
            "ecdf_y": "Empirical CDF",
        },
        "visual_review_required": True,
    }
    (ROOT / "results" / "plot_style_smoke_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
