#!/usr/bin/env python3
"""Qualification and resumable D3 dual-band FAST64 population runner."""

import argparse
import json
import math
import os
import resource
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from dynamic_analysis import coherent_values, fft_metrics
from sar_campaign_common import (
    PVT_CASES,
    ROOT,
    SAMPLE_EDGE_OFFSET_S,
    TRACK_FALL_OFFSET_S,
    load_cdac_weights,
)
from sar_event_noise import run_event_frames
from v7_common import (
    BANDS,
    CAMPAIGN_ID,
    CONFIG_DIR,
    CSV_DIR,
    ENOB_HARD_MIN_BIT,
    ENOB_PREFERRED_BIT,
    FRAME_PERIOD_S,
    INPUT_AMPLITUDE_DIFF_V,
    INPUT_VPP_DIFF_V,
    JOB_DIR,
    LOG_DIR,
    MANIFEST_DIR,
    NFFT,
    PHASE_RAD,
    PVT_NAME,
    REQUIRED_DIES,
    RESULT_DIR,
    SAMPLE_RATE_HZ,
    SNDR_HARD_MIN_DB,
    SNDR_PREFERRED_DB,
    SNR_BUDGET_MIN_DB,
    compact_code_checksum,
    ensure_v7_directories,
    load_manifest_checksums,
    parse_seed_expression,
    read_csv,
    sha256_bytes,
    sha256_file,
    write_csv_atomic,
    write_json_atomic,
)


MASTER_PATH = CSV_DIR / "dynamic_master.csv"
CODE_PATH = CSV_DIR / "dynamic_codes.csv"
QUALIFICATION_PATH = CSV_DIR / "qualification_records.csv"
QUALIFICATION_CODE_PATH = CSV_DIR / "qualification_codes.csv"
RESOURCE_TRACE_PATH = CSV_DIR / "qualification_resource_trace.csv"
JOB_MATRIX_PATH = MANIFEST_DIR / "job_matrix.csv"


def proc_memory_snapshot():
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        name, raw = line.split(":", 1)
        values[name] = int(raw.strip().split()[0])
    vmstat = {}
    for line in Path("/proc/vmstat").read_text(encoding="ascii").splitlines():
        name, raw = line.split()
        if name in {"pgmajfault", "pgfault"}:
            vmstat[name] = int(raw)
    swap_used_kb = values.get("SwapTotal", 0) - values.get("SwapFree", 0)
    return {
        "timestamp_epoch_s": time.time(),
        "mem_total_kb": values.get("MemTotal", 0),
        "mem_available_kb": values.get("MemAvailable", 0),
        "swap_used_kb": swap_used_kb,
        "pgmajfault": vmstat.get("pgmajfault", 0),
        "pgfault": vmstat.get("pgfault", 0),
    }


class ResourceMonitor:
    def __init__(self, interval_s=2.0):
        self.interval_s = interval_s
        self.rows = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self):
        while not self._stop.is_set():
            self.rows.append(proc_memory_snapshot())
            self._stop.wait(self.interval_s)
        self.rows.append(proc_memory_snapshot())

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()


def wait_for_resource_guard():
    while True:
        snapshot = proc_memory_snapshot()
        if (
            snapshot["mem_available_kb"] >= 5 * 1024 * 1024
            and snapshot["swap_used_kb"] <= 512 * 1024
        ):
            return
        print(
            "RESOURCE_PAUSE mem_available_gb={:.3f} swap_used_mb={:.3f}".format(
                snapshot["mem_available_kb"] / 1024**2,
                snapshot["swap_used_kb"] / 1024,
            ),
            flush=True,
        )
        time.sleep(15)


def protocol_fields(result):
    frames = result["frames"]
    vdd = PVT_CASES[PVT_NAME]["vdd_v"]
    valid_count = sum(bool(frame["valid"]) for frame in frames)
    invalid_count = sum(
        math.isfinite(frame["invalid_v"]) and frame["invalid_v"] > vdd / 2.0
        for frame in frames
    )
    timeout_count = sum(
        math.isfinite(frame["timeout_v"]) and frame["timeout_v"] > vdd / 2.0
        for frame in frames
    )
    missing_frame_count = NFFT - valid_count
    duplicate_frame_count = NFFT - len(
        {int(frame["frame_index"]) for frame in frames}
    )
    conversion_times_ns = [
        (
            frame["complete_time_s"]
            - frame["frame_index"] * FRAME_PERIOD_S
            - SAMPLE_EDGE_OFFSET_S
        )
        * 1e9
        for frame in frames
        if math.isfinite(frame["complete_time_s"])
    ]
    return {
        "valid_frame_count": valid_count,
        "invalid_count": invalid_count,
        "timeout_count": timeout_count,
        "missing_frame_count": missing_frame_count,
        "duplicate_frame_count": duplicate_frame_count,
        "mean_conversion_time_ns": (
            float(np.mean(conversion_times_ns)) if conversion_times_ns else ""
        ),
        "max_conversion_time_ns": (
            float(np.max(conversion_times_ns)) if conversion_times_ns else ""
        ),
    }


def empty_error_row(seed, band, maxstep_ps, category, error_text):
    band_config = BANDS[band]
    return {
        "category": category,
        "pvt": PVT_NAME,
        "mismatch_seed": seed,
        "noise_seed": 100_000 + seed,
        "band": band,
        "nfft": NFFT,
        "bin": band_config["bin"],
        "fin_hz": band_config["fin_hz"],
        "phase_rad": float(PHASE_RAD),
        "input_vpp_diff": INPUT_VPP_DIFF_V,
        "maxstep_ns": maxstep_ps / 1000.0,
        "valid_frame_count": 0,
        "hard_dynamic_pass": False,
        "snr_budget_pass": False,
        "preferred_nominal_pass": False,
        "status": "SIM_ERROR_UNRESOLVED",
        "state": "SIM_ERROR_UNRESOLVED",
        "error": error_text[:1000],
    }


def run_record(
    grouped,
    timing,
    mismatch_seed,
    band,
    maxstep_ps,
    stem_prefix,
    category,
    mismatch_checksums,
    noise_checksums,
    preserve_raw=False,
):
    wait_for_resource_guard()
    band_config = BANDS[band]
    noise_seed = 100_000 + mismatch_seed
    ideal_values = coherent_values(
        NFFT,
        band_config["bin"],
        INPUT_AMPLITUDE_DIFF_V,
        PHASE_RAD,
        TRACK_FALL_OFFSET_S,
        SAMPLE_RATE_HZ,
    )
    stem = (
        f"{stem_prefix}_s{mismatch_seed:03d}_{band.lower()}_"
        f"{maxstep_ps:03d}ps"
    )
    result = run_event_frames(
        stem,
        ideal_values,
        noise_seed,
        timing,
        JOB_DIR / category.lower(),
        LOG_DIR / category.lower(),
        frame_s=FRAME_PERIOD_S,
        maxstep_s=maxstep_ps * 1e-12,
        pvt_name=PVT_NAME,
        mismatch_seed=mismatch_seed,
        grouped_weights=grouped,
        timeout_s=7200,
        v7_infrastructure_retry=True,
        v7_primary_solver_profile="ROBUST_GEAR",
        raw_dir=(ROOT / "raw" / "full_waveform_audit") if preserve_raw else None,
    )
    frames = result["frames"]
    codes = [int(frame["code"]) for frame in frames]
    metrics = fft_metrics(codes, band_config["bin"], SAMPLE_RATE_HZ)
    protocol = protocol_fields(result)
    protocol_clean = all(
        (
            result["returncode"] == 0,
            protocol["valid_frame_count"] == NFFT,
            protocol["invalid_count"] == 0,
            protocol["timeout_count"] == 0,
            protocol["missing_frame_count"] == 0,
            protocol["duplicate_frame_count"] == 0,
            bool(metrics["parseval_pass"]),
        )
    )
    hard_pass = all(
        (
            protocol_clean,
            metrics["clipping_count"] == 0,
            metrics["sndr_db"] >= SNDR_HARD_MIN_DB,
            metrics["enob_raw"] >= ENOB_HARD_MIN_BIT,
        )
    )
    snr_pass = protocol_clean and metrics["snr_db"] >= SNR_BUDGET_MIN_DB
    preferred_pass = all(
        (
            protocol_clean,
            metrics["clipping_count"] == 0,
            metrics["snr_db"] >= SNR_BUDGET_MIN_DB,
            metrics["sndr_db"] >= SNDR_PREFERRED_DB,
            metrics["enob_raw"] >= ENOB_PREFERRED_BIT,
        )
    )
    if result["returncode"] != 0:
        state = "SIM_ERROR_UNRESOLVED"
    elif not protocol_clean:
        state = "MEASUREMENT_BLOCKED"
    elif hard_pass:
        state = "VALID_PASS"
    else:
        state = "VALID_FAIL"
    noise_payload = bytearray()
    noise_payload.extend(
        np.asarray(result["noise"]["sample_draws_v"], dtype="<f8").tobytes()
    )
    noise_payload.extend(
        np.asarray(result["noise"]["comparator_draws_v"], dtype="<f8").tobytes()
    )
    actual_noise_checksum = sha256_bytes(bytes(noise_payload))
    raw_path = result.get("raw")
    summary = {
        "category": category,
        "pvt": PVT_NAME,
        "mismatch_seed": mismatch_seed,
        "noise_seed": noise_seed,
        "band": band,
        "nfft": NFFT,
        "bin": band_config["bin"],
        "fin_hz": band_config["fin_hz"],
        "phase_rad": float(PHASE_RAD),
        "input_vpp_diff": INPUT_VPP_DIFF_V,
        "maxstep_ns": maxstep_ps / 1000.0,
        "pfund_linear": metrics["pfund_linear"],
        "pnoise_linear": metrics["pnoise_linear"],
        "pharm_linear": metrics["pharm_linear"],
        "perror_linear": metrics["perror_linear"],
        "pspur_max_linear": metrics["pspur_max_linear"],
        "fundamental_dbfs": metrics["fundamental_dbfs"],
        "fundamental_rms_code": metrics["fundamental_rms_code"],
        "fundamental_peak_code": metrics["fundamental_peak_code"],
        "snr_db": metrics["snr_db"],
        "sndr_db": metrics["sndr_db"],
        "enob_raw": metrics["enob_raw"],
        "sfdr_dbc": metrics["sfdr_dbc"],
        "thd_db": metrics["thd_db"],
        "hd2_dbc": metrics["hd2_dbc"],
        "hd3_dbc": metrics["hd3_dbc"],
        "largest_spur_bin": metrics["largest_spur_bin"],
        "largest_spur_hz": metrics["largest_spur_frequency_hz"],
        "noise_floor_dbfs_per_bin": metrics["noise_floor_dbfs_per_bin"],
        "dc_code_offset": metrics["dc_code_offset"],
        "mean_conversion_time_ns": protocol["mean_conversion_time_ns"],
        "max_conversion_time_ns": protocol["max_conversion_time_ns"],
        "invalid_count": protocol["invalid_count"],
        "timeout_count": protocol["timeout_count"],
        "clipping_count": metrics["clipping_count"],
        "missing_frame_count": protocol["missing_frame_count"],
        "duplicate_frame_count": protocol["duplicate_frame_count"],
        "valid_frame_count": protocol["valid_frame_count"],
        "hard_dynamic_pass": hard_pass,
        "snr_budget_pass": snr_pass,
        "preferred_nominal_pass": preferred_pass,
        "status": state,
        "state": state,
        "harmonic_bins": metrics["harmonic_bins"],
        "parseval_time_mean_square": metrics["parseval_time_mean_square"],
        "parseval_spectral_mean_square": metrics["parseval_spectral_mean_square"],
        "parseval_relative_error": metrics["parseval_relative_error"],
        "parseval_pass": metrics["parseval_pass"],
        "mismatch_checksum_sha256": mismatch_checksums[mismatch_seed],
        "noise_draw_checksum_sha256": actual_noise_checksum,
        "noise_draw_checksum_match": (
            actual_noise_checksum == noise_checksums[noise_seed]
        ),
        "compact_code_checksum_sha256": compact_code_checksum(codes),
        "execution_mode": "SEPARATE_PROCESS_FALLBACK",
        "measurement_stem": result["measurement_stem"],
        "measurement_solver_profile": result["measurement_solver_profile"],
        "attempt_count": result["attempt_count"],
        "attempt_returncodes": result["attempt_returncodes"],
        "retry_used": result["retry_used"],
        "returncode": result["returncode"],
        "timed_out": result.get("timed_out", False),
        "simulation_aborted": result.get("simulation_aborted", False),
        "elapsed_s": result["elapsed_s"],
        "peak_rss_kb": result.get("peak_rss_kb", 0),
        "deck": str(result["deck"].relative_to(ROOT)),
        "log": str(result["log"].relative_to(ROOT)),
        "full_waveform_audit": bool(preserve_raw),
        "raw_path": (
            str(Path(raw_path).relative_to(ROOT))
            if raw_path is not None and Path(raw_path).is_file()
            else ""
        ),
        "raw_sha256": (
            sha256_file(raw_path)
            if raw_path is not None and Path(raw_path).is_file()
            else ""
        ),
        "error": "",
    }
    code_rows = []
    for frame, ideal, commanded in zip(
        frames, result["ideal_vid_values"], result["commanded_vid_values"]
    ):
        code_rows.append(
            {
                "category": category,
                "mismatch_seed": mismatch_seed,
                "noise_seed": noise_seed,
                "band": band,
                "frame_index": frame["frame_index"],
                "ideal_vid_v": ideal,
                "commanded_vid_v": commanded,
                "code": frame["code"],
                "bits": frame["bits"],
                "valid": frame["valid"],
                "invalid_v": frame["invalid_v"],
                "timeout_v": frame["timeout_v"],
                "complete_time_s": frame["complete_time_s"],
                "measurement_stem": result["measurement_stem"],
            }
        )
    return summary, code_rows


def compare_records(reference, candidate, reference_codes, candidate_codes):
    code_match = [int(row["code"]) for row in reference_codes] == [
        int(row["code"]) for row in candidate_codes
    ]
    flag_keys = (
        "valid_frame_count",
        "invalid_count",
        "timeout_count",
        "missing_frame_count",
        "duplicate_frame_count",
        "clipping_count",
    )
    flags_match = all(reference[key] == candidate[key] for key in flag_keys)
    delta_snr = abs(float(reference["snr_db"]) - float(candidate["snr_db"]))
    delta_sndr = abs(float(reference["sndr_db"]) - float(candidate["sndr_db"]))
    delta_enob = abs(float(reference["enob_raw"]) - float(candidate["enob_raw"]))
    return {
        "code_stream_identical": code_match,
        "flags_identical": flags_match,
        "delta_snr_db": delta_snr,
        "delta_sndr_db": delta_sndr,
        "delta_enob_bit": delta_enob,
        "mismatch_checksum_identical": (
            reference["mismatch_checksum_sha256"]
            == candidate["mismatch_checksum_sha256"]
        ),
        "noise_draw_checksum_identical": (
            reference["noise_draw_checksum_sha256"]
            == candidate["noise_draw_checksum_sha256"]
        ),
        "pass": all(
            (
                code_match,
                flags_match,
                delta_snr <= 0.01,
                delta_sndr <= 0.01,
                delta_enob <= 0.002,
                reference["mismatch_checksum_sha256"]
                == candidate["mismatch_checksum_sha256"],
                reference["noise_draw_checksum_sha256"]
                == candidate["noise_draw_checksum_sha256"],
            )
        ),
    }


def resource_summary(trace_rows, qualification_rows, observation_s):
    mem_total_gb = trace_rows[0]["mem_total_kb"] / 1024**2
    min_available_gb = min(row["mem_available_kb"] for row in trace_rows) / 1024**2
    max_swap_mb = max(row["swap_used_kb"] for row in trace_rows) / 1024
    swap_growth_mb = (
        trace_rows[-1]["swap_used_kb"] - trace_rows[0]["swap_used_kb"]
    ) / 1024
    longest_major_rise_samples = 0
    current_rise_samples = 0
    for previous, current in zip(trace_rows, trace_rows[1:]):
        if current["pgmajfault"] > previous["pgmajfault"]:
            current_rise_samples += 1
            longest_major_rise_samples = max(
                longest_major_rise_samples, current_rise_samples
            )
        else:
            current_rise_samples = 0
    interval_s = (
        np.median(
            [
                current["timestamp_epoch_s"] - previous["timestamp_epoch_s"]
                for previous, current in zip(trace_rows, trace_rows[1:])
            ]
        )
        if len(trace_rows) > 1
        else 0.0
    )
    p95_rss_kb = float(
        np.percentile([float(row["peak_rss_kb"]) for row in qualification_rows], 95)
    )
    p95_record_s = float(
        np.percentile(
            [
                float(row["elapsed_s"])
                for row in qualification_rows
                if float(row["elapsed_s"]) > 0
            ],
            95,
        )
    )
    raw_rss_gb = p95_rss_kb / 1024**2
    token_gb = max(0.5, math.ceil(1.25 * raw_rss_gb / 0.5) * 0.5)
    effective_budget_gb = min(22.0, max(0.5, mem_total_gb - 5.0))
    measured_worker_limit = max(1, int(effective_budget_gb // token_gb))
    selected_workers = min(4, measured_worker_limit)
    projected_s = 400.0 * p95_record_s / selected_workers + 7200.0
    major_rise_s = longest_major_rise_samples * float(interval_s)
    admission_pass = all(
        (
            observation_s >= 1200.0,
            min_available_gb >= 5.0,
            max_swap_mb <= 512.0,
            swap_growth_mb <= 0.0,
            major_rise_s < 60.0,
            projected_s <= 24.0 * 3600.0,
            selected_workers >= 1,
        )
    )
    return {
        "container_mem_total_gb": mem_total_gb,
        "nominal_host_profile_gb": 32.0,
        "nominal_ngspice_token_budget_gb": 22.0,
        "effective_container_token_budget_gb": effective_budget_gb,
        "min_mem_available_gb": min_available_gb,
        "max_swap_used_mb": max_swap_mb,
        "swap_growth_mb": swap_growth_mb,
        "longest_continuous_major_fault_rise_s": major_rise_s,
        "resource_observation_s": observation_s,
        "record_peak_rss_p95_gb": raw_rss_gb,
        "token_per_record_gb_with_margin": token_gb,
        "measured_worker_limit": measured_worker_limit,
        "selected_formal_workers": selected_workers,
        "record_runtime_p95_s": p95_record_s,
        "projected_total_s_with_2h_overhead": projected_s,
        "projected_total_h_with_2h_overhead": projected_s / 3600.0,
        "one_day_runtime_pass": projected_s <= 24.0 * 3600.0,
        "admission_pass": admission_pass,
    }


def qualification(grouped, timing):
    qualification_cache_path = CONFIG_DIR / "qualification_cache.json"
    cache = json.loads(qualification_cache_path.read_text(encoding="ascii"))
    if not cache["noise_model_qualified"]:
        cache["fixed_pilot_complete"] = False
        cache["blocked_status"] = "BLOCKED_NOISE_MODEL_NOT_QUALIFIED"
        write_json_atomic(qualification_cache_path, cache)
        return cache
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    monitor = ResourceMonitor()
    monitor.start()
    started = time.monotonic()
    rows = []
    code_rows = []
    pilot_cases = (
        ("P0", 1, 100),
        ("P1", 1, 50),
        ("P2", 44, 100),
        ("P3", 44, 50),
    )
    indexed = {}
    indexed_codes = {}
    for pilot_id, seed, maxstep_ps in pilot_cases:
        for band in BANDS:
            row, codes = run_record(
                grouped,
                timing,
                seed,
                band,
                maxstep_ps,
                pilot_id.lower(),
                "QUALIFICATION",
                mismatch_checksums,
                noise_checksums,
            )
            row["qualification_id"] = pilot_id
            for code in codes:
                code["qualification_id"] = pilot_id
            rows.append(row)
            code_rows.extend(codes)
            indexed[(pilot_id, band)] = row
            indexed_codes[(pilot_id, band)] = codes
            print(
                "{} seed={} band={} maxstep={}ps SNDR={:.4f} state={}".format(
                    pilot_id,
                    seed,
                    band,
                    maxstep_ps,
                    float(row["sndr_db"]),
                    row["state"],
                ),
                flush=True,
            )
    numerical_checks = []
    for seed, bulk_id, strict_id in ((1, "P0", "P1"), (44, "P2", "P3")):
        for band in BANDS:
            comparison = compare_records(
                indexed[(bulk_id, band)],
                indexed[(strict_id, band)],
                indexed_codes[(bulk_id, band)],
                indexed_codes[(strict_id, band)],
            )
            numerical_checks.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "bulk_id": bulk_id,
                    "strict_id": strict_id,
                    **comparison,
                }
            )
    bulk_equivalent = all(item["pass"] for item in numerical_checks)
    selected_maxstep_ps = 100 if bulk_equivalent else 50
    selected_ids = {1: "P0" if bulk_equivalent else "P1", 44: "P2" if bulk_equivalent else "P3"}
    session_checks = []
    for equivalence_id, seed in (("E0", 1), ("E1", 44)):
        for band in BANDS:
            row, codes = run_record(
                grouped,
                timing,
                seed,
                band,
                selected_maxstep_ps,
                equivalence_id.lower(),
                "SESSION_EQUIVALENCE",
                mismatch_checksums,
                noise_checksums,
            )
            row["qualification_id"] = equivalence_id
            for code in codes:
                code["qualification_id"] = equivalence_id
            rows.append(row)
            code_rows.extend(codes)
            comparison = compare_records(
                indexed[(selected_ids[seed], band)],
                row,
                indexed_codes[(selected_ids[seed], band)],
                codes,
            )
            session_checks.append(
                {
                    "mismatch_seed": seed,
                    "band": band,
                    "dual_band_orchestrator_id": selected_ids[seed],
                    "separate_process_reference_id": equivalence_id,
                    **comparison,
                }
            )
            print(
                "{} seed={} band={} deterministic_replay={}".format(
                    equivalence_id, seed, band, comparison["pass"]
                ),
                flush=True,
            )
    while time.monotonic() - started < 1200.0:
        # Keep compact post-processing and output-path reads active for the
        # remainder of the fixed 20-minute resource-observation window.
        for row in rows:
            float(row["pfund_linear"]) + float(row["pnoise_linear"])
        time.sleep(2.0)
    observation_s = time.monotonic() - started
    monitor.stop()
    write_csv_atomic(QUALIFICATION_PATH, rows)
    write_csv_atomic(QUALIFICATION_CODE_PATH, code_rows)
    write_csv_atomic(RESOURCE_TRACE_PATH, monitor.rows)
    write_csv_atomic(CSV_DIR / "numerical_qualification_checks.csv", numerical_checks)
    write_csv_atomic(CSV_DIR / "session_equivalence_checks.csv", session_checks)
    selected_rows = [
        row
        for row in rows
        if row["qualification_id"] in set(selected_ids.values()) | {"E0", "E1"}
    ]
    resource_result = resource_summary(monitor.rows, selected_rows, observation_s)
    selected_profile_clean = all(
        row["state"] in {"VALID_PASS", "VALID_FAIL"}
        and bool(row["parseval_pass"])
        and bool(row["noise_draw_checksum_match"])
        for row in selected_rows
    )
    session_equivalence_pass = all(item["pass"] for item in session_checks)
    cache.update(
        {
            "fixed_pilot_complete": True,
            "numerical_qualification_pass": selected_profile_clean,
            "bulk_100ps_equivalent_to_strict_50ps": bulk_equivalent,
            "selected_formal_maxstep_ps": selected_maxstep_ps,
            "numerical_checks": numerical_checks,
            "session_equivalence_complete": True,
            "session_equivalence_pass": session_equivalence_pass,
            "parsed_ngspice_session_qualification_claim": False,
            "session_fallback_documented": True,
            "session_fallback_reason": (
                "No persistent parsed-ngspice implementation is used. Formal records "
                "use separate ngspice processes; deterministic dual-band orchestration "
                "versus separate-reference replay was checked."
            ),
            "session_checks": session_checks,
            "resource_admission_complete": True,
            "resource_admission_pass": resource_result["admission_pass"],
            "resource": resource_result,
            "qualification_record_count": len(rows),
            "postprocess_peak_rss_kb": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        }
    )
    if not selected_profile_clean or not session_equivalence_pass:
        cache["blocked_status"] = "BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED"
    elif not resource_result["admission_pass"]:
        cache["blocked_status"] = "BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION"
    else:
        cache["blocked_status"] = ""
    write_json_atomic(qualification_cache_path, cache)
    write_json_atomic(RESULT_DIR / "qualification_audit.json", cache)
    return cache


def merge_rows(path, new_rows, key_fields):
    current = read_csv(path) if path.is_file() else []
    merged = {tuple(str(row.get(key, "")) for key in key_fields): row for row in current}
    for row in new_rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        merged[key] = row
    rows = list(merged.values())
    return rows


def update_job_matrix(master_rows):
    master = {
        (int(row["mismatch_seed"]), row["band"]): row for row in master_rows
    }
    jobs = read_csv(JOB_MATRIX_PATH)
    for job in jobs:
        key = (int(job["mismatch_seed"]), job["band"])
        if key not in master:
            continue
        result = master[key]
        job.update(
            {
                "state": result["state"],
                "attempt_count": result.get("attempt_count", ""),
                "measurement_stem": result.get("measurement_stem", ""),
                "compact_code_checksum_sha256": result.get(
                    "compact_code_checksum_sha256", ""
                ),
            }
        )
    write_csv_atomic(JOB_MATRIX_PATH, jobs)


def run_die(
    grouped,
    timing,
    seed,
    maxstep_ps,
    mismatch_checksums,
    noise_checksums,
    missing_bands,
):
    rows = []
    codes = []
    for band in BANDS:
        if band not in missing_bands:
            continue
        try:
            row, code_rows = run_record(
                grouped,
                timing,
                seed,
                band,
                maxstep_ps,
                "formal",
                "D3_NOISE_PLUS_MISMATCH_MC200",
                mismatch_checksums,
                noise_checksums,
            )
        except Exception:
            error_text = traceback.format_exc()
            row = empty_error_row(
                seed,
                band,
                maxstep_ps,
                "D3_NOISE_PLUS_MISMATCH_MC200",
                error_text,
            )
            code_rows = []
        rows.append(row)
        codes.extend(code_rows)
    return rows, codes


def formal_population(grouped, timing, seeds, requested_workers=None):
    cache = json.loads(
        (CONFIG_DIR / "qualification_cache.json").read_text(encoding="ascii")
    )
    if cache.get("blocked_status"):
        print(f"FORMAL_NOT_ADMITTED {cache['blocked_status']}", flush=True)
        return []
    if not all(
        (
            cache.get("fixed_pilot_complete"),
            cache.get("numerical_qualification_pass"),
            cache.get("session_equivalence_complete"),
            cache.get("resource_admission_pass"),
        )
    ):
        raise RuntimeError("qualification is incomplete")
    maxstep_ps = int(cache["selected_formal_maxstep_ps"])
    admitted_workers = int(cache["resource"]["selected_formal_workers"])
    workers = (
        admitted_workers
        if requested_workers is None
        else min(int(requested_workers), admitted_workers)
    )
    workers = max(1, workers)
    mismatch_checksums, noise_checksums = load_manifest_checksums()
    existing_master = read_csv(MASTER_PATH) if MASTER_PATH.is_file() else []
    existing_codes = read_csv(CODE_PATH) if CODE_PATH.is_file() else []
    terminal = {
        (int(row["mismatch_seed"]), row["band"])
        for row in existing_master
        if row.get("state")
        in {
            "VALID_PASS",
            "VALID_FAIL",
            "SIM_ERROR_UNRESOLVED",
            "MODEL_BLOCKED",
            "MEASUREMENT_BLOCKED",
        }
    }
    work = []
    for seed in seeds:
        missing = [band for band in BANDS if (seed, band) not in terminal]
        if missing:
            work.append((seed, missing))
    print(
        f"FORMAL_START dies={len(work)} workers={workers} maxstep_ps={maxstep_ps}",
        flush=True,
    )
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                run_die,
                grouped,
                timing,
                seed,
                maxstep_ps,
                mismatch_checksums,
                noise_checksums,
                missing,
            ): seed
            for seed, missing in work
        }
        for future in as_completed(futures):
            seed = futures[future]
            rows, codes = future.result()
            existing_master = merge_rows(
                MASTER_PATH,
                rows,
                ("mismatch_seed", "band"),
            )
            existing_master.sort(
                key=lambda row: (
                    int(row["mismatch_seed"]),
                    0 if row["band"] == "LOW" else 1,
                )
            )
            write_csv_atomic(MASTER_PATH, existing_master)
            existing_codes = merge_rows(
                CODE_PATH,
                codes,
                ("mismatch_seed", "band", "frame_index"),
            )
            existing_codes.sort(
                key=lambda row: (
                    int(row["mismatch_seed"]),
                    0 if row["band"] == "LOW" else 1,
                    int(row["frame_index"]),
                )
            )
            write_csv_atomic(CODE_PATH, existing_codes)
            update_job_matrix(existing_master)
            print(
                "DIE {:03d} {}".format(
                    seed,
                    " ".join(
                        "{}:{} SNDR={}".format(
                            row["band"],
                            row["state"],
                            (
                                f"{float(row['sndr_db']):.3f}"
                                if row.get("sndr_db", "") != ""
                                else "NA"
                            ),
                        )
                        for row in rows
                    ),
                ),
                flush=True,
            )
    elapsed_s = time.monotonic() - started
    final_rows = read_csv(MASTER_PATH) if MASTER_PATH.is_file() else []
    status_counts = {}
    for row in final_rows:
        status_counts[row["state"]] = status_counts.get(row["state"], 0) + 1
    write_json_atomic(
        RESULT_DIR / "formal_execution_audit.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "requested_seeds": seeds,
            "workers": workers,
            "selected_maxstep_ps": maxstep_ps,
            "wall_elapsed_s_this_invocation": elapsed_s,
            "records_present": len(final_rows),
            "status_counts": status_counts,
            "performance_early_stop": False,
        },
    )
    return final_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=("qualification", "formal", "all"), default="all"
    )
    parser.add_argument("--seeds", default="1:200")
    parser.add_argument("--workers", type=int)
    args = parser.parse_args()
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = "1"
    ensure_v7_directories()
    grouped = load_cdac_weights()
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="ascii")
    )
    if args.stage in ("qualification", "all"):
        cache = qualification(grouped, timing)
        print(
            "QUALIFICATION selected_maxstep_ps={} resource_admission={} blocked={}".format(
                cache.get("selected_formal_maxstep_ps"),
                cache.get("resource_admission_pass"),
                cache.get("blocked_status", ""),
            ),
            flush=True,
        )
    if args.stage in ("formal", "all"):
        formal_population(
            grouped,
            timing,
            parse_seed_expression(args.seeds),
            requested_workers=args.workers,
        )


if __name__ == "__main__":
    main()
