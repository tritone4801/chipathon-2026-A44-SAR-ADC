# unified TOP PEX conversion 分层判断 R2

当前总体状态：`FAIL_FORMAL_MIN2`。

本目录是对包内既有波形和解析结果的判断更新，不替换 `03_UNIFIED_MIN2`、`04_UNIFIED_MINMAX`、`05_UNIFIED_MID`、`06_OTHER_POINTS` 或 `07_SETTLING_DIAG` 中已经保存的原始结果。旧 parser 的复合状态继续作为历史输出保留；当前包级结论以本目录和 `LAYERED_CONVERSION_STATUS.json` 为准。

## 判据分层

1. `INTERNAL_SETTLING_MARGIN_GATE`：保留 `0.25 LSB = 3.3203125 mV,diff` 的 enter-and-remain 判据，但它只衡量模拟节点相对本地平台的稳定余量，不等价于 comparator 判决是否正确。
2. `BIT_DECISION_FUNCTIONAL_MARGIN_GATE`：按预期判决符号 `s_k` 计算 `M_k = s_k × r_k(actual)`；nominal pass 要求在 comparator 实际 aperture 有 `M_k > 0`。
3. `ROBUST_DECISION_MARGIN_GATE`：要求 `M_k` 大于已经绑定的 offset、noise、PVT/model 与未包含的 kickback uncertainty。当前包没有冻结该统一 uncertainty bound，因此除已出现负 nominal margin 的正式失败点外，不报告 robust PASS。
4. `END_TO_END_ADC_GATE`：需要额外的静态线性、动态、PVT 与 MC 证据；当前 conversion 点不构成该 gate。

当前波形没有 StrongARM tail-current onset 观察量。以下 `CMPCK 10% crossing` 仅作为 aperture 代理诊断；旧 `50% crossing 前 50 ps` 结果继续保留，但不再单独承担功能 PASS/FAIL 结论。

按照实际 SAR 事务顺序，settling 表中的 `bit7` 行表示 **D7 更新到下一次 D6 判决** 的余量，`bit6` 行表示 D6 更新到 D5 判决，以此类推；`bit1` 行对应 D1 更新到最终 D0 判决。

## 当前分层结果

| 场景 | 数值/协议结构 | nominal 功能 | 内部 settling 裕量 | signed-margin / aperture | 当前判断 |
|---|---|---|---|---|---|
| MIN2 | 数值完成；两帧协议结构完成 | Frame 1 PEX `0x00`，ideal/schematic `0x01` | 50% 与 1%-preedge 均为 `8/14` | 最终 D0 在 CMPCK 10% 的 `M=-27.832975 mV` | `FAIL_FUNCTIONAL_CONVERSION`、`FAIL_FORMAL_MIN2` |
| MIN→MAX→MIN | 完成并通过 | `[0,255,0]` 三方一致 | 旧 50% 与 1%-preedge 均为 `12/21` | 24 次 10% 代理判决均为正确符号，最小 `+40.158328 mV` | `PASS_FUNCTIONAL_NOMINAL` + `WARN_INTERNAL_SETTLING_MARGIN` |
| 0x7F→0x80→0x7F | 完成并通过 | `[127,128,127]` 三方一致 | 旧 50% 为 `18/21`；本次只读 1%-preedge 诊断为 `13/21` | Frame 0/2 的 D6 在 10% 代理点为 `-17.410136/-18.333651 mV` | `PASS_FUNCTIONAL_NOMINAL` + `WARN_APERTURE_SENSITIVITY` |

## MIN2：真实功能失败，而非 settling 误命名

MIN2 Frame 1 的前七次 comparator 结果在 schematic 与 PEX 中均为 `N`；最终 D0 才出现分歧：schematic 为 `P -> 0x01`，PEX 为 `N -> 0x00`。

| View | D0 residue @ CMPCK 1% | @ 10% | @ 50% |
|---|---:|---:|---:|
| matching schematic | `+0.717089 mV` | `+0.719069 mV` | `+0.340552 mV` |
| unified PEX | `-27.932464 mV` | `-27.832975 mV` | `-27.685374 mV` |

PEX 从 1% 到 50% 均处于错误符号一侧，所以该最终 LSB 错误不能归因于只在 50% review point 混入的 kickback。10% 代理点的 schematic-to-PEX 位移约为 `-28.552044 mV`，约 `-2.15 LSB,diff`；这是定位证据，不是某个晶体管或金属段的根因证明。

同一 Frame 1 的 `bit1` settling 行却通过：其 1%-preedge 本地平台为 `-28.048130 mV`，相对该平台的残差仅 `0.098775 mV < 3.3203125 mV`。这说明节点已经稳定，但稳定在错误判决一侧。因此当前数据同时证明：

- D7/D6/D5 settling FAIL 后，下一次 D6/D5/D4 判决仍可正确，故内部门不是 nominal 功能正确的必要条件。
- D1→D0 settling PASS 后，最终 D0 仍可错误，故内部门也不是功能正确的充分条件。

## 其他 conversion 点

### MIN→MAX→MIN

三个帧的 comparator 序列分别为 `NNNNNNNN / PPPPPPPP / NNNNNNNN`，DOUT、EOC 原子更新与尾部物理保持均正确。内部 bit7–bit5 裕量不足仍保留为模拟 margin 告警，但不能命名为该六个测试帧的功能失败。当前正确分类是：

```text
PASS_FUNCTIONAL_NOMINAL
WARN_INTERNAL_SETTLING_MARGIN
ROBUST_DECISION_MARGIN_NOT_YET_PROVEN
```

### 0x7F→0x80→0x7F

三个 comparator 序列为 `NPPPPPPP / PNNNNNNN / NPPPPPPP`，最终代码正确。但 Frame 0/2 的 D7 更新后，D6 residue 在 CMPCK 10% 仍位于预期 `P` 的反侧；它们分别在 CMPCK 达到约 `17.354% / 17.731% VDD` 时才越过零点，之后 comparator 解析为 `P`。

因此这两个正确帧对 StrongARM 实际 aperture 敏感。它们是 nominal 功能 PASS，但不能升级为 signed-margin 或 robust-margin PASS；应在后续可观察 tail-current onset 时重新绑定 `r_k(actual)`。

## 当前结论边界

- 正式 MIN2 是当前 unified PEX conversion 的主导总体结论：`FAIL_FORMAL_MIN2`。
- MIN/MAX 与中码点是范围明确的 nominal PASS 补充证据，不覆盖 MIN2 的实际码字失败。
- 旧 `FAIL_G3_UNIFIED_PEX_MIN_MAX_MIN` 与 `FAIL_G3_UNIFIED_PEX_MID127_128_127` 作为复合 parser 输出保留，但其 `functional_pass` 字段混合了内部 settling gate；包级报告不再把它们直接翻译为功能失败。
- 现有证据不支持把 bit7 的全部残差归因于 LAYOUT；50% review point 可能混合 comparator kickback，而 1%-preedge 结果又显示部分高位确有 pre-evaluation 轨迹/settling 余量不足。
- 当前未建立 PVT、MC、静态线性、FFT 或系统级性能结论。

## 证据位置

- MIN2 正式报告：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/FINAL/README_CN.md`
- MIN2 最终 LSB 诊断：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/G5_PEX_1300NS/parsed/LAST_LSB_SCHEMATIC_PEX_DIAGNOSTIC_R1.json`
- MIN2 1%-preedge：`../03_UNIFIED_MIN2/04_FORMAL_MIN2/G5_PEX_1300NS/parsed/G5_PEX_TT_3P3_27C_MIN2_180NS_1300NS.preedge_1pct_settling_R1.json`
- MIN/MAX 原始分析：`../04_UNIFIED_MINMAX/03_UNIFIED_PEX/parsed/G3_PEX_TT_3P3_27C_MIN_MAX_MIN_180NS_1800NS_R1.analysis.json`
- 中码原始分析：`../05_UNIFIED_MID/03_UNIFIED_PEX/parsed/G3_PEX_TT_3P3_27C_MID127_128_127_180NS_1800NS_R1.analysis.json`
