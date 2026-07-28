#!/usr/bin/env python3
"""Create the eight required FAST64 V2 figures and source tables."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dynamic_analysis import spectrum_rows
from fast64_v2_common import (
    BANDS,
    CSV_DIR,
    PLOT_DIR,
    ROOT,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


PDF_DIR = ROOT / "output/pdf/figures"
SOURCE_DIR = PLOT_DIR / "source"


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "axes.grid": True,
            "grid.color": "#d9dde3",
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def save_figure(
    fig: plt.Figure, stem: str, source_rows: list[dict[str, object]]
) -> dict[str, object]:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    png = PLOT_DIR / f"{stem}.png"
    pdf = PDF_DIR / f"{stem}.pdf"
    source = SOURCE_DIR / f"{stem}.csv"
    write_csv_atomic(source, source_rows)
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {
        "figure_id": stem,
        "png": png.relative_to(ROOT).as_posix(),
        "pdf": pdf.relative_to(ROOT).as_posix(),
        "source_csv": source.relative_to(ROOT).as_posix(),
        "png_sha256": sha256_file(png),
        "pdf_sha256": sha256_file(pdf),
        "source_sha256": sha256_file(source),
    }


def first_conversion_gate() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["band"]))
    seeds = sorted({int(row["mismatch_seed"]) for row in rows})
    bands = ("LOW", "NEAR_NYQUIST")
    matrix = np.full((len(seeds), len(bands)), np.nan)
    source: list[dict[str, object]] = []
    for row in rows:
        i = seeds.index(int(row["mismatch_seed"]))
        j = bands.index(row["band"])
        value = int(truth(row["first_conversion_pass"]))
        matrix[i, j] = value
        source.append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "band": row["band"],
                "first_conversion_pass": value,
                "first_conversion_status": row["first_conversion_status"],
            }
        )
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    ax.imshow(matrix, vmin=0, vmax=1, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(bands)), ["LOW", "NEAR"])
    ax.set_yticks(range(len(seeds)), [str(seed) for seed in seeds])
    ax.set_xlabel("Input band")
    ax.set_ylabel("Mismatch seed")
    ax.set_title("First-conversion gate - FAST64 V2")
    for i in range(len(seeds)):
        for j in range(len(bands)):
            text = "PASS" if matrix[i, j] == 1 else "FAIL"
            ax.text(j, i, text, ha="center", va="center", fontsize=8)
    return fig, source


def warmup_difference() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "warmup_canonical_comparison.csv")
    source: list[dict[str, object]] = [dict(row) for row in rows]
    labels = [
        f"{row['mismatch_seed'] or 'NOM'}-{row['band'].replace('NEAR_NYQUIST','NEAR')}"
        for row in rows
    ]
    differences = [64 - int(row["canonical_code_match_count"]) for row in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    colors = ["#2a9d8f" if value == 0 else "#d1495b" for value in differences]
    ax.bar(range(len(rows)), differences, color=colors)
    ax.scatter(
        range(len(rows)),
        differences,
        marker="s",
        s=70,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )
    for index, value in enumerate(differences):
        ax.annotate(
            "0/64 PASS" if value == 0 else f"{value}/64 FAIL",
            (index, value),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            color="#176b5b" if value == 0 else "#a12f42",
        )
    ax.set_xticks(range(len(rows)), labels, rotation=35, ha="right")
    ax.set_ylabel("Differing canonical codes / 64")
    ax.set_title("W4 vs W8 canonical-code qualification")
    ax.set_ylim(-0.12, max(1, max(differences, default=0) + 1))
    return fig, source


def w0_w4_dumbbell() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "method_transition_comparison.csv")
    rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["band"]))
    source: list[dict[str, object]] = [dict(row) for row in rows]
    labels = [
        f"S{int(row['mismatch_seed']):03d}-{row['band'].replace('NEAR_NYQUIST','NEAR')}"
        for row in rows
    ]
    w0 = np.asarray([float(row["same_run_w0_replay_sndr_db"]) for row in rows])
    w4 = np.asarray([float(row["new_steady_state_w4_sndr_db"]) for row in rows])
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(8.0, 7.0))
    for index in range(len(rows)):
        ax.plot([w0[index], w4[index]], [y[index], y[index]], color="#aeb6bf")
    ax.scatter(w0, y, label="W0 frames 0-63", color="#e76f51", s=28, zorder=3)
    ax.scatter(w4, y, label="W4 frames 4-67", color="#277da1", s=28, zorder=3)
    ax.axvline(46.91, color="#444444", linestyle="--", linewidth=1, label="46.91 dB")
    ax.set_yticks(y, labels)
    ax.set_xlabel("SNDR (dB)")
    ax.set_title("Same-run W0 replay vs formal steady-state W4")
    ax.legend(loc="best")
    return fig, source


def first_path_pairs() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "first_conversion_path.csv")
    selected = [
        row
        for row in rows
        if row.get("role") == "MAIN_MC10"
        and row.get("noise_mode") == "OFF"
        and int(row["frame_index"]) in (0, 64)
    ]
    source: list[dict[str, object]] = [dict(row) for row in selected]
    by_key: dict[tuple[int, str], dict[int, dict[str, str]]] = {}
    for row in selected:
        key = (int(row["mismatch_seed"]), row["band"])
        by_key.setdefault(key, {})[int(row["frame_index"])] = row
    labels: list[str] = []
    deltas: list[int] = []
    path_fails: list[int] = []
    for key, pair in sorted(by_key.items()):
        if 0 not in pair or 64 not in pair:
            continue
        labels.append(f"S{key[0]:03d}-{key[1].replace('NEAR_NYQUIST','NEAR')}")
        deltas.append(
            int(pair[0]["analog_dout_code"]) ^ int(pair[64]["analog_dout_code"])
        )
        path_fails.append(
            int(not truth(pair[0]["path_pass"]) or not truth(pair[64]["path_pass"]))
        )
    fig, ax = plt.subplots(figsize=(8.0, 5.8))
    y = np.arange(len(labels))
    colors = ["#d1495b" if fail or delta else "#2a9d8f" for fail, delta in zip(path_fails, deltas)]
    ax.barh(y, deltas, color=colors)
    ax.scatter(
        deltas,
        y,
        marker="s",
        s=36,
        color=colors,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    ax.set_yticks(y, labels)
    ax.set_xlabel("frame0 XOR frame64 code")
    ax.set_title("Noise-OFF first-conversion same-phase path check")
    if labels and max(deltas, default=0) == 0 and not any(path_fails):
        ax.set_xlim(-1, 1)
        ax.text(
            0.5,
            0.02,
            "All frame0/frame64 code and path checks matched",
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            color="#1b7f68",
        )
    return fig, source


def bridge_plot() -> tuple[plt.Figure, list[dict[str, object]]]:
    bridge = read_csv(CSV_DIR / "percentile_bridge_comparison.csv")
    transition = read_csv(CSV_DIR / "method_transition_comparison.csv")
    seed109 = next(
        (
            row
            for row in transition
            if int(row["mismatch_seed"]) == 109 and row["band"] == "LOW"
        ),
        None,
    )
    source: list[dict[str, object]] = [dict(row) for row in bridge]
    if seed109:
        source.append(
            {
                "bridge_role": "CURRENT_P1_MAIN",
                "mismatch_seed": 109,
                "band": "LOW",
                "historical_current_mc200_w0_sndr_db": seed109[
                    "historical_current_mc200_sndr_db"
                ],
                "same_run_w0_replay_sndr_db": seed109[
                    "same_run_w0_replay_sndr_db"
                ],
                "new_ss_w4_sndr_db": seed109["new_steady_state_w4_sndr_db"],
            }
        )
    source.sort(key=lambda row: int(row["mismatch_seed"]))
    x = np.arange(len(source))
    historical = []
    same_w0 = []
    new_w4 = []
    for row in source:
        historical_value = (
            row.get("historical_current_mc200_w0_sndr_db")
            or row.get("historical_v7_mc200_w0_sndr_db")
            or np.nan
        )
        historical.append(float(historical_value))
        same_w0.append(float(row.get("same_run_w0_replay_sndr_db") or np.nan))
        new_w4.append(float(row.get("new_ss_w4_sndr_db") or np.nan))
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    width = 0.24
    ax.bar(x - width, historical, width, label="Historical MC200 W0", color="#8d99ae")
    ax.bar(x, same_w0, width, label="Same-run W0", color="#e76f51")
    ax.bar(x + width, new_w4, width, label="New SS W4", color="#277da1")
    ax.set_xticks(x, [f"S{int(row['mismatch_seed']):03d}" for row in source])
    ax.set_ylabel("SNDR (dB)")
    ax.set_title("P1/P5/P10 method-transition bridge")
    ax.legend(fontsize=8)
    return fig, source


def steady_metrics() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["band"]))
    source: list[dict[str, object]] = [dict(row) for row in rows]
    labels = [
        f"S{int(row['mismatch_seed']):03d}-{row['band'].replace('NEAR_NYQUIST','N')}"
        for row in rows
    ]
    x = np.arange(len(rows))
    sndr = [float(row["steady_state_sndr_db"]) for row in rows]
    enob = [float(row["steady_state_enob_raw"]) for row in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.0, 7.0), sharex=True)
    colors = ["#4c78a8" if row["band"] == "LOW" else "#f58518" for row in rows]
    ax1.scatter(x, sndr, c=colors)
    ax1.axhline(46.91, color="#333333", linestyle="--", linewidth=1)
    ax1.set_ylabel("Steady-state SNDR (dB)")
    ax1.set_title("FAST64 SS W4 dynamic performance")
    ax2.scatter(x, enob, c=colors)
    ax2.axhline(7.50, color="#333333", linestyle="--", linewidth=1)
    ax2.set_ylabel("Raw ENOB (bit)")
    ax2.set_xticks(x, labels, rotation=65, ha="right")
    return fig, source


def status_matrix() -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    rows.sort(key=lambda row: (int(row["mismatch_seed"]), row["band"]))
    source: list[dict[str, object]] = []
    counts = np.zeros((2, 2), dtype=int)
    failing_labels: list[str] = []
    for row in rows:
        first = int(truth(row["first_conversion_pass"]))
        steady = int(truth(row["steady_state_hard_dynamic_pass"]))
        counts[steady, first] += 1
        label = f"S{int(row['mismatch_seed']):03d}-{row['band'].replace('NEAR_NYQUIST','N')}"
        if not (first and steady):
            failing_labels.append(label)
        source.append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "band": row["band"],
                "first_conversion_pass": first,
                "steady_state_pass": steady,
                "overall_status": row["overall_status"],
            }
        )
    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    ax.imshow(counts, cmap="YlGn", vmin=0, vmax=max(1, int(counts.max())))
    for steady in range(2):
        for first in range(2):
            ax.text(
                first,
                steady,
                f"{counts[steady, first]} records",
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color=(
                    "white"
                    if counts[steady, first] > max(1, int(counts.max())) / 2
                    else "#17324d"
                ),
            )
    ax.set_xticks((0, 1), ("FAIL", "PASS"))
    ax.set_yticks((0, 1), ("FAIL", "PASS"))
    ax.set_xlabel("First-conversion gate")
    ax.set_ylabel("Steady-state dynamic gate")
    ax.set_title("Independent first-conversion and steady-state status")
    if failing_labels:
        ax.text(
            1.04,
            0.5,
            "Non-PASS records:\n" + "\n".join(failing_labels),
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=8,
            color="#8f2437",
        )
        fig.subplots_adjust(right=0.75)
    return fig, source


def representative_spectra() -> tuple[plt.Figure, list[dict[str, object]]]:
    master = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    selected = []
    for band in ("LOW", "NEAR_NYQUIST"):
        candidates = [row for row in master if row["band"] == band]
        if candidates:
            selected.append(min(candidates, key=lambda row: float(row["steady_state_sndr_db"])))
    source: list[dict[str, object]] = []
    fig, axes = plt.subplots(len(selected), 1, figsize=(8.0, 6.0), squeeze=False)
    for axis, row in zip(axes[:, 0], selected):
        code_rows = read_csv(CSV_DIR / "job_codes" / f"{row['job_id']}.csv")
        codes = [
            int(code["code"])
            for code in code_rows
            if truth(code["retained"])
        ]
        spectrum = spectrum_rows(codes, BANDS[row["band"]]["bin"])
        for item in spectrum:
            item.update(
                {
                    "job_id": row["job_id"],
                    "mismatch_seed": row["mismatch_seed"],
                    "band": row["band"],
                    "method_label": "FAST64 steady-state W4, frames 4-67",
                    "units": "dBFS/bin",
                }
            )
        source.extend(spectrum)
        bins = [int(item["bin"]) for item in spectrum]
        values = [float(item["magnitude_db"]) for item in spectrum]
        markerline, stemlines, baseline = axis.stem(bins, values, basefmt=" ")
        plt.setp(markerline, markersize=3, color="#277da1")
        plt.setp(stemlines, linewidth=0.8, color="#277da1")
        axis.set_ylabel("dBFS/bin")
        axis.set_title(
            f"S{int(row['mismatch_seed']):03d} {row['band']} - SS W4"
        )
        axis.set_xlim(-0.5, 32.5)
        axis.set_ylim(min(values) - 3, max(values) + 3)
    axes[-1, 0].set_xlabel("FFT bin")
    fig.suptitle("Representative 64-point steady-state spectra", y=1.01)
    fig.tight_layout()
    return fig, source


def main() -> int:
    setup_style()
    figure_builders: list[
        tuple[str, Callable[[], tuple[plt.Figure, list[dict[str, object]]]]]
    ] = [
        ("fig01_first_conversion_gate_matrix", first_conversion_gate),
        ("fig02_w4_w8_canonical_difference", warmup_difference),
        ("fig03_w0_vs_w4_sndr_dumbbell", w0_w4_dumbbell),
        ("fig04_frame0_frame64_path", first_path_pairs),
        ("fig05_percentile_bridge", bridge_plot),
        ("fig06_steady_state_sndr_enob", steady_metrics),
        ("fig07_first_vs_steady_status", status_matrix),
        ("fig08_representative_spectra", representative_spectra),
    ]
    inventory: list[dict[str, object]] = []
    for stem, builder in figure_builders:
        fig, source = builder()
        inventory.append(save_figure(fig, stem, source))
    write_csv_atomic(PLOT_DIR / "plot_inventory.csv", inventory)
    payload = {
        "status": "PASS_FAST64_V2_PLOT_GENERATION",
        "pass": len(inventory) == 8,
        "figure_count": len(inventory),
        "pdf_count": sum(Path(ROOT / row["pdf"]).is_file() for row in inventory),
        "png_count": sum(Path(ROOT / row["png"]).is_file() for row in inventory),
        "source_csv_count": sum(
            Path(ROOT / row["source_csv"]).is_file() for row in inventory
        ),
    }
    write_json_atomic(ROOT / "results/plot_generation.json", payload)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
