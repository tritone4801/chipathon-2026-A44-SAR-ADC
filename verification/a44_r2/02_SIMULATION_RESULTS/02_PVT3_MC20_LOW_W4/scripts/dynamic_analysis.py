#!/usr/bin/env python3
import math

import numpy as np

from sar_campaign_common import FULL_SCALE_DIFF_V, LSB_DIFF_V, NUMERICAL_TIEBREAK_DIFF_V


def ideal_codes(vid_values_v):
    values = np.asarray(vid_values_v, dtype=float) + NUMERICAL_TIEBREAK_DIFF_V
    codes = np.floor((values + FULL_SCALE_DIFF_V / 2.0) / LSB_DIFF_V)
    return np.clip(codes, 0, 255).astype(int)


def ratio_db(numerator, denominator):
    if numerator <= 0.0:
        return float("-inf")
    if denominator <= 0.0:
        return float("inf")
    return 10.0 * math.log10(numerator / denominator)


def folded_harmonic_bins(count, fundamental_bin, harmonics=range(2, 6)):
    bins = []
    for harmonic in harmonics:
        raw_bin = (int(harmonic) * int(fundamental_bin)) % int(count)
        folded_bin = raw_bin if raw_bin <= count // 2 else count - raw_bin
        if folded_bin in (0, fundamental_bin) or folded_bin in bins:
            continue
        bins.append(folded_bin)
    return sorted(bins)


def one_sided_spectrum(codes, sample_rate_hz=2.0e6):
    values = np.asarray(codes, dtype=float)
    count = len(values)
    if count < 2:
        raise ValueError("at least two samples are required")
    spectrum = np.fft.rfft(values) / count
    powers = np.abs(spectrum) ** 2
    if count % 2 == 0:
        powers[1:-1] *= 2.0
    else:
        powers[1:] *= 2.0
    frequencies = np.fft.rfftfreq(count, d=1.0 / sample_rate_hz)
    time_mean_square = float(np.mean(values**2))
    spectral_mean_square = float(np.sum(powers))
    scale = max(abs(time_mean_square), np.finfo(float).tiny)
    parseval_relative_error = abs(spectral_mean_square - time_mean_square) / scale
    return {
        "values": values,
        "frequencies_hz": frequencies,
        "powers": powers,
        "time_mean_square": time_mean_square,
        "spectral_mean_square": spectral_mean_square,
        "parseval_relative_error": parseval_relative_error,
        "parseval_pass": parseval_relative_error <= 1.0e-12,
    }


def fft_metrics(codes, fundamental_bin, sample_rate_hz=2.0e6):
    spectral = one_sided_spectrum(codes, sample_rate_hz)
    values = spectral["values"]
    powers = spectral["powers"]
    count = len(values)
    if fundamental_bin <= 0 or fundamental_bin >= len(powers):
        raise ValueError("fundamental bin is outside the one-sided spectrum")
    fundamental_power = float(powers[fundamental_bin])
    harmonic_bins = folded_harmonic_bins(count, fundamental_bin)
    harmonic_powers = {}
    for harmonic in range(2, 6):
        raw_bin = (harmonic * fundamental_bin) % count
        folded = raw_bin if raw_bin <= count // 2 else count - raw_bin
        if folded in (0, fundamental_bin) or folded not in harmonic_bins:
            continue
        harmonic_powers[harmonic] = float(powers[folded])
    harmonic_power = float(sum(powers[index] for index in harmonic_bins))
    noise_bins = [
        index
        for index in range(len(powers))
        if index not in {0, fundamental_bin, *harmonic_bins}
    ]
    noise_power = float(sum(powers[index] for index in noise_bins))
    error_power = noise_power + harmonic_power
    spur_power, spur_bin = max(
        (float(power), index)
        for index, power in enumerate(powers)
        if index not in (0, fundamental_bin)
    )
    full_scale_sine_power = (255.0 / 2.0) ** 2 / 2.0
    mean_noise_bin_power = noise_power / len(noise_bins) if noise_bins else 0.0
    sndr_db = ratio_db(fundamental_power, error_power)
    return {
        "samples": count,
        "fundamental_bin": fundamental_bin,
        "fundamental_frequency_hz": fundamental_bin * sample_rate_hz / count,
        "pfund_linear": fundamental_power,
        "pnoise_linear": noise_power,
        "pharm_linear": harmonic_power,
        "perror_linear": error_power,
        "pspur_max_linear": spur_power,
        "fundamental_dbfs": ratio_db(fundamental_power, full_scale_sine_power),
        "fundamental_rms_code": math.sqrt(max(fundamental_power, 0.0)),
        "fundamental_peak_code": math.sqrt(max(2.0 * fundamental_power, 0.0)),
        "snr_db": ratio_db(fundamental_power, noise_power),
        "sndr_db": sndr_db,
        "enob_raw": (sndr_db - 1.76) / 6.02,
        "enob_bit": (sndr_db - 1.76) / 6.02,
        "sfdr_dbc": ratio_db(fundamental_power, spur_power),
        "thd_db": ratio_db(harmonic_power, fundamental_power),
        "hd2_dbc": ratio_db(harmonic_powers.get(2, 0.0), fundamental_power),
        "hd3_dbc": ratio_db(harmonic_powers.get(3, 0.0), fundamental_power),
        "largest_spur_bin": int(spur_bin),
        "largest_spur_frequency_hz": spur_bin * sample_rate_hz / count,
        "noise_floor_dbfs_per_bin": ratio_db(mean_noise_bin_power, full_scale_sine_power),
        "dc_code_offset": float(np.mean(values) - 127.5),
        "mean_code": float(np.mean(values)),
        "min_code": int(np.min(values)),
        "max_code": int(np.max(values)),
        "clipping_count": int(np.count_nonzero((values <= 0) | (values >= 255))),
        "harmonic_bins": "/".join(str(value) for value in harmonic_bins),
        "parseval_time_mean_square": spectral["time_mean_square"],
        "parseval_spectral_mean_square": spectral["spectral_mean_square"],
        "parseval_relative_error": spectral["parseval_relative_error"],
        "parseval_pass": spectral["parseval_pass"],
    }


def spectrum_rows(codes, fundamental_bin, sample_rate_hz=2.0e6):
    spectral = one_sided_spectrum(codes, sample_rate_hz)
    powers = spectral["powers"]
    count = len(spectral["values"])
    harmonic_bins = folded_harmonic_bins(count, fundamental_bin)
    h2_raw = (2 * fundamental_bin) % count
    h3_raw = (3 * fundamental_bin) % count
    hd2_bin = h2_raw if h2_raw <= count // 2 else count - h2_raw
    hd3_bin = h3_raw if h3_raw <= count // 2 else count - h3_raw
    spur_power, spur_bin = max(
        (float(power), index)
        for index, power in enumerate(powers)
        if index not in (0, fundamental_bin)
    )
    full_scale_sine_power = (255.0 / 2.0) ** 2 / 2.0
    rows = []
    floor = np.finfo(float).tiny
    for index, (frequency_hz, power) in enumerate(
        zip(spectral["frequencies_hz"], powers)
    ):
        rows.append(
            {
                "freq_hz": float(frequency_hz),
                "magnitude_db": 10.0
                * math.log10(max(float(power), floor) / full_scale_sine_power),
                "is_fundamental": index == fundamental_bin,
                "is_hd2": index == hd2_bin,
                "is_hd3": index == hd3_bin,
                "is_largest_spur": index == spur_bin,
                "bin": index,
                "power_linear": float(power),
                "is_declared_harmonic": index in harmonic_bins,
            }
        )
    return rows


def coherent_values(count, bin_index, amplitude_diff_v, phase_rad, sample_offset_s, sample_rate_hz=2.0e6):
    frame_s = 1.0 / sample_rate_hz
    frequency_hz = bin_index * sample_rate_hz / count
    times = np.arange(count, dtype=float) * frame_s + sample_offset_s
    return amplitude_diff_v * np.sin(2.0 * math.pi * frequency_hz * times + phase_rad)


def select_median_phase(count, bin_index, amplitude_diff_v, sample_offset_s):
    rows = []
    for phase_index in range(16):
        phase = 2.0 * math.pi * phase_index / 16.0
        values = coherent_values(
            count, bin_index, amplitude_diff_v, phase, sample_offset_s
        )
        metrics = fft_metrics(ideal_codes(values), bin_index)
        rows.append({"phase_index": phase_index, "phase_rad": phase, **metrics})
    median_sndr = float(np.median([row["sndr_db"] for row in rows]))
    median_sfdr = float(np.median([row["sfdr_dbc"] for row in rows]))
    selected = min(
        rows,
        key=lambda row: (row["sndr_db"] - median_sndr) ** 2
        + (row["sfdr_dbc"] - median_sfdr) ** 2,
    )
    for row in rows:
        row["median_sndr_db"] = median_sndr
        row["median_sfdr_dbc"] = median_sfdr
        row["selected"] = row["phase_index"] == selected["phase_index"]
    return rows, selected
