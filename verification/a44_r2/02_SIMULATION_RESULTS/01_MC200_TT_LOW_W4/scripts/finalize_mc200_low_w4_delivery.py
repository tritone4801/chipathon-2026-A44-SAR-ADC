#!/usr/bin/env python3
"""Finalize the LOW-only W4 MC200 campaign without overstating signoff."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fast64_v2_common import (
    CSV_DIR,
    MANIFEST_DIR,
    RESULT_DIR,
    ROOT,
    read_csv,
    sha256_file,
    write_json_atomic,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def load_json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def percentile_value(
    rows: list[dict[str, str]], metric: str, percentile: int
) -> float:
    return float(
        next(
            row["value"]
            for row in rows
            if row["metric"] == metric
            and int(float(row["percentile"])) == percentile
        )
    )


def main() -> int:
    setup = load_json("results/setup_audit.json")
    execution = load_json("results/execution_audit_mc200_low_w4.json")
    population = load_json("results/population_summary_mc200_low_w4.json")
    plots = load_json("results/plot_audit_mc200_low_w4.json")
    visual_review = load_json("results/visual_review_mc200_low_w4.json")
    master = read_csv(CSV_DIR / "steady_state_master_mc200_low_w4.csv")
    percentiles = read_csv(CSV_DIR / "population_percentiles_w4.csv")
    transition = read_csv(CSV_DIR / "w0_to_w4_method_transition_mc200_low.csv")
    representatives = read_csv(CSV_DIR / "representative_records_w4.csv")
    matrix = read_csv(MANIFEST_DIR / "job_matrix.csv")
    frozen_inputs = read_csv(MANIFEST_DIR / "input_manifest_sha256.csv")
    frozen_input_mismatches = [
        row["relative_path"]
        for row in frozen_inputs
        if not (ROOT / row["relative_path"]).is_file()
        or sha256_file(ROOT / row["relative_path"]) != row["sha256"]
    ]

    hard_pass_count = int(population["steady_state_hard_dynamic_pass_count"])
    first_pass_count = int(population["first_conversion_protocol_pass_count"])
    combined_pass_count = int(population["combined_system_pass_count"])
    budget_pass_count = int(population["steady_state_snr_budget_pass_count"])
    w0_exact_count = int(population["historical_w0_exact_record_count"])
    w0_different_count = int(population["historical_w0_different_record_count"])
    w0_different_frames = int(population["historical_w0_different_frame_count"])
    low_record_95pct = hard_pass_count >= 190

    checks = {
        "setup_freeze_pass": bool(setup.get("pass")),
        "formal_execution_pass": bool(execution.get("pass")),
        "population_200": len(master) == 200,
        "seed_set_1_to_200": {
            int(row["mismatch_seed"]) for row in master
        }
        == set(range(1, 201)),
        "codes_all_13600": (
            len(read_csv(CSV_DIR / "codes_all_13600.csv")) == 13_600
        ),
        "codes_retained_12800": (
            len(read_csv(CSV_DIR / "codes_fft_retained_12800.csv")) == 12_800
        ),
        "first_conversion_path_1600": (
            len(read_csv(CSV_DIR / "first_conversion_path_1600.csv")) == 1_600
        ),
        "startup_pairs_800": (
            len(read_csv(CSV_DIR / "startup_periodic_pairs_800.csv")) == 800
        ),
        "method_transition_200": len(transition) == 200,
        "percentiles_complete": len(percentiles) == 44,
        "representatives_present": len(representatives) == 5,
        "plot_audit_pass": bool(plots.get("pass")),
        "manual_visual_review_pass": bool(visual_review.get("pass")),
        "plot_count_7": len(plots.get("inventory", [])) == 7,
        "frozen_pre_execution_input_manifest_unchanged": not frozen_input_mismatches,
        "formal_job_matrix_200": len(matrix) == 200,
        "all_formal_records_noise_on": all(
            row["noise_mode"] == "ON" for row in master
        ),
        "all_formal_records_low": all(row["band"] == "LOW" for row in master),
        "all_formal_records_w4": all(
            int(row["warmup_frames"]) == 4
            and int(row["total_frames"]) == 68
            and int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            for row in master
        ),
        "all_formal_records_50ps_robust_gear": all(
            abs(float(row["maxstep_ns"]) - 0.05) < 1e-15 for row in master
        )
        and all(
            int(row["maxstep_ps"]) == 50
            and row["solver_profile"] == "ROBUST_GEAR"
            for row in matrix
        ),
        "all_logs_use_hsa_compatibility": bool(
            execution.get("checks", {}).get("all_ngspice_compatibility_hsa")
        ),
        "all_equation_parseval_checks_pass": all(
            truth(row["steady_state_parseval_pass"]) for row in master
        ),
    }
    delivery_complete = all(checks.values())
    status = {
        "campaign": ROOT.name,
        "delivery_status": (
            "DELIVERY_COMPLETE" if delivery_complete else "DELIVERY_INCOMPLETE"
        ),
        "execution_status": execution["status"],
        "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        "steady_state_method_id": "FAST64_SS_W4",
        "scope": "MC200_LOW_ONLY",
        "formal_record_count": len(master),
        "all_frame_count": 13_600,
        "retained_fft_code_count": 12_800,
        "first_conversion_protocol_pass_count": first_pass_count,
        "first_conversion_protocol_fail_count": 200 - first_pass_count,
        "steady_state_hard_dynamic_pass_count": hard_pass_count,
        "steady_state_hard_dynamic_fail_count": 200 - hard_pass_count,
        "steady_state_snr_budget_pass_count": budget_pass_count,
        "steady_state_snr_budget_fail_count": 200 - budget_pass_count,
        "combined_system_pass_count": combined_pass_count,
        "combined_system_fail_count": 200 - combined_pass_count,
        "low_record_95_percent_hard_pass_threshold_met": low_record_95pct,
        "low_record_performance_classification": (
            "LOW_RECORD_POPULATION_AT_LEAST_95_PERCENT_HARD_PASS"
            if low_record_95pct
            else "LOW_RECORD_POPULATION_BELOW_95_PERCENT_HARD_PASS"
        ),
        "historical_w0_exact_record_count": w0_exact_count,
        "historical_w0_different_record_count": w0_different_count,
        "historical_w0_different_frame_count": w0_different_frames,
        "post_execution_visual_only_correction": visual_review[
            "visual_only_correction"
        ],
        "frozen_input_manifest_mismatches": frozen_input_mismatches,
        "sndr_percentiles_db": {
            f"P{value}": percentile_value(
                percentiles, "steady_state_sndr_db", value
            )
            for value in (1, 5, 10, 50)
        },
        "enob_percentiles_bit": {
            f"P{value}": percentile_value(
                percentiles, "steady_state_enob_raw", value
            )
            for value in (1, 5, 10, 50)
        },
        "completion_checks": checks,
        "non_claims": [
            "LOW-only results are not a two-band die-level MC200 yield.",
            "The W4 population does not overwrite the historical W0 MC200.",
            "W4-versus-W0 differences are a method transition, not automatic circuit improvement.",
            "Noise-on frame0/frame64 code equality is diagnostic only.",
            "No production, layout, PEX, silicon, tapeout, or full signoff claim is made.",
        ],
        "completed_utc": utc_now(),
    }
    write_json_atomic(ROOT / "STATUS.json", status)
    write_json_atomic(
        RESULT_DIR / "completion_audit.json",
        {
            "status": (
                "PASS_COMPLETION_AUDIT"
                if delivery_complete
                else "FAIL_COMPLETION_AUDIT"
            ),
            "pass": delivery_complete,
            "checks": checks,
            "manifest_note": (
                "The final package manifest is generated after this file and "
                "audited independently in manifest_audit.json."
            ),
        },
    )

    report = f"""# A44 MC200 LOW FAST64_SS_W4 全量重测报告

## 1. 结论

- 交付状态：`{status['delivery_status']}`
- 执行状态：`{status['execution_status']}`
- 正式总体：200 个 mismatch seed，仅 LOW；
- 方法：`FAST64_SS_W4`，每条68帧，FFT仅使用 frame 4–67；
- first-conversion protocol PASS：{first_pass_count}/200；
- steady-state hard dynamic PASS：{hard_pass_count}/200；
- SNR budget PASS：{budget_pass_count}/200；
- combined system PASS：{combined_pass_count}/200；
- LOW记录级95% hard-pass阈值：{'满足' if low_record_95pct else '未满足'}。

该95%结果只描述LOW记录，不是LOW/NEAR双频die-level yield，也不是生产signoff。

## 2. 固定测量与方程

- TT/3.3 V/27 C；
- 3.0 Vpp,diff；
- Fs=2 MS/s，LOW bin=7，fin=218.75 kHz；
- phase=pi/4；
- event noise seed=`100000+mismatch_seed`；
- `ROBUST_GEAR`，maxstep=50 ps；
- ngspice兼容模式固定为`hs a`，包内`.spiceinit`由执行器显式绑定；
- rectangular window；
- one-sided `rfft/N`功率谱；
- SNR=`10log10(Pfund/Pnoise)`；
- SNDR=`10log10(Pfund/(Pnoise+Pharm))`；
- ENOBraw=`(SNDR-1.76)/6.02`；
- H2至H5折叠后从noise bins中排除；
- 每条记录均执行Parseval检查。

## 3. W4总体分位数

| 指标 | P1 | P5 | P10 | P50 |
|---|---:|---:|---:|---:|
| SNDR/dB | {status['sndr_percentiles_db']['P1']:.6f} | {status['sndr_percentiles_db']['P5']:.6f} | {status['sndr_percentiles_db']['P10']:.6f} | {status['sndr_percentiles_db']['P50']:.6f} |
| ENOB/bit | {status['enob_percentiles_bit']['P1']:.6f} | {status['enob_percentiles_bit']['P5']:.6f} | {status['enob_percentiles_bit']['P10']:.6f} | {status['enob_percentiles_bit']['P50']:.6f} |

分位数使用 NumPy linear/type-7 方法。

## 4. W0历史对照

- 与当前历史W0前64帧码流完全相同：{w0_exact_count}/200；
- 存在差异的记录：{w0_different_count}/200；
- 差异帧总数：{w0_different_frames}。

W0与W4不能合并为同一分布。W4排除frame0–3后形成新的稳态测量总体；
这一变化不能自动解释为电路性能改善。

失配权重与event-noise前64帧校验和在200条记录上均与历史输入一致。
11条码流差异属于本次重算相对历史W0的可复现性观察，不被改写成方法收益。

## 5. first-conversion边界

frame0继续执行protocol、completion、path和DOUT timing检查，但本轮为noise-ON。
因此frame0与frame64的code相等只作为诊断信息，不构成硬判据。

## 6. 主要证据

- `STATUS.json`
- `csv/steady_state_master_mc200_low_w4.csv`
- `csv/codes_all_13600.csv`
- `csv/codes_fft_retained_12800.csv`
- `csv/first_conversion_path_1600.csv`
- `csv/startup_periodic_pairs_800.csv`
- `csv/w0_to_w4_method_transition_mc200_low.csv`
- `csv/population_percentiles_w4.csv`
- `plots/plot_inventory.csv`
- `results/execution_audit_mc200_low_w4.json`
- `results/visual_review_mc200_low_w4.json`
- `results/completion_audit.json`
- `manifest_sha256.csv`
- `manifest_audit.json`

## 7. 非声明

- 本结果不是双频die-level MC200 yield；
- 不覆盖历史W0结果；
- 代表频谱中一个精确零功率bin仅在绘图层标记为负无穷，未改变FFT功率或性能指标；
- 不构成生产、版图、PEX、硅后、tapeout或完整signoff声明。
"""
    report_path = ROOT / "reports/A44_MC200_LOW_FAST64_SS_W4_REPORT_CN.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "delivery_complete": delivery_complete,
                "hard_pass_count": hard_pass_count,
                "first_conversion_pass_count": first_pass_count,
                "combined_pass_count": combined_pass_count,
            },
            sort_keys=True,
        )
    )
    return 0 if delivery_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
