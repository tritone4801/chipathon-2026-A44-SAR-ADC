# 一键运行与验证

## 前提

- Windows 已安装 Docker Desktop。
- 容器 `iic-osic-tools_a44_xvnc` 正在运行。
- 容器内可使用 CACE 2.9、Xschem、ngspice 和 Python。
- 包位于 `D:\PICO`，并通过容器映射为 `/foss/designs`。

## 快速验证

在包根目录运行：

```powershell
.\RUN_QUICK_VERIFY.ps1
```

或双击：

```text
RUN_QUICK_VERIFY.bat
```

该入口实际调用：

```text
make -C 03_CACE_AND_SIMULATION_TOOLS quick-verify
```

执行内容：

1. CACE 2.9 运行 Xschem → ngspice package preflight。
2. MC200 前 5 个 seed，正式 W4 retained 帧 4–8，共 25 条比较。
3. PVT3 每个 corner 前 5 个 job，正式 W4 retained 帧 4–8，共 75 条比较。
4. 6 条 FULL255 曲线各取前 5 个 transition，共 30 条比较。

合计 130/130 一致才通过。最近一次正式 R2 通过证据：

`02_SIMULATION_RESULTS\06_RUN_OUTPUTS\RUN_20260728T190259Z`

## 完整矩阵入口

先验证 staging，不调度正式仿真：

```powershell
.\RUN_FULL_CAMPAIGN.ps1
```

最近一次 staging 通过证据：

`02_SIMULATION_RESULTS\06_RUN_OUTPUTS\FULL_20260728T190527Z`

显式启动完整矩阵：

```powershell
.\RUN_FULL_CAMPAIGN.ps1 -Execute
```

全量运行会建立新的 `FULL_<UTC>` 独立输出目录，不覆盖冻结的历史结果。完整矩阵规模为 MC200 200 jobs、PVT3 selected MC20 共 60 jobs，以及 6 条 FULL255 static 曲线。

## 审计

重新生成索引和 SHA-256 审计：

```powershell
docker exec iic-osic-tools_a44_xvnc bash --noprofile --norc -lc "cd /foss/designs/A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2 && make -C 03_CACE_AND_SIMULATION_TOOLS audit"
```

结果写入 `05_PACKAGE_AUDIT`。完整性 PASS、快速复现 PASS 与性能 PASS 是三类不同结论；本包不改变源 campaign 的 `PERFORMANCE_FAIL_NO_PROMOTION` 边界。

