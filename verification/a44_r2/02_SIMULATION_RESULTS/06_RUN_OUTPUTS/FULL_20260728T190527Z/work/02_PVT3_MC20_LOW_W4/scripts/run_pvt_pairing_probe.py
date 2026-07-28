#!/usr/bin/env python3
"""Probe local MOS mismatch values for PVT pairing and repeatability."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice")
NGSPICE = Path("/foss/tools/bin/ngspice")
COMPARATOR = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
PROBE_DIR = ROOT / "jobs/pvt_pairing_probe"
LOG_DIR = ROOT / "logs/pvt_pairing_probe"
RESULT = ROOT / "results/pvt_pairing_audit.json"
CASES = {
    "TT_3P3_27C": ("typical", 3.3, 27),
    "SS_3P0_125C": ("ss", 3.0, 125),
    "FF_3P6_M40C": ("ff", 3.6, -40),
}
DEVICES = ("m3", "m4", "m5", "m6")
PARAMETERS = ("delvto", "mulu0")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deck(case: str, seed: int) -> str:
    section, vdd, temp = CASES[case]
    legacy_rng_alignment = "\n".join(
        f"RLEGACY_RNG_BURN_{index:02d} legacy_rng_burn_{index:02d} 0 r='1+0*agauss(0,1,3)'"
        for index in range(1, 20)
    )
    probes = " ".join(
        f"@m.xcmp.x{device}.m0[{parameter}]"
        for device in DEVICES
        for parameter in PARAMETERS
    )
    return f"""* PVT local mismatch pairing probe.
.option seed={seed}
.param sw_stat_global=0 sw_stat_mismatch=1 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0
.lib {PDK} {section}
.include {COMPARATOR}
{legacy_rng_alignment}
.temp {temp}
VVDD vdd 0 {vdd}
VCLK clk 0 0
VINP inp 0 1.66
VINN inn 0 1.64
XCMP clk outp inp outn inn vdd 0 Comparator_StrongARM
.control
set noaskquit
op
echo PVT_PAIRING_PROBE_BEGIN
print {probes}
echo PVT_PAIRING_PROBE_END
quit
.endc
.end
"""


def parse_values(text: str) -> list[float]:
    block_match = re.search(
        r"PVT_PAIRING_PROBE_BEGIN(.*?)PVT_PAIRING_PROBE_END",
        text,
        flags=re.S,
    )
    if block_match is None:
        return []
    return [
        float(value)
        for value in re.findall(
            r"=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)",
            block_match.group(1),
            flags=re.I,
        )
    ]


def run_one(case: str, seed: int, repeat: int) -> dict[str, object]:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{case.lower()}_s{seed:03d}_r{repeat}"
    deck_text = deck(case, seed)
    deck_path = PROBE_DIR / f"{stem}.spice"
    log_path = LOG_DIR / f"{stem}.log"
    deck_path.write_text(deck_text, encoding="utf-8")
    environment = os.environ.copy()
    environment["SPICE_USERINIT_DIR"] = str(ROOT / "config/ngspice_userinit")
    process = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log_path), str(deck_path)],
        text=True,
        capture_output=True,
        env=environment,
        timeout=120,
        check=False,
    )
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    values = parse_values(log_text)
    return {
        "case": case,
        "seed": seed,
        "repeat": repeat,
        "returncode": process.returncode,
        "deck": str(deck_path.relative_to(ROOT)),
        "deck_sha256": sha256_text(deck_text),
        "log": str(log_path.relative_to(ROOT)),
        "value_count": len(values),
        "values": values,
        "value_sha256": sha256_text(json.dumps(values, separators=(",", ":"))),
    }


def main() -> int:
    runs = [
        run_one(case, seed, repeat)
        for case in CASES
        for seed in (44, 96)
        for repeat in (1, 2)
    ]
    by_key = {
        (str(row["case"]), int(row["seed"]), int(row["repeat"])): row
        for row in runs
    }
    expected_values = len(DEVICES) * len(PARAMETERS)
    all_probes_valid = all(
        int(row["returncode"]) == 0 and int(row["value_count"]) == expected_values
        for row in runs
    )
    repeatability = all(
        by_key[(case, seed, 1)]["value_sha256"]
        == by_key[(case, seed, 2)]["value_sha256"]
        for case in CASES
        for seed in (44, 96)
    )
    seed_separation = all(
        by_key[(case, 44, 1)]["value_sha256"]
        != by_key[(case, 96, 1)]["value_sha256"]
        for case in CASES
    )
    cross_corner_pairing = all(
        len(
            {
                by_key[(case, seed, 1)]["value_sha256"]
                for case in CASES
            }
        )
        == 1
        for seed in (44, 96)
    )
    checks = {
        "all_probes_valid": all_probes_valid,
        "same_seed_repeatable": repeatability,
        "different_seeds_differ": seed_separation,
        "same_seed_same_local_mismatch_across_pvt": cross_corner_pairing,
    }
    payload = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "probe_paths": [
            f"@m.xcmp.x{device}.m0[{parameter}]"
            for device in DEVICES
            for parameter in PARAMETERS
        ],
        "checks": checks,
        "pass": all(checks.values()),
        "runs": runs,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"pass": payload["pass"], "checks": checks}, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
