#!/usr/bin/env python3
"""Container-side preflight for the fresh fixed-50-ps full MC200 retest."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sar_campaign_common import ROOT


EXPECTED_ROOT = "A44_MC200_FIXED50PS_FULL_RETEST_20260725_R1"
OLD_V7_ROOT = Path(
    "/foss/designs/manual_goal/verification/A44_FAST64_D3_ONLY_MC200_V7"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ngspice_processes():
    found = []
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text(encoding="ascii").strip() == "ngspice":
                found.append(int(comm.parent.name))
        except (FileNotFoundError, ProcessLookupError, ValueError):
            continue
    return found


def verify_dependencies():
    payload = load_json(ROOT / "config" / "dependency_hashes.json")
    checked = []
    failures = []
    host_production = load_json(
        ROOT / "results" / "host_production_source_audit.json"
    )
    for item in payload["dependencies"]:
        source = Path(item["path"])
        if source == Path(
            "/foss/designs/manual_goal/analog/SAR_CURRENT/manifests/"
            "package_manifest_sha256.csv"
        ):
            matched = (
                host_production.get("package_manifest_present") is True
                and host_production.get("package_manifest_sha256") == item["sha256"]
            )
            live = Path(host_production["production_root"]) / "manifests" / "package_manifest_sha256.csv"
            mode = "HOST_RECEIPT"
        else:
            try:
                relative = source.relative_to(OLD_V7_ROOT)
                live = ROOT / relative
                mode = "PACKAGE_REMAP"
            except ValueError:
                live = source
                mode = "CONTAINER_LIVE"
            matched = (
                live.is_file()
                and live.stat().st_size == int(item["size_bytes"])
                and sha256(live) == item["sha256"]
            )
        checked.append(
            {
                "role": item["role"],
                "declared_path": item["path"],
                "live_path": str(live),
                "mode": mode,
                "match": matched,
            }
        )
        if not matched:
            failures.append(checked[-1])
    return {
        "pass": not failures and len(checked) == 20,
        "declared": len(checked),
        "matching": len(checked) - len(failures),
        "failures": failures,
        "checked": checked,
    }


def main() -> int:
    if ROOT.name != EXPECTED_ROOT:
        raise RuntimeError(f"unexpected package root: {ROOT}")
    contract = load_json(ROOT / "config" / "frozen_mc200_contract.json")
    plot_contract = load_json(ROOT / "config" / "plot_contract.json")
    cache = load_json(ROOT / "config" / "qualification_cache.json")
    host_production = load_json(
        ROOT / "results" / "host_production_source_audit.json"
    )
    jobs = read_csv(ROOT / "manifests" / "job_matrix.csv")
    mismatch = read_csv(ROOT / "manifests" / "mismatch_seed_manifest.csv")
    noise = read_csv(ROOT / "manifests" / "noise_seed_manifest.csv")
    keys = {(int(row["mismatch_seed"]), row["band"]) for row in jobs}

    checks = {
        "host_production_113_of_113": host_production.get("pass") is True
        and host_production.get("matching_files") == 113,
        "contract_frozen": contract["status"] == "FROZEN_BEFORE_EXECUTION",
        "contract_400_records": contract["record_count"] == 400
        and contract["code_row_count"] == 25600,
        "contract_fixed_50ps": contract["maxstep_ps"] == 50
        and contract["solver_profile"] == "ROBUST_GEAR",
        "plot_contract_frozen": plot_contract["status"]
        == "FROZEN_BEFORE_EXECUTION"
        and plot_contract["no_smoothing"] is True,
        "job_matrix_400_unique": len(jobs) == 400 and len(keys) == 400,
        "job_matrix_all_pending": all(row["state"] == "PENDING" for row in jobs),
        "job_matrix_method": all(
            int(row["maxstep_ps"]) == 50
            and row["solver_profile"] == "ROBUST_GEAR"
            and int(row["nfft"]) == 64
            for row in jobs
        ),
        "mismatch_manifest_200": len(mismatch) == 200,
        "noise_manifest_200": len(noise) == 200,
        "qualification_complete": all(
            (
                cache.get("fixed_pilot_complete"),
                cache.get("numerical_qualification_pass"),
                cache.get("session_equivalence_complete"),
                cache.get("resource_admission_pass"),
            )
        ),
        "qualification_selects_50ps": int(
            cache.get("selected_formal_maxstep_ps", 0)
        )
        == 50,
        "execution_mode_fixed": cache.get("session_execution_mode")
        == "SEPARATE_PROCESS_FALLBACK",
        "four_workers_admitted": int(
            cache.get("resource", {}).get("selected_formal_workers", 0)
        )
        >= 4,
        "no_active_ngspice": not ngspice_processes(),
        "no_prior_dynamic_master": not (ROOT / "csv" / "dynamic_master.csv").exists(),
        "no_prior_dynamic_codes": not (ROOT / "csv" / "dynamic_codes.csv").exists(),
    }
    dependencies = verify_dependencies()
    checks["dependencies_20_of_20"] = dependencies["pass"]

    ngspice_version = subprocess.run(
        ["/foss/tools/bin/ngspice", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    environment = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ngspice": ngspice_version[:4],
        "cpu_count": os.cpu_count(),
        "container_meminfo": {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines()
            if line.split(":", 1)[0]
            in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
        },
    }
    (ROOT / "config" / "environment_fingerprint.json").write_text(
        json.dumps(environment, indent=2) + "\n", encoding="utf-8"
    )

    result = {
        "status": "PASS_FULL_RETEST_PREFLIGHT"
        if all(checks.values())
        else "FAIL_FULL_RETEST_PREFLIGHT",
        "pass": all(checks.values()),
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "dependencies": dependencies,
        "environment": environment,
    }
    (ROOT / "results" / "preflight_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
