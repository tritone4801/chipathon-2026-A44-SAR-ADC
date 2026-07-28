#!/usr/bin/env python3
"""Create the final status, method-deviation receipt, and Chinese report."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    strict = json.loads(
        (ROOT / "results" / "strict_reproduction_audit.json").read_text(
            encoding="utf-8"
        )
    )
    execution = json.loads(
        (ROOT / "results" / "mc10_execution_status.json").read_text(
            encoding="utf-8"
        )
    )
    diagnostics = json.loads(
        (ROOT / "results" / "diagnostic_status.json").read_text(encoding="utf-8")
    )
    fullwave = json.loads(
        (ROOT / "results" / "triggered_fullwave_audit.json").read_text(
            encoding="utf-8"
        )
    )
    plot_audit = json.loads(
        (ROOT / "results" / "mc10_plot_audit.json").read_text(encoding="utf-8")
    )
    comparison = read_csv(
        ROOT / "comparisons" / "current_mc200_strict_comparison.csv"
    )
    diagnostic_keys = read_csv(
        ROOT / "diagnostics" / "diagnostic_key_summary.csv"
    )
    current_resource = json.loads(
        (
            ROOT
            / "references"
            / "current_mc200_provenance"
            / "full_mc200_resource_summary.json"
        ).read_text(encoding="utf-8")
    )
    immutable = strict["first_run_immutable_artifacts"]
    immutable_checks = {
        "mc10_master_unchanged": sha256(ROOT / "csv" / "mc10_master.csv")
        == immutable["mc10_master_sha256"],
        "mc10_codes_unchanged": sha256(ROOT / "csv" / "mc10_codes.csv")
        == immutable["mc10_codes_sha256"],
        "comparison_unchanged": sha256(
            ROOT / "comparisons" / "current_mc200_strict_comparison.csv"
        )
        == immutable["comparison_sha256"],
        "frame_differences_unchanged": sha256(
            ROOT / "comparisons" / "frame_code_differences.csv"
        )
        == immutable["frame_differences_sha256"],
    }
    deviation = {
        "status": "FIRST_RUN_RESOURCE_PROFILE_DEVIATION",
        "blocking_for_exact_scheduler_profile_claim": True,
        "does_not_replace_electrical_strict_failure": True,
        "current_mc200_launch_command": (
            "python3 scripts/run_v7.py --stage formal --seeds 1:200 --workers 4"
        ),
        "new_mc10_launch_command": "python3 scripts/run_mc10_repro.py",
        "both_used_four_workers": True,
        "current_mc200_max_ngspice_processes": current_resource[
            "max_ngspice_processes"
        ],
        "current_mc200_max_total_threads": current_resource["max_total_threads"],
        "new_mc10_max_ngspice_processes": execution["max_ngspice_processes"],
        "new_mc10_max_total_threads": execution["max_total_threads"],
        "plan_limit_total_threads": 16,
        "diagnostic_corrective_action": (
            "taskset -c 0-11 restored four ngspice processes x four threads"
        ),
        "diagnostic_max_ngspice_processes": diagnostics["max_ngspice_processes"],
        "diagnostic_max_total_threads": diagnostics["max_total_threads"],
        "interpretation": (
            "The first run remains valid electrical evidence, but it cannot be "
            "claimed to have reproduced the current-MC200 scheduler profile."
        ),
    }
    write_json(ROOT / "results" / "execution_profile_deviation.json", deviation)
    launcher_receipt = {
        "status": "LAUNCHER_RECEIPT_NORMALIZED_WITH_RAW_MARKERS_PRESERVED",
        "formal_runner_status": execution["status"],
        "formal_runner_completed": execution["pass"],
        "formal_raw_marker_content": (
            ROOT / "results" / "mc10_formal_exit_code.txt"
        ).read_text(encoding="utf-8", errors="replace"),
        "sequential_diagnostic_raw_marker_content": (
            ROOT / "results" / "diag_sequential_exit_code.txt"
        ).read_text(encoding="utf-8", errors="replace"),
        "concurrent_diagnostic_raw_marker_content": (
            ROOT / "results" / "diag_concurrent_exit_code.txt"
        ).read_text(encoding="utf-8", errors="replace"),
        "triggered_fullwave_raw_marker_content": (
            ROOT / "results" / "triggered_fullwave_exit_code.txt"
        ).read_text(encoding="utf-8", errors="replace"),
        "note": (
            "The first two detached PowerShell launch receipts contain quoting "
            "artifacts ('0n' and 'True'). Completion is established by runner "
            "status JSON, complete row counts, logs, and inactive processes; "
            "the raw marker files are retained unmodified."
        ),
    }
    write_json(ROOT / "results" / "launcher_receipt.json", launcher_receipt)

    changed = [row for row in comparison if row["record_exact"] == "False"]
    pass_to_fail = sum(
        row["expected_state"] == "VALID_PASS"
        and row["actual_state"] == "VALID_FAIL"
        for row in changed
    )
    fail_to_pass = sum(
        row["expected_state"] == "VALID_FAIL"
        and row["actual_state"] == "VALID_PASS"
        for row in changed
    )
    stable_historical = sum(
        row["classification"] == "STABLE_HISTORICAL_REFERENCE_BRANCH"
        for row in diagnostic_keys
    )
    stable_current = sum(
        row["classification"] == "STABLE_CURRENT_MC200_BRANCH"
        for row in diagnostic_keys
    )
    completion_checks = {
        "formal_20_of_20_valid": execution["valid_records"] == 20,
        "formal_1280_of_1280_codes": execution["code_rows"] == 1280,
        "strict_audit_frozen": strict["status"]
        == "FAIL_CURRENT_MC200_MC10_REPRO",
        "immutable_first_run_artifacts": all(immutable_checks.values()),
        "diagnostics_32_of_32_valid": diagnostics["pass_execution"]
        and diagnostics["diagnostic_records"] == 32,
        "diagnostic_resource_limit_restored": diagnostics["max_total_threads"] <= 16,
        "triggered_fullwave_complete": fullwave["pass"],
        "plots_complete": plot_audit["pass"],
        "source_drift_disclosed": execution["preflight"][
            "live_production_source_drift_warning"
        ]["status"]
        == "LIVE_PRODUCTION_SOURCE_DRIFT_AFTER_REFERENCE_FREEZE",
        "resource_profile_deviation_disclosed": deviation[
            "blocking_for_exact_scheduler_profile_claim"
        ],
    }
    delivery_complete = all(completion_checks.values())
    final_status = {
        "campaign": "A44_MC10_CURRENT_MC200_REPRO_20260725_R1",
        "delivery_status": (
            "DELIVERY_COMPLETE" if delivery_complete else "DELIVERY_INCOMPLETE"
        ),
        "reproduction_status": strict["status"],
        "reproduction_pass": False,
        "formal_execution_evidence_valid": execution["pass"],
        "exact_scheduler_profile_reproduced": False,
        "completion_checks": completion_checks,
        "formal_records": 20,
        "formal_codes": 1280,
        "exact_records": strict["record_exact_count"],
        "different_records": strict["record_different_count"],
        "exact_frames": strict["frame_exact_count"],
        "different_frames": strict["frame_different_count"],
        "fail_to_pass_transitions": fail_to_pass,
        "pass_to_fail_transitions": pass_to_fail,
        "diagnostic_records": diagnostics["diagnostic_records"],
        "stable_historical_keys": stable_historical,
        "stable_current_keys": stable_current,
        "fullwave_capture_count": fullwave["captured_count"],
        "plot_count": plot_audit["figure_count"],
        "live_production_source_status": execution["preflight"][
            "live_production_source_drift_warning"
        ]["status"],
        "non_claims": [
            "This enriched MC10 is not a replacement MC200 population.",
            "The current MC200 is not declared reproducible.",
            "No performance, qualification, signoff, layout, or silicon claim is made.",
            "The live production tree is not claimed to match the frozen MC200 source.",
        ],
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ROOT / "STATUS.json", final_status)
    write_json(
        ROOT / "results" / "completion_audit.json",
        {
            "status": (
                "PASS_DELIVERY_COMPLETION_AUDIT"
                if delivery_complete
                else "FAIL_DELIVERY_COMPLETION_AUDIT"
            ),
            "pass": delivery_complete,
            "checks": completion_checks,
            "immutable_checks": immutable_checks,
        },
    )

    table_lines = []
    for row in changed:
        table_lines.append(
            "| {mismatch_seed} | {band} | {different_frames} | {expected_state} | "
            "{actual_state} | {expected_sndr_db:.4f} | {actual_sndr_db:.4f} |".format(
                mismatch_seed=row["mismatch_seed"],
                band=row["band"],
                different_frames=row["different_frames"],
                expected_state=row["expected_state"],
                actual_state=row["actual_state"],
                expected_sndr_db=float(row["expected_sndr_db"]),
                actual_sndr_db=float(row["actual_sndr_db"]),
            )
        )
    diagnostic_lines = []
    for row in diagnostic_keys:
        diagnostic_lines.append(
            f"| {row['mismatch_seed']} | {row['band']} | "
            f"{row['classification']} | {row['unique_diagnostic_streams']} | "
            f"{row['fullwave_triggered']} |"
        )
    capture = fullwave["captures"][0]
    report = f"""# A44 当前 MC200 的 MC10 复现检测最终报告

## 1. 结论

交付执行已完成，但复现结论为 **`FAIL_CURRENT_MC200_MC10_REPRO`**。

- 正式首轮：20/20 条记录有效，1280/1280 帧齐全；
- 严格一致：12/20 条记录、1269/1280 帧；
- 差异：8 条记录、11 帧；
- 状态变化：FAIL→PASS 为 {fail_to_pass} 条，PASS→FAIL 为 {pass_to_fail} 条；
- 后续 32 条诊断记录全部有效，且不能改写首轮 FAIL；
- 唯一触发的 seed109 NEAR 全波形已完成。

因此，当前 MC200 中的极低尾部结果不能被本次 MC10 复现检测确认成稳定可复现结果。

## 2. 冻结输入和执行边界

主参考固定为 `A44_MC200_FIXED50PS_FULL_RETEST_20260725_R1`，10 个 seed 为
`1,2,3,47,53,71,74,109,110,195`，两个频段均执行。测量条件固定为
FAST64、`maxstep=50 ps`、`ROBUST_GEAR`、独立进程，禁止 cache 和性能提前停止。

当前生产树在参考冻结后已漂移，历史参考的 113/113 源审计和 active binding/pin
order 仍通过；本包绑定封存的当前 MC200 输入，没有用已经变化的生产树替换。

## 3. 首轮严格差异

| Seed | Band | 差异帧 | 当前 MC200 状态 | 新 MC10 状态 | 当前 SNDR/dB | 新 SNDR/dB |
|---:|---|---:|---|---|---:|---:|
{chr(10).join(table_lines)}

其中 seed109 NEAR 在正式首轮出现 31.6703 dB 的第三分支；其余 7 个差异项均落入
V7 或固定41中已经存在的历史分支。

## 4. 诊断复测

每个差异 seed-band（包含强制 seed110 LOW）均执行 4 次：2 次顺序单-worker，
2 次正式 4-worker 调度。32/32 条记录有效，2048/2048 帧齐全。

| Seed | Band | 四次诊断分类 | 唯一流数 | 触发全波形 |
|---:|---|---|---:|---|
{chr(10).join(diagnostic_lines)}

7 个键四次均稳定落入历史参考分支；seed109 NEAR 四次均回到当前 MC200/V7
分支（46.8915 dB）。seed110 LOW 四次均为 frame0=224、48.0205 dB，没有复现
当前 MC200 的 frame0=240、32.1292 dB。

## 5. 资源条件偏差

当前 MC200 原正式批次的资源轨迹为最多 4 个 ngspice、总线程 16。本次正式首轮
虽同为 4 workers，但容器自动使用总线程 32，超出计划上限。因此本包明确标记
`FIRST_RUN_RESOURCE_PROFILE_DEVIATION`：首轮仍是有效电气证据，但不能声称完全
复现了当前 MC200 的调度条件。

诊断批次用 12 核 CPU 亲和性恢复到 4 个 ngspice×4 线程，总线程最大 16。
在该条件下，四次重复逐码稳定，仍不能复现当前 MC200 的 7 个极低尾部分支。

## 6. 全波形

- 目标：seed109 NEAR_NYQUIST；
- 触发原因：正式首轮出现第三分支；
- compact 结果：46.8915 dB，frame0=240，回到当前 MC200/V7 分支；
- raw：`{capture['raw_path']}`；
- 大小：{capture['raw_size_bytes']} bytes；
- SHA-256：`{capture['raw_sha256']}`；
- 原生 `-r` 未生成文件，使用 ngspice 显式 `write all` 回退；
- 全波形结果未替换正式 MC10 compact population。

## 7. 图表

已生成 18 幅正式图，每幅均提供矢量 PDF、300 dpi PNG 和源 CSV，包括严格复现
矩阵、8 幅逐帧 code-delta、seed110 五次新运行矩阵、7 幅离散频谱对照和状态变化图。
频谱采用离散 stem+point、dBFS/bin、无 floor clipping；图表审计全部通过。

## 8. 版本与证据完整性

首轮 master、codes、严格比较和帧差异四个哈希在诊断后均保持不变。正式 marker
中的 `0n` 和顺序诊断 marker 中的 `True` 是 PowerShell/容器分离启动的引号格式
瑕疵，原文件未修改；有效完成由 runner JSON、完整行数、日志及进程结束共同证明。

## 9. 非声明

- 本次风险富集 MC10 不能替代 MC200 population；
- 不声明当前 MC200 已可复现；
- 不声明性能、qualification、signoff、版图或硅片结论；
- 不声明当前 live production tree 与冻结参考相同。
"""
    report_path = ROOT / "reports" / "A44_MC10_CURRENT_MC200_REPRO_FINAL_REPORT_CN.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps(final_status, indent=2, ensure_ascii=False))
    return 0 if delivery_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
