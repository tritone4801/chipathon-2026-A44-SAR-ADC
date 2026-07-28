#!/usr/bin/env python3
"""Generate the frozen-format MC10 reproduction evidence plots."""

from __future__ import annotations

import csv
import hashlib
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


PLOT_ROOT = ROOT / "plots" / "formal"
SOURCE_ROOT = PLOT_ROOT / "source"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
    }
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def as_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def style_axis(axis) -> None:
    axis.set_facecolor("#f7f7f7")
    axis.grid(True, color="#bdbdbd", linestyle=":", linewidth=0.7)
    for spine in axis.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.0)


class Inventory:
    def __init__(self) -> None:
        self.rows = []

    def save(self, fig, stem: str, plot_type: str, source: Path, scope: str) -> None:
        pdf = PLOT_ROOT / f"{stem}.pdf"
        png = PLOT_ROOT / f"{stem}.png"
        fig.savefig(pdf, bbox_inches="tight")
        fig.savefig(png, dpi=300, bbox_inches="tight")
        plt.close(fig)
        self.rows.append(
            {
                "figure_id": stem,
                "plot_type": plot_type,
                "scope": scope,
                "pdf": pdf.relative_to(ROOT).as_posix(),
                "png": png.relative_to(ROOT).as_posix(),
                "source_csv": source.relative_to(ROOT).as_posix(),
                "pdf_sha256": sha256(pdf),
                "png_sha256": sha256(png),
                "source_sha256": sha256(source),
            }
        )


def code_map(rows, repeat_field=None):
    output = {}
    for row in rows:
        repeat = int(row[repeat_field]) if repeat_field else 0
        output[
            (
                int(row["mismatch_seed"]),
                row["band"],
                repeat,
                int(row["frame_index"]),
            )
        ] = int(row["code"])
    return output


def stream(mapping, seed, band, repeat=0):
    return [mapping[(seed, band, repeat, frame)] for frame in range(64)]


def strict_matrix(inventory: Inventory, comparison: list[dict]) -> None:
    seeds = sorted({int(row["mismatch_seed"]) for row in comparison})
    bands = ["LOW", "NEAR_NYQUIST"]
    source_rows = []
    matrix = np.zeros((len(seeds), 2))
    lookup = {(int(row["mismatch_seed"]), row["band"]): row for row in comparison}
    for y, seed in enumerate(seeds):
        for x, band in enumerate(bands):
            exact = as_bool(lookup[(seed, band)]["record_exact"])
            matrix[y, x] = 1 if exact else 0
            source_rows.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "record_exact": exact,
                    "different_frames": lookup[(seed, band)]["different_frames"],
                }
            )
    source = SOURCE_ROOT / "strict_reproduction_matrix.csv"
    write_csv(source, source_rows)
    fig, axis = plt.subplots(figsize=(6.8, 7.0), facecolor="#eeeeee")
    image = axis.imshow(
        matrix,
        cmap=matplotlib.colors.ListedColormap(["#d55e00", "#009e73"]),
        vmin=0,
        vmax=1,
        aspect="auto",
    )
    axis.set_xticks(range(2), ["LOW", "NEAR NYQUIST"])
    axis.set_yticks(range(len(seeds)), [str(seed) for seed in seeds])
    axis.set_xlabel("Band")
    axis.set_ylabel("Mismatch seed")
    axis.set_title("Current MC200 Strict Reproduction Matrix")
    for y, seed in enumerate(seeds):
        for x, band in enumerate(bands):
            row = lookup[(seed, band)]
            axis.text(
                x,
                y,
                "EXACT" if as_bool(row["record_exact"]) else f"DIFF {row['different_frames']}",
                ha="center",
                va="center",
                color="white",
                fontsize=8,
                fontweight="bold",
            )
    axis.set_xticks(np.arange(-0.5, 2, 1), minor=True)
    axis.set_yticks(np.arange(-0.5, len(seeds), 1), minor=True)
    axis.grid(which="minor", color="white", linewidth=1.0)
    axis.grid(False, which="major")
    fig.colorbar(image, ax=axis, ticks=[0, 1], label="0=DIFF, 1=EXACT")
    inventory.save(fig, "strict_reproduction_matrix", "STRICT_MATRIX", source, "20_RECORDS")


def delta_plots(
    inventory: Inventory,
    comparison: list[dict],
    current_codes,
    new_codes,
) -> None:
    for item in comparison:
        if as_bool(item["record_exact"]):
            continue
        seed = int(item["mismatch_seed"])
        band = item["band"]
        expected = stream(current_codes, seed, band)
        actual = stream(new_codes, seed, band)
        rows = [
            {
                "mismatch_seed": seed,
                "band": band,
                "frame_index": frame,
                "current_mc200_code": expected[frame],
                "mc10_code": actual[frame],
                "delta_code": actual[frame] - expected[frame],
            }
            for frame in range(64)
        ]
        stem = f"code_delta_s{seed:03d}_{band.lower()}"
        source = SOURCE_ROOT / f"{stem}.csv"
        write_csv(source, rows)
        fig, axis = plt.subplots(figsize=(11.0, 4.8), facecolor="#eeeeee")
        style_axis(axis)
        x = np.arange(64)
        y = np.asarray([row["delta_code"] for row in rows])
        axis.vlines(x, 0, y, color="#0067b1", linewidth=1.0)
        axis.scatter(x, y, color="#0067b1", s=18, zorder=3)
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_xlim(-1, 64)
        bound = max(4, int(math.ceil(max(abs(y.min()), abs(y.max())) / 4) * 4))
        axis.set_ylim(-bound * 1.15, bound * 1.15)
        axis.set_xlabel("Frame index")
        axis.set_ylabel("MC10 - current MC200 [code]")
        axis.set_title(f"Frame Code Delta - Seed {seed} {band}")
        fig.text(
            0.99,
            0.02,
            "maxstep=50 ps | ROBUST_GEAR | compact FAST64",
            ha="right",
            va="bottom",
            fontsize=8,
        )
        inventory.save(fig, stem, "FRAME_CODE_DELTA", source, f"{seed}:{band}")


def seed110_plot(
    inventory: Inventory,
    current_codes,
    primary_codes,
    diagnostic_codes,
    repeat_rows,
) -> None:
    seed = 110
    band = "LOW"
    current_stream = stream(current_codes, seed, band)
    streams = [stream(primary_codes, seed, band)]
    streams.extend(stream(diagnostic_codes, seed, band, repeat) for repeat in range(1, 5))
    labels = ["Formal first run", "Diag R1 single", "Diag R2 single", "Diag R3 four", "Diag R4 four"]
    rows = []
    matrix = []
    for index, (label, values) in enumerate(zip(labels, streams), start=1):
        branch = "CURRENT_MC200" if values == current_stream else "OTHER_BRANCH"
        matching = next(
            (
                row["matching_branches"]
                for row in repeat_rows
                if int(row["mismatch_seed"]) == seed
                and row["band"] == band
                and int(row["diagnostic_repeat"]) == index - 1
            ),
            branch,
        )
        branch = matching if index > 1 else branch
        rows.append(
            {
                "sequence": index,
                "run": label,
                "frame0": values[0],
                "sndr_branch": branch,
                "matches_current_mc200": values == current_stream,
            }
        )
        matrix.append([1 if code == ref else 0 for code, ref in zip(values, current_stream)])
    source = SOURCE_ROOT / "seed110_five_run_branch_matrix.csv"
    write_csv(source, rows)
    fig, axis = plt.subplots(figsize=(12.0, 4.4), facecolor="#eeeeee")
    image = axis.imshow(
        np.asarray(matrix),
        cmap=matplotlib.colors.ListedColormap(["#d55e00", "#009e73"]),
        vmin=0,
        vmax=1,
        aspect="auto",
    )
    axis.set_yticks(range(5), labels)
    axis.set_xticks(np.arange(0, 64, 4))
    axis.set_xlabel("Frame index")
    axis.set_title("Seed110 LOW - Five New Runs vs Current MC200")
    axis.set_xticks(np.arange(-0.5, 64, 1), minor=True)
    axis.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    axis.grid(which="minor", color="white", linewidth=0.25)
    axis.grid(False, which="major")
    fig.colorbar(image, ax=axis, ticks=[0, 1], label="0=different, 1=exact")
    inventory.save(
        fig,
        "seed110_five_run_branch_matrix",
        "SEED110_BRANCH_MATRIX",
        source,
        "SEED110_LOW",
    )


def spectrum_compare(
    inventory: Inventory,
    comparison: list[dict],
    master_rows,
    current_codes,
    new_codes,
) -> None:
    selected = {47, 53, 71, 109, 195}
    master = {(int(row["mismatch_seed"]), row["band"]): row for row in master_rows}
    for item in comparison:
        seed = int(item["mismatch_seed"])
        band = item["band"]
        if seed not in selected or as_bool(item["record_exact"]):
            continue
        metadata = master[(seed, band)]
        series = {
            "CURRENT_MC200": spectrum_rows(
                stream(current_codes, seed, band), int(metadata["bin"])
            ),
            "NEW_MC10": spectrum_rows(
                stream(new_codes, seed, band), int(metadata["bin"])
            ),
        }
        rows = []
        for label, values in series.items():
            for row in values:
                rows.append(
                    {
                        "mismatch_seed": seed,
                        "band": band,
                        "series": label,
                        "bin": row["bin"],
                        "frequency_mhz": row["freq_hz"] / 1e6,
                        "amplitude_dbfs_per_bin": row["magnitude_db"],
                        "amplitude_unit": "dBFS/bin",
                        "display_clipped": False,
                        "is_fundamental": row["is_fundamental"],
                        "is_hd2": row["is_hd2"],
                        "is_hd3": row["is_hd3"],
                        "is_largest_spur": row["is_largest_spur"],
                    }
                )
        stem = f"spectrum_compare_s{seed:03d}_{band.lower()}"
        source = SOURCE_ROOT / f"{stem}.csv"
        write_csv(source, rows)
        minimum = min(float(row["amplitude_dbfs_per_bin"]) for row in rows)
        lower = min(-100.0, math.floor(minimum / 10.0) * 10.0)
        fig, axis = plt.subplots(figsize=(12.0, 6.0), facecolor="#eeeeee")
        fig.subplots_adjust(right=0.74)
        style_axis(axis)
        for label, color, offset in (
            ("CURRENT_MC200", "#d55e00", -0.003),
            ("NEW_MC10", "#0067b1", 0.003),
        ):
            subset = [row for row in rows if row["series"] == label]
            x = [float(row["frequency_mhz"]) + offset for row in subset]
            y = [float(row["amplitude_dbfs_per_bin"]) for row in subset]
            axis.vlines(x, lower, y, color=color, linewidth=0.8, alpha=0.85)
            axis.scatter(x, y, color=color, s=14, label=label, zorder=3)
        axis.set_xlim(0, 1.0)
        axis.set_ylim(lower, 0)
        axis.set_xlabel("Frequency [MHz]")
        axis.set_ylabel("Amplitude [dBFS/bin]")
        axis.set_title(f"Discrete Spectrum Comparison - Seed {seed} {band}")
        axis.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
        fig.text(
            0.76,
            0.72,
            "NFFT=64\nFs=2.000 MHz\nWindow=rectangular\n"
            "No floor clipping\nmaxstep=50 ps\nROBUST_GEAR",
            ha="left",
            va="top",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "black"},
        )
        inventory.save(fig, stem, "DISCRETE_SPECTRUM_COMPARE", source, f"{seed}:{band}")


def state_change_plot(inventory: Inventory, comparison: list[dict]) -> None:
    rows = []
    categories = []
    for item in comparison:
        expected = item["expected_state"]
        actual = item["actual_state"]
        if expected == "VALID_PASS" and actual == "VALID_FAIL":
            category = "PASS_TO_FAIL"
        elif expected == "VALID_FAIL" and actual == "VALID_PASS":
            category = "FAIL_TO_PASS"
        elif expected == actual:
            category = "UNCHANGED"
        else:
            category = "OTHER"
        rows.append(
            {
                "mismatch_seed": item["mismatch_seed"],
                "band": item["band"],
                "current_mc200_state": expected,
                "new_mc10_state": actual,
                "change_category": category,
            }
        )
        categories.append(category)
    source = SOURCE_ROOT / "state_change_map.csv"
    write_csv(source, rows)
    labels = [f"S{row['mismatch_seed']} {row['band'].replace('_NYQUIST', 'N')}" for row in rows]
    mapping = {"UNCHANGED": 0, "PASS_TO_FAIL": -1, "FAIL_TO_PASS": 1, "OTHER": 2}
    colors = {
        "UNCHANGED": "#999999",
        "PASS_TO_FAIL": "#d55e00",
        "FAIL_TO_PASS": "#009e73",
        "OTHER": "#cc79a7",
    }
    x = np.arange(len(rows))
    fig, axis = plt.subplots(figsize=(13.0, 5.2), facecolor="#eeeeee")
    style_axis(axis)
    axis.scatter(
        x,
        [mapping[item] for item in categories],
        c=[colors[item] for item in categories],
        s=70,
        edgecolors="black",
        linewidths=0.5,
    )
    axis.set_xticks(x, labels, rotation=55, ha="right")
    axis.set_yticks([-1, 0, 1, 2], ["PASS→FAIL", "UNCHANGED", "FAIL→PASS", "OTHER"])
    axis.set_ylim(-1.6, 2.6)
    axis.set_title("Current MC200 to New MC10 State Changes")
    axis.set_ylabel("State transition")
    inventory.save(fig, "state_change_map", "STATE_CHANGE_MAP", source, "20_RECORDS")


def validate(inventory: Inventory) -> dict:
    checks = {}
    for item in inventory.rows:
        pdf = ROOT / item["pdf"]
        png = ROOT / item["png"]
        source = ROOT / item["source_csv"]
        with Image.open(png) as image:
            dpi = image.info.get("dpi", (0, 0))
            checks[f"{item['figure_id']}_png_300dpi"] = min(dpi) >= 299
            checks[f"{item['figure_id']}_png_size"] = (
                image.width >= 1000 and image.height >= 600
            )
        checks[f"{item['figure_id']}_pdf_vector_container"] = (
            pdf.read_bytes()[:4] == b"%PDF"
        )
        checks[f"{item['figure_id']}_source_nonempty"] = source.stat().st_size > 40
    return {
        "status": "PASS_MC10_PLOT_AUDIT" if all(checks.values()) else "FAIL_MC10_PLOT_AUDIT",
        "pass": all(checks.values()),
        "figure_count": len(inventory.rows),
        "checks": checks,
    }


def main() -> int:
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    comparison = read_csv(ROOT / "comparisons" / "current_mc200_strict_comparison.csv")
    current_code_rows = read_csv(ROOT / "references" / "current_mc200_target_codes.csv")
    new_code_rows = read_csv(ROOT / "csv" / "mc10_codes.csv")
    diagnostic_code_rows = read_csv(ROOT / "diagnostics" / "diagnostic_codes.csv")
    repeat_rows = read_csv(ROOT / "diagnostics" / "diagnostic_repeat_classification.csv")
    master_rows = read_csv(ROOT / "csv" / "mc10_master.csv")
    current_codes = code_map(current_code_rows)
    new_codes = code_map(new_code_rows)
    diagnostic_codes = code_map(diagnostic_code_rows, "diagnostic_repeat")
    inventory = Inventory()
    strict_matrix(inventory, comparison)
    delta_plots(inventory, comparison, current_codes, new_codes)
    seed110_plot(
        inventory,
        current_codes,
        new_codes,
        diagnostic_codes,
        repeat_rows,
    )
    spectrum_compare(inventory, comparison, master_rows, current_codes, new_codes)
    state_change_plot(inventory, comparison)
    write_csv(ROOT / "manifests" / "mc10_plot_inventory.csv", inventory.rows)
    audit = validate(inventory)
    (ROOT / "results" / "mc10_plot_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
