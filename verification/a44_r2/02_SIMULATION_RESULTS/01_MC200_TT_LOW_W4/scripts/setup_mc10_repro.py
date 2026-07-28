#!/usr/bin/env python3
"""Reset the copied infrastructure and freeze the current-MC200 MC10 target."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT = "A44_MC10_CURRENT_MC200_REPRO_20260725_R1"
REFERENCE = Path(
    r"C:\Users\15031\eda\designs\manual_goal\verification"
    r"\A44_MC200_FIXED50PS_FULL_RETEST_20260725_R1"
)
SELECTED = (1, 2, 3, 47, 53, 71, 74, 109, 110, 195)
BANDS = {
    "LOW": {"bin": 7, "fin_hz": 218750.0},
    "NEAR_NYQUIST": {"bin": 29, "fin_hz": 906250.0},
}
EXPECTED_HASHES = {
    "manifest_sha256.csv": "a31f1ef5482b841717ad0e4f3062523886083177bc07d3ebc7d95f41b54dd48c",
    "csv/dynamic_master.csv": "069fedf9a359cea5d81af449d3d0e284b6187ca57db0719209f0f0cdb257ecdb",
    "csv/dynamic_codes.csv": "fef09049af42a7701c0466ac41043383775d770c67a789162dc354edabde4dde",
    "config/frozen_mc200_contract.json": "55e85a33d2d1cc32dbec643247f0fc8c80b36e408f8f8600add3a1d56d468f38",
    "source_snapshot/sar_current/assembly_checks.json": "34880e6c569570c71f846ff702beeb47ec889f4c207c7d1d779639869c864473",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> int:
    if ROOT.name != EXPECTED_ROOT:
        raise RuntimeError(f"refusing unexpected root: {ROOT}")
    failures = []
    for relative, expected in EXPECTED_HASHES.items():
        path = REFERENCE / relative
        actual = sha256(path) if path.is_file() else ""
        if actual != expected:
            failures.append(
                {"relative_path": relative, "expected": expected, "actual": actual}
            )
    reference_audit = json.loads(
        (REFERENCE / "manifest_audit.json").read_text(encoding="utf-8")
    )
    if not reference_audit.get("pass"):
        failures.append({"relative_path": "manifest_audit.json", "reason": "not_pass"})
    if failures:
        raise RuntimeError(json.dumps(failures, indent=2))

    for name in (
        "comparisons",
        "diagnostics",
        "generated",
        "jobs",
        "logs",
        "plots",
        "raw",
        "reports",
        "results",
        "tmp",
    ):
        remove(ROOT / name)
        (ROOT / name).mkdir(parents=True)

    for path in (ROOT / "csv").glob("*.csv"):
        if path.name != "cdac_mismatch_weights.csv":
            path.unlink()
    for name in (
        "job_matrix.csv",
        "mismatch_seed_manifest.csv",
        "noise_seed_manifest.csv",
        "reference_bindings.json",
    ):
        remove(ROOT / "manifests" / name)
    for name in (
        "fixed50_target_contract.csv",
        "fixed50_target_contract.json",
        "frozen_mc200_contract.json",
        "plot_resolved_ranges.json",
    ):
        remove(ROOT / "config" / name)

    reference_master = [
        row
        for row in read_csv(REFERENCE / "csv" / "dynamic_master.csv")
        if int(row["mismatch_seed"]) in SELECTED
    ]
    reference_codes = [
        row
        for row in read_csv(REFERENCE / "csv" / "dynamic_codes.csv")
        if int(row["mismatch_seed"]) in SELECTED
    ]
    reference_master.sort(
        key=lambda row: (SELECTED.index(int(row["mismatch_seed"])), row["band"])
    )
    reference_codes.sort(
        key=lambda row: (
            SELECTED.index(int(row["mismatch_seed"])),
            row["band"],
            int(row["frame_index"]),
        )
    )
    target_keys = {
        (int(row["mismatch_seed"]), row["band"]) for row in reference_master
    }
    if (
        len(reference_master) != 20
        or len(reference_codes) != 1280
        or len(target_keys) != 20
    ):
        raise RuntimeError("reference extraction did not produce 20 records / 1280 codes")
    write_csv(
        ROOT / "references" / "current_mc200_target_master.csv",
        reference_master,
    )
    write_csv(
        ROOT / "references" / "current_mc200_target_codes.csv",
        reference_codes,
    )
    provenance_dir = ROOT / "references" / "current_mc200_provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    for relative in (
        "results/host_production_source_audit.json",
        "results/execution_audit.json",
        "manifest_audit.json",
    ):
        shutil.copy2(
            REFERENCE / relative,
            provenance_dir / Path(relative).name,
        )

    contract_fields = (
        "mismatch_seed",
        "noise_seed",
        "band",
        "nfft",
        "bin",
        "fin_hz",
        "maxstep_ps",
        "solver_profile",
        "execution_mode",
        "compact_code_checksum_sha256",
        "state",
        "hard_dynamic_pass",
        "snr_budget_pass",
        "preferred_nominal_pass",
        "snr_db",
        "sndr_db",
        "enob_raw",
        "sfdr_dbc",
        "thd_db",
        "mismatch_checksum_sha256",
        "noise_draw_checksum_sha256",
    )
    contract_rows = []
    for row in reference_master:
        contract_rows.append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "noise_seed": row["noise_seed"],
                "band": row["band"],
                "nfft": row["nfft"],
                "bin": row["bin"],
                "fin_hz": row["fin_hz"],
                "maxstep_ps": 50,
                "solver_profile": row["measurement_solver_profile"],
                "execution_mode": row["execution_mode"],
                "compact_code_checksum_sha256": row[
                    "compact_code_checksum_sha256"
                ],
                "state": row["state"],
                "hard_dynamic_pass": row["hard_dynamic_pass"],
                "snr_budget_pass": row["snr_budget_pass"],
                "preferred_nominal_pass": row["preferred_nominal_pass"],
                "snr_db": row["snr_db"],
                "sndr_db": row["sndr_db"],
                "enob_raw": row["enob_raw"],
                "sfdr_dbc": row["sfdr_dbc"],
                "thd_db": row["thd_db"],
                "mismatch_checksum_sha256": row["mismatch_checksum_sha256"],
                "noise_draw_checksum_sha256": row[
                    "noise_draw_checksum_sha256"
                ],
            }
        )
    write_csv(
        ROOT / "config" / "mc10_target_contract.csv",
        contract_rows,
        contract_fields,
    )
    frozen = {
        "status": "FROZEN_BEFORE_EXECUTION",
        "campaign_id": EXPECTED_ROOT,
        "scope": "CURRENT_MC200_SELECTED_MC10_STRICT_REPRODUCTION",
        "selected_seeds": list(SELECTED),
        "seed_count": 10,
        "bands": BANDS,
        "record_count": 20,
        "frames_per_record": 64,
        "code_row_count": 1280,
        "pvt": "TT_3P3_27C",
        "noise_seed_rule": "100000_plus_mismatch_seed",
        "nfft": 64,
        "sample_rate_hz": 2000000.0,
        "input_vpp_diff": 3.0,
        "input_phase_rad": 0.7853981633974483,
        "maxstep_ps": 50,
        "maxstep_ns": 0.05,
        "solver_profile": "ROBUST_GEAR",
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "worker_cap": 4,
        "measurement_method": "FROZEN_FAST64_EXISTING_ANALYZER",
        "primary_reference": str(REFERENCE),
        "reference_hashes": EXPECTED_HASHES,
        "first_run_results_are_immutable": True,
        "seed110_mandatory_repeat_count": 4,
    }
    write_json(ROOT / "config" / "mc10_target_contract.json", frozen)

    original_mismatch = read_csv(
        REFERENCE / "manifests" / "mismatch_seed_manifest.csv"
    )
    original_noise = read_csv(REFERENCE / "manifests" / "noise_seed_manifest.csv")
    write_csv(
        ROOT / "manifests" / "mismatch_seed_manifest.csv",
        [
            row
            for row in original_mismatch
            if int(row["mismatch_seed"]) in SELECTED
        ],
    )
    write_csv(
        ROOT / "manifests" / "noise_seed_manifest.csv",
        [
            row for row in original_noise if int(row["mismatch_seed"]) in SELECTED
        ],
    )

    jobs = []
    for seed in SELECTED:
        for band, spec in BANDS.items():
            jobs.append(
                {
                    "job_id": f"MC10_S{seed:03d}_{band}",
                    "mismatch_seed": seed,
                    "noise_seed": 100000 + seed,
                    "band": band,
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
    write_csv(ROOT / "manifests" / "job_matrix.csv", jobs)
    bindings = {
        "status": "FROZEN_REFERENCE_BINDINGS",
        "primary_current_mc200": {
            "root": str(REFERENCE),
            "master_sha256": EXPECTED_HASHES["csv/dynamic_master.csv"],
            "codes_sha256": EXPECTED_HASHES["csv/dynamic_codes.csv"],
            "manifest_sha256": EXPECTED_HASHES["manifest_sha256.csv"],
        },
        "secondary_references": {
            "v7_mc200": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_FAST64_D3_ONLY_MC200_V7"
            ),
            "early_mc200": (
                r"C:\Users\15031\eda\designs\manual_goal\verification"
                r"\A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
            ),
            "fixed50_41": str(ROOT / "references" / "fixed50_41_compact"),
        },
    }
    write_json(ROOT / "manifests" / "reference_bindings.json", bindings)
    receipt = {
        "status": "PASS_MC10_SETUP",
        "pass": True,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "selected_seeds": list(SELECTED),
        "target_records": len(reference_master),
        "target_code_rows": len(reference_codes),
        "target_master_sha256": sha256(
            ROOT / "references" / "current_mc200_target_master.csv"
        ),
        "target_codes_sha256": sha256(
            ROOT / "references" / "current_mc200_target_codes.csv"
        ),
        "target_contract_sha256": sha256(
            ROOT / "config" / "mc10_target_contract.json"
        ),
        "plan_sha256": sha256(
            ROOT / "A44_MC10_CURRENT_MC200_REPRO_PLAN_CN_V1.md"
        ),
        "reference_checks": {key: True for key in EXPECTED_HASHES},
        "derived_outputs_cleared": True,
    }
    write_json(ROOT / "results" / "setup_audit.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
