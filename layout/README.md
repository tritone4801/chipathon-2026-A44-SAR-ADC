# A44 SAR ADC layout and DEF integration views

The current files are the saved VMP3 layout snapshot built on the Q2 analog
ESD implementation, with the MIM M5 coverFT update and parent PG additions.

```text
info.yaml -> lvs_config.json -> gds/A44_A.gds
                           -> verification/a44_q2_analog_esd/spice/A44_A_lvs_reference.spice
```

[Current file bindings](CURRENT_LAYOUT.json) · [Update record](CHANGELOG.md)

## Project interface

The `A44_A` outline is 1110 × 1110 µm. The 1000 × 1000 µm CORE remains at
`(55,55)` µm, R0. The 89 logical pins and 127 Metal2 pin rectangles retain
their official locations. DEF, LEF and the circuit reference are retained
from the Q2 interface; current internal PG additions are carried by the GDS.

## Current layout catalog

The following existing images show the saved metal/MIM layers in the cell
envelopes. Each drawing preserves its physical aspect ratio.

| Role | GDS top cell | Cell envelope (µm) | Image |
| --- | --- | ---: | --- |
| [TOP](../gds/A44_A.gds) | `A44_A` | 1110 × 1110 | [View](../layout/images/mslot_pg_20260905/A44_A.png) |
| [CORE](../gds/A44_SAR_ADC_CORE_1000.gds) | `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` | 1000 × 1000 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_CORE_1000.png) |
| [CDAC east](../gds/components/A44_SAR_ADC_CDAC_E_390X399P7.gds) | `A44_CDAC_UNIT_E_R8_M6` | 390 × 399.7 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_CDAC_E_390X399P7.png) |
| [CDAC west](../gds/components/A44_SAR_ADC_CDAC_W_390X399P7.gds) | `A44_CDAC_UNIT_W_R8_M6` | 390 × 399.7 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_CDAC_W_390X399P7.png) |
| [Comparator](../gds/components/A44_SAR_ADC_COMPARATOR_168X100.gds) | `A44_COMP_PEX_ECO1_SD_REQUIRED_G6_FULL_R9` | 168 × 100 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_COMPARATOR_168X100.png) |
| [SAR logic](../gds/components/A44_SAR_ADC_SAR_LOGIC_240X240.gds) | `SAR_LOGIC_ACTUAL_RTL_SS` | 240 × 240 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_SAR_LOGIC_240X240.png) |
| [Clock buffer](../gds/components/A44_SAR_ADC_CLKS_BUFFER_120X60.gds) | `A44_CLKS_BUFFER_R1` | 120 × 60 | [View](../layout/images/mslot_pg_20260905/A44_SAR_ADC_CLKS_BUFFER_120X60.png) |
| [Secondary ESD](../gds/components/A44_SECONDARY_ESD_M2.gds) | `io_secondary_5p0` | Source envelope 80 × 76 | [View](images/q2_analog_esd_20260903/io_secondary_5p0.png) |

## Source and verification files

- [TOP and component GDS](../gds) and [current physical-check records](../verification/a44_mslot_pg_20260905).
- [DEF](def/A44_A.def), [LEF](lef/A44_A.lef) and the [unchanged TOP circuit reference](../verification/a44_q2_analog_esd/spice/A44_A_lvs_reference.spice).
- The original `layout/mag` hierarchy and Q2 cache are retained as the source snapshot from commit `7ed565d`; they do not represent the current VMP3 GDS.
- [Q2 analog ESD files](../verification/a44_q2_analog_esd) retain the four `io_secondary_5p0` cells and their original circuit material.
- Previous component images remain in `images/q2_prefill_20260903`.
