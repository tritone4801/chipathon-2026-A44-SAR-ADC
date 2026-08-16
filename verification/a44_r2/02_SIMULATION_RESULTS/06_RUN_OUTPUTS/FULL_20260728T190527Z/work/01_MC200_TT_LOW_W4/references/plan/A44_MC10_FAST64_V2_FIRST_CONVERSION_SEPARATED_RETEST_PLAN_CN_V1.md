# A44 10 样本蒙特卡洛失配仿真第二版 64 帧动态仿真首次转换分离重测计划 V1

日期：2026-07-25  
计划状态：`PLANNED_NOT_EXECUTED`  
方法标识：`FAST64_V2_FIRST_CONVERSION_SEPARATED`  
正式稳态筛选标识：`FAST64_SS_W4`

## 1. 目标

本计划重测刚完成的“当前 200 样本蒙特卡洛失配仿真复现用 10 样本子集”，并将旧
`FAST64_STARTUP_INCLUSIVE_W0` 的一个混合结果拆成两个互不替代的结论：

1. first-conversion 功能、路径和数值稳定性；
2. warm-up 后连续 64 帧的稳态噪声和失真性能。

正式 10 样本蒙特卡洛失配仿真必须回答：

- frame 0 是否完成且在 480 ns aperture 前给出一致 DOUT；
- noise-OFF 时，frame 0 与同相位 warm frame 64 是否逐层一致；
- frames 4–67 是否形成完整、相干、可用的 64 点稳态频谱；
- 第 4 至第 67 帧稳态统计窗口是否已经达到与第 8 至第 71 帧稳态对照窗口相同的 canonical 64-code 稳态；
- 旧第 0 至第 63 帧启动期窗口指标与新第 4 至第 67 帧稳态统计窗口指标的差异是否由 first-conversion 污染造成；
- 当前 10 样本蒙特卡洛失配仿真中曾落入当前 200 样本蒙特卡洛失配仿真、V7、固定41或第三分支的结果，在修正
  方法下分别如何分类。

本任务只修正动态测量语义并重测；不修改电路尺寸、生产 TOP/core、版图或 PDK。

## 2. 冻结依据和版本边界

### 2.1 方法合同

方法合同来自用户提供的：

```text
FAST64 修正版：将 first-conversion 与稳态频谱彻底分离
```



执行建包时必须把原文复制到：

```text
references/method_contract/FAST64_V2_FIRST_CONVERSION_SEPARATED_CN.txt
```

并保存原路径和字节数。

### 2.2 主要旧结果

主重测对象固定为：

```text
C:\Users\15031\eda\designs\manual_goal\verification\
A44_MC10_CURRENT_MC200_REPRO_20260725_R1
```

该包：

- 包内文件：504 项；
- 正式首轮：20/20 记录、1280/1280 帧有效；
- 严格结果：12/20 与当前 200 样本蒙特卡洛失配仿真完全一致，8 条记录存在差异；
- 后续诊断：32/32 有效；
- 原方法：`FAST64_STARTUP_INCLUSIVE_W0`。

旧包保持只读，不重新聚合、不改名、不覆盖。

### 2.3 新工作包

建立独立同级包：

```text
D:\PICO\A44_MC10_FAST64_V2_SS_W4_RETEST_20260725_R1
```

容器路径：

```text
/foss/designs/A44_MC10_FAST64_V2_SS_W4_RETEST_20260725_R1
```

完成后正式复制到：

```text
C:\Users\15031\eda\designs\manual_goal\verification\
A44_MC10_FAST64_V2_SS_W4_RETEST_20260725_R1
```

所有输入从旧 10 样本蒙特卡洛失配仿真及其封存的当前 200 样本蒙特卡洛失配仿真来源中复制并重建输入集合；
不得改用已经漂移的 live `SAR_CURRENT` 树。

## 3. 修正后的冻结测量合同

| 参数 | 正式值 |
|---|---:|
| Fs | 2 MS/s |
| frame period | 500 ns |
| input | 3.0 Vpp,diff |
| LOW bin | 7 |
| NEAR_NYQUIST bin | 29 |
| window | rectangular |
| warm-up | 4 frames |
| total converted frames | 68 |
| first-conversion frame | 0 |
| startup diagnostic frames | 0–3 |
| FFT retained frames | 4–67 |
| NFFT | 64 |
| same-phase warm reference | 64 |
| DOUT aperture | 480 ns |
| formal maxstep | 0.05 ns |
| bulk maxstep | 0.10 ns，仅在重新资格化后可用 |
| ENOB | raw ENOB，不补偿输入 backoff |
| formal workers | 最多 4 |
| total ngspice threads | 不超过 16 |

正式稳态指标必须改名为：

```text
steady_state_snr_db
steady_state_sndr_db
steady_state_enob_raw
steady_state_sfdr_dbc
steady_state_thd_db
```

旧的 `sndr_db`、`enob` 只能出现在带
`FAST64_STARTUP_INCLUSIVE_W0` 前缀的历史参考列中。

## 4. 重测队列

### 4.1 主 10 样本蒙特卡洛失配仿真队列

保持刚完成 10 样本蒙特卡洛失配仿真的 10 个 mismatch seed 不变：

```text
1, 2, 3, 47, 53, 71, 74, 109, 110, 195
```

每个 seed 同时运行：

```text
LOW
NEAR_NYQUIST
```

因此主队列仍为 20 个 seed-band，禁止因方法修正替换 seed。

角色保持：

| Seed | 角色 |
|---:|---|
| 1、74 | 历史 full-waveform / formal 差异锚点 |
| 2、3 | 稳定控制 |
| 47、53、71、109、195 | 当前 200 样本蒙特卡洛失配仿真的极低尾部或分支差异 |
| 110 | 当前 200 样本蒙特卡洛失配仿真的 240 分支与固定41/V7的 224 分支 |

### 4.2 P1/P5/P10 历史桥接记录

以下记录不计入主 10 样本蒙特卡洛失配仿真 population，只用于方法迁移：

| 来源 | 角色 | Seed | Band |
|---|---|---:|---|
| 第 7 版 200 样本蒙特卡洛失配仿真 | P1 | 21 | LOW |
| 第 7 版 200 样本蒙特卡洛失配仿真 | P5 | 129 | LOW |
| 第 7 版 200 样本蒙特卡洛失配仿真 | P10 | 183 | NEAR_NYQUIST |
| current 200-sample Monte Carlo mismatch simulation | P5 | 19 | LOW |
| current 200-sample Monte Carlo mismatch simulation | P10 | 182 | LOW |

当前 200 样本蒙特卡洛失配仿真 P1 的 seed109 LOW 已包含在主 10 样本蒙特卡洛失配仿真，不重复计数。

桥接结果放在独立：

```text
csv/percentile_bridge_*
```

不得与主 10 样本蒙特卡洛失配仿真的 10-seed 统计混合。

### 4.3 第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口资格化队列

最低覆盖：

```text
nominal TT: LOW, NEAR
seed 44 mismatch-only: LOW, NEAR
seed 96 mismatch-only: LOW, NEAR
```

以上 6 个条件分别运行第 4 至第 67 帧稳态统计窗口和第 8 至第 71 帧稳态对照窗口。

若当前绑定中另有一个不同于 nominal 的 promoted candidate，则最低覆盖还必须追加：

```text
promoted candidate TT: LOW, NEAR
promoted candidate SS: NEAR
```

这 3 个条件同样分别运行第 4 至第 67 帧稳态统计窗口和第 8 至第 71 帧稳态对照窗口。若本次 10 样本蒙特卡洛失配仿真绑定中没有独立的 promoted
candidate，必须在资格化报告中写明
`NOT_APPLICABLE_NO_DISTINCT_PROMOTED_CANDIDATE`，并列出支持该结论的 DUT/netlist
绑定信息；不得把未检查静默解释为“不适用”。

若主队列任一记录出现 startup pair mismatch，再把对应 seed-band 加入第 8 至第 71 帧稳态对照窗口
触发队列，但不能删除原有第 4 至第 67 帧稳态统计窗口失败结果。

## 5. 两类正式仿真必须分开

### 5.1 mismatch-only / noise-OFF companion

主 10 样本蒙特卡洛失配仿真的 20 个 seed-band 全部运行一份 noise-OFF、strict 50 ps companion。

用途：

- first-conversion 协议检查；
- frame 0 与 frame 64 确定性同相位比较；
- frames 0–3 与 64–67 startup history 比较；
- comparator decision、DCTRL、digital/driver/analog DOUT 路径定位；
- mismatch-only steady-state 64-frame dynamic simulation；
- 排除 event-noise draw 对 first-conversion 判断的干扰。

### 5.2 event-noise / noise-ON 正式 10 样本蒙特卡洛失配仿真

使用原 10 样本蒙特卡洛失配仿真的 mismatch/noise seed 映射：

```text
noise_seed = 100000 + mismatch_seed
```

每个 seed-band 运行 68 帧，正式 FFT 只使用 frames 4–67。

noise-ON 的 frame 0：

- 必须通过 protocol、completion、DOUT path 和 aperture timing；
- 不要求 `code[0] == code[64]`；
- 不从单次 64 帧动态仿真推导 cold-start BER。

若以后需要 first-conversion 噪声错误概率，另建
`F0_NOISE_COLD_START_REPEAT`，不在本次 10 样本蒙特卡洛失配仿真内临时推断。

## 6. 执行阶段

### P0：独立建包和冻结

1. 建立新包，不复制旧 `jobs/`、缓存和派生 CSV；
2. 复制 accepted netlists、模型、timing、mismatch weights、noise 合同；
3. 保存旧 10 样本蒙特卡洛失配仿真、V7、固定41和当前 200 样本蒙特卡洛失配仿真的结构化参考；
4. 记录所有输入文件的来源与版本；
5. 记录 ngspice、PDK、Python、analyzer 版本；
6. 确认当前源文件、TOP pin order 和 behavioral logic `.so`；
7. 将所有正式 job 初始化为 `PENDING`。

P0 失败时不得生成任何新性能结论。

### P1：68/72-frame 实现和单元测试

新增独立 runner/analyzer，不直接改写旧 `run_v7.py`：

```text
scripts/run_fast64_v2.py
scripts/analyze_fast64_v2.py
```

必须通过：

- 68 帧索引严格为 0–67；
- retained 索引严格为 4–67，共 64 帧；
- 第 8 至第 71 帧稳态对照窗口 retained 索引为 8–71，共 64 帧；
- canonical phase index 为 `frame_index mod 64`；
- LOW/NEAR 均覆盖 64 个唯一 phase；
- FFT bin 仍为 7/29；
- 不允许 63 点 FFT、68点 FFT或非连续抽帧；
- noise draw 的 frames 0–63 prefix 在延长到68帧后保持不变；
- 旧第 0 至第 63 帧启动期窗口 replay 使用 frames 0–63；
- 新正式 SS_W4 使用 frames 4–67。

先运行 nominal 典型工艺角 LOW/NEAR smoke。smoke 不得复用为正式结果。

### P2：第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口资格化

对第4.3节的6个条件，在 noise-OFF、strict 50 ps 下分别运行：

```text
W4: total=68, retained=4–67
W8: total=72, retained=8–71
```

比较前按照 `frame_index mod 64` 排成相同 phase origin。

硬门禁：

```text
64/64 canonical codes exact
64/64 completion flags exact
0 missing / duplicate / invalid / timeout / clipping
```

全部通过：

```text
WARMUP4_QUALIFIED
```

任一失败：

```text
WARMUP4_NOT_QUALIFIED
STEADY_STATE_NOT_REACHED_OR_HISTORY_SENSITIVE
```

失败时停止主 10 样本蒙特卡洛失配仿真；不得把正式方法私自改成第 8 至第 71 帧稳态对照窗口后继续。

### P3：bulk/strict 数值资格化

复用 P2 的6个 strict 第 4 至第 67 帧稳态统计窗口结果，再增加相同条件的 bulk 100 ps 第 4 至第 67 帧稳态统计窗口结果。

分开生成：

```text
N1_F0
N1_SS
```

`N1_F0` 比较：

- frame 0 code；
- frames 0–3 protocol；
- comparator decisions；
- DCTRL trajectory；
- digital/driver/analog DOUT；
- completion time 和 aperture。

`N1_SS` 比较：

- phase-aligned frames 4–67；
- 64/64 code；
- completion flags；
- steady-state metrics。

即使 100 ps 的 `N1_SS_PASS`，本次正式 10 样本蒙特卡洛失配仿真仍固定使用 strict 50 ps；
100 ps 只形成以后 bulk 加速是否可用的资格化结果。

### P4：主队列 noise-OFF first-conversion companion

运行 10 seeds × 2 bands = 20 条 strict 第 4 至第 67 帧稳态统计窗口。

frame 0 硬门禁：

```text
decision_count = 8
update_count   = 7
COMPLETE       = 1
INVALID        = 0
TIMEOUT        = 0
clipping       = 0
DOUT 在 480 ns 前稳定
```

路径一致：

```text
comparator code
= DCTRL code
= digital DOUT
= driver DOUT
= analog DOUT
```

同相位确定性检查：

```text
frame 0 code == frame 64 code
frame 0 comparator decisions == frame 64 comparator decisions
```

并为 frame 0/64、1/65、2/66、3/67输出逐层差异。

分类：

```text
FIRST_CONVERSION_HISTORY_DIVERGENCE
FIRST_CONVERSION_NUMERICAL_DIVERGENCE
SAR_CAPTURE_OR_DOUT_COMMIT_DIVERGENCE
PASS_FIRST_CONVERSION_DETERMINISTIC
```

### P5：主队列 event-noise 64 帧稳态动态仿真，第 4 至第 67 帧为正式统计窗口

运行 20 条正式 event-noise 记录：

- strict maxstep 50 ps；
- 68 frames；
- frame 0 只作独立功能 Gate；
- frames 4–67 作正式 FFT；
- 最多 4 个 ngspice；
- 使用 12-core affinity，确保总线程不超过16；
- 记录过程数、线程数、RSS、返回码、timeout、abort。

每条结果同时保存三层视图：

1. `first_conversion`：frame 0；
2. `startup_diagnostic`：frames 0–3与64–67；
3. `steady_state`：frames 4–67。

### P6：P1/P5/P10 桥接

第4.2节的5条记录分别运行：

- strict 50 ps noise-OFF frames 4 through 67 steady-state analysis window；
- strict 50 ps event-noise frames 4 through 67 steady-state analysis window。

桥接表必须同时列出：

```text
historical_MC200_W0
historical_MC10_W0
fixed50_41_W0（若存在）
same_run_W0_replay
new_SS_W4
```

特别关注：

- seed129 LOW：V7 32.276029 dB分支与10 样本蒙特卡洛失配仿真/固定41 48.304910 dB分支；
- seed19 LOW：当前 200 样本蒙特卡洛失配仿真的实际P5 32.261188 dB分支；
- seed109 LOW：当前 200 样本蒙特卡洛失配仿真的实际P1 23.344590 dB分支。

桥接记录不参与主 10 样本蒙特卡洛失配仿真 pass rate 或候选排名。

### P7：同一68帧内的旧/新方法隔离

每条 event-noise 正式记录同时计算一个诊断性旧窗：

```text
W0 replay: frames 0–63
W4 formal: frames 4–67
```

必须输出：

```text
delta_snr_db
delta_sndr_db
delta_enob_raw
delta_sfdr_dbc
delta_thd_db
frame0_code
frame64_code
```

用途：

- 隔离“仅改变 FFT window”造成的性能变化；
- 判断原低 SNDR 是否由 frame 0 单点污染；
- 检查新68帧 runner的frames 0–63是否复现旧第 0 至第 63 帧启动期窗口 runner。

第 0 至第 63 帧启动期窗口 replay 只作诊断，禁止进入新 SS_W4 distribution 或 ranking。

## 7. FFT和性能门禁

正式 FFT 输入严格为：

```text
codes_all_68[4:68]
```

要求：

```text
64/64 valid
64/64 complete
0 invalid
0 timeout
0 clipping
0 missing
0 duplicate
DOUT stable at aperture
```

沿用现有动态阈值，但只作用于 `steady_state_*`：

```text
steady_state_sndr_db >= 46.91 dB
steady_state_enob_raw >= 7.50 bit
steady_state_snr_db >= 48.14 dB（SNR budget）
```

preferred 指标仍作为次级报告：

```text
steady_state_sndr_db >= 47.75 dB
steady_state_enob_raw >= 7.64 bit
```

first-conversion FAIL 时，即使 steady-state PASS，记录总体也必须 FAIL。

## 8. 结果状态

每条记录只允许以下最终状态：

```text
PASS_FAST64_COMPLETE
FAIL_FIRST_CONVERSION_ONLY
FAIL_FIRST_CONVERSION_NUMERICAL
FAIL_STEADY_STATE_DYNAMIC
FAIL_STEADY_STATE_NUMERICAL
FAIL_PROTOCOL_OR_COMPLETION
NOISE_RESULT_DIAGNOSTIC_ONLY
```

方法级状态：

```text
PASS_FAST64_V2_METHOD_QUALIFICATION
FAIL_WARMUP4_QUALIFICATION
FAIL_FAST64_V2_IMPLEMENTATION
```

执行级状态：

```text
PASS_MC10_FAST64_V2_EXECUTION
MC10_FAST64_V2_EXECUTION_INCOMPLETE
```

性能/复现状态必须与执行状态分开。旧第 0 至第 63 帧启动期窗口 200 样本蒙特卡洛失配仿真与新第 4 至第 67 帧稳态统计窗口 10 样本蒙特卡洛失配仿真不是同一测量语义，
因此不得输出“严格复现/不复现当前 200 样本蒙特卡洛失配仿真”的二元结论；只能输出：

```text
METHOD_TRANSITION_DIAGNOSTIC_COMPARISON
```

除非将对应当前 200 样本蒙特卡洛失配仿真全部按第二版 64 帧动态仿真重新测量。

## 9. 必需输出

主数据：

```text
csv/codes_all_68.csv
csv/codes_fft_retained_64.csv
csv/startup_periodic_pairs.csv
csv/first_conversion_path.csv
csv/steady_state_master_mc10.csv
csv/method_transition_comparison.csv
csv/percentile_bridge_master.csv
csv/percentile_bridge_comparison.csv
csv/resource_trace.csv
```

结果：

```text
results/first_conversion_status.json
results/fast64_steady_state_metrics.json
results/warmup_qualification.json
results/mc10_execution_status.json
STATUS.json
```

每条 master 至少记录：

```text
method_id
warmup_frames
total_frames
retained_frame_start
retained_frame_end
nfft
bin
fin_hz
phase_rad
aperture_ns
maxstep_ns
mismatch_seed
noise_seed
first_conversion_status
startup_pair_mismatch_count
warmup_qualified
n1_f0_status
n1_ss_status
steady_state_snr_db
steady_state_sndr_db
steady_state_enob_raw
steady_state_sfdr_dbc
steady_state_thd_db
overall_status
```

## 10. 绘图规范

旧/new图例必须明确区分：

```text
FAST64 startup-inclusive W0, frames 0–63
FAST64 steady-state W4, frames 4–67
```

必备图：

1. 10 seeds × 2 bands 的 first-conversion Gate矩阵；
2. 第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口 canonical-code差异矩阵；
3. 20条记录的第 0 至第 63 帧启动期窗口 replay vs 第 4 至第 67 帧稳态统计窗口 SNDR dumbbell图；
4. 所有曾出现首帧差异记录的 frame0/frame64 code及bit路径图；
5. seed19、21、109、129、182、183的历史/新方法桥接图；
6. LOW/NEAR steady-state SNDR、ENOB结果图；
7. first-conversion状态与steady-state状态的二维矩阵；
8. 代表频谱，使用离散 FFT bin stem+point、dBFS/bin、无floor clipping。

每幅正式图同时输出：

```text
矢量 PDF
300 dpi PNG
源 CSV
```

PDF经 Poppler 渲染并逐页目检。

## 11. 工作量和执行顺序

无条件最小作业量：

| 阶段 | 新作业数 |
|---|---:|
| 第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口 strict资格化 | 12 |
| 100 ps bulk补充资格化 | 6 |
| 主10 样本蒙特卡洛失配仿真 noise-OFF companion | 20 |
| 主10 样本蒙特卡洛失配仿真 event-noise正式记录 | 20 |
| P1/P5/P10桥接，noise-OFF＋noise-ON | 10 |
| 合计 | 68 |

smoke、失败重试和条件性第 8 至第 71 帧稳态对照窗口升级不计入68。

若存在第4.3节定义的独立 promoted candidate，则在68条基础上追加：

- 6 条 strict 50 ps 第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口资格化作业；
- 3 条 100 ps 第 4 至第 67 帧稳态统计窗口 bulk补充资格化作业；
- 条件性最小总量因此为77条。

运行时间只用于排程，不作为验收门。必须按 P0→P7顺序通过门禁，不允许因时间预算
跳过第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口、first-conversion companion或输出生成。

## 12. 完成门禁

计划完成要求：

1. 新包与旧包独立，旧包内容不变；
2. 方法合同和所有输入已版本绑定；
3. 第 4 至第 67 帧稳态统计窗口/第 8 至第 71 帧稳态对照窗口资格化通过；
4. bulk/strict得到独立N1_F0和N1_SS；
5. 主10 样本蒙特卡洛失配仿真 20条noise-OFF和20条noise-ON均完成；
6. first-conversion和steady-state结果完全分开；
7. 20条正式steady-state记录全部有64帧；
8. P1/P5/P10桥接完成但未混入主总体；
9. 资源轨迹满足4进程/16线程；
10. 图表、报告和 STATUS 均已生成；
11. 明确列出所有FAIL和非声明。

## 13. 非声明

本次重测不允许直接声明：

- 新 10 样本蒙特卡洛失配仿真等价于旧 startup-inclusive 200 样本蒙特卡洛失配仿真；
- 200 样本蒙特卡洛失配仿真 yield 或 production yield；
- resizing candidate 已晋级；
- 版图后仿真、硅片或一般性 signoff；
- warm-up 隐藏的 first-conversion失败可以忽略；
- 10 样本蒙特卡洛失配仿真或固定41的样本P5可以替代200-seed population P5。

最终交付必须分别陈述：

```text
方法资格化是否完成
执行是否完成
first-conversion是否通过
steady-state性能是否通过
旧/新方法诊断差异
哪些结论仍需FAST64 V2 MC200才能闭合
```
