#!/usr/bin/env python3
"""Generate paired baseline/CMP_IN_A2P25_W MC200 LOW W4 plots."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fast64_v2_common import CSV_DIR, RESULT_DIR, ROOT, read_csv, sha256_file, write_json_atomic


PLOT_DIR = ROOT / "plots/comparison"
COLORS = {
    "baseline": "#4C78A8",
    "candidate": "#F58518",
    "pass": "#2A9D8F",
    "fail": "#D1495B",
}


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def save(stem: str, fig: plt.Figure) -> dict[str, object]:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    png = PLOT_DIR / f"{stem}.png"
    pdf = PLOT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {
        "stem": stem,
        "png": png.relative_to(ROOT).as_posix(),
        "png_sha256": sha256_file(png),
        "pdf": pdf.relative_to(ROOT).as_posix(),
        "pdf_sha256": sha256_file(pdf),
    }


def main() -> int:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 9,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    rows = read_csv(CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv")
    if len(rows) != 200:
        raise RuntimeError("paired MC200 table must contain 200 rows")
    seeds = np.asarray([int(row["mismatch_seed"]) for row in rows])
    baseline = np.asarray([float(row["baseline_w4_sndr_db"]) for row in rows])
    candidate = np.asarray([float(row["candidate_w4_sndr_db"]) for row in rows])
    delta = candidate - baseline
    inventory: list[dict[str, object]] = []

    limits = (
        np.floor(min(float(np.min(baseline)), float(np.min(candidate)))),
        np.ceil(max(float(np.max(baseline)), float(np.max(candidate)))),
    )
    fig, ax = plt.subplots(figsize=(5.7, 5.2))
    ax.scatter(baseline, candidate, s=18, color=COLORS["candidate"], alpha=0.86)
    ax.plot(limits, limits, color="black", linestyle="--", linewidth=0.9)
    ax.axhline(46.91, color=COLORS["fail"], linestyle=":", linewidth=1.0)
    ax.axvline(46.91, color=COLORS["fail"], linestyle=":", linewidth=1.0)
    ax.set_xlim(*limits)
    ax.set_ylim(*limits)
    ax.set_xlabel("Baseline FAST64_SS_W4 SNDR [dB]")
    ax.set_ylabel("CMP_IN_A2P25_W FAST64_SS_W4 SNDR [dB]")
    ax.set_title("MC200 LOW paired SNDR — fixed 50 ps")
    inventory.append(save("paired_sndr_baseline_vs_cmp_in_a2p25_w", fig))

    fig, ax = plt.subplots(figsize=(7.4, 4.1))
    colors = np.where(delta >= 0.0, COLORS["pass"], COLORS["fail"])
    ax.bar(seeds, delta, width=0.82, color=colors)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlim(0, 201)
    ax.set_xlabel("Mismatch seed")
    ax.set_ylabel("Candidate − baseline SNDR [dB]")
    ax.set_title("MC200 LOW paired ΔSNDR — FAST64_SS_W4")
    inventory.append(save("paired_delta_sndr_by_seed", fig))

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for values, label, color in (
        (baseline, "Baseline", COLORS["baseline"]),
        (candidate, "CMP_IN_A2P25_W", COLORS["candidate"]),
    ):
        ordered = np.sort(values)
        ecdf = np.arange(1, len(ordered) + 1) / len(ordered)
        ax.step(ordered, ecdf, where="post", label=label, color=color, linewidth=1.4)
    ax.axvline(46.91, color=COLORS["fail"], linestyle="--", linewidth=1.0, label="SNDR gate")
    ax.set_xlabel("Steady-state SNDR [dB]")
    ax.set_ylabel("Empirical CDF")
    ax.set_ylim(0.0, 1.02)
    ax.set_title("MC200 LOW SNDR ECDF — baseline versus 2.25×")
    ax.legend(loc="lower right")
    inventory.append(save("paired_sndr_ecdf", fig))

    baseline_pass = np.asarray(
        [truth(row["baseline_hard_dynamic_pass"]) for row in rows], dtype=int
    )
    candidate_pass = np.asarray(
        [truth(row["candidate_hard_dynamic_pass"]) for row in rows], dtype=int
    )
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 3.8), sharex=True)
    for ax, values, title in (
        (axes[0], baseline_pass, "Baseline"),
        (axes[1], candidate_pass, "CMP_IN_A2P25_W"),
    ):
        ax.scatter(
            seeds,
            values,
            c=[COLORS["pass"] if value else COLORS["fail"] for value in values],
            s=14,
        )
        ax.set_yticks([0, 1], labels=["FAIL", "PASS"])
        ax.set_ylim(-0.35, 1.35)
        ax.set_title(title, loc="left", fontsize=9)
    axes[-1].set_xlabel("Mismatch seed")
    fig.suptitle("MC200 LOW hard-dynamic status map — fixed method", y=1.01)
    fig.tight_layout()
    inventory.append(save("paired_hard_dynamic_status_map", fig))

    audit = {
        "status": "PASS_COMPARISON_PLOT_AUDIT",
        "pass": True,
        "candidate_id": "CMP_IN_A2P25_W",
        "population_count": 200,
        "artifact_count": len(inventory) * 2,
        "inventory": inventory,
        "style": {
            "font": "DejaVu Serif",
            "png_dpi": 300,
            "pdf": "vector",
            "smoothing": False,
        },
        "source_csv": "csv/paired_baseline_candidate_mc200_low_w4.csv",
        "source_csv_sha256": sha256_file(
            CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv"
        ),
    }
    write_json_atomic(RESULT_DIR / "comparison_plot_audit.json", audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
