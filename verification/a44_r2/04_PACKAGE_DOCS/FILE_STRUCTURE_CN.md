# 文件结构与地址

包根目录：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2`

## 1. 当前电路

`01_CURRENT_CIRCUIT_FILES` 保存当前调整尺寸后确认的电路版本，包括
Xschem 原理图和符号、电气 SPICE 子电路、寄存器传输级逻辑与必要配置。

逐文件记录位于 `04_PACKAGE_DOCS/CURRENT_CIRCUIT_FILE_INDEX.csv`。

## 2. 仿真结果

统一结果根目录为 `02_SIMULATION_RESULTS`，其中包括：

- 200 样本蒙特卡洛失配动态仿真：典型工艺角、3.3 伏、27 摄氏度、低差分输入区间，正式稳态统计窗口为第 4 至第 67 帧；
- 三工艺电压温度角动态仿真：每个工艺角选择 20 个蒙特卡洛失配样本，覆盖典型工艺角、慢速工艺角和快速工艺角；
- 完整 255 个码间转换静态传输曲线仿真：共 6 条唯一曲线；
- 跨仿真结果汇总；
- Circuit Automatic Characterization Engine 生成的网表与报告；
- 预运行、快速结果复现、完整矩阵准备和保留的调试输出。

逐文件记录位于 `04_PACKAGE_DOCS/SIMULATION_RESULTS_INDEX.csv`。

## 3. Circuit Automatic Characterization Engine 与仿真工具

`03_CACE_AND_SIMULATION_TOOLS` 包含：

- Circuit Automatic Characterization Engine 配置、模板和 Xschem 预运行源文件；
- 当前电气仿真使用的 GF180 ngspice 工艺文件；
- 快速结果复现、完整矩阵准备和预运行脚本；
- 统一命令入口 `Makefile`。

逐文件记录位于 `04_PACKAGE_DOCS/CACE_AND_TOOLS_INDEX.csv`。

## 4. 文档

方法、完成矩阵、性能指标、结果位置和运行说明位于
`04_PACKAGE_DOCS`。

