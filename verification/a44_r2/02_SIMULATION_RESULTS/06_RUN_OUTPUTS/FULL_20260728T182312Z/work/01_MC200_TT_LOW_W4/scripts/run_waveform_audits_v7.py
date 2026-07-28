#!/usr/bin/env python3
"""Run the six fixed full-waveform audits outside the formal population count."""

import json

import numpy as np

from run_v7 import compare_records, run_record
from sar_campaign_common import (
    FRAME_DEFAULT_S,
    PVT_CASES,
    ROOT,
    decode_frames,
    load_cdac_weights,
    run_deck,
)
from v7_common import (
    CONFIG_DIR,
    CSV_DIR,
    JOB_DIR,
    LOG_DIR,
    MANIFEST_DIR,
    RESULT_DIR,
    compact_code_checksum,
    load_manifest_checksums,
    read_csv,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def main():
    master_rows = read_csv(CSV_DIR / "dynamic_master.csv")
    formal_codes = read_csv(CSV_DIR / "dynamic_codes.csv")
    combined_rows = read_csv(CSV_DIR / "d3_combined_summary.csv")
    valid_combined = [row for row in combined_rows if as_bool(row["valid_die"])]
    if len(valid_combined) != 200:
        raise RuntimeError("full-waveform audit requires 200 valid combined dies")
    worst_values = np.asarray(
        [float(row["sndr_worst_band"]) for row in valid_combined], dtype=float
    )
    median_value = float(np.median(worst_values))
    median_row = min(
        valid_combined,
        key=lambda row: abs(float(row["sndr_worst_band"]) - median_value),
    )
    worst_row = min(valid_combined, key=lambda row: float(row["sndr_worst_band"]))
    cases = [
        ("SEED001_LOW", 1, "LOW"),
        ("SEED001_NEAR", 1, "NEAR_NYQUIST"),
        ("SEED044_LOW", 44, "LOW"),
        ("SEED044_NEAR", 44, "NEAR_NYQUIST"),
        (
            "MEDIAN_WORST_BAND_SNDR",
            int(median_row["mismatch_seed"]),
            median_row["sndr_worst_band_name"],
        ),
        (
            "WORST_OBSERVED_WORST_BAND_SNDR",
            int(worst_row["mismatch_seed"]),
            worst_row["sndr_worst_band_name"],
        ),
    ]
    cache = json.loads(
        (CONFIG_DIR / "qualification_cache.json").read_text(encoding="ascii")
    )
    maxstep_ps = int(cache["selected_formal_maxstep_ps"])
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    grouped = load_cdac_weights()
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    formal_by_key = {
        (int(row["mismatch_seed"]), row["band"]): row for row in master_rows
    }
    codes_by_key = {}
    for row in formal_codes:
        codes_by_key.setdefault((int(row["mismatch_seed"]), row["band"]), []).append(
            row
        )
    prior_audit_rows = (
        {
            row["audit_role"]: row
            for row in read_csv(CSV_DIR / "full_waveform_audit_records.csv")
        }
        if (CSV_DIR / "full_waveform_audit_records.csv").is_file()
        else {}
    )
    prior_audit_codes = (
        read_csv(CSV_DIR / "full_waveform_audit_codes.csv")
        if (CSV_DIR / "full_waveform_audit_codes.csv").is_file()
        else []
    )
    audit_rows = []
    audit_codes = []
    manifest_rows = []
    comparison_rows = []
    for role, seed, band in cases:
        if role in prior_audit_rows:
            row = dict(prior_audit_rows[role])
            codes = [
                item
                for item in prior_audit_codes
                if item["audit_role"] == role
            ]
        else:
            row, codes = run_record(
                grouped,
                timing,
                seed,
                band,
                maxstep_ps,
                f"waveform_audit_{role.lower()}",
                "FULL_WAVEFORM_AUDIT",
                mismatch_checksums,
                noise_checksums,
                preserve_raw=False,
            )
            row["audit_role"] = role
            for code in codes:
                code["audit_role"] = role
        audit_rows.append(row)
        audit_codes.extend(codes)
        formal = dict(formal_by_key[(seed, band)])
        for key in (
            "valid_frame_count",
            "invalid_count",
            "timeout_count",
            "missing_frame_count",
            "duplicate_frame_count",
            "clipping_count",
        ):
            formal[key] = int(formal[key])
        comparison_candidate = dict(row)
        for key in (
            "valid_frame_count",
            "invalid_count",
            "timeout_count",
            "missing_frame_count",
            "duplicate_frame_count",
            "clipping_count",
        ):
            comparison_candidate[key] = int(comparison_candidate[key])
        reference_codes = sorted(
            codes_by_key[(seed, band)], key=lambda item: int(item["frame_index"])
        )
        comparison = compare_records(
            formal, comparison_candidate, reference_codes, codes
        )
        comparison_rows.append(
            {
                "audit_role": role,
                "mismatch_seed": seed,
                "band": band,
                **comparison,
            }
        )
        source_deck_path = ROOT / row["deck"]
        raw_path = ROOT / "raw" / "full_waveform_audit" / f"{role.lower()}.raw"
        raw_deck = source_deck_path.read_text(encoding="ascii")
        raw_anchor = "\nquit\n.endc\n"
        if raw_deck.count(raw_anchor) != 1:
            raise RuntimeError(f"raw write anchor count invalid for {role}")
        raw_deck = raw_deck.replace(
            raw_anchor,
            f"\nwrite {raw_path}\nquit\n.endc\n",
            1,
        )
        capture = run_deck(
            raw_deck,
            f"raw_capture_{role.lower()}",
            JOB_DIR / "full_waveform_raw_capture",
            LOG_DIR / "full_waveform_raw_capture",
            timeout_s=7200,
            cache_completed_failure=True,
            raw_path=raw_path,
        )
        capture_frames = decode_frames(
            capture, 64, PVT_CASES["TT_3P3_27C"]["vdd_v"], FRAME_DEFAULT_S
        )
        capture_codes = [int(item["code"]) for item in capture_frames]
        formal_code_values = [int(item["code"]) for item in reference_codes]
        capture_equivalent = capture_codes == formal_code_values
        raw_exists = raw_path.is_file() and raw_path.stat().st_size > 0
        manifest_rows.append(
            {
                "audit_role": role,
                "mismatch_seed": seed,
                "noise_seed": 100_000 + seed,
                "band": band,
                "raw_path": str(raw_path.relative_to(ROOT)),
                "raw_size_bytes": raw_path.stat().st_size if raw_exists else "",
                "raw_sha256": sha256_file(raw_path) if raw_exists else "",
                "compact_code_checksum_sha256": row[
                    "compact_code_checksum_sha256"
                ],
                "formal_equivalence_pass": comparison["pass"],
                "raw_capture_formal_code_equivalence_pass": capture_equivalent,
                "raw_capture_code_checksum_sha256": compact_code_checksum(
                    capture_codes
                ),
                "raw_capture_returncode": capture["returncode"],
                "state": row["state"],
            }
        )
        print(
            f"AUDIT {role} seed={seed:03d} band={band} "
            f"raw={raw_path.relative_to(ROOT)} prior_equivalent={comparison['pass']} "
            f"capture_equivalent={capture_equivalent}",
            flush=True,
        )
    write_csv_atomic(CSV_DIR / "full_waveform_audit_records.csv", audit_rows)
    write_csv_atomic(CSV_DIR / "full_waveform_audit_codes.csv", audit_codes)
    write_csv_atomic(CSV_DIR / "full_waveform_audit_comparisons.csv", comparison_rows)
    write_csv_atomic(
        MANIFEST_DIR / "full_waveform_audit_manifest.csv", manifest_rows
    )
    audit = {
        "required_audit_records": 6,
        "completed_audit_records": len(audit_rows),
        "all_raw_files_present": all(row["raw_path"] for row in manifest_rows),
        "all_formal_equivalent": all(row["pass"] for row in comparison_rows),
        "formal_equivalence_required": False,
        "formal_equivalence_pass_count": sum(
            row["pass"] for row in comparison_rows
        ),
        "all_raw_capture_returncodes_zero": all(
            int(row["raw_capture_returncode"]) == 0 for row in manifest_rows
        ),
        "raw_capture_formal_code_equivalence_pass_count": sum(
            as_bool(row["raw_capture_formal_code_equivalence_pass"])
            for row in manifest_rows
        ),
        "all_states_terminal_valid": all(
            row["state"] in {"VALID_PASS", "VALID_FAIL"} for row in audit_rows
        ),
    }
    audit["pass"] = all(
        (
            audit["completed_audit_records"] == audit["required_audit_records"],
            audit["all_raw_files_present"],
            audit["all_raw_capture_returncodes_zero"],
            audit["all_states_terminal_valid"],
        )
    )
    write_json_atomic(RESULT_DIR / "full_waveform_audit.json", audit)
    if not audit["pass"]:
        raise SystemExit("full-waveform audit failed")


if __name__ == "__main__":
    main()
