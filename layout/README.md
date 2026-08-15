# A44 SAR ADC layout views

This directory accompanies the Chipathon 2026 layout-review submission for
Team A44. It contains the current no-pad, pre-fill CORE layout and the five
direct component layouts instantiated by that CORE.

The official dry-run binding remains:

```text
info.yaml -> lvs_config.json
TOP_LAYOUT = A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR
LAYOUT_FILE = gds/A44_SAR_ADC_CORE_1000.gds
```

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

## Scope boundary

This is a CORE layout-review publication without padframe, I/O pads, primary
or secondary ESD, or a workshop full-die wrapper. The CORE is the current
pre-fill baseline. The files are not a claim of density/fill closure,
full-chip signoff, Channel Partner acceptance, or tapeout readiness.

Per the requested repository scope, this layout publication adds no audit,
manifest, checksum, rehash, or standalone verification-result files.
