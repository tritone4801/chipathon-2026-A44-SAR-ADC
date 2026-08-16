# A44 200 样本蒙特卡洛失配仿真固定 50 ps 不可复现子集复现实验

本目录是本次固定条件复现实验的紧凑结果副本。完整可继续执行的工程包位于：

`C:\Users\15031\eda\designs\manual_goal\verification\A44_MC200_FIXED50PS_NONREPRO_SUBSET_RERUN_20260725_R1`

## 固定条件

- 目标集合：此前被标记为不一致或不可复现的 41 个 seed-band 记录
- 瞬态最大步长：50 ps
- 求解器配置：`ROBUST_GEAR`
- 每个记录：64 帧
- 并行度：4 个独立 ngspice 进程

## 当前状态

- 执行：`PASS_FIXED50_EXECUTION`
- 有效记录：41/41
- 输出码：2624/2624
- 后期 10 样本蒙特卡洛失配仿真可比唯一目标：8/8 整记录一致
- 早期 200 样本蒙特卡洛失配仿真与 V7 的 33 个 LOW 分歧：固定 50 ps 后落到早期侧 9 个、V7 侧 24 个
- R1 极低尾部目标帧：17/17 复现 R1 回放码，0/17 复现 V7 正式码

## 入口

- 中文报告：`reports/A44_MC200_FIXED50PS_NONREPRO_SUBSET_RERUN_REPORT_CN.md`
- 对照摘要：`comparisons/comparison_summary.json`
- 冻结目标：`config/fixed50_target_contract.csv`
- 主结果：`data/fixed50_target_master.csv`
- 逐帧输出：`data/fixed50_target_codes.csv`

## 声明边界

这是针对 41 个争议记录的定向复现实验，不是完整的 200-seed × 2-band 200 样本蒙特卡洛失配仿真重跑，不建立全量良率、动态性能尾部或 signoff 结论。
