import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ideal_sar_lib import coherent_sine, derived_values, load_config, spectral_metrics


class MetricFormulaTests(unittest.TestCase):
    def test_known_white_noise_sqnr(self):
        cfg = load_config()
        d = derived_values(cfg)
        npts = 16384
        k = 137
        rng = np.random.default_rng(2026)
        signal = coherent_sine(npts, k, 0.5, 0.0, cfg)
        noise = rng.normal(0.0, d["lsb"], npts)
        metrics = spectral_metrics(signal + noise, signal, k, cfg)
        expected = 10.0 * math.log10(float(np.mean(signal**2)) / float(np.mean(noise**2)))
        self.assertLess(abs(metrics["SQNR_spectral_dB"] - expected), 0.7)


    def test_known_harmonic_sqdr(self):
        cfg = load_config()
        d = derived_values(cfg)
        npts = 16384
        k = 137
        signal = coherent_sine(npts, k, 0.5, 0.0, cfg)
        harmonic = 0.5 * d["vfs_diff_peak"] * 10 ** (-60.0 / 20.0)
        x = signal + harmonic * np.sin(2 * np.pi * 3 * k * np.arange(npts) / npts)
        metrics = spectral_metrics(x, signal, k, cfg)
        self.assertLess(abs(metrics["SQDR_dB"] - 60.0), 0.5)


if __name__ == "__main__":
    unittest.main()
