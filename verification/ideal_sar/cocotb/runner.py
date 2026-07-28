"""Cocotb runner for the ideal SystemVerilog SAR core."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if shutil.which("iverilog"):
        sim = "icarus"
    elif shutil.which("verilator"):
        sim = "verilator"
    else:
        print("NOT_RUN: no iverilog or verilator found")
        return 77
    cocotb_config = shutil.which("cocotb-config")
    if cocotb_config is None:
        print("NOT_RUN: cocotb-config not found")
        return 77
    try:
        import cocotb  # noqa: F401
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"NOT_RUN: cocotb import failed: {exc}")
        return 77

    build_dir = root / "results" / "raw" / "cocotb_build"
    results_xml = root / "results" / "raw" / "cocotb_results.xml"
    makefiles = subprocess.check_output([cocotb_config, "--makefiles"], text=True).strip()
    env = os.environ.copy()
    env.update(
        {
            "SIM": sim,
            "TOPLEVEL_LANG": "verilog",
            "VERILOG_SOURCES": str(root / "models" / "ideal_sar_core.sv"),
            "TOPLEVEL": "ideal_sar_core",
            "COCOTB_TEST_MODULES": "test_ideal_sar",
            "COCOTB_RESULTS_FILE": str(results_xml),
            "SIM_BUILD": str(build_dir),
            "COMPILE_ARGS": "-g2012",
            "PYTHONPATH": str(root / "cocotb") + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )
    cmd = ["make", "-f", str(Path(makefiles) / "Makefile.sim")]
    cp = subprocess.run(cmd, cwd=str(root), env=env, text=True)
    if cp.returncode != 0:
        print(f"FAIL: cocotb {sim} returned {cp.returncode}")
        return cp.returncode
    print(f"PASS: cocotb {sim} ideal_sar_core smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
