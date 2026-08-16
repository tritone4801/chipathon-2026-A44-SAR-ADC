# Ideal SAR ADC/DAC Validation Harness

This directory is an isolated clean-room ideal testbench for the A44 8-bit,
2-MS/s, 3.3-V fully differential SAR ADC. It implements the execution
specification in `D:\PICO\CODEX_IDEAL_SAR_ADC_TESTBENCH_VALIDATION.md`
without using process mismatch, Monte Carlo, process-voltage-temperature
corners, or schematic nonidealities.

The single source of configuration is `config/sar_adc.yaml`. All Python models,
stimulus generators, checkers, plots, and report builders load that file.

Key conventions now match `D:\PICO\current_goal.md`:

- `v_diff = VINP - VINN`
- legal input range: `-1.70 V <= v_diff <= +1.70 V`
- `VREFP = 2.50 V`, `VREFN = 0.80 V`
- `VFS_diff_pp = 3.4 V`
- `LSB_diff = 3.4 V / 256 = 13.28125 mV`
- straight-binary, mid-rise quantizer
- normal external functional clock is `CLKS` only
- `EOC_INT` is an internal observation signal; there is no external `READY`
- transition DAC: `V_DAC_threshold(code) = v_min + code*LSB`
- reconstruction DAC: `V_DAC_center(code) = v_min + (code+0.5)*LSB`
- tie rule: an input exactly on transition `k` returns code `k`

Main entry points:

```powershell
python verification\ideal_sar\scripts\run_all.py all
```

Chipathon container entry point used for the external `ngspice` and
`cocotb`/Icarus gates:

```powershell
docker run --rm -v "D:/PICO/simple_SAR_ADC_repo:/work" -w /work hpretl/iic-osic-tools:chipathon26 --skip bash -lc "python3 verification/ideal_sar/scripts/run_all.py all"
```

If GNU Make is available:

```powershell
make -C verification/ideal_sar all
```

Generated results:

- `results/README.md`
- `results/README.zh-CN.md`
- `results/csv/metrics.csv`
- `results/csv/coverage_matrix.csv`
- `results/csv/repeatability_check.csv`
- `results/metrics.json`
- `results/plots/`
- `results/logs/`
- `report/ideal_sar_adc_testbench_validation.md`

External simulator status is measured, not assumed. If `ngspice`, `iverilog`,
`verilator`, or `cocotb` are unavailable, the corresponding rows are marked
`NOT_RUN` or `FAIL` and the final Go/No-Go decision remains `NO-GO` even when
the Python ideal baseline passes.
