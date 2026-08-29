# Current A44 cap x1/3 CDAC engineering baseline

This package publishes the review-sized portion of
`A44_CDAC_CAP_X1DIV3_BASELINE_20260828_R1`, the current Team A44 engineering
baseline. It is a versioned derivative of the preserved W5P29 circuit: the C1
and dummy MIM capacitor multiplier changes from 18 to 6, while the
reference-switch multiplier remains 18 and the sampling-TG multiplier remains
8.

## Current status

| Item | Current record | Result summary |
| --- | ---: | --- |
| R8/M6 east and west CDAC layout | DRC 0/0; LVS unique | Native and GDS-readback DRC are clean for both sides; all 12 recorded LVS comparisons are unique |
| Current final-integration CORE | DRC 0; LVS 3/3 | Selected post-fill CORE has zero Magic full-DRC errors and unique full-transistor connectivity matches in hierarchical, flat merge-none, and flat conservative views |
| R8/M6 FULL-RC-CC acquisition, frozen ESD plus input RC, generator plane | 151.832300 ns | TT, 3.3 V, 27 °C; 0.25-LSB enter-and-remain criterion |
| Attempt20 FULL-RC-CC acquisition, same method | 151.934940 ns | 3-point maxstep span is 0.020303 ns |
| Direct-input upward-T1 offset | 100/100 | Whole-ADC TT mean signed offset is 0.430039 LSB |
| Unified TOP MIN2 | **FAIL_FORMAL_MIN2** | Frame 1 ends at PEX code 0x00 while ideal and matching schematic end at 0x01 |
| Unified TOP MIN-MAX-MIN | Nominal functional pass | Codes are [0, 255, 0]; internal settling warning is recorded |
| Unified TOP 0x7F-0x80-0x7F | Nominal functional pass | Codes are [127, 128, 127]; internal settling and comparator-aperture sensitivity remain warnings |

## Package contents

- [`00_CONTRACT`](00_CONTRACT): current status, frozen methods, and completed
  versus open coverage.
- [`01_CURRENT_CIRCUIT_FILES`](01_CURRENT_CIRCUIT_FILES): the cap x1/3 circuit
  delta and fixed input-network files.
- [`02_LAYOUT`](02_LAYOUT): verified east/west GDS, native Magic cells, flat
  LVS netlists, layout images, and the current final-integration GDS plus its
  complete DRC/LVS records.
- [`03_RESULTS`](03_RESULTS): structured acquisition, MC offset, and
  layered unified-TOP conversion results.
- [`STATUS.json`](STATUS.json): machine-readable public status entry point.

## Package scope

The 1.23-GiB engineering snapshot also preserves raw waveforms, simulator
logs, construction worktrees, and failed-attempt history. This GitHub package
contains the current circuit delta, verified layout deliverables, and final
structured records used for review.

No conversion simulation or PEX extraction was rerun while publishing this
component package. The repository-root `lvs_config.json` now binds the
official-DEF-aligned `A44_A` top at `gds/A44_A.gds`; its interface, DRC, and LVS
records are kept in [`verification/a44_def_alignment`](../a44_def_alignment).
