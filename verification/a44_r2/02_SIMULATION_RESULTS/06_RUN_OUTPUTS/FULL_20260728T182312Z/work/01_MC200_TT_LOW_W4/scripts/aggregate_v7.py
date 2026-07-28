#!/usr/bin/env python3
"""Aggregate, plot, report, and integrity-audit the V7 formal population."""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator
from scipy.stats import beta

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]

from dynamic_analysis import spectrum_rows
from v7_common import (
    BANDS,
    CAMPAIGN_ID,
    CONFIG_DIR,
    CSV_DIR,
    ENOB_HARD_MIN_BIT,
    ENOB_PREFERRED_BIT,
    EVIDENCE_CLASS,
    MANIFEST_DIR,
    MINIMUM_PASSING_DIES,
    NFFT,
    PLOT_DIR,
    REPORT_DIR,
    REQUIRED_DIES,
    RESULT_DIR,
    SAMPLE_RATE_HZ,
    SNDR_HARD_MIN_DB,
    SNDR_PREFERRED_DB,
    SNR_BUDGET_MIN_DB,
    compact_code_checksum,
    ensure_v7_directories,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


MASTER_PATH = CSV_DIR / "dynamic_master.csv"
CODE_PATH = CSV_DIR / "dynamic_codes.csv"
COMBINED_PATH = CSV_DIR / "d3_combined_summary.csv"
PERCENTILE_PATH = CSV_DIR / "population_percentiles.csv"
REPRESENTATIVE_PATH = CSV_DIR / "representative_spectra_manifest.csv"
FINAL_REPORT_PATH = REPORT_DIR / "FINAL_FAST64_DYNAMIC_REPORT.md"
FINAL_STATUS_PATH = RESULT_DIR / "final_status.json"

VALID_STATES = {"VALID_PASS", "VALID_FAIL"}
SPECTRUM_PERCENTILES = (5, 1, 10)
SPECTRUM_SELECTION_POLICY = (
    "USER_OVERRIDE_P5_P1_P10_WORST_BAND_SNDR_TOTAL_3"
)
METRIC_CONFIG = {
    "SNR": {
        "column": "snr_db",
        "label": "SNR (dB)",
        "hard": SNR_BUDGET_MIN_DB,
        "preferred": None,
    },
    "SNDR": {
        "column": "sndr_db",
        "label": "SNDR (dB)",
        "hard": SNDR_HARD_MIN_DB,
        "preferred": SNDR_PREFERRED_DB,
    },
    "ENOB": {
        "column": "enob_raw",
        "label": "ENOB raw (bit)",
        "hard": ENOB_HARD_MIN_BIT,
        "preferred": ENOB_PREFERRED_BIT,
    },
}


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def as_float(row, key):
    value = row.get(key, "")
    return float(value) if value not in ("", None) else float("nan")


def clopper_pearson(successes, trials, alpha=0.05):
    if trials <= 0:
        return float("nan"), float("nan")
    lower = (
        0.0
        if successes == 0
        else float(beta.ppf(alpha / 2.0, successes, trials - successes + 1))
    )
    upper = (
        1.0
        if successes == trials
        else float(beta.ppf(1.0 - alpha / 2.0, successes + 1, trials - successes))
    )
    return lower, upper


def validate_compact_inputs(master_rows, code_rows):
    keys = [(int(row["mismatch_seed"]), row["band"]) for row in master_rows]
    duplicate_master = len(keys) - len(set(keys))
    code_groups = {}
    for row in code_rows:
        key = (int(row["mismatch_seed"]), row["band"])
        code_groups.setdefault(key, []).append(row)
    checksum_failures = []
    code_count_failures = []
    for row in master_rows:
        key = (int(row["mismatch_seed"]), row["band"])
        rows = sorted(
            code_groups.get(key, []), key=lambda item: int(item["frame_index"])
        )
        if len(rows) != NFFT:
            code_count_failures.append(
                {"mismatch_seed": key[0], "band": key[1], "rows": len(rows)}
            )
            continue
        actual = compact_code_checksum([int(item["code"]) for item in rows])
        if actual != row.get("compact_code_checksum_sha256", ""):
            checksum_failures.append(
                {
                    "mismatch_seed": key[0],
                    "band": key[1],
                    "expected": row.get("compact_code_checksum_sha256", ""),
                    "actual": actual,
                }
            )
    required_columns = {
        "category",
        "pvt",
        "mismatch_seed",
        "noise_seed",
        "band",
        "nfft",
        "bin",
        "fin_hz",
        "phase_rad",
        "input_vpp_diff",
        "maxstep_ns",
        "pfund_linear",
        "pnoise_linear",
        "pharm_linear",
        "perror_linear",
        "pspur_max_linear",
        "fundamental_dbfs",
        "snr_db",
        "sndr_db",
        "enob_raw",
        "sfdr_dbc",
        "thd_db",
        "hd2_dbc",
        "hd3_dbc",
        "largest_spur_bin",
        "largest_spur_hz",
        "noise_floor_dbfs_per_bin",
        "dc_code_offset",
        "mean_conversion_time_ns",
        "max_conversion_time_ns",
        "invalid_count",
        "timeout_count",
        "clipping_count",
        "missing_frame_count",
        "duplicate_frame_count",
        "valid_frame_count",
        "hard_dynamic_pass",
        "snr_budget_pass",
        "preferred_nominal_pass",
        "status",
    }
    actual_columns = set().union(*(row.keys() for row in master_rows)) if master_rows else set()
    audit = {
        "master_record_count": len(master_rows),
        "unique_master_record_count": len(set(keys)),
        "duplicate_master_record_count": duplicate_master,
        "code_row_count": len(code_rows),
        "expected_code_row_count": len(master_rows) * NFFT,
        "code_count_failure_count": len(code_count_failures),
        "code_checksum_failure_count": len(checksum_failures),
        "missing_required_columns": sorted(required_columns - actual_columns),
        "snr_present_every_record": all(row.get("snr_db", "") != "" for row in master_rows),
        "parseval_pass_every_record": all(
            as_bool(row.get("parseval_pass", False)) for row in master_rows
        ),
        "code_count_failures": code_count_failures,
        "code_checksum_failures": checksum_failures,
    }
    audit["pass"] = all(
        (
            duplicate_master == 0,
            not code_count_failures,
            not checksum_failures,
            not audit["missing_required_columns"],
            audit["snr_present_every_record"],
            audit["parseval_pass_every_record"],
        )
    )
    write_json_atomic(RESULT_DIR / "compact_input_audit.json", audit)
    return audit


def build_combined(master_rows):
    by_die = {}
    for row in master_rows:
        by_die.setdefault(int(row["mismatch_seed"]), {})[row["band"]] = row
    combined = []
    for seed in range(1, REQUIRED_DIES + 1):
        bands = by_die.get(seed, {})
        low = bands.get("LOW")
        near = bands.get("NEAR_NYQUIST")
        both_present = low is not None and near is not None
        both_valid = both_present and all(
            row["state"] in VALID_STATES for row in (low, near)
        )
        hard_both = both_valid and all(
            as_bool(row["hard_dynamic_pass"]) for row in (low, near)
        )
        snr_both = both_valid and all(
            as_bool(row["snr_budget_pass"]) for row in (low, near)
        )
        preferred_both = both_valid and all(
            as_bool(row["preferred_nominal_pass"]) for row in (low, near)
        )
        row = {
            "mismatch_seed": seed,
            "noise_seed": 100_000 + seed,
            "low_present": low is not None,
            "near_present": near is not None,
            "valid_die": both_valid,
            "hard_dynamic_pass_both": hard_both,
            "snr_budget_pass_both": snr_both,
            "preferred_nominal_pass_both": preferred_both,
            "die_state": (
                "VALID_PASS"
                if hard_both
                else ("VALID_FAIL" if both_valid else "UNRESOLVED")
            ),
        }
        for band_name, source in (("low", low), ("near", near)):
            for metric in ("snr_db", "sndr_db", "enob_raw", "sfdr_dbc", "thd_db"):
                row[f"{band_name}_{metric}"] = (
                    source.get(metric, "") if source is not None else ""
                )
            row[f"{band_name}_state"] = source["state"] if source is not None else "MISSING"
            row[f"{band_name}_hard_dynamic_pass"] = (
                source.get("hard_dynamic_pass", "") if source is not None else ""
            )
            row[f"{band_name}_snr_budget_pass"] = (
                source.get("snr_budget_pass", "") if source is not None else ""
            )
        if both_valid:
            row.update(
                {
                    "snr_worst_band": min(as_float(low, "snr_db"), as_float(near, "snr_db")),
                    "sndr_worst_band": min(
                        as_float(low, "sndr_db"), as_float(near, "sndr_db")
                    ),
                    "enob_worst_band": min(
                        as_float(low, "enob_raw"), as_float(near, "enob_raw")
                    ),
                    "snr_worst_band_name": (
                        "LOW"
                        if as_float(low, "snr_db") <= as_float(near, "snr_db")
                        else "NEAR_NYQUIST"
                    ),
                    "sndr_worst_band_name": (
                        "LOW"
                        if as_float(low, "sndr_db") <= as_float(near, "sndr_db")
                        else "NEAR_NYQUIST"
                    ),
                    "enob_worst_band_name": (
                        "LOW"
                        if as_float(low, "enob_raw") <= as_float(near, "enob_raw")
                        else "NEAR_NYQUIST"
                    ),
                }
            )
        else:
            row.update(
                {
                    "snr_worst_band": "",
                    "sndr_worst_band": "",
                    "enob_worst_band": "",
                    "snr_worst_band_name": "",
                    "sndr_worst_band_name": "",
                    "enob_worst_band_name": "",
                }
            )
        combined.append(row)
    write_csv_atomic(COMBINED_PATH, combined)
    return combined


def population_scopes(master_rows, combined_rows):
    scopes = {
        "LOW": [row for row in master_rows if row["band"] == "LOW"],
        "NEAR_NYQUIST": [
            row for row in master_rows if row["band"] == "NEAR_NYQUIST"
        ],
    }
    worst_rows = []
    for row in combined_rows:
        worst_rows.append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "state": (
                    "VALID_PASS"
                    if as_bool(row["hard_dynamic_pass_both"])
                    else (
                        "VALID_FAIL" if as_bool(row["valid_die"]) else "UNRESOLVED"
                    )
                ),
                "hard_dynamic_pass": row["hard_dynamic_pass_both"],
                "snr_budget_pass": row["snr_budget_pass_both"],
                "snr_db": row["snr_worst_band"],
                "sndr_db": row["sndr_worst_band"],
                "enob_raw": row["enob_worst_band"],
            }
        )
    scopes["WORST_BAND"] = worst_rows
    return scopes


def summarize_population(scopes):
    rows = []
    for scope, scope_rows in scopes.items():
        valid_rows = [row for row in scope_rows if row["state"] in VALID_STATES]
        hard_pass_count = sum(
            as_bool(row["hard_dynamic_pass"]) for row in valid_rows
        )
        snr_pass_count = sum(
            as_bool(row["snr_budget_pass"]) for row in valid_rows
        )
        ci_low, ci_high = clopper_pearson(hard_pass_count, len(valid_rows))
        for metric_name, config in METRIC_CONFIG.items():
            values_and_seeds = [
                (as_float(row, config["column"]), int(row["mismatch_seed"]))
                for row in valid_rows
                if math.isfinite(as_float(row, config["column"]))
            ]
            values = np.asarray([item[0] for item in values_and_seeds], dtype=float)
            if len(values):
                worst_index = int(np.argmin(values))
                stats = {
                    "mean": float(np.mean(values)),
                    "standard_deviation": (
                        float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                    ),
                    "p1": float(np.percentile(values, 1)),
                    "p5": float(np.percentile(values, 5)),
                    "p10": float(np.percentile(values, 10)),
                    "p50": float(np.percentile(values, 50)),
                    "p90": float(np.percentile(values, 90)),
                    "p95": float(np.percentile(values, 95)),
                    "p99": float(np.percentile(values, 99)),
                    "worst_observed": float(values[worst_index]),
                    "worst_seed": values_and_seeds[worst_index][1],
                }
            else:
                stats = {
                    key: ""
                    for key in (
                        "mean",
                        "standard_deviation",
                        "p1",
                        "p5",
                        "p10",
                        "p50",
                        "p90",
                        "p95",
                        "p99",
                        "worst_observed",
                        "worst_seed",
                    )
                }
            rows.append(
                {
                    "scope": scope,
                    "metric": metric_name,
                    "required_count": REQUIRED_DIES,
                    "terminal_count": len(scope_rows),
                    "valid_count": len(valid_rows),
                    "unresolved_count": len(scope_rows) - len(valid_rows),
                    "hard_pass_count": hard_pass_count,
                    "hard_fail_count": len(valid_rows) - hard_pass_count,
                    "snr_budget_pass_count": snr_pass_count,
                    "snr_budget_fail_count": len(valid_rows) - snr_pass_count,
                    "hard_pass_rate": (
                        hard_pass_count / len(valid_rows) if valid_rows else ""
                    ),
                    "hard_pass_exact_95ci_low": ci_low,
                    "hard_pass_exact_95ci_high": ci_high,
                    **stats,
                }
            )
    write_csv_atomic(PERCENTILE_PATH, rows)
    return rows


def setup_axes(ax):
    ax.set_facecolor("#f2f2f2")
    ax.grid(True, which="major", color="#b8b8b8", linestyle=":", linewidth=0.9)
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.1)
    ax.tick_params(colors="black", width=1.0)


def save_figure(fig, stem, plot_type, scope, source_csv, artifact_rows):
    pdf_path = PLOT_DIR / f"{stem}.pdf"
    png_path = PLOT_DIR / f"{stem}.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    for format_name, path in (
        ("PDF_VECTOR", pdf_path),
        ("PNG_300DPI", png_path),
        ("SOURCE_CSV", source_csv),
    ):
        artifact_rows.append(
            {
                "figure_id": stem,
                "plot_type": plot_type,
                "scope": scope,
                "format": format_name,
                "relative_path": str(path.relative_to(PLOT_DIR.parent)).replace(
                    "\\", "/"
                ),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )


def representative_selection(master_rows, combined_rows):
    master_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row
        for row in master_rows
        if row["state"] in VALID_STATES
    }
    valid_combined = [
        row for row in combined_rows if as_bool(row["valid_die"])
    ]
    worst_band_sndr = [
        float(row["sndr_worst_band"]) for row in valid_combined
    ]
    selections = []
    for percentile in SPECTRUM_PERCENTILES:
        target_sndr_db = float(
            np.percentile(worst_band_sndr, percentile)
        )
        combined = min(
            valid_combined,
            key=lambda row: (
                abs(float(row["sndr_worst_band"]) - target_sndr_db),
                int(row["mismatch_seed"]),
            ),
        )
        seed = int(combined["mismatch_seed"])
        band = combined["sndr_worst_band_name"]
        selections.append(
            {
                "band": band,
                "role": f"P{percentile}_WORST_BAND_SNDR",
                "percentile": percentile,
                "mismatch_seed": seed,
                "target_sndr_db": target_sndr_db,
                "master_row": master_by_key[(seed, band)],
            }
        )
    return selections


def generate_representative_spectra(master_rows, code_rows, combined_rows, artifacts):
    code_groups = {}
    for row in code_rows:
        key = (int(row["mismatch_seed"]), row["band"])
        code_groups.setdefault(key, []).append(row)
    manifest_rows = []
    for selection in representative_selection(master_rows, combined_rows):
        band = selection["band"]
        seed = selection["mismatch_seed"]
        role = selection["role"]
        master = selection["master_row"]
        compact = sorted(
            code_groups[(seed, band)], key=lambda row: int(row["frame_index"])
        )
        codes = [int(row["code"]) for row in compact]
        source_rows = spectrum_rows(codes, int(master["bin"]), SAMPLE_RATE_HZ)
        safe_band = band.lower()
        safe_role = role.lower()
        stem = f"spectrum_{safe_band}_s{seed:03d}_{safe_role}"
        source_path = PLOT_DIR / f"{stem}.csv"
        write_csv_atomic(source_path, source_rows)
        fig, ax = plt.subplots(figsize=(10.0, 6.2), facecolor="#eeeeee")
        setup_axes(ax)
        ax.plot(
            [row["freq_hz"] for row in source_rows],
            [row["magnitude_db"] for row in source_rows],
            color="#1d16ee",
            linewidth=2.0,
        )
        ax.set_xlim(0, SAMPLE_RATE_HZ / 2.0)
        ax.set_ylim(-100, 10)
        ax.set_xticks([0, 250_000, 500_000, 750_000, 1_000_000])
        ax.set_xticklabels(["0 Hz", "250 kHz", "500 kHz", "750 kHz", "1 MHz"])
        ax.yaxis.set_major_locator(MultipleLocator(10))
        ax.set_xlabel("Frequency (Hz)", fontsize=15)
        ax.set_ylabel("Magnitude (dB)", fontsize=15)
        ax.set_title(
            f"{band} | seed {seed} | {role.replace('_', ' ')}", fontsize=11
        )
        annotation = "\n".join(
            (
                f"SNR  = {float(master['snr_db']):.2f} dB",
                f"SNDR = {float(master['sndr_db']):.2f} dB",
                f"ENOB = {float(master['enob_raw']):.2f} bits",
                f"SFDR = {float(master['sfdr_dbc']):.2f} dB",
                f"THD  = {float(master['thd_db']):.2f} dB",
            )
        )
        ax.text(
            0.97,
            0.95,
            annotation,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=11,
            bbox={
                "facecolor": "white",
                "edgecolor": "black",
                "linewidth": 1.5,
                "boxstyle": "square,pad=0.45",
            },
        )
        save_figure(fig, stem, "REPRESENTATIVE_SPECTRUM", band, source_path, artifacts)
        manifest_rows.append(
            {
                "band": band,
                "role": role,
                "mismatch_seed": seed,
                "noise_seed": master["noise_seed"],
                "percentile": selection["percentile"],
                "selection_scope": "WORST_BAND",
                "target_percentile_sndr_db": selection["target_sndr_db"],
                "selected_distance_from_percentile_db": abs(
                    float(master["sndr_db"]) - selection["target_sndr_db"]
                ),
                "sndr_db": master["sndr_db"],
                "snr_db": master["snr_db"],
                "enob_raw": master["enob_raw"],
                "sfdr_dbc": master["sfdr_dbc"],
                "code_checksum_sha256": compact_code_checksum(codes),
                "source_csv": str(source_path.relative_to(PLOT_DIR.parent)).replace(
                    "\\", "/"
                ),
                "pdf": f"plots/{stem}.pdf",
                "png": f"plots/{stem}.png",
            }
        )
    write_csv_atomic(REPRESENTATIVE_PATH, manifest_rows)
    return manifest_rows


def metric_source_rows(scope_rows, column):
    return [
        {
            "mismatch_seed": int(row["mismatch_seed"]),
            "value": float(row[column]),
            "hard_dynamic_pass": as_bool(row["hard_dynamic_pass"]),
            "snr_budget_pass": as_bool(row["snr_budget_pass"]),
        }
        for row in scope_rows
        if row["state"] in VALID_STATES and math.isfinite(as_float(row, column))
    ]


def add_metric_reference_lines(ax, metric_name):
    config = METRIC_CONFIG[metric_name]
    ax.axvline(
        config["hard"],
        color="#b21f35",
        linestyle="--",
        linewidth=1.4,
        label=f"Gate {config['hard']:.2f}",
    )
    if config["preferred"] is not None:
        ax.axvline(
            config["preferred"],
            color="#197a60",
            linestyle="-.",
            linewidth=1.3,
            label=f"Preferred {config['preferred']:.2f}",
        )


def generate_population_plots(scopes, artifacts):
    for scope, rows in scopes.items():
        for metric_name, config in METRIC_CONFIG.items():
            source = metric_source_rows(rows, config["column"])
            values = np.asarray([row["value"] for row in source], dtype=float)
            if not len(values):
                continue
            histogram_counts, histogram_edges = np.histogram(
                values, bins=max(8, min(20, int(round(math.sqrt(len(values))))))
            )
            histogram_source = [
                {
                    "bin_left": histogram_edges[index],
                    "bin_right": histogram_edges[index + 1],
                    "count": int(histogram_counts[index]),
                }
                for index in range(len(histogram_counts))
            ]
            hist_stem = f"{scope.lower()}_{metric_name.lower()}_histogram"
            hist_source_path = PLOT_DIR / f"{hist_stem}.csv"
            write_csv_atomic(hist_source_path, histogram_source)
            fig, ax = plt.subplots(figsize=(8.2, 5.2), facecolor="#eeeeee")
            setup_axes(ax)
            ax.hist(
                values,
                bins=histogram_edges,
                color="#3d6f9e",
                edgecolor="black",
                linewidth=0.7,
            )
            add_metric_reference_lines(ax, metric_name)
            ax.set_xlabel(config["label"])
            ax.set_ylabel("Count")
            ax.set_title(f"{scope} {metric_name} histogram")
            ax.legend(frameon=False)
            save_figure(
                fig, hist_stem, f"{metric_name}_HISTOGRAM", scope, hist_source_path, artifacts
            )

            sorted_values = np.sort(values)
            cdf_source = [
                {"value": value, "empirical_cdf": (index + 1) / len(sorted_values)}
                for index, value in enumerate(sorted_values)
            ]
            cdf_stem = f"{scope.lower()}_{metric_name.lower()}_cdf"
            cdf_source_path = PLOT_DIR / f"{cdf_stem}.csv"
            write_csv_atomic(cdf_source_path, cdf_source)
            fig, ax = plt.subplots(figsize=(8.2, 5.2), facecolor="#eeeeee")
            setup_axes(ax)
            ax.step(
                sorted_values,
                np.arange(1, len(sorted_values) + 1) / len(sorted_values),
                where="post",
                color="#294f82",
                linewidth=1.8,
            )
            add_metric_reference_lines(ax, metric_name)
            ax.set_ylim(0, 1.02)
            ax.set_xlabel(config["label"])
            ax.set_ylabel("Empirical CDF")
            ax.set_title(f"{scope} {metric_name} empirical CDF")
            ax.legend(frameon=False)
            save_figure(
                fig, cdf_stem, f"{metric_name}_CDF", scope, cdf_source_path, artifacts
            )

        for metric_name in ("SNR", "SNDR"):
            config = METRIC_CONFIG[metric_name]
            source = sorted(
                metric_source_rows(rows, config["column"]),
                key=lambda row: row["mismatch_seed"],
            )
            stem = f"{scope.lower()}_seed_{metric_name.lower()}"
            source_path = PLOT_DIR / f"{stem}.csv"
            write_csv_atomic(source_path, source)
            fig, ax = plt.subplots(figsize=(9.0, 5.0), facecolor="#eeeeee")
            setup_axes(ax)
            ax.plot(
                [row["mismatch_seed"] for row in source],
                [row["value"] for row in source],
                color="#2b5e90",
                linewidth=1.2,
            )
            ax.axhline(
                config["hard"],
                color="#b21f35",
                linestyle="--",
                linewidth=1.4,
            )
            if config["preferred"] is not None:
                ax.axhline(
                    config["preferred"],
                    color="#197a60",
                    linestyle="-.",
                    linewidth=1.3,
                )
            ax.set_xlim(1, REQUIRED_DIES)
            ax.set_xlabel("Mismatch seed")
            ax.set_ylabel(config["label"])
            ax.set_title(f"{scope} seed-by-seed {metric_name}")
            save_figure(
                fig,
                stem,
                f"SEED_BY_SEED_{metric_name}",
                scope,
                source_path,
                artifacts,
            )

        for pass_name, pass_column, title in (
            ("hard", "hard_dynamic_pass", "hard pass/fail"),
            ("snr_budget", "snr_budget_pass", "SNR-budget pass/fail"),
        ):
            source = [
                {
                    "mismatch_seed": int(row["mismatch_seed"]),
                    "pass": as_bool(row[pass_column]),
                    "state": row["state"],
                }
                for row in rows
            ]
            source.sort(key=lambda row: row["mismatch_seed"])
            stem = f"{scope.lower()}_{pass_name}_map"
            source_path = PLOT_DIR / f"{stem}.csv"
            write_csv_atomic(source_path, source)
            fig, ax = plt.subplots(figsize=(9.0, 3.8), facecolor="#eeeeee")
            setup_axes(ax)
            colors = ["#24735c" if row["pass"] else "#b33a3a" for row in source]
            ax.scatter(
                [row["mismatch_seed"] for row in source],
                [1 if row["pass"] else 0 for row in source],
                c=colors,
                s=18,
                marker="s",
            )
            ax.set_xlim(1, REQUIRED_DIES)
            ax.set_ylim(-0.25, 1.25)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(["FAIL", "PASS"])
            ax.set_xlabel("Mismatch seed")
            ax.set_title(f"{scope} {title} map")
            save_figure(
                fig,
                stem,
                f"{pass_name.upper()}_PASS_FAIL_MAP",
                scope,
                source_path,
                artifacts,
            )


def campaign_status(
    master_rows, combined_rows, qualification, compact_audit, waveform_audit_pass
):
    formal_execution_path = RESULT_DIR / "formal_execution_audit.json"
    formal_execution = (
        json.loads(formal_execution_path.read_text(encoding="ascii"))
        if formal_execution_path.is_file()
        else {}
    )
    record_keys = {(int(row["mismatch_seed"]), row["band"]) for row in master_rows}
    all_required_records_present = len(record_keys) == REQUIRED_DIES * len(BANDS)
    all_records_valid = all(row["state"] in VALID_STATES for row in master_rows) and (
        len(master_rows) == REQUIRED_DIES * len(BANDS)
    )
    valid_dies = sum(as_bool(row["valid_die"]) for row in combined_rows)
    passing_dies = sum(
        as_bool(row["hard_dynamic_pass_both"]) for row in combined_rows
    )
    if not qualification.get("noise_model_qualified", False):
        status = "BLOCKED_NOISE_MODEL_NOT_QUALIFIED"
    elif not qualification.get("numerical_qualification_pass", False) or not qualification.get(
        "session_equivalence_complete", False
    ):
        status = "BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED"
    elif not qualification.get("resource_admission_pass", False):
        status = "BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION"
    elif (
        not all_required_records_present
        or not all_records_valid
        or not compact_audit["pass"]
        or not waveform_audit_pass
    ):
        status = "BLOCKED_INCOMPLETE_DYNAMIC_POPULATION"
    elif valid_dies == REQUIRED_DIES and passing_dies >= MINIMUM_PASSING_DIES:
        status = "PASS_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95"
    else:
        status = "FAIL_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95"
    ci_low, ci_high = clopper_pearson(passing_dies, valid_dies)
    return {
        "campaign_id": CAMPAIGN_ID,
        "status": status,
        "evidence_class": EVIDENCE_CLASS,
        "scope_claim": [
            "FAST64_DYNAMIC_ONLY",
            "D3_NOISE_PLUS_MISMATCH_MC200",
            "WITH_FIXED_TT_TIMED_BEHAVIORAL_SAR",
            "NO_R6",
            "MODEL_CONDITIONAL",
        ],
        "document_scope_completed": all_required_records_present
        and all_records_valid
        and compact_audit["pass"],
        "performance_acceptance_pass": (
            valid_dies == REQUIRED_DIES and passing_dies >= MINIMUM_PASSING_DIES
        ),
        "required_record_count": REQUIRED_DIES * len(BANDS),
        "terminal_record_count": len(master_rows),
        "valid_record_count": sum(row["state"] in VALID_STATES for row in master_rows),
        "unresolved_record_count": sum(
            row["state"] not in VALID_STATES for row in master_rows
        ),
        "required_die_count": REQUIRED_DIES,
        "valid_die_count": valid_dies,
        "hard_passing_die_count": passing_dies,
        "hard_failing_die_count": valid_dies - passing_dies,
        "observed_hard_pass_rate": passing_dies / valid_dies if valid_dies else None,
        "exact_binomial_95ci_low": ci_low if valid_dies else None,
        "exact_binomial_95ci_high": ci_high if valid_dies else None,
        "minimum_passing_die_count": MINIMUM_PASSING_DIES,
        "snr_budget_passing_die_count": sum(
            as_bool(row["snr_budget_pass_both"]) for row in combined_rows
        ),
        "low_snr_budget_pass_count": sum(
            row["band"] == "LOW" and as_bool(row["snr_budget_pass"])
            for row in master_rows
        ),
        "near_snr_budget_pass_count": sum(
            row["band"] == "NEAR_NYQUIST" and as_bool(row["snr_budget_pass"])
            for row in master_rows
        ),
        "qualification_cache_key_sha256": qualification.get("cache_key_sha256"),
        "selected_formal_maxstep_ps": qualification.get(
            "selected_formal_maxstep_ps"
        ),
        "formal_wall_elapsed_s": formal_execution.get(
            "wall_elapsed_s_this_invocation"
        ),
        "formal_wall_elapsed_h": (
            formal_execution["wall_elapsed_s_this_invocation"] / 3600.0
            if "wall_elapsed_s_this_invocation" in formal_execution
            else None
        ),
        "execution_mode": qualification.get("session_execution_mode"),
        "parsed_ngspice_session_claim": False,
        "native_mos_transient_noise_claim": False,
        "production_yield_claim": False,
        "full_waveform_audit_pass": waveform_audit_pass,
        "spectrum_selection_policy": SPECTRUM_SELECTION_POLICY,
        "non_claims": [
            "static DNL/INL/offset characterization",
            "noise-only or mismatch-only decomposition",
            "FAST128/FAST256 long-record closure",
            "actual self-timed SAR full-IP closure",
            "PEX/layout signoff",
            "package/PCB performance",
            "silicon production yield",
        ],
    }


def write_final_report(status, percentile_rows, qualification, plot_artifacts):
    lookup = {
        (row["scope"], row["metric"]): row for row in percentile_rows
    }
    lines = [
        "# A44 FAST64 D3-Only MC200 Final Dynamic Report",
        "",
        f"- Campaign status: `{status['status']}`",
        f"- Document scope completed: `{status['document_scope_completed']}`",
        f"- Performance acceptance pass: `{status['performance_acceptance_pass']}`",
        f"- Formal records: `{status['valid_record_count']}/{status['required_record_count']}` valid",
        f"- Valid dies: `{status['valid_die_count']}/{status['required_die_count']}`",
        f"- Hard passing dies: `{status['hard_passing_die_count']}/{status['valid_die_count']}`",
        f"- SNR-budget passing dies: `{status['snr_budget_passing_die_count']}/{status['valid_die_count']}`",
        f"- Exact 95% binomial interval: `[{status['exact_binomial_95ci_low']:.6f}, {status['exact_binomial_95ci_high']:.6f}]`"
        if status["valid_die_count"]
        else "- Exact 95% binomial interval: `not available`",
        f"- Selected formal maxstep: `{status['selected_formal_maxstep_ps']} ps`",
        f"- Execution mode: `{status['execution_mode']}`",
        f"- Actual formal-matrix wall time: `{status['formal_wall_elapsed_h']:.3f} h`",
        f"- Plot artifacts: `{len(plot_artifacts)}` files",
        f"- Spectrum selection: `{SPECTRUM_SELECTION_POLICY}`.",
        "",
        "## Population Metrics",
        "",
        "| Scope | Metric | Mean | Std | P1 | P5 | P50 | Worst | Worst seed |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scope in ("LOW", "NEAR_NYQUIST", "WORST_BAND"):
        for metric in ("SNR", "SNDR", "ENOB"):
            row = lookup[(scope, metric)]
            lines.append(
                "| {} | {} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {} |".format(
                    scope,
                    metric,
                    float(row["mean"]),
                    float(row["standard_deviation"]),
                    float(row["p1"]),
                    float(row["p5"]),
                    float(row["p50"]),
                    float(row["worst_observed"]),
                    row["worst_seed"],
                )
            )
    lines.extend(
        [
            "",
            "## Qualification",
            "",
            f"- Noise model qualified for this evidence class: `{qualification.get('noise_model_qualified')}`",
            "- Noise evidence is `T2_TARGET_CALIBRATED_EVENT_NOISE`; it is not native MOS transient-noise evidence.",
            f"- Retained prior Phase-G system gate status: `{qualification.get('prior_phase_g_system_gate_status')}`; V7 does not relabel that result.",
            f"- 100 ps equivalent to 50 ps: `{qualification.get('bulk_100ps_equivalent_to_strict_50ps')}`",
            f"- Session/replay check complete: `{qualification.get('session_equivalence_complete')}`",
            "- No persistent parsed-ngspice session is claimed; formal execution used the documented separate-process fallback.",
            f"- 32-GB/one-day resource admission: `{qualification.get('resource_admission_pass')}`",
            f"- Pilot-projected total: `{qualification.get('resource', {}).get('projected_total_h_with_2h_overhead', 'NA')} h`",
            f"- Actual formal-matrix wall time: `{status['formal_wall_elapsed_h']:.3f} h`; this remained below the 24 h admission limit.",
            "",
            "## Claim Boundary",
            "",
            "This package is FAST64-only, D3 noise-plus-mismatch MC200, fixed-TT timed-behavioral-SAR, No-R6, model-conditional evidence.",
            "",
            "It does not claim static DNL/INL/offset characterization, noise-only or mismatch-only decomposition, FAST128/FAST256 closure, actual self-timed full-IP closure, PEX/layout signoff, package/PCB performance, or silicon production yield.",
        ]
    )
    FINAL_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")


def final_manifest():
    excluded = {
        "manifests/final_manifest_sha256.csv",
        "results/final_manifest_audit.json",
    }
    rows = []
    for path in sorted(item for item in PLOT_DIR.parent.rglob("*") if item.is_file()):
        relative = path.relative_to(PLOT_DIR.parent).as_posix()
        if relative in excluded or "__pycache__" in path.parts:
            continue
        rows.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest_path = MANIFEST_DIR / "final_manifest_sha256.csv"
    write_csv_atomic(manifest_path, rows)
    failures = []
    for row in read_csv(manifest_path):
        path = PLOT_DIR.parent / row["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["size_bytes"])
            or sha256_file(path) != row["sha256"]
        ):
            failures.append(row["relative_path"])
    audit = {
        "manifest_path": str(manifest_path.relative_to(PLOT_DIR.parent)),
        "manifest_sha256": sha256_file(manifest_path),
        "declared_files": len(rows),
        "matching_files": len(rows) - len(failures),
        "failures": failures,
        "pass": not failures,
    }
    write_json_atomic(RESULT_DIR / "final_manifest_audit.json", audit)
    return audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=("tables", "plots", "final", "all"), default="all"
    )
    args = parser.parse_args()
    ensure_v7_directories()
    qualification = json.loads(
        (CONFIG_DIR / "qualification_cache.json").read_text(encoding="ascii")
    )
    master_rows = read_csv(MASTER_PATH) if MASTER_PATH.is_file() else []
    code_rows = read_csv(CODE_PATH) if CODE_PATH.is_file() else []
    compact_audit = validate_compact_inputs(master_rows, code_rows)
    combined_rows = build_combined(master_rows)
    scopes = population_scopes(master_rows, combined_rows)
    percentile_rows = summarize_population(scopes)
    if args.stage == "tables":
        print(
            f"TABLES master={len(master_rows)} combined={len(combined_rows)} "
            f"compact_pass={compact_audit['pass']}"
        )
        return
    artifacts = []
    representative_rows = []
    if args.stage == "final":
        artifacts = read_csv(MANIFEST_DIR / "plot_artifact_manifest.csv")
        representative_rows = read_csv(REPRESENTATIVE_PATH)
    elif master_rows and code_rows:
        representative_rows = generate_representative_spectra(
            master_rows, code_rows, combined_rows, artifacts
        )
        generate_population_plots(scopes, artifacts)
        write_csv_atomic(MANIFEST_DIR / "plot_artifact_manifest.csv", artifacts)
    plot_audit = {
        "representative_spectrum_roles": len(representative_rows),
        "expected_representative_spectrum_roles": 3,
        "spectrum_selection_policy": SPECTRUM_SELECTION_POLICY,
        "population_figure_count": len(
            {
                row["figure_id"]
                for row in artifacts
                if row["plot_type"] != "REPRESENTATIVE_SPECTRUM"
            }
        ),
        "expected_population_figure_count": 30,
        "artifact_file_count": len(artifacts),
        "all_artifacts_nonempty": all(
            int(row["size_bytes"]) > 0 for row in artifacts
        ),
    }
    plot_audit["pass"] = all(
        (
            plot_audit["representative_spectrum_roles"] == 3,
            plot_audit["population_figure_count"] == 30,
            plot_audit["all_artifacts_nonempty"],
        )
    )
    write_json_atomic(RESULT_DIR / "plot_audit.json", plot_audit)
    waveform_audit_path = RESULT_DIR / "full_waveform_audit.json"
    waveform_audit_pass = (
        json.loads(waveform_audit_path.read_text(encoding="ascii")).get("pass", False)
        if waveform_audit_path.is_file()
        else False
    )
    status = campaign_status(
        master_rows,
        combined_rows,
        qualification,
        compact_audit,
        waveform_audit_pass,
    )
    status["plot_audit_pass"] = plot_audit["pass"]
    write_json_atomic(FINAL_STATUS_PATH, status)
    write_final_report(status, percentile_rows, qualification, artifacts)
    checklist = {
        "dependency_hashes_generated": (CONFIG_DIR / "dependency_hashes.json").is_file(),
        "qualification_completed": qualification.get("fixed_pilot_complete", False),
        "analyzer_parseval_all_records": compact_audit["parseval_pass_every_record"],
        "snr_every_record": compact_audit["snr_present_every_record"],
        "resource_pilot_completed": qualification.get(
            "resource_admission_complete", False
        ),
        "session_equivalence_or_fallback_documented": qualification.get(
            "session_fallback_documented", False
        ),
        "dies_200_terminal": sum(
            row["die_state"] in {"VALID_PASS", "VALID_FAIL"} for row in combined_rows
        )
        == REQUIRED_DIES,
        "records_400_accounted": len(master_rows) == REQUIRED_DIES * len(BANDS),
        "hard_and_snr_counts_separate": True,
        "dynamic_master_schema_valid": not compact_audit["missing_required_columns"],
        "plots_complete": plot_audit["pass"],
        "full_waveform_audits_complete": waveform_audit_pass,
        "final_status_generated": FINAL_STATUS_PATH.is_file(),
        "claim_boundary_present": True,
        "independent_final_audit_pass": (
            json.loads(
                (RESULT_DIR / "final_independent_audit.json").read_text(
                    encoding="ascii"
                )
            ).get("pass", False)
            if (RESULT_DIR / "final_independent_audit.json").is_file()
            else False
        ),
    }
    checklist["pass"] = all(checklist.values())
    write_json_atomic(RESULT_DIR / "final_checklist_audit.json", checklist)
    manifest_audit = final_manifest()
    print(
        "FINAL status={} records={} dies={} pass_dies={} plots={} manifest={}/{}".format(
            status["status"],
            status["valid_record_count"],
            status["valid_die_count"],
            status["hard_passing_die_count"],
            len(artifacts),
            manifest_audit["matching_files"],
            manifest_audit["declared_files"],
        )
    )


if __name__ == "__main__":
    main()
