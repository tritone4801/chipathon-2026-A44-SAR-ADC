# Current final-integration CORE DRC and LVS evidence

This directory publishes the exact current post-fill GDS container used by the
baseline's unified-TOP flow and the final DRC/LVS pass records for the selected
CORE cell.

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

The controlling machine-readable record is
[`drc_lvs/TOP_MAGIC_DRC_LVS_SUMMARY.json`](drc_lvs/TOP_MAGIC_DRC_LVS_SUMMARY.json).
The complete Magic log and all three Netgen JSON, log, and comparison-output
files are retained under `drc_lvs/`.

The GDS is a container that also includes `chip_top`, fill, I/O, and preserved
orphan hierarchy. The PASS above is explicitly for the selected
`A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` cell; it is not a DRC/LVS claim
for every top cell in the container.

This PASS covers Magic full DRC and three full-transistor connectivity LVS
views. Official KLayout DRC, density, PEX behavior, electrical performance,
manual review, promotion, and tapeout signoff remain separate gates.
