#!/usr/bin/env python3
"""Create the final status, Chinese Markdown report, and polished PDF report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from fast64_v2_common import (
    CSV_DIR,
    REPORT_DIR,
    RESULT_DIR,
    ROOT,
    read_csv,
    sha256_file,
    write_json_atomic,
)


OUTPUT_PDF = ROOT / "output/pdf/A44_MC10_FAST64_V2_FINAL_REPORT.pdf"
OUTPUT_MD = REPORT_DIR / "A44_MC10_FAST64_V2_FINAL_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def status_payload() -> dict:
    setup = load_json("results/setup_audit.json")
    unit = load_json("results/fast64_v2_unit_tests.json")
    warmup = load_json("results/warmup_qualification.json")
    numerical = load_json("results/numerical_split_audit.json")
    execution = load_json("results/mc10_execution_status.json")
    first = load_json("results/first_conversion_status.json")
    steady = load_json("results/fast64_steady_state_metrics.json")
    transition = load_json("results/method_transition_audit.json")
    plot = load_json("results/plot_generation.json")
    main = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    first_main = [
        row
        for row in first["records"]
        if row["role"] == "MAIN_MC10" and row["noise_mode"] == "ON"
    ]
    fail_records = [
        {
            "mismatch_seed": row["mismatch_seed"],
            "band": row["band"],
            "first_conversion_status": row["first_conversion_status"],
            "steady_state_sndr_db": row["steady_state_sndr_db"],
            "steady_state_enob_raw": row["steady_state_enob_raw"],
            "steady_state_hard_dynamic_pass": row[
                "steady_state_hard_dynamic_pass"
            ],
            "overall_status": row["overall_status"],
        }
        for row in main
        if row["overall_status"] != "PASS_FAST64_COMPLETE"
    ]
    delivery_complete = all(
        (
            setup["pass"],
            unit["pass"],
            warmup["pass"],
            execution["pass"],
            plot["pass"],
            len(main) == 20,
        )
    )
    return {
        "campaign": ROOT.name,
        "delivery_status": "DELIVERY_COMPLETE"
        if delivery_complete
        else "DELIVERY_INCOMPLETE",
        "delivery_complete": delivery_complete,
        "method_id": "FAST64_V2_FIRST_CONVERSION_SEPARATED",
        "steady_state_method_id": "FAST64_SS_W4",
        "method_qualification_status": (
            "PASS_FAST64_V2_METHOD_QUALIFICATION"
            if warmup["pass"]
            else "FAIL_WARMUP4_QUALIFICATION"
        ),
        "warmup_qualification_status": warmup["status"],
        "numerical_qualification_status": numerical["status"],
        "execution_status": execution["status"],
        "first_conversion_status": (
            "PASS_MAIN_MC10_FIRST_CONVERSION"
            if len(first_main) == 20
            and all(bool(row["first_conversion_pass"]) for row in first_main)
            else "FAIL_MAIN_MC10_FIRST_CONVERSION"
        ),
        "first_conversion_main_pass_count": sum(
            bool(row["first_conversion_pass"]) for row in first_main
        ),
        "first_conversion_main_record_count": len(first_main),
        "steady_state_status": (
            "PASS_MAIN_MC10_STEADY_STATE_ALL"
            if steady["hard_dynamic_pass_count"] == 20
            else "FAIL_MAIN_MC10_STEADY_STATE_PERFORMANCE"
        ),
        "steady_state_record_count": steady["records"],
        "steady_state_hard_pass_count": steady["hard_dynamic_pass_count"],
        "steady_state_snr_budget_pass_count": steady["snr_budget_pass_count"],
        "overall_record_pass_count": steady["overall_pass_count"],
        "method_transition_status": transition["status"],
        "strict_current_mc200_reproduction_claim": False,
        "resource_contract_pass": execution["resource_contract_pass"],
        "max_ngspice_processes_observed": execution[
            "max_ngspice_processes_observed"
        ],
        "max_ngspice_threads_observed": execution["max_ngspice_threads_observed"],
        "fail_records": fail_records,
        "non_claims": [
            "The new MC10 is not equivalent to the old startup-inclusive MC200.",
            "No MC200 yield or production-yield claim is made.",
            "No resizing candidate promotion is claimed.",
            "No post-layout, silicon, or general signoff claim is made.",
            "Warm-up does not hide or waive a first-conversion failure.",
            "MC10 and fixed-41 sample percentiles do not replace a 200-seed population percentile.",
            "The d_cosim digital output is inferred at the DAC bridge output and is not an independently measured analog node.",
        ],
        "completed_utc": utc_now(),
    }


def markdown_report(status: dict) -> str:
    main = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    lines = [
        "# A44 MC10 FAST64 V2 重测最终报告",
        "",
        "## 1. 结论",
        "",
        f"- 交付状态：`{status['delivery_status']}`",
        f"- 方法资格化：`{status['method_qualification_status']}`",
        f"- 数值资格化：`{status['numerical_qualification_status']}`",
        f"- 执行状态：`{status['execution_status']}`",
        f"- first-conversion：`{status['first_conversion_status']}`，"
        f"{status['first_conversion_main_pass_count']}/"
        f"{status['first_conversion_main_record_count']} 条通过",
        f"- steady-state：`{status['steady_state_status']}`，"
        f"{status['steady_state_hard_pass_count']}/"
        f"{status['steady_state_record_count']} 条通过硬动态门禁",
        f"- SNR budget：{status['steady_state_snr_budget_pass_count']}/"
        f"{status['steady_state_record_count']} 条通过",
        f"- 旧/新方法比较：`{status['method_transition_status']}`",
        "",
        "执行完成、方法资格化、first-conversion、steady-state 性能和旧方法复现语义"
        "分别报告；其中任何一项通过都不能替代另一项。",
        "",
        "## 2. 固定方法",
        "",
        "- 每条正式记录转换 68 帧。",
        "- frame 0 是独立 first-conversion Gate。",
        "- frames 1-3 只作启动诊断。",
        "- frames 4-67 是正式 64 点矩形窗 FFT。",
        "- frame 64 是 frame 0 的同相位暖机参考。",
        "- 正式 maxstep 固定 50 ps；100 ps 只形成资格化证据。",
        "- noise-OFF 要求 frame 0/64 的确定性同相位一致。",
        "- noise-ON 不要求 frame 0 code 等于 frame 64 code，但仍要求协议、完成、"
        "路径和 aperture timing 通过。",
        "",
        "## 3. 主 MC10 结果",
        "",
        "| Seed | Band | F0 | SS SNDR/dB | ENOB/bit | SS Gate | Overall |",
        "|---:|---|---|---:|---:|---|---|",
    ]
    for row in main:
        lines.append(
            "| {seed} | {band} | {f0} | {sndr:.6f} | {enob:.6f} | {ss} | {overall} |".format(
                seed=row["mismatch_seed"],
                band=row["band"],
                f0=row["first_conversion_status"],
                sndr=float(row["steady_state_sndr_db"]),
                enob=float(row["steady_state_enob_raw"]),
                ss=row["steady_state_hard_dynamic_pass"],
                overall=row["overall_status"],
            )
        )
    lines.extend(
        [
            "",
            "## 4. 资源和完整性",
            "",
            f"- 最大同时 ngspice 进程：{status['max_ngspice_processes_observed']}。",
            f"- 最大 ngspice 线程总数：{status['max_ngspice_threads_observed']}。",
            f"- 4进程/16线程合同：`{status['resource_contract_pass']}`。",
            "- 主 event-noise 数据为 20 条记录，每条正式 FFT 均使用 64 帧。",
            "- 桥接记录与主 MC10 population 分离。",
            "",
            "## 5. 方法迁移边界",
            "",
            "旧方法 `FAST64_STARTUP_INCLUSIVE_W0` 使用 frames 0-63；新方法 "
            "`FAST64_SS_W4` 使用 frames 4-67。二者只允许形成 "
            "`METHOD_TRANSITION_DIAGNOSTIC_COMPARISON`，不得混入同一分布或输出"
            " current MC200 的严格复现结论。",
            "",
            "## 6. 非声明",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in status["non_claims"])
    lines.extend(
        [
            "",
            "## 7. 证据入口",
            "",
            "- `csv/steady_state_master_mc10.csv`",
            "- `csv/first_conversion_path.csv`",
            "- `csv/warmup_canonical_comparison.csv`",
            "- `csv/numerical_split_comparison.csv`",
            "- `csv/method_transition_comparison.csv`",
            "- `csv/percentile_bridge_comparison.csv`",
            "- `results/mc10_execution_status.json`",
            "- `results/warmup_qualification.json`",
            "- `results/numerical_split_audit.json`",
            "- `plots/plot_inventory.csv`",
            "- `manifest_sha256.csv`",
            "",
        ]
    )
    return "\n".join(lines)


def page_decor(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#59636e"))
    canvas.drawString(18 * mm, 12 * mm, "A44 MC10 FAST64 V2 evidence report")
    canvas.drawRightString(
        A4[0] - 18 * mm, 12 * mm, f"Page {document.page}"
    )
    canvas.restoreState()


def build_pdf(status: dict) -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#17324d"),
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#17324d"),
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#26323d"),
        spaceAfter=2.2 * mm,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=7.5,
        leading=10,
    )
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="A44 MC10 FAST64 V2 Final Report",
        author="Codex",
    )
    story = [
        Spacer(1, 18 * mm),
        Paragraph("A44 MC10 FAST64 V2", title_style),
        Paragraph("First-conversion separated steady-state retest", styles["Heading2"]),
        Spacer(1, 8 * mm),
    ]
    summary_data = [
        ["Category", "Status"],
        ["Delivery", status["delivery_status"]],
        ["Method qualification", status["method_qualification_status"]],
        ["Numerical split", status["numerical_qualification_status"]],
        ["Execution", status["execution_status"]],
        ["First conversion", status["first_conversion_status"]],
        ["Steady-state performance", status["steady_state_status"]],
        ["Method transition", status["method_transition_status"]],
    ]
    summary = Table(summary_data, colWidths=(55 * mm, 105 * mm), repeatRows=1)
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfc7cf")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f7")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            summary,
            Spacer(1, 8 * mm),
            Paragraph(
                "The first-conversion gate, the steady-state spectrum, execution "
                "completeness, and performance acceptance are independent status "
                "dimensions. A pass in one dimension does not waive a failure in another.",
                body,
            ),
            PageBreak(),
            Paragraph("1. Frozen measurement contract", heading),
            Paragraph(
                "Each formal record converts 68 frames. Frame 0 is the independent "
                "first-conversion gate; frames 1-3 are startup diagnostics; frames "
                "4-67 are the 64 samples used by the rectangular FFT. Frame 64 is "
                "the same-phase warm reference for frame 0.",
                body,
            ),
        ]
    )
    contract_data = [
        ["Parameter", "Formal value"],
        ["Fs", "2 MS/s"],
        ["Input", "3.0 Vpp differential"],
        ["LOW / NEAR bins", "7 / 29"],
        ["Formal window", "W4, frames 4-67"],
        ["NFFT", "64"],
        ["First-conversion aperture", "480 ns"],
        ["Formal maxstep", "50 ps"],
        ["Bulk maxstep", "100 ps - qualification evidence only"],
        ["Workers / total threads", "4 / 16 maximum"],
    ]
    contract_table = Table(contract_data, colWidths=(65 * mm, 95 * mm), repeatRows=1)
    contract_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#277da1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c5ccd3")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7f9")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            contract_table,
            Spacer(1, 5 * mm),
            Paragraph("2. Qualification and execution", heading),
            Paragraph(
                f"Warm-up qualification: {status['warmup_qualification_status']}. "
                f"Numerical split: {status['numerical_qualification_status']}. "
                f"Execution: {status['execution_status']}. The maximum observed "
                f"ngspice process/thread counts were "
                f"{status['max_ngspice_processes_observed']}/"
                f"{status['max_ngspice_threads_observed']}.",
                body,
            ),
            PageBreak(),
            Paragraph("3. Main MC10 result", heading),
            Paragraph(
                f"First-conversion passes: {status['first_conversion_main_pass_count']}/"
                f"{status['first_conversion_main_record_count']}. Steady-state hard "
                f"dynamic passes: {status['steady_state_hard_pass_count']}/"
                f"{status['steady_state_record_count']}. SNR-budget passes: "
                f"{status['steady_state_snr_budget_pass_count']}/"
                f"{status['steady_state_record_count']}.",
                body,
            ),
        ]
    )
    for figure in (
        "fig01_first_conversion_gate_matrix.png",
        "fig06_steady_state_sndr_enob.png",
        "fig03_w0_vs_w4_sndr_dumbbell.png",
    ):
        path = ROOT / "plots" / figure
        if path.is_file():
            story.append(Image(str(path), width=160 * mm, height=100 * mm))
            story.append(Spacer(1, 3 * mm))
    story.extend(
        [
            PageBreak(),
            Paragraph("4. Method-transition boundary", heading),
            Paragraph(
                "Historical FAST64 used the startup-inclusive W0 window, frames "
                "0-63. The corrected formal result uses steady-state W4, frames "
                "4-67. These values are diagnostic method-transition comparisons. "
                "They are not merged into one distribution and do not establish "
                "strict current-MC200 reproduction.",
                body,
            ),
        ]
    )
    bridge_figure = ROOT / "plots/fig05_percentile_bridge.png"
    if bridge_figure.is_file():
        story.append(Image(str(bridge_figure), width=160 * mm, height=92 * mm))
    story.extend(
        [
            Paragraph("5. Explicit non-claims", heading),
            *[
                Paragraph(f"- {claim}", body)
                for claim in status["non_claims"]
            ],
            Paragraph("6. Evidence index", heading),
            Paragraph(
                "Primary evidence: csv/steady_state_master_mc10.csv, "
                "csv/first_conversion_path.csv, "
                "csv/warmup_canonical_comparison.csv, "
                "csv/numerical_split_comparison.csv, "
                "csv/method_transition_comparison.csv, "
                "results/mc10_execution_status.json, STATUS.json, and "
                "manifest_sha256.csv.",
                small,
            ),
        ]
    )
    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    status = status_payload()
    write_json_atomic(ROOT / "STATUS.json", status)
    OUTPUT_MD.write_text(markdown_report(status), encoding="utf-8")
    build_pdf(status)
    audit = {
        "status": "PASS_FINAL_REPORT_GENERATION",
        "pass": OUTPUT_MD.is_file() and OUTPUT_PDF.is_file(),
        "markdown": OUTPUT_MD.relative_to(ROOT).as_posix(),
        "markdown_sha256": sha256_file(OUTPUT_MD),
        "pdf": OUTPUT_PDF.relative_to(ROOT).as_posix(),
        "pdf_sha256": sha256_file(OUTPUT_PDF),
        "pdf_size_bytes": OUTPUT_PDF.stat().st_size,
        "completed_utc": utc_now(),
    }
    write_json_atomic(RESULT_DIR / "final_report_generation.json", audit)
    print(json.dumps(audit, sort_keys=True))
    return 0 if audit["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
