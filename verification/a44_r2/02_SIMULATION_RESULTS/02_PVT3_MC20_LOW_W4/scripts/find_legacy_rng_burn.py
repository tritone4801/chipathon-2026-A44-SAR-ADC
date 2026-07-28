#!/usr/bin/env python3
"""Find an explicit RNG burn that preserves legacy statistical local mismatch."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice")
COMPARATOR = ROOT / "netlists/core/subckts/Comparator_StrongARM_extracted.subckt.spice"
NGSPICE = Path("/foss/tools/bin/ngspice")
WORK = ROOT / "tmp/rng_burn_search"
LOGS = ROOT / "logs/rng_burn_search"
OUT = ROOT / "results/rng_burn_search.json"


def deck(seed: int, section: str, burns: int, legacy: bool = False) -> str:
    model = "statistical" if legacy else section
    burn_elements = "\n".join(
        f"RBURN{index} burn{index} 0 r='1+0*agauss(0,1,3)'"
        for index in range(1, burns + 1)
    )
    return f"""* Local mismatch RNG burn search.
.option seed={seed}
.param sw_stat_global=0 sw_stat_mismatch=1 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0
.lib {PDK} {model}
.include {COMPARATOR}
{burn_elements}
.temp 27
VVDD vdd 0 3.3
VCLK clk 0 0
VINP inp 0 1.66
VINN inn 0 1.64
XCMP clk outp inp outn inn vdd 0 Comparator_StrongARM
.control
set noaskquit
op
echo RNG_BURN_BEGIN
print @m.xcmp.xm3.m0[delvto] @m.xcmp.xm3.m0[mulu0]
echo RNG_BURN_END
quit
.endc
.end
"""


def run(seed: int, section: str, burns: int, legacy: bool = False) -> list[float]:
    WORK.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    tag = "legacy" if legacy else f"{section}_b{burns:02d}"
    source = WORK / f"{tag}_s{seed}.spice"
    log = LOGS / f"{tag}_s{seed}.log"
    source.write_text(deck(seed, section, burns, legacy), encoding="utf-8")
    env = os.environ.copy()
    env["SPICE_USERINIT_DIR"] = str(ROOT / "config/ngspice_userinit")
    process = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log), str(source)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    text = log.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"RNG_BURN_BEGIN(.*?)RNG_BURN_END", text, re.S)
    if process.returncode != 0 or block is None:
        return []
    return [
        float(value)
        for value in re.findall(
            r"=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)",
            block.group(1),
            re.I,
        )
    ]


def main() -> int:
    legacy = {seed: run(seed, "typical", 0, True) for seed in (44, 96)}
    rows = []
    matches = []
    for burns in range(0, 41):
        values = {seed: run(seed, "typical", burns) for seed in (44, 96)}
        match = all(values[seed] == legacy[seed] for seed in (44, 96))
        rows.append({"burns": burns, "values": values, "match_both": match})
        if match:
            matches.append(burns)
    payload = {"legacy": legacy, "matches": matches, "rows": rows}
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"matches": matches, "legacy": legacy}, indent=2))
    return 0 if matches else 2


if __name__ == "__main__":
    raise SystemExit(main())
