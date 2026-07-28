#!/usr/bin/env python3
"""Build a standalone audited TT-only MC20 result package."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / (
    "A44_CMP_XM5_XM6_XM7_XM11_RESIZE_TT_MC20_LOW_"
    "FAST64_SS_W4_FIXED50PS_20260727_R1"
)
TT = "TT_3P3_27C"
SEEDS = (44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96)
METRICS = {
    "SNR_dB": "steady_state_snr_db",
    "SNDR_dB": "steady_state_sndr_db",
    "ENOB_raw_bit": "steady_state_enob_raw",
    "SFDR_dBc": "steady_state_sfdr_dbc",
    "THD_dB": "steady_state_thd_db",
    "HD2_dBc": "steady_state_hd2_dbc",
    "HD3_dBc": "steady_state_hd3_dbc",
}
PAIR_FIELDS = (
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
        for field in row:
            if field not in fields:
                fields.append(field)
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


def csv_bool(value: object) -> bool:
    return str(value).strip().lower() == "true"


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q, method="linear"))


def save_figure(fig: plt.Figure, name: str) -> None:
    plots = OUT / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    fig.savefig(plots / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(plots / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def seal_manifest() -> dict[str, object]:
    excluded = {"manifest_sha256.csv", "manifest_audit.json"}
    files = sorted(
        path
        for path in OUT.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    rows = [
        {
            "relative_path": path.relative_to(OUT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    write_csv(OUT / "manifest_sha256.csv", rows)
    mismatches = []
    for row in rows:
        path = OUT / str(row["relative_path"])
        if path.stat().st_size != int(row["bytes"]) or sha256_file(path) != row["sha256"]:
            mismatches.append(str(row["relative_path"]))
    payload = {
        "completed_utc": utc_now(),
        "manifest_record_count": len(rows),
        "manifest_sha256": sha256_file(OUT / "manifest_sha256.csv"),
        "mismatches": mismatches,
        "pass": not mismatches,
    }
    write_json(OUT / "manifest_audit.json", payload)
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for relative in (
        "config",
        "csv/job_codes",
        "jobs",
        "logs",
        "manifests",
        "netlists",
        "plots",
        "references",
        "reports",
        "results/jobs",
    ):
        (OUT / relative).mkdir(parents=True, exist_ok=True)

    matrix = [
        row
        for row in read_csv(ROOT / "manifests/job_matrix.csv")
        if row["pvt"] == TT
    ]
    if len(matrix) != 20:
        raise RuntimeError(f"expected 20 TT matrix rows, got {len(matrix)}")

    candidate: list[dict[str, object]] = []
    all_codes: list[dict[str, object]] = []
    for row in matrix:
        job_id = row["job_id"]
        result_path = ROOT / "results/jobs" / f"{job_id}.json"
        code_path = ROOT / "csv/job_codes" / f"{job_id}.csv"
        if not result_path.is_file() or not code_path.is_file():
            raise RuntimeError(f"missing TT evidence for {job_id}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        candidate.append(
            {
                "seed_order": SEEDS.index(int(result["mismatch_seed"])) + 1,
                "seed_group": row["category"],
                **result,
            }
        )
        rows = read_csv(code_path)
        for code_row in rows:
            all_codes.append({"pvt": TT, **code_row})

        shutil.copy2(result_path, OUT / "results/jobs" / result_path.name)
        shutil.copy2(code_path, OUT / "csv/job_codes" / code_path.name)
        deck_path = ROOT / str(result["deck"])
        log_path = ROOT / str(result["log"])
        shutil.copy2(deck_path, OUT / "jobs" / deck_path.name)
        shutil.copy2(log_path, OUT / "logs" / log_path.name)

    candidate.sort(key=lambda row: SEEDS.index(int(row["mismatch_seed"])))
    all_codes.sort(
        key=lambda row: (
            SEEDS.index(int(row["mismatch_seed"])),
            int(row["frame_index"]),
        )
    )
    retained = [row for row in all_codes if row["retained"].lower() == "true"]

    baseline_rows = [
        row
        for row in read_csv(ROOT / "references/baseline_t1p000_pvt3_mc20_master.csv")
        if row["pvt"] == TT
    ]
    baseline = {int(row["mismatch_seed"]): row for row in baseline_rows}
    if len(baseline_rows) != 20 or len(baseline) != 20:
        raise RuntimeError("baseline TT reference is not 20 unique seeds")

    pairing_rows: list[dict[str, object]] = []
    paired: list[dict[str, object]] = []
    for row in candidate:
        seed = int(row["mismatch_seed"])
        reference = baseline[seed]
        checks = {
            field: str(row[field]) == str(reference[field])
            for field in PAIR_FIELDS
        }
        pairing_rows.append(
            {
                "mismatch_seed": seed,
                **{f"match_{field}": value for field, value in checks.items()},
                "pass": all(checks.values()),
            }
        )

        baseline_hard = csv_bool(reference["steady_state_hard_dynamic_pass"])
        resized_hard = bool(row["steady_state_hard_dynamic_pass"])
        baseline_snr = csv_bool(reference["steady_state_snr_budget_pass"])
        resized_snr = bool(row["steady_state_snr_budget_pass"])
        output: dict[str, object] = {
            "seed_order": row["seed_order"],
            "seed_group": row["seed_group"],
            "mismatch_seed": seed,
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
            "resized_codes_all_checksum": row["codes_all_checksum"],
            "baseline_codes_retained_checksum": reference["codes_retained_checksum"],
            "resized_codes_retained_checksum": row["codes_retained_checksum"],
        }
        for label, field in METRICS.items():
            baseline_value = float(reference[field])
            resized_value = float(row[field])
            output[f"baseline_{label}"] = baseline_value
            output[f"resized_{label}"] = resized_value
            output[f"delta_resize_minus_baseline_{label}"] = resized_value - baseline_value
        paired.append(output)

    pairing_pass = len(pairing_rows) == 20 and all(
        bool(row["pass"]) for row in pairing_rows
    )
    execution_checks = {
        "tt_records_20": len(candidate) == 20,
        "all_code_rows_1360": len(all_codes) == 1360,
        "w4_code_rows_1280": len(retained) == 1280,
        "all_terminal": all(
            row["state"] in {"COMPLETE", "COMPLETE_WITH_FAIL"} for row in candidate
        ),
        "all_returncode_zero": all(int(row["returncode"]) == 0 for row in candidate),
        "all_protocol_clean": all(bool(row["protocol_clean"]) for row in candidate),
        "all_valid_frames_68": all(int(row["valid_frame_count"]) == 68 for row in candidate),
        "all_parseval": all(bool(row["steady_state_parseval_pass"]) for row in candidate),
        "all_w4_fixed_50ps": all(
            int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            and abs(float(row["maxstep_ns"]) - 0.05) < 1e-15
            for row in candidate
        ),
        "paired_method_noise_mismatch_20": pairing_pass,
    }
    execution_pass = all(execution_checks.values())

    summary: dict[str, object] = {
        "pvt": TT,
        "record_count": 20,
        "baseline_hard_dynamic_pass_count": sum(
            bool(row["baseline_hard_dynamic_pass"]) for row in paired
        ),
        "resized_hard_dynamic_pass_count": sum(
            bool(row["resized_hard_dynamic_pass"]) for row in paired
        ),
        "hard_fail_to_pass_count": sum(
            row["hard_dynamic_transition"] == "FAIL_TO_PASS" for row in paired
        ),
        "hard_pass_to_fail_count": sum(
            row["hard_dynamic_transition"] == "PASS_TO_FAIL" for row in paired
        ),
        "baseline_snr_budget_pass_count": sum(
            bool(row["baseline_snr_budget_pass"]) for row in paired
        ),
        "resized_snr_budget_pass_count": sum(
            bool(row["resized_snr_budget_pass"]) for row in paired
        ),
        "snr_fail_to_pass_count": sum(
            row["snr_budget_transition"] == "FAIL_TO_PASS" for row in paired
        ),
        "snr_pass_to_fail_count": sum(
            row["snr_budget_transition"] == "PASS_TO_FAIL" for row in paired
        ),
        "frame0_pass_count": sum(
            bool(row["first_conversion_protocol_pass"]) for row in candidate
        ),
    }
    for label in METRICS:
        baseline_values = [float(row[f"baseline_{label}"]) for row in paired]
        resized_values = [float(row[f"resized_{label}"]) for row in paired]
        delta_values = [
            float(row[f"delta_resize_minus_baseline_{label}"]) for row in paired
        ]
        for q in (0, 10, 50, 90, 100):
            summary[f"baseline_{label}_P{q}"] = percentile(baseline_values, q)
            summary[f"resized_{label}_P{q}"] = percentile(resized_values, q)
            summary[f"delta_{label}_P{q}"] = percentile(delta_values, q)

    write_csv(OUT / "manifests/tt_job_matrix.csv", matrix)
    write_csv(OUT / "csv/tt_mc20_master.csv", candidate)
    write_csv(OUT / "csv/tt_mc20_codes_all.csv", all_codes)
    write_csv(OUT / "csv/tt_mc20_codes_w4.csv", retained)
    write_csv(OUT / "csv/tt_mc20_paired_vs_t1p000.csv", paired)
    write_csv(OUT / "csv/tt_mc20_summary.csv", [summary])
    write_csv(OUT / "results/tt_pairing_audit.csv", pairing_rows)
    write_json(
        OUT / "results/tt_pairing_audit.json",
        {
            "completed_utc": utc_now(),
            "record_count": len(pairing_rows),
            "checks": PAIR_FIELDS,
            "candidate_comparator_intentionally_differs": True,
            "pass": pairing_pass,
        },
    )
    write_json(
        OUT / "results/final_verification.json",
        {
            "completed_utc": utc_now(),
            "checks": execution_checks,
            "pass": execution_pass,
            "performance_failures_are_retained_evidence_not_execution_failures": True,
        },
    )

    shutil.copy2(
        ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice",
        OUT / "netlists/candidate_resized_comparator.subckt.spice",
    )
    shutil.copy2(
        ROOT / "references/baseline_t1p000_comparator.subckt.spice",
        OUT / "references/baseline_t1p000_comparator.subckt.spice",
    )
    write_csv(OUT / "references/baseline_t1p000_tt_mc20.csv", baseline_rows)
    for name in (
        "setup_audit.json",
        "pvt_binding_static_audit.json",
        "pvt_pairing_audit.json",
        "smoke_audit_pvt3.json",
    ):
        shutil.copy2(ROOT / "results" / name, OUT / "references" / name)

    contract = {
        "campaign": OUT.name,
        "created_utc": utc_now(),
        "scope": "TT_3P3_27C_ONLY_SELECTED_DIAGNOSTIC_MC20",
        "candidate": {
            "candidate_id": "CMP_XM5_XM6_XM7_XM11_RESIZE",
            "comparator_sha256": sha256_file(
                OUT / "netlists/candidate_resized_comparator.subckt.spice"
            ),
            "resized_widths_um": {
                "XM5": 5.6316,
                "XM6": 5.6316,
                "XM7": 16.8587,
                "XM11": 16.8587,
            },
        },
        "baseline": {
            "candidate_id": "CMP_IN_A2P25_W_T1P000",
            "comparator_sha256": sha256_file(
                OUT / "references/baseline_t1p000_comparator.subckt.spice"
            ),
        },
        "method": {
            "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
            "steady_state_method_id": "FAST64_SS_W4",
            "sample_rate_hz": 2_000_000.0,
            "fin_hz": 218_750.0,
            "coherent_bin": 7,
            "total_frames": 68,
            "frame0_independent_gate": True,
            "startup_diagnostic_frames": [1, 3],
            "retained_frames": [4, 67],
            "nfft": 64,
            "window": "rectangular",
            "maxstep_ps": 50,
            "noise_seed_rule": "100000_plus_mismatch_seed",
        },
        "population": {
            "seeds": list(SEEDS),
            "record_count": 20,
            "selected_diagnostic_sample_not_yield": True,
        },
        "scope_change": {
            "requested_after_tt_20_completed": True,
            "ss_ff_excluded_from_this_package_and_all_claims": True,
            "partial_ss_attempt_evidence_retained_only_in_source_working_package": str(ROOT),
        },
    }
    write_json(OUT / "config/tt_mc20_contract.json", contract)

    x = np.arange(len(SEEDS))
    baseline_sndr = [float(row["baseline_SNDR_dB"]) for row in paired]
    resized_sndr = [float(row["resized_SNDR_dB"]) for row in paired]
    delta_sndr = [
        float(row["delta_resize_minus_baseline_SNDR_dB"]) for row in paired
    ]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.plot(x, baseline_sndr, marker="o", label="T1P000 baseline")
    ax.plot(x, resized_sndr, marker="o", label="XM5/6/7/11 resize")
    ax.axhline(46.91, color="#333333", linestyle="--", label="SNDR gate 46.91 dB")
    ax.set_xticks(x, [str(seed) for seed in SEEDS], rotation=45)
    ax.set_xlabel("Paired mismatch seed")
    ax.set_ylabel("SNDR (dB)")
    ax.set_title("TT MC20 paired SNDR")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    save_figure(fig, "tt_mc20_paired_sndr")

    colors = ["#2a9d8f" if value >= 0 else "#c83e4d" for value in delta_sndr]
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(x, delta_sndr, color=colors)
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.set_xticks(x, [str(seed) for seed in SEEDS], rotation=45)
    ax.set_xlabel("Paired mismatch seed")
    ax.set_ylabel("Resize minus baseline SNDR (dB)")
    ax.set_title("TT MC20 paired SNDR delta")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, "tt_mc20_paired_sndr_delta")

    transition_map = {
        "FAIL_STAYS_FAIL": 0,
        "PASS_TO_FAIL": 1,
        "PASS_STAYS_PASS": 2,
        "FAIL_TO_PASS": 3,
    }
    transition_label = {
        "FAIL_STAYS_FAIL": "FAIL→FAIL",
        "PASS_TO_FAIL": "PASS→FAIL",
        "PASS_STAYS_PASS": "PASS→PASS",
        "FAIL_TO_PASS": "FAIL→PASS",
    }
    values = np.asarray(
        [[transition_map[str(row["hard_dynamic_transition"])]] for row in paired]
    )
    fig, ax = plt.subplots(figsize=(3.8, 8.0))
    cmap = matplotlib.colors.ListedColormap(
        ["#8c8c8c", "#c83e4d", "#4c78a8", "#2a9d8f"]
    )
    ax.imshow(values, cmap=cmap, vmin=0, vmax=3, aspect="auto")
    ax.set_xticks([0], ["Hard dynamic"])
    ax.set_yticks(range(len(SEEDS)), [str(seed) for seed in SEEDS])
    ax.set_ylabel("Mismatch seed")
    ax.set_title("TT baseline → resize transition")
    for index, row in enumerate(paired):
        ax.text(
            0,
            index,
            transition_label[str(row["hard_dynamic_transition"])],
            ha="center",
            va="center",
            fontsize=6,
            color="white",
        )
    fig.tight_layout()
    save_figure(fig, "tt_mc20_hard_transition")

    fail_to_pass = [
        int(row["mismatch_seed"])
        for row in paired
        if row["hard_dynamic_transition"] == "FAIL_TO_PASS"
    ]
    pass_to_fail = [
        int(row["mismatch_seed"])
        for row in paired
        if row["hard_dynamic_transition"] == "PASS_TO_FAIL"
    ]
    status = {
        "campaign": OUT.name,
        "completed_utc": utc_now(),
        "scope": "TT_ONLY_FIXED_MC20_LOW_FAST64_SS_W4_FIXED50PS",
        "execution_status": "PASS_TT_20_OF_20_COMPLETE" if execution_pass else "INCOMPLETE",
        "pairing_status": "PASS_20_OF_20" if pairing_pass else "FAIL",
        "performance_status": "TT_PASS_COUNT_IMPROVED_WITH_REGRESSION_PRESENT",
        "performance": summary,
        "hard_fail_to_pass_seeds": fail_to_pass,
        "hard_pass_to_fail_seeds": pass_to_fail,
        "scope_boundary": {
            "ss_ff_measured_or_claimed": False,
            "mc200_yield_claimed": False,
            "promotion_claimed": False,
            "signoff_claimed": False,
        },
    }
    write_json(OUT / "STATUS.json", status)

    report = [
        "# XM5/XM6/XM7/XM11 resizing：TT MC20 动态性能",
        "",
        f"- 执行：TT 20/20；配对审计：{'PASS' if pairing_pass else 'FAIL'}。",
        "- 方法：FAST64_V2，frame0 独立；frames 4–67 做 64 点矩形窗 FFT；50 ps；LOW bin 7。",
        f"- hard dynamic：基线 {summary['baseline_hard_dynamic_pass_count']}/20 → resize {summary['resized_hard_dynamic_pass_count']}/20。",
        f"- FAIL→PASS：{fail_to_pass}；PASS→FAIL：{pass_to_fail}。",
        f"- SNR budget：基线 {summary['baseline_snr_budget_pass_count']}/20 → resize {summary['resized_snr_budget_pass_count']}/20。",
        f"- SNDR 配对 Δ：P50 {summary['delta_SNDR_dB_P50']:+.4f} dB；范围 {summary['delta_SNDR_dB_P0']:+.4f} 到 {summary['delta_SNDR_dB_P100']:+.4f} dB。",
        f"- ENOB 配对 Δ：P50 {summary['delta_ENOB_raw_bit_P50']:+.5f} bit。",
        f"- frame0 protocol：{summary['frame0_pass_count']}/20。",
        "",
        "结论边界：该 20-seed 集合是既定的定向诊断样本，不是 MC200 或总体良率；",
        "按用户范围，本包仅汇总 TT，不包含 SS/FF 性能结论，也不形成 promotion/signoff。",
        "",
    ]
    (OUT / "reports/tt_mc20_report_cn.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    manifest = seal_manifest()
    print(
        json.dumps(
            {
                "output": str(OUT),
                "execution_pass": execution_pass,
                "pairing_pass": pairing_pass,
                "summary": summary,
                "manifest": manifest,
            },
            indent=2,
        )
    )
    return 0 if execution_pass and pairing_pass and manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
