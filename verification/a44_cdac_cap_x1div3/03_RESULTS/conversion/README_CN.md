# Unified-TOP PEX conversion 结果

本目录汇总既有 unified-TOP 波形与解析结果。结构化入口为
[`LAYERED_CONVERSION_STATUS.json`](LAYERED_CONVERSION_STATUS.json)。

## 结果摘要

| 场景 | Ideal | Schematic | PEX | 已记录状态 |
| --- | --- | --- | --- | --- |
| MIN2 | `[0, 1]` | `[0, 1]` | `[0, 0]` | `FAIL_FUNCTIONAL_CONVERSION`; `FAIL_FORMAL_MIN2` |
| MIN-MAX-MIN | `[0, 255, 0]` | `[0, 255, 0]` | `[0, 255, 0]` | `PASS_FUNCTIONAL_NOMINAL`; `WARN_INTERNAL_SETTLING_MARGIN` |
| 0x7F-0x80-0x7F | `[127, 128, 127]` | `[127, 128, 127]` | `[127, 128, 127]` | `PASS_FUNCTIONAL_NOMINAL`; `WARN_APERTURE_SENSITIVITY` |

## 主要观测

- MIN2 Frame 1 的前七次 comparator 结果在 schematic 与 PEX 中均为
  `N`；最终 D0 为 schematic `P -> 0x01`、PEX `N -> 0x00`。
- MIN2 最终 D0 在 CMPCK 10% 代理点的 residue 为 schematic
  `+0.719069 mV`、PEX `-27.832975 mV`。
- MIN-MAX-MIN 的 comparator 序列为
  `NNNNNNNN / PPPPPPPP / NNNNNNNN`。
- 0x7F-0x80-0x7F 的 comparator 序列为
  `NPPPPPPP / PNNNNNNN / NPPPPPPP`。

## 数据索引

- MIN2 正式报告：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/FINAL/README_CN.md`
- MIN2 最终 LSB 诊断：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/G5_PEX_1300NS/parsed/LAST_LSB_SCHEMATIC_PEX_DIAGNOSTIC_R1.json`
- MIN2 1%-preedge：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/G5_PEX_1300NS/parsed/G5_PEX_TT_3P3_27C_MIN2_180NS_1300NS.preedge_1pct_settling_R1.json`
- MIN-MAX-MIN 分析：`../04_UNIFIED_MINMAX/03_UNIFIED_PEX/parsed/G3_PEX_TT_3P3_27C_MIN_MAX_MIN_180NS_1800NS_R1.analysis.json`
- 0x7F-0x80-0x7F 分析：`../05_UNIFIED_MID/03_UNIFIED_PEX/parsed/G3_PEX_TT_3P3_27C_MID127_128_127_180NS_1800NS_R1.analysis.json`
