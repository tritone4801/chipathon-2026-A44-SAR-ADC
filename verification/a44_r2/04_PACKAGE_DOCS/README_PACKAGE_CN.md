# A44 逐次逼近型模数转换器当前电路与固定仿真复现包

本包把当前电路、仿真结果、运行工具和说明文档分开存放。

## 顶层目录

- `01_CURRENT_CIRCUIT_FILES`：当前调整尺寸后确定的电路文件，包含 Xschem 原理图和符号、SPICE 子电路、寄存器传输级逻辑和配置；
- `02_SIMULATION_RESULTS`：固定动态仿真、静态传输曲线、工艺电压温度角仿真、调试输出和结果复现输出；
- `03_CACE_AND_SIMULATION_TOOLS`：Circuit Automatic Characterization Engine 配置、Xschem 预运行、电气仿真所需工艺文件、仿真脚本和 Makefile；
- `04_PACKAGE_DOCS`：仿真方法、已完成矩阵、性能指标、路径索引和使用说明。

## 根目录一键入口

- `RUN_QUICK_VERIFY.bat` 和 `RUN_QUICK_VERIFY.ps1`：执行 Circuit Automatic Characterization Engine 预运行，并复现 130 条结果记录；
- `RUN_FULL_CAMPAIGN.bat` 和 `RUN_FULL_CAMPAIGN.ps1`：默认准备完整仿真矩阵；显式传入 `-Execute` 时启动全部仿真。

建议先运行：

```powershell
.\RUN_QUICK_VERIFY.ps1
```

快速结果复现包括：

- 200 样本蒙特卡洛失配动态仿真中的 25 条记录；
- 三工艺电压温度角动态仿真中的 75 条记录；
- 6 条完整 255 个码间转换静态传输曲线中的 30 条记录。

全部 130 条记录一致只表示结果可复现，不改变当前电气结论：所有规定仿真
已经执行，但完整性能要求未全部通过，设计不晋级。

