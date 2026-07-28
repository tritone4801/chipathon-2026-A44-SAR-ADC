import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ideal_sar_lib import dac_center, dac_threshold, derived_values, direct_quantize, load_config, oracle_quantize, sar_quantize


class GoldenVectorTests(unittest.TestCase):
    def test_transfer_edges_and_ties(self):
        cfg = load_config()
        d = derived_values(cfg)
        self.assertEqual(direct_quantize(d["vmin"], cfg), 0)
        self.assertEqual(direct_quantize(d["vmax"], cfg), 255)
        for code in [1, 127, 128, 255]:
            self.assertEqual(direct_quantize(dac_threshold(code, cfg), cfg), code)


    def test_center_codes_round_trip(self):
        cfg = load_config()
        d = derived_values(cfg)
        codes = np.arange(d["codes"])
        self.assertTrue(np.array_equal(direct_quantize(dac_center(codes, cfg), cfg), codes))


    def test_sar_and_oracle_match_direct(self):
        cfg = load_config()
        d = derived_values(cfg)
        values = np.linspace(d["vmin"], d["vmax"], 4097)
        direct = direct_quantize(values, cfg)
        self.assertTrue(np.array_equal(sar_quantize(values, cfg), direct))
        self.assertTrue(np.array_equal(oracle_quantize(values, cfg), direct))


if __name__ == "__main__":
    unittest.main()
