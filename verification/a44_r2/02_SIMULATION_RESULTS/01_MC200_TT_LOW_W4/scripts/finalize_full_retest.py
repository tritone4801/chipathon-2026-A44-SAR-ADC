#!/usr/bin/env python3
"""Create the final status, Chinese report, README, and completion audit."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_csv(relative: str):
    with (ROOT / relative).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def fmt(value: object, digits: int = 4) -> str:
    return f"{float(value):.{digits}f}"


def percentile_table(rows: list[dict[str, str]]) -> str:
    selected = [
        row
        for row in rows
        if row["metric"] in {"SNR", "SNDR", "ENOB"}
        and row["scope"] in {"LOW", "NEAR_NYQUIST", "WORST_BAND"}
    ]
    lines = [
        "| 范围 | 指标 | P1 | P5 | P10 | P50 | 最差观测 | 最差 seed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            "| {scope} | {metric} | {p1} | {p5} | {p10} | {p50} | "
            "{worst} | {seed} |".format(
                scope=row["scope"],
                metric=row["metric"],
                p1=fmt(row["p1"]),
                p5=fmt(row["p5"]),
                p10=fmt(row["p10"]),
                p50=fmt(row["p50"]),
                worst=fmt(row["worst_observed"]),
                seed=row["worst_seed"],
            )
        )
    return "\n".join(lines)


def comparison_table(summary: dict) -> str:
    lines = [
        "| 参考数据集 | 可比记录 | 当前不可比 | code 完全相同 | code 不同 | 不同帧数 | "
        "指标完全相同 | 状态完全相同 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, row in summary["reference_summary"].items():
        lines.append(
            "| {label} | {comparable_records} | {not_comparable_current_records} | "
            "{code_exact_records} | "
            "{code_different_records} | {different_frames} | "
            "{metric_exact_records} | {state_exact_records} |".format(
                label=label, **row
            )
        )
    return "\n".join(lines)


def main() -> int:
    execution = read_json("results/execution_audit.json")
    repeatability = read_json("results/repeatability_audit.json")
    comparison = read_json("comparisons/comparison_summary.json")
    statistics = read_json("results/statistics_status.json")
    plot_audit = read_json("results/plot_audit.json")
    pdf_audit = read_json("results/pdf_audit.json")
    visual = read_json("results/formal_plot_visual_review.json")
    s110_diagnostic = read_json("results/s110_repeatability_diagnostic.json")
    s110_fullwave = read_json("results/s110_fullwave_audit.json")
    percentiles = read_csv("csv/population_percentiles.csv")
    contract = read_json("config/frozen_mc200_contract.json")

    evidence_checks = {
        "execution_pass": execution["pass"] is True,
        "comparison_complete": comparison["status"] == "COMPARISON_COMPLETE",
        "statistics_complete": statistics["statistics_complete"] is True,
        "formal_plot_audit_pass": plot_audit["pass"] is True,
        "pdf_structure_audit_pass": pdf_audit["pass"] is True,
        "formal_plot_visual_review_pass": visual["pass"] is True,
        "formal_plot_visual_review_hashes_match": all(
            sha256(relative) == expected
            for relative, expected in visual["reviewed_files"].items()
        )
        and sha256("reports/plot_contact_sheet.pdf")
        == visual["contact_sheet_sha256"],
        "contract_is_fixed_50ps": contract["maxstep_ps"] == 50,
        "contract_has_200_seeds": contract["mismatch_seeds"]["count"] == 200,
        "contract_has_two_bands": set(contract["bands"]) == {
            "LOW",
            "NEAR_NYQUIST",
        },
        "repeatability_failure_diagnostic_complete": (
            s110_diagnostic["status"]
            == "S110_REPEATABILITY_DIAGNOSTIC_COMPLETE"
            and s110_diagnostic["all_repeats_valid"] is True
            and s110_diagnostic["main_population_was_not_modified"] is True
        ),
        "repeatability_failure_fullwave_capture_pass": (
            s110_fullwave["pass"] is True
            and s110_fullwave["main_population_was_not_modified"] is True
            and sha256(s110_fullwave["raw_path"]) == s110_fullwave["raw_sha256"]
        ),
    }
    evidence_complete = all(evidence_checks.values())
    repeatability_pass = repeatability["pass"] is True
    qualification_pass = (
        evidence_complete and repeatability_pass and statistics["performance_pass"]
    )
    if not evidence_complete:
        overall = "INCOMPLETE_EVIDENCE"
    elif not repeatability_pass and not statistics["performance_pass"]:
        overall = "EVIDENCE_COMPLETE_REPEATABILITY_FAIL_PERFORMANCE_FAIL"
    elif not repeatability_pass:
        overall = "EVIDENCE_COMPLETE_REPEATABILITY_FAIL"
    elif not statistics["performance_pass"]:
        overall = "EVIDENCE_COMPLETE_PERFORMANCE_FAIL"
    else:
        overall = "QUALIFICATION_PASS"

    generated = datetime.now(timezone.utc).isoformat()
    status = {
        "status": overall,
        "evidence_package_complete": evidence_complete,
        "qualification_pass": qualification_pass,
        "repeatability_pass": repeatability_pass,
        "performance_pass": statistics["performance_pass"],
        "generated_utc": generated,
        "campaign_id": contract["campaign_id"],
        "fixed_maxstep_ps": contract["maxstep_ps"],
        "records": execution["records"],
        "code_rows": execution["code_rows"],
        "valid_dies": statistics["valid_dies"],
        "hard_pass_dies": statistics["hard_pass_dies"],
        "hard_fail_dies": statistics["hard_fail_dies"],
        "required_hard_pass_dies": statistics["required_hard_pass_dies"],
        "fixed50_41_repeatability_status": repeatability["status"],
        "s110_repeatability_diagnostic_status": s110_diagnostic["status"],
        "s110_fullwave_status": s110_fullwave["status"],
        "s110_fullwave_raw_sha256": s110_fullwave["raw_sha256"],
        "s110_fullwave_raw_size_bytes": s110_fullwave["raw_size_bytes"],
        "comparison_status": comparison["status"],
        "plot_status": plot_audit["status"],
        "visual_review_status": visual["status"],
        "evidence_checks": evidence_checks,
        "qualification_gates": {
            "fixed50_41_repeatability_pass": repeatability_pass,
            "performance_pass": statistics["performance_pass"],
        },
        "claim_boundaries": [
            "Execution completion is separate from performance acceptance.",
            "The evidence package is complete even though qualification is not passed.",
            "The one differing full-run population record was not overwritten.",
            "Historical equality is reported per reference and is not required "
            "except for the frozen FIXED50_41 repeatability set.",
            "Performance failure, if present, does not invalidate a complete "
            "and reproducible execution package.",
            "No layout, post-layout, silicon, or general PVT claim is made.",
        ],
    }
    (ROOT / "STATUS.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    performance_word = "通过" if statistics["performance_pass"] else "未通过"
    report = f"""# A44 MC200 固定 50 ps 全量重测报告

生成时间（UTC）：`{generated}`

## 结论

- 交付状态：`{overall}`
- 执行审计：`{execution["status"]}`，共 {execution["records"]}/400 条双频记录、
  {execution["code_rows"]}/25600 个逐帧 code。
- 固定 50 ps 的 41 条既有记录复现审计：`{repeatability["status"]}`。
- 证据包完成：`{evidence_complete}`；资格通过：`{qualification_pass}`。
- 项目定义的双频 hard dynamic 门槛：{performance_word}；
  {statistics["hard_pass_dies"]}/200 个 die 双频通过，要求不少于
  {statistics["required_hard_pass_dies"]}/200。
- 正式绘图自动审计：`{plot_audit["status"]}`；人工视觉复核：
  `{visual["status"]}`。
- PDF 结构审计：`{pdf_audit["status"]}`。

以上状态彼此独立。执行完成不自动等于性能通过；性能未通过也不抹除已完成、
可复核的仿真证据。

## 冻结测量合同

- PVT：`{contract["pvt"]}`
- mismatch seed：1–200；noise seed：`100000 + mismatch seed`
- 频带：LOW（bin 7，218.75 kHz）与 NEAR_NYQUIST（bin 29，906.25 kHz）
- 每条记录：64 帧，采样率 2 MHz
- `maxstep = 50 ps`，求解器档位：`{contract["solver_profile"]}`
- 测量器：`{contract["measurement_method"]}`
- 每个 seed/频带使用独立 ngspice 进程；最多 {contract["worker_cap"]} 个并发

## 200 die 统计

{percentile_table(percentiles)}

百分位采用 `LINEAR_TYPE7`。WORST_BAND 对每个 die 先取双频较差值，再计算总体
分位数；不是把 400 条频带记录直接混为一个总体。

## 与历史数据逐记录比较

{comparison_table(comparison)}

41 条固定 50 ps 子集要求逐 code、逐帧、逐指标、逐状态与执行档位完全一致；
其他历史集只作差异归档，不作为本次执行完成的必要条件。

## seed110 LOW 复现差异闭环

- 全量正式运行的 frame 0 code 为
  `{s110_diagnostic["full_run_frame0_code"]}`；冻结 41 条参考值为
  `{s110_diagnostic["fixed50_reference_frame0_code"]}`，其余 63 帧一致。
- 在相同 50 ps、`{s110_diagnostic["solver_profile"]}` 条件下进行 4 个独立并发
  复测，4/4 均得到参考分支、frame 0 =
  `{s110_diagnostic["fixed50_reference_frame0_code"]}`，checksum =
  `{s110_diagnostic["fixed50_reference_checksum_sha256"]}`。
- 随后显式保存全部向量的全波形复测也得到 frame 0 =
  `{s110_fullwave["frame0_code"]}`；原始波形大小
  {s110_fullwave["raw_size_bytes"]} bytes，SHA-256 =
  `{s110_fullwave["raw_sha256"]}`。
- 因此，全量运行中的 code 240 被保留为一次未在随后 5 次相同条件复测中重现的
  分支。正式 200-seed population CSV 未被回写或替换，复现门仍严格记为 FAIL。

## 绘图规范与证据

- 正式频谱仅绘制离散 FFT bin，横轴为 MHz，纵轴为 dBFS/bin。
- 图内不画连线伪装连续谱；注释/信息栏位于坐标区外，不遮挡基波或杂散。
- 总体分布覆盖 LOW、NEAR_NYQUIST 与逐 die WORST_BAND，并使用统一量程。
- 每幅正式图均保留矢量 PDF、300 dpi PNG 和源 CSV。
- 联系表仅用于浏览；单幅 PDF/PNG 和源 CSV 才是正式审阅对象。

图清单：`plots/plot_inventory.csv`；源数据绑定：
`plots/plot_source_manifest.csv`；联系表：`reports/plot_contact_sheet.pdf`。

## 可追溯性

- 执行审计：`results/execution_audit.json`
- 41 条复现审计：`results/repeatability_audit.json`
- 历史对比摘要：`comparisons/comparison_summary.json`
- 统计状态：`results/statistics_status.json`
- 绘图自动审计：`results/plot_audit.json`
- PDF 结构审计：`results/pdf_audit.json`
- 绘图视觉复核：`results/formal_plot_visual_review.json`
- seed110 复现诊断：`results/s110_repeatability_diagnostic.json`
- seed110 全波形审计：`results/s110_fullwave_audit.json`
- 冻结合同：`config/frozen_mc200_contract.json`
- 资源轨迹：`csv/full_mc200_resource_trace.csv`

## 声明边界

本报告仅覆盖指定 TT 3.3 V、27 °C、固定 50 ps、FAST64 测量方式下的
MC200 双频重测。它不声明版图后仿真、寄生、电源完整性、其他 PVT、硅片结果
或一般性 signoff。历史差异归因也不因“比较完成”而自动闭环。
"""
    (ROOT / "reports" / "FINAL_MC200_FIXED50PS_REPORT_CN.md").write_text(
        report, encoding="utf-8"
    )

    readme = f"""# {contract["campaign_id"]}

这是固定 `maxstep=50 ps` 的 200-seed、双频 FAST64 重测全证据包。

最终状态：`{overall}`  
性能状态：`{statistics["status"]}`

从以下文件开始审阅：

1. `STATUS.json`
2. `reports/FINAL_MC200_FIXED50PS_REPORT_CN.md`
3. `results/execution_audit.json`
4. `results/repeatability_audit.json`
5. `comparisons/comparison_summary.json`
6. `results/plot_audit.json`
7. `plots/plot_inventory.csv`
8. `results/s110_repeatability_diagnostic.json`
9. `results/s110_fullwave_audit.json`

`jobs/`、`generated/`、`logs/` 和逐帧 `csv/dynamic_codes.csv` 保留完整执行
证据。5.06 GB 的 seed110 全波形仅保留在完整包；摘要包保留其审计记录、
SHA-256、复测逐帧数据以及生成 deck/log，但省略原始波形。
"""
    (ROOT / "README_CN.md").write_text(readme, encoding="utf-8")

    completion = {
        "status": (
            "PASS_EVIDENCE_COMPLETION_AUDIT"
            if evidence_complete
            else "FAIL_EVIDENCE_COMPLETION_AUDIT"
        ),
        "pass": evidence_complete,
        "checked_utc": generated,
        "overall_status": overall,
        "qualification_pass": qualification_pass,
        "repeatability_pass": repeatability_pass,
        "performance_pass": statistics["performance_pass"],
        "evidence_checks": evidence_checks,
        "qualification_gates": {
            "fixed50_41_repeatability_pass": repeatability_pass,
            "performance_pass": statistics["performance_pass"],
        },
        "key_artifact_sha256": {
            relative: sha256(relative)
            for relative in (
                "STATUS.json",
                "reports/FINAL_MC200_FIXED50PS_REPORT_CN.md",
                "csv/dynamic_master.csv",
                "csv/dynamic_codes.csv",
                "csv/population_percentiles.csv",
                "comparisons/comparison_summary.json",
                "plots/plot_inventory.csv",
            )
        },
    }
    (ROOT / "results" / "completion_audit.json").write_text(
        json.dumps(completion, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(completion, indent=2))
    return 0 if evidence_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
