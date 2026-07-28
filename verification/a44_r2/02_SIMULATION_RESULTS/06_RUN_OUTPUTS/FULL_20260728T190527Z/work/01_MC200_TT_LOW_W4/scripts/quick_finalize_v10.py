#!/usr/bin/env python3
"""Finalize strict MC10 regression evidence without MC200 claims."""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from dynamic_analysis import spectrum_rows
from regression_gate_v10 import as_bool, comparisons_pass
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


CORE_SEEDS = (1, 21, 44, 48, 64, 115, 129, 166, 170, 183)
SPECTRA = (
    ("P1_WORST_BAND_SNDR", 21, "LOW"),
    ("P5_WORST_BAND_SNDR", 129, "LOW"),
    ("P10_WORST_BAND_SNDR", 183, "NEAR_NYQUIST"),
)
VALID_STATES = {"VALID_PASS", "VALID_FAIL"}
VALIDATION_ID = os.environ.get(
    "A44_VALIDATION_ID", "A44_FAST64_D3_MC10_1H_V10"
)
REQUIRED_RECORDS = len(CORE_SEEDS) * len(BANDS)


def write_report(status, comparisons, representatives, integrity_failures):
    max_sndr = max(
        (abs(float(row["delta_sndr_db"])) for row in comparisons), default=0.0
    )
    max_snr = max(
        (abs(float(row["delta_snr_db"])) for row in comparisons), default=0.0
    )
    max_enob = max(
        (abs(float(row["delta_enob_bit"])) for row in comparisons), default=0.0
    )
    lines = [
        "# A44 FAST64 D3 MC10 One-Hour Validation Report",
        "",
        f"- Status: `{status['status']}`",
        f"- Execution complete: `{status['execution_complete']}`",
        f"- Strict regression pass: `{status['regression_pass']}`",
        (
            f"- Required records: `{status['valid_core_records']}/"
            f"{status['required_core_records']}` valid"
        ),
        f"- Selected seeds: `{status['executed_seeds']}`",
        f"- Selected maxstep: `{status['selected_maxstep_ps']} ps`",
        f"- Execution mode: `{status['execution_mode']}`",
        f"- Maximum absolute SNDR delta: `{max_sndr:.6f} dB`",
        f"- Maximum absolute SNR delta: `{max_snr:.6f} dB`",
        f"- Maximum absolute ENOB delta: `{max_enob:.6f} bit`",
        (
            "- Compact code checksums equal: "
            f"`{status['all_code_checksums_equal']}`"
        ),
        f"- Integrity failures: `{len(integrity_failures)}`",
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
            "It is not an unbiased MC200 yield estimate, production-yield",
            "evidence, native-MOS transient-noise evidence, or dynamic signoff.",
            "",
        ]
    )
    (REPORT_DIR / "FINAL_MC10_ONE_HOUR_REPORT.md").write_text(
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
    ax.grid(
        True,
        which="major",
        color="#b8b8b8",
        linestyle=":",
        linewidth=0.9,
    )
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


def record_integrity_failures(required_keys, current_by_key, code_groups):
    failures = []
    for key in sorted(required_keys):
        row = current_by_key.get(key)
        if row is None:
            failures.append({"seed": key[0], "band": key[1], "reason": "missing"})
            continue
        checks = {
            "valid_state": row["state"] in VALID_STATES,
            "valid_frames_64": int(row["valid_frame_count"]) == NFFT,
            "compact_codes_64": len(code_groups.get(key, [])) == NFFT,
            "invalid_zero": int(row["invalid_count"]) == 0,
            "timeout_zero": int(row["timeout_count"]) == 0,
            "clipping_zero": int(row["clipping_count"]) == 0,
            "missing_frame_zero": int(row["missing_frame_count"]) == 0,
            "duplicate_frame_zero": int(row["duplicate_frame_count"]) == 0,
            "parseval_pass": as_bool(row["parseval_pass"]),
            "noise_draw_checksum_match": as_bool(
                row["noise_draw_checksum_match"]
            ),
            "returncode_zero": int(row["returncode"]) == 0,
            "not_timed_out": not as_bool(row["timed_out"]),
            "not_aborted": not as_bool(row["simulation_aborted"]),
        }
        if not all(checks.values()):
            failures.append(
                {
                    "seed": key[0],
                    "band": key[1],
                    "reason": "record_integrity",
                    "checks": checks,
                }
            )
    return failures


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
        (int(row["mismatch_seed"]), row["band"]): row
        for row in current_master
    }
    baseline_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row
        for row in baseline_master
    }
    code_groups = {}
    for row in current_codes:
        key = (int(row["mismatch_seed"]), row["band"])
        code_groups.setdefault(key, []).append(row)
    for rows in code_groups.values():
        rows.sort(key=lambda row: int(row["frame_index"]))

    required_keys = {
        (seed, band) for seed in CORE_SEEDS for band in BANDS
    }
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
                "mismatch_checksum_match": current[
                    "mismatch_checksum_sha256"
                ]
                == baseline["mismatch_checksum_sha256"],
                "noise_checksum_match": current[
                    "noise_draw_checksum_sha256"
                ]
                == baseline["noise_draw_checksum_sha256"],
                "code_checksum_match": current[
                    "compact_code_checksum_sha256"
                ]
                == baseline["compact_code_checksum_sha256"],
                "delta_sndr_db": float(current["sndr_db"])
                - float(baseline["sndr_db"]),
                "delta_snr_db": float(current["snr_db"])
                - float(baseline["snr_db"]),
                "delta_enob_bit": float(current["enob_raw"])
                - float(baseline["enob_raw"]),
            }
        )

    write_csv_atomic(
        CSV_DIR / "selected_seed_comparison_mc10.csv", comparisons
    )
    write_csv_atomic(CSV_DIR / "dynamic_master_mc10.csv", current_master)
    write_csv_atomic(CSV_DIR / "dynamic_codes_mc10.csv", current_codes)

    representatives = []
    for role, seed, band in SPECTRA:
        key = (seed, band)
        if key in current_by_key and key in code_groups:
            representatives.append(
                save_spectrum(
                    current_by_key[key],
                    code_groups[key],
                    role,
                )
            )
    write_csv_atomic(
        CSV_DIR / "representative_spectra_manifest.csv", representatives
    )

    integrity_failures = record_integrity_failures(
        required_keys, current_by_key, code_groups
    )
    valid_core = sum(
        key in current_by_key and current_by_key[key]["state"] in VALID_STATES
        for key in required_keys
    )
    execution_complete = not integrity_failures
    regression_pass = comparisons_pass(comparisons, REQUIRED_RECORDS)
    plots_complete = len(representatives) == len(SPECTRA) and all(
        (ROOT / row[path_field]).stat().st_size > 0
        for row in representatives
        for path_field in ("source_csv", "pdf", "png")
    )
    if not execution_complete:
        final_status = "BLOCKED_SELECTED_SEED_QUICK_REGRESSION_INCOMPLETE"
    elif not regression_pass:
        final_status = "FAIL_SELECTED_SEED_QUICK_REGRESSION_MC10"
    elif not plots_complete:
        final_status = "BLOCKED_SELECTED_SEED_ARTIFACT_INCOMPLETE"
    else:
        final_status = "PASS_SELECTED_SEED_QUICK_REGRESSION_MC10"

    executed_seeds = sorted(
        {int(row["mismatch_seed"]) for row in current_master}
    )
    all_code_checksums_equal = (
        len(comparisons) == REQUIRED_RECORDS
        and all(as_bool(row["code_checksum_match"]) for row in comparisons)
    )
    status = {
        "validation_id": VALIDATION_ID,
        "status": final_status,
        "execution_complete": execution_complete,
        "regression_pass": regression_pass,
        "valid_core_records": valid_core,
        "required_core_records": REQUIRED_RECORDS,
        "executed_seeds": executed_seeds,
        "selected_maxstep_ps": 50,
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "all_code_checksums_equal": all_code_checksums_equal,
        "integrity_failure_count": len(integrity_failures),
        "plots_complete": plots_complete,
        "mc200_yield_claim": False,
        "production_yield_claim": False,
        "dynamic_signoff_claim": False,
        "evidence_class": (
            "FAST64_D3_SELECTED_SEED_QUICK_REGRESSION_MODEL_CONDITIONAL"
        ),
    }
    audit = {
        "pass": (
            execution_complete
            and regression_pass
            and plots_complete
            and preflight["pass"]
        ),
        "preflight_pass": preflight["pass"],
        "execution_complete": execution_complete,
        "integrity_failures": integrity_failures,
        "comparison_rows": len(comparisons),
        "expected_comparison_rows": REQUIRED_RECORDS,
        "regression_pass": regression_pass,
        "representative_spectra_count": len(representatives),
        "representative_roles": [row["role"] for row in representatives],
        "all_plot_artifacts_nonempty": plots_complete,
    }
    write_json_atomic(RESULT_DIR / "quick_status.json", status)
    write_json_atomic(RESULT_DIR / "quick_audit.json", audit)
    write_report(status, comparisons, representatives, integrity_failures)
    print(
        "QUICK_FINAL_V10 status={} records={}/{} comparisons={} plots={}".format(
            status["status"],
            valid_core,
            REQUIRED_RECORDS,
            len(comparisons),
            len(representatives),
        ),
        flush=True,
    )
    raise SystemExit(0 if audit["pass"] else 1)


if __name__ == "__main__":
    main()
