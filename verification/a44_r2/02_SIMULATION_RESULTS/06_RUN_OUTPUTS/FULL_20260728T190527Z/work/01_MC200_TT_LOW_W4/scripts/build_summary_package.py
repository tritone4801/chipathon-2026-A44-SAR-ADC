#!/usr/bin/env python3
"""Build a compact, review-oriented sibling package from the sealed full package."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


FULL = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = FULL.parent / "A44_MC200_FIXED50PS_FULL_RETEST_SUMMARY_20260725_R1"

FILES = (
    "README_CN.md",
    "STATUS.json",
    "A44_MC200_FIXED50PS_FULL_RETEST_PLAN_CN_V1.md",
    "reports/FINAL_MC200_FIXED50PS_REPORT_CN.md",
    "reports/plot_contact_sheet.pdf",
    "results/execution_audit.json",
    "results/formal_execution_audit.json",
    "results/full_mc200_exit_code.txt",
    "results/host_production_source_audit.json",
    "results/repeatability_audit.json",
    "results/s110_repeatability_diagnostic.json",
    "results/s110_fullwave_audit.json",
    "results/statistics_status.json",
    "results/plot_audit.json",
    "results/pdf_audit.json",
    "results/formal_plot_visual_review.json",
    "results/completion_audit.json",
    "results/preflight_audit.json",
    "results/anchor_smoke_audit.json",
    "results/plot_style_smoke_audit.json",
    "results/plot_style_visual_review.json",
    "results/full_mc200_resource_summary.json",
    "comparisons/comparison_summary.json",
    "comparisons/comparison_by_reference.csv",
    "comparisons/frame_code_differences.csv",
    "comparisons/key_classification.csv",
    "csv/dynamic_master.csv",
    "csv/d3_combined_summary.csv",
    "csv/population_percentiles.csv",
    "csv/representative_spectra_manifest.csv",
    "csv/full_mc200_resource_trace.csv",
    "diagnostics/s110_repeatability/repeat_master.csv",
    "diagnostics/s110_repeatability/repeat_codes.csv",
    "diagnostics/s110_fullwave/fullwave_master.csv",
    "diagnostics/s110_fullwave/fullwave_codes.csv",
    "config/frozen_mc200_contract.json",
    "config/plot_contract.json",
    "config/plot_resolved_ranges.json",
    "config/qualification_cache.json",
    "manifests/reference_bindings.json",
    "manifests/job_matrix.csv",
    "manifests/mismatch_seed_manifest.csv",
    "manifests/noise_seed_manifest.csv",
    "source_snapshot/sar_current/assembly_checks.json",
    "source_snapshot/sar_current/SOURCE_BINDING.md",
    "plots/plot_inventory.csv",
    "plots/plot_source_manifest.csv",
    "jobs/v7/repeatability_fullwave_s110/s110_fullwave_explicit_all_vectors.spice",
    "logs/v7/repeatability_fullwave_s110/s110_fullwave_explicit_all_vectors.log",
)

TREES = (
    "plots/formal",
    "scripts",
)


def copy_file(relative: str, target: Path) -> None:
    source = FULL / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TARGET
    if target.exists():
        raise FileExistsError(
            f"refusing to overwrite existing compact package: {target}"
        )
    target.mkdir(parents=True)
    for relative in FILES:
        copy_file(relative, target)
    for relative in TREES:
        source = FULL / relative
        if not source.is_dir():
            raise FileNotFoundError(source)
        shutil.copytree(
            source,
            target / relative,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    # Bind the compact package to the sealed full-package inventory without
    # confusing it with the compact package's own root manifest.
    provenance = target / "manifests"
    provenance.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        FULL / "manifest_sha256.csv",
        provenance / "full_package_manifest_sha256.csv",
    )
    shutil.copy2(
        FULL / "manifest_audit.json",
        provenance / "full_package_manifest_audit.json",
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
