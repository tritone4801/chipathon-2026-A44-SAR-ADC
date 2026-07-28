#!/usr/bin/env python3
"""Frozen event-noise adapter for the campaign-local transient decks."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from sar_campaign_common import (
    FRAME_DEFAULT_S,
    ROOT,
    TRACK_FALL_OFFSET_S,
    PVT_CASES,
    build_deck,
    decode_frames,
    load_cdac_weights,
    run_deck,
)


COMPARATOR_SIGMA_V = 1.5e-3
SAMPLE_SIGMA_V = 64.681023032e-6
COMPARATOR_NOISE_EDGE_S = 100e-12
COMPARATOR_NOISE_FRAME_UPDATE_OFFSET_S = 10e-9
ROBUST_GEAR_OPTIONS = (
    ".options method=gear reltol=3e-4 abstol=3e-13 vntol=3e-7 trtol=10 "
    "chgtol=1e-14 rshunt=1e10 gmin=1e-12 itl1=500 itl4=1000"
)
ULTRA_ROBUST_GEAR_OPTIONS = (
    ".options method=gear reltol=1e-3 abstol=1e-12 vntol=1e-6 trtol=20 "
    "chgtol=1e-13 rshunt=1e9 gmin=1e-10 itl1=1000 itl4=5000"
)


def frozen_event_draws(noise_seed, total_frames, comparator_sigma_v=COMPARATOR_SIGMA_V, sample_sigma_v=SAMPLE_SIGMA_V):
    sequence = np.random.SeedSequence([0xA44, 0xE77, int(noise_seed)])
    sample_sequence, comparator_sequence = sequence.spawn(2)
    sample_rng = np.random.Generator(np.random.PCG64(sample_sequence))
    comparator_rng = np.random.Generator(np.random.PCG64(comparator_sequence))
    return {
        "noise_seed": int(noise_seed),
        "sample_draws_v": sample_rng.normal(0.0, sample_sigma_v, total_frames),
        "comparator_draws_v": comparator_rng.normal(
            0.0, comparator_sigma_v, (total_frames, 8)
        ),
        "sample_sigma_v": float(sample_sigma_v),
        "comparator_sigma_v": float(comparator_sigma_v),
    }


def _bit_timing(timing):
    aperture = {
        bit: timing["decision_aperture_from_cmpck_rise"][7 - bit]
        for bit in range(8)
    }
    high = {bit: timing["cmpck_high"][7 - bit] for bit in range(8)}
    low = {
        bit: timing["cmpck_low_guard_bits_7_to_1"][7 - bit]
        for bit in range(1, 8)
    }
    return aperture, high, low


def decision_apertures_s(total_frames, frame_s, timing):
    aperture_ns, high_ns, low_ns = _bit_timing(timing)
    output = []
    for frame in range(total_frames):
        rise_s = (
            frame * frame_s
            + TRACK_FALL_OFFSET_S
            + timing["t_clks_fall_to_first_cmpck_rise"] * 1e-9
        )
        frame_times = []
        for bit in range(7, -1, -1):
            frame_times.append(rise_s + aperture_ns[bit] * 1e-9)
            if bit > 0:
                rise_s += (high_ns[bit] + low_ns[bit]) * 1e-9
        output.append(frame_times)
    return output


def comparator_noise_source(draws_v, frame_s, timing):
    draws = np.asarray(draws_v, dtype=float)
    total_frames = draws.shape[0]
    if draws.shape != (total_frames, 8):
        raise ValueError("comparator draws must have shape (frames, 8)")
    apertures = decision_apertures_s(total_frames, frame_s, timing)
    edge_s = COMPARATOR_NOISE_EDGE_S
    points = [(0.0, float(draws[0, 0]))]
    for frame in range(total_frames):
        frame_start = frame * frame_s
        if frame > 0:
            update_s = frame_start + COMPARATOR_NOISE_FRAME_UPDATE_OFFSET_S
            points.append((update_s - edge_s, float(draws[frame - 1, -1])))
            points.append((update_s, float(draws[frame, 0])))
        for bit_offset in range(1, 8):
            boundary = apertures[frame][bit_offset - 1] + 6e-9
            points.append((boundary - edge_s, float(draws[frame, bit_offset - 1])))
            points.append((boundary, float(draws[frame, bit_offset])))
    points.append((total_frames * frame_s, float(draws[-1, -1])))
    tokens = [f"{time_s:.12g} {value_v:.17g}" for time_s, value_v in points]
    lines = ["VCMP_NOISE cmp_noise 0 PWL("]
    for start in range(0, len(tokens), 4):
        lines.append("+ " + " ".join(tokens[start : start + 4]))
    lines.append("+ )")
    return "\n".join(lines)


def add_comparator_event_noise(deck, comparator_draws_v, frame_s, timing, provenance):
    noisy = deck
    replacements = (
        (
            "+ DCMPP DCMPN VRESP VRESN\n",
            "+ DCMPP DCMPN VRESP VRESN CMPNOISE\n",
        ),
        (
            "XCDACP VINP CLKS VRESP ",
            "XCDACP VINP CLKS VRESP_RAW ",
        ),
        (
            "XCDACN VINN CLKS VRESN ",
            "XCDACN VINN CLKS VRESN_RAW ",
        ),
        (
            "XCMP CMPCK DCMPP VRESP DCMPN VRESN VDD GND Comparator_StrongARM",
            "E_CMP_NOISE_P VRESP VRESP_RAW CMPNOISE GND 0.5\n"
            "E_CMP_NOISE_N VRESN VRESN_RAW CMPNOISE GND -0.5\n"
            "XCMP CMPCK DCMPP VRESP DCMPN VRESN VDD GND Comparator_StrongARM",
        ),
        (
            "+ dcmpp dcmpn vresp vresn SAR_ADC_ACTIVE",
            "+ dcmpp dcmpn vresp vresn cmp_noise SAR_ADC_ACTIVE",
        ),
    )
    for old, new in replacements:
        if noisy.count(old) != 1:
            raise RuntimeError(f"noisy-deck anchor count is {noisy.count(old)} for {old!r}")
        noisy = noisy.replace(old, new, 1)
    source = comparator_noise_source(comparator_draws_v, frame_s, timing)
    anchor = "\nXCORE vdd 0 vrefp vrefn vinp vinn clks cmpck\n"
    if noisy.count(anchor) != 1:
        raise RuntimeError("XCORE insertion anchor missing")
    noisy = noisy.replace(anchor, f"\n{source}\n{anchor}", 1)
    noisy = noisy.replace(
        "* A44 actual analog core with fixed TT timed behavioral SAR control.\n",
        "* A44 actual analog core with fixed TT timed behavioral SAR control.\n"
        f"* T2_EVENT_NOISE {provenance}\n",
        1,
    )
    return noisy


def apply_solver_profile(base_deck, solver_profile):
    if solver_profile == "DEFAULT":
        return base_deck
    options = {
        "ROBUST_GEAR": ROBUST_GEAR_OPTIONS,
        "ULTRA_ROBUST_GEAR": ULTRA_ROBUST_GEAR_OPTIONS,
    }
    if solver_profile not in options:
        raise ValueError(f"unknown solver profile {solver_profile}")
    lines = base_deck.splitlines()
    option_indices = [
        index for index, line in enumerate(lines) if line.startswith(".options ")
    ]
    if len(option_indices) != 1:
        raise RuntimeError("event-noise deck must contain exactly one .options line")
    lines[option_indices[0]] = options[solver_profile]
    return "\n".join(lines) + "\n"


def run_event_frames(
    stem,
    ideal_vid_values,
    noise_seed,
    timing,
    job_dir,
    log_dir,
    frame_s=FRAME_DEFAULT_S,
    maxstep_s=100e-12,
    pvt_name="TT_3P3_27C",
    mismatch_seed=None,
    grouped_weights=None,
    comparator_sigma_v=COMPARATOR_SIGMA_V,
    sample_sigma_v=SAMPLE_SIGMA_V,
    timeout_s=3600,
    v7_infrastructure_retry=False,
    raw_dir=None,
    v7_primary_solver_profile="DEFAULT",
):
    ideal = np.asarray(ideal_vid_values, dtype=float)
    total_frames = len(ideal)
    if grouped_weights is None:
        grouped_weights = load_cdac_weights()
    draws = frozen_event_draws(
        noise_seed,
        total_frames,
        comparator_sigma_v=comparator_sigma_v,
        sample_sigma_v=sample_sigma_v,
    )
    commanded = ideal + draws["sample_draws_v"]
    provenance = (
        f"noise_seed={int(noise_seed)} sample_sigma_v={sample_sigma_v:.17g} "
        f"comparator_sigma_v={comparator_sigma_v:.17g} "
        f"comparator_noise_edge_s={COMPARATOR_NOISE_EDGE_S:.17g} "
        f"frame_update_offset_s={COMPARATOR_NOISE_FRAME_UPDATE_OFFSET_S:.17g}"
    )

    def execute(attempt_stem, attempt_maxstep_s, solver_profile):
        base_deck = build_deck(
            input_spec={"kind": "static_sequence", "vid_values": commanded},
            total_frames=total_frames,
            frame_s=frame_s,
            maxstep_s=attempt_maxstep_s,
            pvt_name=pvt_name,
            mismatch_seed=mismatch_seed,
            grouped_weights=grouped_weights,
        )
        base_deck = apply_solver_profile(base_deck, solver_profile)
        deck = add_comparator_event_noise(
            base_deck,
            draws["comparator_draws_v"],
            frame_s,
            timing,
            f"{provenance} solver_profile={solver_profile}",
        )
        attempt = run_deck(
            deck,
            attempt_stem,
            job_dir,
            log_dir,
            timeout_s=timeout_s,
            cache_completed_failure=True,
            raw_path=(
                raw_dir / f"{attempt_stem}.raw"
                if raw_dir is not None
                else None
            ),
        )
        attempt["frames"] = decode_frames(
            attempt, total_frames, PVT_CASES[pvt_name]["vdd_v"], frame_s
        )
        attempt["noise"] = draws
        attempt["ideal_vid_values"] = ideal
        attempt["commanded_vid_values"] = commanded
        attempt["attempt_stem"] = attempt_stem
        attempt["attempt_maxstep_s"] = attempt_maxstep_s
        attempt["solver_profile"] = solver_profile
        return attempt

    attempts = [execute(stem, maxstep_s, v7_primary_solver_profile)]
    if v7_infrastructure_retry:
        if attempts[-1]["returncode"] != 0:
            attempts.append(
                execute(
                    f"{stem}_infrastructure_retry",
                    maxstep_s,
                    v7_primary_solver_profile,
                )
            )
    else:
        if attempts[-1]["returncode"] != 0 and maxstep_s > 50e-12:
            attempts.append(execute(f"{stem}_strict_retry", 50e-12, "DEFAULT"))
        if attempts[-1]["returncode"] != 0:
            attempts.append(execute(f"{stem}_robust_retry", 50e-12, "ROBUST_GEAR"))
        if attempts[-1]["returncode"] != 0:
            attempts.append(
                execute(f"{stem}_ultra_robust_retry", 50e-12, "ULTRA_ROBUST_GEAR")
            )

    first = attempts[0]
    result = attempts[-1]
    result.update(
        {
            "bulk_stem": first["attempt_stem"],
            "bulk_returncode": first["returncode"],
            "bulk_simulation_aborted": first.get("simulation_aborted", False),
            "bulk_elapsed_s": first["elapsed_s"],
            "retry_used": len(attempts) > 1,
            "retry_stem": result["attempt_stem"] if len(attempts) > 1 else "",
            "retry_returncode": result["returncode"] if len(attempts) > 1 else "",
            "retry_simulation_aborted": (
                result.get("simulation_aborted", False) if len(attempts) > 1 else ""
            ),
            "measurement_stem": result["attempt_stem"],
            "measurement_maxstep_s": result["attempt_maxstep_s"],
            "measurement_solver_profile": result["solver_profile"],
            "attempt_count": len(attempts),
            "attempt_stems": ";".join(item["attempt_stem"] for item in attempts),
            "attempt_solver_profiles": ";".join(item["solver_profile"] for item in attempts),
            "attempt_returncodes": ";".join(str(item["returncode"]) for item in attempts),
            "attempt_simulation_aborted": ";".join(
                str(item.get("simulation_aborted", False)) for item in attempts
            ),
            "attempt_elapsed_s": ";".join(
                f"{item['elapsed_s']:.12g}" for item in attempts
            ),
            "peak_rss_kb": max(item.get("peak_rss_kb", 0) for item in attempts),
            "timed_out": any(item.get("timed_out", False) for item in attempts),
            "elapsed_s": sum(item["elapsed_s"] for item in attempts),
        }
    )
    return result


def run_event_frames_isolated(
    stem,
    ideal_vid_values,
    noise_seed,
    timing,
    job_dir,
    log_dir,
    frame_s=FRAME_DEFAULT_S,
    maxstep_s=50e-12,
    pvt_name="TT_3P3_27C",
    mismatch_seed=None,
    grouped_weights=None,
    comparator_sigma_v=COMPARATOR_SIGMA_V,
    sample_sigma_v=SAMPLE_SIGMA_V,
    timeout_s=900,
    max_workers=4,
):
    """Replay independent reset frames while preserving the frozen event draws."""
    ideal = np.asarray(ideal_vid_values, dtype=float)
    total_frames = len(ideal)
    if grouped_weights is None:
        grouped_weights = load_cdac_weights()
    draws = frozen_event_draws(
        noise_seed,
        total_frames,
        comparator_sigma_v=comparator_sigma_v,
        sample_sigma_v=sample_sigma_v,
    )
    commanded = ideal + draws["sample_draws_v"]
    provenance = (
        f"noise_seed={int(noise_seed)} sample_sigma_v={sample_sigma_v:.17g} "
        f"comparator_sigma_v={comparator_sigma_v:.17g} "
        f"comparator_noise_edge_s={COMPARATOR_NOISE_EDGE_S:.17g} "
        f"frame_update_offset_s={COMPARATOR_NOISE_FRAME_UPDATE_OFFSET_S:.17g} "
        "execution=FRAME_ISOLATED_REPLAY"
    )

    def execute_frame(frame_index):
        attempts = []
        profiles = ("DEFAULT", "ROBUST_GEAR", "ULTRA_ROBUST_GEAR")
        for profile in profiles:
            suffix = {
                "DEFAULT": "",
                "ROBUST_GEAR": "_robust_retry",
                "ULTRA_ROBUST_GEAR": "_ultra_robust_retry",
            }[profile]
            attempt_stem = f"{stem}_f{frame_index:03d}{suffix}"
            base_deck = build_deck(
                input_spec={
                    "kind": "static_sequence",
                    "vid_values": [commanded[frame_index]],
                },
                total_frames=1,
                frame_s=frame_s,
                maxstep_s=maxstep_s,
                pvt_name=pvt_name,
                mismatch_seed=mismatch_seed,
                grouped_weights=grouped_weights,
            )
            base_deck = apply_solver_profile(base_deck, profile)
            deck = add_comparator_event_noise(
                base_deck,
                draws["comparator_draws_v"][frame_index : frame_index + 1],
                frame_s,
                timing,
                f"{provenance} global_frame={frame_index} solver_profile={profile}",
            )
            attempt = run_deck(
                deck,
                attempt_stem,
                job_dir,
                log_dir,
                timeout_s=timeout_s,
                cache_completed_failure=True,
            )
            decoded = decode_frames(
                attempt, 1, PVT_CASES[pvt_name]["vdd_v"], frame_s
            )
            attempt.update(
                {
                    "attempt_stem": attempt_stem,
                    "solver_profile": profile,
                    "decoded_frame": decoded[0],
                }
            )
            attempts.append(attempt)
            if attempt["returncode"] == 0 and decoded[0]["valid"]:
                break

        final = attempts[-1]
        frame = dict(final["decoded_frame"])
        frame["frame_index"] = frame_index
        if np.isfinite(frame["complete_time_s"]):
            frame["complete_time_s"] += frame_index * frame_s
        frame.update(
            {
                "measurement_stem": final["attempt_stem"],
                "measurement_maxstep_s": maxstep_s,
                "measurement_solver_profile": final["solver_profile"],
                "attempt_count": len(attempts),
                "attempt_stems": ";".join(item["attempt_stem"] for item in attempts),
                "attempt_solver_profiles": ";".join(
                    item["solver_profile"] for item in attempts
                ),
                "attempt_returncodes": ";".join(
                    str(item["returncode"]) for item in attempts
                ),
                "attempt_simulation_aborted": ";".join(
                    str(item.get("simulation_aborted", False)) for item in attempts
                ),
                "attempt_elapsed_s": ";".join(
                    f"{item['elapsed_s']:.12g}" for item in attempts
                ),
            }
        )
        return frame, attempts

    started = time.perf_counter()
    completed = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_frame, frame_index): frame_index
            for frame_index in range(total_frames)
        }
        for future in as_completed(futures):
            completed.append(future.result())
    completed.sort(key=lambda item: item[0]["frame_index"])
    frames = [item[0] for item in completed]
    frame_attempts = [item[1] for item in completed]
    attempts = [attempt for group in frame_attempts for attempt in group]
    first_attempts = [group[0] for group in frame_attempts]
    final_attempts = [group[-1] for group in frame_attempts]
    final_profiles = sorted({item["solver_profile"] for item in final_attempts})
    final_ok = all(
        item["returncode"] == 0 and frame["valid"]
        for item, frame in zip(final_attempts, frames)
    )
    first_ok = all(
        item["returncode"] == 0 and item["decoded_frame"]["valid"]
        for item in first_attempts
    )
    return {
        "frames": frames,
        "noise": draws,
        "ideal_vid_values": ideal,
        "commanded_vid_values": commanded,
        "elapsed_s": sum(float(item["elapsed_s"]) for item in attempts),
        "wall_elapsed_s": time.perf_counter() - started,
        "cached": all(item.get("cached", False) for item in final_attempts),
        "bulk_stem": f"{stem}_FRAME_ISOLATED_DEFAULT_SET",
        "bulk_returncode": 0 if first_ok else 3,
        "bulk_simulation_aborted": any(
            item.get("simulation_aborted", False) for item in first_attempts
        ),
        "retry_used": any(len(group) > 1 for group in frame_attempts),
        "retry_stem": f"{stem}_FRAME_ISOLATED_RETRY_SET",
        "retry_returncode": 0 if final_ok else 3,
        "retry_simulation_aborted": any(
            item.get("simulation_aborted", False) for item in final_attempts
        ),
        "measurement_stem": f"{stem}_FRAME_ISOLATED_SET",
        "measurement_maxstep_s": maxstep_s,
        "measurement_solver_profile": "FRAME_ISOLATED_" + "+".join(final_profiles),
        "attempt_count": len(attempts),
        "attempt_stems": ";".join(item["attempt_stem"] for item in attempts),
        "attempt_solver_profiles": ";".join(
            item["solver_profile"] for item in attempts
        ),
        "attempt_returncodes": ";".join(
            str(item["returncode"]) for item in attempts
        ),
        "attempt_simulation_aborted": ";".join(
            str(item.get("simulation_aborted", False)) for item in attempts
        ),
        "attempt_elapsed_s": ";".join(
            f"{item['elapsed_s']:.12g}" for item in attempts
        ),
        "frame_attempts": frame_attempts,
    }
