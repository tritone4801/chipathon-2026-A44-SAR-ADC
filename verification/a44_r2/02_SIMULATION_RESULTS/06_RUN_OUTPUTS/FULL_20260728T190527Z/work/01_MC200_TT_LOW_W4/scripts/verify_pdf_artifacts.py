#!/usr/bin/env python3
"""Open every formal PDF with pypdf and audit page/content structure."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_size(page) -> int:
    contents = page.get_contents()
    if contents is None:
        return 0
    data = contents.get_data()
    return len(data)


def main() -> int:
    with (ROOT / "plots" / "plot_inventory.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        inventory = list(csv.DictReader(handle))

    details = []
    for item in inventory:
        path = ROOT / item["pdf"]
        reader = PdfReader(path)
        page = reader.pages[0] if len(reader.pages) == 1 else None
        box_ok = bool(
            page is not None
            and float(page.mediabox.width) > 100
            and float(page.mediabox.height) > 100
        )
        stream_bytes = content_size(page) if page is not None else 0
        details.append(
            {
                "figure_id": item["figure_id"],
                "relative_path": item["pdf"],
                "sha256": sha256(path),
                "page_count": len(reader.pages),
                "media_box_ok": box_ok,
                "content_stream_bytes": stream_bytes,
                "pass": len(reader.pages) == 1 and box_ok and stream_bytes > 100,
            }
        )

    contact_path = ROOT / "reports" / "plot_contact_sheet.pdf"
    contact = PdfReader(contact_path)
    expected_contact_pages = math.ceil(len(inventory) / 4)
    contact_details = {
        "relative_path": contact_path.relative_to(ROOT).as_posix(),
        "sha256": sha256(contact_path),
        "page_count": len(contact.pages),
        "expected_page_count": expected_contact_pages,
        "all_media_boxes_ok": all(
            float(page.mediabox.width) > 100
            and float(page.mediabox.height) > 100
            for page in contact.pages
        ),
        "all_content_streams_nonempty": all(
            content_size(page) > 100 for page in contact.pages
        ),
    }
    checks = {
        "inventory_nonempty": bool(inventory),
        "all_formal_pdfs_open_as_one_page": all(row["pass"] for row in details),
        "contact_sheet_page_count": contact_details["page_count"]
        == expected_contact_pages,
        "contact_sheet_media_boxes": contact_details["all_media_boxes_ok"],
        "contact_sheet_content_streams": contact_details[
            "all_content_streams_nonempty"
        ],
    }
    result = {
        "status": "PASS_PDF_STRUCTURE_AUDIT"
        if all(checks.values())
        else "FAIL_PDF_STRUCTURE_AUDIT",
        "pass": all(checks.values()),
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "formal_pdf_count": len(details),
        "formal_pdf_details": details,
        "contact_sheet": contact_details,
        "visual_render_review_required": True,
    }
    (ROOT / "results" / "pdf_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
