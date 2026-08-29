# 当前 R8/M6 CDAC acquisition time 与公共外框

## 结论

本轮正式 acquisition time 采用既有完成方法的同源复现：双向满量程长跟踪阶跃、`0.25 LSB = 3.3203125 mV` 的 enter-and-remain 判据，正式参考面为外部发生器 `GEN`。当前 CDAC layout 的 FULL-RC-CC PEX 相对匹配 schematic 确实引入 acquisition time 恶化：

| 输入条件 | Schematic / ns | 当前 layout PEX / ns | Layout 增量 / ns | Layout 增幅 |
|---|---:|---:|---:|---:|
| 无输入阻抗（理想 0 Ω） | 61.763312 | 76.550952 | 14.787640 | 23.942% |
| 既有 ESD+RC 输入模型 | 134.335424 | 151.832300 | 17.496876 | 13.025% |

因此，在相同激励和测量口径下，版图寄生造成的正式 GEN 面恶化为：无输入阻抗时 `+14.788 ns`，含既有 ESD+RC 时 `+17.497 ns`。外部输入网络本身的增量为 schematic `+72.572 ns`、PEX `+75.281 ns`。

## 当前 CDAC layout 的组分

- 二进制权重 `1/2/4/8/16/32/64` 的七组电容—开关支路，共 `127` 个 active CAP_SWITCH site。
- 每个 unit capacitor 为当前 cap×1/3 的 MIM 单元（schematic `m=6`）；加上一组接 GND 的 Cdummy，共 `128` 个逻辑 site、`768` 个物理 MIM-B primitive。
- 每个 active CAP_SWITCH 由一只连接 VREFN 的 NMOS 和一只连接 VREFP 的 PMOS 构成。
- 七通道 DCTRL conversion buffer / driver strip，每通道为两级反相器。
- 输入采样 transmission gate：NMOS 与 PMOS pass device（schematic `m=8`），以及产生 `N_CLK/P_CLK` 的本地 TG clock-driver chains。
- `VIN、CLKS、VTOP、DCTRL[7:1]、VREFP、VREFN、VDD、GND` 的 pin、参考/供电轨和互连；E/W 两个版本仅镜像侧向集成接口。

当前完整提取每侧统计为 `768 MIM + 2337 NFET + 2337 PFET + 162 nets`。这些组分都包含在本轮 FULL-RC-CC PEX acquisition DUT 中。

## 输入模型与测量方法

- ESD+RC 模型 ID：`A44_SCHEM_ACQ_ESD_LUMPED_RC_GEN50_R1`。
- 每路外部串联电阻 `55 Ω`，每路对地电容 `1.5 pF`，差分电容 `0.2 pF`。
- 主 ESD pad 采用 GF180 `asig_5p0` 提取的 `RLE=0.1 Ω` acquisition 执行视图，并串接既有 3.3 V secondary ESD wrapper。
- PEX DUT 是当前 R8/M6 的 E/W 两个 CDAC 单元，FULL-RC-CC，包含采样 TG、TG driver、DCTRL driver、开关阵列和 MIM 阵列。
- TT、3.3 V、27 °C；FS_UP 与 FS_DOWN；输入阶跃时刻 `20.1 ns`，CLKS 跟踪保持至约 `500.3 ns`，末端保留 `2 ns` guard。
- 不加载 comparator/scope，与先前已完成 acquisition 方法保持一致。

三个参考面的补充结果如下；最终正式比较仍使用 GEN 面：

| 视图与输入 | GEN / ns | PAD / ns | TG / ns |
|---|---:|---:|---:|
| Schematic，0 Ω | 61.763312 | 61.763312 | 61.763312 |
| PEX，0 Ω | 76.550952 | 76.550952 | 76.550952 |
| Schematic，ESD+RC | 134.335424 | 129.459884 | 116.311776 |
| PEX，ESD+RC | 151.832300 | 146.910932 | 134.457740 |

既有 schematic ESD+RC 正式值为 `134.342218 ns`；本轮同方法复现为 `134.335424 ns`，差值 `-0.006794 ns`（`-0.005057%`）。

## 最小收敛检查

仅对 nominal 最慢方向 `FS_UP` 的 `PEX + ESD+RC` 做三点 maxstep 检查：

| maxstep / ns | GEN / ns | PAD / ns | TG / ns |
|---:|---:|---:|---:|
| 0.125 | 151.836351 | 146.914802 | 134.461287 |
| 0.25 | 151.832300 | 146.910932 | 134.457740 |
| 0.5 | 151.816528 | 146.895423 | 134.443572 |

状态：`PASS_3_POINT_MAXSTEP_SPAN_LE_MAX_1NS_OR_1PCT`。GEN 三点跨度为 `0.019823 ns`（相对 0.25 ns 结果 `0.013056%`）。

## 公共外框

- E 实际 GDS bbox：`[0.1, 0.0, 390.0, 399.7] µm`。
- W 实际 GDS bbox：`[0.0, 0.0, 389.9, 399.7] µm`。
- E/W 联合实际 bbox：`[0.0, 0.0, 390.0, 399.7] µm`。
- 建议公共外框：`[0, 0, 390, 400] µm`，即 `390 × 400 µm`，面积 `156000 µm² = 0.156 mm²`。

该外框是在 1 µm 集成网格上对实际 E/W 几何联合范围向外取整。它不移动版图、不裁切边缘 pin/metal，也不等同于顶层 abutment clearance 或 sign-off。

## 结果边界

本结果只表征 TT/3.3 V/27 °C 下当前 CDAC schematic 与 FULL-RC-CC PEX 的 acquisition；不包含噪声、失配、PVT、comparator/scope 负载、完整 ADC 动态性能或顶层签核。早期 105 Ω proxy、TG-reopen 探索和未完成 raw-pad ngspice 工况均不进入正式数值。按用户要求未生成 SHA256 manifest，只保留数值、完成性、收敛和几何包围检查。
