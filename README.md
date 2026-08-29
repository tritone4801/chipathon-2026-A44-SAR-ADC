# Chipathon 2026 Team A44 8-bit SAR ADC

This repository contains the Team A44 8-bit, 2 MS/s, 3.3 V fully differential
capacitive SAR ADC design, its layouts, and its simulation results.

## Published layout-review submission

The retained Chipathon 2026 repository-root layout-review submission is the
no-pad, pre-fill core selected by `info.yaml` and `lvs_config.json`:

- [CORE layout in GDSII format](gds/A44_SAR_ADC_CORE_1000.gds)
- [Component layouts](gds/components)
- [Layout catalog, integration views, and images](layout/README.md)
- [Layout-review presentation](docs/slides/A44_SAR_ADC_LAYOUT_REVIEW_20260821.pptx)

This publication is for layout review. It does not claim density or fill
closure, padframe or ESD completion, full-chip signoff,
Channel Partner acceptance, or tapeout readiness.

The newer R8/M6 CDAC GDS and verification records are published in the current
engineering package above. The repository-root binding is not repointed because
that component package does not provide a newly requalified, coherent root
CORE/LEF/DEF submission set.

## Current engineering baseline

The current working engineering baseline is the
[cap x1/3 CDAC package](verification/a44_cdac_cap_x1div3). It changes the C1
and dummy MIM multiplier from 18 to 6 while retaining the multiplier-18
reference switches, multiplier-8 sampling TG, comparator,
drivers, and SAR logic inherited from the W5P29 circuit.

The current baseline publishes:

- [the cap x1/3 circuit delta](verification/a44_cdac_cap_x1div3/01_CURRENT_CIRCUIT_FILES);
- [qualified R8/M6 east and west CDAC layouts](verification/a44_cdac_cap_x1div3/02_LAYOUT);
- [the current final-integration GDS and DRC/LVS pass evidence](verification/a44_cdac_cap_x1div3/02_LAYOUT/final_integration);
- [structured acquisition, offset, and conversion results](verification/a44_cdac_cap_x1div3/03_RESULTS); and
- [the machine-readable current status](verification/a44_cdac_cap_x1div3/STATUS.json).

The qualified CDAC component layout has zero native and GDS-readback DRC
errors on both sides and unique results for all 12 recorded LVS comparisons.
For the selected final-integration CORE cell, Magic full DRC reports zero
errors and all three hierarchical/flat full-transistor LVS views are unique.
The controlling unified-TOP conversion result is `FAIL_FORMAL_MIN2`: the
second MIN2 frame resolves to 0x00 in PEX while ideal and matching schematic
resolve to 0x01. The MIN-MAX-MIN and 0x7F-0x80-0x7F cases are
bounded nominal functional passes with settling and decision-margin warnings;
they do not override the formal MIN2 failure.

This is a current working baseline, not promotion, full ADC performance
qualification, Channel Partner acceptance, or tapeout signoff.

## Preserved W5P29 schematic baseline

The previously published transistor-level schematic baseline is the
[W5P29 unit-transmission-gate-driver schematic package](verification/a44_w5p29_trans_driver/01_CURRENT_CIRCUIT_FILES).
It is additive; the
[original GitHub schematic](verification/a44_r2/01_CURRENT_CIRCUIT_FILES)
remains unchanged. Relative to that original schematic, the current baseline
changes only the following published components, bindings, and sizes:

- **StrongARM comparator:** the input pair changes from M3/M4 at
  W/L = 3.51/0.28 µm, `m=4`, to CMP55_A XCOMP_INPUT_P/N at
  W/L = 55.8/0.28 µm, `m=4`. The published M5/M6 width of 8.2524 µm and
  M7/M11 width of 16.8587 µm are retained.
- **CDAC:** the monolithic `CDAC`, whose
  capacitor multipliers are 1/2/4/8/16/32/64, changes to
  `A44_CDAC_UNIT_TRANS_DRIVER` with explicit
  `A44_C1_SWITCH`/C2/C4/C8/C16/C32/C64 unit hierarchy. Each C1 unit uses the
  6.855-by-6.855 µm MIM capacitor with multiplier 18 and N/P reference
  switches at W/L = 1.56/0.28 µm, `m=18`. Each side has 127 switched units
  plus one dummy unit, approximately 230.72 pF per side.
- **Sampling switch:** `SWITCH_BOOT_SP` changes to `A44_SWITCH_TRANS_TG8`;
  its N device is W/L = 3.11/0.28 µm, `m=8`, and its P device is
  W/L = 6.22/0.28 µm, `m=8`.
- **Digital-control drive:** the direct control connection changes to one
  `A44_CONVERSION_BUFFER` two-stage transistor driver per bit. INV1 N/P widths
  are 2.34/4.67 µm and INV2 N/P widths are 6.22/12.44 µm, all at L = 0.28 µm.
- **Sampling-clock drive:** direct `CLKS` distribution changes to the
  non-inverting C1 two-stage buffer and internal `CLKS_CORE`. Stage-one N/P
  widths are 0.78/1.56 µm and stage-two N/P widths are 3.11/6.22 µm, all at
  L = 0.28 µm.
- **SAR-logic binding:** the generic SS-corner PEX wrapper changes to the R1L
  true-transistor SS-corner PEX core and a header-aware 28-pin wrapper.
  The logic-to-converter/output interface changes from underscore aliases to
  `DCTRLP[7:1]`, `DCTRLN[7:1]`, and `DOUT[7:0]` bracket names.

## Preserved A44_W5P29_UNIT_TRANS_DRIVER electrical results

The following five entries and their order are preserved from the prior W5P29
publication. They qualify that multiplier-18 capacitor baseline and are not
silently transferred to the current multiplier-6 CDAC.

| Simulation or execution | Completion | Current interpretation |
| --- | ---: | --- |
| 100-sample independent Monte Carlo mismatch dynamic simulation at the typical-typical process corner, 3.3 volts, 27 degrees Celsius, using the low differential-input band and steady-state frames 4 through 67 | **100/100** | Formal audit passed: 100/100 hard-dynamic passes and 100/100 SNR-budget passes, with zero protocol, Parseval, or clipping failures; minimum/mean/maximum SNDR is 47.993/48.927/49.890 dB and ENOB is 7.680/7.835/7.995 bit |
| Full 255-transition static transfer-curve simulation | **255/255** | Representative preselected TT seed 98 passed all 255 transitions, with zero missing codes and zero nonmonotonic transitions; maximum absolute DNL is 0.109557 LSB and maximum absolute endpoint-fit INL is 0.133033 LSB. This is a representative-seed result, not yield, worst-case, PEX pairing, or signoff |
| Three-corner process-voltage-temperature dynamic simulation using 20 selected Monte Carlo mismatch samples per corner | **60/60** | All 60 paired TT, SS, and FF records passed the system specification with zero protocol failures; mean SNDR is 48.928/46.270/48.760 dB, respectively, with SS as the limiting corner. This selected diagnostic campaign uses fixed TT behavioral SAR timing; it is not yield, full-logic PVT qualification, PEX, or signoff |
| Circuit Automatic Characterization Engine package preflight | **Planned** | No CACE package preflight result is included in `PEX_GOLDEN_BASELINE`; the available preflight records qualify individual simulation campaigns and do not complete this entry |
| Quick result-reproduction run | **Planned** | No quick result-reproduction run corresponding to this entry is included in `PEX_GOLDEN_BASELINE`; the folder instead contains audited 100-sample dynamic, full-static, selected three-corner 20-sample, and 100-sample offset packages |

Historical typical-corner results reproduce exactly when their historical
electrical inputs are restored. The current C18 unit converter, TG8 switch,
CMP55_A input pair, control drivers, and C1 clock buffer form a different
electrical baseline; matching methods or seeds alone does not transfer the old
performance result.

Current full-static and PVT requalification, together
with dynamic coverage outside the completed MC100 typical-corner low-band
experiment, therefore remains open. Completed package,
connectivity, sizing, or selected-replay checks do not imply population yield,
layout or PEX signoff, silicon signoff, tapeout readiness, or
production readiness.

## Preserved revision 2 package and electrical results

The preserved [revision 2 resized-circuit simulation package](verification/a44_r2)
contains:

- its revision 2 Xschem, SPICE, and RTL circuit files;
- completed dynamic, static, and PVT simulation
  results;
- CACE and simulation tooling;
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
| Full 255-transition static transfer-curve simulation | 6 unique curves | Pass based only on seed 44 at TT, 3.3 V, and 27 °C |
| Three-corner process-voltage-temperature dynamic simulation using 20 selected Monte Carlo mismatch samples per corner | 60/60 | Diagnostic only; not a performance-pass, yield, promotion, or signoff basis |
| Circuit Automatic Characterization Engine package preflight | 1/1 | Pass; final voltage is 1.250 V |
| Quick result-reproduction run | 130/130 | Pass |

For the full static transfer-curve qualification, seed 44 at the
TT, 3.3 V, and 27 °C is the sole governing case. Its maximum
absolute DNL is 0.610351 LSB, its maximum absolute INL is 0.686645 LSB, and it
has no missing codes or reversals. Other TT seeds and the seed-44 SS and FF
corner curves are diagnostic only.

Successful package execution and quick result reproduction do not imply
electrical performance acceptance, population yield, layout or
PEX signoff, silicon signoff, tapeout readiness, or production
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

The earlier ideal SAR ADC flow remains available under
[the ideal reference model](verification/ideal_sar). It is useful as an ideal
system-level baseline, but it is not transistor-level electrical authority and
does not override the current resized-circuit simulation results.
