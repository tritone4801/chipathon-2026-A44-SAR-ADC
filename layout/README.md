# Published A44 SAR ADC layout-review views

This directory retains the Chipathon 2026 layout-review submission for Team
A44. It contains the no-pad, pre-fill CORE layout and the five direct component
layouts instantiated by that submitted CORE.

The official dry-run binding remains:

```text
info.yaml -> lvs_config.json
TOP_LAYOUT = A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR
LAYOUT_FILE = gds/A44_SAR_ADC_CORE_1000.gds
```

The later cap x1/3 R8/M6 CDAC component layouts and their current DRC/LVS and
PEX result records are published separately under
[`verification/a44_cdac_cap_x1div3`](../verification/a44_cdac_cap_x1div3).
The repository-root binding continues to use the retained CORE/LEF/DEF set.

## Published layout names

All public filenames use the `A44_SAR_ADC_` prefix and omit revision suffixes.
GDS top-cell names remain unchanged so that hierarchy and existing integration
contracts are preserved.

| Role | Public filename stem | GDS top cell | Size (um) |
| --- | --- | --- | ---: |
| CORE | `A44_SAR_ADC_CORE_1000` | `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` | 1000 x 1000 |
| CDAC east | `A44_SAR_ADC_CDAC_E` | `A44_CDAC_UNIT_E_R7` | 390 x 626 |
| CDAC west | `A44_SAR_ADC_CDAC_W` | `A44_CDAC_UNIT_W_R7` | 390 x 626 |
| Comparator | `A44_SAR_ADC_COMPARATOR` | `A44_COMP_PEX_ECO1_SD_REQUIRED_G6_FULL_R9` | 168 x 100 |
| SAR logic | `A44_SAR_ADC_SAR_LOGIC` | `SAR_LOGIC_ACTUAL_RTL_SS` | 240 x 240 |
| Clock buffer | `A44_SAR_ADC_CLKS_BUFFER` | `A44_CLKS_BUFFER_R1` | 120 x 60 |

## Directory contents

- `../gds/`: the authoritative CORE GDS used by `lvs_config.json`.
- `../gds/components/`: one standalone GDS for each direct CORE component.
- `lef/`: CORE and component integration abstracts.
- `def/`: SAR logic placement/routing view.
- `images/`: exactly one full-layout image for each published GDS.
- `../docs/slides/`: the layout-review presentation.

## Layout contents

This retained layout-review publication contains the pre-fill CORE without a
padframe, I/O pads, primary or secondary ESD, or a workshop full-die wrapper.
