#!/usr/bin/env python3
"""Independent completion, manifest, PDF, and claim-boundary audit."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from fast64_v2_common import (
    CSV_DIR,
    MANIFEST_DIR,
    RESULT_DIR,
    ROOT,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


BASE = (
    Path("/foss/designs/A44_MC10_CURRENT_MC200_REPRO_20260725_R1")
    if Path("/foss/designs").is_dir()
    else Path(
        "C:/Users/15031/eda/designs/manual_goal/verification/"
        "A44_MC10_CURRENT_MC200_REPRO_20260725_R1"
    )
)
EXPECTED_BASE_MANIFEST = (
    "3c2130f305e70968e7a2651b6c5ec445b973c0b27d0e5a8c466ce09b4817d0a7"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truth(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def check_required_file(relative: str) -> dict[str, object]:
    path = ROOT / relative
    return {
        "gate": f"FILE_{relative}",
        "pass": path.is_file() and path.stat().st_size > 0,
        "observed": path.stat().st_size if path.is_file() else 0,
        "required": "non-empty file",
    }


def verify_input_manifest() -> dict[str, object]:
    path = MANIFEST_DIR / "input_manifest_sha256.csv"
    failures = []
    rows = read_csv(path)
    for row in rows:
        target = ROOT / row["relative_path"]
        observed = sha256_file(target) if target.is_file() else ""
        if observed != row["sha256"]:
            failures.append(
                {
                    "relative_path": row["relative_path"],
                    "expected": row["sha256"],
                    "observed": observed,
                }
            )
    return {
        "gate": "INPUT_MANIFEST_IMMUTABLE",
        "pass": bool(rows) and not failures,
        "observed": {"entries": len(rows), "failures": failures},
        "required": "all frozen input hashes exact",
    }


def pdf_checks() -> tuple[list[dict[str, object]], dict[str, object]]:
    pdfs = sorted((ROOT / "output/pdf").rglob("*.pdf"))
    rows: list[dict[str, object]] = []
    render_root = ROOT / "tmp/pdfs/rendered"
    render_root.mkdir(parents=True, exist_ok=True)
    bundled = Path(
        "C:/Users/15031/.cache/codex-runtimes/codex-primary-runtime/"
        "dependencies/native/poppler/Library/bin/pdftoppm.exe"
    )
    if os.name == "nt" and bundled.is_file():
        pdftoppm = str(bundled)
    else:
        pdftoppm = os.environ.get("PDFTOPPM") or shutil.which("pdftoppm")
    for pdf in pdfs:
        relative = pdf.relative_to(ROOT).as_posix()
        try:
            reader = PdfReader(str(pdf))
            page_count = len(reader.pages)
            extracted_chars = sum(
                len(page.extract_text() or "") for page in reader.pages
            )
            read_pass = page_count > 0
            error = ""
        except Exception as exc:
            page_count = 0
            extracted_chars = 0
            read_pass = False
            error = f"{type(exc).__name__}: {exc}"
        prefix = render_root / pdf.stem
        if pdftoppm:
            render = subprocess.run(
                [pdftoppm, "-png", "-r", "120", str(pdf), str(prefix)],
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
            render_returncode = render.returncode
            render_stderr = render.stderr
        else:
            render_returncode = 127
            render_stderr = "pdftoppm not found"
        rendered = sorted(render_root.glob(f"{pdf.stem}-*.png"))
        render_pass = render_returncode == 0 and len(rendered) == page_count
        rows.append(
            {
                "relative_path": relative,
                "size_bytes": pdf.stat().st_size,
                "sha256": sha256_file(pdf),
                "page_count": page_count,
                "extracted_chars": extracted_chars,
                "pypdf_pass": read_pass,
                "render_returncode": render_returncode,
                "rendered_page_count": len(rendered),
                "render_pass": render_pass,
                "error": error or render_stderr[:500],
                "pass": read_pass and render_pass,
            }
        )
    visual_path = RESULT_DIR / "pdf_visual_inspection.json"
    try:
        visual = json.loads(visual_path.read_text(encoding="utf-8"))
    except Exception as exc:
        visual = {
            "pass": False,
            "status": "MISSING_PDF_VISUAL_INSPECTION",
            "error": f"{type(exc).__name__}: {exc}",
        }
    rendered_page_count = sum(int(row["rendered_page_count"]) for row in rows)
    render_pass = len(rows) == 9 and all(bool(row["pass"]) for row in rows)
    visual_pass = all(
        (
            bool(visual.get("pass")),
            int(visual.get("inspected_page_count", 0)) == rendered_page_count,
            not visual.get("defects"),
        )
    )
    payload = {
        "status": "PASS_PDF_RENDER_AND_VISUAL_AUDIT"
        if render_pass and visual_pass
        else "FAIL_PDF_RENDER_OR_VISUAL_AUDIT",
        "pass": render_pass and visual_pass,
        "pdf_count": len(rows),
        "expected_pdf_count": 9,
        "rendered_page_count": rendered_page_count,
        "records": rows,
        "visual_inspection": visual,
    }
    return rows, payload


def final_manifest_rows() -> list[dict[str, object]]:
    excluded = {
        "manifest_sha256.csv",
        "manifest_audit.json",
        "results/completion_audit.json",
    }
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if (
            relative in excluded
            or relative.startswith("tmp/")
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        rows.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def main() -> int:
    gates: list[dict[str, object]] = []
    required_files = (
        "csv/codes_all_68.csv",
        "csv/codes_fft_retained_64.csv",
        "csv/startup_periodic_pairs.csv",
        "csv/first_conversion_path.csv",
        "csv/steady_state_master_mc10.csv",
        "csv/method_transition_comparison.csv",
        "csv/percentile_bridge_master.csv",
        "csv/percentile_bridge_comparison.csv",
        "csv/resource_trace.csv",
        "results/first_conversion_status.json",
        "results/fast64_steady_state_metrics.json",
        "results/warmup_qualification.json",
        "results/numerical_split_audit.json",
        "results/mc10_execution_status.json",
        "results/method_transition_audit.json",
        "STATUS.json",
        "reports/A44_MC10_FAST64_V2_FINAL_REPORT_CN.md",
        "output/pdf/A44_MC10_FAST64_V2_FINAL_REPORT.pdf",
        "plots/plot_inventory.csv",
    )
    gates.extend(check_required_file(relative) for relative in required_files)
    gates.append(verify_input_manifest())

    base_manifest = BASE / "manifest_sha256.csv"
    base_hash = sha256_file(base_manifest) if base_manifest.is_file() else ""
    gates.append(
        {
            "gate": "BASE_PACKAGE_UNCHANGED",
            "pass": base_hash == EXPECTED_BASE_MANIFEST,
            "observed": base_hash,
            "required": EXPECTED_BASE_MANIFEST,
        }
    )

    matrix = read_csv(MANIFEST_DIR / "job_matrix.csv")
    terminal = {
        "COMPLETE",
        "COMPLETE_WITH_FAIL",
        "SIM_ERROR_UNRESOLVED",
        "MEASUREMENT_BLOCKED",
    }
    gates.append(
        {
            "gate": "FORMAL_JOB_68_TERMINAL",
            "pass": len(matrix) == 68
            and all(row.get("state") in terminal for row in matrix),
            "observed": {
                "jobs": len(matrix),
                "terminal": sum(row.get("state") in terminal for row in matrix),
            },
            "required": {"jobs": 68, "terminal": 68},
        }
    )
    unresolved = [
        row
        for row in matrix
        if row.get("state") in {"SIM_ERROR_UNRESOLVED", "MEASUREMENT_BLOCKED"}
    ]
    gates.append(
        {
            "gate": "NO_UNRESOLVED_EXECUTION",
            "pass": not unresolved,
            "observed": len(unresolved),
            "required": 0,
        }
    )
    main = read_csv(CSV_DIR / "steady_state_master_mc10.csv")
    main_codes = [
        row
        for row in read_csv(CSV_DIR / "codes_fft_retained_64.csv")
        if row.get("role") == "MAIN_MC10" and row.get("noise_mode") == "ON"
    ]
    gates.extend(
        [
            {
                "gate": "MAIN_EVENT_NOISE_20",
                "pass": len(main) == 20,
                "observed": len(main),
                "required": 20,
            },
            {
                "gate": "MAIN_RETAINED_1280",
                "pass": len(main_codes) == 1280
                and all(truth(row["retained"]) for row in main_codes),
                "observed": len(main_codes),
                "required": 1280,
            },
            {
                "gate": "MAIN_EACH_64_RETAINED",
                "pass": all(
                    sum(row["job_id"] == master["job_id"] for row in main_codes) == 64
                    for master in main
                ),
                "observed": {
                    master["job_id"]: sum(
                        row["job_id"] == master["job_id"] for row in main_codes
                    )
                    for master in main
                },
                "required": "64 per job",
            },
        ]
    )
    off_count = sum(
        row.get("phase") == "P4_FIRST_CONVERSION_COMPANION" for row in matrix
    )
    on_count = sum(row.get("phase") == "P5_EVENT_NOISE_MC10" for row in matrix)
    bridge_count = sum(row.get("phase") == "P6_PERCENTILE_BRIDGE" for row in matrix)
    gates.extend(
        [
            {
                "gate": "MAIN_NOISE_OFF_20",
                "pass": off_count == 20,
                "observed": off_count,
                "required": 20,
            },
            {
                "gate": "MAIN_NOISE_ON_20",
                "pass": on_count == 20,
                "observed": on_count,
                "required": 20,
            },
            {
                "gate": "BRIDGE_10_SEPARATE",
                "pass": bridge_count == 10
                and all(
                    not truth(row.get("included_in_main_mc10_population", True))
                    for row in read_csv(
                        CSV_DIR / "percentile_bridge_comparison.csv"
                    )
                ),
                "observed": bridge_count,
                "required": 10,
            },
        ]
    )
    warmup = json.loads(
        (RESULT_DIR / "warmup_qualification.json").read_text(encoding="utf-8")
    )
    numerical = json.loads(
        (RESULT_DIR / "numerical_split_audit.json").read_text(encoding="utf-8")
    )
    execution = json.loads(
        (RESULT_DIR / "mc10_execution_status.json").read_text(encoding="utf-8")
    )
    gates.extend(
        [
            {
                "gate": "W4_W8_QUALIFIED",
                "pass": bool(warmup["pass"]),
                "observed": warmup["status"],
                "required": "WARMUP4_QUALIFIED",
            },
            {
                "gate": "N1_F0_N1_SS_SEPARATE_AND_COMPLETE",
                "pass": numerical["comparison_pairs"] == 6
                and numerical["n1_f0_pass_count"] + sum(
                    row.get("n1_f0_status") == "N1_F0_FAIL"
                    for row in read_csv(CSV_DIR / "numerical_split_comparison.csv")
                )
                == 6
                and numerical["n1_ss_pass_count"] + sum(
                    row.get("n1_ss_status") == "N1_SS_FAIL"
                    for row in read_csv(CSV_DIR / "numerical_split_comparison.csv")
                )
                == 6,
                "observed": {
                    "pairs": numerical["comparison_pairs"],
                    "n1_f0": numerical["n1_f0_pass_count"],
                    "n1_ss": numerical["n1_ss_pass_count"],
                },
                "required": "six explicit N1_F0 and six explicit N1_SS outcomes",
            },
            {
                "gate": "RESOURCE_4_PROCESS_16_THREAD",
                "pass": bool(execution["resource_contract_pass"]),
                "observed": {
                    "processes": execution["max_ngspice_processes_observed"],
                    "threads": execution["max_ngspice_threads_observed"],
                },
                "required": {"processes_max": 4, "threads_max": 16},
            },
        ]
    )
    transition = read_csv(CSV_DIR / "method_transition_comparison.csv")
    gates.append(
        {
            "gate": "METHOD_SEMANTICS_NOT_MIXED",
            "pass": len(transition) == 20
            and all(
                row["comparison_status"]
                == "METHOD_TRANSITION_DIAGNOSTIC_COMPARISON"
                and not truth(row["strict_reproduction_claim_allowed"])
                for row in transition
            ),
            "observed": len(transition),
            "required": "20 diagnostic-only rows",
        }
    )
    plot_inventory = read_csv(ROOT / "plots/plot_inventory.csv")
    gates.append(
        {
            "gate": "EIGHT_FIGURES_TRIPLET",
            "pass": len(plot_inventory) == 8
            and all(
                (ROOT / row["pdf"]).is_file()
                and (ROOT / row["png"]).is_file()
                and (ROOT / row["source_csv"]).is_file()
                for row in plot_inventory
            ),
            "observed": len(plot_inventory),
            "required": 8,
        }
    )
    pdf_rows, pdf_payload = pdf_checks()
    write_csv_atomic(ROOT / "reports/pdf_artifact_audit.csv", pdf_rows)
    write_json_atomic(RESULT_DIR / "pdf_render_audit.json", pdf_payload)
    gates.append(
        {
            "gate": "PDF_RENDER_AUDIT",
            "pass": bool(pdf_payload["pass"]),
            "observed": {
                "pdfs": pdf_payload["pdf_count"],
                "rendered_pages": pdf_payload["rendered_page_count"],
            },
            "required": {"pdfs": 9, "all_rendered": True},
        }
    )
    completion_pass = all(bool(gate["pass"]) for gate in gates)
    completion = {
        "status": "PASS_FAST64_V2_COMPLETION_AUDIT"
        if completion_pass
        else "FAIL_FAST64_V2_COMPLETION_AUDIT",
        "pass": completion_pass,
        "gate_count": len(gates),
        "pass_count": sum(bool(gate["pass"]) for gate in gates),
        "failures": [gate for gate in gates if not gate["pass"]],
        "gates": gates,
        "completed_utc": utc_now(),
    }
    write_json_atomic(RESULT_DIR / "completion_audit.json", completion)

    manifest_rows = final_manifest_rows()
    write_csv_atomic(ROOT / "manifest_sha256.csv", manifest_rows)
    manifest_hash = sha256_file(ROOT / "manifest_sha256.csv")
    verification_failures = [
        row
        for row in manifest_rows
        if sha256_file(ROOT / row["relative_path"]) != row["sha256"]
    ]
    write_json_atomic(
        ROOT / "manifest_audit.json",
        {
            "status": "PASS_MANIFEST_AUDIT"
            if not verification_failures
            else "FAIL_MANIFEST_AUDIT",
            "pass": not verification_failures,
            "manifest_entries": len(manifest_rows),
            "manifest_sha256": manifest_hash,
            "failures": verification_failures,
            "excluded": [
                "manifest_sha256.csv",
                "manifest_audit.json",
                "results/completion_audit.json",
                "tmp/",
                "__pycache__/",
                "*.pyc",
            ],
        },
    )
    print(
        json.dumps(
            {
                "completion_status": completion["status"],
                "gate_count": completion["gate_count"],
                "failures": len(completion["failures"]),
                "manifest_entries": len(manifest_rows),
                "manifest_sha256": manifest_hash,
                "pdf_status": pdf_payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if completion_pass and not verification_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
