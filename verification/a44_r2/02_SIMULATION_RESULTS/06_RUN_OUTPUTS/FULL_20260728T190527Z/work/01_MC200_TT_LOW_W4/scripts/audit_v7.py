#!/usr/bin/env python3
"""Independent final V7 scope, binding, accounting, and artifact audit."""

import json
from pathlib import Path

from v7_common import (
    BANDS,
    CONFIG_DIR,
    CSV_DIR,
    MANIFEST_DIR,
    NFFT,
    PLOT_DIR,
    REPORT_DIR,
    REQUIRED_DIES,
    RESULT_DIR,
    read_csv,
    sha256_file,
    write_json_atomic,
)


ROOT = PLOT_DIR.parent
PRODUCTION_ROOT = Path("/foss/designs/manual_goal/analog/SAR_CURRENT")
REQUIRED_FILES = (
    "config/frozen_dynamic_config.yaml",
    "config/dependency_hashes.json",
    "config/qualification_cache.json",
    "manifests/mismatch_seed_manifest.csv",
    "manifests/noise_seed_manifest.csv",
    "manifests/job_matrix.csv",
    "csv/dynamic_master.csv",
    "csv/d3_combined_summary.csv",
    "csv/population_percentiles.csv",
    "csv/representative_spectra_manifest.csv",
    "reports/FINAL_FAST64_DYNAMIC_REPORT.md",
    "results/final_status.json",
)


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def main():
    dependency_payload = json.loads(
        (CONFIG_DIR / "dependency_hashes.json").read_text(encoding="ascii")
    )
    dependency_failures = []
    for item in dependency_payload["dependencies"]:
        path = Path(item["path"])
        if (
            not path.is_file()
            or path.stat().st_size != int(item["size_bytes"])
            or sha256_file(path) != item["sha256"]
        ):
            dependency_failures.append(item["path"])
    source_rows = read_csv(MANIFEST_DIR / "production_source_integrity.csv")
    live_source_failures = []
    for row in source_rows:
        path = PRODUCTION_ROOT / row["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["expected_size_bytes"])
            or sha256_file(path) != row["expected_sha256"]
        ):
            live_source_failures.append(row["relative_path"])
    master = read_csv(CSV_DIR / "dynamic_master.csv")
    codes = read_csv(CSV_DIR / "dynamic_codes.csv")
    combined = read_csv(CSV_DIR / "d3_combined_summary.csv")
    percentiles = read_csv(CSV_DIR / "population_percentiles.csv")
    representatives = read_csv(CSV_DIR / "representative_spectra_manifest.csv")
    jobs = read_csv(MANIFEST_DIR / "job_matrix.csv")
    plot_manifest = read_csv(MANIFEST_DIR / "plot_artifact_manifest.csv")
    waveform_manifest = read_csv(
        MANIFEST_DIR / "full_waveform_audit_manifest.csv"
    )
    final_status = json.loads(
        (RESULT_DIR / "final_status.json").read_text(encoding="ascii")
    )
    keys = {(int(row["mismatch_seed"]), row["band"]) for row in master}
    noise_pairing_pass = all(
        int(row["noise_seed"]) == 100_000 + int(row["mismatch_seed"])
        for row in master
    )
    per_die_checksums = {}
    for row in master:
        per_die_checksums.setdefault(int(row["mismatch_seed"]), set()).add(
            row["noise_draw_checksum_sha256"]
        )
    same_noise_both_bands = all(
        len(checksums) == 1 for checksums in per_die_checksums.values()
    )
    raw_failures = []
    for row in waveform_manifest:
        path = ROOT / row["raw_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["raw_size_bytes"])
            or sha256_file(path) != row["raw_sha256"]
        ):
            raw_failures.append(row["audit_role"])
    artifact_failures = []
    for row in plot_manifest:
        path = ROOT / row["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["size_bytes"])
            or sha256_file(path) != row["sha256"]
        ):
            artifact_failures.append(row["relative_path"])
    checks = {
        "required_files_present": all(
            (ROOT / relative).is_file() and (ROOT / relative).stat().st_size > 0
            for relative in REQUIRED_FILES
        ),
        "dependencies_match_frozen_hashes": not dependency_failures,
        "production_source_113_of_113_unchanged": (
            len(source_rows) == 113 and not live_source_failures
        ),
        "formal_record_count_400": len(master) == REQUIRED_DIES * len(BANDS),
        "formal_record_keys_unique_400": len(keys) == REQUIRED_DIES * len(BANDS),
        "formal_categories_d3_only": {
            row["category"] for row in master
        }
        == {"D3_NOISE_PLUS_MISMATCH_MC200"},
        "formal_bands_low_and_near_only": {row["band"] for row in master}
        == set(BANDS),
        "compact_code_rows_25600": len(codes) == REQUIRED_DIES * len(BANDS) * NFFT,
        "all_formal_records_valid_terminal": all(
            row["state"] in {"VALID_PASS", "VALID_FAIL"} for row in master
        ),
        "retry_limit_respected": all(int(row["attempt_count"]) <= 2 for row in master),
        "noise_seed_rule_pass": noise_pairing_pass,
        "same_noise_sequence_both_bands": same_noise_both_bands,
        "combined_die_rows_200": len(combined) == REQUIRED_DIES,
        "all_combined_dies_valid": all(as_bool(row["valid_die"]) for row in combined),
        "population_summary_rows_9": len(percentiles) == 9,
        "representative_spectra_p5_p1_p10_worst_band_total_3": (
            len(representatives) == 3
            and {row["role"] for row in representatives}
            == {
                "P5_WORST_BAND_SNDR",
                "P1_WORST_BAND_SNDR",
                "P10_WORST_BAND_SNDR",
            }
            and {int(row["percentile"]) for row in representatives}
            == {1, 5, 10}
            and {row["selection_scope"] for row in representatives}
            == {"WORST_BAND"}
        ),
        "population_figures_30": len(
            {
                row["figure_id"]
                for row in plot_manifest
                if row["plot_type"] != "REPRESENTATIVE_SPECTRUM"
            }
        )
        == 30,
        "plot_artifact_hashes_pass": not artifact_failures,
        "full_waveform_audit_records_6": len(waveform_manifest) == 6,
        "full_waveform_raw_hashes_pass": not raw_failures,
        "job_matrix_400_terminal": len(jobs) == 400
        and all(
            row["state"]
            in {
                "VALID_PASS",
                "VALID_FAIL",
                "SIM_ERROR_UNRESOLVED",
                "MODEL_BLOCKED",
                "MEASUREMENT_BLOCKED",
            }
            for row in jobs
        ),
        "final_status_allowed": final_status["status"]
        in {
            "PASS_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95",
            "FAIL_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95",
            "BLOCKED_INCOMPLETE_DYNAMIC_POPULATION",
            "BLOCKED_NOISE_MODEL_NOT_QUALIFIED",
            "BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED",
            "BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION",
        },
        "scope_and_performance_reported_separately": {
            "document_scope_completed",
            "performance_acceptance_pass",
        }.issubset(final_status),
        "production_yield_not_claimed": not final_status["production_yield_claim"],
    }
    audit = {
        "checks": checks,
        "pass": all(checks.values()),
        "dependency_failures": dependency_failures,
        "live_source_failures": live_source_failures,
        "raw_failures": raw_failures,
        "artifact_failures": artifact_failures,
        "final_status": final_status["status"],
    }
    write_json_atomic(RESULT_DIR / "final_independent_audit.json", audit)
    lines = [
        "# V7 Final Independent Audit",
        "",
        f"- Overall audit: `{'PASS' if audit['pass'] else 'FAIL'}`",
        f"- Final campaign status: `{audit['final_status']}`",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines.extend(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in checks.items()
    )
    (REPORT_DIR / "FINAL_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    print(
        f"INDEPENDENT_AUDIT pass={audit['pass']} checks={sum(checks.values())}/{len(checks)}"
    )
    if not audit["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
