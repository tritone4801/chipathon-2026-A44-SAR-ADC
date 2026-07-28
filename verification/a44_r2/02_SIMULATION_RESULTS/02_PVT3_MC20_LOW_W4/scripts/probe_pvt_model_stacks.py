#!/usr/bin/env python3
"""Compare local-mismatch RNG and process signatures for candidate model stacks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice")
COMPARATOR = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
WORK = ROOT / "tmp/model_stack_probe"
LOGS = ROOT / "logs/model_stack_probe"
OUT = ROOT / "results/model_stack_probe.json"
NGSPICE = Path("/foss/tools/bin/ngspice")

STACKS = {
    "legacy_statistical": [".lib {pdk} statistical"],
    "tt_corner": [".lib {pdk} typical"],
    "ss_corner": [".lib {pdk} ss"],
    "ff_corner": [".lib {pdk} ff"],
    "stat_then_tt": [".lib {pdk} statistical", ".lib {pdk} typical"],
    "stat_then_ss": [".lib {pdk} statistical", ".lib {pdk} ss"],
    "stat_then_ff": [".lib {pdk} statistical", ".lib {pdk} ff"],
}


def make_deck(stack: str, seed: int) -> str:
    includes = "\n".join(line.format(pdk=PDK) for line in STACKS[stack])
    return f"""* Model-stack probe.
.option seed={seed}
.param sw_stat_global=0 sw_stat_mismatch=1 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0
{includes}
.include {COMPARATOR}
.temp 27
VVDD vdd 0 3.3
VCLK clk 0 0
VINP inp 0 1.66
VINN inn 0 1.64
XCMP clk outp inp outn inn vdd 0 Comparator_StrongARM
.control
set noaskquit
op
echo STACK_PROBE_BEGIN
print @m.xcmp.xm3.m0[delvto] @m.xcmp.xm3.m0[mulu0]
echo STACK_PROBE_END
quit
.endc
.end
"""


def run(stack: str, seed: int) -> dict[str, object]:
    WORK.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    text = make_deck(stack, seed)
    deck = WORK / f"{stack}_s{seed}.spice"
    log = LOGS / f"{stack}_s{seed}.log"
    deck.write_text(text, encoding="utf-8")
    env = os.environ.copy()
    env["SPICE_USERINIT_DIR"] = str(ROOT / "config/ngspice_userinit")
    process = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log), str(deck)],
        text=True,
        capture_output=True,
        env=env,
        timeout=120,
        check=False,
    )
    log_text = log.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"STACK_PROBE_BEGIN(.*?)STACK_PROBE_END", log_text, re.S)
    values = [] if block is None else [
        float(value)
        for value in re.findall(
            r"=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)",
            block.group(1),
            re.I,
        )
    ]
    digest = hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "stack": stack,
        "seed": seed,
        "returncode": process.returncode,
        "values": values,
        "value_sha256": digest,
        "duplicate_definition_warning": "already defined" in log_text.lower()
        or "redefined" in log_text.lower(),
        "fatal_or_error": bool(re.search(r"(?im)^(fatal|error):", log_text)),
        "log": str(log.relative_to(ROOT)),
    }


def main() -> int:
    rows = [run(stack, seed) for stack in STACKS for seed in (44, 96)]
    lookup = {(row["stack"], row["seed"]): row for row in rows}
    comparisons = {
        stack: {
            str(seed): lookup[(stack, seed)]["value_sha256"]
            == lookup[("legacy_statistical", seed)]["value_sha256"]
            for seed in (44, 96)
        }
        for stack in ("tt_corner", "ss_corner", "ff_corner", "stat_then_tt", "stat_then_ss", "stat_then_ff")
    }
    payload = {"rows": rows, "matches_legacy_statistical": comparisons}
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(comparisons, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
