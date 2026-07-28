#!/usr/bin/env python3
"""Reset a copied fixed50 package and freeze a fresh 200-die full retest."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_ROOT = "A44_MC200_FIXED50PS_FULL_RETEST_20260725_R1"
BASE_PACKAGE = "A44_MC200_FIXED50PS_NONREPRO_SUBSET_RERUN_20260725_R1"
BANDS = {
    "LOW": {"bin": 7, "fin_hz": 218750.0},
    "NEAR_NYQUIST": {"bin": 29, "fin_hz": 906250.0},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows, fieldnames) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def verify_copied_base(root: Path) -> dict:
    manifest = root / "manifest_sha256.csv"
    failures = []
    rows = []
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        path = root / row["relative_path"]
        if not path.is_file():
            failures.append({"path": row["relative_path"], "reason": "missing"})
        elif path.stat().st_size != int(row["size_bytes"]):
            failures.append({"path": row["relative_path"], "reason": "size"})
        elif sha256(path) != row["sha256"]:
            failures.append({"path": row["relative_path"], "reason": "sha256"})
    return {
        "status": "PASS_BASE_COPY_INTEGRITY" if not failures else "FAIL_BASE_COPY_INTEGRITY",
        "pass": not failures,
        "base_package": BASE_PACKAGE,
        "manifest_entries_checked": len(rows),
        "source_manifest_sha256": sha256(manifest),
        "failures": failures,
    }


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if root.name != EXPECTED_ROOT:
        raise RuntimeError(f"refusing unexpected root: {root}")

    base_audit = verify_copied_base(root)
    if not base_audit["pass"]:
        raise RuntimeError(json.dumps(base_audit, indent=2))

    references = root / "references"
    fixed_reference = references / "fixed50_41_compact"
    if (root / "evidence").is_dir() and not fixed_reference.exists():
        fixed_reference.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / "evidence"), str(fixed_reference))

    for directory in ("jobs", "logs", "plots", "plots_legacy_v7", "raw", "reports", "results"):
        remove(root / directory)
        (root / directory).mkdir(parents=True, exist_ok=True)

    csv_dir = root / "csv"
    for path in csv_dir.glob("*.csv"):
        if path.name not in {
            "cdac_weights_mc200.csv",
            "cdac_mismatch_weights.csv",
        }:
            remove(path)

    for name in (
        "job_matrix.csv",
        "plot_artifact_manifest.csv",
        "full_waveform_audit_manifest.csv",
    ):
        remove(root / "manifests" / name)
    for name in ("manifest_sha256.csv", "manifest_audit.json", "README_CN.md", "STATUS.json"):
        remove(root / name)

    contract = {
        "status": "FROZEN_BEFORE_EXECUTION",
        "campaign_id": EXPECTED_ROOT,
        "scope": "D3_FAST64_MC200_FULL_RETEST",
        "pvt": "TT_3P3_27C",
        "mismatch_seeds": {"first": 1, "last": 200, "count": 200},
        "noise_seed_rule": "100000_plus_mismatch_seed",
        "bands": BANDS,
        "record_count": 400,
        "frames_per_record": 64,
        "code_row_count": 25600,
        "nfft": 64,
        "sample_rate_hz": 2000000.0,
        "input_vpp_diff": 3.0,
        "input_phase_rad": 0.7853981633974483,
        "maxstep_ps": 50,
        "maxstep_ns": 0.05,
        "solver_profile": "ROBUST_GEAR",
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "worker_cap": 4,
        "performance_early_stop": False,
        "measurement_method": "FROZEN_FAST64_EXISTING_ANALYZER",
        "fixed50_41_repeatability_required_records": 41,
        "full_mc200_performance_minimum_hard_pass_dies": 190,
        "full_mc200_required_valid_dies": 200,
    }
    write_json(root / "config" / "frozen_mc200_contract.json", contract)

    plot_contract = {
        "status": "FROZEN_BEFORE_EXECUTION",
        "formal_spectrum": {
            "x_label": "Frequency [MHz]",
            "y_label": "Amplitude [dBFS/bin]",
            "x_range_mhz": [0.0, 1.0],
            "default_y_range_dbfs_per_bin": [-100.0, 0.0],
            "display": "DISCRETE_FFT_BINS_NO_SMOOTHING",
            "mark": ["fundamental", "HD2", "HD3", "largest_spur"],
        },
        "formal_formats": ["PDF_VECTOR", "PNG_300_DPI", "SOURCE_CSV"],
        "font_family": ["Times New Roman", "DejaVu Serif"],
        "axis_label_pt": 10,
        "tick_label_pt": 9,
        "no_smoothing": True,
        "no_spline": True,
        "no_tail_clipping": True,
        "ecdf": "SORTED_OBSERVATIONS_I_OVER_N_STEP",
        "percentile_method": "LINEAR_TYPE7",
        "representative_tie_break": "NEAREST_OBSERVED_THEN_LOWEST_SEED",
        "formal_scopes": ["LOW", "NEAR_NYQUIST", "WORST_BAND"],
        "legacy_v7_output_directory": "plots_legacy_v7",
        "legacy_v7_is_formal": False,
    }
    write_json(root / "config" / "plot_contract.json", plot_contract)

    reference_bindings = {
        "status": "FROZEN_PATHS_HASHES_VERIFIED_DURING_POSTPROCESS",
        "references": {
            "EARLY_MC200": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
            ),
            "V7_MC200": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_FAST64_D3_ONLY_MC200_V7"
            ),
            "FIXED50_41": str(fixed_reference),
            "V10_MC10": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_FAST64_D3_MC10_1H_V10"
            ),
            "V11_MC10": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_FAST64_D3_MC10_EXCL3_REPRO_V11"
            ),
        },
    }
    write_json(root / "manifests" / "reference_bindings.json", reference_bindings)

    jobs = []
    for seed in range(1, 201):
        for band, spec in BANDS.items():
            jobs.append(
                {
                    "job_id": f"D3_S{seed:03d}_{band}",
                    "category": "D3_NOISE_PLUS_MISMATCH_MC200",
                    "pvt": "TT_3P3_27C",
                    "mismatch_seed": seed,
                    "noise_seed": 100000 + seed,
                    "band": band,
                    "nfft": 64,
                    "bin": spec["bin"],
                    "fin_hz": spec["fin_hz"],
                    "maxstep_ps": 50,
                    "solver_profile": "ROBUST_GEAR",
                    "required": True,
                    "state": "PENDING",
                    "attempt_count": "",
                    "measurement_stem": "",
                    "compact_code_checksum_sha256": "",
                }
            )
    write_csv(root / "manifests" / "job_matrix.csv", jobs, list(jobs[0]))

    base_audit["copied_at_utc"] = datetime.now(timezone.utc).isoformat()
    base_audit["new_package"] = EXPECTED_ROOT
    base_audit["derived_outputs_cleared"] = True
    base_audit["job_matrix_records"] = len(jobs)
    base_audit["fixed50_41_reference_present"] = fixed_reference.is_dir()
    write_json(root / "results" / "base_copy_and_reset_audit.json", base_audit)
    print(json.dumps(base_audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
