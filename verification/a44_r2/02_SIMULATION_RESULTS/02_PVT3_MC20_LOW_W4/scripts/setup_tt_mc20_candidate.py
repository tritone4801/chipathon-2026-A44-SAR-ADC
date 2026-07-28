#!/usr/bin/env python3
"""Freeze the W5P29/W3P61 TT-only fixed MC20 campaign."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PICO = ROOT.parent
SOURCE = PICO / "A44_CMP_XM5_XM6_XM7_XM11_RESIZE_PVT3_MC20_LOW_FAST64_SS_W4_FIXED50PS_20260727_R1"
CURRENT_RESULT = PICO / "A44_CMP_XM5_XM6_XM7_XM11_RESIZE_TT_MC20_LOW_FAST64_SS_W4_FIXED50PS_20260727_R1"
CANDIDATE_ID = "CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def widths(path: Path) -> dict[str, str]:
    return dict(
        re.findall(
            r"^(XM\d+)\b.*?\bW=([^\s]+)",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )


def main() -> int:
    source_netlist = SOURCE / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    candidate_netlist = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
    current = widths(source_netlist)
    candidate = widths(candidate_netlist)
    changed = sorted(
        (name for name in candidate if candidate[name] != current[name]),
        key=lambda name: int(name[2:]),
    )
    expected = {**current, "XM5": "8.2524u", "XM6": "8.2524u"}
    unchanged_paths = (
        "scripts/dynamic_analysis.py",
        "scripts/fast64_v2_common.py",
        "scripts/run_fast64_v2.py",
        "scripts/sar_campaign_common.py",
        "scripts/sar_event_noise.py",
        "netlists/core/subckts/CDAC_native_extracted.subckt.spice",
        "netlists/core/subckts/SWITCH_BOOT_SP_native_extracted.subckt.spice",
        "models/SAR_LOGIC_BEH_TT_3P3_27C.so",
        "models/no_r6_equivalent_loads.inc",
        "config/frozen_dynamic_config.yaml",
        "config/timing_tt_3p3_27c.json",
        "config/noise_model.yaml",
        "config/plot_contract.json",
        "config/plot_style.yaml",
        "config/ngspice_userinit/.spiceinit",
        "csv/cdac_mismatch_weights.csv",
    )
    unchanged = [
        {
            "relative_path": relative,
            "source_sha256": sha(SOURCE / relative),
            "candidate_sha256": sha(ROOT / relative),
            "match": sha(SOURCE / relative) == sha(ROOT / relative),
        }
        for relative in unchanged_paths
    ]

    source_jobs = [
        row
        for row in read_csv(SOURCE / "manifests/job_matrix.csv")
        if row["pvt"] == "TT_3P3_27C"
    ]
    formal: list[dict[str, object]] = []
    for row in source_jobs:
        seed = int(row["mismatch_seed"])
        item: dict[str, object] = dict(row)
        item.update(
            {
                "job_id": f"TT_{CANDIDATE_ID}_S{seed:03d}_LOW_W4",
                "role": f"{CANDIDATE_ID}_TT_MC20_LOW",
                "state": "PENDING",
                "returncode": "",
                "elapsed_s": "",
                "overall_status": "",
                "completed_utc": "",
            }
        )
        formal.append(item)
    source_smoke = [
        row
        for row in read_csv(SOURCE / "manifests/smoke_job_matrix.csv")
        if row["pvt"] == "TT_3P3_27C"
    ]
    smoke: list[dict[str, object]] = []
    for row in source_smoke:
        item: dict[str, object] = dict(row)
        item.update(
            {
                "job_id": row["job_id"].replace("SMOKE_TT_3P3_27C", f"SMOKE_TT_{CANDIDATE_ID}"),
                "role": f"{CANDIDATE_ID}_TT_BINDING_SMOKE",
                "state": "PENDING",
                "returncode": "",
                "elapsed_s": "",
                "overall_status": "",
                "completed_utc": "",
            }
        )
        smoke.append(item)
    write_csv(ROOT / "manifests/job_matrix.csv", formal)
    write_csv(ROOT / "manifests/smoke_job_matrix.csv", smoke)

    seeds = [int(row["mismatch_seed"]) for row in formal]
    checks = {
        "source_current_netlist_hash": sha(source_netlist)
        == "54b5d6778b5a9ec6d7059bca4e2222231b6cb5a0821740d63a2b7f343250f347",
        "only_xm5_xm6_changed_from_current": changed == ["XM5", "XM6"],
        "candidate_width_map_exact": candidate == expected,
        "xm7_xm11_held": candidate["XM7"] == "16.8587u"
        and candidate["XM11"] == "16.8587u",
        "xm3_xm4_held": candidate["XM3"] == "3.51u"
        and candidate["XM4"] == "3.51u",
        "xm1_held": candidate["XM1"] == "1.56u",
        "all_other_dynamic_inputs_exact": all(row["match"] for row in unchanged),
        "formal_tt_job_count_20": len(formal) == 20,
        "smoke_tt_job_count_3": len(smoke) == 3,
        "seed_set_exact": seeds
        == [44, 26, 65, 21, 36, 2, 12, 182, 86, 80, 128, 189, 116, 190, 45, 188, 142, 53, 132, 96],
        "fixed_mc20_method": all(
            row["phase"] == "P4_PVT_TT_MC20_LOW"
            and row["pvt"] == "TT_3P3_27C"
            and int(row["warmup_frames"]) == 4
            and int(row["total_frames"]) == 68
            and int(row["retained_frame_start"]) == 4
            and int(row["retained_frame_end"]) == 67
            and int(row["nfft"]) == 64
            and int(row["bin"]) == 7
            and int(row["maxstep_ps"]) == 50
            and int(row["noise_seed"]) == 100000 + int(row["mismatch_seed"])
            for row in formal
        ),
        "current_reference_20_rows": len(
            read_csv(ROOT / "references/current_w3p61_tt_mc20_master.csv")
        )
        == 20,
        "original_reference_20_rows": len(
            read_csv(ROOT / "references/baseline_t1p000_tt_mc20.csv")
        )
        == 20,
        "current_result_manifest_pass": bool(json.loads(
            (CURRENT_RESULT / "manifest_audit.json").read_text(encoding="utf-8")
        ).get("pass")),
    }
    completed = datetime.now(timezone.utc).isoformat()
    payload = {
        "completed_utc": completed,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "method_id": "FAST64_SS_W4",
        "scope": "TT_3P3_27C_ONLY_FIXED_MC20_LOW_20_SELECTED_SEEDS",
        "candidate_id": CANDIDATE_ID,
        "checks": checks,
        "netlists": {
            "current_w3p61_sha256": sha(source_netlist),
            "candidate_sha256": sha(candidate_netlist),
            "changed_from_current": changed,
            "current_widths": current,
            "candidate_widths": candidate,
        },
        "unchanged_input_records": unchanged,
        "formal_job_count": len(formal),
        "smoke_job_count": len(smoke),
        "pass": all(checks.values()),
        "claim_boundary": "Selected TT MC20 diagnostic sample; not MC200, yield, PVT, promotion, or signoff evidence.",
    }
    (ROOT / "results/setup_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (ROOT / "STATUS.json").write_text(
        json.dumps(
            {
                "package": ROOT.name,
                "state": "SETUP_PASS" if payload["pass"] else "SETUP_FAIL",
                "stages": {
                    "setup": payload["status"],
                    "smoke": "PENDING",
                    "tt_mc20_execution": "PENDING",
                    "analysis": "PENDING",
                    "manifest": "PENDING",
                },
                "updated_utc": completed,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
