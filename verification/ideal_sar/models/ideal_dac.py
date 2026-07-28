"""Ideal threshold and reconstruction DAC functions."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ideal_sar_lib import dac_center, dac_threshold, load_config


def threshold(code):
    return dac_threshold(code, load_config())


def center(code):
    return dac_center(code, load_config())


if __name__ == "__main__":
    for code in [0, 1, 127, 128, 255]:
        print(f"{code},{threshold(code):.9f},{center(code):.9f}")

