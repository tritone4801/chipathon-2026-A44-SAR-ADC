#!/usr/bin/env python3
"""Audit the PVT3 smoke gate before formal MC20 execution."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "manifests/smoke_job_matrix.csv"
RESULTS = ROOT / "results/jobs"
OUT = ROOT / "results/smoke_audit_pvt3.json"
CANDIDATE_COMPARATOR_SHA256 = "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"
PVT = {
    "TT_3P3_27C": ("typical", "mimcap_typical", 3.3, 27),
    "SS_3P0_125C": ("ss", "mimcap_ss", 3.0, 125),
    "FF_3P6_M40C": ("ff", "mimcap_ff", 3.6, -40),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    matrix = read_csv(MATRIX)
    pairing_path = ROOT / "results/pvt_pairing_audit.json"
    pairing = json.loads(pairing_path.read_text(encoding="utf-8"))
    rows = []
    for job in matrix:
        result_path = RESULTS / f"{job['job_id']}.json"
        result = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.is_file()
            else {}
        )
        deck_path = ROOT / str(result.get("deck", ""))
        deck = (
            deck_path.read_text(encoding="utf-8", errors="replace")
            if deck_path.is_file()
            else ""
        )
        section, mim, vdd, temp = PVT[job["pvt"]]
        noise_on = job["noise_mode"] == "ON"
        checks = {
            "result_present": result_path.is_file(),
            "returncode_zero": int(result.get("returncode", -1)) == 0,
            "terminal_state": result.get("state") in {"COMPLETE", "COMPLETE_WITH_FAIL"},
            "protocol_clean": bool(result.get("protocol_clean")),
            "valid_frames_68": int(result.get("valid_frame_count", -1)) == 68,
            "total_frames_68": int(result.get("total_frames", -1)) == 68,
            "w4_4_to_67": int(result.get("retained_frame_start", -1)) == 4
            and int(result.get("retained_frame_end", -1)) == 67,
            "parseval": bool(result.get("steady_state_parseval_pass")),
            "frame0_protocol": bool(result.get("first_conversion_protocol_pass")),
            "fixed_step_50ps": abs(float(result.get("maxstep_ns", -1)) - 0.05) < 1e-15,
            "process_section": bool(
                re.search(rf"(?im)^\.lib\s+\S+\s+{re.escape(section)}\s*$", deck)
            ),
            "mim_section": bool(
                re.search(rf"(?im)^\.lib\s+\S+\s+{re.escape(mim)}\s*$", deck)
            ),
            "no_statistical_section": not bool(
                re.search(r"(?im)^\.lib\s+\S+\s+statistical\s*$", deck)
            ),
            "temperature": bool(
                re.search(rf"(?im)^\.temp\s+{re.escape(str(temp))}(?:\.0+)?\s*$", deck)
            ),
            "vdd": bool(
                re.search(
                    rf"(?im)^VVDD\s+vdd\s+0\s+{re.escape(f'{vdd:.12g}')}\s*$",
                    deck,
                )
            ),
            "legacy_rng_alignment": (
                len(re.findall(r"(?im)^RLEGACY_RNG_BURN_", deck)) == 19
                if noise_on
                else len(re.findall(r"(?im)^RLEGACY_RNG_BURN_", deck)) == 0
            ),
            "corner_scaled_logic_bridge": (
                f"in_low={0.30 * vdd:.12g}" in deck
                and f"in_high={0.70 * vdd:.12g}" in deck
                and f"out_high={vdd:.12g}" in deck
            ),
            "candidate_comparator_bound": str(
                ROOT
                / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
            )
            in deck,
        }
        rows.append(
            {
                "job_id": job["job_id"],
                "pvt": job["pvt"],
                "mismatch_seed": job["mismatch_seed"],
                "performance_status": result.get("overall_status", ""),
                "checks": checks,
                "pass": all(checks.values()),
            }
        )

    top_checks = {
        "smoke_record_count_9": len(rows) == 9,
        "all_smoke_execution_protocol_binding_pass": all(
            row["pass"] for row in rows
        ),
        "pairing_parameter_probe_pass": bool(pairing.get("pass")),
        "candidate_comparator_hash": sha256_file(
            ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
        )
        == CANDIDATE_COMPARATOR_SHA256,
    }
    payload = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "checks": top_checks,
        "pass": all(top_checks.values()),
        "performance_is_not_a_smoke_gate": True,
        "frame0_is_an_independent_functional_gate": True,
        "historical_code_compatibility_not_required_because_candidate_electrical_netlist_changed": True,
        "rows": rows,
    }
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"pass": payload["pass"], "checks": top_checks}, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
