#!/usr/bin/env python3
import csv
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dynamic_analysis import fft_metrics
from run_exact_static import static_metrics
from sar_campaign_common import ROOT, ensure_directories, write_csv


CSV_DIR = ROOT / "csv"
PLOT_DIR = ROOT / "plots"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
SAMPLE_RATE_HZ = 2.0e6


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def save_figure(fig, stem):
    fig.savefig(PLOT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(PLOT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def style_axis(axis):
    axis.grid(True, color="#bdbdbd", linewidth=0.5, alpha=0.45)
    axis.tick_params(labelsize=8)
    axis.xaxis.label.set_size(9)
    axis.yaxis.label.set_size(9)
    axis.title.set_size(10)


def plot_dnl(rows, stem, title):
    source = [
        {
            "output_code": int(row["target_transition"]),
            "dnl_lsb": float(row["dnl_to_next_lsb"]),
        }
        for row in rows
        if row.get("dnl_to_next_lsb") not in (None, "", "None")
    ]
    write_csv(PLOT_DIR / f"{stem}.csv", source)
    x = np.asarray([row["output_code"] for row in source])
    y = np.asarray([row["dnl_lsb"] for row in source])
    maximum = int(np.argmax(y))
    minimum = int(np.argmin(y))
    limit = max(1.10, 1.2 * float(np.max(np.abs(y))))
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.plot(x, y, color="#0072B2", linewidth=1.1)
    for value, color, label in ((0.0, "#4d4d4d", "0 LSB"), (1.0, "#D55E00", "+1 LSB"), (-1.0, "#D55E00", "-1 LSB")):
        axis.axhline(value, color=color, linestyle="--" if value else "-", linewidth=0.8, label=label)
    axis.scatter(
        [x[maximum], x[minimum]],
        [y[maximum], y[minimum]],
        color="#CC79A7",
        s=18,
        zorder=3,
    )
    axis.annotate(f"max {y[maximum]:.4f} @ {x[maximum]}", (x[maximum], y[maximum]), xytext=(5, 8), textcoords="offset points", fontsize=8)
    axis.annotate(f"min {y[minimum]:.4f} @ {x[minimum]}", (x[minimum], y[minimum]), xytext=(5, -13), textcoords="offset points", fontsize=8)
    axis.set_xlim(0, 255)
    axis.set_ylim(-limit, limit)
    axis.set_xticks(np.arange(0, 257, 32))
    axis.set_xlabel("Output Code")
    axis.set_ylabel("DNL [LSB]")
    axis.set_title(title)
    style_axis(axis)
    save_figure(fig, stem)


def plot_inl(rows, field, stem, title):
    source = [
        {
            "output_code": int(row["target_transition"]),
            "inl_lsb": float(row[field]),
        }
        for row in rows
    ]
    write_csv(PLOT_DIR / f"{stem}.csv", source)
    x = np.asarray([row["output_code"] for row in source])
    y = np.asarray([row["inl_lsb"] for row in source])
    maximum = int(np.argmax(y))
    minimum = int(np.argmin(y))
    limit = max(1.65, 1.2 * float(np.max(np.abs(y))))
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.plot(x, y, color="#009E73", linewidth=1.1)
    axis.axhline(0.0, color="#4d4d4d", linewidth=0.8)
    axis.axhline(1.5, color="#D55E00", linestyle="--", linewidth=0.8)
    axis.axhline(-1.5, color="#D55E00", linestyle="--", linewidth=0.8)
    axis.scatter([x[maximum], x[minimum]], [y[maximum], y[minimum]], color="#CC79A7", s=18, zorder=3)
    axis.annotate(f"max {y[maximum]:.4f} @ {x[maximum]}", (x[maximum], y[maximum]), xytext=(5, 8), textcoords="offset points", fontsize=8)
    axis.annotate(f"min {y[minimum]:.4f} @ {x[minimum]}", (x[minimum], y[minimum]), xytext=(5, -13), textcoords="offset points", fontsize=8)
    axis.set_xlim(0, 255)
    axis.set_ylim(-limit, limit)
    axis.set_xticks(np.arange(0, 257, 32))
    axis.set_xlabel("Output Code")
    axis.set_ylabel("INL [LSB]")
    axis.set_title(title)
    style_axis(axis)
    save_figure(fig, stem)


def exact_metric_rows(seed):
    transitions = read_csv(CSV_DIR / f"transitions_mc_seed{seed:03d}_up.csv")
    typed = []
    for row in transitions:
        converted = dict(row)
        converted["target_transition"] = int(row["target_transition"])
        converted["transition_v"] = float(row["transition_v"])
        converted["status"] = row["status"]
        typed.append(converted)
    metrics = static_metrics(typed)
    if metrics.get("transition_count") != 255 or not metrics.get("rows"):
        raise RuntimeError(
            f"exact metric plot source for seed {seed} is structurally incomplete: "
            f"{metrics['status']}"
        )
    return metrics["rows"]


def spectrum_source(codes, bin_index):
    values = np.asarray(codes, dtype=float)
    count = len(values)
    spectrum = np.fft.rfft(values) / count
    powers = np.abs(spectrum) ** 2
    if count > 1:
        powers[1:-1] *= 2.0
    full_scale_sine_power = (255.0 / 2.0) ** 2 / 2.0
    dbfs = 10.0 * np.log10(np.maximum(powers, 1e-30) / full_scale_sine_power)
    rows = []
    for index, value in enumerate(dbfs):
        raw_hd2 = (2 * bin_index) % count
        raw_hd3 = (3 * bin_index) % count
        hd2 = raw_hd2 if raw_hd2 <= count // 2 else count - raw_hd2
        hd3 = raw_hd3 if raw_hd3 <= count // 2 else count - raw_hd3
        marker = ""
        if index == bin_index:
            marker = "FUNDAMENTAL"
        elif index == hd2:
            marker = "HD2"
        elif index == hd3:
            marker = "HD3"
        rows.append(
            {
                "bin": index,
                "frequency_hz": index * SAMPLE_RATE_HZ / count,
                "frequency_mhz": index * SAMPLE_RATE_HZ / count / 1e6,
                "amplitude_dbfs_per_bin": float(value),
                "marker": marker,
            }
        )
    metrics = fft_metrics(codes, bin_index, SAMPLE_RATE_HZ)
    for row in rows:
        if row["bin"] == metrics["largest_spur_bin"] and not row["marker"]:
            row["marker"] = "LARGEST_SPUR"
    return rows, metrics


def plot_spectrum(codes, bin_index, metadata, stem, title):
    source, metrics = spectrum_source(codes, bin_index)
    write_csv(PLOT_DIR / f"{stem}.csv", source)
    x = np.asarray([row["frequency_mhz"] for row in source])
    y = np.asarray([row["amplitude_dbfs_per_bin"] for row in source])
    fig, axis = plt.subplots(figsize=(7.6, 4.6))
    markerline, stemlines, baseline = axis.stem(x, y, linefmt="-", markerfmt="o", basefmt=" ")
    plt.setp(stemlines, linewidth=0.9, color="#0072B2")
    plt.setp(markerline, markersize=2.4, markerfacecolor="#0072B2", markeredgewidth=0.0)
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(-100.0, 1.0)
    axis.set_xlabel("Frequency [MHz]")
    axis.set_ylabel("Amplitude [dBFS/bin]")
    axis.set_title(title)
    annotations = [row for row in source if row["marker"]]
    for row in annotations:
        axis.annotate(
            row["marker"],
            (row["frequency_mhz"], max(-96.0, row["amplitude_dbfs_per_bin"])),
            xytext=(3, 5),
            textcoords="offset points",
            fontsize=7,
            rotation=45,
        )
    info = (
        f"NFFT={len(codes)}  Fs=2.0 MHz  fin={bin_index*SAMPLE_RATE_HZ/len(codes)/1e3:.3f} kHz\n"
        f"Input=3.0 Vpp,diff (-1.09 dBFS)  Window=rectangular  RBW={SAMPLE_RATE_HZ/len(codes)/1e3:.3f} kHz\n"
        f"PVT={metadata['pvt']}  Logic=SAR_LOGIC_BEH_TT_3P3_27C\n"
        f"Mismatch={metadata.get('mismatch_seed')}  Noise={metadata.get('noise_seed')}\n"
        f"SNR={metrics['snr_db']:.3f}  SNDR={metrics['sndr_db']:.3f}  ENOB={metrics['enob_bit']:.3f}\n"
        f"SFDR={metrics['sfdr_dbc']:.3f}  THD={metrics['thd_db']:.3f} dB"
    )
    axis.text(
        0.985,
        0.97,
        info,
        transform=axis.transAxes,
        ha="right",
        va="top",
        fontsize=7,
        bbox={"facecolor": "white", "edgecolor": "#777777", "linewidth": 0.6, "alpha": 0.92},
    )
    style_axis(axis)
    save_figure(fig, stem)


def plot_cdf(rows, field, stem, title, xlabel):
    values = np.sort(np.asarray([float(row[field]) for row in rows]))
    probabilities = np.arange(1, len(values) + 1, dtype=float) / len(values)
    source = [
        {field: float(value), "empirical_cdf": float(probability)}
        for value, probability in zip(values, probabilities)
    ]
    write_csv(PLOT_DIR / f"{stem}.csv", source)
    fig, axis = plt.subplots(figsize=(6.6, 4.2))
    axis.step(values, probabilities, where="post", color="#0072B2", linewidth=1.2)
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Empirical CDF")
    axis.set_title(title)
    style_axis(axis)
    save_figure(fig, stem)


def main():
    ensure_directories(PLOT_DIR, REPORT_DIR, RESULT_DIR)
    tt_rows = read_csv(CSV_DIR / "dnl_inl_tt_nominal.csv")
    validation = read_csv(CSV_DIR / "static_mc_exact_validation.csv")
    worst_dnl_row = max(validation, key=lambda row: float(row["exact_max_abs_dnl_lsb"]))
    worst_seed = int(worst_dnl_row["mismatch_seed"])
    worst_rows = exact_metric_rows(worst_seed)

    plot_dnl(tt_rows, "dnl_tt_nominal", "TT Nominal Exact DNL")
    plot_dnl(worst_rows, "dnl_worst_exact_seed", f"Exact DNL, Worst Exact Seed {worst_seed}")
    plot_inl(tt_rows, "inl_endpoint_lsb", "inl_endpoint_tt_nominal", "TT Nominal Endpoint INL")
    plot_inl(worst_rows, "inl_endpoint_lsb", "inl_endpoint_worst_exact_seed", f"Endpoint INL, Seed {worst_seed}")
    plot_inl(tt_rows, "inl_best_fit_lsb", "inl_bestfit_tt_nominal", "TT Nominal Best-Fit INL")

    nominal_summary = read_csv(CSV_DIR / "dynamic_fast64_nominal.csv")[0]
    nominal_codes = [int(row["code"]) for row in read_csv(CSV_DIR / "dynamic_fast64_nominal_codes.csv")]
    plot_spectrum(
        nominal_codes,
        7,
        nominal_summary,
        "spectrum_fast64_nominal",
        "FAST64 Nominal Spectrum",
    )
    dynamic = read_csv(CSV_DIR / "dynamic_mc200_fast64.csv")
    worst_dynamic = min(dynamic, key=lambda row: float(row["sndr_db"]))
    worst_dynamic_seed = int(worst_dynamic["mismatch_seed"])
    worst_codes = [
        int(row["code"])
        for row in read_csv(CSV_DIR / "dynamic_mc200_fast64_codes.csv")
        if int(row["mismatch_seed"]) == worst_dynamic_seed
    ]
    plot_spectrum(
        worst_codes,
        7,
        worst_dynamic,
        "spectrum_fast64_worst_sndr",
        f"FAST64 Worst-SNDR Spectrum, Seed {worst_dynamic_seed}",
    )
    fast256 = read_csv(CSV_DIR / "dynamic_fast256_closure.csv")
    pvt_near = next(
        row
        for row in fast256
        if row["role"] == "PVT_DYNAMIC_WORST" and row["band"] == "NEAR_NYQUIST"
    )
    pvt_near_codes = [
        int(row["code"])
        for row in read_csv(CSV_DIR / "dynamic_fast256_closure_codes.csv")
        if row["role"] == "PVT_DYNAMIC_WORST" and row["band"] == "NEAR_NYQUIST"
    ]
    plot_spectrum(
        pvt_near_codes,
        117,
        pvt_near,
        "spectrum_fast256_pvt_worst_near_nyquist",
        "FAST256 PVT-Worst Near-Nyquist Spectrum",
    )
    plot_cdf(dynamic, "sndr_db", "mc_sndr_cdf", "MC200 FAST64 SNDR", "SNDR [dB]")
    plot_cdf(dynamic, "sfdr_dbc", "mc_sfdr_cdf", "MC200 FAST64 SFDR", "SFDR [dBc]")

    required = (
        "dnl_tt_nominal",
        "dnl_worst_exact_seed",
        "inl_endpoint_tt_nominal",
        "inl_endpoint_worst_exact_seed",
        "inl_bestfit_tt_nominal",
        "spectrum_fast64_nominal",
        "spectrum_fast64_worst_sndr",
        "spectrum_fast256_pvt_worst_near_nyquist",
        "mc_sndr_cdf",
        "mc_sfdr_cdf",
    )
    audit_rows = []
    for stem in required:
        for suffix in ("pdf", "png", "csv"):
            path = PLOT_DIR / f"{stem}.{suffix}"
            audit_rows.append(
                {
                    "plot": stem,
                    "format": suffix,
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "status": "PASS" if path.exists() and path.stat().st_size > 0 else "FAIL",
                }
            )
    write_csv(CSV_DIR / "plot_audit.csv", audit_rows)
    status = "PASS" if all(row["status"] == "PASS" for row in audit_rows) else "FAIL"
    (RESULT_DIR / "plot_audit.json").write_text(
        json.dumps(
            {
                "status": status,
                "required_plot_count": len(required),
                "artifact_count": len(audit_rows),
                "worst_exact_seed": worst_seed,
                "worst_dynamic_seed": worst_dynamic_seed,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="ascii",
    )
    lines = [
        "# Plot Audit",
        "",
        f"- Status: `{status}`",
        f"- Required formal plots: `{len(required)}`",
        f"- PDF/PNG/source-CSV artifacts: `{len(audit_rows)}`",
        "- Smoothing or spline interpolation: `NONE`",
        "- FFT metric extraction uses native bins; display zero-padding: `NONE`",
        "",
        "Every required figure has a vector PDF, a 300 dpi PNG, and an independently retained source CSV.",
    ]
    (REPORT_DIR / "11_plot_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
