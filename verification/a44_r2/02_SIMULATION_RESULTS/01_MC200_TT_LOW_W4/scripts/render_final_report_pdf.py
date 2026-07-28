#!/usr/bin/env python3
"""Render the Chinese final Markdown report as a checked PDF."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "A44_MC10_CURRENT_MC200_REPRO_FINAL_REPORT_CN.md"
OUTPUT = ROOT / "reports" / "A44_MC10_CURRENT_MC200_REPRO_FINAL_REPORT_CN.pdf"
FONT = Path(r"C:\Windows\Fonts\simhei.ttf")


def clean(text: str) -> str:
    text = text.replace("**", "").replace("`", "")
    text = text.replace("→", "-&gt;")
    return text


def parse_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [clean(cell.strip()) for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("A44CN", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 10 * mm, "A44 MC10 current-MC200 reproduction evidence")
    canvas.drawRightString(
        A4[0] - 18 * mm,
        10 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def main() -> int:
    if not FONT.is_file():
        raise FileNotFoundError(FONT)
    pdfmetrics.registerFont(TTFont("A44CN", str(FONT)))
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "A44Title",
        parent=styles["Title"],
        fontName="A44CN",
        fontSize=19,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=12,
    )
    heading = ParagraphStyle(
        "A44Heading",
        parent=styles["Heading2"],
        fontName="A44CN",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=9,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "A44Body",
        parent=styles["BodyText"],
        fontName="A44CN",
        fontSize=9.2,
        leading=14.0,
        textColor=colors.black,
        spaceAfter=5,
    )
    bullet = ParagraphStyle(
        "A44Bullet",
        parent=body,
        leftIndent=12,
        firstLineIndent=-8,
        bulletIndent=2,
    )
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title="A44 MC10 当前 MC200 复现检测最终报告",
        author="Codex",
    )
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(clean(line[2:]), title))
            story.append(
                Paragraph(
                    "交付状态：完成；复现状态：FAIL_CURRENT_MC200_MC10_REPRO",
                    ParagraphStyle(
                        "Status",
                        parent=body,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor("#B03A2E"),
                        spaceAfter=10,
                    ),
                )
            )
        elif line.startswith("## "):
            story.append(Paragraph(clean(line[3:]), heading))
        elif line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = parse_table(table_lines)
            cell_style = ParagraphStyle(
                "Cell",
                parent=body,
                fontSize=6.5,
                leading=8.3,
                spaceAfter=0,
            )
            wrapped = [[Paragraph(cell, cell_style) for cell in row] for row in rows]
            width = (A4[0] - 34 * mm) / max(len(rows[0]), 1)
            table = Table(wrapped, colWidths=[width] * len(rows[0]), repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "A44CN"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 5))
            continue
        elif line.startswith("- "):
            story.append(Paragraph("- " + clean(line[2:]), bullet))
        else:
            paragraph = [line]
            while (
                index + 1 < len(lines)
                and lines[index + 1].strip()
                and not lines[index + 1].strip().startswith(("#", "-", "|"))
            ):
                index += 1
                paragraph.append(lines[index].strip())
            story.append(Paragraph(clean(" ".join(paragraph)), body))
        index += 1

    story.append(PageBreak())
    story.append(Paragraph("附录：核心图表", heading))
    for name, caption in (
        ("strict_reproduction_matrix.png", "严格复现矩阵"),
        ("seed110_five_run_branch_matrix.png", "seed110 五次新运行分支矩阵"),
        ("state_change_map.png", "状态变化图"),
    ):
        image_path = ROOT / "plots" / "formal" / name
        image = Image(str(image_path))
        max_width = A4[0] - 34 * mm
        max_height = 82 * mm
        scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        story.append(KeepTogether([Paragraph(caption, body), image]))
        story.append(Spacer(1, 7))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
