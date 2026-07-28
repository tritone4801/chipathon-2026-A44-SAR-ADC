#!/usr/bin/env python3
"""Aggregate, pair, plot, audit, and seal the four-device resize PVT3 MC20 campaign."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "csv"
CONFIG = ROOT / "config"
MANIFESTS = ROOT / "manifests"
RESULTS = ROOT / "results"
PLOTS = ROOT / "plots"
REPORTS = ROOT / "reports"
JOB_RESULTS = RESULTS / "jobs"
JOB_CODES = CSV_DIR / "job_codes"

SEEDS = (44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96)
PVT_ORDER = ("TT_3P3_27C", "SS_3P0_125C", "FF_3P6_M40C")
PVT_SHORT = {"TT_3P3_27C": "TT", "SS_3P0_125C": "SS", "FF_3P6_M40C": "FF"}
PVT_META = {
    "TT_3P3_27C": ("typical", "mimcap_typical", 3.3, 27),
    "SS_3P0_125C": ("ss", "mimcap_ss", 3.0, 125),
    "FF_3P6_M40C": ("ff", "mimcap_ff", 3.6, -40),
}
METRICS = {
    "SNR_dB": "steady_state_snr_db",
    "SNDR_dB": "steady_state_sndr_db",
    "ENOB_raw_bit": "steady_state_enob_raw",
    "SFDR_dBc": "steady_state_sfdr_dbc",
    "THD_dB": "steady_state_thd_db",
    "HD2_dBc": "steady_state_hd2_dbc",
    "HD3_dBc": "steady_state_hd3_dbc",
}
CANDIDATE_ID = "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587"
BASELINE_ID = "CMP_IN_A2P25_W_T1P000"
BASELINE_MASTER = ROOT / "references/baseline_t1p000_pvt3_mc20_master.csv"
COLORS = {"TT_3P3_27C": "#1f77b4", "SS_3P0_125C": "#d62728", "FF_3P6_M40C": "#2ca02c"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def percentile(values: Iterable[float], q: float) -> float:
    return float(np.percentile(np.asarray(list(values), dtype=float), q, method="linear"))


def csv_bool(value: object) -> bool:
    return str(value).strip().lower() == "true"


def load_baseline() -> dict[tuple[int, str], dict[str, str]]:
    rows = read_csv(BASELINE_MASTER)
    lookup = {
        (int(row["mismatch_seed"]), row["pvt"]): row
        for row in rows
    }
    if len(rows) != 60 or len(lookup) != 60:
        raise RuntimeError(
            f"baseline must contain 60 unique seed/PVT records, got rows={len(rows)} unique={len(lookup)}"
        )
    return lookup


def save_figure(fig: plt.Figure, stem: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(PLOTS / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def load_formal() -> tuple[list[dict[str, object]], list[dict[str, str]], list[dict[str, object]]]:
    matrix = read_csv(MANIFESTS / "job_matrix.csv")
    master: list[dict[str, object]] = []
    code_rows: list[dict[str, str]] = []
    missing = []
    for job in matrix:
        result_path = JOB_RESULTS / f"{job['job_id']}.json"
        code_path = JOB_CODES / f"{job['job_id']}.csv"
        if not result_path.is_file() or not code_path.is_file():
            missing.append(job["job_id"])
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        master.append(
            {
                "seed_order": SEEDS.index(int(result["mismatch_seed"])) + 1,
                "seed_group": job["category"],
                "process_section": PVT_META[str(result["pvt"])][0],
                "mim_section": PVT_META[str(result["pvt"])][1],
                "vdd_v": PVT_META[str(result["pvt"])][2],
                "temp_c": PVT_META[str(result["pvt"])][3],
                **result,
            }
        )
        for row in read_csv(code_path):
            code_rows.append(
                {
                    "pvt": result["pvt"],
                    "process_section": PVT_META[str(result["pvt"])][0],
                    "mim_section": PVT_META[str(result["pvt"])][1],
                    "vdd_v": PVT_META[str(result["pvt"])][2],
                    "temp_c": PVT_META[str(result["pvt"])][3],
                    **row,
                }
            )
    if missing:
        raise RuntimeError(f"missing formal artifacts: {missing}")
    master.sort(key=lambda row: (PVT_ORDER.index(str(row["pvt"])), SEEDS.index(int(row["mismatch_seed"]))))
    code_rows.sort(
        key=lambda row: (
            PVT_ORDER.index(row["pvt"]),
            SEEDS.index(int(row["mismatch_seed"])),
            int(row["frame_index"]),
        )
    )
    return master, matrix, code_rows


def audit_formal_decks(master: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for result in master:
        pvt = str(result["pvt"])
        section, mim, vdd, temp = PVT_META[pvt]
        deck_path = ROOT / str(result["deck"])
        text = deck_path.read_text(encoding="utf-8", errors="replace")
        checks = {
            "seed": f".option seed={int(result['mismatch_seed'])}" in text,
            "process": f"sm141064.ngspice {section}" in text,
            "mim": f"sm141064.ngspice {mim}" in text,
            "not_statistical": "sm141064.ngspice statistical" not in text,
            "temp": f".temp {temp}" in text,
            "vdd": f"VVDD vdd 0 {vdd:.12g}" in text,
            "rng_burn_19": text.count("RLEGACY_RNG_BURN_") == 19,
            "bridge_low": f"in_low={0.30 * vdd:.12g}" in text,
            "bridge_high": f"in_high={0.70 * vdd:.12g}" in text,
            "logic_high": f"out_high={vdd:.12g}" in text,
            "candidate_comparator_bound": str(
                ROOT
                / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
            )
            in text,
        }
        rows.append(
            {
                "job_id": result["job_id"],
                "pvt": pvt,
                "mismatch_seed": result["mismatch_seed"],
                **checks,
                "pass": all(checks.values()),
            }
        )
    return rows


def audit_baseline_pairing(
    master: list[dict[str, object]],
    baseline: dict[tuple[int, str], dict[str, str]],
) -> tuple[bool, list[dict[str, object]]]:
    exact_fields = (
        "band",
        "bin",
        "fin_hz",
        "input_vpp_diff",
        "maxstep_ns",
        "method_id",
        "mismatch_checksum",
        "mismatch_seed",
        "nfft",
        "noise_full_checksum",
        "noise_mode",
        "noise_prefix_checksum_0_63",
        "noise_seed",
        "phase_rad",
        "pvt",
        "retained_frame_end",
        "retained_frame_start",
        "steady_state_method_id",
        "total_frames",
        "warmup_frames",
    )
    rows: list[dict[str, object]] = []
    for candidate in master:
        key = (int(candidate["mismatch_seed"]), str(candidate["pvt"]))
        reference = baseline[key]
        field_checks = {
            field: str(candidate[field]) == str(reference[field])
            for field in exact_fields
        }
        row_pass = all(field_checks.values())
        rows.append(
            {
                "mismatch_seed": key[0],
                "pvt": key[1],
                "candidate_job_id": candidate["job_id"],
                "baseline_job_id": reference["job_id"],
                **{f"match_{field}": value for field, value in field_checks.items()},
                "pass": row_pass,
            }
        )
    return len(rows) == 60 and all(bool(row["pass"]) for row in rows), rows


def build_pivot(
    master: list[dict[str, object]],
    baseline: dict[tuple[int, str], dict[str, str]],
    pairing_pass: bool,
) -> list[dict[str, object]]:
    lookup = {(int(row["mismatch_seed"]), str(row["pvt"])): row for row in master}
    rows = []
    for seed in SEEDS:
        by_pvt = {pvt: lookup[(seed, pvt)] for pvt in PVT_ORDER}
        hard = {pvt: bool(by_pvt[pvt]["steady_state_hard_dynamic_pass"]) for pvt in PVT_ORDER}
        if all(hard.values()):
            classification = "ALL_CORNER_PASS"
        elif hard["TT_3P3_27C"]:
            classification = "PVT_INDUCED_REGRESSION"
        elif any(hard[pvt] for pvt in PVT_ORDER[1:]):
            classification = "CORNER_RECOVERY"
        else:
            classification = "PERSISTENT_FAIL"
        output: dict[str, object] = {
            "seed_order": SEEDS.index(seed) + 1,
            "mismatch_seed": seed,
            "seed_group": str(by_pvt["TT_3P3_27C"]["seed_group"]),
            "classification": classification,
            "all_corner_hard_pass": all(hard.values()),
        }
        for pvt in PVT_ORDER:
            short = PVT_SHORT[pvt]
            output[f"{short}_frame0_pass"] = by_pvt[pvt]["first_conversion_protocol_pass"]
            output[f"{short}_hard_dynamic_pass"] = hard[pvt]
            output[f"{short}_snr_budget_pass"] = by_pvt[pvt]["steady_state_snr_budget_pass"]
            baseline_row = baseline[(seed, pvt)]
            output[f"{short}_baseline_hard_dynamic_pass"] = csv_bool(
                baseline_row["steady_state_hard_dynamic_pass"]
            )
            output[f"{short}_baseline_snr_budget_pass"] = csv_bool(
                baseline_row["steady_state_snr_budget_pass"]
            )
            for label, field in METRICS.items():
                output[f"{short}_{label}"] = by_pvt[pvt][field]
                output[f"{short}_baseline_{label}"] = baseline_row[field]
                if pairing_pass:
                    output[f"delta_resize_minus_baseline_{short}_{label}"] = (
                        float(by_pvt[pvt][field]) - float(baseline_row[field])
                    )
        if pairing_pass:
            for pvt in PVT_ORDER[1:]:
                short = PVT_SHORT[pvt]
                for label, field in METRICS.items():
                    output[f"delta_{short}_minus_TT_{label}"] = (
                        float(by_pvt[pvt][field])
                        - float(by_pvt["TT_3P3_27C"][field])
                    )
        rows.append(output)
    return rows


def build_corner_summary(master: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for pvt in PVT_ORDER:
        subset = [row for row in master if row["pvt"] == pvt]
        section, mim, vdd, temp = PVT_META[pvt]
        output: dict[str, object] = {
            "pvt": pvt,
            "process_section": section,
            "mim_section": mim,
            "vdd_v": vdd,
            "temp_c": temp,
            "record_count": len(subset),
            "execution_complete_count": sum(
                row["state"] in {"COMPLETE", "COMPLETE_WITH_FAIL"} for row in subset
            ),
            "frame0_protocol_pass_count": sum(bool(row["first_conversion_protocol_pass"]) for row in subset),
            "hard_dynamic_pass_count": sum(bool(row["steady_state_hard_dynamic_pass"]) for row in subset),
            "snr_budget_pass_count": sum(bool(row["steady_state_snr_budget_pass"]) for row in subset),
        }
        for label, field in METRICS.items():
            values = [float(row[field]) for row in subset]
            for q in (0, 1, 5, 10, 50, 90, 95, 99, 100):
                output[f"{label}_P{q}"] = percentile(values, q)
        rows.append(output)
    return rows


def build_paired_deltas(
    master: list[dict[str, object]],
    baseline: dict[tuple[int, str], dict[str, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in master:
        key = (int(candidate["mismatch_seed"]), str(candidate["pvt"]))
        reference = baseline[key]
        baseline_hard = csv_bool(reference["steady_state_hard_dynamic_pass"])
        resized_hard = bool(candidate["steady_state_hard_dynamic_pass"])
        baseline_snr = csv_bool(reference["steady_state_snr_budget_pass"])
        resized_snr = bool(candidate["steady_state_snr_budget_pass"])
        row: dict[str, object] = {
            "seed_order": candidate["seed_order"],
            "seed_group": candidate["seed_group"],
            "mismatch_seed": key[0],
            "pvt": key[1],
            "baseline_hard_dynamic_pass": baseline_hard,
            "resized_hard_dynamic_pass": resized_hard,
            "hard_dynamic_transition": (
                "FAIL_TO_PASS"
                if not baseline_hard and resized_hard
                else "PASS_TO_FAIL"
                if baseline_hard and not resized_hard
                else "PASS_STAYS_PASS"
                if baseline_hard
                else "FAIL_STAYS_FAIL"
            ),
            "baseline_snr_budget_pass": baseline_snr,
            "resized_snr_budget_pass": resized_snr,
            "snr_budget_transition": (
                "FAIL_TO_PASS"
                if not baseline_snr and resized_snr
                else "PASS_TO_FAIL"
                if baseline_snr and not resized_snr
                else "PASS_STAYS_PASS"
                if baseline_snr
                else "FAIL_STAYS_FAIL"
            ),
            "baseline_codes_all_checksum": reference["codes_all_checksum"],
            "resized_codes_all_checksum": candidate["codes_all_checksum"],
            "baseline_codes_retained_checksum": reference["codes_retained_checksum"],
            "resized_codes_retained_checksum": candidate["codes_retained_checksum"],
        }
        for label, field in METRICS.items():
            baseline_value = float(reference[field])
            resized_value = float(candidate[field])
            row[f"baseline_{label}"] = baseline_value
            row[f"resized_{label}"] = resized_value
            row[f"delta_resize_minus_baseline_{label}"] = resized_value - baseline_value
        rows.append(row)
    return rows


def build_comparison_summary(paired: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pvt in PVT_ORDER:
        subset = [row for row in paired if row["pvt"] == pvt]
        output: dict[str, object] = {
            "pvt": pvt,
            "record_count": len(subset),
            "baseline_hard_dynamic_pass_count": sum(
                bool(row["baseline_hard_dynamic_pass"]) for row in subset
            ),
            "resized_hard_dynamic_pass_count": sum(
                bool(row["resized_hard_dynamic_pass"]) for row in subset
            ),
            "hard_fail_to_pass_count": sum(
                row["hard_dynamic_transition"] == "FAIL_TO_PASS" for row in subset
            ),
            "hard_pass_to_fail_count": sum(
                row["hard_dynamic_transition"] == "PASS_TO_FAIL" for row in subset
            ),
            "baseline_snr_budget_pass_count": sum(
                bool(row["baseline_snr_budget_pass"]) for row in subset
            ),
            "resized_snr_budget_pass_count": sum(
                bool(row["resized_snr_budget_pass"]) for row in subset
            ),
            "snr_fail_to_pass_count": sum(
                row["snr_budget_transition"] == "FAIL_TO_PASS" for row in subset
            ),
            "snr_pass_to_fail_count": sum(
                row["snr_budget_transition"] == "PASS_TO_FAIL" for row in subset
            ),
        }
        for label in METRICS:
            baseline_values = [float(row[f"baseline_{label}"]) for row in subset]
            resized_values = [float(row[f"resized_{label}"]) for row in subset]
            delta_values = [
                float(row[f"delta_resize_minus_baseline_{label}"]) for row in subset
            ]
            output[f"baseline_{label}_P50"] = percentile(baseline_values, 50)
            output[f"resized_{label}_P50"] = percentile(resized_values, 50)
            for q in (0, 10, 50, 90, 100):
                output[f"delta_{label}_P{q}"] = percentile(delta_values, q)
        rows.append(output)
    return rows


def plot_seed_sndr(master: list[dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.3))
    x = np.arange(len(SEEDS))
    lookup = {(int(row["mismatch_seed"]), str(row["pvt"])): row for row in master}
    for pvt in PVT_ORDER:
        y = [float(lookup[(seed, pvt)]["steady_state_sndr_db"]) for seed in SEEDS]
        ax.plot(x, y, marker="o", markersize=4, linewidth=1.3, label=PVT_SHORT[pvt], color=COLORS[pvt])
    ax.axhline(46.91, color="#333333", linestyle="--", linewidth=1, label="SNDR gate 46.91 dB")
    ax.set_xticks(x)
    ax.set_xticklabels(SEEDS, rotation=45)
    ax.set_xlabel("Selected mismatch seed")
    ax.set_ylabel("SNDR (dB)")
    ax.set_title(f"{CANDIDATE_ID} selected MC20: SNDR by analog PVT")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=4, fontsize=8)
    save_figure(fig, "pvt3_mc20_seed_sndr")


def plot_ecdf(master: list[dict[str, object]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    for ax, (label, field), gate in zip(
        axes,
        (("SNR (dB)", "steady_state_snr_db"), ("SNDR (dB)", "steady_state_sndr_db"), ("Raw ENOB (bit)", "steady_state_enob_raw")),
        (48.14, 46.91, 7.50),
    ):
        for pvt in PVT_ORDER:
            values = np.sort([float(row[field]) for row in master if row["pvt"] == pvt])
            y = np.arange(1, len(values) + 1) / len(values)
            ax.step(values, y, where="post", label=PVT_SHORT[pvt], color=COLORS[pvt])
        ax.axvline(gate, color="#333333", linestyle="--", linewidth=1)
        ax.set_xlabel(label)
        ax.set_ylabel("ECDF i/N")
        ax.grid(True, alpha=0.25)
    axes[0].legend()
    fig.suptitle("Selected MC20 descriptive ECDF by analog PVT (not yield)")
    fig.tight_layout()
    save_figure(fig, "pvt3_mc20_ecdf")


def plot_status_map(pivot: list[dict[str, object]]) -> None:
    matrix = np.asarray(
        [
            [1 if row[f"{short}_hard_dynamic_pass"] else 0 for short in ("TT", "SS", "FF")]
            for row in pivot
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(5.2, 8.4))
    image = ax.imshow(matrix, cmap=matplotlib.colors.ListedColormap(["#c83e4d", "#2a9d8f"]), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(3), ("TT", "SS", "FF"))
    ax.set_yticks(range(len(SEEDS)), [str(seed) for seed in SEEDS])
    ax.set_xlabel("Analog PVT")
    ax.set_ylabel("Mismatch seed")
    ax.set_title("Hard dynamic status map")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "PASS" if matrix[i, j] else "FAIL", ha="center", va="center", fontsize=6, color="white")
    fig.colorbar(image, ax=ax, ticks=(0, 1), label="0=FAIL, 1=PASS")
    fig.tight_layout()
    save_figure(fig, "pvt3_mc20_hard_status_map")


def plot_delta_heatmap(pivot: list[dict[str, object]], pairing_pass: bool) -> None:
    if not pairing_pass:
        return
    values = np.asarray(
        [
            [
                float(row[f"delta_resize_minus_baseline_{short}_SNDR_dB"])
                for short in ("TT", "SS", "FF")
            ]
            for row in pivot
        ]
    )
    limit = max(0.5, float(np.max(np.abs(values))))
    fig, ax = plt.subplots(figsize=(6.3, 8.2))
    image = ax.imshow(values, cmap="coolwarm", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks((0, 1, 2), ("TT", "SS", "FF"))
    ax.set_yticks(range(len(SEEDS)), [str(seed) for seed in SEEDS])
    ax.set_xlabel("Paired analog PVT")
    ax.set_ylabel("Mismatch seed")
    ax.set_title("Resized minus T1P000 paired SNDR delta (dB)")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, f"{values[i, j]:+.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(image, ax=ax, label="ΔSNDR (dB)")
    fig.tight_layout()
    save_figure(fig, "pvt3_mc20_paired_sndr_delta")


def plot_spectra(master: list[dict[str, object]], code_rows: list[dict[str, str]]) -> None:
    by_job: dict[str, list[dict[str, str]]] = {}
    for row in code_rows:
        if row["retained"].lower() == "true":
            by_job.setdefault(row["job_id"], []).append(row)
    fig, axes = plt.subplots(3, 2, figsize=(11.5, 11.5), sharex=True, sharey=True)
    for row_index, pvt in enumerate(PVT_ORDER):
        subset = [row for row in master if row["pvt"] == pvt]
        worst = min(subset, key=lambda row: float(row["steady_state_sndr_db"]))
        median_value = percentile([float(row["steady_state_sndr_db"]) for row in subset], 50)
        representative = min(subset, key=lambda row: abs(float(row["steady_state_sndr_db"]) - median_value))
        for column, (role, record) in enumerate((("worst", worst), ("near-median", representative))):
            rows = sorted(by_job[str(record["job_id"])], key=lambda row: int(row["frame_index"]))
            codes = np.asarray([int(row["code"]) for row in rows], dtype=float)
            fft = np.fft.rfft(codes) / len(codes)
            amplitude = np.abs(fft)
            amplitude[1:-1] *= 2.0
            dbfs = 20.0 * np.log10(np.maximum(amplitude / (255.0 / 2.0), 1e-12))
            bins = np.arange(len(dbfs))
            ax = axes[row_index, column]
            markerline, stemlines, baseline = ax.stem(bins, dbfs, basefmt=" ")
            plt.setp(markerline, markersize=3, color=COLORS[pvt])
            plt.setp(stemlines, linewidth=0.7, color=COLORS[pvt])
            ax.set_ylim(-100, 5)
            ax.grid(True, alpha=0.2)
            ax.set_title(
                f"{PVT_SHORT[pvt]} {role}: seed {int(record['mismatch_seed'])}, "
                f"SNDR {float(record['steady_state_sndr_db']):.2f} dB",
                fontsize=9,
            )
            if column == 0:
                ax.set_ylabel("Magnitude (dBFS)")
            if row_index == 2:
                ax.set_xlabel("FFT bin")
    fig.suptitle("Discrete W4 spectra; rectangular FFT, no smoothing")
    fig.tight_layout()
    save_figure(fig, "pvt3_mc20_representative_spectra")


def input_manifest_unchanged() -> tuple[bool, list[dict[str, object]]]:
    rows = read_csv(MANIFESTS / "frozen_input_manifest.csv")
    audit = []
    for row in rows:
        path = ROOT / row["relative_path"]
        observed = sha256_file(path) if path.is_file() else ""
        audit.append(
            {
                "relative_path": row["relative_path"],
                "expected_sha256": row["sha256"],
                "observed_sha256": observed,
                "pass": observed == row["sha256"],
            }
        )
    return all(row["pass"] for row in audit), audit


def seal_manifest() -> dict[str, object]:
    excluded = {"manifest_sha256.csv", "manifest_audit.json"}
    files = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    rows = [
        {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    write_csv(ROOT / "manifest_sha256.csv", rows)
    mismatches = []
    for row in rows:
        path = ROOT / str(row["relative_path"])
        if path.stat().st_size != int(row["bytes"]) or sha256_file(path) != row["sha256"]:
            mismatches.append(str(row["relative_path"]))
    payload = {
        "completed_utc": utc_now(),
        "manifest_record_count": len(rows),
        "mismatches": mismatches,
        "pass": not mismatches,
        "manifest_sha256": sha256_file(ROOT / "manifest_sha256.csv"),
    }
    write_json(ROOT / "manifest_audit.json", payload)
    return payload


def main() -> int:
    for directory in (CSV_DIR, RESULTS, PLOTS, REPORTS):
        directory.mkdir(parents=True, exist_ok=True)
    smoke = json.loads((RESULTS / "smoke_audit_pvt3.json").read_text(encoding="utf-8"))
    pairing_probe = json.loads((RESULTS / "pvt_pairing_audit.json").read_text(encoding="utf-8"))
    master, matrix, code_rows = load_formal()
    baseline = load_baseline()
    retained = [row for row in code_rows if row["retained"].lower() == "true"]
    deck_audit = audit_formal_decks(master)
    write_csv(MANIFESTS / "pvt_binding_formal_audit.csv", deck_audit)

    baseline_pairing_pass, baseline_pairing_rows = audit_baseline_pairing(
        master, baseline
    )
    write_csv(RESULTS / "baseline_pairing_audit.csv", baseline_pairing_rows)
    write_json(
        RESULTS / "baseline_pairing_audit.json",
        {
            "completed_utc": utc_now(),
            "record_count": len(baseline_pairing_rows),
            "all_method_noise_mismatch_fields_match": baseline_pairing_pass,
            "candidate_comparator_is_intentionally_different": True,
            "pass": baseline_pairing_pass,
        },
    )
    pairing_pass = bool(pairing_probe.get("pass")) and baseline_pairing_pass
    pivot = build_pivot(master, baseline, pairing_pass)
    summary = build_corner_summary(master)
    paired = build_paired_deltas(master, baseline)
    comparison_summary = build_comparison_summary(paired)
    write_csv(CSV_DIR / "pvt3_mc20_master.csv", master)
    write_csv(CSV_DIR / "pvt3_mc20_codes_all.csv", code_rows)
    write_csv(CSV_DIR / "pvt3_mc20_codes_w4.csv", retained)
    write_csv(CSV_DIR / "pvt3_mc20_by_seed_pivot.csv", pivot)
    write_csv(CSV_DIR / "pvt3_mc20_corner_summary.csv", summary)
    write_csv(CSV_DIR / "pvt3_mc20_paired_vs_t1p000.csv", paired)
    write_csv(CSV_DIR / "pvt3_mc20_comparison_summary.csv", comparison_summary)

    frame0 = {
        pvt: {
            "pass_count": sum(
                bool(row["first_conversion_protocol_pass"])
                for row in master
                if row["pvt"] == pvt
            ),
            "fail_count": sum(
                not bool(row["first_conversion_protocol_pass"])
                for row in master
                if row["pvt"] == pvt
            ),
            "failure_seeds": [
                int(row["mismatch_seed"])
                for row in master
                if row["pvt"] == pvt and not bool(row["first_conversion_protocol_pass"])
            ],
        }
        for pvt in PVT_ORDER
    }
    write_json(
        RESULTS / "frame0_pvt3_summary.json",
        {
            "method": "FIRST_CONVERSION_SEPARATED",
            "noise_on_frame0_frame64_code_equality_required": False,
            "corners": frame0,
        },
    )

    plot_seed_sndr(master)
    plot_ecdf(master)
    plot_status_map(pivot)
    plot_delta_heatmap(pivot, pairing_pass)
    plot_spectra(master, code_rows)

    input_ok, input_audit = input_manifest_unchanged()
    write_json(RESULTS / "frozen_input_recheck.json", {"pass": input_ok, "rows": input_audit})

    corner_by_pvt = {row["pvt"]: row for row in summary}
    comparison_by_pvt = {row["pvt"]: row for row in comparison_summary}
    tt_pass_seeds = {
        int(row["mismatch_seed"])
        for row in master
        if row["pvt"] == "TT_3P3_27C" and bool(row["steady_state_hard_dynamic_pass"])
    }
    all_corner_pass_seeds = {
        int(row["mismatch_seed"]) for row in pivot if bool(row["all_corner_hard_pass"])
    }
    classification_counts = {
        label: sum(row["classification"] == label for row in pivot)
        for label in (
            "ALL_CORNER_PASS",
            "PVT_INDUCED_REGRESSION",
            "PERSISTENT_FAIL",
            "CORNER_RECOVERY",
        )
    }
    manual_visual_path = RESULTS / "manual_visual_review.json"
    manual_visual = (
        json.loads(manual_visual_path.read_text(encoding="utf-8"))
        if manual_visual_path.is_file()
        else {"pass": False, "status": "PENDING"}
    )
    execution_checks = {
        "formal_records_60": len(master) == 60,
        "formal_job_matrix_60": len(matrix) == 60,
        "all_code_rows_4080": len(code_rows) == 4080,
        "w4_code_rows_3840": len(retained) == 3840,
        "all_terminal": all(row["state"] in {"COMPLETE", "COMPLETE_WITH_FAIL"} for row in master),
        "all_returncode_zero": all(int(row["returncode"]) == 0 for row in master),
        "all_protocol_clean": all(bool(row["protocol_clean"]) for row in master),
        "all_valid_frames_68": all(int(row["valid_frame_count"]) == 68 for row in master),
        "all_parseval": all(bool(row["steady_state_parseval_pass"]) for row in master),
        "all_w4_50ps": all(
            int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            and abs(float(row["maxstep_ns"]) - 0.05) < 1e-15
            for row in master
        ),
        "formal_pvt_binding": all(bool(row["pass"]) for row in deck_audit),
        "smoke_gate": bool(smoke.get("pass")),
        "local_mismatch_pairing_probe": bool(pairing_probe.get("pass")),
        "baseline_pairing_60": baseline_pairing_pass,
        "frozen_inputs_unchanged": input_ok,
        "manual_visual_review": bool(manual_visual.get("pass")),
        "plot_pairs_5": all(
            (PLOTS / f"{stem}.png").is_file() and (PLOTS / f"{stem}.pdf").is_file()
            for stem in (
                "pvt3_mc20_seed_sndr",
                "pvt3_mc20_ecdf",
                "pvt3_mc20_hard_status_map",
                "pvt3_mc20_paired_sndr_delta",
                "pvt3_mc20_representative_spectra",
            )
        ),
    }
    completion_pass = all(execution_checks.values())
    performance = {
        pvt: {
            "hard_dynamic_pass_count": int(corner_by_pvt[pvt]["hard_dynamic_pass_count"]),
            "hard_dynamic_fail_count": 20 - int(corner_by_pvt[pvt]["hard_dynamic_pass_count"]),
            "snr_budget_pass_count": int(corner_by_pvt[pvt]["snr_budget_pass_count"]),
            "frame0_pass_count": int(corner_by_pvt[pvt]["frame0_protocol_pass_count"]),
            "baseline_hard_dynamic_pass_count": int(
                comparison_by_pvt[pvt]["baseline_hard_dynamic_pass_count"]
            ),
            "hard_fail_to_pass_count": int(
                comparison_by_pvt[pvt]["hard_fail_to_pass_count"]
            ),
            "hard_pass_to_fail_count": int(
                comparison_by_pvt[pvt]["hard_pass_to_fail_count"]
            ),
            "baseline_snr_budget_pass_count": int(
                comparison_by_pvt[pvt]["baseline_snr_budget_pass_count"]
            ),
            "snr_fail_to_pass_count": int(
                comparison_by_pvt[pvt]["snr_fail_to_pass_count"]
            ),
            "snr_pass_to_fail_count": int(
                comparison_by_pvt[pvt]["snr_pass_to_fail_count"]
            ),
            "baseline_sndr_p50_db": float(
                comparison_by_pvt[pvt]["baseline_SNDR_dB_P50"]
            ),
            "resized_sndr_p50_db": float(
                comparison_by_pvt[pvt]["resized_SNDR_dB_P50"]
            ),
            "paired_sndr_delta_p50_db": float(
                comparison_by_pvt[pvt]["delta_SNDR_dB_P50"]
            ),
            "paired_enob_delta_p50_bit": float(
                comparison_by_pvt[pvt]["delta_ENOB_raw_bit_P50"]
            ),
        }
        for pvt in PVT_ORDER
    }
    status = {
        "campaign": ROOT.name,
        "completed_utc": utc_now(),
        "candidate_id": CANDIDATE_ID,
        "baseline_id": BASELINE_ID,
        "resize": {
            "XM5_XM6_width_um": 8.2524,
            "XM7_XM11_width_um": 16.8587,
            "unchanged_XM3_XM4_width_um": 3.51,
            "unchanged_XM1_tail_width_um": 1.56,
        },
        "scope": "SELECTED_DIAGNOSTIC_MC20_LOW_W4_AT_THREE_ANALOG_PVT_CORNERS",
        "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        "steady_state_method_id": "FAST64_SS_W4",
        "fixed_step_ps": 50,
        "source_and_binding_status": "PASS" if input_ok and all(row["pass"] for row in deck_audit) else "FAIL",
        "execution_status": "PASS_60_OF_60_COMPLETE" if completion_pass else "INCOMPLETE_OR_AUDIT_FAIL",
        "frame0_status_by_corner": {
            pvt: (
                "PASS_20_OF_20"
                if frame0[pvt]["pass_count"] == 20
                else f"FAIL_{frame0[pvt]['fail_count']}_OF_20"
            )
            for pvt in PVT_ORDER
        },
        "performance_by_corner": performance,
        "tt_pass_seeds": sorted(tt_pass_seeds),
        "tt_pass_count": len(tt_pass_seeds),
        "tt_pass_remaining_pass_at_both_ss_ff_count": len(tt_pass_seeds & all_corner_pass_seeds),
        "tt_pass_remaining_pass_at_both_ss_ff_seeds": sorted(tt_pass_seeds & all_corner_pass_seeds),
        "cross_pvt_classification_counts": classification_counts,
        "pairing_status": "PASS_60_OF_60_METHOD_NOISE_AND_MISMATCH_PAIRED_TO_T1P000" if pairing_pass else "BLOCKED_PVT_MC_BASELINE_PAIRING",
        "completion_checks": execution_checks,
        "completion_status": "COMPLETE_AS_EXECUTED" if completion_pass else "INCOMPLETE",
        "promotion_status": "UNCHANGED_NOT_PROMOTED",
        "signoff_status": "SIGNOFF_NOT_CLAIMED",
        "non_claims": [
            "The selected MC20 set is intentionally tail/edge/diagnostic biased and is not a yield population.",
            "No MC200 190/200 requirement is applied to this MC20 screen.",
            "Corner recovery does not compensate for failure at another corner.",
            "This paired PVT3 MC20 comparison does not replace or extend an MC200 result.",
            "No layout, PEX, silicon, production-yield, promotion, or signoff claim is made.",
        ],
    }
    write_json(ROOT / "STATUS.json", status)
    verification = {
        "completed_utc": utc_now(),
        "checks": execution_checks,
        "pass": completion_pass,
        "performance_failures_are_retained_evidence_not_completion_failures": True,
    }
    write_json(RESULTS / "final_verification.json", verification)

    report_lines = [
        f"# {CANDIDATE_ID} 三 PVT MC20 性能测量报告",
        "",
        f"- 完成状态：`{status['completion_status']}`",
        f"- 执行：60/60，固定 50 ps，LOW/FAST64_SS_W4。",
        "- frame 0 独立于 W4 FFT 汇报。",
        "- MOS corner 为 typical/ss/ff，MIM 分别为 mimcap_typical/mimcap_ss/mimcap_ff。",
        "- 数字逻辑保持固定 TT 时序，逻辑电平及 bridge threshold 随各 corner VDD 缩放。",
        f"- 与 `{BASELINE_ID}` 按相同 seed、corner、CDAC mismatch checksum、事件噪声 checksum 和 FAST64 方法逐条配对。",
        "",
        "## 每个 corner 的结果",
        "",
    ]
    for pvt in PVT_ORDER:
        row = performance[pvt]
        report_lines.append(
            f"- `{pvt}`：hard dynamic 基线 {row['baseline_hard_dynamic_pass_count']}/20 → "
            f"resize {row['hard_dynamic_pass_count']}/20（FAIL→PASS {row['hard_fail_to_pass_count']}，"
            f"PASS→FAIL {row['hard_pass_to_fail_count']}）；SNR budget 基线 "
            f"{row['baseline_snr_budget_pass_count']}/20 → resize {row['snr_budget_pass_count']}/20；"
            f"SNDR 配对中位数 Δ={row['paired_sndr_delta_p50_db']:+.3f} dB；"
            f"ENOB 配对中位数 Δ={row['paired_enob_delta_p50_bit']:+.4f} bit；"
            f"frame0 {row['frame0_pass_count']}/20。"
        )
    report_lines.extend(
        [
            "",
            "## 跨 PVT 结果",
            "",
            f"- TT 通过：{len(tt_pass_seeds)}/20。",
            f"- TT 通过且在 SS、FF 均继续通过：{len(tt_pass_seeds & all_corner_pass_seeds)}/{len(tt_pass_seeds)}。",
            f"- 分类计数：`{json.dumps(classification_counts, ensure_ascii=False)}`。",
            "",
            "## 结论边界",
            "",
            "- 该 MC20 为定向尾部/边缘/机制诊断样本，不是总体良率。",
            "- 本结果是同一固定 MC20 方法下的 resizing 配对动态比较，不形成 MC200、promotion 或 signoff 结论。",
        ]
    )
    (REPORTS / "pvt3_mc20_report_cn.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )
    manifest = seal_manifest()
    print(
        json.dumps(
            {
                "completion_pass": completion_pass,
                "performance": performance,
                "classification_counts": classification_counts,
                "manifest": manifest,
            },
            indent=2,
        )
    )
    return 0 if completion_pass and manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
