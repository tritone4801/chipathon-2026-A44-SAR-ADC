# A44 SAR ADC 当前电路与固定仿真复现包（R2）

本包把“当前已确定电路”“统一仿真结果”“CACE/仿真工具”“说明文档”和“审计证据”分开存放。包根目录只保留四个一键启动文件，原始 R1 包保持不变。

## 顶层目录

- `01_CURRENT_CIRCUIT_FILES`：当前 resizing 后确定的 SAR ADC 电路文件，包含 `.sch`、`.sym`、SPICE 子电路、RTL 和 Xschem 配置。
- `02_SIMULATION_RESULTS`：所有历史基线、CACE 生成结果、调试证据和本包复现运行结果。
- `03_CACE_AND_SIMULATION_TOOLS`：CACE 配置、Xschem preflight、电气绑定所需 PDK 快照、仿真脚本和 Makefile。
- `04_PACKAGE_DOCS`：固定方法、已完成矩阵、性能指标、路径索引和使用说明。
- `05_PACKAGE_AUDIT`：源文件复制审计、依赖闭包审计、根目录布局审计、SHA-256 清单和包状态。

## 根目录一键入口

- `RUN_QUICK_VERIFY.bat` / `RUN_QUICK_VERIFY.ps1`：执行 CACE preflight，并复现 130 条冻结比较记录。
- `RUN_FULL_CAMPAIGN.bat` / `RUN_FULL_CAMPAIGN.ps1`：默认执行全量运行的 staging dry-run；只有显式传入 `-Execute` 才启动完整矩阵。

建议先运行：

```powershell
.\RUN_QUICK_VERIFY.ps1
```

通过标准为 CACE PASS，MC200 25/25、PVT3 75/75、FULL255 static 30/30，总计 130/130 一致。该通过只证明包、方法与冻结比较记录可复现，不改变原 campaign 的性能结论：

`COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION`

