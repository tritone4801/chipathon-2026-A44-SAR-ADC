#!/usr/bin/env python3
import csv
import json

from run_exact_static import exact_search
from sar_campaign_common import LSB_DIFF_V, ROOT, ensure_directories, load_cdac_weights, write_csv


CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
SEED = 2
TARGETS = (63, 64, 65, 191, 192, 193)


def read_csv(path):
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def main():
    ensure_directories(CSV_DIR, REPORT_DIR, RESULT_DIR)
    grouped = load_cdac_weights()
    reconstructed = {
        int(row["target_transition"]): float(row["transition_v"])
        for row in read_csv(CSV_DIR / "static_mc200_reconstructed.csv")
        if int(row["mismatch_seed"]) == SEED
    }
    runtime_rows = []
    evaluation_rows = []
    rows = exact_search(
        "mc_failure_confirmation",
        "TT_3P3_27C",
        "up",
        list(TARGETS),
        grouped,
        runtime_rows,
        evaluation_rows,
        mismatch_seed=SEED,
        shard_size=len(TARGETS),
        center_overrides=reconstructed,
        initial_half_lsb=0.04,
        max_expansions=8,
    )
    write_csv(CSV_DIR / "static_mc_failure_confirmation.csv", rows)
    write_csv(CSV_DIR / "static_mc_failure_confirmation_runtime.csv", runtime_rows)
    write_csv(
        CSV_DIR / "static_mc_failure_confirmation_evaluations.csv", evaluation_rows
    )
    lookup = {int(row["target_transition"]): row for row in rows}
    all_search_pass = all(row["status"] == "PASS" for row in rows)
    comparisons = []
    for lower, upper in ((63, 64), (64, 65), (191, 192), (192, 193)):
        lower_row = lookup[lower]
        upper_row = lookup[upper]
        lower_v = float(lower_row["transition_v"])
        upper_v = float(upper_row["transition_v"])
        width_lsb = (upper_v - lower_v) / LSB_DIFF_V
        min_width_lsb = (
            float(upper_row["lower_v"]) - float(lower_row["upper_v"])
        ) / LSB_DIFF_V
        max_width_lsb = (
            float(upper_row["upper_v"]) - float(lower_row["lower_v"])
        ) / LSB_DIFF_V
        dnl_failure_proven = max_width_lsb <= 0.0 or min_width_lsb >= 2.0
        comparisons.append(
            {
                "code": lower,
                "lower_transition": lower,
                "upper_transition": upper,
                "lower_v": lower_v,
                "upper_v": upper_v,
                "width_lsb_nominal": width_lsb,
                "min_width_lsb": min_width_lsb,
                "max_width_lsb": max_width_lsb,
                "dnl_failure_proven": dnl_failure_proven,
                "missing_code_strictly_proven": max_width_lsb <= 0.0,
                "lower_search_code_jump": (
                    int(lower_row["upper_code"]) - int(lower_row["lower_code"])
                ),
                "upper_search_code_jump": (
                    int(upper_row["upper_code"]) - int(upper_row["lower_code"])
                ),
            }
        )
    write_csv(CSV_DIR / "static_mc_failure_widths.csv", comparisons)
    dnl_failures = [row for row in comparisons if row["dnl_failure_proven"]]
    strict_missing = [
        row for row in comparisons if row["missing_code_strictly_proven"]
    ]
    if not all_search_pass:
        status = "BLOCKED_EXACT_SEARCH"
    elif dnl_failures:
        status = "FAIL_DNL_BOUND"
    else:
        status = "PASS_NO_FAILURE_CONFIRMED"
    payload = {
        "status": status,
        "mismatch_seed": SEED,
        "targets": list(TARGETS),
        "all_search_pass": all_search_pass,
        "proven_dnl_failure_count": len(dnl_failures),
        "strictly_proven_missing_code_count": len(strict_missing),
        "comparisons": comparisons,
        "maxstep_final_s": 5.0e-11,
        "final_bracket_requirement_lsb": 0.02,
    }
    (RESULT_DIR / "static_mc_failure_confirmation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Static MC Failure Confirmation",
        "",
        f"- Status: `{status}`",
        f"- Fixed mismatch die: `{SEED}`",
        "- PVT: `TT_3P3_27C`",
        "- Noise: `OFF`",
        "- Final maxstep: `0.05 ns`",
        "- Final bracket width: `<= 0.02 LSB`",
        "",
        "| Code | Lower T | Upper T | Nominal (LSB) | Min (LSB) | Max (LSB) | DNL fail proven | Strict missing |",
        "|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in comparisons:
        lines.append(
            f"| {row['code']} | {row['lower_transition']} | {row['upper_transition']} | "
            f"{row['width_lsb_nominal']:.6f} | {row['min_width_lsb']:.6f} | "
            f"{row['max_width_lsb']:.6f} | {row['dnl_failure_proven']} | "
            f"{row['missing_code_strictly_proven']} |"
        )
    lines.extend(
        (
            "",
            "A DNL failure is proven only when the complete conservative width interval lies outside the frozen (0, 2) LSB code-width range corresponding to DNL < +/-1 LSB.",
            "A finite bracket and a multi-code endpoint jump do not by themselves prove mathematically zero code width; that stronger missing-code claim is reported separately and is not made here unless the conservative maximum width is non-positive.",
        )
    )
    (REPORT_DIR / "static_mc_failure_confirmation.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    print(
        f"STATIC_FAILURE_CONFIRMATION status={status} dnl_failures={len(dnl_failures)} strict_missing={len(strict_missing)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
