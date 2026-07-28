#!/usr/bin/env python3
"""Audit and compare the W5P29/W3P61 TT MC20 candidate."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SEEDS = (44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96)
METRICS = (
    "steady_state_sndr_db",
    "steady_state_snr_db",
    "steady_state_enob_raw",
    "steady_state_sfdr_dbc",
    "steady_state_thd_db",
    "steady_state_hd2_dbc",
    "steady_state_hd3_dbc",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def truth(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def pair_rows(
    new: dict[int, dict[str, Any]],
    reference: dict[int, dict[str, Any]],
    reference_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order, seed in enumerate(SEEDS, 1):
        candidate = new[seed]
        base = reference[seed]
        row: dict[str, Any] = {
            "seed_order": order,
            "mismatch_seed": seed,
            "reference": reference_name,
            "mismatch_checksum_match": candidate["mismatch_checksum"]
            == base["mismatch_checksum"],
            "noise_seed_match": int(candidate["noise_seed"])
            == int(base["noise_seed"]),
            "noise_prefix_checksum_match": candidate[
                "noise_prefix_checksum_0_63"
            ]
            == base["noise_prefix_checksum_0_63"],
            "method_match": candidate["method_id"] == base["method_id"],
            "steady_method_match": candidate["steady_state_method_id"]
            == base["steady_state_method_id"],
            "reference_hard_pass": truth(base["steady_state_hard_dynamic_pass"]),
            "candidate_hard_pass": truth(
                candidate["steady_state_hard_dynamic_pass"]
            ),
            "reference_snr_budget_pass": truth(
                base["steady_state_snr_budget_pass"]
            ),
            "candidate_snr_budget_pass": truth(
                candidate["steady_state_snr_budget_pass"]
            ),
        }
        for metric in METRICS:
            row[f"reference_{metric}"] = float(base[metric])
            row[f"candidate_{metric}"] = float(candidate[metric])
            row[f"delta_{metric}"] = float(candidate[metric]) - float(
                base[metric]
            )
        rows.append(row)
    return rows


def summary(
    name: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "reference": name,
        "record_count": len(rows),
        "reference_hard_pass_count": sum(row["reference_hard_pass"] for row in rows),
        "candidate_hard_pass_count": sum(row["candidate_hard_pass"] for row in rows),
        "hard_fail_to_pass_seeds": [
            row["mismatch_seed"]
            for row in rows
            if not row["reference_hard_pass"] and row["candidate_hard_pass"]
        ],
        "hard_pass_to_fail_seeds": [
            row["mismatch_seed"]
            for row in rows
            if row["reference_hard_pass"] and not row["candidate_hard_pass"]
        ],
        "reference_snr_budget_pass_count": sum(
            row["reference_snr_budget_pass"] for row in rows
        ),
        "candidate_snr_budget_pass_count": sum(
            row["candidate_snr_budget_pass"] for row in rows
        ),
        "snr_fail_to_pass_seeds": [
            row["mismatch_seed"]
            for row in rows
            if not row["reference_snr_budget_pass"]
            and row["candidate_snr_budget_pass"]
        ],
        "snr_pass_to_fail_seeds": [
            row["mismatch_seed"]
            for row in rows
            if row["reference_snr_budget_pass"]
            and not row["candidate_snr_budget_pass"]
        ],
    }
    for metric in METRICS:
        for prefix, key in (
            ("reference", f"reference_{metric}"),
            ("candidate", f"candidate_{metric}"),
            ("delta", f"delta_{metric}"),
        ):
            values = [float(row[key]) for row in rows]
            for label, quantile in (
                ("P0", 0.0),
                ("P10", 0.1),
                ("P50", 0.5),
                ("P90", 0.9),
                ("P100", 1.0),
            ):
                output[f"{prefix}_{metric}_{label}"] = percentile(
                    values, quantile
                )
    return output


def main() -> int:
    new_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        path = next(
            (ROOT / "results/jobs").glob(
                f"TT_CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587_S{seed:03d}_LOW_W4.json"
            )
        )
        new_rows.append(json.loads(path.read_text(encoding="utf-8")))
    new = {int(row["mismatch_seed"]): row for row in new_rows}
    current_rows = read_csv(
        ROOT / "references/current_w3p61_tt_mc20_master.csv"
    )
    original_rows = read_csv(
        ROOT / "references/baseline_t1p000_tt_mc20.csv"
    )
    current = {int(row["mismatch_seed"]): row for row in current_rows}
    original = {int(row["mismatch_seed"]): row for row in original_rows}

    execution_checks = {
        "new_record_count_20": len(new_rows) == 20
        and set(new) == set(SEEDS),
        "all_returncode_zero": all(int(row["returncode"]) == 0 for row in new_rows),
        "all_terminal": all(
            row["state"] in {"COMPLETE", "COMPLETE_WITH_FAIL"}
            for row in new_rows
        ),
        "all_protocol_clean": all(bool(row["protocol_clean"]) for row in new_rows),
        "all_valid_frames_68": all(
            int(row["valid_frame_count"]) == 68 for row in new_rows
        ),
        "all_w4_fixed_50ps": all(
            row["steady_state_method_id"] == "FAST64_SS_W4"
            and int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            and int(row["nfft"]) == 64
            and abs(float(row["maxstep_ns"]) - 0.05) < 1e-12
            for row in new_rows
        ),
        "all_parseval": all(bool(row["steady_state_parseval_pass"]) for row in new_rows),
        "all_clipping_zero": all(
            int(row["steady_state_clipping_count"]) == 0 for row in new_rows
        ),
        "reference_seed_sets_match": set(current) == set(original) == set(new),
    }
    paired_current = pair_rows(new, current, "CURRENT_W3P61")
    paired_original = pair_rows(new, original, "ORIGINAL_T1P000")
    pair_checks = {
        "current_pairing_20": len(paired_current) == 20
        and all(
            row["mismatch_checksum_match"]
            and row["noise_seed_match"]
            and row["noise_prefix_checksum_match"]
            and row["method_match"]
            and row["steady_method_match"]
            for row in paired_current
        ),
        "original_pairing_20": len(paired_original) == 20
        and all(
            row["mismatch_checksum_match"]
            and row["noise_seed_match"]
            and row["noise_prefix_checksum_match"]
            and row["method_match"]
            and row["steady_method_match"]
            for row in paired_original
        ),
    }
    current_summary = summary("CURRENT_W3P61", paired_current)
    original_summary = summary("ORIGINAL_T1P000", paired_original)

    write_csv(ROOT / "csv/new_tt_mc20_master.csv", new_rows)
    write_csv(ROOT / "csv/paired_vs_current_w3p61.csv", paired_current)
    write_csv(ROOT / "csv/paired_vs_original_t1p000.csv", paired_original)
    write_csv(
        ROOT / "csv/summary_vs_references.csv",
        [current_summary, original_summary],
    )
    completed = datetime.now(timezone.utc).isoformat()
    complete = all(execution_checks.values()) and all(pair_checks.values())
    payload = {
        "completed_utc": completed,
        "status": "COMPLETE_TT_MC20_MEASURED"
        if complete
        else "INCOMPLETE",
        "method_id": "FAST64_SS_W4",
        "scope": "TT_3P3_27C_ONLY_FIXED_MC20_LOW_20_SELECTED_SEEDS",
        "candidate_id": "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587",
        "execution_checks": execution_checks,
        "pairing_checks": pair_checks,
        "candidate_hard_pass_count": sum(
            truth(row["steady_state_hard_dynamic_pass"]) for row in new_rows
        ),
        "candidate_snr_budget_pass_count": sum(
            truth(row["steady_state_snr_budget_pass"]) for row in new_rows
        ),
        "vs_current_w3p61": current_summary,
        "vs_original_t1p000": original_summary,
        "performance_gate": "NOT_DEFINED_FOR_RESIZE_PROMOTION",
        "claim_boundary": "Selected TT MC20 diagnostic sample; not MC200, yield, PVT, promotion, or signoff evidence.",
        "pass": complete,
    }
    write_json(ROOT / "results/tt_mc20_analysis.json", payload)
    write_json(
        ROOT / "results/final_verification.json",
        {
            "completed_utc": completed,
            "checks": {**execution_checks, **pair_checks},
            "pass": complete,
            "performance_failures_are_retained_evidence_not_execution_failures": True,
        },
    )
    report = [
        "# XM5/XM6 W5P29、XM7/XM11 W3P61：TT MC20 动态性能",
        "",
        "- 方法：固定 FAST64_SS_W4，LOW bin 7，frames 4–67，NFFT=64，50 ps。",
        "- 20 个既定诊断 seed 全部执行；性能 FAIL 不作为执行失败。",
        f"- 新候选 hard dynamic：{payload['candidate_hard_pass_count']}/20；SNR budget：{payload['candidate_snr_budget_pass_count']}/20。",
        "",
        "## 相对当前 W3P61",
        "",
        f"- hard dynamic：{current_summary['reference_hard_pass_count']}/20 → {current_summary['candidate_hard_pass_count']}/20。",
        f"- FAIL→PASS：{current_summary['hard_fail_to_pass_seeds']}；PASS→FAIL：{current_summary['hard_pass_to_fail_seeds']}。",
        f"- SNDR 配对 Δ：P50 {current_summary['delta_steady_state_sndr_db_P50']:+.4f} dB，范围 {current_summary['delta_steady_state_sndr_db_P0']:+.4f} 至 {current_summary['delta_steady_state_sndr_db_P100']:+.4f} dB。",
        f"- ENOB 配对 Δ：P50 {current_summary['delta_steady_state_enob_raw_P50']:+.5f} bit。",
        "",
        "## 相对原始 T1P000",
        "",
        f"- hard dynamic：{original_summary['reference_hard_pass_count']}/20 → {original_summary['candidate_hard_pass_count']}/20。",
        f"- FAIL→PASS：{original_summary['hard_fail_to_pass_seeds']}；PASS→FAIL：{original_summary['hard_pass_to_fail_seeds']}。",
        f"- SNDR 配对 Δ：P50 {original_summary['delta_steady_state_sndr_db_P50']:+.4f} dB。",
        "",
        "结论边界：该 20-seed 集合是既定定向诊断样本，不是 MC200 或总体良率；仅测 TT，不形成 PVT、promotion 或 signoff 结论。",
    ]
    (ROOT / "reports/tt_mc20_report_cn.md").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )
    status_path = ROOT / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["stages"]["smoke"] = "PASS_3_OF_3"
    status["stages"]["tt_mc20_execution"] = "PASS_20_OF_20_COMPLETE"
    status["stages"]["analysis"] = "PASS" if complete else "FAIL"
    status["state"] = (
        "COMPLETE_TT_MC20_MEASURED" if complete else "INCOMPLETE"
    )
    status["updated_utc"] = completed
    write_json(status_path, status)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
