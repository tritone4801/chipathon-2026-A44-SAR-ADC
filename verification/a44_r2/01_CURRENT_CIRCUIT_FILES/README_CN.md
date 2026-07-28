# A44 SAR ADC 当前最新电路文件集

本目录只收录截至 2026-07-28 已确定的当前 SAR ADC 设计文件。原文件未修改；所有电路文件均按原字节复制到独立目录，并通过源文件/副本 SHA-256 比对。

## 内容

- `xschem/`：4 个 `.sch`、5 个 `.sym` 和 1 个 `xschemrc`
- `rtl/`：1 个当前规范 SAR logic RTL 文件
- `spice/`：1 个顶层网表和 5 个当前子电路网表
- `indexes/CURRENT_FILE_INDEX.csv`：17 个设计文件的角色、原地址、包内地址、大小和源/副本 SHA-256
- `audits/CURRENT_HIERARCHY_AUDIT.json`：层级、比较器 resizing 绑定与范围审计
- `manifests/package_manifest_sha256.csv`：整包文件清单和 SHA-256

设计文件共 17 个，合计 5,100,010 字节。

## 当前层级

顶层为 `SAR_ADC_TOP_FIXED`，已收录其当前 Xschem 原理图/符号和 SPICE 网表。顶层 SPICE 网表引用：

- `CDAC`
- `Comparator_StrongARM`
- `SAR_LOGIC_ACTUAL_RTL`

上述三个定义均已收录。`SWITCH_BOOT_SP` 作为当前已完成电路块，也保留其原理图、符号和 SPICE 子电路。

## 当前 resized StrongARM

当前比较器原理图、符号和正式仿真子电路来自已验证的 resized 版本：

- M3/M4：W = 3.51 um
- M5/M6：W = 8.2524 um
- M7/M11：W = 16.8587 um

比较器 Xschem 原理图包含的 15 个器件块与正式仿真网表一致，符号引脚顺序也与正式网表一致。正式仿真的电气绑定以本包 `spice/subckts/Comparator_StrongARM_extracted.subckt.spice` 为准。

## 使用注意

`spice/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_wrapper_local.spice` 为保持精确副本，仍保留原环境中的绝对 `.include`：

`/foss/designs/manual_goal/analog/SAR_CURRENT/netlists/accepted/core/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_core.spice`

实际从本目录运行仿真前，需要在工作副本或仿真 deck 中将该引用重绑定到：

`spice/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_core.spice`

本目录内的原始精确副本不作改写。

## 未收录内容

为满足“只包含当前已确定的最新文件”，本目录未收录：

- 旧比较器尺寸、历史快照及重复副本
- Monte Carlo、PVT、FAST/FULL STATIC 测试 deck 与结果
- 行为模型编译产物、运行日志、波形和临时文件
- PDK 模型等外部工艺依赖

## 声明边界

本包的 `COMPLETE` 表示当前文件筛选、复制和哈希审计完成，不等同于整机性能 PASS、PVT signoff 或 tapeout signoff。SAR logic 的收录晶体管级实现是已确定的 SS PEX 候选；不能据此扩展为全 PVT 或流片签核结论。
