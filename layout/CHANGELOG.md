# Layout updates

## 2026-09-05 — MIM coverFT and PG layout snapshot

- Updated the existing TOP, CORE and five component GDS paths from the saved VMP3 files.
- Updated their existing image entries and added the corresponding dated image set.
- Updated layout bindings and included the existing GDS DRC/LVS, public KLayout and geometry records.
- Retained the Q2 DEF/LEF interface files, circuit reference and historical layout sources.

## 2026-09-03 — Q2 implementation with analog secondary ESD

Replaces the GitHub layout selection at commit `52275be` with
`Q2_LINK18_HIER_R1_ANALOG_ESD_R1`.

- Updated `A44_A`, the CORE and the five component GDS files to the current Q2 implementation. The CDAC uses the R13 MIM/VBOT breakout and Q2 parent VTOP M5 links; SAR logic uses the TG3G_R7A2 physical implementation with its existing cell name.
- Added four official `io_secondary_5p0` cells on VREFN, VINN, VINP and VREFP, with the corresponding parent routing. The cells add four series poly resistors and 32 diodes.
- Updated routed DEF, LEF, the full TOP LVS circuit reference and the 140-cell Magic hierarchy. The DEF uses 1000 database units per um and includes the ESD instances.
- Retained the 1110 x 1110 um TOP outline, 1000 x 1000 um CORE at (55,55) um, 89 logical ports and 127 external Metal2 rectangles.
- Updated `info.yaml`, `lvs_config.json`, `CURRENT_LAYOUT.json`, `MODULE_NAMING_MAP.csv`, `NAMING_POLICY.json`, and image/implementation bindings.
- Replaced the six canonical component images and added the current TOP, analog routing and ESD views. The layout catalog records cell envelopes and visible dimensions separately.
- Preserved the earlier GitHub layout selection in `verification/a44_layout_history/pre_q2_20260903`.

The current entry point is [CURRENT_LAYOUT.json](CURRENT_LAYOUT.json).
