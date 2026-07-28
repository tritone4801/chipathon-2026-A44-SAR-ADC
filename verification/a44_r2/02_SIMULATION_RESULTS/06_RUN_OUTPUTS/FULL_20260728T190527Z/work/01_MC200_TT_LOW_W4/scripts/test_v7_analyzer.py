#!/usr/bin/env python3
"""Deterministic unit checks for V7 FFT normalization and harmonic folding."""

import math

import numpy as np

from dynamic_analysis import (
    fft_metrics,
    folded_harmonic_bins,
    one_sided_spectrum,
    spectrum_rows,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require(
        folded_harmonic_bins(64, 7) == [14, 21, 28, 29],
        "LOW folded harmonic bins do not match the V7 declaration",
    )
    require(
        folded_harmonic_bins(64, 29) == [6, 12, 17, 23],
        "NEAR folded harmonic bins do not match the V7 declaration",
    )
    index = np.arange(64, dtype=float)
    codes = 127.5 + 100.0 * np.sin(2.0 * math.pi * 7.0 * index / 64.0)
    spectral = one_sided_spectrum(codes)
    require(spectral["parseval_pass"], "Parseval check failed for coherent sine")
    require(
        abs(spectral["powers"][7] - 5000.0) <= 1e-9,
        "one-sided sine power normalization is incorrect",
    )
    metrics = fft_metrics(codes, 7)
    require(metrics["parseval_pass"], "metric Parseval flag failed")
    require(metrics["pfund_linear"] > 0.0, "fundamental power is not positive")
    require(metrics["perror_linear"] >= 0.0, "error power is negative")
    rows = spectrum_rows(codes, 7)
    require(len(rows) == 33, "FAST64 one-sided spectrum must contain 33 bins")
    require(sum(row["is_fundamental"] for row in rows) == 1, "fundamental flag count")
    print(
        "PASS analyzer parseval={:.3e} LOW={} NEAR={}".format(
            metrics["parseval_relative_error"],
            folded_harmonic_bins(64, 7),
            folded_harmonic_bins(64, 29),
        )
    )


if __name__ == "__main__":
    main()
