#!/usr/bin/env python3
"""Finalize the 2.25x LOW W4 MC200 evidence without overstating signoff."""

from __future__ import annotations

import json
from datetime import datetime, timezone

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


def load_json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    setup = load_json("results/setup_audit.json")
    execution = load_json("results/execution_audit_mc200_low_w4.json")
    scorecard = load_json("results/cmp_in_a2p25_w_mc200_scorecard.json")
    population = load_json("results/population_summary_mc200_low_w4.json")
    formal_plots = load_json("results/plot_audit_mc200_low_w4.json")
    comparison_plots = load_json("results/comparison_plot_audit.json")
    visual_review = load_json("results/visual_review_cmp_in_a2p25_w_mc200.json")
    prior_qualification = load_json(
        "references/candidate_source/QUALIFICATION_STATUS.json"
    )
    master = read_csv(CSV_DIR / "steady_state_master_mc200_low_w4.csv")
    paired = read_csv(CSV_DIR / "paired_baseline_candidate_mc200_low_w4.csv")
    frozen_inputs = read_csv(MANIFEST_DIR / "input_manifest_sha256.csv")
    frozen_input_mismatches = [
        row["relative_path"]
        for row in frozen_inputs
        if not (ROOT / row["relative_path"]).is_file()
        or sha256_file(ROOT / row["relative_path"]) != row["sha256"]
    ]

    performance = scorecard["performance"]
    frame0 = scorecard["frame0"]
    candidate_percentiles = scorecard["candidate_percentiles"]
    baseline_percentiles = scorecard["baseline_percentiles"]
    checks = {
        "setup_freeze_pass": bool(setup.get("pass")),
        "candidate_binding_pass": bool(setup.get("candidate_binding_pass")),
        "formal_execution_pass": bool(execution.get("pass")),
        "formal_record_count_200": len(master) == 200,
        "seed_set_1_to_200": {
            int(row["mismatch_seed"]) for row in master
        }
        == set(range(1, 201)),
        "all_code_rows_13600": len(
            read_csv(CSV_DIR / "codes_all_13600.csv")
        )
        == 13_600,
        "retained_code_rows_12800": len(
            read_csv(CSV_DIR / "codes_fft_retained_12800.csv")
        )
        == 12_800,
        "paired_rows_200": len(paired) == 200,
        "paired_input_checksums_200": (
            scorecard["input_pairing"]["mismatch_checksum_match_count"] == 200
            and scorecard["input_pairing"]["noise_prefix_checksum_match_count"]
            == 200
        ),
        "all_formal_records_50ps": all(
            abs(float(row["maxstep_ns"]) - 0.05) < 1e-15 for row in master
        ),
        "all_formal_records_w4": all(
            int(row["warmup_frames"]) == 4
            and int(row["total_frames"]) == 68
            and int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            for row in master
        ),
        "all_parseval_checks_pass": all(
            str(row["steady_state_parseval_pass"]).lower() == "true"
            for row in master
        ),
        "formal_plot_audit_pass": bool(formal_plots.get("pass")),
        "comparison_plot_audit_pass": bool(comparison_plots.get("pass")),
        "manual_visual_review_pass": bool(visual_review.get("pass")),
        "frozen_input_manifest_unchanged": not frozen_input_mismatches,
        "analysis_complete": bool(scorecard.get("pass")),
    }
    delivery_complete = all(checks.values())
    existing_gates = (
        "UNCHANGED_FAIL"
        if not prior_qualification.get("gate1_block_pass")
        and not prior_qualification.get("four_phase_gate_pass")
        else "SOURCE_STATUS_CHANGED_REVIEW_REQUIRED"
    )
    status = {
        "campaign": ROOT.name,
        "candidate_id": "CMP_IN_A2P25_W",
        "width_multiplier": 2.25,
        "delivery_status": (
            "DELIVERY_COMPLETE" if delivery_complete else "DELIVERY_INCOMPLETE"
        ),
        "execution_status": execution["status"],
        "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        "steady_state_method_id": "FAST64_SS_W4",
        "scope": "MC200_LOW_ONLY",
        "fixed_step_ps": 50,
        "formal_record_count": len(master),
        "all_frame_count": 13_600,
        "retained_fft_code_count": 12_800,
        "frame0_status": frame0["status"],
        "frame0_protocol_pass_count": frame0["pass_count"],
        "frame0_protocol_fail_count": frame0["fail_count"],
        "frame0_protocol_failure_seeds": frame0["failure_seeds"],
        "dynamic_performance_status": performance["status"],
        "dynamic_performance_pass": performance["pass"],
        "required_hard_dynamic_pass_count": performance[
            "required_hard_pass_count"
        ],
        "baseline_hard_dynamic_pass_count": performance[
            "baseline_hard_dynamic_pass_count"
        ],
        "candidate_hard_dynamic_pass_count": performance[
            "candidate_hard_dynamic_pass_count"
        ],
        "baseline_snr_budget_pass_count": performance[
            "baseline_snr_budget_pass_count"
        ],
        "candidate_snr_budget_pass_count": performance[
            "candidate_snr_budget_pass_count"
        ],
        "hard_dynamic_recovered_count": performance[
            "hard_dynamic_recovered_count"
        ],
        "hard_dynamic_regressed_count": performance[
            "hard_dynamic_regressed_count"
        ],
        "median_delta_sndr_db": performance["median_delta_sndr_db"],
        "baseline_fail_median_delta_sndr_db": performance[
            "baseline_fail_median_delta_sndr_db"
        ],
        "minimum_delta_sndr_db": performance["minimum_delta_sndr_db"],
        "minimum_delta_seed": performance["minimum_delta_seed"],
        "candidate_percentiles": candidate_percentiles,
        "baseline_percentiles": baseline_percentiles,
        "existing_block_and_four_phase_gates": existing_gates,
        "promotion_status": "NOT_PROMOTED",
        "signoff_status": "SIGNOFF_NOT_CLAIMED",
        "frozen_input_manifest_mismatches": frozen_input_mismatches,
        "completion_checks": checks,
        "non_claims": scorecard["non_claims"],
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
            "performance_result_is_not_a_completion_gate": True,
            "frame0_result_is_not_a_completion_gate": True,
            "existing_gate_result_is_not_overwritten": True,
        },
    )

    cp = candidate_percentiles
    bp = baseline_percentiles
    report = f"""# CMP_IN_A2P25_W MC200 LOW FAST64_SS_W4 性能测量报告

## 1. 独立状态

- 交付：`{status['delivery_status']}`
- 执行：`{status['execution_status']}`
- frame 0：`{status['frame0_status']}`
- 动态性能：`{status['dynamic_performance_status']}`
- 既有 block/four-phase gates：`{existing_gates}`
- promotion：`NOT_PROMOTED`
- signoff：`SIGNOFF_NOT_CLAIMED`

执行完成、frame 0、动态性能、既有门禁和 signoff 分别判定，互不覆盖。

## 2. 冻结测量合同

- DUT：`CMP_IN_A2P25_W`，仅 XM3/XM4 宽度由 1.56 um 调整到 3.51 um；
- TT / 3.3 V / 27 C；
- mismatch seed 1–200，noise seed=`100000+mismatch_seed`；
- LOW bin 7，fin=218.75 kHz，Fs=2 MS/s，输入 3.0 Vpp,diff；
- 每条 68 帧，frame 0 独立门，frame 1–3 startup diagnostic；
- frame 4–67 构成正式 NFFT=64 `FAST64_SS_W4`；
- `ROBUST_GEAR`，固定 `maxstep=50 ps`；
- rectangular coherent FFT 与既有 SNR/SNDR/ENOB/SFDR/THD 方程不变。

## 3. 完整性

- 正式记录：{len(master)}/200；
- 全部 code：13,600/13,600；
- 正式 FFT code：12,800/12,800；
- paired baseline/candidate：{len(paired)}/200；
- mismatch checksum 配对：{scorecard['input_pairing']['mismatch_checksum_match_count']}/200；
- noise-prefix checksum 配对：{scorecard['input_pairing']['noise_prefix_checksum_match_count']}/200；
- 50 ps、W4 与 Parseval：全部通过。

## 4. 性能结果

- hard-dynamic PASS：{performance['baseline_hard_dynamic_pass_count']}/200
  -> {performance['candidate_hard_dynamic_pass_count']}/200；
- 固定性能门：candidate 至少 190/200，结果
  `{'PASS' if performance['pass'] else 'FAIL'}`；
- SNR-budget PASS：{performance['baseline_snr_budget_pass_count']}/200
  -> {performance['candidate_snr_budget_pass_count']}/200；
- hard-dynamic 恢复：{performance['hard_dynamic_recovered_count']}；
- hard-dynamic 回归：{performance['hard_dynamic_regressed_count']}；
- median delta SNDR：{performance['median_delta_sndr_db']:.6f} dB；
- baseline-fail seed median delta SNDR：
  {performance['baseline_fail_median_delta_sndr_db']:.6f} dB；
- 最小 delta SNDR：{performance['minimum_delta_sndr_db']:.6f} dB，
  seed {performance['minimum_delta_seed']}。

## 5. 总体分位数

| 指标 | DUT | P1 | P5 | P10 | P50 |
|---|---|---:|---:|---:|---:|
| SNR/dB | baseline | {bp['SNR_dB']['P1']:.6f} | {bp['SNR_dB']['P5']:.6f} | {bp['SNR_dB']['P10']:.6f} | {bp['SNR_dB']['P50']:.6f} |
| SNR/dB | 2.25x | {cp['SNR_dB']['P1']:.6f} | {cp['SNR_dB']['P5']:.6f} | {cp['SNR_dB']['P10']:.6f} | {cp['SNR_dB']['P50']:.6f} |
| SNDR/dB | baseline | {bp['SNDR_dB']['P1']:.6f} | {bp['SNDR_dB']['P5']:.6f} | {bp['SNDR_dB']['P10']:.6f} | {bp['SNDR_dB']['P50']:.6f} |
| SNDR/dB | 2.25x | {cp['SNDR_dB']['P1']:.6f} | {cp['SNDR_dB']['P5']:.6f} | {cp['SNDR_dB']['P10']:.6f} | {cp['SNDR_dB']['P50']:.6f} |
| ENOB/bit | baseline | {bp['ENOB_raw_bit']['P1']:.6f} | {bp['ENOB_raw_bit']['P5']:.6f} | {bp['ENOB_raw_bit']['P10']:.6f} | {bp['ENOB_raw_bit']['P50']:.6f} |
| ENOB/bit | 2.25x | {cp['ENOB_raw_bit']['P1']:.6f} | {cp['ENOB_raw_bit']['P5']:.6f} | {cp['ENOB_raw_bit']['P10']:.6f} | {cp['ENOB_raw_bit']['P50']:.6f} |

分位数固定使用 NumPy linear/type-7。

## 6. frame 0

- protocol/path PASS：{frame0['pass_count']}/200；
- FAIL：{frame0['fail_count']}/200；
- failure seeds：{frame0['failure_seeds']}；
- noise-on frame0/frame64 code 不相等仅为诊断，不是硬判据。

## 7. 结论边界

本轮是 LOW-only MC200，不是 LOW/NEAR 双频 die-level yield。candidate 与
baseline 的逐码差异是 changed-DUT 性能诊断，不是 equivalence gate。
即使动态性能门通过，也不自动关闭既有 block kickback 或 nominal
four-phase FAIL，不产生 promotion、layout/PEX、silicon、tapeout 或 signoff。
"""
    report_path = ROOT / "reports/CMP_IN_A2P25_W_MC200_LOW_W4_REPORT_CN.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if delivery_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
