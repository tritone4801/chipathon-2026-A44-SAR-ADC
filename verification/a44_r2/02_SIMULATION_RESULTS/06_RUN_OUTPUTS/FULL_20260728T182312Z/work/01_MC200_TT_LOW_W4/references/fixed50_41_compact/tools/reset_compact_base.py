#!/usr/bin/env python3
"""Reset a copied V10 compact package for the fixed-50-ps subset rerun."""

import json
import shutil
import sys
from pathlib import Path


EXPECTED_NAME = "A44_MC200_FIXED50PS_NONREPRO_SUBSET_RERUN_20260725_R1"


def remove(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_if_present(source: Path, destination: Path):
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: reset_compact_base.py PACKAGE_ROOT")
    root = Path(sys.argv[1]).resolve()
    if root.name != EXPECTED_NAME:
        raise RuntimeError(f"refusing unexpected root: {root}")

    frozen = root / "references" / "later_mc10_v10_original"
    frozen.mkdir(parents=True, exist_ok=True)
    preserved = (
        "csv/dynamic_master.csv",
        "csv/dynamic_codes.csv",
        "csv/selected_seed_comparison_mc10.csv",
        "results/quick_status.json",
        "results/runtime_validation_timing.json",
        "manifests/job_matrix.csv",
    )
    for relative in preserved:
        copy_if_present(root / relative, frozen / relative.replace("/", "__"))

    for name in (
        "dynamic_master.csv",
        "dynamic_codes.csv",
        "dynamic_master_mc10.csv",
        "dynamic_codes_mc10.csv",
        "selected_seed_comparison_mc10.csv",
        "representative_spectra_manifest.csv",
        "runtime_resource_trace.csv",
        "fixed50_target_master.csv",
        "fixed50_target_codes.csv",
        "fixed50_resource_trace.csv",
    ):
        remove(root / "csv" / name)

    for directory in ("jobs", "logs", "plots", "reports", "results"):
        remove(root / directory)
        (root / directory).mkdir(parents=True, exist_ok=True)

    remove(root / "manifests" / "compact_manifest_sha256.csv")
    remove(root / "manifests" / "job_matrix.csv")

    audit = {
        "status": "RESET_TO_PRE_EXECUTION",
        "active_master_absent": not (
            root / "csv" / "fixed50_target_master.csv"
        ).exists(),
        "active_codes_absent": not (
            root / "csv" / "fixed50_target_codes.csv"
        ).exists(),
        "preserved_v10_files": len(
            [path for path in frozen.iterdir() if path.is_file()]
        ),
        "original_base": "A44_FAST64_D3_MC10_1H_V10",
    }
    (root / "results" / "base_reset_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="ascii"
    )
    if not all(
        (audit["active_master_absent"], audit["active_codes_absent"])
    ):
        raise RuntimeError("active output survived reset")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
