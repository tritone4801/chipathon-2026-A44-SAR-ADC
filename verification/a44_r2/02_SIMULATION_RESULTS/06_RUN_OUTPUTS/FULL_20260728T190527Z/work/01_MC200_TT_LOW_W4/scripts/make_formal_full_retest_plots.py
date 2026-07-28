#!/usr/bin/env python3
"""Generate audited formal MC200 plots using the frozen dBFS/bin plotting contract."""

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
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

from dynamic_analysis import spectrum_rows
from sar_campaign_common import ROOT


PLOT_ROOT = ROOT / "plots" / "formal"
SOURCE_ROOT = PLOT_ROOT / "source"
REPORT_ROOT = ROOT / "reports"
METRICS = {
    "SNR": {"field": "snr_db", "label": "SNR [dB]", "hard": 48.14, "preferred": None},
    "SNDR": {"field": "sndr_db", "label": "SNDR [dB]", "hard": 46.91, "preferred": 47.75},
    "ENOB": {"field": "enob_raw", "label": "ENOB [bit]", "hard": 7.50, "preferred": 7.64},
    "SFDR": {"field": "sfdr_dbc", "label": "SFDR [dBc]", "hard": None, "preferred": None},
}

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


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else [])
    path.parent.mkdir(parents=True, exist_ok=True)
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


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def style_axis(axis):
    axis.set_facecolor("#f7f7f7")
    axis.grid(True, which="major", color="#bdbdbd", linestyle=":", linewidth=0.7)
    for spine in axis.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.0)


def add_reference_lines(axis, metric, vertical=True):
    config = METRICS[metric]
    method = axis.axvline if vertical else axis.axhline
    if config["hard"] is not None:
        method(
            config["hard"],
            color="#d55e00",
            linestyle="--",
            linewidth=1.2,
            label=f"Hard {config['hard']:.2f}",
        )
    if config["preferred"] is not None:
        method(
            config["preferred"],
            color="#009e73",
            linestyle="-.",
            linewidth=1.2,
            label=f"Preferred {config['preferred']:.2f}",
        )


def place_reference_legend_outside(fig, axis):
    fig.subplots_adjust(right=0.74)
    axis.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
        facecolor="white",
        edgecolor="black",
    )


class Inventory:
    def __init__(self):
        self.figures = []
        self.artifacts = []

    def save(self, fig, stem, plot_type, scope, source_path, roles=""):
        pdf = PLOT_ROOT / f"{stem}.pdf"
        png = PLOT_ROOT / f"{stem}.png"
        fig.savefig(pdf, bbox_inches="tight")
        fig.savefig(png, dpi=300, bbox_inches="tight")
        plt.close(fig)
        self.figures.append(
            {
                "figure_id": stem,
                "plot_type": plot_type,
                "scope": scope,
                "roles": roles,
                "pdf": pdf.relative_to(ROOT).as_posix(),
                "png": png.relative_to(ROOT).as_posix(),
                "source_csv": source_path.relative_to(ROOT).as_posix(),
            }
        )
        for format_name, path in (
            ("PDF_VECTOR", pdf),
            ("PNG_300_DPI", png),
            ("SOURCE_CSV", source_path),
        ):
            self.artifacts.append(
                {
                    "figure_id": stem,
                    "plot_type": plot_type,
                    "scope": scope,
                    "format": format_name,
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )


def build_scopes(master, combined):
    scopes = {
        "LOW": [row for row in master if row["band"] == "LOW"],
        "NEAR_NYQUIST": [
            row for row in master if row["band"] == "NEAR_NYQUIST"
        ],
        "WORST_BAND": [],
    }
    for row in combined:
        scopes["WORST_BAND"].append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "state": row["die_state"],
                "hard_dynamic_pass": row["hard_dynamic_pass_both"],
                "snr_budget_pass": row["snr_budget_pass_both"],
                "preferred_nominal_pass": row["preferred_nominal_pass_both"],
                "snr_db": row["snr_db_worst_band"],
                "sndr_db": row["sndr_db_worst_band"],
                "enob_raw": row["enob_raw_worst_band"],
                "sfdr_dbc": row["sfdr_dbc_worst_band"],
            }
        )
    return scopes


def resolved_edges(scopes):
    edges = {}
    steps = {"SNR": 1.0, "SNDR": 1.0, "ENOB": 0.1}
    for metric in ("SNR", "SNDR", "ENOB"):
        field = METRICS[metric]["field"]
        values = [
            float(row[field])
            for rows in scopes.values()
            for row in rows
            if row["state"] in {"VALID_PASS", "VALID_FAIL"}
        ]
        step = steps[metric]
        lower = math.floor(min(values) / step) * step
        upper = math.ceil(max(values) / step) * step
        count = max(8, int(round((upper - lower) / step)))
        edges[metric] = np.linspace(lower, upper, count + 1).tolist()
    return edges


def population_plots(scopes, edges, inventory):
    for scope, rows in scopes.items():
        valid = [row for row in rows if row["state"] in {"VALID_PASS", "VALID_FAIL"}]
        for metric in ("SNR", "SNDR", "ENOB"):
            config = METRICS[metric]
            values = np.asarray([float(row[config["field"]]) for row in valid])
            hist_counts, hist_edges = np.histogram(values, bins=np.asarray(edges[metric]))
            hist_rows = [
                {
                    "scope": scope,
                    "metric": metric,
                    "unit": config["label"].split("[", 1)[1].rstrip("]"),
                    "bin_left": hist_edges[index],
                    "bin_right": hist_edges[index + 1],
                    "count": int(hist_counts[index]),
                }
                for index in range(len(hist_counts))
            ]
            stem = f"{scope.lower()}_{metric.lower()}_histogram"
            source = SOURCE_ROOT / f"{stem}.csv"
            write_csv(source, hist_rows)
            fig, axis = plt.subplots(figsize=(10.0, 5.2), facecolor="#eeeeee")
            style_axis(axis)
            axis.hist(
                values,
                bins=hist_edges,
                color="#4c78a8",
                edgecolor="black",
                linewidth=0.7,
            )
            add_reference_lines(axis, metric, vertical=True)
            axis.set_xlabel(config["label"])
            axis.set_ylabel("Count")
            axis.set_title(f"{scope} {metric} Histogram", fontsize=11)
            if config["hard"] is not None:
                place_reference_legend_outside(fig, axis)
            inventory.save(fig, stem, f"{metric}_HISTOGRAM", scope, source)

        for metric in ("SNR", "SNDR", "ENOB", "SFDR"):
            config = METRICS[metric]
            ordered = sorted(
                (
                    {
                        "scope": scope,
                        "metric": metric,
                        "unit": config["label"].split("[", 1)[1].rstrip("]"),
                        "mismatch_seed": int(row["mismatch_seed"]),
                        "value": float(row[config["field"]]),
                    }
                    for row in valid
                ),
                key=lambda row: (row["value"], row["mismatch_seed"]),
            )
            for index, row in enumerate(ordered, start=1):
                row["empirical_cdf"] = index / len(ordered)
            stem = f"{scope.lower()}_{metric.lower()}_ecdf"
            source = SOURCE_ROOT / f"{stem}.csv"
            write_csv(source, ordered)
            fig, axis = plt.subplots(figsize=(10.0, 5.2), facecolor="#eeeeee")
            style_axis(axis)
            axis.step(
                [row["value"] for row in ordered],
                [row["empirical_cdf"] for row in ordered],
                where="post",
                color="#0067b1",
                linewidth=1.5,
            )
            add_reference_lines(axis, metric, vertical=True)
            axis.set_ylim(0.0, 1.0)
            axis.set_xlabel(config["label"])
            axis.set_ylabel("Empirical CDF")
            axis.set_title(f"{scope} {metric} Empirical CDF", fontsize=11)
            if config["hard"] is not None:
                place_reference_legend_outside(fig, axis)
            inventory.save(fig, stem, f"{metric}_ECDF", scope, source)

        for metric in ("SNR", "SNDR"):
            config = METRICS[metric]
            ordered = sorted(
                (
                    {
                        "scope": scope,
                        "metric": metric,
                        "unit": config["label"].split("[", 1)[1].rstrip("]"),
                        "mismatch_seed": int(row["mismatch_seed"]),
                        "value": float(row[config["field"]]),
                    }
                    for row in valid
                ),
                key=lambda row: row["mismatch_seed"],
            )
            stem = f"{scope.lower()}_seed_by_seed_{metric.lower()}"
            source = SOURCE_ROOT / f"{stem}.csv"
            write_csv(source, ordered)
            fig, axis = plt.subplots(figsize=(10.2, 5.0), facecolor="#eeeeee")
            style_axis(axis)
            axis.plot(
                [row["mismatch_seed"] for row in ordered],
                [row["value"] for row in ordered],
                color="#0067b1",
                linewidth=0.9,
                marker="o",
                markersize=2.2,
            )
            add_reference_lines(axis, metric, vertical=False)
            axis.set_xlim(1, 200)
            axis.set_xlabel("Mismatch Seed")
            axis.set_ylabel(config["label"])
            axis.set_title(f"{scope} Seed-by-Seed {metric}", fontsize=11)
            place_reference_legend_outside(fig, axis)
            inventory.save(fig, stem, f"SEED_BY_SEED_{metric}", scope, source)

        for label, field in (
            ("hard_dynamic", "hard_dynamic_pass"),
            ("snr_budget", "snr_budget_pass"),
        ):
            ordered = sorted(
                (
                    {
                        "scope": scope,
                        "criterion": label.upper(),
                        "mismatch_seed": int(row["mismatch_seed"]),
                        "pass": as_bool(row[field]),
                        "state": row["state"],
                    }
                    for row in rows
                ),
                key=lambda row: row["mismatch_seed"],
            )
            stem = f"{scope.lower()}_{label}_pass_fail_map"
            source = SOURCE_ROOT / f"{stem}.csv"
            write_csv(source, ordered)
            fig, axis = plt.subplots(figsize=(9.0, 3.8), facecolor="#eeeeee")
            style_axis(axis)
            axis.scatter(
                [row["mismatch_seed"] for row in ordered],
                [1 if row["pass"] else 0 for row in ordered],
                c=["#009e73" if row["pass"] else "#d55e00" for row in ordered],
                s=18,
                marker="s",
            )
            axis.set_xlim(1, 200)
            axis.set_ylim(-0.25, 1.25)
            axis.set_yticks([0, 1], labels=["FAIL", "PASS"])
            axis.set_xlabel("Mismatch Seed")
            axis.set_title(
                f"{scope} {label.replace('_', ' ').title()} Pass/Fail Map",
                fontsize=11,
            )
            inventory.save(fig, stem, f"{label.upper()}_PASS_FAIL_MAP", scope, source)


def representative_spectra(master, codes, representatives, inventory):
    master_by_key = {(int(row["mismatch_seed"]), row["band"]): row for row in master}
    code_by_key = {}
    for row in codes:
        code_by_key.setdefault((int(row["mismatch_seed"]), row["band"]), []).append(row)
    for representative in representatives:
        key = (int(representative["mismatch_seed"]), representative["band"])
        metadata = master_by_key[key]
        stream = [
            int(row["code"])
            for row in sorted(code_by_key[key], key=lambda row: int(row["frame_index"]))
        ]
        raw_source = spectrum_rows(stream, int(metadata["bin"]))
        source_rows = [
            {
                "bin": row["bin"],
                "mismatch_seed": key[0],
                "band": key[1],
                "scope": key[1],
                "frequency_mhz": row["freq_hz"] / 1e6,
                "frequency_unit": "MHz",
                "amplitude_dbfs_per_bin": row["magnitude_db"],
                "amplitude_unit": "dBFS/bin",
                "display_amplitude_dbfs_per_bin": row["magnitude_db"],
                "display_clipped": False,
                "is_fundamental": row["is_fundamental"],
                "is_hd2": row["is_hd2"],
                "is_hd3": row["is_hd3"],
                "is_largest_spur": row["is_largest_spur"],
            }
            for row in raw_source
        ]
        stem = f"spectrum_{key[1].lower()}_s{key[0]:03d}"
        source = SOURCE_ROOT / f"{stem}.csv"
        write_csv(source, source_rows)
        minimum = min(row["amplitude_dbfs_per_bin"] for row in source_rows)
        lower = min(-100.0, math.floor(minimum / 10.0) * 10.0)
        fig, axis = plt.subplots(figsize=(12.0, 6.2), facecolor="#eeeeee")
        fig.subplots_adjust(right=0.68)
        style_axis(axis)
        x = [row["frequency_mhz"] for row in source_rows]
        y = [row["amplitude_dbfs_per_bin"] for row in source_rows]
        axis.vlines(x, lower, y, color="#0067b1", linewidth=0.9)
        axis.scatter(x, y, color="#0067b1", s=14, marker="o", zorder=3)
        labels = {
            "is_fundamental": ("Fundamental", (0, -18)),
            "is_hd2": ("HD2", (4, 8)),
            "is_hd3": ("HD3", (4, 8)),
            "is_largest_spur": ("Largest spur", (4, -14)),
        }
        for flag, (label, offset) in labels.items():
            for row in source_rows:
                if row[flag]:
                    annotation = axis.annotate(
                        label,
                        (
                            row["frequency_mhz"],
                            row["amplitude_dbfs_per_bin"],
                        ),
                        xytext=offset,
                        textcoords="offset points",
                        fontsize=8,
                    )
                    if flag == "is_fundamental":
                        annotation.set_ha("center")
        axis.set_xlim(0.0, 1.0)
        axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.set_ylim(lower, 0.0)
        axis.set_xlabel("Frequency [MHz]")
        axis.set_ylabel("Amplitude [dBFS/bin]")
        axis.set_title(
            f"FAST64 Spectrum - Seed {key[0]} {key[1]}", fontsize=11
        )
        info = (
            f"NFFT=64  Fs=2.000 MHz  fin={float(metadata['fin_hz'])/1e6:.6f} MHz\n"
            "Input=3.0 Vpp,diff (-1.09 dBFS)  Window=rectangular  RBW=31.25 kHz\n"
            "PVT=TT 3.3 V 27 C  Logic=timed behavioral SAR\n"
            f"Mismatch seed={key[0]}  Noise seed={metadata['noise_seed']}\n"
            "maxstep=50 ps  Solver=ROBUST_GEAR\n"
            f"SNR={float(metadata['snr_db']):.2f} dB  "
            f"SNDR={float(metadata['sndr_db']):.2f} dB  "
            f"ENOB={float(metadata['enob_raw']):.2f} bit\n"
            f"SFDR={float(metadata['sfdr_dbc']):.2f} dBc  "
            f"THD={float(metadata['thd_db']):.2f} dB\n"
            f"Roles={representative['roles']}"
        )
        fig.text(
            0.70,
            0.88,
            info,
            ha="left",
            va="top",
            fontsize=7.8,
            bbox={"facecolor": "white", "edgecolor": "black", "linewidth": 1.0},
        )
        inventory.save(
            fig,
            stem,
            "REPRESENTATIVE_SPECTRUM",
            key[1],
            source,
            representative["roles"],
        )


def make_contact_sheet(inventory):
    path = REPORT_ROOT / "plot_contact_sheet.pdf"
    with PdfPages(path) as pdf:
        for start in range(0, len(inventory.figures), 4):
            batch = inventory.figures[start : start + 4]
            fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.5), facecolor="white")
            for axis, item in zip(axes.flat, batch):
                image = plt.imread(ROOT / item["png"])
                axis.imshow(image)
                axis.set_title(item["figure_id"], fontsize=8)
                axis.axis("off")
            for axis in axes.flat[len(batch) :]:
                axis.axis("off")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    return path


def audit(inventory):
    checks = {}
    contract = json.loads(
        (ROOT / "config" / "plot_contract.json").read_text(encoding="utf-8")
    )
    resolved = json.loads(
        (ROOT / "config" / "plot_resolved_ranges.json").read_text(encoding="utf-8")
    )
    expected_units = {
        "SNR": "dB",
        "SNDR": "dB",
        "ENOB": "bit",
        "SFDR": "dBc",
    }
    checks["formal_script_hash_matches_frozen_contract"] = (
        sha256(Path(__file__).resolve()) == contract["formal_plot_script_sha256"]
    )
    checks["reference_thresholds_match_frozen_method"] = (
        contract["reference_thresholds"]
        == {
            "snr_hard_db": 48.14,
            "sndr_hard_db": 46.91,
            "sndr_preferred_db": 47.75,
            "enob_hard_bit": 7.5,
            "enob_preferred_bit": 7.64,
        }
        and METRICS["SNR"]["hard"] == 48.14
        and METRICS["SNDR"]["hard"] == 46.91
        and METRICS["SNDR"]["preferred"] == 47.75
        and METRICS["ENOB"]["hard"] == 7.50
        and METRICS["ENOB"]["preferred"] == 7.64
    )
    checks["resolved_edges_bound_into_plot_contract"] = (
        contract["resolved_histogram_edges"] == resolved["histogram_edges"]
        and contract["range_resolution_status"]
        == "RESOLVED_FROM_COMPLETE_POPULATION"
    )
    checks["artifact_manifest_has_three_entries_per_figure"] = (
        len(inventory.artifacts) == 3 * len(inventory.figures)
        and all(
            artifact["sha256"] == sha256(ROOT / artifact["relative_path"])
            for artifact in inventory.artifacts
        )
    )
    for item in inventory.figures:
        stem = item["figure_id"]
        png = ROOT / item["png"]
        pdf = ROOT / item["pdf"]
        source = ROOT / item["source_csv"]
        with Image.open(png) as image:
            dpi = image.info.get("dpi", (0.0, 0.0))
            checks[f"{stem}_png_300dpi"] = min(dpi) >= 299.0
            checks[f"{stem}_png_nonempty"] = image.width > 1000 and image.height > 600
        pdf_bytes = pdf.read_bytes()
        checks[f"{stem}_pdf_vector_container"] = (
            pdf.stat().st_size > 1000
            and pdf_bytes.startswith(b"%PDF")
            and b"/Type /Page" in pdf_bytes
            and b"%%EOF" in pdf_bytes[-1024:]
        )
        checks[f"{stem}_source_nonempty"] = source.stat().st_size > 50
        rows = read_csv(source)
        checks[f"{stem}_scope_binding"] = (
            bool(rows)
            and all(row.get("scope", item["scope"]) == item["scope"] for row in rows)
        )
        if item["plot_type"] == "REPRESENTATIVE_SPECTRUM":
            checks[f"{stem}_33_bins"] = len(rows) == 33
            checks[f"{stem}_frequency_axis_and_units"] = (
                [int(row["bin"]) for row in rows] == list(range(33))
                and all(int(row["mismatch_seed"]) == int(stem[-3:]) for row in rows)
                and all(row["band"] == item["scope"] for row in rows)
                and all(row["frequency_unit"] == "MHz" for row in rows)
                and all(row["amplitude_unit"] == "dBFS/bin" for row in rows)
                and all(
                    math.isclose(
                        float(row["frequency_mhz"]),
                        int(row["bin"]) / 32.0,
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                    for row in rows
                )
            )
            checks[f"{stem}_flags"] = (
                sum(as_bool(row["is_fundamental"]) for row in rows) == 1
                and sum(as_bool(row["is_hd2"]) for row in rows) == 1
                and sum(as_bool(row["is_hd3"]) for row in rows) == 1
                and sum(as_bool(row["is_largest_spur"]) for row in rows) == 1
            )
            checks[f"{stem}_no_display_clipping"] = all(
                row["display_clipped"].strip().lower() == "false"
                and math.isclose(
                    float(row["amplitude_dbfs_per_bin"]),
                    float(row["display_amplitude_dbfs_per_bin"]),
                    rel_tol=0.0,
                    abs_tol=0.0,
                )
                for row in rows
            )
        elif item["plot_type"].endswith("_HISTOGRAM"):
            metric = item["plot_type"].split("_", 1)[0]
            expected_edges = resolved["histogram_edges"][metric]
            observed_edges = [float(rows[0]["bin_left"])] + [
                float(row["bin_right"]) for row in rows
            ]
            checks[f"{stem}_histogram_population_and_edges"] = (
                sum(int(row["count"]) for row in rows) == 200
                and len(observed_edges) == len(expected_edges)
                and all(
                    math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
                    for actual, expected in zip(observed_edges, expected_edges)
                )
                and all(row["metric"] == metric for row in rows)
                and all(row["unit"] == expected_units[metric] for row in rows)
            )
        if item["plot_type"].endswith("_ECDF"):
            metric = item["plot_type"].split("_", 1)[0]
            values = [float(row["empirical_cdf"]) for row in rows]
            checks[f"{stem}_ecdf_monotonic"] = all(
                values[index] <= values[index + 1]
                for index in range(len(values) - 1)
            ) and math.isclose(values[-1], 1.0)
            checks[f"{stem}_ecdf_population_and_units"] = (
                len(rows) == 200
                and all(row["metric"] == metric for row in rows)
                and all(row["unit"] == expected_units[metric] for row in rows)
            )
        if item["plot_type"].startswith("SEED_BY_SEED_"):
            metric = item["plot_type"].removeprefix("SEED_BY_SEED_")
            checks[f"{stem}_seed_population_and_units"] = (
                [int(row["mismatch_seed"]) for row in rows] == list(range(1, 201))
                and all(row["metric"] == metric for row in rows)
                and all(row["unit"] == expected_units[metric] for row in rows)
            )
        if item["plot_type"].endswith("_PASS_FAIL_MAP"):
            checks[f"{stem}_map_population"] = (
                len(rows) == 200
                and [int(row["mismatch_seed"]) for row in rows]
                == list(range(1, 201))
                and len({row["criterion"] for row in rows}) == 1
            )
    type_counts = {}
    for item in inventory.figures:
        type_counts[item["plot_type"]] = type_counts.get(item["plot_type"], 0) + 1
    checks["three_scope_population_suite"] = all(
        type_counts.get(f"{metric}_{plot}", 0) == 3
        for metric, plot in (
            ("SNR", "HISTOGRAM"),
            ("SNDR", "HISTOGRAM"),
            ("ENOB", "HISTOGRAM"),
            ("SNR", "ECDF"),
            ("SNDR", "ECDF"),
            ("ENOB", "ECDF"),
            ("SFDR", "ECDF"),
        )
    )
    checks["three_scope_seed_and_maps"] = all(
        type_counts.get(name, 0) == 3
        for name in (
            "SEED_BY_SEED_SNR",
            "SEED_BY_SEED_SNDR",
            "HARD_DYNAMIC_PASS_FAIL_MAP",
            "SNR_BUDGET_PASS_FAIL_MAP",
        )
    )
    checks["representative_spectra_present"] = type_counts.get(
        "REPRESENTATIVE_SPECTRUM", 0
    ) >= 6
    result = {
        "status": "PASS_FORMAL_PLOT_AUDIT" if all(checks.values()) else "FAIL_FORMAL_PLOT_AUDIT",
        "pass": all(checks.values()),
        "checks": checks,
        "figure_count": len(inventory.figures),
        "artifact_count": len(inventory.artifacts),
        "plot_type_counts": type_counts,
        "visual_review_required": True,
    }
    (ROOT / "results" / "plot_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    statistics = json.loads(
        (ROOT / "results" / "statistics_status.json").read_text(encoding="utf-8")
    )
    if not statistics["statistics_complete"]:
        raise RuntimeError("statistics are incomplete")
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    master = read_csv(ROOT / "csv" / "dynamic_master.csv")
    codes = read_csv(ROOT / "csv" / "dynamic_codes.csv")
    combined = read_csv(ROOT / "csv" / "d3_combined_summary.csv")
    representatives = read_csv(
        ROOT / "csv" / "representative_spectra_manifest.csv"
    )
    scopes = build_scopes(master, combined)
    edges = resolved_edges(scopes)
    plot_contract_path = ROOT / "config" / "plot_contract.json"
    plot_contract = json.loads(plot_contract_path.read_text(encoding="utf-8"))
    plot_contract["status"] = "FROZEN_STYLE_WITH_POSTPOPULATION_RANGES_RESOLVED"
    plot_contract["range_resolution_status"] = "RESOLVED_FROM_COMPLETE_POPULATION"
    plot_contract["resolved_histogram_edges"] = edges
    plot_contract["range_resolution_master_sha256"] = sha256(
        ROOT / "csv" / "dynamic_master.csv"
    )
    plot_contract_path.write_text(
        json.dumps(plot_contract, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "config" / "plot_resolved_ranges.json").write_text(
        json.dumps(
            {
                "status": "RESOLVED_FROM_COMPLETE_POPULATION",
                "histogram_edges": edges,
                "rule": "SHARED_PER_METRIC_ACROSS_LOW_NEAR_WORST_BAND",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = Inventory()
    population_plots(scopes, edges, inventory)
    representative_spectra(master, codes, representatives, inventory)
    write_csv(ROOT / "plots" / "plot_inventory.csv", inventory.figures)
    write_csv(ROOT / "plots" / "plot_source_manifest.csv", inventory.artifacts)
    contact = make_contact_sheet(inventory)
    result = audit(inventory)
    result["contact_sheet"] = contact.relative_to(ROOT).as_posix()
    result["contact_sheet_sha256"] = sha256(contact)
    (ROOT / "results" / "plot_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
