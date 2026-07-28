#!/usr/bin/env python3
"""Generate the formal plots that remain applicable after the static fail gate."""

import csv
import json

import matplotlib.pyplot as plt
import numpy as np

from make_formal_plots import plot_dnl, plot_inl, save_figure, style_axis
from sar_campaign_common import ROOT, ensure_directories, write_csv


CSV_DIR = ROOT / "csv"
PLOT_DIR = ROOT / "plots"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def plot_failure_bounds(rows):
    source = []
    for row in rows:
        nominal = float(row["width_lsb_nominal"]) - 1.0
        minimum = float(row["min_width_lsb"]) - 1.0
        maximum = float(row["max_width_lsb"]) - 1.0
        source.append(
            {
                "output_code": int(row["code"]),
                "dnl_nominal_lsb": nominal,
                "dnl_min_lsb": minimum,
                "dnl_max_lsb": maximum,
                "dnl_failure_proven": row["dnl_failure_proven"],
                "evidence": "T4_EXACT_STRICT_BOUND",
            }
        )
    write_csv(PLOT_DIR / "dnl_seed002_failure_bounds.csv", source)
    labels = [row["output_code"] for row in source]
    x = np.asarray([0.0, 1.0, 3.0, 4.0])
    y = np.asarray([row["dnl_nominal_lsb"] for row in source])
    low = y - np.asarray([row["dnl_min_lsb"] for row in source])
    high = np.asarray([row["dnl_max_lsb"] for row in source]) - y
    limit = max(1.2, 1.18 * float(np.max(np.abs(np.concatenate((y - low, y + high))))))
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.errorbar(
        x,
        y,
        yerr=np.vstack((low, high)),
        fmt="o",
        color="#0072B2",
        ecolor="#0072B2",
        elinewidth=1.1,
        capsize=4,
        markersize=4,
    )
    axis.axhline(0.0, color="#4d4d4d", linewidth=0.8)
    axis.axhline(1.0, color="#D55E00", linestyle="--", linewidth=0.8)
    axis.axhline(-1.0, color="#D55E00", linestyle="--", linewidth=0.8)
    axis.set_xlim(-0.5, 4.5)
    axis.set_ylim(-limit, limit)
    axis.set_xticks(x, labels)
    axis.set_xlabel("Output Code")
    axis.set_ylabel("DNL Bound [LSB]")
    axis.set_title("Seed 2 Exact Strict DNL Failure Bounds")
    style_axis(axis)
    save_figure(fig, "dnl_seed002_failure_bounds")


def main():
    ensure_directories(PLOT_DIR, REPORT_DIR, RESULT_DIR)
    tt_rows = read_csv(CSV_DIR / "dnl_inl_tt_nominal.csv")
    pvt_rows = read_csv(CSV_DIR / "dnl_inl_pvt_worst.csv")
    failure_rows = read_csv(CSV_DIR / "static_mc_failure_widths.csv")

    plot_dnl(tt_rows, "dnl_tt_nominal", "TT Nominal Exact DNL")
    plot_dnl(pvt_rows, "dnl_pvt_worst", "SS 3.0 V 125 C Exact DNL")
    plot_inl(
        tt_rows,
        "inl_endpoint_lsb",
        "inl_endpoint_tt_nominal",
        "TT Nominal Endpoint INL",
    )
    plot_inl(
        tt_rows,
        "inl_best_fit_lsb",
        "inl_bestfit_tt_nominal",
        "TT Nominal Best-Fit INL",
    )
    plot_inl(
        pvt_rows,
        "inl_endpoint_lsb",
        "inl_endpoint_pvt_worst",
        "SS 3.0 V 125 C Endpoint INL",
    )
    plot_inl(
        pvt_rows,
        "inl_best_fit_lsb",
        "inl_bestfit_pvt_worst",
        "SS 3.0 V 125 C Best-Fit INL",
    )
    plot_failure_bounds(failure_rows)

    generated = (
        "dnl_tt_nominal",
        "dnl_pvt_worst",
        "inl_endpoint_tt_nominal",
        "inl_bestfit_tt_nominal",
        "inl_endpoint_pvt_worst",
        "inl_bestfit_pvt_worst",
        "dnl_seed002_failure_bounds",
    )
    gated = (
        "dnl_worst_exact_seed",
        "inl_endpoint_worst_exact_seed",
        "spectrum_fast64_nominal",
        "spectrum_fast64_worst_sndr",
        "spectrum_fast256_pvt_worst_near_nyquist",
        "mc_sndr_cdf",
        "mc_sfdr_cdf",
    )
    audit_rows = []
    for stem in generated:
        for suffix in ("pdf", "png", "csv"):
            path = PLOT_DIR / f"{stem}.{suffix}"
            audit_rows.append(
                {
                    "plot": stem,
                    "format": suffix,
                    "applicability": "APPLICABLE_FAIL_CLOSURE",
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "status": "PASS" if path.exists() and path.stat().st_size else "FAIL",
                    "reason": "generated from exact electrical data",
                }
            )
    for stem in gated:
        for suffix in ("pdf", "png", "csv"):
            audit_rows.append(
                {
                    "plot": stem,
                    "format": suffix,
                    "applicability": "NOT_RUN_GATE_CLOSED",
                    "exists": False,
                    "bytes": 0,
                    "status": "NOT_RUN_GATE_CLOSED",
                    "reason": "Gate E FAIL_DNL closed downstream population and FFT work",
                }
            )
    write_csv(CSV_DIR / "plot_audit.csv", audit_rows)
    generated_pass = all(
        row["status"] == "PASS"
        for row in audit_rows
        if row["applicability"] == "APPLICABLE_FAIL_CLOSURE"
    )
    payload = {
        "status": "PASS_APPLICABLE_FAIL_CLOSURE" if generated_pass else "FAIL",
        "generated_plot_count": len(generated),
        "generated_artifact_count": len(generated) * 3,
        "not_run_gate_closed_plot_count": len(gated),
        "smoothing": "NONE",
        "fft_plot_claim": "NOT_RUN_GATE_CLOSED",
    }
    (RESULT_DIR / "plot_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Plot Audit",
        "",
        f"- Status: `{payload['status']}`",
        f"- Applicable formal plots generated: `{len(generated)}`",
        f"- PDF/300-dpi-PNG/source-CSV artifacts: `{len(generated) * 3}`",
        "- Smoothing or spline interpolation: `NONE`",
        "- Seed 2 failure plot: exact strict transition-bound intervals; not a reconstructed full-transfer curve",
        "- FFT and MC CDF figures: `NOT_RUN_GATE_CLOSED` after Gate E `FAIL_DNL`",
        "",
        "All applicable static figures have vector PDF, 300 dpi PNG, and retained source CSV. No placeholder FFT figure was fabricated.",
    ]
    (REPORT_DIR / "11_plot_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    print(
        f"STATIC_FAIL_PLOTS status={payload['status']} generated={len(generated)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
