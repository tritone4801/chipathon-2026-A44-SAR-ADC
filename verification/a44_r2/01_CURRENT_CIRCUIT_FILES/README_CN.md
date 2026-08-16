# A44 逐次逼近型模数转换器当前电路文件集

本目录收录截至 2026-07-28 用于当前晶体管级电气仿真的设计文件。

## 内容

- `xschem/`：4 个 `.sch`、5 个 `.sym` 和 1 个 `xschemrc`；
- `rtl/`：1 个当前规范的逐次逼近控制逻辑寄存器传输级文件；
- `spice/`：1 个顶层网表和 5 个当前子电路网表；
- `indexes/CURRENT_FILE_INDEX.csv`：17 个设计文件的角色及包内地址。

设计文件共 17 个，合计 5,100,010 字节。

## 当前层级

顶层为 `SAR_ADC_TOP_FIXED`，包含其当前 Xschem 原理图、符号和 SPICE
网表。顶层 SPICE 网表引用：

- 电容式数模转换器 `CDAC`；
- StrongARM 比较器 `Comparator_StrongARM`；
- 逐次逼近控制逻辑 `SAR_LOGIC_ACTUAL_RTL`。

上述三个定义均已收录。自举采样开关 `SWITCH_BOOT_SP` 作为当前完成的
电路块，也保留其原理图、符号和 SPICE 子电路。

## 当前调整尺寸后的 StrongARM 比较器

当前比较器原理图、符号和正式仿真子电路采用以下晶体管尺寸：

- M3/M4：宽度 3.51 微米；
- M5/M6：宽度 8.2524 微米；
- M7/M11：宽度 16.8587 微米。

比较器 Xschem 原理图包含 15 个器件块。正式仿真的电气连接以
`spice/subckts/Comparator_StrongARM_extracted.subckt.spice` 为准。

## 使用注意

`spice/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_wrapper_local.spice` 保留了原
环境中的绝对 `.include`：

`/foss/designs/manual_goal/analog/SAR_CURRENT/netlists/accepted/core/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_core.spice`

从本目录运行仿真前，需要在工作副本或仿真输入文件中将该引用改为：

`spice/subckts/SAR_LOGIC_ACTUAL_RTL_SS_pex_core.spice`

## 未收录内容

本目录未收录：

- 旧比较器尺寸、历史快照及重复副本；
- 200 样本蒙特卡洛失配动态仿真、三工艺电压温度角动态仿真、快速动态
  仿真和完整静态传输曲线仿真的输入文件与结果；
- 行为模型编译产物、运行日志、波形和临时文件；
- 工艺设计套件模型等外部工艺依赖。

## 声明边界

本目录只表示当前电路文件已整理，不等同于整机性能通过、完整工艺电压
温度范围签核或流片签核。逐次逼近控制逻辑采用当前的慢速工艺角寄生提取
候选实现，不能据此扩展为完整工艺电压温度范围或流片结论。
