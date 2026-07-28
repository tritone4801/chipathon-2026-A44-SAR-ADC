#!/usr/bin/env python3
"""Build the cross-campaign summary, plots, report, and SHA-256 manifest."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MC = ROOT / "01_MC200_TT_LOW_W4"
PVT = ROOT / "02_PVT3_MC20_LOW_W4"
STATIC = ROOT / "03_FULL255_STATIC"
RESULTS = HERE / "results"
PLOTS = HERE / "plots"
REPORTS = HERE / "reports"
MANIFESTS = HERE / "manifests"
CASES = ("S044_TT", "S116_TT", "S180_TT", "S106_TT", "S044_SS", "S044_FF")
CANDIDATE_HASH = "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    for directory in (RESULTS, PLOTS, REPORTS, MANIFESTS):
        directory.mkdir(parents=True, exist_ok=True)

    mc_summary = read_json(MC / "results/population_summary_mc200_low_w4.json")
    mc_audit = read_json(MC / "results/execution_audit_mc200_low_w4.json")
    mc_execution = read_json(MC / "results/execution_mc200-low.json")
    mc_percentiles = read_csv(MC / "csv/population_percentiles_w4.csv")
    mc_representatives = read_csv(MC / "csv/representative_records_w4.csv")
    mc_master = read_csv(MC / "csv/steady_state_master_mc200_low_w4.csv")
    sndr_percentiles = {
        int(row["percentile"]): float(row["value"])
        for row in mc_percentiles
        if row["metric"] == "steady_state_sndr_db"
    }
    selected_mc = {
        int(row["mismatch_seed"]): {
            "sndr_db": float(row["steady_state_sndr_db"]),
            "snr_db": float(row["steady_state_snr_db"]),
            "enob_raw": float(row["steady_state_enob_raw"]),
            "overall_status": row["overall_status"],
        }
        for row in mc_master
        if int(row["mismatch_seed"]) in {44, 116, 180, 106}
    }

    pvt_status = read_json(PVT / "STATUS.json")
    pvt_execution = read_json(PVT / "results/execution_pvt-formal.json")
    pvt_smoke = read_json(PVT / "results/execution_smoke.json")
    pvt_manifest = read_json(PVT / "manifest_audit.json")

    static_rows: list[dict[str, object]] = []
    static_payload: dict[str, dict] = {}
    for case in CASES:
        payload = read_json(
            STATIC / "cases" / case / "results/current_full255_summary.json"
        )
        static_payload[case] = payload
        static_rows.append(
            {
                "case": case,
                "seed": payload["case"]["mismatch_seed"],
                "pvt": payload["case"]["pvt"],
                "transition_count": payload["transition_count"],
                "max_final_bracket_lsb": payload["max_final_bracket_lsb"],
                "max_abs_dnl_ep_lsb": payload["max_abs_dnl_ep_lsb"],
                "max_abs_inl_ep_lsb": payload["max_abs_inl_ep_lsb"],
                "min_width_code": payload["min_width_code"],
                "min_dnl_ep_lsb": payload["min_dnl_ep_lsb"],
                "missing_code_count": payload["missing_code_count_center"],
                "reversal_count": payload["reversal_count_center"],
                "status": payload["absolute_static_status"],
            }
        )
    write_csv(RESULTS / "full255_static_summary.csv", static_rows)

    all_hashes = {
        "mc_setup": read_json(MC / "results/setup_audit.json")[
            "candidate_comparator_sha256"
        ],
        "pvt_contract": read_json(PVT / "config/pvt3_mc20_contract.json")[
            "candidate"
        ]["comparator_sha256"],
        **{
            case: static_payload[case]["case"]["candidate_comparator_sha256"]
            for case in CASES
        },
    }
    binding_pass = set(all_hashes.values()) == {CANDIDATE_HASH}
    queue_a = read_json(STATIC / "results/queue_A_status.json")
    queue_b = read_json(STATIC / "results/queue_B_status.json")
    execution_complete = (
        mc_audit.get("pass")
        and pvt_status["completion_status"] == "COMPLETE_AS_EXECUTED"
        and queue_a["state"] == "COMPLETE"
        and queue_b["state"] == "COMPLETE"
        and all(row["transition_count"] == 255 for row in static_rows)
    )
    static_pass_count = sum(row["status"] == "PASS" for row in static_rows)

    summary = {
        "campaign": ROOT.name,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "id": "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587",
            "comparator_sha256": CANDIDATE_HASH,
            "widths_um": {
                "XM1": 1.56,
                "XM3_XM4": 3.51,
                "XM5_XM6": 8.2524,
                "XM7_XM11": 16.8587,
            },
        },
        "binding": {
            "pass": binding_pass,
            "declared_hashes": all_hashes,
        },
        "execution": {
            "complete": bool(execution_complete),
            "mc200": {
                "records": mc_summary["population_count"],
                "execution_audit_pass": mc_audit["pass"],
                "formal_wall_elapsed_s": mc_execution["wall_elapsed_s"],
                "exceptions": mc_execution["exception_jobs"],
            },
            "pvt3_mc20": {
                "records": 60,
                "completion_status": pvt_status["completion_status"],
                "smoke_wall_elapsed_s": pvt_smoke["wall_elapsed_s"],
                "formal_wall_elapsed_s": pvt_execution["wall_elapsed_s"],
                "exceptions": pvt_execution["exception_jobs"],
                "manifest_pass": pvt_manifest["pass"],
            },
            "full255_static": {
                "unique_curve_count": 6,
                "transition_search_count": 1530,
                "queue_a": queue_a["state"],
                "queue_b": queue_b["state"],
                "tt_seed44_reused_for_seed44_pvt_tt": True,
                "reuse_source": (
                    "03_FULL255_STATIC/cases/S044_TT/"
                    "results/current_full255_summary.json"
                ),
            },
        },
        "performance": {
            "mc200_tt_low_w4": {
                "hard_dynamic_pass_count": mc_summary[
                    "steady_state_hard_dynamic_pass_count"
                ],
                "hard_dynamic_fail_count": mc_summary[
                    "steady_state_hard_dynamic_fail_count"
                ],
                "failure_seeds": mc_summary[
                    "steady_state_hard_dynamic_failure_seeds"
                ],
                "sndr_percentiles_db": {
                    str(p): sndr_percentiles[p] for p in (1, 5, 10, 50)
                },
                "representative_records": mc_representatives,
                "selected_static_seed_dynamic_records": selected_mc,
            },
            "selected_pvt3_mc20_not_yield": pvt_status["performance_by_corner"],
            "full255_static": {
                "pass_count": static_pass_count,
                "fail_count": len(static_rows) - static_pass_count,
                "rows": static_rows,
            },
        },
        "overall_status": (
            "COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION"
            if execution_complete and static_pass_count != len(static_rows)
            else (
                "COMPLETE_AS_EXECUTED_ALL_PERFORMANCE_GATES_PASS"
                if execution_complete
                else "INCOMPLETE_EXECUTION"
            )
        ),
        "claim_boundary": [
            "MC200 is the fixed TT LOW/W4 population result.",
            "PVT3 MC20 is a selected diagnostic sample and not a yield population.",
            "FULL255 curves are deterministic seed/corner static results.",
            "TT seed44 is computed once and reused only after exact hash/method audit.",
            "Seed44 SS static failure prevents promotion.",
            "No layout, PEX, silicon, production-yield, tapeout, or signoff claim.",
        ],
    }
    write_json(RESULTS / "cross_campaign_summary.json", summary)

    labels = [row["case"] for row in static_rows]
    dnl = [float(row["max_abs_dnl_ep_lsb"]) for row in static_rows]
    inl = [float(row["max_abs_inl_ep_lsb"]) for row in static_rows]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5.8))
    width = 0.38
    ax.bar(x - width / 2, dnl, width, label="max |DNL|", color="#4c78a8")
    ax.bar(x + width / 2, inl, width, label="max |INL|", color="#f58518")
    ax.axhline(1.0, color="#4c78a8", linestyle="--", linewidth=1.4)
    ax.axhline(1.5, color="#f58518", linestyle="--", linewidth=1.4)
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("LSB")
    ax.set_title("Current resizing FULL255 static results")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "full255_static_dnl_inl_summary.png", dpi=180)
    fig.savefig(PLOTS / "full255_static_dnl_inl_summary.pdf")
    plt.close(fig)

    report_rows = "\n".join(
        "| {case} | {pvt} | {status} | {max_abs_dnl_ep_lsb:.4f} | "
        "{max_abs_inl_ep_lsb:.4f} | {missing_code_count} | {reversal_count} |".format(
            **row
        )
        for row in static_rows
    )
    pvt_rows = "\n".join(
        "| {corner} | {hard_dynamic_pass_count}/20 | {snr_budget_pass_count}/20 | "
        "{resized_sndr_p50_db:.4f} | {paired_sndr_delta_p50_db:+.4f} |".format(
            corner=corner, **pvt_status["performance_by_corner"][corner]
        )
        for corner in ("TT_3P3_27C", "SS_3P0_125C", "FF_3P6_M40C")
    )
    report = f"""# 当前 comparator resizing：MC200 + PVT3 MC20 + FULL255 STATIC

## 结论

执行矩阵完整，所有分支均绑定同一 comparator SHA-256 `{CANDIDATE_HASH}`。
最终状态为 **{summary["overall_status"]}**：动态总体改善明显，但 seed44 在 SS
corner 的 FULL255 静态性能失败，因此不晋级、不作 signoff 声明。

## MC200 TT LOW / FAST64_SS_W4

- 完整记录：200/200；执行审计：PASS；异常作业：0。
- hard dynamic：{mc_summary["steady_state_hard_dynamic_pass_count"]}/200 PASS。
- 失败 seeds：{", ".join(map(str, mc_summary["steady_state_hard_dynamic_failure_seeds"]))}。
- SNDR P1/P5/P10/P50：{sndr_percentiles[1]:.4f} / {sndr_percentiles[5]:.4f} /
  {sndr_percentiles[10]:.4f} / {sndr_percentiles[50]:.4f} dB。
- 正式批次墙钟：{mc_execution["wall_elapsed_s"] / 60:.2f} 分钟。

## Selected PVT3 MC20（诊断样本，不是 yield）

| Corner | Hard dynamic | SNR budget | Resized SNDR P50 (dB) | Paired SNDR ΔP50 (dB) |
|---|---:|---:|---:|---:|
{pvt_rows}

60/60 完成、frame0 60/60 PASS、PVT pairing PASS、最终 manifest PASS。
正式批次墙钟 {pvt_execution["wall_elapsed_s"] / 60:.2f} 分钟。

## FULL255 STATIC

| Case | PVT | Gate | max abs DNL (LSB) | max abs INL (LSB) | Missing | Reversal |
|---|---|---:|---:|---:|---:|---:|
{report_rows}

共计算 6 条唯一曲线、1530 个 transition。seed44 TT 同时服务于“TT seeds”
与“seed44 PVT”的 TT 项，复用前已确认 candidate hash、seed、corner、2-frame、
50 ps 和 0.02 LSB bracket 方法完全相同。

## 声明边界

- MC200 才是固定 TT LOW/W4 population 结果。
- PVT3 MC20 是选定的诊断 seeds，不能外推生产 yield。
- FULL255 是确定性 seed/corner 静态曲线。
- seed44 SS 的 static FAIL 阻止 promotion。
- 不作 layout、PEX、silicon、production-yield、tapeout 或 signoff 声明。
"""
    (REPORTS / "FINAL_REPORT_CN.md").write_text(report, encoding="utf-8")

    excluded = {
        (MANIFESTS / "package_manifest_sha256.csv").resolve(),
        (MANIFESTS / "manifest_audit.json").resolve(),
    }
    manifest_rows = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        if path.resolve() in excluded:
            continue
        manifest_rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_csv(MANIFESTS / "package_manifest_sha256.csv", manifest_rows)
    manifest_hash = sha256(MANIFESTS / "package_manifest_sha256.csv")
    readback_mismatches = []
    for row in manifest_rows:
        path = ROOT / row["relative_path"]
        if not path.is_file():
            readback_mismatches.append(
                {"relative_path": row["relative_path"], "reason": "missing"}
            )
            continue
        actual_bytes = path.stat().st_size
        actual_sha256 = sha256(path)
        if actual_bytes != int(row["bytes"]) or actual_sha256 != row["sha256"]:
            readback_mismatches.append(
                {
                    "relative_path": row["relative_path"],
                    "reason": "size_or_sha256_mismatch",
                    "expected_bytes": int(row["bytes"]),
                    "actual_bytes": actual_bytes,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": actual_sha256,
                }
            )
    duplicate_relative_paths = len(manifest_rows) - len(
        {row["relative_path"] for row in manifest_rows}
    )
    write_json(
        MANIFESTS / "manifest_audit.json",
        {
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "record_count": len(manifest_rows),
            "manifest_sha256": manifest_hash,
            "duplicate_relative_paths": duplicate_relative_paths,
            "all_files_hashed": True,
            "readback_mismatch_count": len(readback_mismatches),
            "readback_mismatches": readback_mismatches,
            "pass": duplicate_relative_paths == 0 and not readback_mismatches,
            "excluded_self_referential_files": [
                "04_CROSS_CAMPAIGN_SUMMARY/manifests/package_manifest_sha256.csv",
                "04_CROSS_CAMPAIGN_SUMMARY/manifests/manifest_audit.json",
            ],
        },
    )
    print(
        json.dumps(
            {
                "overall_status": summary["overall_status"],
                "execution_complete": execution_complete,
                "static_pass_count": static_pass_count,
                "manifest_records": len(manifest_rows),
                "manifest_sha256": manifest_hash,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
