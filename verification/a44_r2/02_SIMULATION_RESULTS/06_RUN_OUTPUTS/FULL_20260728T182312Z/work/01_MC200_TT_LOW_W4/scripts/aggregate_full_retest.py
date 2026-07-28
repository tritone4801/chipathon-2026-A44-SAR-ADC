#!/usr/bin/env python3
"""Aggregate the completed fixed50 MC200 into per-die and population tables."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import beta

from sar_campaign_common import ROOT


VALID_STATES = {"VALID_PASS", "VALID_FAIL"}
METRICS = {
    "SNR": ("snr_db", "LOWER_IS_WORSE"),
    "SNDR": ("sndr_db", "LOWER_IS_WORSE"),
    "ENOB": ("enob_raw", "LOWER_IS_WORSE"),
    "SFDR": ("sfdr_dbc", "LOWER_IS_WORSE"),
    "THD": ("thd_db", "HIGHER_IS_WORSE"),
}
PERCENTILES = (1, 5, 10, 50, 90, 95, 99)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def as_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def exact_interval(successes, trials, alpha=0.05):
    if trials == 0:
        return float("nan"), float("nan")
    low = (
        0.0
        if successes == 0
        else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    )
    high = (
        1.0
        if successes == trials
        else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    )
    return low, high


def worst_pair(low, near, field, direction):
    low_value = float(low[field])
    near_value = float(near[field])
    if direction == "LOWER_IS_WORSE":
        return (low_value, "LOW") if low_value <= near_value else (near_value, "NEAR_NYQUIST")
    return (low_value, "LOW") if low_value >= near_value else (near_value, "NEAR_NYQUIST")


def build_combined(master):
    by_key = {(int(row["mismatch_seed"]), row["band"]): row for row in master}
    combined = []
    for seed in range(1, 201):
        low = by_key[(seed, "LOW")]
        near = by_key[(seed, "NEAR_NYQUIST")]
        valid = low["state"] in VALID_STATES and near["state"] in VALID_STATES
        row = {
            "mismatch_seed": seed,
            "noise_seed": 100000 + seed,
            "valid_die": valid,
            "die_state": (
                "VALID_PASS"
                if valid
                and as_bool(low["hard_dynamic_pass"])
                and as_bool(near["hard_dynamic_pass"])
                else ("VALID_FAIL" if valid else "UNRESOLVED")
            ),
            "hard_dynamic_pass_both": valid
            and as_bool(low["hard_dynamic_pass"])
            and as_bool(near["hard_dynamic_pass"]),
            "snr_budget_pass_both": valid
            and as_bool(low["snr_budget_pass"])
            and as_bool(near["snr_budget_pass"]),
            "preferred_nominal_pass_both": valid
            and as_bool(low["preferred_nominal_pass"])
            and as_bool(near["preferred_nominal_pass"]),
            "low_state": low["state"],
            "near_state": near["state"],
        }
        for prefix, source in (("low", low), ("near", near)):
            for _, (field, _) in METRICS.items():
                row[f"{prefix}_{field}"] = source[field]
            row[f"{prefix}_hard_dynamic_pass"] = source["hard_dynamic_pass"]
            row[f"{prefix}_snr_budget_pass"] = source["snr_budget_pass"]
            row[f"{prefix}_preferred_nominal_pass"] = source[
                "preferred_nominal_pass"
            ]
        for _, (field, direction) in METRICS.items():
            value, band = worst_pair(low, near, field, direction)
            row[f"{field}_worst_band"] = value
            row[f"{field}_worst_band_name"] = band
        combined.append(row)
    return combined


def population_scopes(master, combined):
    scopes = {
        "LOW": [row for row in master if row["band"] == "LOW"],
        "NEAR_NYQUIST": [
            row for row in master if row["band"] == "NEAR_NYQUIST"
        ],
        "WORST_BAND": [],
    }
    for row in combined:
        scopes["WORST_BAND"].append(
            {
                "mismatch_seed": row["mismatch_seed"],
                "state": row["die_state"],
                "hard_dynamic_pass": row["hard_dynamic_pass_both"],
                "snr_budget_pass": row["snr_budget_pass_both"],
                "preferred_nominal_pass": row["preferred_nominal_pass_both"],
                **{
                    field: row[f"{field}_worst_band"]
                    for field, _ in METRICS.values()
                },
            }
        )
    return scopes


def summarize(scopes):
    rows = []
    for scope, scope_rows in scopes.items():
        valid = [row for row in scope_rows if row["state"] in VALID_STATES]
        hard_pass = sum(as_bool(row["hard_dynamic_pass"]) for row in valid)
        snr_pass = sum(as_bool(row["snr_budget_pass"]) for row in valid)
        preferred_pass = sum(as_bool(row["preferred_nominal_pass"]) for row in valid)
        ci_low, ci_high = exact_interval(hard_pass, len(valid))
        for metric_name, (field, direction) in METRICS.items():
            values_and_seeds = [
                (float(row[field]), int(row["mismatch_seed"])) for row in valid
            ]
            values = np.asarray([item[0] for item in values_and_seeds], dtype=float)
            if direction == "LOWER_IS_WORSE":
                worst_index = int(np.argmin(values))
            else:
                worst_index = int(np.argmax(values))
            row = {
                "scope": scope,
                "metric": metric_name,
                "unit": {
                    "SNR": "dB",
                    "SNDR": "dB",
                    "ENOB": "bit",
                    "SFDR": "dBc",
                    "THD": "dB",
                }[metric_name],
                "worse_direction": direction,
                "required_count": 200,
                "terminal_count": len(scope_rows),
                "valid_count": len(valid),
                "unresolved_count": len(scope_rows) - len(valid),
                "hard_pass_count": hard_pass,
                "hard_fail_count": len(valid) - hard_pass,
                "snr_budget_pass_count": snr_pass,
                "snr_budget_fail_count": len(valid) - snr_pass,
                "preferred_nominal_pass_count": preferred_pass,
                "preferred_nominal_fail_count": len(valid) - preferred_pass,
                "hard_pass_rate": hard_pass / len(valid),
                "hard_pass_exact_95ci_low": ci_low,
                "hard_pass_exact_95ci_high": ci_high,
                "mean": float(np.mean(values)),
                "standard_deviation": float(np.std(values, ddof=1)),
            }
            for percentile in PERCENTILES:
                row[f"p{percentile}"] = float(
                    np.percentile(values, percentile, method="linear")
                )
            row["worst_observed"] = values_and_seeds[worst_index][0]
            row["worst_seed"] = values_and_seeds[worst_index][1]
            rows.append(row)
    return rows


def representative_manifest(master, combined):
    by_key = {(int(row["mismatch_seed"]), row["band"]): row for row in master}
    roles = []
    worst_sndr = np.asarray(
        [float(row["sndr_db_worst_band"]) for row in combined], dtype=float
    )
    for percentile in (1, 5, 10, 50):
        target = float(np.percentile(worst_sndr, percentile, method="linear"))
        selected = min(
            combined,
            key=lambda row: (
                abs(float(row["sndr_db_worst_band"]) - target),
                int(row["mismatch_seed"]),
            ),
        )
        roles.append(
            {
                "mismatch_seed": int(selected["mismatch_seed"]),
                "band": selected["sndr_db_worst_band_name"],
                "role": f"P{percentile}_WORST_BAND_SNDR",
                "selection_target_sndr_db": target,
            }
        )
    for band in ("LOW", "NEAR_NYQUIST"):
        band_rows = [
            row
            for row in master
            if row["band"] == band and row["state"] in VALID_STATES
        ]
        worst = min(
            band_rows, key=lambda row: (float(row["sndr_db"]), int(row["mismatch_seed"]))
        )
        roles.append(
            {
                "mismatch_seed": int(worst["mismatch_seed"]),
                "band": band,
                "role": f"{band}_WORST_SNDR",
                "selection_target_sndr_db": worst["sndr_db"],
            }
        )
        passing = [row for row in band_rows if as_bool(row["hard_dynamic_pass"])]
        failing = [row for row in band_rows if not as_bool(row["hard_dynamic_pass"])]
        nearest_pass = min(
            passing,
            key=lambda row: (
                abs(float(row["sndr_db"]) - 46.91),
                int(row["mismatch_seed"]),
            ),
        )
        roles.append(
            {
                "mismatch_seed": int(nearest_pass["mismatch_seed"]),
                "band": band,
                "role": f"{band}_NEAREST_HARD_PASS",
                "selection_target_sndr_db": 46.91,
            }
        )
        nearest_fail = (
            min(
                failing,
                key=lambda row: (
                    abs(float(row["sndr_db"]) - 46.91),
                    int(row["mismatch_seed"]),
                ),
            )
            if failing
            else worst
        )
        roles.append(
            {
                "mismatch_seed": int(nearest_fail["mismatch_seed"]),
                "band": band,
                "role": (
                    f"{band}_NEAREST_HARD_FAIL"
                    if failing
                    else f"{band}_WORST_PASSING_SUBSTITUTE"
                ),
                "selection_target_sndr_db": 46.91,
            }
        )
    grouped = {}
    for role in roles:
        key = (role["mismatch_seed"], role["band"])
        grouped.setdefault(key, []).append(role)
    output = []
    for key, selected_roles in sorted(grouped.items()):
        row = by_key[key]
        output.append(
            {
                "mismatch_seed": key[0],
                "noise_seed": row["noise_seed"],
                "band": key[1],
                "roles": ";".join(role["role"] for role in selected_roles),
                "role_targets_sndr_db": ";".join(
                    str(role["selection_target_sndr_db"]) for role in selected_roles
                ),
                "snr_db": row["snr_db"],
                "sndr_db": row["sndr_db"],
                "enob_raw": row["enob_raw"],
                "sfdr_dbc": row["sfdr_dbc"],
                "thd_db": row["thd_db"],
                "hard_dynamic_pass": row["hard_dynamic_pass"],
                "compact_code_checksum_sha256": row[
                    "compact_code_checksum_sha256"
                ],
            }
        )
    return output


def main() -> int:
    execution = json.loads(
        (ROOT / "results" / "execution_audit.json").read_text(encoding="utf-8")
    )
    if not execution["pass"]:
        raise RuntimeError("execution audit did not pass")
    master = read_csv(ROOT / "csv" / "dynamic_master.csv")
    combined = build_combined(master)
    scopes = population_scopes(master, combined)
    percentiles = summarize(scopes)
    representatives = representative_manifest(master, combined)
    write_csv(ROOT / "csv" / "d3_combined_summary.csv", combined)
    write_csv(ROOT / "csv" / "population_percentiles.csv", percentiles)
    write_csv(
        ROOT / "csv" / "representative_spectra_manifest.csv", representatives
    )
    hard_pass = sum(as_bool(row["hard_dynamic_pass_both"]) for row in combined)
    snr_pass = sum(as_bool(row["snr_budget_pass_both"]) for row in combined)
    preferred_pass = sum(
        as_bool(row["preferred_nominal_pass_both"]) for row in combined
    )
    status = {
        "status": (
            "PASS_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95"
            if hard_pass >= 190
            else "FAIL_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95"
        ),
        "statistics_complete": True,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "valid_dies": sum(as_bool(row["valid_die"]) for row in combined),
        "hard_pass_dies": hard_pass,
        "hard_fail_dies": 200 - hard_pass,
        "snr_budget_pass_dies": snr_pass,
        "preferred_nominal_pass_dies": preferred_pass,
        "required_hard_pass_dies": 190,
        "performance_pass": hard_pass >= 190,
        "population_scopes": ["LOW", "NEAR_NYQUIST", "WORST_BAND"],
        "percentile_method": "LINEAR_TYPE7",
        "representative_unique_spectra": len(representatives),
    }
    (ROOT / "results" / "statistics_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
