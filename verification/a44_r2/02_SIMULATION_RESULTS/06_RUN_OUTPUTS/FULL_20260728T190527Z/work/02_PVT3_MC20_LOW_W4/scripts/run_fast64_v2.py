#!/usr/bin/env python3
"""Execute resumable FAST64 V2 jobs, including the LOW-only MC200 W4 population."""

from __future__ import annotations

import argparse
import json
import math
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

from dynamic_analysis import fft_metrics
from fast64_v2_common import (
    BANDS,
    CONFIG_DIR,
    CSV_DIR,
    DOUT_APERTURE_NS,
    ENOB_HARD_MIN_BIT,
    ENOB_PREFERRED_BIT,
    FRAME_PERIOD_S,
    HISTORICAL_METHOD_ID,
    INPUT_AMPLITUDE_DIFF_V,
    INPUT_VPP_DIFF_V,
    JOB_DIR,
    LOG_DIR,
    MANIFEST_DIR,
    METHOD_ID,
    NFFT,
    PHASE_RAD,
    RESULT_DIR,
    ROOT,
    SAMPLE_RATE_HZ,
    SNDR_HARD_MIN_DB,
    SNDR_PREFERRED_DB,
    SNR_BUDGET_MIN_DB,
    STEADY_METHOD_ID,
    canonical_json_hash,
    code_checksum,
    coherent_input_values,
    ensure_directories,
    noise_checksum,
    read_csv,
    retained_indices,
    sha256_file,
    smoke_jobs,
    startup_pair_indices,
    write_csv_atomic,
    write_json_atomic,
)
from sar_campaign_common import (
    PVT_CASES,
    SAMPLE_EDGE_OFFSET_S,
    TRACK_FALL_OFFSET_S,
    build_deck,
    decode_frames,
    load_cdac_weights,
    run_deck,
)
from sar_event_noise import (
    COMPARATOR_SIGMA_V,
    SAMPLE_SIGMA_V,
    add_comparator_event_noise,
    apply_solver_profile,
    decision_apertures_s,
    frozen_event_draws,
)


JOB_MATRIX = MANIFEST_DIR / "job_matrix.csv"
SMOKE_MATRIX = MANIFEST_DIR / "smoke_job_matrix.csv"
JOB_RESULT_DIR = RESULT_DIR / "jobs"
JOB_CODE_DIR = CSV_DIR / "job_codes"
JOB_PATH_DIR = CSV_DIR / "job_paths"
RESOURCE_TRACE = CSV_DIR / "resource_trace.csv"

TERMINAL_STATES = {
    "COMPLETE",
    "COMPLETE_WITH_FAIL",
    "SIM_ERROR_UNRESOLVED",
    "MEASUREMENT_BLOCKED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_int(value: object, default: int | None = None) -> int | None:
    text = str(value).strip()
    if text == "":
        return default
    return int(text)


def mismatch_checksum_table() -> dict[int, str]:
    rows = read_csv(CSV_DIR / "cdac_mismatch_weights.csv")
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        if row["branch"] != "CLAIM_BASELINE_3SIGMA_CONVERSION":
            continue
        seed = int(row["mismatch_seed"])
        grouped.setdefault(seed, []).append(
            {
                "side": row["side"],
                "element": row["element"],
                "nominal_units": row["nominal_units"],
                "realized_units": row["realized_units"],
                "relative_error": row["relative_error"],
            }
        )
    output: dict[int, str] = {}
    for seed, values in grouped.items():
        values.sort(key=lambda item: (item["side"], item["element"]))
        output[seed] = canonical_json_hash(values)
    return output


class ResourceMonitor:
    def __init__(self, interval_s: float = 1.0):
        self.interval_s = interval_s
        self.rows: list[dict[str, object]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    @staticmethod
    def _process_snapshot() -> dict[str, object]:
        process_count = 0
        thread_count = 0
        rss_kb = 0
        process_rows: list[str] = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                    "utf-8", errors="replace"
                )
                if "ngspice" not in cmdline:
                    continue
                status = (entry / "status").read_text(
                    encoding="utf-8", errors="replace"
                )
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
            fields: dict[str, str] = {}
            for line in status.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    fields[key] = value.strip()
            process_count += 1
            thread_count += int(fields.get("Threads", "0"))
            rss_kb += int(fields.get("VmRSS", "0 kB").split()[0])
            process_rows.append(f"{entry.name}:{fields.get('Threads','')}:{cmdline[:120]}")
        meminfo: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
                    meminfo[key] = int(value.strip().split()[0])
        return {
            "utc": utc_now(),
            "monotonic_s": time.monotonic(),
            "ngspice_process_count": process_count,
            "ngspice_thread_count": thread_count,
            "ngspice_rss_kb": rss_kb,
            "mem_available_kb": meminfo.get("MemAvailable", 0),
            "swap_used_kb": meminfo.get("SwapTotal", 0)
            - meminfo.get("SwapFree", 0),
            "process_detail": "|".join(sorted(process_rows)),
        }

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.rows.append(self._process_snapshot())
            self._stop.wait(self.interval_s)
        self.rows.append(self._process_snapshot())

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()


def wait_for_resources() -> None:
    while True:
        snapshot = ResourceMonitor._process_snapshot()
        if (
            int(snapshot["mem_available_kb"]) >= 4 * 1024 * 1024
            and int(snapshot["swap_used_kb"]) <= 512 * 1024
        ):
            return
        print(
            "RESOURCE_PAUSE mem_available_gb={:.3f} swap_used_mb={:.3f}".format(
                int(snapshot["mem_available_kb"]) / 1024**2,
                int(snapshot["swap_used_kb"]) / 1024,
            ),
            flush=True,
        )
        time.sleep(15)


def startup_frame_indices(total_frames: int) -> tuple[int, ...]:
    values = {
        frame
        for pair in startup_pair_indices(total_frames)
        for frame in pair
    }
    return tuple(sorted(values))


def _decision_update_times(frame: int, timing: Mapping[str, object]) -> dict[int, float]:
    high = {
        bit: float(timing["cmpck_high"][7 - bit])  # type: ignore[index]
        for bit in range(8)
    }
    low = {
        bit: float(timing["cmpck_low_guard_bits_7_to_1"][7 - bit])  # type: ignore[index]
        for bit in range(1, 8)
    }
    rise_s = (
        frame * FRAME_PERIOD_S
        + TRACK_FALL_OFFSET_S
        + float(timing["t_clks_fall_to_first_cmpck_rise"]) * 1e-9
    )
    output: dict[int, float] = {}
    for bit in range(7, 0, -1):
        # Observe the DCTRL after its RC transition has settled, one nanosecond
        # before the next comparator rise. This is the functional deadline for
        # the updated CDAC control, not an arbitrary early post-event point.
        output[bit] = rise_s + (high[bit] + low[bit] - 1.0) * 1e-9
        rise_s += (high[bit] + low[bit]) * 1e-9
    return output


def add_startup_path_instrumentation(
    deck: str, total_frames: int, timing: Mapping[str, object]
) -> str:
    save_anchor = ".control\n"
    if deck.count(save_anchor) != 1:
        raise RuntimeError("deck .control anchor count is not one")
    save_lines = [
        ".save v(dcmpp) v(dcmpn)",
        "+ v(dout7_drv) v(dout6_drv) v(dout5_drv) v(dout4_drv) v(dout3_drv) v(dout2_drv) v(dout1_drv) v(dout0_drv)",
        "+ v(dctrlp7) v(dctrlp6) v(dctrlp5) v(dctrlp4) v(dctrlp3) v(dctrlp2) v(dctrlp1)",
        "+ v(dctrln7) v(dctrln6) v(dctrln5) v(dctrln4) v(dctrln3) v(dctrln2) v(dctrln1)",
    ]
    deck = deck.replace(save_anchor, "\n".join(save_lines) + "\n" + save_anchor, 1)

    apertures = decision_apertures_s(total_frames, FRAME_PERIOD_S, timing)
    measures: list[str] = []
    for frame in startup_frame_indices(total_frames):
        for offset, bit in enumerate(range(7, -1, -1)):
            at_s = apertures[frame][offset]
            measures.append(
                f"meas tran p_f{frame:03d}_cmp{bit}_p0 find v(dcmpp) at={at_s:.12g}"
            )
            measures.append(
                f"meas tran p_f{frame:03d}_cmp{bit}_n0 find v(dcmpn) at={at_s:.12g}"
            )
            measures.append(
                f"meas tran p_f{frame:03d}_cmp{bit}_p5 find v(dcmpp) at={at_s + 5e-9:.12g}"
            )
            measures.append(
                f"meas tran p_f{frame:03d}_cmp{bit}_n5 find v(dcmpn) at={at_s + 5e-9:.12g}"
            )
        for bit, at_s in _decision_update_times(frame, timing).items():
            measures.append(
                f"meas tran p_f{frame:03d}_dctrl{bit}_p find v(dctrlp{bit}) at={at_s:.12g}"
            )
            measures.append(
                f"meas tran p_f{frame:03d}_dctrl{bit}_n find v(dctrln{bit}) at={at_s:.12g}"
            )
        for offset_ns in (470.0, DOUT_APERTURE_NS):
            at_s = frame * FRAME_PERIOD_S + offset_ns * 1e-9
            suffix = int(offset_ns)
            for bit in range(7, -1, -1):
                measures.append(
                    f"meas tran p_f{frame:03d}_do{bit}_drv_{suffix} "
                    f"find v(dout{bit}_drv) at={at_s:.12g}"
                )
                measures.append(
                    f"meas tran p_f{frame:03d}_do{bit}_rx_{suffix} "
                    f"find v(dout{bit}_rx) at={at_s:.12g}"
                )
    quit_anchor = "\nquit\n.endc"
    if deck.count(quit_anchor) != 1:
        raise RuntimeError("deck quit anchor count is not one")
    return deck.replace(quit_anchor, "\n" + "\n".join(measures) + quit_anchor, 1)


def decode_bits(values: Iterable[float], threshold: float) -> tuple[str, int]:
    bits = [int(math.isfinite(value) and value > threshold) for value in values]
    return "".join(str(bit) for bit in bits), sum(
        bit << (7 - offset) for offset, bit in enumerate(bits)
    )


def decode_path_rows(
    job: Mapping[str, object],
    measures: Mapping[str, float],
    total_frames: int,
    vdd: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    threshold = vdd / 2.0
    for frame in startup_frame_indices(total_frames):
        cmp_p0 = [
            measures.get(f"p_f{frame:03d}_cmp{bit}_p0", math.nan)
            for bit in range(7, -1, -1)
        ]
        cmp_n0 = [
            measures.get(f"p_f{frame:03d}_cmp{bit}_n0", math.nan)
            for bit in range(7, -1, -1)
        ]
        cmp_p5 = [
            measures.get(f"p_f{frame:03d}_cmp{bit}_p5", math.nan)
            for bit in range(7, -1, -1)
        ]
        cmp_n5 = [
            measures.get(f"p_f{frame:03d}_cmp{bit}_n5", math.nan)
            for bit in range(7, -1, -1)
        ]
        comparator_direct_bits: list[int] = []
        comparator_decision_sources: list[str] = []
        for p0, n0, p5, n5 in zip(cmp_p0, cmp_n0, cmp_p5, cmp_n5):
            if math.isfinite(p0) and math.isfinite(n0) and p0 > threshold and n0 < threshold:
                comparator_direct_bits.append(1)
                comparator_decision_sources.append("INITIAL")
            elif math.isfinite(p0) and math.isfinite(n0) and p0 < threshold and n0 > threshold:
                comparator_direct_bits.append(0)
                comparator_decision_sources.append("INITIAL")
            elif math.isfinite(p5) and math.isfinite(n5) and p5 > threshold and n5 < threshold:
                comparator_direct_bits.append(1)
                comparator_decision_sources.append("RETRY_5NS")
            elif math.isfinite(p5) and math.isfinite(n5) and p5 < threshold and n5 > threshold:
                comparator_direct_bits.append(0)
                comparator_decision_sources.append("RETRY_5NS")
            else:
                comparator_direct_bits.append(0)
                comparator_decision_sources.append("INVALID")
        comparator_inverse_bits = [1 - bit for bit in comparator_direct_bits]
        comparator_direct = sum(
            bit << (7 - offset)
            for offset, bit in enumerate(comparator_direct_bits)
        )
        comparator_inverse = sum(
            bit << (7 - offset)
            for offset, bit in enumerate(comparator_inverse_bits)
        )
        dctrl_direct_bits = []
        dctrl_valid_updates = 0
        for bit in range(7, 0, -1):
            p = measures.get(f"p_f{frame:03d}_dctrl{bit}_p", math.nan)
            n = measures.get(f"p_f{frame:03d}_dctrl{bit}_n", math.nan)
            if (
                math.isfinite(p)
                and math.isfinite(n)
                and ((p > threshold and n < threshold) or (p < threshold and n > threshold))
            ):
                dctrl_valid_updates += 1
            dctrl_direct_bits.append(
                int(math.isfinite(p) and math.isfinite(n) and p > n)
            )
        driver_bits_470, driver_code_470 = decode_bits(
            (
                measures.get(f"p_f{frame:03d}_do{bit}_drv_470", math.nan)
                for bit in range(7, -1, -1)
            ),
            threshold,
        )
        analog_bits_470, analog_code_470 = decode_bits(
            (
                measures.get(f"p_f{frame:03d}_do{bit}_rx_470", math.nan)
                for bit in range(7, -1, -1)
            ),
            threshold,
        )
        driver_bits_480, driver_code_480 = decode_bits(
            (
                measures.get(f"p_f{frame:03d}_do{bit}_drv_480", math.nan)
                for bit in range(7, -1, -1)
            ),
            threshold,
        )
        analog_bits_480, analog_code_480 = decode_bits(
            (
                measures.get(f"p_f{frame:03d}_do{bit}_rx_480", math.nan)
                for bit in range(7, -1, -1)
            ),
            threshold,
        )
        dctrl_direct_7 = sum(
            bit_value << (7 - offset)
            for offset, bit_value in enumerate(dctrl_direct_bits)
        )
        dctrl_inverse_7 = sum(
            (1 - bit_value) << (7 - offset)
            for offset, bit_value in enumerate(dctrl_direct_bits)
        )
        rows.append(
            {
                "job_id": job["job_id"],
                "frame_index": frame,
                "comparator_p_initial_values": ";".join(
                    f"{value:.12g}" for value in cmp_p0
                ),
                "comparator_n_initial_values": ";".join(
                    f"{value:.12g}" for value in cmp_n0
                ),
                "comparator_p_retry_5ns_values": ";".join(
                    f"{value:.12g}" for value in cmp_p5
                ),
                "comparator_n_retry_5ns_values": ";".join(
                    f"{value:.12g}" for value in cmp_n5
                ),
                "comparator_decision_sources": ";".join(
                    comparator_decision_sources
                ),
                "comparator_valid_decision_count": sum(
                    source != "INVALID" for source in comparator_decision_sources
                ),
                "comparator_retry_decision_count": sum(
                    source == "RETRY_5NS" for source in comparator_decision_sources
                ),
                "comparator_direct_bits": "".join(
                    str(bit) for bit in comparator_direct_bits
                ),
                "comparator_direct_code": comparator_direct,
                "comparator_inverse_code": comparator_inverse,
                "dctrl_direct_bits_7_to_1": "".join(
                    str(bit) for bit in dctrl_direct_bits
                ),
                "dctrl_valid_update_count": dctrl_valid_updates,
                "dctrl_direct_code_7_to_1": dctrl_direct_7,
                "dctrl_inverse_code_7_to_1": dctrl_inverse_7,
                "digital_dout_code": driver_code_480,
                "digital_observation": "INFERRED_AT_DAC_BRIDGE_OUTPUT",
                "driver_dout_bits_470": driver_bits_470,
                "driver_dout_code_470": driver_code_470,
                "analog_dout_bits_470": analog_bits_470,
                "analog_dout_code_470": analog_code_470,
                "driver_dout_bits_480": driver_bits_480,
                "driver_dout_code_480": driver_code_480,
                "analog_dout_bits_480": analog_bits_480,
                "analog_dout_code_480": analog_code_480,
                "driver_analog_match_480": driver_code_480 == analog_code_480,
                "dout_stable_470_to_480": (
                    driver_code_470 == driver_code_480
                    and analog_code_470 == analog_code_480
                ),
            }
        )
    return rows


def protocol_summary(frames: list[dict[str, object]], returncode: int) -> dict[str, object]:
    valid_count = sum(bool(frame["valid"]) for frame in frames)
    invalid_count = sum(
        math.isfinite(float(frame["invalid_v"])) and float(frame["invalid_v"]) > 1.65
        for frame in frames
    )
    timeout_count = sum(
        math.isfinite(float(frame["timeout_v"])) and float(frame["timeout_v"]) > 1.65
        for frame in frames
    )
    frame_indices = [int(frame["frame_index"]) for frame in frames]
    conversion_times_ns = [
        (
            float(frame["complete_time_s"])
            - int(frame["frame_index"]) * FRAME_PERIOD_S
            - SAMPLE_EDGE_OFFSET_S
        )
        * 1e9
        for frame in frames
        if math.isfinite(float(frame["complete_time_s"]))
    ]
    return {
        "valid_frame_count": valid_count,
        "invalid_count": invalid_count,
        "timeout_count": timeout_count,
        "missing_frame_count": len(frames) - valid_count,
        "duplicate_frame_count": len(frame_indices) - len(set(frame_indices)),
        "mean_conversion_time_ns": float(np.mean(conversion_times_ns))
        if conversion_times_ns
        else "",
        "max_conversion_time_ns": float(np.max(conversion_times_ns))
        if conversion_times_ns
        else "",
        "protocol_clean": (
            returncode == 0
            and valid_count == len(frames)
            and invalid_count == 0
            and timeout_count == 0
            and len(frame_indices) == len(set(frame_indices))
        ),
    }


def run_one_job(
    job: Mapping[str, object],
    grouped_weights: Mapping[object, object],
    timing: Mapping[str, object],
    mismatch_checksums: Mapping[int, str],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    wait_for_resources()
    job_id = str(job["job_id"])
    band = str(job["band"])
    band_config = BANDS[band]
    total_frames = int(job["total_frames"])
    warmup = int(job["warmup_frames"])
    maxstep_ps = int(job["maxstep_ps"])
    seed = as_int(job.get("mismatch_seed"))
    noise_mode = str(job["noise_mode"])
    noise_seed = as_int(job.get("noise_seed"))
    pvt = str(job["pvt"])
    ideal = coherent_input_values(total_frames, band, TRACK_FALL_OFFSET_S)

    if noise_mode == "ON":
        if noise_seed is None:
            raise ValueError(f"{job_id}: noise-on job has no noise seed")
        draws = frozen_event_draws(noise_seed, total_frames)
        commanded = ideal + draws["sample_draws_v"]
    elif noise_mode == "OFF":
        draws = {
            "sample_draws_v": np.zeros(total_frames),
            "comparator_draws_v": np.zeros((total_frames, 8)),
            "sample_sigma_v": 0.0,
            "comparator_sigma_v": 0.0,
        }
        commanded = ideal
    else:
        raise ValueError(f"{job_id}: invalid noise mode {noise_mode}")

    deck = build_deck(
        input_spec={"kind": "static_sequence", "vid_values": commanded},
        total_frames=total_frames,
        frame_s=FRAME_PERIOD_S,
        maxstep_s=maxstep_ps * 1e-12,
        pvt_name=pvt,
        mismatch_seed=seed,
        grouped_weights=grouped_weights,
    )
    deck = apply_solver_profile(deck, "ROBUST_GEAR")
    if noise_mode == "ON":
        deck = add_comparator_event_noise(
            deck,
            draws["comparator_draws_v"],
            FRAME_PERIOD_S,
            timing,
            (
                f"FAST64_V2 noise_seed={noise_seed} "
                f"sample_sigma_v={SAMPLE_SIGMA_V:.17g} "
                f"comparator_sigma_v={COMPARATOR_SIGMA_V:.17g} "
                "solver_profile=ROBUST_GEAR"
            ),
        )
    deck = add_startup_path_instrumentation(deck, total_frames, timing)
    run = run_deck(
        deck,
        job_id.lower(),
        JOB_DIR / str(job["phase"]).lower(),
        LOG_DIR / str(job["phase"]).lower(),
        timeout_s=7200,
        cache_completed_failure=True,
    )
    frames = decode_frames(
        run, total_frames, PVT_CASES[pvt]["vdd_v"], FRAME_PERIOD_S
    )
    retained = [frames[index] for index in retained_indices(warmup)]
    codes_all = [int(frame["code"]) for frame in frames]
    retained_codes = [int(frame["code"]) for frame in retained]
    w0_codes = codes_all[:64]
    metrics = fft_metrics(retained_codes, band_config["bin"], SAMPLE_RATE_HZ)
    w0_metrics = fft_metrics(w0_codes, band_config["bin"], SAMPLE_RATE_HZ)
    protocol = protocol_summary(frames, int(run["returncode"]))
    path_rows = decode_path_rows(
        job, run["measures"], total_frames, PVT_CASES[pvt]["vdd_v"]
    )
    path_by_frame = {int(row["frame_index"]): row for row in path_rows}
    frame0 = frames[0]
    frame64 = frames[64] if total_frames > 64 else None
    frame0_path = path_by_frame.get(0, {})
    frame64_path = path_by_frame.get(64, {})
    first_protocol_pass = all(
        (
            int(run["returncode"]) == 0,
            bool(frame0["valid"]),
            float(frame0["stable_margin_s"]) >= 0.0,
            bool(frame0_path.get("driver_analog_match_480", False)),
            bool(frame0_path.get("dout_stable_470_to_480", False)),
        )
    )
    deterministic_pair_pass: object = ""
    if noise_mode == "OFF" and frame64 is not None:
        deterministic_pair_pass = all(
            (
                int(frame0["code"]) == int(frame64["code"]),
                frame0_path.get("comparator_direct_code")
                == frame64_path.get("comparator_direct_code"),
                frame0_path.get("comparator_inverse_code")
                == frame64_path.get("comparator_inverse_code"),
            )
        )
    hard_dynamic_pass = all(
        (
            bool(protocol["protocol_clean"]),
            metrics["clipping_count"] == 0,
            metrics["sndr_db"] >= SNDR_HARD_MIN_DB,
            metrics["enob_raw"] >= ENOB_HARD_MIN_BIT,
        )
    )
    first_conversion_pass = first_protocol_pass and (
        bool(deterministic_pair_pass) if noise_mode == "OFF" else True
    )
    if int(run["returncode"]) != 0:
        state = "SIM_ERROR_UNRESOLVED"
        overall_status = "FAIL_PROTOCOL_OR_COMPLETION"
    elif not bool(protocol["protocol_clean"]):
        state = "MEASUREMENT_BLOCKED"
        overall_status = "FAIL_PROTOCOL_OR_COMPLETION"
    elif not first_conversion_pass:
        state = "COMPLETE_WITH_FAIL"
        overall_status = "FAIL_FIRST_CONVERSION_ONLY"
    elif not hard_dynamic_pass:
        state = "COMPLETE_WITH_FAIL"
        overall_status = "FAIL_STEADY_STATE_DYNAMIC"
    else:
        state = "COMPLETE"
        overall_status = "PASS_FAST64_COMPLETE"

    sample_draws = np.asarray(draws["sample_draws_v"], dtype=float)
    comparator_draws = np.asarray(draws["comparator_draws_v"], dtype=float)
    prefix_count = min(64, total_frames)
    summary: dict[str, object] = {
        "job_id": job_id,
        "phase": job["phase"],
        "role": job["role"],
        "method_id": METHOD_ID,
        "steady_state_method_id": STEADY_METHOD_ID,
        "historical_replay_method_id": HISTORICAL_METHOD_ID,
        "pvt": pvt,
        "mismatch_seed": "" if seed is None else seed,
        "noise_mode": noise_mode,
        "noise_seed": "" if noise_seed is None else noise_seed,
        "band": band,
        "warmup_frames": warmup,
        "total_frames": total_frames,
        "retained_frame_start": warmup,
        "retained_frame_end": warmup + 63,
        "nfft": NFFT,
        "bin": band_config["bin"],
        "fin_hz": band_config["fin_hz"],
        "phase_rad": PHASE_RAD,
        "input_vpp_diff": INPUT_VPP_DIFF_V,
        "aperture_ns": DOUT_APERTURE_NS,
        "maxstep_ns": maxstep_ps / 1000.0,
        "mismatch_checksum": (
            canonical_json_hash({"nominal": True})
            if seed is None
            else mismatch_checksums[seed]
        ),
        "noise_prefix_checksum_0_63": noise_checksum(
            sample_draws[:prefix_count], comparator_draws[:prefix_count]
        ),
        "noise_full_checksum": noise_checksum(sample_draws, comparator_draws),
        "codes_all_checksum": code_checksum(codes_all),
        "codes_retained_checksum": code_checksum(retained_codes),
        "w0_replay_codes_checksum": code_checksum(w0_codes),
        "returncode": run["returncode"],
        "timed_out": run.get("timed_out", False),
        "simulation_aborted": run.get("simulation_aborted", False),
        "cached": run.get("cached", False),
        "elapsed_s": run["elapsed_s"],
        "peak_rss_kb": run.get("peak_rss_kb", 0),
        "deck": Path(run["deck"]).relative_to(ROOT).as_posix(),
        "log": Path(run["log"]).relative_to(ROOT).as_posix(),
        **protocol,
        "first_conversion_code": frame0["code"],
        "same_phase_reference_code": frame64["code"] if frame64 is not None else "",
        "first_conversion_protocol_pass": first_protocol_pass,
        "first_conversion_deterministic_pair_pass": deterministic_pair_pass,
        "first_conversion_status": (
            "PASS_FIRST_CONVERSION_DETERMINISTIC"
            if first_conversion_pass
            else "FIRST_CONVERSION_HISTORY_OR_PATH_DIVERGENCE"
        ),
        "startup_pair_mismatch_count": sum(
            int(frames[index]["code"]) != int(frames[index + 64]["code"])
            for index in range(min(warmup, total_frames - 64))
        ),
        "steady_state_snr_db": metrics["snr_db"],
        "steady_state_sndr_db": metrics["sndr_db"],
        "steady_state_enob_raw": metrics["enob_raw"],
        "steady_state_sfdr_dbc": metrics["sfdr_dbc"],
        "steady_state_thd_db": metrics["thd_db"],
        "steady_state_hd2_dbc": metrics["hd2_dbc"],
        "steady_state_hd3_dbc": metrics["hd3_dbc"],
        "steady_state_parseval_pass": metrics["parseval_pass"],
        "steady_state_clipping_count": metrics["clipping_count"],
        "steady_state_hard_dynamic_pass": hard_dynamic_pass,
        "steady_state_snr_budget_pass": (
            bool(protocol["protocol_clean"])
            and metrics["snr_db"] >= SNR_BUDGET_MIN_DB
        ),
        "steady_state_preferred_pass": all(
            (
                bool(protocol["protocol_clean"]),
                metrics["snr_db"] >= SNR_BUDGET_MIN_DB,
                metrics["sndr_db"] >= SNDR_PREFERRED_DB,
                metrics["enob_raw"] >= ENOB_PREFERRED_BIT,
            )
        ),
        "w0_replay_snr_db": w0_metrics["snr_db"],
        "w0_replay_sndr_db": w0_metrics["sndr_db"],
        "w0_replay_enob_raw": w0_metrics["enob_raw"],
        "w0_replay_sfdr_dbc": w0_metrics["sfdr_dbc"],
        "w0_replay_thd_db": w0_metrics["thd_db"],
        "delta_snr_db": metrics["snr_db"] - w0_metrics["snr_db"],
        "delta_sndr_db": metrics["sndr_db"] - w0_metrics["sndr_db"],
        "delta_enob_raw": metrics["enob_raw"] - w0_metrics["enob_raw"],
        "delta_sfdr_dbc": metrics["sfdr_dbc"] - w0_metrics["sfdr_dbc"],
        "delta_thd_db": metrics["thd_db"] - w0_metrics["thd_db"],
        "state": state,
        "overall_status": overall_status,
        "completed_utc": utc_now(),
    }
    code_rows: list[dict[str, object]] = []
    for frame, ideal_value, commanded_value in zip(frames, ideal, commanded):
        code_rows.append(
            {
                "job_id": job_id,
                "phase": job["phase"],
                "role": job["role"],
                "method_id": METHOD_ID,
                "mismatch_seed": "" if seed is None else seed,
                "noise_mode": noise_mode,
                "noise_seed": "" if noise_seed is None else noise_seed,
                "band": band,
                "warmup_frames": warmup,
                "total_frames": total_frames,
                "maxstep_ns": maxstep_ps / 1000.0,
                "frame_index": frame["frame_index"],
                "phase_index": int(frame["frame_index"]) % NFFT,
                "view": (
                    "FIRST_CONVERSION"
                    if int(frame["frame_index"]) == 0
                    else (
                        "STARTUP_DIAGNOSTIC"
                        if int(frame["frame_index"]) < warmup
                        else "STEADY_STATE_RETAINED"
                    )
                ),
                "retained": int(frame["frame_index"])
                in retained_indices(warmup),
                "ideal_vid_v": ideal_value,
                "commanded_vid_v": commanded_value,
                "code": frame["code"],
                "bits": frame["bits"],
                "valid": frame["valid"],
                "complete_v": frame["complete_v"],
                "invalid_v": frame["invalid_v"],
                "timeout_v": frame["timeout_v"],
                "sampled_diff_v": frame["sampled_diff_v"],
                "input_diff_v": frame["input_diff_v"],
                "complete_time_s": frame["complete_time_s"],
                "stable_margin_s": frame["stable_margin_s"],
            }
        )
    return summary, code_rows, path_rows


def verify_setup() -> None:
    setup = RESULT_DIR / "setup_audit.json"
    if not setup.is_file():
        raise RuntimeError("P0 setup audit is missing")
    payload = json.loads(setup.read_text(encoding="utf-8"))
    if not payload.get("pass"):
        raise RuntimeError("P0 setup audit is not passing")


def write_job_artifacts(
    summary: Mapping[str, object],
    code_rows: list[Mapping[str, object]],
    path_rows: list[Mapping[str, object]],
) -> None:
    job_id = str(summary["job_id"])
    JOB_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    JOB_CODE_DIR.mkdir(parents=True, exist_ok=True)
    JOB_PATH_DIR.mkdir(parents=True, exist_ok=True)
    write_json_atomic(JOB_RESULT_DIR / f"{job_id}.json", dict(summary))
    write_csv_atomic(JOB_CODE_DIR / f"{job_id}.csv", code_rows)
    write_csv_atomic(JOB_PATH_DIR / f"{job_id}.csv", path_rows)


def update_matrix(
    matrix_path: Path, jobs: list[dict[str, str]], summary: Mapping[str, object]
) -> None:
    job_id = str(summary["job_id"])
    for job in jobs:
        if job["job_id"] == job_id:
            job["state"] = str(summary["state"])
            job["returncode"] = str(summary["returncode"])
            job["elapsed_s"] = str(summary["elapsed_s"])
            job["overall_status"] = str(summary["overall_status"])
            job["completed_utc"] = str(summary["completed_utc"])
            break
    write_csv_atomic(matrix_path, jobs)


PHASE_ALIASES = {
    "mc200-low": {"P4_EVENT_NOISE_MC200_LOW"},
    "pvt-tt": {"P4_PVT_TT_MC20_LOW"},
    "pvt-ss": {"P5_PVT_SS_MC20_LOW"},
    "pvt-ff": {"P6_PVT_FF_MC20_LOW"},
    "pvt-formal": {
        "P4_PVT_TT_MC20_LOW",
        "P5_PVT_SS_MC20_LOW",
        "P6_PVT_FF_MC20_LOW",
    },
    "qualification": {
        "P2_WARMUP_QUALIFICATION",
        "P3_NUMERICAL_QUALIFICATION",
    },
    "warmup": {"P2_WARMUP_QUALIFICATION"},
    "numerical": {"P3_NUMERICAL_QUALIFICATION"},
    "main-off": {"P4_FIRST_CONVERSION_COMPANION"},
    "main-on": {"P5_EVENT_NOISE_MC10"},
    "bridge": {"P6_PERCENTILE_BRIDGE"},
    "formal": {
        "P2_WARMUP_QUALIFICATION",
        "P3_NUMERICAL_QUALIFICATION",
        "P4_FIRST_CONVERSION_COMPANION",
        "P5_EVENT_NOISE_MC10",
        "P6_PERCENTILE_BRIDGE",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("smoke", *PHASE_ALIASES),
        required=True,
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--rerun-failed", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("--workers must be between 1 and 4")
    ensure_directories()
    verify_setup()
    matrix_path = SMOKE_MATRIX if args.phase == "smoke" else JOB_MATRIX
    jobs = read_csv(matrix_path)
    if args.phase == "smoke":
        if not jobs:
            jobs = [{key: str(value) for key, value in row.items()} for row in smoke_jobs()]
            write_csv_atomic(matrix_path, jobs)
        allowed = {"P1_SMOKE"}
    else:
        allowed = PHASE_ALIASES[args.phase]
    selected = [
        row
        for row in jobs
        if row["phase"] in allowed
        and (not args.job_id or row["job_id"] in set(args.job_id))
        and (
            row.get("state", "PENDING") == "PENDING"
            or (
                args.rerun_failed
                and row.get("state") in {"SIM_ERROR_UNRESOLVED", "MEASUREMENT_BLOCKED"}
            )
        )
    ]
    print(
        f"FAST64_V2_START phase={args.phase} selected={len(selected)} workers={args.workers}",
        flush=True,
    )
    if not selected:
        return 0
    timing = json.loads(
        (CONFIG_DIR / "timing_tt_3p3_27c.json").read_text(encoding="utf-8")
    )
    grouped_weights = load_cdac_weights()
    mismatch_checksums = mismatch_checksum_table()
    monitor = ResourceMonitor()
    monitor.start()
    started = time.monotonic()
    failures = 0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    run_one_job,
                    job,
                    grouped_weights,
                    timing,
                    mismatch_checksums,
                ): job
                for job in selected
            }
            for future in as_completed(futures):
                job = futures[future]
                try:
                    summary, code_rows, path_rows = future.result()
                except Exception:
                    failures += 1
                    summary = {
                        "job_id": job["job_id"],
                        "phase": job["phase"],
                        "role": job["role"],
                        "state": "SIM_ERROR_UNRESOLVED",
                        "overall_status": "FAIL_PROTOCOL_OR_COMPLETION",
                        "returncode": -1,
                        "elapsed_s": 0,
                        "completed_utc": utc_now(),
                        "error": traceback.format_exc(),
                    }
                    code_rows = []
                    path_rows = []
                write_job_artifacts(summary, code_rows, path_rows)
                update_matrix(matrix_path, jobs, summary)
                print(
                    "{} state={} overall={} elapsed_s={}".format(
                        summary["job_id"],
                        summary["state"],
                        summary["overall_status"],
                        summary["elapsed_s"],
                    ),
                    flush=True,
                )
    finally:
        monitor.stop()
    existing_trace = read_csv(RESOURCE_TRACE)
    invocation = f"{args.phase}_{int(time.time())}"
    trace_rows = [
        {**row, "invocation": invocation, "phase": args.phase}
        for row in monitor.rows
    ]
    write_csv_atomic(RESOURCE_TRACE, [*existing_trace, *trace_rows])
    elapsed = time.monotonic() - started
    write_json_atomic(
        RESULT_DIR / f"execution_{args.phase}.json",
        {
            "status": "PASS_INVOCATION_COMPLETE" if failures == 0 else "FAIL_INVOCATION",
            "phase": args.phase,
            "selected_jobs": len(selected),
            "exception_jobs": failures,
            "workers": args.workers,
            "affinity": sorted(os.sched_getaffinity(0)),
            "wall_elapsed_s": elapsed,
            "max_ngspice_processes": max(
                int(row["ngspice_process_count"]) for row in monitor.rows
            ),
            "max_ngspice_threads": max(
                int(row["ngspice_thread_count"]) for row in monitor.rows
            ),
            "max_ngspice_rss_kb": max(
                int(row["ngspice_rss_kb"]) for row in monitor.rows
            ),
            "completed_utc": utc_now(),
        },
    )
    print(
        f"FAST64_V2_DONE phase={args.phase} elapsed_s={elapsed:.3f} exceptions={failures}",
        flush=True,
    )
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
