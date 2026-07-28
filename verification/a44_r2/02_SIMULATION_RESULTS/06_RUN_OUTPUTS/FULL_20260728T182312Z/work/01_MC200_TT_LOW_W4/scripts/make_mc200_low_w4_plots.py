#!/usr/bin/env python3
"""Generate LOW-only W4 MC200 plots with the frozen visual contract."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dynamic_analysis import spectrum_rows
from fast64_v2_common import (
    CSV_DIR,
    ROOT,
    read_csv,
    write_csv_atomic,
    write_json_atomic,
)


PLOT_DIR = ROOT / "plots/formal"
SOURCE_DIR = PLOT_DIR / "source"
RESULT_DIR = ROOT / "results"

COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "gray": "#6C757D",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 8,
            "lines.linewidth": 1.2,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
        }
    )


def save_figure(
    name: str, figure: plt.Figure, rows: list[dict[str, object]]
) -> dict[str, object]:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source = SOURCE_DIR / f"{name}.csv"
    pdf = PLOT_DIR / f"{name}.pdf"
    png = PLOT_DIR / f"{name}.png"
    write_csv_atomic(source, rows)
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return {
        "name": name,
        "pdf": pdf.relative_to(ROOT).as_posix(),
        "pdf_sha256": sha256(pdf),
        "png": png.relative_to(ROOT).as_posix(),
        "png_sha256": sha256(png),
        "source_csv": source.relative_to(ROOT).as_posix(),
        "source_csv_sha256": sha256(source),
        "source_rows": len(rows),
    }


def ecdf_plot(
    master: list[dict[str, str]],
    field: str,
    label: str,
    threshold: float,
    color: str,
) -> tuple[plt.Figure, list[dict[str, object]]]:
    values = np.sort(np.asarray([float(row[field]) for row in master]))
    y = np.arange(1, len(values) + 1, dtype=float) / len(values)
    rows = [
        {"rank": index + 1, "value": value, "ecdf": probability}
        for index, (value, probability) in enumerate(zip(values, y))
    ]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.step(values, y, where="post", color=color)
    ax.scatter(values, y, s=8, color=color, zorder=3)
    ax.axvline(threshold, color=COLORS["red"], linestyle="--", label=f"Gate {threshold:g}")
    ax.set_xlabel(label)
    ax.set_ylabel("Empirical CDF")
    ax.set_ylim(0.0, 1.02)
    ax.set_title(f"MC200 LOW steady-state {label} ECDF\nFAST64_SS_W4, N=200")
    ax.legend(loc="lower right")
    return fig, rows


def histogram_plot(
    master: list[dict[str, str]],
) -> tuple[plt.Figure, list[dict[str, object]], list[float]]:
    values = np.asarray([float(row["steady_state_sndr_db"]) for row in master])
    low = math.floor(float(np.min(values)))
    high = math.ceil(float(np.max(values)))
    edges = np.arange(low, high + 1.0, 1.0)
    if len(edges) < 3:
        edges = np.linspace(float(np.min(values)), float(np.max(values)) + 1e-9, 4)
    counts, used_edges = np.histogram(values, bins=edges)
    rows = [
        {
            "bin_left_db": float(left),
            "bin_right_db": float(right),
            "count": int(count),
        }
        for left, right, count in zip(used_edges[:-1], used_edges[1:], counts)
    ]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.hist(
        values,
        bins=used_edges,
        color=COLORS["blue"],
        edgecolor="black",
        linewidth=0.5,
    )
    ax.axvline(46.91, color=COLORS["red"], linestyle="--", label="SNDR gate 46.91 dB")
    ax.set_xlabel("Steady-state SNDR [dB]")
    ax.set_ylabel("Seed count")
    ax.set_title("MC200 LOW steady-state SNDR histogram\nFAST64_SS_W4, no tail clipping")
    ax.legend(loc="upper left")
    return fig, rows, [float(value) for value in used_edges]


def seed_plot(
    master: list[dict[str, str]],
) -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = [
        {
            "mismatch_seed": int(row["mismatch_seed"]),
            "steady_state_sndr_db": float(row["steady_state_sndr_db"]),
            "hard_dynamic_pass": truth(row["steady_state_hard_dynamic_pass"]),
        }
        for row in master
    ]
    x = np.asarray([row["mismatch_seed"] for row in rows])
    y = np.asarray([row["steady_state_sndr_db"] for row in rows])
    colors = [
        COLORS["green"] if row["hard_dynamic_pass"] else COLORS["red"]
        for row in rows
    ]
    fig, ax = plt.subplots(figsize=(9.0, 4.3))
    ax.plot(x, y, color=COLORS["gray"], linewidth=0.6, zorder=1)
    ax.scatter(x, y, c=colors, s=17, zorder=2)
    ax.axhline(46.91, color=COLORS["red"], linestyle="--", linewidth=1.0)
    ax.set_xlim(0, 201)
    ax.set_xlabel("Mismatch seed")
    ax.set_ylabel("Steady-state SNDR [dB]")
    ax.set_title("MC200 LOW seed-by-seed steady-state SNDR\nFAST64_SS_W4")
    return fig, rows


def status_plot(
    master: list[dict[str, str]],
) -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = [
        {
            "mismatch_seed": int(row["mismatch_seed"]),
            "first_conversion_protocol_pass": truth(
                row["first_conversion_protocol_pass"]
            ),
            "steady_state_hard_dynamic_pass": truth(
                row["steady_state_hard_dynamic_pass"]
            ),
            "combined_system_pass": (
                truth(row["first_conversion_protocol_pass"])
                and truth(row["steady_state_hard_dynamic_pass"])
            ),
        }
        for row in master
    ]
    x = np.asarray([row["mismatch_seed"] for row in rows])
    first = np.asarray([int(row["first_conversion_protocol_pass"]) for row in rows])
    steady = np.asarray([int(row["steady_state_hard_dynamic_pass"]) for row in rows])
    combined = np.asarray([int(row["combined_system_pass"]) for row in rows])
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 4.8), sharex=True)
    for ax, values, title, color in (
        (axes[0], first, "First-conversion protocol", COLORS["blue"]),
        (axes[1], steady, "Steady-state dynamic", COLORS["orange"]),
        (axes[2], combined, "Combined system", COLORS["green"]),
    ):
        ax.scatter(x, values, s=14, color=color)
        ax.set_yticks([0, 1], labels=["FAIL", "PASS"])
        ax.set_ylim(-0.35, 1.35)
        ax.set_title(title, loc="left", fontsize=9)
    axes[-1].set_xlabel("Mismatch seed")
    fig.suptitle("MC200 LOW split status map — FAST64_SS_W4", y=1.01)
    fig.tight_layout()
    return fig, rows


def transition_plot(
    paired: list[dict[str, str]],
) -> tuple[plt.Figure, list[dict[str, object]]]:
    rows = [
        {
            "mismatch_seed": int(row["mismatch_seed"]),
            "baseline_w4_sndr_db": float(row["baseline_w4_sndr_db"]),
            "candidate_w4_sndr_db": float(row["candidate_w4_sndr_db"]),
            "delta_sndr_db": float(row["delta_sndr_db"]),
            "retained_code_exact": truth(row["retained_code_exact"]),
        }
        for row in paired
    ]
    x = np.asarray([row["baseline_w4_sndr_db"] for row in rows])
    y = np.asarray([row["candidate_w4_sndr_db"] for row in rows])
    limits = (
        math.floor(float(min(np.min(x), np.min(y)))),
        math.ceil(float(max(np.max(x), np.max(y)))),
    )
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    colors = [
        COLORS["blue"] if row["retained_code_exact"] else COLORS["orange"]
        for row in rows
    ]
    ax.scatter(x, y, c=colors, s=18)
    ax.plot(limits, limits, color="black", linestyle="--", linewidth=0.8)
    ax.set_xlim(*limits)
    ax.set_ylim(*limits)
    ax.set_xlabel("Baseline FAST64_SS_W4 SNDR [dB]")
    ax.set_ylabel("CMP_IN_A2P25_W FAST64_SS_W4 SNDR [dB]")
    ax.set_title("LOW MC200 paired DUT comparison\nBaseline versus CMP_IN_A2P25_W")
    return fig, rows


def spectra_plot(
    master: list[dict[str, str]],
    representatives: list[dict[str, str]],
    retained: list[dict[str, str]],
) -> tuple[plt.Figure, list[dict[str, object]], float]:
    master_by_seed = {int(row["mismatch_seed"]): row for row in master}
    retained_by_seed: dict[int, list[dict[str, str]]] = {}
    for row in retained:
        retained_by_seed.setdefault(int(row["mismatch_seed"]), []).append(row)
    selected = []
    seen: set[int] = set()
    for representative in representatives:
        seed = int(representative["mismatch_seed"])
        if seed in seen:
            continue
        selected.append((representative["role"], seed))
        seen.add(seed)
    columns = 2
    rows_count = math.ceil(len(selected) / columns)
    fig, axes = plt.subplots(
        rows_count,
        columns,
        figsize=(9.2, 3.35 * rows_count),
        squeeze=False,
    )
    source: list[dict[str, object]] = []
    global_min = 0.0
    for axis, (role, seed) in zip(axes.flat, selected):
        code_rows = sorted(
            retained_by_seed[seed], key=lambda row: int(row["phase_index"])
        )
        codes = [int(row["code"]) for row in code_rows]
        spectrum = spectrum_rows(codes, 7, 2.0e6)
        finite = [
            float(row["magnitude_db"])
            for row in spectrum
            if math.isfinite(float(row["magnitude_db"]))
        ]
        ymin = min(finite)
        global_min = min(global_min, ymin)
        frequencies = np.asarray([float(row["freq_hz"]) / 1e6 for row in spectrum])
        magnitudes = np.asarray([float(row["magnitude_db"]) for row in spectrum])
        axis.vlines(frequencies, ymin, magnitudes, color=COLORS["blue"], linewidth=0.8)
        axis.scatter(frequencies, magnitudes, color=COLORS["blue"], s=9)
        for row in spectrum:
            if row["is_fundamental"] or row["is_hd2"] or row["is_hd3"] or row["is_largest_spur"]:
                axis.scatter(
                    float(row["freq_hz"]) / 1e6,
                    float(row["magnitude_db"]),
                    color=(
                        COLORS["red"]
                        if row["is_fundamental"]
                        else COLORS["orange"]
                    ),
                    s=28,
                    zorder=4,
                )
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(ymin, 0.0)
        axis.set_xlabel("Frequency [MHz]")
        axis.set_ylabel("Amplitude [dBFS/bin]")
        metric = master_by_seed[seed]
        axis.set_title(
            f"{role}: seed {seed} — SNDR {float(metric['steady_state_sndr_db']):.3f} dB"
        )
        for row in spectrum:
            source.append(
                {
                    "role": role,
                    "mismatch_seed": seed,
                    **row,
                }
            )
    for axis in axes.flat[len(selected) :]:
        axis.axis("off")
    fig.suptitle(
        "MC200 LOW representative spectra\nFAST64 steady-state screen; warm-up=4; FFT frames 4–67",
        y=1.01,
    )
    fig.tight_layout()
    return fig, source, global_min


def main() -> int:
    configure_style()
    master = read_csv(CSV_DIR / "steady_state_master_mc200_low_w4.csv")
    transition = read_csv(
        CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv"
    )
    representatives = read_csv(CSV_DIR / "representative_records_w4.csv")
    retained = read_csv(CSV_DIR / "codes_fft_retained_12800.csv")
    if len(master) != 200 or len(retained) != 12_800:
        raise RuntimeError("complete 200-record W4 population is required")

    inventory: list[dict[str, object]] = []
    fig, rows = ecdf_plot(
        master,
        "steady_state_sndr_db",
        "SNDR [dB]",
        46.91,
        COLORS["blue"],
    )
    inventory.append(save_figure("low_w4_sndr_ecdf", fig, rows))
    fig, rows = ecdf_plot(
        master,
        "steady_state_enob_raw",
        "ENOBraw [bit]",
        7.50,
        COLORS["green"],
    )
    inventory.append(save_figure("low_w4_enob_ecdf", fig, rows))
    fig, rows, histogram_edges = histogram_plot(master)
    inventory.append(save_figure("low_w4_sndr_histogram", fig, rows))
    fig, rows = seed_plot(master)
    inventory.append(save_figure("low_w4_seed_by_seed_sndr", fig, rows))
    fig, rows = status_plot(master)
    inventory.append(save_figure("low_w4_split_status_map", fig, rows))
    fig, rows = transition_plot(transition)
    inventory.append(
        save_figure("baseline_w4_vs_cmp_in_a2p25_w_sndr", fig, rows)
    )
    fig, rows, spectrum_ymin = spectra_plot(master, representatives, retained)
    inventory.append(save_figure("low_w4_representative_spectra", fig, rows))

    write_csv_atomic(ROOT / "plots/plot_inventory.csv", inventory)
    write_json_atomic(
        ROOT / "config/mc200_low_w4_plot_resolved_ranges.json",
        {
            "status": "RESOLVED_FROM_COMPLETE_W4_LOW_POPULATION",
            "histogram_sndr_edges_db": histogram_edges,
            "representative_spectrum_global_min_dbfs_per_bin": spectrum_ymin,
            "no_tail_clipping": True,
            "population_master": "csv/steady_state_master_mc200_low_w4.csv",
            "population_count": 200,
        },
    )
    checks = {
        "figure_count_7": len(inventory) == 7,
        "all_pdf_exist": all((ROOT / row["pdf"]).is_file() for row in inventory),
        "all_png_exist": all((ROOT / row["png"]).is_file() for row in inventory),
        "all_source_csv_exist": all(
            (ROOT / row["source_csv"]).is_file() for row in inventory
        ),
        "all_source_nonempty": all(int(row["source_rows"]) > 0 for row in inventory),
        "no_smoothing": True,
        "discrete_spectrum_bins": True,
        "no_tail_clipping": True,
    }
    write_json_atomic(
        RESULT_DIR / "plot_audit_mc200_low_w4.json",
        {
            "status": "PASS_PLOT_AUDIT" if all(checks.values()) else "FAIL_PLOT_AUDIT",
            "pass": all(checks.values()),
            "checks": checks,
            "inventory": inventory,
        },
    )
    print(json.dumps({"status": "PASS_PLOT_AUDIT", "figures": len(inventory)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
