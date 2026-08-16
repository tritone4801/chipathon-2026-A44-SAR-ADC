# 一键运行与结果复现

## 前提

- Windows 已安装 Docker Desktop；
- 容器 `iic-osic-tools_a44_xvnc` 正在运行；
- 容器内可使用 Circuit Automatic Characterization Engine 2.9、Xschem、ngspice 和 Python；
- 包位于 `D:\PICO`，并通过容器映射为 `/foss/designs`。

## 快速结果复现

在包根目录运行：

```powershell
.\RUN_QUICK_VERIFY.ps1
```

或双击：

```text
RUN_QUICK_VERIFY.bat
```

该入口调用：

```text
make -C 03_CACE_AND_SIMULATION_TOOLS quick-verify
```

执行内容：

1. Circuit Automatic Characterization Engine 2.9 运行 Xschem 到 ngspice 的包预运行；
2. 从 200 样本蒙特卡洛失配动态仿真的前 5 个种子中，比较正式稳态窗口第 4 至第 8 帧，共 25 条记录；
3. 从三工艺电压温度角动态仿真的每个工艺角前 5 个作业中，比较正式稳态窗口第 4 至第 8 帧，共 75 条记录；
4. 从 6 条完整静态传输曲线中各比较前 5 个码间转换，共 30 条记录。

全部 130 条记录一致时，快速结果复现通过。最近一次正式结果位于
`02_SIMULATION_RESULTS/06_RUN_OUTPUTS/RUN_20260728T190259Z`。

## 完整仿真矩阵入口

先准备完整矩阵而不调度仿真：

```powershell
.\RUN_FULL_CAMPAIGN.ps1
```

最近一次准备输出位于
`02_SIMULATION_RESULTS/06_RUN_OUTPUTS/FULL_20260728T190527Z`。

显式启动完整矩阵：

```powershell
.\RUN_FULL_CAMPAIGN.ps1 -Execute
```

完整运行会建立新的 `FULL_<UTC>` 输出目录，不覆盖既有结果。矩阵包括
200 个典型工艺角蒙特卡洛失配动态仿真作业、三个工艺电压温度角下每角
20 个选定失配样本的 60 个动态仿真作业，以及 6 条完整 255 个码间转换
静态传输曲线。

