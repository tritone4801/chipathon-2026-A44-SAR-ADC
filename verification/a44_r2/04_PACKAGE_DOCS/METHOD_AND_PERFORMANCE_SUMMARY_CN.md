# 固定仿真方法、已完成内容和性能指标

## 1. MC200 TT LOW/W4

- 方法：`FAST64_SS_W4`
- 条件：TT、3.3 V、27 °C、LOW band、50 ps maxstep
- 样本：mismatch seed 1–200；event-noise seed = 100000 + mismatch seed
- 每个 job：68 帧；帧 0–3 为 first-conversion/startup 诊断，正式 W4 统计窗口为帧 4–67，共 64 帧
- 完成度：200/200 records，exceptions = 0
- hard dynamic：197 PASS，3 FAIL
- 失败 seed：65、68、141
- SNDR Type-7 percentiles：P1 46.8729 dB、P5 47.2961 dB、P10 47.4636 dB、P50 48.4065 dB
- 边界：这是固定 TT LOW/W4 population；LOW-only 不能表述为双 band die-level yield。

结果地址：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\02_SIMULATION_RESULTS\01_MC200_TT_LOW_W4`

## 2. PVT3 selected MC20 LOW/W4

- 方法：与 MC200 相同的 FAST64 W4、50 ps、帧 4–67 正式窗口
- 样本：TT/SS/FF 各 selected MC20，共 60 records
- 完成度：60/60，formal manifest、protocol、Parseval、binding 和 returncode 审计均通过
- TT/3.3 V/27 °C：19/20 hard dynamic PASS，resized SNDR P50 = 48.4048 dB
- SS/3.0 V/125 °C：20/20 hard dynamic PASS，resized SNDR P50 = 48.3026 dB
- FF/3.6 V/-40 °C：20/20 hard dynamic PASS，resized SNDR P50 = 48.6010 dB
- 边界：MC20 是 selected diagnostic sample，不是 MC200，也不是良率、promotion 或 signoff 证据。

结果地址：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\02_SIMULATION_RESULTS\02_PVT3_MC20_LOW_W4`

## 3. FULL255 STATIC

每条曲线均完成 255 个 transition 的正式静态搜索。TT seed44 只计算一次，经精确方法/哈希核对后在“四 seed TT”和“seed44 PVT”两个视图中复用，因此共有 6 条唯一曲线。

| Case | PVT | Seed | max \|DNL\| (LSB) | max \|INL\| (LSB) | Missing | Reversal | 状态 |
|---|---|---:|---:|---:|---:|---:|---|
| S044_TT | TT/3.3 V/27 °C | 44 | 0.610351 | 0.686645 | 0 | 0 | PASS |
| S116_TT | TT/3.3 V/27 °C | 116 | 0.422577 | 0.358017 | 0 | 0 | PASS |
| S180_TT | TT/3.3 V/27 °C | 180 | 0.469508 | 0.451902 | 0 | 0 | PASS |
| S106_TT | TT/3.3 V/27 °C | 106 | 0.146719 | 0.093900 | 0 | 0 | PASS |
| S044_SS | SS/3.0 V/125 °C | 44 | 1.496350 | 1.572634 | 1 | 1 | FAIL |
| S044_FF | FF/3.6 V/-40 °C | 44 | 0.328772 | 0.416836 | 0 | 0 | PASS |

结果地址：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\02_SIMULATION_RESULTS\03_FULL255_STATIC`

## 4. CACE 与快速可复现性

- CACE 2.9 实际执行 Xschem → ngspice package preflight：PASS，`final_v = 1.250 V`，限制为 1.249–1.251 V。
- MC200 前 5 个 seed：正式 W4 retained 帧 4–8，25/25 一致。
- PVT3 每个 corner 前 5 个 job：正式 W4 retained 帧 4–8，75/75 一致。
- 6 条 FULL255：每条前 5 个 transition 的冻结 lower/upper bracket，30/30 一致。
- 合计：130/130 一致，状态 `PASS_QUICK_REPRODUCIBILITY_ALL_LANES`。
- 一致后动态帧 9–67和静态 transition 6–255均不调度，用于快速确认复现闭包。

正式通过证据：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\02_SIMULATION_RESULTS\06_RUN_OUTPUTS\RUN_20260728T190259Z`

## 5. 最终结论边界

所有规定矩阵已经执行完整，但性能并非全部通过：MC200 有 3 个 hard-dynamic fail，seed44 SS FULL STATIC 有 missing code、reversal、DNL 和 INL 失败。因此源 campaign 的最终状态保持：

`COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION`

文件完整、CACE 可执行和快速复现 PASS 不等于性能 PASS，也不构成 PEX、layout、silicon、production-yield、tapeout 或 signoff 结论。
