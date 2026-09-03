# A44 SAR ADC layout and DEF integration views

This directory contains the DEF-aligned `A44_A` project-slot top, its embedded
SAR ADC CORE, and the five direct component layouts instantiated by that CORE.

The repository-root binding is:

```text
info.yaml -> lvs_config.json
TOP_LAYOUT = A44_A
LAYOUT_FILE = gds/A44_A.gds
```

The cap x1/3 R8/M6 CDAC component layouts and their DRC/LVS and PEX records are
available separately under
[`verification/a44_cdac_cap_x1div3`](../verification/a44_cdac_cap_x1div3).

## Official DEF geometry

| Item | Value |
| --- | --- |
| Top cell | `A44_A` |
| Origin | `(0, 0) um` |
| Width x height | `1110 x 1110 um` |
| Logical pins | 89 |
| Metal2 pin shapes | 127 |
| Pin sides | 85 west, 4 north |
| CORE child origin | `(55, 55) um`, R0 |

The final DEF preserves the official `PINS` section exactly. Each official pin
rectangle is covered by top-level Metal2 in the GDS and has a same-name label
at the rectangle center. The detailed comparison is in
[`verification/a44_def_alignment`](../verification/a44_def_alignment).

## Published layout names

All public filenames use the `A44_SAR_ADC_` prefix and omit revision suffixes.
GDS top-cell names remain unchanged so that hierarchy and existing integration
contracts are preserved.

| Role | Public filename stem | GDS top cell | Size (um) |
| --- | --- | --- | ---: |
| Project-slot top | `A44_A` | `A44_A` | 1110 x 1110 |
| CORE | `A44_SAR_ADC_CORE_1000` | `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR` | 1000 x 1000 |
| CDAC east | `A44_SAR_ADC_CDAC_E_390X399P7` | `A44_CDAC_UNIT_E_R8_M6` | 390 x 399.7 |
| CDAC west | `A44_SAR_ADC_CDAC_W_390X399P7` | `A44_CDAC_UNIT_W_R8_M6` | 390 x 399.7 |
| Comparator | `A44_SAR_ADC_COMPARATOR_168X100` | `A44_COMP_PEX_ECO1_SD_REQUIRED_G6_FULL_R9` | 168 x 100 |
| SAR logic | `A44_SAR_ADC_SAR_LOGIC_240X240` | `SAR_LOGIC_ACTUAL_RTL_SS` | 240 x 240 |
| Clock buffer | `A44_SAR_ADC_CLKS_BUFFER_120X60` | `A44_CLKS_BUFFER_R1` | 120 x 60 |

## Directory contents

- `../gds/A44_A.gds`: the project-slot GDS used by `lvs_config.json`.
- `../gds/A44_SAR_ADC_CORE_1000.gds`: the current C6/R8-M6 CORE GDS embedded by `A44_A`.
- `../gds/components/`: five current standalone component GDS files, each named with its actual bbox.
- `MODULE_NAMING_MAP.csv`, `NAMING_POLICY.json`, and `CURRENT_LAYOUT.json`: current public-name and repository-path bindings.
- `lef/A44_A.lef`: the current project-top abstract; older component abstracts are under `lef/legacy/pre_def_alignment/`.
- `def/A44_A.def` and `def/A44_SAR_ADC_SAR_LOGIC_240X240.def`: current project-top and SAR-logic DEF views.
- `mag/`: editable Magic view of the project-slot top.
- `images/`: current bbox-qualified layout images; older images are under `images/legacy/pre_def_alignment/`.
- `../gds/legacy/pre_def_alignment/`: the previously published CORE and component GDS files.
- `../docs/slides/`: the preserved earlier CORE layout-review presentation.

## Layout contents

The `A44_A` wrapper connects the fixed project-slot pin locations to the
embedded current CORE and retains the official pad-control interface names.
The previous public CORE and component files remain available only in the
versioned legacy directories listed above.
