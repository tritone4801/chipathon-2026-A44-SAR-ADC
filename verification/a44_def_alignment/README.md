# A44_A official-DEF alignment

This package records the layout selection at commit `52275be`. Its reports
and scripts refer to that earlier selection, now preserved in
[the layout history](../a44_layout_history/pre_q2_20260903).
The current implementation is selected by
[CURRENT_LAYOUT.json](../../layout/CURRENT_LAYOUT.json).

## Recorded layout contract

| Item | Recorded value |
| --- | --- |
| Design and GDS top | `A44_A` |
| Origin | `(0, 0) um` |
| Outline | `1110 x 1110 um` |
| Official logical pins | 89 |
| Official Metal2 pin rectangles | 127 |
| Pin placement | 85 west, 4 north |
| Embedded CORE | `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` at `(55, 55) um`, R0 |
| Active CORE public file | `gds/A44_SAR_ADC_CORE_1000.gds` |
| CDAC implementation | C6 / R8-M6 |

The final DEF has the same `DESIGN`, database units, `DIEAREA`, complete
`PINS` section, and pin order as the official DEF. Every official pin
rectangle is covered by top-level Metal2 and has a same-name GDS label at the
official rectangle center.

## Results

- [`reports/DEF_ALIGNMENT.json`](reports/DEF_ALIGNMENT.json): exact DEF and
  GDS interface comparison, `PASS_DEF_ALIGNED`.
- [`reports/PIN_ALIGNMENT.csv`](reports/PIN_ALIGNMENT.csv): one row per
  logical pin with shape and side counts.
- [`reports/CURRENT_BINDINGS.json`](reports/CURRENT_BINDINGS.json): active
  root, CORE, component, image, DEF, LEF, MAG, and LVS path checks,
  `PASS_CURRENT_BINDINGS`.
- [`reports/DRC_LVS_SUMMARY.json`](reports/DRC_LVS_SUMMARY.json): consolidated
  Magic, KLayout, and Netgen results.
- [`reports/drc_lvs`](reports/drc_lvs): compact tool logs, LVS reports, and
  the KLayout results database.

The checks use the files at their GitHub repository paths. No conversion or
performance simulation was repeated.

## Reproduction

The scripts in [`scripts`](scripts) reproduce the coordinate checks and the
Magic GDS/DEF readback setup. Tool-generated extraction work directories are
kept outside the tracked package; the compact final evidence is under
`reports/drc_lvs`.
