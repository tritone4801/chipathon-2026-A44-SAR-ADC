# Current A44 cap x1/3 CDAC engineering baseline

This package publishes the review-sized portion of
`A44_CDAC_CAP_X1DIV3_BASELINE_20260828_R1`, the current Team A44 engineering
baseline. It is a versioned derivative of the preserved W5P29 circuit: the C1
and dummy metal-insulator-metal capacitor multiplier changes from 18 to 6,
while the reference-switch multiplier remains 18 and the sampling
transmission-gate multiplier remains 8.

## Current status

| Gate or result | Current record | Interpretation |
| --- | ---: | --- |
| Qualified R8/M6 east and west CDAC layout | DRC 0/0; LVS unique | Native and second-generation GDS-readback DRC are clean for both sides; all 12 recorded LVS comparisons are unique |
| Current final-integration CORE | DRC 0; LVS 3/3 | Selected post-fill CORE has zero Magic full-DRC errors and unique full-transistor connectivity matches in hierarchical, flat merge-none, and flat conservative views |
| R8/M6 FULL-RC-CC acquisition, frozen ESD plus input RC, generator plane | 151.832300 ns | TT, 3.3 V, 27 degrees Celsius; 0.25-least-significant-bit enter-and-remain criterion |
| Attempt20 FULL-RC-CC acquisition, same method | 151.934940 ns | Three-point maximum-timestep span is 0.020303 ns |
| Direct-input upward-T1 offset | 100/100 | Mean signed offset is 0.430039 least-significant-bit units; this is a whole-ADC TT experiment, not comparator-only offset or yield |
| Unified TOP MIN2 | **FAIL_FORMAL_MIN2** | Frame 1 ends at parasitic-extraction code 0x00 while ideal and matching schematic end at 0x01 |
| Unified TOP minimum-maximum-minimum | Nominal functional pass | Codes are [0, 255, 0]; internal settling margin remains a warning and robust margin is not proven |
| Unified TOP 0x7F-0x80-0x7F | Nominal functional pass | Codes are [127, 128, 127]; internal settling and comparator-aperture sensitivity remain warnings |

The formal MIN2 failure is the controlling unified-TOP conversion result. The
two correct three-frame cases are bounded supplemental evidence and do not
override that failure.

## Package contents

- [`00_CONTRACT`](00_CONTRACT): current status, frozen methods, and completed
  versus open coverage.
- [`01_CURRENT_CIRCUIT_FILES`](01_CURRENT_CIRCUIT_FILES): the cap x1/3 circuit
  delta and fixed input-network files.
- [`02_LAYOUT`](02_LAYOUT): qualified east/west GDS, native Magic cells, flat
  LVS netlists, layout images, and the current final-integration GDS plus its
  complete DRC/LVS pass records.
- [`03_RESULTS`](03_RESULTS): structured acquisition, Monte Carlo offset, and
  layered unified-TOP conversion results.
- [`STATUS.json`](STATUS.json): machine-readable public status entry point.

## Publication boundary

The 1.23-GiB engineering snapshot also preserves raw waveforms, simulator
logs, construction worktrees, and failed-attempt history. Those large and
mostly reproducible files are not duplicated here; this publication contains
the current circuit delta, qualified layout deliverables, and final structured
records needed for review.

No simulation, extraction, DRC, LVS, or hash audit was rerun for this GitHub
publication. The repository-root `info.yaml` and `lvs_config.json` remain bound
to the retained no-pad layout-review submission because this package does not
claim a newly requalified standalone root CORE/LEF/DEF submission set.

This package does not prove full static linearity, low-frequency or
near-Nyquist dynamic performance, noise, mismatch, full-logic process-voltage-
temperature coverage, population yield, promotion, or tapeout signoff.
