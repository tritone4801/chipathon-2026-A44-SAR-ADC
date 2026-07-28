#!/usr/bin/env python3
import csv
import json
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
WEIGHTS_CSV = ROOT / "csv" / "cdac_mismatch_weights.csv"
JOB_DIR = ROOT / "jobs" / "cdac_mismatch_validation"
RAW_DIR = ROOT / "raw" / "cdac_mismatch_validation"
LOG_DIR = ROOT / "logs" / "cdac_mismatch_validation"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
PDK = Path("/foss/pdks/gf180mcuD/libs.tech/ngspice")
NGSPICE = Path("/foss/tools/bin/ngspice")
ELEMENTS = ("BIT7", "BIT6", "BIT5", "BIT4", "BIT3", "BIT2", "BIT1")
CASES = (
    ("CLAIM_BASELINE_3SIGMA_CONVERSION", 1),
    ("CLAIM_BASELINE_3SIGMA_CONVERSION", 137),
    ("SENSITIVITY_1SIGMA_ENVELOPE", 1),
)


def load_weights():
    grouped = {}
    with WEIGHTS_CSV.open(newline="", encoding="ascii") as handle:
        for row in csv.DictReader(handle):
            key = (row["branch"], int(row["mismatch_seed"]), row["side"])
            grouped.setdefault(key, {})[row["element"]] = float(row["realized_units"])
    return grouped


def make_deck(branch, seed, grouped, raw_path):
    instances = []
    vectors = []
    for side in ("P", "N"):
        weights = grouped[(branch, seed, side)]
        total = sum(weights.values())
        for element in ELEMENTS:
            label = element.lower()
            node = f"w{side.lower()}{label[3:]}"
            weight = weights[element]
            rest = total - weight
            instances.extend(
                (
                    f"XB_{side}_{element} {node} bot cap_mim_2f0_m4m5_noshield "
                    f"c_width=6.855u c_length=6.855u m={weight:.17g}",
                    f"XR_{side}_{element} {node} 0 cap_mim_2f0_m4m5_noshield "
                    f"c_width=6.855u c_length=6.855u m={rest:.17g}",
                    f"RL_{side}_{element} {node} 0 1T",
                )
            )
            vectors.append(f"v({node})")
    return f"""* PDK MIM electrical realization of frozen T2 CDAC weights.
.option seed={seed}
.include {PDK / 'design.ngspice'}
.lib {PDK / 'sm141064.ngspice'} typical
.lib {PDK / 'sm141064.ngspice'} mimcap_typical
.temp 27
VBOT bot 0 PULSE(0 1 5n 10p 10p 20n 50n)
{chr(10).join(instances)}
.tran 50p 15n 0 50p uic
.control
set noaskquit
run
set wr_singlescale
wrdata {raw_path} {' '.join(vectors)}
quit
.endc
.end
"""


def read_vectors(path):
    data = np.loadtxt(path)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    expected_vectors = 2 * len(ELEMENTS)
    if data.shape[1] == expected_vectors + 1:
        return data[:, 0], data[:, 1:]
    if data.shape[1] == 2 * expected_vectors:
        return data[:, 0], data[:, 1::2]
    raise ValueError(f"unexpected wrdata shape {data.shape}")


def run_case(branch, seed, grouped, suffix=""):
    safe_branch = branch.lower()
    stem = f"{safe_branch}_seed{seed}{suffix}"
    deck_path = JOB_DIR / f"{stem}.spice"
    raw_path = RAW_DIR / f"{stem}.txt"
    log_path = LOG_DIR / f"{stem}.log"
    deck_path.write_text(make_deck(branch, seed, grouped, raw_path), encoding="ascii")
    if raw_path.exists():
        raw_path.unlink()
    completed = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log_path), str(deck_path)],
        cwd=JOB_DIR,
        check=False,
    )
    if completed.returncode != 0 or not raw_path.exists():
        raise RuntimeError(f"ngspice failed for {stem}: rc={completed.returncode}")
    time, values = read_vectors(raw_path)
    return time, values, deck_path, raw_path, log_path


def main():
    for directory in (JOB_DIR, RAW_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    grouped = load_weights()
    rows = []
    case_arrays = {}
    maximum_error = 0.0

    for branch, seed in CASES:
        time, values, deck_path, raw_path, log_path = run_case(branch, seed, grouped)
        case_arrays[(branch, seed)] = values
        column = 0
        for side in ("P", "N"):
            weights = grouped[(branch, seed, side)]
            total = sum(weights.values())
            for element in ELEMENTS:
                expected = weights[element] / total
                measured = float(values[-1, column])
                error = measured - expected
                maximum_error = max(maximum_error, abs(error))
                rows.append(
                    {
                        "branch": branch,
                        "mismatch_seed": seed,
                        "side": side,
                        "element": element,
                        "expected_fraction": f"{expected:.17g}",
                        "measured_fraction": f"{measured:.17g}",
                        "error_fraction": f"{error:.17g}",
                        "tstop_s": f"{float(time[-1]):.17g}",
                        "deck": str(deck_path.relative_to(ROOT)),
                        "raw": str(raw_path.relative_to(ROOT)),
                        "log": str(log_path.relative_to(ROOT)),
                        "status": "PASS" if abs(error) <= 1e-5 else "FAIL",
                    }
                )
                column += 1

    replay_branch, replay_seed = CASES[0]
    _, replay_values, _, _, _ = run_case(
        replay_branch, replay_seed, grouped, suffix="_replay"
    )
    exact_replay = np.array_equal(case_arrays[(replay_branch, replay_seed)], replay_values)
    different_seed_spread = not np.array_equal(
        case_arrays[("CLAIM_BASELINE_3SIGMA_CONVERSION", 1)],
        case_arrays[("CLAIM_BASELINE_3SIGMA_CONVERSION", 137)],
    )
    row_pass = all(row["status"] == "PASS" for row in rows)
    status = "PASS" if row_pass and exact_replay and different_seed_spread else "FAIL"

    with (CSV_DIR / "cdac_mismatch_electrical_validation.csv").open(
        "w", newline="", encoding="ascii"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "status": status,
        "classification": "T2_ENGINEERING_MODEL_PDK_MIM_ELECTRICAL_REALIZATION",
        "cases": len(CASES),
        "checked_bit_nodes": len(rows),
        "maximum_fraction_error": maximum_error,
        "tolerance_fraction": 1e-5,
        "same_seed_exact_replay": exact_replay,
        "different_seed_spread": different_seed_spread,
        "ngspice_executable": str(NGSPICE),
        "mim_subcircuit": "cap_mim_2f0_m4m5_noshield",
        "claim_boundary": "T2 realization check; not PDK-native local MIM mismatch",
    }
    (RESULT_DIR / "cdac_mismatch_electrical_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    report = f"""# CDAC Mismatch Electrical Validation

- Status: `{status}`
- Frozen model classification: `APPROVED_ENGINEERING_MODEL`, T2
- Electrical primitive: `cap_mim_2f0_m4m5_noshield`
- ngspice executable: `{NGSPICE}`
- Cases: `{len(CASES)}`
- Checked P/N bit nodes: `{len(rows)}`
- Maximum measured weight-fraction error: `{maximum_error:.9g}`
- Acceptance tolerance: `1e-5`
- Same-seed independent-process exact replay: `{'PASS' if exact_replay else 'FAIL'}`
- Different-seed spread: `{'PASS' if different_seed_spread else 'FAIL'}`

Each frozen noninteger group weight was applied as the multiplicity of the
actual GF180 MIM subcircuit. A complementary MIM multiplicity completed the
128-unit array, and the resulting capacitive-divider voltage was compared with
the analytical group-weight fraction. This validates the netlist realization
path; it does not promote the engineering mismatch distribution to PDK-native
local MIM evidence.
"""
    (REPORT_DIR / "cdac_mismatch_electrical_validation.md").write_text(
        report, encoding="ascii"
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
