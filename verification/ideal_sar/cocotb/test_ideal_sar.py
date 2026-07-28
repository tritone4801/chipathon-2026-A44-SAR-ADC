"""Cocotb smoke tests for the CLKS-only ideal SAR core.

These tests are provided for environments with cocotb plus Icarus or Verilator.
The Python harness records NOT_RUN when those tools are missing.
"""

import cocotb
from cocotb.triggers import FallingEdge, Timer


async def init_reset(dut):
    dut.rst_n.value = 0
    dut.clks.value = 1
    dut.vdiff_q_lsb.value = 0
    await Timer(2, unit="ns")
    dut.rst_n.value = 1
    await Timer(2, unit="ns")


async def sample_phase(dut, q_code):
    dut.vdiff_q_lsb.value = q_code
    dut.clks.value = 1
    await Timer(1, unit="ns")


async def convert_code(dut, q_code):
    await sample_phase(dut, q_code)
    dut.clks.value = 0
    await FallingEdge(dut.clks)
    await Timer(1, unit="ns")
    if int(dut.eoc_int.value) != 1:
        raise AssertionError("EOC_INT did not assert")
    return int(dut.dout.value)


def no_unknown(value):
    return all(ch in "01" for ch in str(value).lower())


@cocotb.test()
async def reset_and_midscale_conversion(dut):
    await init_reset(dut)
    assert await convert_code(dut, 128) == 128
    assert int(dut.clk_bit.value) == 0xFF
    assert int(dut.eoc_int.value) == 1


@cocotb.test()
async def dout_holds_during_sample_and_updates_at_eoc(dut):
    await init_reset(dut)
    assert await convert_code(dut, 200) == 200
    await sample_phase(dut, 64)
    assert int(dut.eoc_int.value) == 0
    assert int(dut.dout.value) == 200
    dut.clks.value = 0
    await FallingEdge(dut.clks)
    await Timer(1, unit="ns")
    assert int(dut.eoc_int.value) == 1
    assert int(dut.dout.value) == 64


@cocotb.test()
async def reset_and_internal_observation_ports_are_clean(dut):
    await init_reset(dut)
    assert await convert_code(dut, 37) == 37
    assert no_unknown(dut.dout.value)
    assert no_unknown(dut.eoc_int.value)
    assert no_unknown(dut.clk_bit.value)
    assert no_unknown(dut.dctrlp.value)
    assert no_unknown(dut.dctrln.value)
    assert no_unknown(dut.dcmpp.value)
    assert no_unknown(dut.dcmpn.value)
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    assert int(dut.eoc_int.value) == 0
    assert int(dut.clk_bit.value) == 0
    assert no_unknown(dut.dout.value)
    dut.rst_n.value = 1
    await Timer(1, unit="ns")
