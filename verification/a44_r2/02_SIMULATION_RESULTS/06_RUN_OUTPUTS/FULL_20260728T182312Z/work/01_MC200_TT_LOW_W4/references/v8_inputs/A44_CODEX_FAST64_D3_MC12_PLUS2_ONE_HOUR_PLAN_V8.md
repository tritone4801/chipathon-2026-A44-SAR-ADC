# A44 FAST64 D3 MC12+2 One-Hour Selected-Seed Simulation Plan V8

**Document ID:** `A44_CODEX_FAST64_D3_MC12_PLUS2_ONE_HOUR_PLAN_V8`  
**Purpose:** 在当前主机上，用 MC200 中选定的少量 seed 完成 1 小时以内的 FAST64 D3 双频带快速回归。  
**Evidence class:** `FAST64_D3_SELECTED_SEED_QUICK_REGRESSION_MODEL_CONDITIONAL`  
**This is not:** 新的 MC200 良率估计、量产良率声明或动态 signoff。

## 1. Current measured basis

当前正式 V7 结果提供以下实测基线：

```text
formal records                 = 400 / 400
formal dies                    = 200 / 200
formal wall time               = 29635.083 s = 8.232 h
formal workers                 = 4
selected maxstep               = 50 ps
execution mode                 = SEPARATE_PROCESS_FALLBACK
record runtime median          = 281.54 s
record runtime P95             = 492.85 s
dual-band seed runtime median  = 566.90 s
dual-band seed runtime P95     = 907.60 s
```

资源观测表明，当前主机同时运行 4 个 ngspice 进程时，每个进程约有 8 个线程，24 个逻辑 CPU 已接近饱和。内存不是限制项，但把同机 worker 增加到 5 或 6 会造成 CPU oversubscription。因此本计划硬限制：

```text
maximum concurrent seed jobs = 4
maximum active ngspice processes = 4
```

不得依赖 `OMP_NUM_THREADS=1` 解除该限制；当前流程中它没有把 ngspice 实际线程数降到 1。

## 2. Frozen simulation definition

快速回归必须保持 V7 的以下条件不变：

```text
category             = D3_NOISE_PLUS_MISMATCH
PVT                  = TT_3P3_27C
FFT method           = FAST64
bands                = LOW and NEAR_NYQUIST
frames per record    = 64
maxstep              = 50 ps
noise seed rule      = 100000 + mismatch seed
execution mode       = separate ngspice process fallback
```

只允许减少 seed 数量。不得改变输入幅度、相干 bin、噪声模型、比较器/CDAC/TOP、采样时刻或分析公式来压缩时间。

## 3. Seed-selection method

这是一个结果知情的覆盖型集合，目的是快速发现回归，不用于无偏良率统计。

### 3.1 Mandatory core: MC12

| Seed | Selection role | Worst band | Baseline worst SNDR (dB) | LOW state | NEAR state | Historical dual-band runtime (s) |
|---:|---|---|---:|---|---|---:|
| 1 | qualification anchor S1 | NEAR_NYQUIST | 32.293807 | VALID_PASS | VALID_FAIL | 796.79 |
| 21 | WORST_BAND SNDR P1 | LOW | 31.871876 | VALID_FAIL | VALID_FAIL | 1053.38 |
| 25 | WORST_BAND SNDR P75 | NEAR_NYQUIST | 48.000299 | VALID_PASS | VALID_PASS | 456.82 |
| 44 | qualification anchor S44 | LOW | 41.065067 | VALID_FAIL | VALID_FAIL | 560.68 |
| 48 | WORST_BAND SNDR P50 | LOW | 47.512930 | VALID_PASS | VALID_PASS | 723.62 |
| 64 | nearest below 46.91 dB, NEAR side | NEAR_NYQUIST | 46.898212 | VALID_PASS | VALID_FAIL | 578.93 |
| 115 | nearest above 46.91 dB, NEAR side | NEAR_NYQUIST | 46.982259 | VALID_PASS | VALID_PASS | 505.58 |
| 129 | WORST_BAND SNDR P5 | LOW | 32.276029 | VALID_FAIL | VALID_FAIL | 493.02 |
| 140 | WORST_BAND SNDR P25 | LOW | 46.786467 | VALID_FAIL | VALID_PASS | 566.25 |
| 166 | nearest below 46.91 dB, LOW side | LOW | 46.894125 | VALID_FAIL | VALID_PASS | 644.21 |
| 170 | nearest above 46.91 dB, LOW side | LOW | 46.931189 | VALID_PASS | VALID_PASS | 774.63 |
| 183 | WORST_BAND SNDR P10 | NEAR_NYQUIST | 44.250496 | VALID_PASS | VALID_FAIL | 473.59 |

Mandatory seed expression:

```text
1,21,25,44,48,64,115,129,140,166,170,183
```

This gives:

```text
mandatory seeds             = 12
mandatory FAST64 records    = 24
historical worker-time sum  = 127.13 min
historical 4-worker wall    = 34.62 min
25% runtime-margin wall     = 43.27 min
```

### 3.2 Optional extension: +2 seeds

Only launch these seeds when the mandatory MC12 phase has completed by overall minute 42:

| Seed | Selection role | Worst band | Baseline worst SNDR (dB) | Historical dual-band runtime (s) |
|---:|---|---|---:|---:|
| 13 | WORST_BAND SNDR P99 | NEAR_NYQUIST | 48.699308 | 459.18 |
| 167 | WORST_BAND SNDR P90 | LOW | 48.304179 | 475.46 |

Optional seed expression:

```text
13,167
```

The optional pair historically requires about 7.9 minutes with two active seed jobs. If the MC12 completion time is later than minute 42, skip the optional pair and close the valid MC12 package.

## 4. Parallel-execution policy

1. Use exactly 4 workers for MC12.
2. A worker owns one seed and runs its LOW and NEAR_NYQUIST records sequentially.
3. Never run more than 4 seed jobs or 4 ngspice processes on this host.
4. Run the optional pair with 2 workers, not 4 placeholder workers.
5. Do not run plotting, full-waveform replay, final raw-file hashing, Docker image work or another ngspice campaign concurrently.
6. Do not launch automatic retries. A failed record is recorded as unresolved unless there is enough time for one controlled retry before minute 42.
7. If dependency or qualification-cache hashes do not match V7, stop with `BLOCKED_STALE_QUALIFICATION_CACHE`; do not spend the one-hour window rebuilding qualification.

## 5. Independent workspace

Do not modify or clear the completed MC200 V7 package. Create an independent package:

```text
/foss/designs/manual_goal/verification/A44_FAST64_D3_MC12_PLUS2_1H_V8/
```

Copy only the small frozen inputs, scripts, dependency manifests and qualified cache required by the runner. Do not copy the approximately 30 GB full-waveform audit data. The new package must begin with no `dynamic_master.csv`, no `dynamic_codes.csv` and no terminal job rows, otherwise resume logic will skip the selected seeds.

The quick package shall set:

```text
campaign id           = A44_FAST64_D3_MC12_PLUS2_1H_V8
required core seeds   = 12
optional seeds        = 2
MC200 yield claim     = false
production yield claim = false
```

## 6. One-hour execution schedule

| Overall time | Action | Admission rule |
|---|---|---|
| 0:00 to 0:05 | Preflight, package creation, dependency/cache hash check, process and disk check | Must finish by minute 5 |
| 0:05 to about 0:40 | Run mandatory MC12 with 4 workers | 24 records |
| up to 0:42 | Validate mandatory completeness and runtime | Optional admission deadline |
| 0:40 to 0:50 | Run seeds 13 and 167 with 2 workers, only if admitted | Otherwise skip |
| 0:50 to 0:57 | Merge CSV, compare with MC200 baseline, generate three selected spectra and quick audit | No raw replay |
| 0:57 to 1:00 | Write final status and compact manifest | No new simulation launch |

Budget for the mandatory path:

```text
preflight                         = 5.0 min
MC12 historical wall             = 34.6 min
MC12 wall with 25% margin        = 43.3 min
postprocess and compact audit     = 7.0 min
total conservative mandatory     = 55.3 min
```

## 7. Runner commands

All EDA execution must occur in the installed Chipathon container.

Mandatory MC12:

```bash
cd /foss/designs/manual_goal/verification/A44_FAST64_D3_MC12_PLUS2_1H_V8
PYTHONPATH=scripts python3 scripts/run_v7.py \
  --stage formal \
  --seeds "1,21,25,44,48,64,115,129,140,166,170,183" \
  --workers 4
```

Optional +2, only when the overall clock is no later than minute 42:

```bash
PYTHONPATH=scripts python3 scripts/run_v7.py \
  --stage formal \
  --seeds "13,167" \
  --workers 2
```

The V8 quick finalizer must use the explicit required-seed list. Do not run the existing V7 MC200 finalizer unchanged because it expects 200 dies and 400 records.

## 8. Required quick outputs

```text
csv/dynamic_master_mc12.csv
csv/dynamic_codes_mc12.csv
csv/selected_seed_comparison.csv
csv/representative_spectra_manifest.csv
plots/P1 spectrum: seed 21
plots/P5 spectrum: seed 129
plots/P10 spectrum: seed 183
results/quick_status.json
results/quick_audit.json
manifests/compact_manifest_sha256.csv
reports/FINAL_MC12_PLUS2_ONE_HOUR_REPORT.md
```

Do not generate six full-waveform raw replays or the 30 MC200 population plots in the one-hour path.

## 9. Acceptance gates

### Gate A: execution completeness

Mandatory PASS requires:

```text
24 / 24 mandatory records terminal and valid
64 / 64 frames per record
no timeout, clipping, missing frame or duplicate frame
Parseval check passes for every record
mismatch and noise-input checksums match the frozen manifests
```

If the optional pair was admitted, require `28 / 28` total records terminal and valid.

### Gate B: regression comparison

Compare every selected record with its frozen MC200 baseline:

```text
LOW/NEAR validity state unchanged
hard-pass classification unchanged
abs(delta SNDR) <= 0.10 dB
abs(delta SNR)  <= 0.20 dB
abs(delta ENOB) <= 0.02 bit
```

These are quick-regression tolerances, not new ADC performance specifications. Record compact-code checksum equality separately. A code-stream mismatch must be reported even when the metric tolerances pass.

### Gate C: status wording

Allowed final statuses:

```text
PASS_SELECTED_SEED_QUICK_REGRESSION_MC12
FAIL_SELECTED_SEED_QUICK_REGRESSION_MC12
BLOCKED_SELECTED_SEED_QUICK_REGRESSION_INCOMPLETE
BLOCKED_STALE_QUALIFICATION_CACHE
```

The report must state the number of executed seeds and whether the optional pair ran. It must not reuse `PASS_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95`.

## 10. Hard time protection

1. Do not launch optional work after minute 42.
2. Do not launch any new simulation after minute 50.
3. At minute 55, stop postprocessing expansion and retain only required outputs.
4. If simulation is still active near the deadline, verify PID and process group before a controlled `SIGTERM`; preserve raw exit evidence and mark the package incomplete.
5. Never rewrite an interrupted or partial run as PASS.

## 11. Final recommendation

Use MC12 as the guaranteed one-hour product and treat seeds 13 and 167 as opportunistic coverage. The seed set intentionally overrepresents tails, threshold-adjacent cases and known LOW/NEAR disagreements. It is therefore useful for regression sensitivity but statistically biased for yield estimation.
