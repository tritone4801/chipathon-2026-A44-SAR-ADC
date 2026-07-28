#!/usr/bin/env python3
"""Freeze the LOW-only MC200 FAST64_SS_W4 campaign before simulation."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fast64_v2_common import (
    CONFIG_DIR,
    CSV_DIR,
    MANIFEST_DIR,
    METHOD_ID,
    RESULT_DIR,
    ROOT,
    STEADY_METHOD_ID,
    canonical_json_hash,
    ensure_directories,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


W4_BASE = Path("/foss/designs/A44_MC10_FAST64_V2_SS_W4_RETEST_20260725_R1")
CURRENT_MC200 = Path("/foss/designs/A44_MC200_FIXED50PS_FULL_RETEST_20260725_R1")
EXPECTED_W4_MANIFEST_SHA256 = (
    "250653c1f3748cf9739974e4dfbbb7e4908ce1e92d24496cd4e276415a2c211d"
)
EXPECTED_MC200_MATRIX_SHA256 = (
    "229faad34c29cbaf0c9c6f23ee45b8de6c8baab449163a7fa7e4610d2b7b998d"
)
EXPECTED_METHOD_SHA256 = (
    "12c4936f8039daeb28a472ed8f9cbf4193cf05e163e7357f1d17c61c3f238afe"
)
EXPECTED_ANALYZER_SHA256 = (
    "327628f51fdc0b88ee72ee14dc0c33ceb2d93a56a17c61093db9053990e0a90a"
)
EXPECTED_PLOT_CONTRACT_SHA256 = (
    "404c6c93d79a903aca609fd6f5fd873c73cb3a2150b240f5763d61a1684c98e7"
)
EXPECTED_NGSPICE_USERINIT_SHA256 = (
    "e4fedb09e98dc2f3df539fe215df79f4977d8fb3f7bcdd61c606d8bb90da1325"
)
EXPECTED_BASELINE_COMPARATOR_SHA256 = (
    "27da9f627ade204e4481ae399e1fb606002fad24a7cfe581e518dc0e5813cba8"
)
EXPECTED_CANDIDATE_COMPARATOR_SHA256 = (
    "e30b2055a880b83176f9389c8b79a13201fdd0e689ca46f3dc3f32b19436f303"
)
EXPECTED_BASELINE_W4_HASHES = {
    "steady_state_master_mc200_low_w4.csv": (
        "4ca004a5569487e19134430b35a6827bab2ef397169f298fd04fbddc336a7c7c"
    ),
    "codes_all_13600.csv": (
        "a3fddf3a6e91fae87d2e05c47279b08390b115c0f45b3b241d53095769ea4113"
    ),
    "codes_fft_retained_12800.csv": (
        "7d8f6c334e6ed441c05dc630f4041ad04728189bd259e0d1aa40c051eb17fb2d"
    ),
    "population_percentiles_w4.csv": (
        "f1f129823dc7d3c210135012595893e5265e9cc679ffe77882d08f7f4e203b0f"
    ),
    "population_summary_mc200_low_w4.json": (
        "ed3259231a440ce4e90247395555d989edbea6c6624f591abcac56982d98d71f"
    ),
    "STATUS.json": (
        "728915c280c268512ad9ada9931ccab36283d82f77f94c927894af68fb4d5a25"
    ),
    "manifest_sha256.csv": (
        "ad2975531814a181dc6d1b034a9ff25f41e963053a9d86c5a81647f364244eb1"
    ),
}

INPUT_PREFIXES = (
    "config/",
    "models/",
    "netlists/",
    "references/",
    "scripts/",
    "source_snapshot/",
    "tb/",
)
ACTIVE_INPUT_FILES = ("csv/cdac_mismatch_weights.csv",)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_lines(command: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        return [f"ERROR: {type(exc).__name__}: {exc}"]
    return (result.stdout + "\n" + result.stderr).strip().splitlines()[:20]


def environment_fingerprint() -> dict[str, object]:
    meminfo: dict[str, str] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            meminfo[key] = value.strip()
    return {
        "checked_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "ngspice": command_lines(["/foss/tools/bin/ngspice", "--version"]),
        "cpu_count": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)),
        "container_meminfo": meminfo,
        "thread_environment": {
            key: os.environ.get(key, "")
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }


def pin_binding_checks() -> list[dict[str, object]]:
    expected = {
        "netlists/core/subckts/CDAC_native_extracted.subckt.spice": (
            ".subckt CDAC "
        ),
        "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice": (
            ".subckt Comparator_StrongARM "
        ),
        "netlists/core/subckts/SWITCH_BOOT_SP_native_extracted.subckt.spice": (
            ".subckt SWITCH_BOOT_SP "
        ),
    }
    checks: list[dict[str, object]] = []
    for relative, signature in expected.items():
        path = ROOT / relative
        text = (
            path.read_text(encoding="ascii", errors="replace")
            if path.is_file()
            else ""
        )
        subckts = [
            line.strip()
            for line in text.splitlines()
            if line.lower().startswith(".subckt ")
        ]
        checks.append(
            {
                "relative_path": relative,
                "exists": path.is_file(),
                "expected_signature": signature.strip(),
                "subckt_lines": subckts,
                "pass": path.is_file()
                and any(
                    line.lower().startswith(signature.lower()) for line in subckts
                ),
                "sha256": sha256_file(path) if path.is_file() else "",
            }
        )
    behavior = ROOT / "models/SAR_LOGIC_BEH_TT_3P3_27C.so"
    checks.append(
        {
            "relative_path": behavior.relative_to(ROOT).as_posix(),
            "exists": behavior.is_file(),
            "expected_signature": "ELF shared object, campaign-local behavioral logic",
            "subckt_lines": [],
            "pass": behavior.is_file() and behavior.stat().st_size > 1024,
            "sha256": sha256_file(behavior) if behavior.is_file() else "",
        }
    )
    return checks


def active_input_paths() -> list[Path]:
    paths: set[Path] = set()
    for prefix in INPUT_PREFIXES:
        base = ROOT / prefix
        if base.is_dir():
            paths.update(path for path in base.rglob("*") if path.is_file())
    for relative in ACTIVE_INPUT_FILES:
        path = ROOT / relative
        if path.is_file():
            paths.add(path)
    return sorted(
        (
            path
            for path in paths
            if "__pycache__" not in path.relative_to(ROOT).parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def expected_jobs() -> list[dict[str, object]]:
    return [
        {
            "job_id": f"MC200_CMP_IN_A2P25_W_S{seed:03d}_LOW_W4",
            "phase": "P4_EVENT_NOISE_MC200_LOW",
            "role": "CMP_IN_A2P25_W_MC200_LOW",
            "category": "CMP_IN_A2P25_W_D3_NOISE_PLUS_MISMATCH_MC200_W4",
            "mismatch_seed": seed,
            "noise_mode": "ON",
            "noise_seed": 100_000 + seed,
            "band": "LOW",
            "pvt": "TT_3P3_27C",
            "warmup_frames": 4,
            "total_frames": 68,
            "retained_frame_start": 4,
            "retained_frame_end": 67,
            "nfft": 64,
            "bin": 7,
            "fin_hz": 218_750.0,
            "maxstep_ps": 50,
            "solver_profile": "ROBUST_GEAR",
            "required": True,
            "state": "PENDING",
        }
        for seed in range(1, 201)
    ]


def expected_smoke_jobs() -> list[dict[str, object]]:
    return [
        {
            "job_id": f"SMOKE_CMP_IN_A2P25_W_S{seed:03d}_LOW_W4",
            "phase": "P1_SMOKE",
            "role": "SMOKE_CMP_IN_A2P25_W_MC200_LOW",
            "category": "CMP_IN_A2P25_W_D3_NOISE_PLUS_MISMATCH_MC200_W4_SMOKE",
            "mismatch_seed": seed,
            "noise_mode": "ON",
            "noise_seed": 100_000 + seed,
            "band": "LOW",
            "pvt": "TT_3P3_27C",
            "warmup_frames": 4,
            "total_frames": 68,
            "retained_frame_start": 4,
            "retained_frame_end": 67,
            "nfft": 64,
            "bin": 7,
            "fin_hz": 218_750.0,
            "maxstep_ps": 50,
            "solver_profile": "ROBUST_GEAR",
            "required": True,
            "state": "PENDING",
        }
        for seed in (1, 44, 96)
    ]


def main() -> int:
    ensure_directories()
    failures: list[dict[str, object]] = []

    method_path = (
        ROOT
        / "references/method_contract/FAST64_V2_FIRST_CONVERSION_SEPARATED_CN.txt"
    )
    analyzer_path = ROOT / "scripts/dynamic_analysis.py"
    plot_contract_path = ROOT / "config/plot_contract.json"
    ngspice_userinit_path = ROOT / "config/ngspice_userinit/.spiceinit"
    frozen_hashes = {
        "method_contract": sha256_file(method_path) if method_path.is_file() else "",
        "dynamic_analyzer": (
            sha256_file(analyzer_path) if analyzer_path.is_file() else ""
        ),
        "plot_contract": (
            sha256_file(plot_contract_path) if plot_contract_path.is_file() else ""
        ),
        "ngspice_userinit": (
            sha256_file(ngspice_userinit_path)
            if ngspice_userinit_path.is_file()
            else ""
        ),
    }
    for name, observed, expected in (
        ("METHOD_CONTRACT_HASH", frozen_hashes["method_contract"], EXPECTED_METHOD_SHA256),
        ("DYNAMIC_ANALYZER_HASH", frozen_hashes["dynamic_analyzer"], EXPECTED_ANALYZER_SHA256),
        ("PLOT_CONTRACT_HASH", frozen_hashes["plot_contract"], EXPECTED_PLOT_CONTRACT_SHA256),
        (
            "NGSPICE_USERINIT_HASH",
            frozen_hashes["ngspice_userinit"],
            EXPECTED_NGSPICE_USERINIT_SHA256,
        ),
    ):
        if observed != expected:
            failures.append(
                {"gate": name, "expected": expected, "observed": observed}
            )

    w4_manifest = W4_BASE / "manifest_sha256.csv"
    w4_hash = sha256_file(w4_manifest) if w4_manifest.is_file() else ""
    if w4_hash != EXPECTED_W4_MANIFEST_SHA256:
        failures.append(
            {
                "gate": "W4_BASE_MANIFEST_HASH",
                "expected": EXPECTED_W4_MANIFEST_SHA256,
                "observed": w4_hash,
            }
        )
    try:
        w4_audit = json.loads(
            (W4_BASE / "manifest_audit.json").read_text(encoding="utf-8")
        )
    except Exception as exc:
        w4_audit = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
    if not w4_audit.get("pass"):
        failures.append({"gate": "W4_BASE_MANIFEST_AUDIT", "observed": w4_audit})

    mc200_matrix = CURRENT_MC200 / "manifests/job_matrix.csv"
    mc200_matrix_hash = sha256_file(mc200_matrix) if mc200_matrix.is_file() else ""
    if mc200_matrix_hash != EXPECTED_MC200_MATRIX_SHA256:
        failures.append(
            {
                "gate": "CURRENT_MC200_MATRIX_HASH",
                "expected": EXPECTED_MC200_MATRIX_SHA256,
                "observed": mc200_matrix_hash,
            }
        )
    low_rows = [
        row for row in read_csv(mc200_matrix) if row.get("band") == "LOW"
    ]
    low_seed_set = {int(row["mismatch_seed"]) for row in low_rows}
    low_contract_pass = all(
        (
            len(low_rows) == 200,
            low_seed_set == set(range(1, 201)),
            all(int(row["noise_seed"]) == 100_000 + int(row["mismatch_seed"]) for row in low_rows),
            all(int(row["maxstep_ps"]) == 50 for row in low_rows),
            all(row["solver_profile"] == "ROBUST_GEAR" for row in low_rows),
        )
    )
    if not low_contract_pass:
        failures.append(
            {
                "gate": "CURRENT_MC200_LOW_CONTRACT",
                "record_count": len(low_rows),
                "seed_count": len(low_seed_set),
            }
        )

    reference_copy_checks: list[dict[str, object]] = []
    for relative in (
        "csv/dynamic_master.csv",
        "csv/dynamic_codes.csv",
        "manifests/job_matrix.csv",
    ):
        source = CURRENT_MC200 / relative
        destination = (
            ROOT
            / "references/current_mc200_full"
            / Path(relative).name
        )
        observed = sha256_file(destination) if destination.is_file() else ""
        expected = sha256_file(source) if source.is_file() else ""
        row = {
            "source": str(source),
            "destination": destination.relative_to(ROOT).as_posix(),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "pass": bool(expected) and observed == expected,
        }
        reference_copy_checks.append(row)
        if not row["pass"]:
            failures.append(
                {"gate": "CURRENT_MC200_REFERENCE_COPY", "observed": row}
            )

    weight_rows = [
        row
        for row in read_csv(CSV_DIR / "cdac_mismatch_weights.csv")
        if row.get("branch") == "CLAIM_BASELINE_3SIGMA_CONVERSION"
    ]
    weight_seeds = {int(row["mismatch_seed"]) for row in weight_rows}
    if not set(range(1, 201)).issubset(weight_seeds):
        failures.append(
            {
                "gate": "MISMATCH_WEIGHT_SEED_COVERAGE",
                "missing": sorted(set(range(1, 201)) - weight_seeds),
            }
        )

    binding_checks = pin_binding_checks()
    failures.extend(
        {"gate": "ACTIVE_BINDING", "observed": row}
        for row in binding_checks
        if not row["pass"]
    )
    comparator_path = (
        ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    )
    comparator_sha256 = (
        sha256_file(comparator_path) if comparator_path.is_file() else ""
    )
    source_binding_path = (
        ROOT / "references/candidate_source/candidate_binding_audit.json"
    )
    try:
        source_binding = json.loads(source_binding_path.read_text(encoding="utf-8"))
    except Exception as exc:
        source_binding = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
    candidate_binding_pass = all(
        (
            comparator_sha256 == EXPECTED_CANDIDATE_COMPARATOR_SHA256,
            bool(source_binding.get("pass")),
            source_binding.get("candidate_sha256")
            == EXPECTED_CANDIDATE_COMPARATOR_SHA256,
            source_binding.get("baseline_sha256")
            == EXPECTED_BASELINE_COMPARATOR_SHA256,
            source_binding.get("changed_devices") == ["XM3", "XM4"],
            bool(source_binding.get("subckt_pin_order_unchanged")),
            not source_binding.get("unexpected_changes"),
        )
    )
    if not candidate_binding_pass:
        failures.append(
            {
                "gate": "CMP_IN_A2P25_W_BINDING",
                "observed_sha256": comparator_sha256,
                "source_binding": source_binding,
            }
        )
    baseline_w4_checks = []
    baseline_w4_dir = ROOT / "references/baseline_mc200_low_w4"
    for name, expected_hash in EXPECTED_BASELINE_W4_HASHES.items():
        path = baseline_w4_dir / name
        observed_hash = sha256_file(path) if path.is_file() else ""
        row = {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "expected_sha256": expected_hash,
            "observed_sha256": observed_hash,
            "pass": observed_hash == expected_hash,
        }
        baseline_w4_checks.append(row)
        if not row["pass"]:
            failures.append({"gate": "BASELINE_W4_REFERENCE", "observed": row})
    write_json_atomic(
        RESULT_DIR / "candidate_binding_audit.json",
        {
            "status": (
                "PASS_CMP_IN_A2P25_W_BINDING"
                if candidate_binding_pass
                else "FAIL_CMP_IN_A2P25_W_BINDING"
            ),
            "pass": candidate_binding_pass,
            "candidate_id": "CMP_IN_A2P25_W",
            "width_multiplier": 2.25,
            "baseline_comparator_sha256": EXPECTED_BASELINE_COMPARATOR_SHA256,
            "candidate_comparator_sha256": comparator_sha256,
            "authorized_devices": ["XM3", "XM4"],
            "authorized_change": "W=1.56u to W=3.51u",
            "source_binding_audit": source_binding_path.relative_to(ROOT).as_posix(),
            "baseline_w4_reference_checks": baseline_w4_checks,
        },
    )

    jobs = expected_jobs()
    smoke = expected_smoke_jobs()
    previous_smoke = {
        row["job_id"]: row
        for row in read_csv(MANIFEST_DIR / "smoke_job_matrix.csv")
    }
    for job in smoke:
        previous = previous_smoke.get(str(job["job_id"]))
        if previous and previous.get("state") in {
            "COMPLETE",
            "COMPLETE_WITH_FAIL",
            "SIM_ERROR_UNRESOLVED",
            "MEASUREMENT_BLOCKED",
        }:
            for field in (
                "state",
                "returncode",
                "elapsed_s",
                "overall_status",
                "completed_utc",
            ):
                if field in previous:
                    job[field] = previous[field]
    write_csv_atomic(MANIFEST_DIR / "job_matrix.csv", jobs)
    write_csv_atomic(MANIFEST_DIR / "smoke_job_matrix.csv", smoke)

    equation_contract = {
        "window": "rectangular",
        "fft": "numpy_rfft(codes)/N",
        "one_sided_power": "abs(fft)^2; double bins 1..N/2-1",
        "harmonics": "folded H2..H5; exclude DC and fundamental",
        "noise_bins": "all one-sided bins excluding DC, fundamental, and declared harmonics",
        "snr_db": "10*log10(Pfund/Pnoise)",
        "sndr_db": "10*log10(Pfund/(Pnoise+Pharm))",
        "enob_raw_bit": "(SNDR_dB-1.76)/6.02",
        "sfdr_dbc": "10*log10(Pfund/max_non_DC_non_fundamental_bin_power)",
        "thd_db": "10*log10(Pharm/Pfund)",
        "full_scale_sine_power_code2": "(255/2)^2/2",
        "parseval_relative_error_max": 1.0e-12,
        "analyzer_relative_path": "scripts/dynamic_analysis.py",
        "analyzer_sha256": frozen_hashes["dynamic_analyzer"],
    }
    contract = {
        "status": "FROZEN_BEFORE_EXECUTION",
        "campaign": ROOT.name,
        "candidate_id": "CMP_IN_A2P25_W",
        "width_multiplier": 2.25,
        "candidate_comparator_sha256": comparator_sha256,
        "baseline_comparator_sha256": EXPECTED_BASELINE_COMPARATOR_SHA256,
        "scope": "MC200_LOW_FAST64_SS_W4",
        "method_id": METHOD_ID,
        "steady_state_method_id": STEADY_METHOD_ID,
        "historical_method_id": "FAST64_STARTUP_INCLUSIVE_W0",
        "population": {
            "mismatch_seed_first": 1,
            "mismatch_seed_last": 200,
            "mismatch_seed_count": 200,
            "noise_seed_rule": "100000_plus_mismatch_seed",
            "band": "LOW",
            "formal_record_count": 200,
            "frames_per_record": 68,
            "total_code_rows": 13_600,
            "retained_code_rows": 12_800,
        },
        "measurement": {
            "pvt": "TT_3P3_27C",
            "band": "LOW",
            "sample_rate_hz": 2_000_000.0,
            "frame_period_ns": 500.0,
            "input_vpp_diff": 3.0,
            "input_phase_rad": 0.7853981633974483,
            "bin": 7,
            "fin_hz": 218_750.0,
            "window": "rectangular",
            "warmup_frames": 4,
            "total_frames": 68,
            "first_conversion_frame": 0,
            "startup_diagnostic_frames": [0, 3],
            "same_phase_reference_frame": 64,
            "retained_frames": [4, 67],
            "nfft": 64,
            "dout_aperture_ns": 480.0,
            "maxstep_ps": 50,
            "solver_profile": "ROBUST_GEAR",
            "noise_mode": "ON",
        },
        "first_conversion_gate": {
            "protocol_and_path_required": True,
            "frame0_equals_frame64_required_for_noise_on": False,
            "reason": "Independent event-noise draws make equality non-deterministic.",
        },
        "steady_state_gate": {
            "protocol_clean": True,
            "clipping_count_max": 0,
            "sndr_min_db": 46.91,
            "enob_raw_min_bit": 7.50,
            "snr_budget_min_db": 48.14,
        },
        "equation_contract": equation_contract,
        "style_contract": {
            "plot_contract_relative_path": "config/plot_contract.json",
            "plot_contract_sha256": frozen_hashes["plot_contract"],
            "vector_format": "PDF",
            "raster_format": "PNG_300_DPI",
            "source_data_format": "CSV",
            "spectrum_display": "DISCRETE_FFT_BINS_NO_SMOOTHING",
            "ecdf": "SORTED_OBSERVATIONS_I_OVER_N_STEP",
            "percentile_method": "LINEAR_TYPE7",
            "no_tail_clipping": True,
        },
        "resource_contract": {
            "workers_max": 4,
            "affinity_core_count": 12,
            "total_ngspice_threads_max": 16,
            "performance_early_stop": False,
        },
        "simulator_startup_contract": {
            "spice_userinit_dir": "config/ngspice_userinit",
            "spice_userinit_sha256": frozen_hashes["ngspice_userinit"],
            "ngbehavior": "hsa",
            "expected_log_banner": "Compatibility modes selected: hs a",
            "num_threads": 4,
            "ng_nomodcheck": True,
            "enable_noisy_r": True,
        },
        "source_boundary": {
            "w4_method_base": str(W4_BASE),
            "w4_base_manifest_sha256": w4_hash,
            "current_mc200_reference": str(CURRENT_MC200),
            "current_mc200_job_matrix_sha256": mc200_matrix_hash,
            "current_mc200_reference_copy_checks": reference_copy_checks,
            "baseline_w4_reference": (
                "references/baseline_mc200_low_w4"
            ),
            "baseline_w4_reference_checks": baseline_w4_checks,
            "live_sar_current_used": False,
        },
        "frozen_hashes": frozen_hashes,
        "binding_hashes": {
            row["relative_path"]: row["sha256"] for row in binding_checks
        },
        "created_utc": utc_now(),
        "contract_sha256": canonical_json_hash(
            {
                "method": frozen_hashes,
                "equations": equation_contract,
                "population": list(range(1, 201)),
                "noise_seed_offset": 100_000,
            }
        ),
    }
    write_json_atomic(CONFIG_DIR / "mc200_low_w4_contract.json", contract)
    write_json_atomic(
        CONFIG_DIR / "environment_fingerprint.json", environment_fingerprint()
    )

    input_rows = [
        {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in active_input_paths()
    ]
    write_csv_atomic(MANIFEST_DIR / "input_manifest_sha256.csv", input_rows)
    input_manifest_hash = sha256_file(
        MANIFEST_DIR / "input_manifest_sha256.csv"
    )
    write_json_atomic(
        MANIFEST_DIR / "input_manifest_audit.json",
        {
            "status": (
                "PASS_INPUT_MANIFEST_FREEZE"
                if not failures
                else "FAIL_INPUT_MANIFEST_FREEZE"
            ),
            "pass": not failures,
            "entries": len(input_rows),
            "manifest_sha256": input_manifest_hash,
            "failures": failures,
        },
    )
    write_json_atomic(
        RESULT_DIR / "setup_audit.json",
        {
            "status": (
                "PASS_P0_MC200_LOW_W4_FREEZE"
                if not failures
                else "FAIL_P0_MC200_LOW_W4_FREEZE"
            ),
            "pass": not failures,
            "checked_utc": utc_now(),
            "formal_job_count": len(jobs),
            "pending_job_count": sum(row["state"] == "PENDING" for row in jobs),
            "smoke_job_count": len(smoke),
            "input_manifest_entries": len(input_rows),
            "input_manifest_sha256": input_manifest_hash,
            "w4_base_manifest_sha256": w4_hash,
            "current_mc200_matrix_sha256": mc200_matrix_hash,
            "current_mc200_low_contract_pass": low_contract_pass,
            "current_mc200_reference_copy_checks": reference_copy_checks,
            "candidate_id": "CMP_IN_A2P25_W",
            "candidate_binding_pass": candidate_binding_pass,
            "candidate_comparator_sha256": comparator_sha256,
            "baseline_w4_reference_checks": baseline_w4_checks,
            "binding_checks": binding_checks,
            "failures": failures,
        },
    )
    print(
        json.dumps(
            {
                "status": (
                    "PASS_P0_MC200_LOW_W4_FREEZE"
                    if not failures
                    else "FAIL_P0_MC200_LOW_W4_FREEZE"
                ),
                "formal_jobs": len(jobs),
                "smoke_jobs": len(smoke),
                "input_manifest_entries": len(input_rows),
                "failures": len(failures),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
