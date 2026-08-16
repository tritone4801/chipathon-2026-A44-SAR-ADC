# A44 W5P29 当前原理图文件集

本目录是当前使用的 `A44_W5P29_UNIT_TRANS_DRIVER` 原理图基线在 GitHub
中的只读发布副本。目录形式与已有
`verification/a44_r2/01_CURRENT_CIRCUIT_FILES` 一致，旧包未删除、未覆盖。

## 内容

- `xschem/`：14 个 `.sch`、15 个 `.sym` 和 1 个沿用现有 GitHub 配置的
  `xschemrc`；
- `rtl/`：当前逐次逼近控制逻辑的 1 个 SystemVerilog 文件和 1 个 include；
- `spice/`：1 个顶层网表；
- `spice/subckts/`：12 个子电路、wrapper 或 include 文件；
- `indexes/A44_SIZING_LOCK.json`：当前 W5P29 尺寸锁；
- `indexes/CURRENT_FILE_INDEX.csv`：逐文件来源、包内位置、大小和 SHA-256；
- `audits/CURRENT_HIERARCHY_AUDIT.json`：本次发布范围与层级审计；
- `manifests/`：包内清单及独立回读结果。

45 个 W5P29 源文件均从
`D:\PICO\DESIGN_FILES\CURRENT\A44_W5P29_UNIT_TRANS_DRIVER\01_CIRCUIT_FILES`
精确复制；`xschemrc` 复用已有 GitHub schematic 包的配置。源基线未修改。

## 当前层级和电气绑定

活动顶层为 `xschem/A44_SAR_ADC_TOP_FIXED.sch`。固定时钟路径为
`CLKS -> A44_CLKS_BUFFER -> CLKS_CORE`，`CLKS_CORE` 同时驱动两个 TG8
采样器和逐次逼近控制逻辑。两个差分电容式数模转换器均使用 unit-based
层级和七路晶体管驱动器。

当前关键选择为：

- 比较器：CMP55_A，StrongARM 的 XM3/XM4 各为 W/L 55.8/0.28 微米、`m=4`；
- 电容阵列：C18，约 230.72 皮法/侧；
- 采样传输门：N 3.11/0.28 微米、P 6.22/0.28 微米，均为 `m=8`；
- 数据控制驱动器：INV1 N/P 2.34/4.67 微米，INV2 N/P 6.22/12.44 微米；
- 时钟缓冲器：C1，两级 N/P 为 0.78/1.56 和 3.11/6.22 微米；
- 逐次逼近逻辑：R1L slow-slow-corner true-transistor PEX core，通过按当前
  28 个逻辑引脚名映射的 wrapper 接入；旧 generic PEX/wrapper 仍保留为历史输入。

接口统一使用 bracket 命名：`DCTRLP[7:1]`、`DCTRLN[7:1]`、
`DOUT[7:0]`。源包审计记录为 22/22 条 logic-to-CDAC/TOP-output 文本连通；
这是一项结构闭合结论，不是模数转换器性能或版图签核。

## 仿真结果的缺失和变化

本次 GitHub 增量只发布当前原理图文件集，不复制新的仿真 deck、波形、日志
或批量结果。状态如下：

| 项目 | 状态 | 当前解释 |
| --- | --- | --- |
| `verification/a44_r2` 的 200 样本蒙特卡洛、三角工艺电压温度动态和完整静态结果 | 已保留，但电气基线不同 | 仍是 revision 2 历史证据，不能直接用于当前 W5P29 性能资格 |
| 较早 W5P29 三角、每角 20 样本动态结果 | 结果未随本包复制 | 60/60 终止；58/60 满足 hard-dynamic；56/60 满足信噪比预算；结论保持 `COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION` |
| 较早 W5P29 `FAST25 STATIC` 和 TT `MC100 OFFSET` | 已完成但未随本包复制，且电气绑定早于当前 UNIT+CLKS-buffer 基线 | `FAST25` 仅覆盖 38 个局部转移点/29 个局部 DNL；`MC100 OFFSET` 是整机 ADC 上升 T1 transfer offset，不是比较器 Vos；均不构成当前完整静态或良率结论 |
| 当前 UNIT 基线的完整 TT `MC100 OFFSET` | 输入已绑定，但执行未开始 | 状态为 `INPUT_BOUND_EXECUTION_NOT_STARTED`，不得沿用较早 MC100 人口统计 |
| 当前 UNIT 基线的源 worst-five 重放 | 已完成但未随本包复制 | 只覆盖选定的 20 条记录，状态保持 `COMPLETE_AS_EXECUTED_SELECTED_WORST5_PERFORMANCE_FAIL_NO_PROMOTION`，不是完整 MC20/MC100 或良率证据 |
| 加入 CLKS buffer 后的两个历史最差坐标重放 | 已完成但未随本包复制 | 两个锁定样本执行完整；只证明这两个坐标的重放，不构成新的 worst-case 搜索、总体性能或晋级依据 |
| W5P29 sizing-sync 的三角、每角 20 样本活动 | 部分执行后由用户停止，未随本包复制 | 不得报告完成率、良率、晋级或签核；停止快照存在写回滞后，计数不作为权威完成量 |
| 典型角历史结果复现诊断 | 方法结论已知，结果未随本包复制 | 旧电气输入可精确复现旧结果；当前 C18、TG8、CMP55 和时钟缓冲重绑定构成新的电气基线，解释了结果变化 |
| 当前 W5P29 的完整动态、静态、工艺电压温度和蒙特卡洛性能重验证 | 缺失/开放 | 本 schematic 包不声称这些项目已完成或通过 |

## 使用注意

Xschem 文件在 `xschem/` 内保持相互引用。SPICE 和 include 文件是源基线的
字节级副本，其中若干 `.include` 仍指向源环境中的绝对
`/foss/designs/DESIGN_FILES/CURRENT/A44_W5P29_UNIT_TRANS_DRIVER/...` 路径。
在 GitHub 副本内执行仿真前必须在工作副本或 deck 中完成路径重绑定；为保持
源哈希，本发布未改写这些文件。

GF180MCU 工艺设计套件模型未复制，仍需使用权威 PDK 安装。

## 声明边界

本包的 PASS 只表示文件范围、源到发布副本的精确复制、层级清单和哈希回读
通过。它不表示当前 W5P29 已通过完整动态/静态性能、工艺电压温度/蒙特卡洛
良率、版图、LVS、PEX、密度、EM/IR、pad/ESD、流片或硅后签核。R1L 仍为
未晋级的集成候选。
