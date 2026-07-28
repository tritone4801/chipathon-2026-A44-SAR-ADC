# 文件结构与地址

包根目录：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2`

## 1. 当前电路

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\01_CURRENT_CIRCUIT_FILES`

该目录仅保存当前 resizing 后确认的电路版本，包括 `.sch`、`.sym`、电气 SPICE 子电路、RTL 与必要配置。详细逐文件记录见：

`04_PACKAGE_DOCS\CURRENT_CIRCUIT_FILE_INDEX.csv`

## 2. 所有仿真结果

统一结果根目录：

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\02_SIMULATION_RESULTS`

其下包括：

- `01_MC200_TT_LOW_W4`：TT LOW/W4 MC200 完整结果。
- `02_PVT3_MC20_LOW_W4`：TT/SS/FF selected MC20 诊断结果。
- `03_FULL255_STATIC`：6 条唯一 FULL255 静态曲线。
- `04_CROSS_CAMPAIGN_SUMMARY`：跨 campaign 汇总。
- `05_CACE_GENERATED`：CACE 生成 netlist 与报告。
- `06_RUN_OUTPUTS`：preflight、quick verify、full staging 和保留的调试证据。

详细逐文件记录见：

`04_PACKAGE_DOCS\SIMULATION_RESULTS_INDEX.csv`

## 3. CACE 与仿真工具

`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\03_CACE_AND_SIMULATION_TOOLS`

- `CACE`：CACE YAML、模板和 Xschem preflight 源文件。
- `PDK`：本包电气绑定使用的 GF180 ngspice 文件快照。
- `scripts`：快速验证、完整矩阵 staging、CACE preflight 和包审计脚本。
- `Makefile`：工具目录内部的统一命令入口。

详细逐文件记录见：

`04_PACKAGE_DOCS\CACE_AND_TOOLS_INDEX.csv`

## 4. 文档与审计

- 文档：`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\04_PACKAGE_DOCS`
- 审计：`D:\PICO\A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R2\05_PACKAGE_AUDIT`

`05_PACKAGE_AUDIT\package_manifest_sha256.csv` 给出包内文件的相对路径、大小和 SHA-256。

