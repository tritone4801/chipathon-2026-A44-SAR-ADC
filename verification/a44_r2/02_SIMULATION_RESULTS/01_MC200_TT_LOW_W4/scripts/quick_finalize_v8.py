#!/usr/bin/env python3
"""Finalize selected-seed regression evidence without MC200 claims."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from dynamic_analysis import spectrum_rows
from v7_common import (
    BANDS,
    CSV_DIR,
    NFFT,
    PLOT_DIR,
    REPORT_DIR,
    RESULT_DIR,
    ROOT,
    SAMPLE_RATE_HZ,
    compact_code_checksum,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


CORE_SEEDS = (1, 21, 25, 44, 48, 64, 115, 129, 140, 166, 170, 183)
OPTIONAL_SEEDS = (13, 167)
SPECTRA = (
    ("P1_WORST_BAND_SNDR", 21, "LOW"),
    ("P5_WORST_BAND_SNDR", 129, "LOW"),
    ("P10_WORST_BAND_SNDR", 183, "NEAR_NYQUIST"),
)
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def write_report(status, comparisons, representatives):
    max_sndr = max(abs(float(row["delta_sndr_db"])) for row in comparisons)
    max_snr = max(abs(float(row["delta_snr_db"])) for row in comparisons)
    max_enob = max(abs(float(row["delta_enob_bit"])) for row in comparisons)
    lines = [
        "# A44 FAST64 D3 MC12+2 One-Hour Validation Report",
        "",
        f"- Status: `{status['status']}`",
        f"- Mandatory records: `{status['valid_core_records']}/24` valid",
        f"- Optional pair executed: `{status['optional_pair_executed']}`",
        f"- Optional records: `{status['valid_optional_records']}/4` valid",
        f"- Selected maxstep: `{status['selected_maxstep_ps']} ps`",
        f"- Execution mode: `{status['execution_mode']}`",
        f"- Maximum absolute SNDR delta: `{max_sndr:.6f} dB`",
        f"- Maximum absolute SNR delta: `{max_snr:.6f} dB`",
        f"- Maximum absolute ENOB delta: `{max_enob:.6f} bit`",
        f"- Compact code checksums equal: `{status['all_code_checksums_equal']}`",
        "",
        "## Representative Spectra",
        "",
        "| Role | Seed | Band | SNDR (dB) | PNG |",
        "|---|---:|---|---:|---|",
    ]
    for row in representatives:
        lines.append(
            "| {} | {} | {} | {:.6f} | `{}` |".format(
                row["role"],
                row["mismatch_seed"],
                row["band"],
                float(row["sndr_db"]),
                row["png"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a result-informed selected-seed quick regression.",
            "It is not an unbiased MC200 yield estimate, production-yield evidence,",
            "native-MOS transient-noise evidence, or dynamic signoff.",
            "",
        ]
    )
    (REPORT_DIR / "FINAL_MC12_PLUS2_ONE_HOUR_REPORT.md").write_text(
        "\n".join(lines), encoding="ascii"
    )


def save_spectrum(master, compact_rows, role):
    seed = int(master["mismatch_seed"])
    band = master["band"]
    codes = [int(row["code"]) for row in compact_rows]
    rows = spectrum_rows(codes, int(master["bin"]), SAMPLE_RATE_HZ)
    stem = f"spectrum_{band.lower()}_s{seed:03d}_{role.lower()}"
    csv_path = PLOT_DIR / f"{stem}.csv"
    write_csv_atomic(csv_path, rows)

    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
    fig, ax = plt.subplots(figsize=(10.0, 6.2), facecolor="#eeeeee")
    ax.set_facecolor("#eeeeee")
    ax.plot(
        [row["freq_hz"] for row in rows],
        [row["magnitude_db"] for row in rows],
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
    ax.grid(True, which="major", color="#b8b8b8", linestyle=":", linewidth=0.9)
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.2)
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
    fig.tight_layout()
    pdf_path = PLOT_DIR / f"{stem}.pdf"
    png_path = PLOT_DIR / f"{stem}.png"
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {
        "role": role,
        "mismatch_seed": seed,
        "noise_seed": master["noise_seed"],
        "band": band,
        "sndr_db": master["sndr_db"],
        "snr_db": master["snr_db"],
        "enob_raw": master["enob_raw"],
        "sfdr_dbc": master["sfdr_dbc"],
        "code_checksum_sha256": compact_code_checksum(codes),
        "source_csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "pdf": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
        "png": str(png_path.relative_to(ROOT)).replace("\\", "/"),
        "source_csv_sha256": sha256_file(csv_path),
        "pdf_sha256": sha256_file(pdf_path),
        "png_sha256": sha256_file(png_path),
    }


def main():
    preflight = json.loads(
        (RESULT_DIR / "preflight_audit.json").read_text(encoding="ascii")
    )
    current_master = read_csv(CSV_DIR / "dynamic_master.csv")
    current_codes = read_csv(CSV_DIR / "dynamic_codes.csv")
    baseline_master = read_csv(
        ROOT / "references" / "baseline_mc200" / "dynamic_master.csv"
    )

    current_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in current_master
    }
    baseline_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in baseline_master
    }
    code_groups = {}
    for row in current_codes:
        key = (int(row["mismatch_seed"]), row["band"])
        code_groups.setdefault(key, []).append(row)
    for rows in code_groups.values():
        rows.sort(key=lambda row: int(row["frame_index"]))

    executed_seeds = sorted({int(row["mismatch_seed"]) for row in current_master})
    optional_executed = any(seed in executed_seeds for seed in OPTIONAL_SEEDS)
    required_seeds = set(CORE_SEEDS)
    if optional_executed:
        required_seeds.update(OPTIONAL_SEEDS)
    required_keys = {(seed, band) for seed in required_seeds for band in BANDS}

    comparisons = []
    for key in sorted(required_keys):
        current = current_by_key.get(key)
        baseline = baseline_by_key[key]
        if current is None:
            continue
        comparisons.append(
            {
                "mismatch_seed": key[0],
                "band": key[1],
                "current_state": current["state"],
                "baseline_state": baseline["state"],
                "state_match": current["state"] == baseline["state"],
                "hard_pass_match": as_bool(current["hard_dynamic_pass"])
                == as_bool(baseline["hard_dynamic_pass"]),
                "mismatch_checksum_match": current["mismatch_checksum_sha256"]
                == baseline["mismatch_checksum_sha256"],
                "noise_checksum_match": current["noise_draw_checksum_sha256"]
                == baseline["noise_draw_checksum_sha256"],
                "code_checksum_match": current["compact_code_checksum_sha256"]
                == baseline["compact_code_checksum_sha256"],
                "delta_sndr_db": float(current["sndr_db"])
                - float(baseline["sndr_db"]),
                "delta_snr_db": float(current["snr_db"])
                - float(baseline["snr_db"]),
                "delta_enob_bit": float(current["enob_raw"])
                - float(baseline["enob_raw"]),
            }
        )
    write_csv_atomic(CSV_DIR / "selected_seed_comparison.csv", comparisons)
    write_csv_atomic(CSV_DIR / "dynamic_master_mc12.csv", current_master)
    write_csv_atomic(CSV_DIR / "dynamic_codes_mc12.csv", current_codes)

    representatives = []
    for role, seed, band in SPECTRA:
        representatives.append(
            save_spectrum(
                current_by_key[(seed, band)],
                code_groups[(seed, band)],
                role,
            )
        )
    write_csv_atomic(
        CSV_DIR / "representative_spectra_manifest.csv", representatives
    )

    core_keys = {(seed, band) for seed in CORE_SEEDS for band in BANDS}
    optional_keys = {(seed, band) for seed in OPTIONAL_SEEDS for band in BANDS}
    valid_core = sum(
        key in current_by_key and current_by_key[key]["state"] in VALID_STATES
        for key in core_keys
    )
    valid_optional = sum(
        key in current_by_key and current_by_key[key]["state"] in VALID_STATES
        for key in optional_keys
    )
    comparisons_complete = len(comparisons) == len(required_keys)
    regression_pass = comparisons_complete and all(
        (
            as_bool(row["state_match"]),
            as_bool(row["hard_pass_match"]),
            as_bool(row["mismatch_checksum_match"]),
            as_bool(row["noise_checksum_match"]),
            abs(float(row["delta_sndr_db"])) <= 0.10,
            abs(float(row["delta_snr_db"])) <= 0.20,
            abs(float(row["delta_enob_bit"])) <= 0.02,
        )
        for row in comparisons
    )
    execution_complete = valid_core == 24 and (
        not optional_executed or valid_optional == 4
    )
    if not execution_complete:
        final_status = "BLOCKED_SELECTED_SEED_QUICK_REGRESSION_INCOMPLETE"
    elif regression_pass:
        final_status = "PASS_SELECTED_SEED_QUICK_REGRESSION_MC12"
    else:
        final_status = "FAIL_SELECTED_SEED_QUICK_REGRESSION_MC12"

    status = {
        "validation_id": "A44_FAST64_D3_MC12_PLUS2_1H_V8",
        "status": final_status,
        "execution_complete": execution_complete,
        "regression_pass": regression_pass,
        "valid_core_records": valid_core,
        "required_core_records": 24,
        "optional_pair_executed": optional_executed,
        "valid_optional_records": valid_optional,
        "executed_seeds": executed_seeds,
        "selected_maxstep_ps": 50,
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "all_code_checksums_equal": comparisons_complete
        and all(as_bool(row["code_checksum_match"]) for row in comparisons),
        "mc200_yield_claim": False,
        "production_yield_claim": False,
        "dynamic_signoff_claim": False,
        "evidence_class": "FAST64_D3_SELECTED_SEED_QUICK_REGRESSION_MODEL_CONDITIONAL",
    }
    audit = {
        "pass": execution_complete and regression_pass and preflight["pass"],
        "preflight_pass": preflight["pass"],
        "execution_complete": execution_complete,
        "comparison_rows": len(comparisons),
        "expected_comparison_rows": len(required_keys),
        "regression_pass": regression_pass,
        "representative_spectra_count": len(representatives),
        "representative_roles": [row["role"] for row in representatives],
        "all_plot_artifacts_nonempty": all(
            (ROOT / row[path_field]).stat().st_size > 0
            for row in representatives
            for path_field in ("source_csv", "pdf", "png")
        ),
    }
    write_json_atomic(RESULT_DIR / "quick_status.json", status)
    write_json_atomic(RESULT_DIR / "quick_audit.json", audit)
    write_report(status, comparisons, representatives)
    print(
        "QUICK_FINAL status={} core={}/24 optional={} comparisons={} plots={}".format(
            status["status"],
            valid_core,
            optional_executed,
            len(comparisons),
            len(representatives),
        ),
        flush=True,
    )
    raise SystemExit(0 if audit["pass"] else 1)


if __name__ == "__main__":
    main()
