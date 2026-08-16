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
It is an additive package; the earlier schematic and simulation material under
`verification/a44_r2` remains available and unchanged.

The W5P29 package contains the current Xschem hierarchy, SPICE netlists,
register-transfer-level sources, sizing lock, source index, and hash audit. Its
active top is `A44_SAR_ADC_TOP_FIXED`, with a buffered `CLKS_CORE` clock path,
TG8 sampling switches, unit-based differential capacitive digital-to-analog
converters, the CMP55 StrongARM comparator, and the R1L slow-slow-corner
parasitic-extraction candidate for the successive-approximation control logic.

The package README marks simulation results that are absent or changed after
the electrical rebinding. No earlier result is promoted to a current W5P29
performance qualification merely because its method or seeds are similar.

The preserved [revision 2 resized-circuit simulation package](verification/a44_r2)
contains:

- current Xschem, SPICE, and register-transfer-level circuit files;
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

## Preserved revision 2 electrical results

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
