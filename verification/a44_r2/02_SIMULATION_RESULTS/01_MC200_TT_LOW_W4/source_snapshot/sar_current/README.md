# SAR_CURRENT

本目录汇总当前 ACTUAL SAR ADC 仿真与验证所绑定的工程文件。主入口是
`SAR_ADC_TOP_FIXED.sch`，对应的可复用 TOP symbol 是
`A44_SAR_ADC_TOP_FIXED.sym`。

## 当前层级

```text
SAR_ADC_TOP_FIXED.sch
|-- A44_CDAC.sym x2 -> CDAC
|   `-- A44_SWITCH_BOOT_SP.sym -> SWITCH_BOOT_SP
|-- A44_Comparator_StrongARM.sym -> Comparator_StrongARM
`-- A44_SAR_LOGIC_ACTUAL_RTL_REPAIR.sym
    `-- current accepted SAR logic RTL/PEX wrapper and core
```

以下内容不在本包的 active hierarchy 中：comparator resize candidates、V2
debug candidates、ideal comparator、ideal CDAC、legacy SAR logic stub，以及
任何临时 sizing 版本。

## 目录说明

- 根目录的 `.sch`/`.sym`：可直接用 Xschem 打开的自包含工程副本。
- `project_templates/`：组装脚本采用的五个 `A44_` symbol 模板。
- `verification/`：每个 symbol 的直线接线测试图。
- `logic/`：当前 accepted SAR logic RTL、PEX wrapper 与 PEX core。
- `netlists/accepted/`：完成的 measurement campaign 所用 netlist include 闭包；
  include 根路径已重定位到本目录。
- `source_snapshot/authoritative/`：未经改写的原始工程文件副本。
- `reports/images/`：接口和 symbol 的 Xschem 截图。
- `verification/A44_SYMBOL_NAME_CHECK.sch`：五个项目 symbol 的统一命名展示图。

## Symbol 命名

五个项目自有 symbol 的文件名、`symname` 和图中可见名称统一使用 `A44_`
前缀：

```text
A44_SAR_ADC_TOP_FIXED.sym
A44_SAR_LOGIC_ACTUAL_RTL_REPAIR.sym
A44_CDAC.sym
A44_Comparator_StrongARM.sym
A44_SWITCH_BOOT_SP.sym
```

标准 Xschem/PDK symbols 不改名；`source_snapshot/` 中的权威原件保留上游原名。
`A44_` 只属于 symbol 工程命名，网表中的 `SAR_ADC_TOP_FIXED`、`CDAC`、
`Comparator_StrongARM`、`SWITCH_BOOT_SP` 和 `SAR_LOGIC_ACTUAL_RTL` 电气名称不变。

## 在容器中打开

```bash
cd /foss/designs/manual_goal/analog/SAR_CURRENT
xschem SAR_ADC_TOP_FIXED.sch
```

检查修正后的 symbol 与直线接口：

```bash
cd /foss/designs/manual_goal/analog/SAR_CURRENT
xschem verification/SAR_LOGIC_SYMBOL_STRAIGHT_WIRE_CHECK.sch
xschem verification/SAR_ADC_TOP_SYMBOL_STRAIGHT_WIRE_CHECK.sch
```

生成批处理 netlist：

```bash
cd /foss/designs/manual_goal/analog/SAR_CURRENT
bash scripts/verify_xschem.sh
```

用 ngspice 解析 accepted netlist 闭包：

```bash
cd /foss/designs/manual_goal/analog/SAR_CURRENT
ngspice -b -o generated/ngspice_parse.log scripts/verify_ngspice_parse.cir
```

## 边界

根目录 TOP 与 CDAC schematic 仅把原来的 workspace symbol 路径改成了本包内
相对路径，电气连接和器件参数未改。原始文件保存在
`source_snapshot/authoritative/`。

本包的两个 TOP/logic 可复用 symbol 做了显示几何修正：所有 pin box 中心都在 Xschem
20-unit 网格上，并增加了从 pin box 到 symbol 边框的正交直线。该修正不改变
`SAR_ADC_TOP_FIXED` 的冻结端口顺序，也不改变 `SAR_LOGIC_ACTUAL_RTL` 的显式
flattened subcircuit 实例顺序。修正前副本保存在
`source_snapshot/project_before_symbol_repair_20260717/`。

增加 `A44_` 前缀之前的项目副本保存在
`source_snapshot/project_before_a44_prefix_20260717/`。

本包提供当前源文件集合和可由 Xschem 解析的 symbol/netlist，
不新增模拟性能、版图后仿或 signoff 结论。当前 analog TOP/CDAC/
switch/comparator 是 schematic-level 源文件集合；SAR logic 使用当前 accepted SAR logic
RTL/PEX wrapper/core。

特别说明：SAR logic 当前没有 transistor-level Xschem schematic。TOP 的
Xschem smoke netlist 因而只用于检查图纸与 symbol 解析；实际 DUT 逻辑来源
由 `netlists/accepted/core/subckts/` 下的 SAR logic RTL/PEX wrapper/core 提供。
