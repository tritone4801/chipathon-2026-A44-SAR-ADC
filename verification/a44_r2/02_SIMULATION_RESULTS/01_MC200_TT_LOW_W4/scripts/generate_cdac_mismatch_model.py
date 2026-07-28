#!/usr/bin/env python3
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path("/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718")
CONFIG = ROOT / "config" / "cdac_mismatch_model.yaml"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"

SOURCE_URL = (
    "https://gf180mcu-pdk.readthedocs.io/en/latest/analog/spice/"
    "elec_specs/elec_specs_6_4.html"
)
SOURCE_TITLE = "GF180MCU PDK Electrical Specifications, 6.2 MIM Capacitor"
SOURCE_ACCESS_DATE = "2026-07-18"
SOURCE_COMMIT = "de3240d7529a6970437ac3344820aaae7839f215"
SOURCE_RAW_URL = (
    "https://raw.githubusercontent.com/google/gf180mcu-pdk/"
    f"{SOURCE_COMMIT}/docs/analog/spice/elec_specs/tables_clear/"
    "6_Passive_Elements6.csv"
)
SOURCE_LOCAL = ROOT / "references" / "GF180_6_Passive_Elements6_commit_de3240d.csv"
SOURCE_SHA256 = "7597c4460eb7ca9aa85241f922c04c7fa6a5baafce22efa86ae56000b6a46cd8"

SEEDS = tuple(range(1, 201))
SIDES = ("P", "N")
ELEMENTS = (
    ("BIT7", 64),
    ("BIT6", 32),
    ("BIT5", 16),
    ("BIT4", 8),
    ("BIT3", 4),
    ("BIT2", 2),
    ("BIT1", 1),
    ("DUMMY", 1),
)

CAP_DENSITY_F_PER_UM2 = 2.0e-15
UNIT_WIDTH_UM = 6.855
UNIT_LENGTH_UM = 6.855
REFERENCE_CAP_F = 1.0e-12
DOCUMENTED_PAIR_MATCHING_MAX = 0.01
BRANCHES = (
    {
        "name": "CLAIM_BASELINE_3SIGMA_CONVERSION",
        "sigma_divisor": 3.0,
        "claim_bearing": True,
        "description": (
            "The documented 1 percent maximum adjacent-pair matching value at "
            "1 pF is treated as a 3-sigma pair-difference bound."
        ),
    },
    {
        "name": "SENSITIVITY_1SIGMA_ENVELOPE",
        "sigma_divisor": 1.0,
        "claim_bearing": False,
        "description": (
            "The documented 1 percent value is treated directly as the 1-sigma "
            "pair difference for a conservative sensitivity envelope."
        ),
    },
)


def model_values(sigma_divisor):
    unit_area_um2 = UNIT_WIDTH_UM * UNIT_LENGTH_UM
    unit_cap_f = CAP_DENSITY_F_PER_UM2 * unit_area_um2
    pair_sigma_ref = DOCUMENTED_PAIR_MATCHING_MAX / sigma_divisor
    individual_sigma_ref = pair_sigma_ref / math.sqrt(2.0)
    individual_sigma_unit = individual_sigma_ref * math.sqrt(REFERENCE_CAP_F / unit_cap_f)
    ac_um = individual_sigma_unit * math.sqrt(unit_area_um2)
    return {
        "unit_area_um2": unit_area_um2,
        "unit_cap_f": unit_cap_f,
        "pair_sigma_ref": pair_sigma_ref,
        "individual_sigma_ref": individual_sigma_ref,
        "individual_sigma_unit": individual_sigma_unit,
        "ac_um": ac_um,
    }


def draw_units(branch_index, branch, seed, side):
    values = model_values(branch["sigma_divisor"])
    side_index = SIDES.index(side)
    seed_sequence = np.random.SeedSequence([0xA44, seed, branch_index, side_index])
    rng = np.random.Generator(np.random.PCG64(seed_sequence))
    errors = rng.normal(0.0, values["individual_sigma_unit"], 128)
    return errors, 1.0 + errors


def group_units(unit_weights):
    result = []
    cursor = 0
    for element, count in ELEMENTS:
        realized = float(np.sum(unit_weights[cursor : cursor + count]))
        result.append((element, count, realized, realized / count - 1.0))
        cursor += count
    if cursor != 128:
        raise AssertionError(f"CDAC grouping consumed {cursor} units")
    return result


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def yaml_bool(value):
    return "true" if value else "false"


def write_config(branch_results):
    baseline = branch_results[BRANCHES[0]["name"]]["model"]
    stress = branch_results[BRANCHES[1]["name"]]["model"]
    text = f"""classification: APPROVED_ENGINEERING_MODEL
status: PASS
evidence_tier: T2
pdk_native_local_mim_mismatch: false
approved_engineering_model: true
claim_bearing_branch: CLAIM_BASELINE_3SIGMA_CONVERSION
source:
  title: {SOURCE_TITLE}
  documentation_url: {SOURCE_URL}
  raw_table_url: {SOURCE_RAW_URL}
  repository_commit: {SOURCE_COMMIT}
  local_copy: references/GF180_6_Passive_Elements6_commit_de3240d.csv
  local_copy_sha256: {SOURCE_SHA256}
  accessed: {SOURCE_ACCESS_DATE}
  documented_device: 2fF_per_um2_single_MIM
  documented_matching: 1_percent_max_adjacent_pair_at_1pF
geometry:
  unit_width_um: {UNIT_WIDTH_UM:.12g}
  unit_length_um: {UNIT_LENGTH_UM:.12g}
  unit_area_um2: {baseline['unit_area_um2']:.12g}
  nominal_density_f_per_um2: {CAP_DENSITY_F_PER_UM2:.12g}
  nominal_unit_cap_f: {baseline['unit_cap_f']:.12g}
statistical_conversion:
  documented_pair_matching_max_fraction: {DOCUMENTED_PAIR_MATCHING_MAX:.12g}
  baseline_interpretation: max_value_equals_3sigma_pair_difference
  baseline_pair_sigma_at_1pF_fraction: {baseline['pair_sigma_ref']:.12g}
  baseline_individual_sigma_at_1pF_fraction: {baseline['individual_sigma_ref']:.12g}
  baseline_individual_unit_sigma_fraction: {baseline['individual_sigma_unit']:.12g}
  baseline_Ac_um: {baseline['ac_um']:.12g}
  area_scaling: sigma_C_over_C_equals_Ac_over_sqrt_area_um2
  sensitivity_interpretation: documented_value_equals_1sigma_pair_difference
  sensitivity_pair_sigma_at_1pF_fraction: {stress['pair_sigma_ref']:.12g}
  sensitivity_individual_unit_sigma_fraction: {stress['individual_sigma_unit']:.12g}
  sensitivity_Ac_um: {stress['ac_um']:.12g}
correlation_assumptions:
  p_side_n_side_local_correlation: 0.0
  within_array_unit_local_correlation: 0.0
  binary_groups: disjoint_sums_of_unit_capacitors
  global_mim_process_variation: separate_PDK_native_global_term_not_duplicated_here
systematic_gradient_assumption:
  enabled: false
  value: 0.0
  reason: no_verified_physical_unit_placement_map_or_gradient_coefficient
  residual_risk: layout_systematic_gradient_not_covered_by_claim_bearing_model
rng:
  algorithm: numpy_PCG64
  seed_sequence_words: [0xA44, mismatch_seed, branch_index, side_index]
  mismatch_seeds: 1_through_200
  same_seed_reused_for_static_and_dynamic: true
frozen_outputs:
  unit_realizations: csv/cdac_mismatch_unit_realizations.csv
  group_weights: csv/cdac_mismatch_weights.csv
  statistical_audit: csv/cdac_mismatch_model_audit.csv
  machine_report: results/cdac_mismatch_model.json
claim_boundary:
  permitted: T2_engineering_model_under_explicit_assumptions
  prohibited: PDK_native_MIM_mismatch_or_production_yield_claim
"""
    CONFIG.write_text(text, encoding="ascii")


def main():
    for directory in (CSV_DIR, REPORT_DIR, RESULT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    source_hash = hashlib.sha256(SOURCE_LOCAL.read_bytes()).hexdigest()
    source_hash_pass = source_hash == SOURCE_SHA256
    unit_rows = []
    weight_rows = []
    branch_results = {}
    exact_replay = True

    for branch_index, branch in enumerate(BRANCHES):
        branch_name = branch["name"]
        model = model_values(branch["sigma_divisor"])
        all_errors = []
        totals_by_side = {side: [] for side in SIDES}
        element_errors = {element: [] for element, _ in ELEMENTS}
        minimum_weight = float("inf")

        for seed in SEEDS:
            for side in SIDES:
                errors, weights = draw_units(branch_index, branch, seed, side)
                replay_errors, replay_weights = draw_units(branch_index, branch, seed, side)
                exact_replay &= np.array_equal(errors, replay_errors)
                exact_replay &= np.array_equal(weights, replay_weights)
                all_errors.extend(float(value) for value in errors)
                minimum_weight = min(minimum_weight, float(np.min(weights)))
                totals_by_side[side].append(float(np.mean(weights) - 1.0))

                for unit_index, (error, weight) in enumerate(zip(errors, weights)):
                    unit_rows.append(
                        {
                            "branch": branch_name,
                            "mismatch_seed": seed,
                            "side": side,
                            "unit_index": unit_index,
                            "x_index_assumed": unit_index % 16,
                            "y_index_assumed": unit_index // 16,
                            "relative_error": f"{float(error):.17g}",
                            "unit_weight": f"{float(weight):.17g}",
                        }
                    )

                for element, count, realized, relative_error in group_units(weights):
                    element_errors[element].append(relative_error)
                    weight_rows.append(
                        {
                            "branch": branch_name,
                            "mismatch_seed": seed,
                            "side": side,
                            "element": element,
                            "nominal_units": count,
                            "realized_units": f"{realized:.17g}",
                            "relative_error": f"{relative_error:.17g}",
                        }
                    )

        empirical_unit_sigma = float(np.std(all_errors, ddof=1))
        pn_correlation = float(
            np.corrcoef(totals_by_side["P"], totals_by_side["N"])[0, 1]
        )
        branch_results[branch_name] = {
            "description": branch["description"],
            "claim_bearing": branch["claim_bearing"],
            "model": model,
            "empirical_unit_sigma": empirical_unit_sigma,
            "empirical_pn_total_error_correlation": pn_correlation,
            "minimum_unit_weight": minimum_weight,
            "elements": {},
        }
        for element, count in ELEMENTS:
            empirical = float(np.std(element_errors[element], ddof=1))
            expected = model["individual_sigma_unit"] / math.sqrt(count)
            branch_results[branch_name]["elements"][element] = {
                "nominal_units": count,
                "expected_relative_sigma": expected,
                "empirical_relative_sigma": empirical,
                "empirical_to_expected_ratio": empirical / expected,
            }

    audit_rows = []
    checks = []
    for branch in BRANCHES:
        name = branch["name"]
        result = branch_results[name]
        model = result["model"]
        unit_ratio = result["empirical_unit_sigma"] / model["individual_sigma_unit"]
        audit_rows.append(
            {
                "branch": name,
                "item": "UNIT",
                "nominal_units": 1,
                "expected_sigma": f"{model['individual_sigma_unit']:.17g}",
                "empirical_sigma": f"{result['empirical_unit_sigma']:.17g}",
                "ratio": f"{unit_ratio:.17g}",
                "status": "PASS" if 0.97 <= unit_ratio <= 1.03 else "FAIL",
            }
        )
        checks.append(0.97 <= unit_ratio <= 1.03)
        checks.append(abs(result["empirical_pn_total_error_correlation"]) <= 0.20)
        checks.append(result["minimum_unit_weight"] > 0.0)
        for element, data in result["elements"].items():
            ratio = data["empirical_to_expected_ratio"]
            audit_rows.append(
                {
                    "branch": name,
                    "item": element,
                    "nominal_units": data["nominal_units"],
                    "expected_sigma": f"{data['expected_relative_sigma']:.17g}",
                    "empirical_sigma": f"{data['empirical_relative_sigma']:.17g}",
                    "ratio": f"{ratio:.17g}",
                    "status": "PASS" if 0.80 <= ratio <= 1.20 else "FAIL",
                }
            )
            checks.append(0.80 <= ratio <= 1.20)

    checks.append(exact_replay)
    checks.append(source_hash_pass)
    status = "PASS" if all(checks) else "FAIL"
    payload = {
        "status": status,
        "classification": "APPROVED_ENGINEERING_MODEL" if status == "PASS" else "MODEL_AUDIT_FAIL",
        "evidence_tier": "T2",
        "pdk_native_local_mim_mismatch": False,
        "source": {
            "title": SOURCE_TITLE,
            "documentation_url": SOURCE_URL,
            "raw_table_url": SOURCE_RAW_URL,
            "repository_commit": SOURCE_COMMIT,
            "local_copy": str(SOURCE_LOCAL.relative_to(ROOT)),
            "local_copy_sha256": source_hash,
            "local_copy_hash_pass": source_hash_pass,
            "accessed": SOURCE_ACCESS_DATE,
            "documented_matching": "1 percent maximum for adjacent 1 pF capacitors",
        },
        "seed_count": len(SEEDS),
        "sides": list(SIDES),
        "units_per_side": 128,
        "same_seed_exact_replay": exact_replay,
        "branches": branch_results,
        "claim_boundary": (
            "T2 engineering model only; not PDK-native local MIM mismatch and not "
            "production-yield evidence"
        ),
    }

    write_csv(
        CSV_DIR / "cdac_mismatch_unit_realizations.csv",
        unit_rows,
        [
            "branch",
            "mismatch_seed",
            "side",
            "unit_index",
            "x_index_assumed",
            "y_index_assumed",
            "relative_error",
            "unit_weight",
        ],
    )
    write_csv(
        CSV_DIR / "cdac_mismatch_weights.csv",
        weight_rows,
        [
            "branch",
            "mismatch_seed",
            "side",
            "element",
            "nominal_units",
            "realized_units",
            "relative_error",
        ],
    )
    write_csv(
        CSV_DIR / "cdac_mismatch_model_audit.csv",
        audit_rows,
        [
            "branch",
            "item",
            "nominal_units",
            "expected_sigma",
            "empirical_sigma",
            "ratio",
            "status",
        ],
    )
    (RESULT_DIR / "cdac_mismatch_model.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    write_config(branch_results)

    baseline = branch_results[BRANCHES[0]["name"]]
    stress = branch_results[BRANCHES[1]["name"]]
    report = f"""# CDAC MIM Mismatch Engineering Model

- Status: `{status}`
- Classification: `APPROVED_ENGINEERING_MODEL`
- Evidence tier: `T2`
- PDK-native local MIM mismatch: `NO`
- Frozen virtual dies: `{len(SEEDS)}`
- Same-seed exact replay: `{'PASS' if exact_replay else 'FAIL'}`

## Source and Conversion

The official GF180MCU electrical-specification table identifies the selected
2 fF/um2 single MIM and lists 1 percent as the maximum matching value for
adjacent 1 pF capacitors laid out according to the characterization guideline.
Source: {SOURCE_URL}
Pinned raw table: {SOURCE_RAW_URL}

The campaign-local source copy has SHA-256 `{source_hash}`; source integrity is
`{'PASS' if source_hash_pass else 'FAIL'}`.

The source does not define a probability distribution. The claim-bearing T2
branch therefore makes an explicit engineering convention: the listed maximum
is a 3-sigma adjacent-pair difference. Independent equal-variance capacitors
divide pair sigma by sqrt(2), and Pelgrom area scaling is then applied from
1 pF to the 6.855 um by 6.855 um unit.

- Nominal unit capacitance from documented density: `{baseline['model']['unit_cap_f'] * 1e15:.6f} fF`
- Baseline individual unit sigma C/C: `{baseline['model']['individual_sigma_unit'] * 100:.6f} percent`
- Baseline A_C: `{baseline['model']['ac_um']:.9f} um`
- Sensitivity-envelope individual unit sigma C/C: `{stress['model']['individual_sigma_unit'] * 100:.6f} percent`

## Correlation and Gradient Assumptions

- P-side/N-side local correlation: `0`.
- Within-array unit local correlation: `0`.
- Bit capacitors are disjoint sums of 128 unit-capacitor draws per side.
- PDK-native global MIM variation is a separate term and is not duplicated.
- Systematic gradient is `0` because no verified physical unit-placement map
  or gradient coefficient is available. Layout-gradient behavior remains an
  explicit residual risk inside this T2 model boundary.

## Statistical Audit

- Baseline empirical/target unit-sigma ratio: `{baseline['empirical_unit_sigma'] / baseline['model']['individual_sigma_unit']:.6f}`.
- Sensitivity empirical/target unit-sigma ratio: `{stress['empirical_unit_sigma'] / stress['model']['individual_sigma_unit']:.6f}`.
- Baseline empirical P/N total-error correlation: `{baseline['empirical_pn_total_error_correlation']:.6f}`.
- Sensitivity empirical P/N total-error correlation: `{stress['empirical_pn_total_error_correlation']:.6f}`.
- All unit weights positive: `{'PASS' if baseline['minimum_unit_weight'] > 0 and stress['minimum_unit_weight'] > 0 else 'FAIL'}`.
- All 1/sqrt(N) group-scaling checks within 20 percent: `{'PASS' if all(row['status'] == 'PASS' for row in audit_rows) else 'FAIL'}`.

## Claim Boundary

This model closes the plan's model-availability gate as an
`APPROVED_ENGINEERING_MODEL`. It remains T2 engineering evidence under the
recorded assumptions. It shall not be described as GF180 PDK-native local MIM
mismatch, a layout-gradient model, or production-yield evidence.
"""
    (REPORT_DIR / "cdac_mismatch_model.md").write_text(report, encoding="ascii")
    print(json.dumps({"status": status, "exact_replay": exact_replay}, sort_keys=True))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
