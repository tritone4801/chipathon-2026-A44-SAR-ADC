# A44 One-Hour Selected-Seed Plan for a 10-Sample Monte Carlo Mismatch and Qualified Temporal-Noise 64-Frame Dynamic Simulation (Version 10)

**Document ID:** `A44_CODEX_FAST64_D3_MC10_ONE_HOUR_PLAN_V10`  
**Plan status:** `READY_FOR_EXECUTION_NOT_RUN`  
**Purpose:** 在当前主机和 Chipathon login 环境中，以 200 样本蒙特卡洛失配仿真中固定选择的
10 个 seed 完成 1 小时以内的蒙特卡洛失配与合格时域噪声组合类别的 64 帧动态仿真双频带快速回归。
**This is not:** 200 样本蒙特卡洛失配仿真良率估计、生产良率声明、动态 signoff 或完整角落覆盖。

## 1. 固定 10 样本蒙特卡洛失配仿真

```text
1,21,44,48,64,115,129,166,170,183
```

```text
selected seeds             = 10
bands per seed             = 2
required FAST64 records    = 20
frames per record          = 64
required valid frames      = 1280
workers                    = 4
maximum ngspice processes  = 4
```

不设置可选追加 seed。

## 2. Seed 选择

| Seed | 角色 | 冻结最差频带 | 冻结最差 SNDR (dB) | LOW 状态 | NEAR 状态 |
|---:|---|---|---:|---|---|
| 1 | 资格锚点 S1 | NEAR_NYQUIST | 32.293807 | VALID_PASS | VALID_FAIL |
| 21 | WORST_BAND SNDR P1 | LOW | 31.871876 | VALID_FAIL | VALID_FAIL |
| 44 | 资格锚点 S44 | LOW | 41.065067 | VALID_FAIL | VALID_FAIL |
| 48 | WORST_BAND SNDR P50 | LOW | 47.512930 | VALID_PASS | VALID_PASS |
| 64 | 46.91 dB 阈值下方，NEAR 侧 | NEAR_NYQUIST | 46.898212 | VALID_PASS | VALID_FAIL |
| 115 | 46.91 dB 阈值上方，NEAR 侧 | NEAR_NYQUIST | 46.982259 | VALID_PASS | VALID_PASS |
| 129 | WORST_BAND SNDR P5 | LOW | 32.276029 | VALID_FAIL | VALID_FAIL |
| 166 | 46.91 dB 阈值下方，LOW 侧 | LOW | 46.894125 | VALID_FAIL | VALID_PASS |
| 170 | 46.91 dB 阈值上方，LOW 侧 | LOW | 46.931189 | VALID_PASS | VALID_PASS |
| 183 | WORST_BAND SNDR P10 | NEAR_NYQUIST | 44.250496 | VALID_PASS | VALID_FAIL |

相对 8 样本蒙特卡洛失配仿真，新增：

```text
seed 115 = NEAR_NYQUIST threshold-above sample
seed 166 = LOW threshold-below sample
```

因此 LOW 和 NEAR_NYQUIST 均具备 46.91 dB 阈值上下的配对样本，同时保留
P1、P5、P10、P50 和两个资格锚点。P25 seed 140 和 P75 seed 25 仍不执行。

## 3. 冻结仿真定义

```text
category             = D3_NOISE_PLUS_MISMATCH_MC200
PVT                  = TT_3P3_27C
FFT method           = FAST64
bands                = LOW and NEAR_NYQUIST
frames per record    = 64
maxstep              = 50 ps
noise seed rule      = 100000 + mismatch seed
execution mode       = SEPARATE_PROCESS_FALLBACK
solver profile       = ROBUST_GEAR
interpreter          = /foss/tools/bin/python3
```

不得改变输入幅度、相干 bin、相位、噪声模型、比较器、CDAC、SAR TOP、采样
时刻或分析公式。生产 TOP/core 和
`/foss/designs/manual_goal/analog/SAR_CURRENT/` 保持只读。

## 4. 独立工作区

```text
/foss/designs/manual_goal/verification/A44_FAST64_D3_MC10_1H_V10/
```

V7、V8、8 样本蒙特卡洛失配仿真 V9 和 8 样本蒙特卡洛失配仿真 V9 exact 包保持只读。新目录开始时必须满足：

```text
no dynamic_master.csv
no dynamic_codes.csv
20 / 20 job rows are PENDING
no stale RUNNING state
```

## 5. 并行策略

1. 精确使用 4 个 seed worker。
2. 每个 worker 顺序执行一个 seed 的 LOW 和 NEAR_NYQUIST。
3. 同时最多存在 4 个 ngspice 进程。
4. 使用 Chipathon login 环境和 `/foss/tools/bin/python3`。
5. 不并行运行其他 ngspice campaign、raw replay 或重型绘图。
6. 不启动自动 retry。
7. 不追加第 11 个 seed。

## 6. 实测驱动的时间预算

8 样本蒙特卡洛失配仿真 exact 实测用于 8 个已有 seed；第 8 版 12 样本蒙特卡洛失配仿真实测用于新增 seed 115 和 166。

| Seed | 时间依据 | Worker | 双频带时间 (s) | 预计开始 (min) | 预计完成 (min) |
|---:|---|---:|---:|---:|---:|
| 1 | 8-sample Monte Carlo mismatch simulation exact | 1 | 743.013 | 0.000 | 12.384 |
| 21 | 8-sample Monte Carlo mismatch simulation exact | 2 | 900.289 | 0.000 | 15.005 |
| 44 | 8-sample Monte Carlo mismatch simulation exact | 3 | 749.628 | 0.000 | 12.494 |
| 48 | 8-sample Monte Carlo mismatch simulation exact | 4 | 967.506 | 0.000 | 16.125 |
| 64 | 8-sample Monte Carlo mismatch simulation exact | 1 | 610.285 | 12.384 | 22.555 |
| 115 | version 8 12-sample Monte Carlo mismatch simulation | 3 | 1053.528 | 12.494 | 30.053 |
| 129 | 8-sample Monte Carlo mismatch simulation exact | 2 | 550.381 | 15.005 | 24.178 |
| 166 | version 8 12-sample Monte Carlo mismatch simulation | 4 | 768.560 | 16.125 | 28.934 |
| 170 | 8-sample Monte Carlo mismatch simulation exact | 1 | 479.780 | 22.555 | 30.551 |
| 183 | 8-sample Monte Carlo mismatch simulation exact | 2 | 381.376 | 24.178 | 30.534 |

```text
measured worker-time sum          = 120.072 min
nominal four-worker wall          = 30.551 min
simulation with 25% margin        = 38.189 min
package, preflight and gate       = 3.000 min
comparison and three spectra      = 5.000 min
result consolidation and report  = 3.000 min
conservative total                = 49.189 min
one-hour reserve                  = 10.811 min
```

## 7. 一小时执行时序

| 总时钟 | 动作 | 门禁 |
|---|---|---|
| 0:00-0:03 | 建立独立包、预检、回归门禁自测 | 任一依赖版本不匹配立即停止 |
| 0:03-0:42 | 4 workers 执行 10 样本蒙特卡洛失配仿真 | 20 records；不追加 seed |
| 0:42-0:47 | 合并 CSV、严格比较、生成 P1/P5/P10 频谱 | 不做 raw replay |
| 0:47-0:50 | 最终状态、结果汇总 | 不扩展输出 |
| 0:50-1:00 | 截止缓冲 | 不再启动仿真 |

到 55 分钟仍未结束时，先核对 PID/PGID，再受控停止并保留退出记录，状态写为
incomplete，绝不改写为 PASS。

## 8. 执行命令

```bash
cd /foss/designs/manual_goal/verification/A44_FAST64_D3_MC10_1H_V10
PYTHONPATH=scripts /foss/tools/bin/python3 scripts/run_v7.py \
  --stage formal \
  --seeds "1,21,44,48,64,115,129,166,170,183" \
  --workers 4
```

V10 finalizer 必须使用显式 10 样本蒙特卡洛失配仿真 required-seed 列表和严格逐行 nested `all()`
门禁。

## 9. 必需输出

```text
csv/dynamic_master_mc10.csv
csv/dynamic_codes_mc10.csv
csv/selected_seed_comparison_mc10.csv
plots/P1:  seed 21  LOW
plots/P5:  seed 129 LOW
plots/P10: seed 183 NEAR_NYQUIST
results/regression_gate_self_test.json
results/quick_status.json
results/runtime_validation_timing.json
reports/FINAL_MC10_ONE_HOUR_REPORT.md
```

## 10. 验收门禁

### Gate A: Preflight

```text
frozen dependency versions match
qualification cache matches
production sources = 113 / 113
job matrix = 20 / 20 PENDING
selected maxstep = 50 ps
workers = 4
no competing ngspice process
strict regression-gate self-test = PASS
```

### Gate B: Execution

```text
20 / 20 records terminal and valid
1280 / 1280 frames valid
no timeout, clipping, missing frame or duplicate frame
Parseval passes for every record
input mismatch realizations and noise sequences match
```

### Gate C: Strict Regression

每条记录必须全部满足：

```text
state unchanged
hard-pass classification unchanged
mismatch realization unchanged
noise sequence unchanged
compact code stream unchanged
abs(delta SNDR) <= 0.10 dB
abs(delta SNR)  <= 0.20 dB
abs(delta ENOB) <= 0.02 bit
```

### Gate D: Outputs and Time

```text
three required spectra exist and are non-empty
all required outputs exist and are non-empty
end-to-end elapsed <= 3600 s
```

## 11. 状态规则

```text
PASS_SELECTED_SEED_QUICK_REGRESSION_MC10
FAIL_SELECTED_SEED_QUICK_REGRESSION_MC10
BLOCKED_SELECTED_SEED_QUICK_REGRESSION_INCOMPLETE
BLOCKED_STALE_QUALIFICATION_CACHE
BLOCKED_REGRESSION_GATE_IMPLEMENTATION
```

运行时间结果、执行完成情况和严格回归必须分别报告。即使 20/20 仿真按时完成，
只要比较超差，也必须记录 `execution_complete=true`、
`time_validation_pass=true`、`regression_pass=false`，不能声明性能 PASS。

## 12. 声明边界

```text
selected_seed_count = 10
mc200_yield_claim = false
production_yield_claim = false
dynamic_signoff_claim = false
```

该集合对尾部、阈值邻近和资格锚点有意识地过采样，适合快速回归，不可替代
200 样本蒙特卡洛失配仿真良率结果。
