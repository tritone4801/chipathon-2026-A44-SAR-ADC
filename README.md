# Chipathon 2026 Team A44 Successive-Approximation-Register Analog-to-Digital Converter

This repository contains the Team A44 8-bit, 2 mega-samples-per-second,
3.3-volt fully differential capacitive successive-approximation-register
analog-to-digital converter design, its layouts, and its simulation results.

## Current layout review

The current Chipathon 2026 layout-review baseline is the no-pad, pre-fill core
layout selected by `info.yaml` and `lvs_config.json`:

- [Core layout in Graphic Data System format](gds/A44_SAR_ADC_CORE_1000.gds)
- [Component layouts](gds/components)
- [Layout catalog, integration views, and images](layout/README.md)
- [Layout-review presentation](docs/slides/A44_SAR_ADC_LAYOUT_REVIEW_20260821.pptx)

This publication is for layout review. It does not claim density or fill
closure, padframe or electrostatic-discharge completion, full-chip signoff,
Channel Partner acceptance, or tapeout readiness.

## Current schematic baseline

The current transistor-level schematic baseline is the
[W5P29 unit-transmission-gate-driver schematic package](verification/a44_w5p29_trans_driver/01_CURRENT_CIRCUIT_FILES).
It is additive; the
[original GitHub schematic](verification/a44_r2/01_CURRENT_CIRCUIT_FILES)
remains unchanged. Relative to that original schematic, the current baseline
changes only the following published components, bindings, and sizes:

- **StrongARM comparator:** the input pair changes from M3/M4 at
  W/L = 3.51/0.28 micrometres, `m=4`, to CMP55_A XCOMP_INPUT_P/N at
  W/L = 55.8/0.28 micrometres, `m=4`. The published M5/M6 width of
  8.2524 micrometres and M7/M11 width of 16.8587 micrometres are retained.
- **Capacitive digital-to-analog converter:** the monolithic `CDAC`, whose
  capacitor multipliers are 1/2/4/8/16/32/64, changes to
  `A44_CDAC_UNIT_TRANS_DRIVER` with explicit
  `A44_C1_SWITCH`/C2/C4/C8/C16/C32/C64 unit hierarchy. Each C1 unit uses the
  6.855-by-6.855-micrometre metal-insulator-metal capacitor with multiplier 18
  and N/P reference switches at W/L = 1.56/0.28 micrometres, `m=18`. Each side
  has 127 switched units plus one dummy unit, approximately 230.72 picofarads
  per side.
- **Sampling switch:** `SWITCH_BOOT_SP` changes to `A44_SWITCH_TRANS_TG8`;
  its N device is W/L = 3.11/0.28 micrometres, `m=8`, and its P device is
  W/L = 6.22/0.28 micrometres, `m=8`.
- **Digital-control drive:** the direct control connection changes to one
  `A44_CONVERSION_BUFFER` two-stage transistor driver per bit. INV1 N/P widths are 2.34/4.67
  micrometres and INV2 N/P widths are 6.22/12.44 micrometres, all at
  L = 0.28 micrometres.
- **Sampling-clock drive:** direct `CLKS` distribution changes to the
  non-inverting C1 two-stage buffer and internal `CLKS_CORE`. Stage-one N/P
  widths are 0.78/1.56 micrometres and stage-two N/P widths are 3.11/6.22
  micrometres, all at L = 0.28 micrometres.
- **Successive-approximation logic binding:** the generic slow-slow-corner
  parasitic-extraction wrapper changes to the R1L true-transistor
  slow-slow-corner parasitic-extraction core and a header-aware 28-pin wrapper.
  The logic-to-converter/output interface changes from underscore aliases to
  `DCTRLP[7:1]`, `DCTRLN[7:1]`, and `DOUT[7:0]` bracket names.

## Current A44_W5P29_UNIT_TRANS_DRIVER electrical results

| Simulation or execution | Completion | Current interpretation |
| --- | ---: | --- |
| 100-sample independent Monte Carlo mismatch dynamic simulation at the typical-typical process corner, 3.3 volts, 27 degrees Celsius, using the low differential-input band and steady-state frames 4 through 67 | **100/100** | 100/100 hard-dynamic passes and 100/100 signal-to-noise-budget passes; minimum/mean/maximum signal-to-noise-and-distortion ratio is 47.993/48.927/49.890 decibels and effective number of bits is 7.680/7.835/7.995 bits |
| Full 255-transition static transfer-curve simulation | **Planned** | The related `FAST25 STATIC` diagnostic passed all 38 sampled transitions and 29 local differential-nonlinearity checks; maximum absolute local differential nonlinearity is 0.166289 least-significant-bit units |
| Three-corner process-voltage-temperature dynamic simulation using 20 selected Monte Carlo mismatch samples per corner | **Planned** | The related completed W5P29 screen produced 60/60 terminal results, 58/60 hard-dynamic passes, and 56/60 signal-to-noise-budget passes |
| Circuit Automatic Characterization Engine package preflight | **Planned** | The related preserved revision 2 preflight completed 1/1 and reported a final voltage of 1.250 volts |
| Quick result-reproduction run | **Planned** | The related current selected-replay campaign completed 15 dynamic and 5 offset cases, with 12/15 hard-dynamic passes and 5/5 valid offset results |

Historical typical-corner results reproduce exactly when their historical
electrical inputs are restored. The current C18 unit converter, TG8 switch,
CMP55_A input pair, control drivers, and C1 clock buffer form a different
electrical baseline; matching methods or seeds alone does not transfer the old
performance result.

Current full-static and process-voltage-temperature requalification, together
with dynamic coverage outside the completed MC100 typical-corner low-band
experiment, therefore remains open. Completed package,
connectivity, sizing, or selected-replay checks do not imply population yield,
layout or parasitic-extraction signoff, silicon signoff, tapeout readiness, or
production readiness.

## Preserved revision 2 package and electrical results

The preserved [revision 2 resized-circuit simulation package](verification/a44_r2)
contains:

- its revision 2 Xschem, SPICE, and register-transfer-level circuit files;
- completed dynamic, static, and process-voltage-temperature simulation
  results;
- Circuit Automatic Characterization Engine and simulation tooling;
- one-click launchers and method documentation.

All simulations planned for that preserved revision 2 package were executed.
That package was not promoted because three samples failed its hard dynamic
acceptance criteria; those results do not qualify the newer W5P29 electrical
baseline.

See [Team A44 revision 2 progress and performance](docs/A44_SAR_ADC_R2_PROGRESS_AND_PERFORMANCE.md)
for the complete methods, numerical results, result locations, and claim
boundaries.

The current project tracker is available at
[Team A44 project tracker, revision 2](docs/A44_SAR_ADC_Project_Tracker_20260728_R2.xlsx).

| Simulation or execution | Completion | Current interpretation |
| --- | ---: | --- |
| 200-sample Monte Carlo mismatch dynamic simulation at the typical-typical process corner, 3.3 volts, 27 degrees Celsius, using the low differential-input band and steady-state frames 4 through 67 | 200/200 | 197 hard-dynamic passes; failures at seeds 65, 68, and 141 |
| Full 255-transition static transfer-curve simulation | 6 unique curves | Pass based only on seed 44 at the typical-typical process corner, 3.3 volts, and 27 degrees Celsius |
| Three-corner process-voltage-temperature dynamic simulation using 20 selected Monte Carlo mismatch samples per corner | 60/60 | Diagnostic only; not a performance-pass, yield, promotion, or signoff basis |
| Circuit Automatic Characterization Engine package preflight | 1/1 | Pass; final voltage is 1.250 volts |
| Quick result-reproduction run | 130/130 | Pass |

For the full static transfer-curve qualification, seed 44 at the
typical-typical process corner, 3.3 volts, and 27 degrees Celsius is the sole
governing case. Its maximum absolute differential nonlinearity is 0.610351
least-significant-bit units, its maximum absolute integral nonlinearity is
0.686645 least-significant-bit units, and it has no missing codes or
reversals. Other typical-process seeds and the seed-44 slow-slow and fast-fast
corner curves are diagnostic only.

Successful package execution and quick result reproduction do not imply
electrical performance acceptance, population yield, layout or
parasitic-extraction signoff, silicon signoff, tapeout readiness, or production
readiness.

## One-click package entry points

From `verification/a44_r2` on Windows, run the quick result-reproduction flow:

```powershell
.\RUN_QUICK_VERIFY.ps1
```

The full campaign launcher executes every planned dynamic and static
simulation and can be long-running:

```powershell
.\RUN_FULL_CAMPAIGN.ps1
```

To stage and validate the full campaign without dispatching the complete
matrix:

```powershell
docker exec iic-osic-tools_a44_xvnc bash --noprofile --norc -lc "cd /foss/designs/chipathon-2026-A44-SAR-ADC/verification/a44_r2 && make -C 03_CACE_AND_SIMULATION_TOOLS full-dry-run"
```

## Ideal reference model

The earlier ideal successive-approximation-register analog-to-digital
converter flow remains available under
[the ideal reference model](verification/ideal_sar). It is useful as an ideal
system-level baseline, but it is not transistor-level electrical authority and
does not override the current resized-circuit simulation results.
