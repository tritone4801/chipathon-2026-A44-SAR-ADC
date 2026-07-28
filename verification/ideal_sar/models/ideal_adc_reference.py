"""Direct ideal ADC reference model for the A44 SAR ADC."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ideal_sar_lib import direct_quantize, load_config, derived_values


def convert(vdiff):
    cfg = load_config()
    return direct_quantize(vdiff, cfg)


def derived():
    return derived_values(load_config())


if __name__ == "__main__":
    cfg = load_config()
    d = derived_values(cfg)
    for voltage in [d["vmin"], -d["lsb"], 0.0, d["lsb"], d["vmax"]]:
        print(f"{voltage:.9f} V -> {int(direct_quantize(voltage, cfg))}")

