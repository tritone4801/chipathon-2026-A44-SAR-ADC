# Preserved final-integration CORE DRC and LVS evidence

This directory preserves the exact post-fill GDS container used by the
recorded unified-TOP flow and its DRC/LVS evidence for the selected CORE cell.

This directory records the embedded CORE verification. The repository-root
layout is now the official-DEF-aligned `A44_A` wrapper; its GDS, DEF, pin map,
and fresh top-level checks are in
[`verification/a44_def_alignment`](../../../a44_def_alignment).
The active standalone CORE binding is
[`gds/A44_SAR_ADC_CORE_1000.gds`](../../../../gds/A44_SAR_ADC_CORE_1000.gds).

| Item | Current value |
| --- | --- |
| GDS | [`gds/A44_SAR_ADC_CORE_1000.gds`](gds/A44_SAR_ADC_CORE_1000.gds) |
| Selected DRC/LVS top | `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` |
| Magic style | `drc(full)` |
| Magic result | return code 0; total DRC errors 0; DRC and extraction completion markers present |
| Hierarchical, merge-none LVS | unique full-transistor connectivity match |
| Flat, merge-none LVS | unique full-transistor connectivity match |
| Flat, conservative LVS | unique full-transistor connectivity match |
| Port binding | exact 15-port set in every view |
| Netgen properties | no property errors; no black-box option |

The machine-readable summary is
[`drc_lvs/TOP_MAGIC_DRC_LVS_SUMMARY.json`](drc_lvs/TOP_MAGIC_DRC_LVS_SUMMARY.json).
The complete Magic log and all three Netgen JSON, log, and comparison-output
files are retained under `drc_lvs/`.

The GDS is a container that also includes `chip_top`, fill, I/O, and preserved
orphan hierarchy. The table above records the selected
`A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` cell; `chip_top` and other top
cells are listed separately in the GDS hierarchy.
