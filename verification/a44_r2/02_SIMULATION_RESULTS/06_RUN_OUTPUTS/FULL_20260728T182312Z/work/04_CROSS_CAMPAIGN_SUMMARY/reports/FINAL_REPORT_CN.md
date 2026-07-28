# 当前 comparator resizing：MC200 + PVT3 MC20 + FULL255 STATIC

## 结论

执行矩阵完整，所有分支均绑定同一 comparator SHA-256 `53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49`。
最终状态为 **COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION**：动态总体改善明显，但 seed44 在 SS
corner 的 FULL255 静态性能失败，因此不晋级、不作 signoff 声明。

## MC200 TT LOW / FAST64_SS_W4

- 完整记录：200/200；执行审计：PASS；异常作业：0。
- hard dynamic：197/200 PASS。
- 失败 seeds：65, 68, 141。
- SNDR P1/P5/P10/P50：46.8729 / 47.2961 /
  47.4636 / 48.4065 dB。
- 正式批次墙钟：77.29 分钟。

## Selected PVT3 MC20（诊断样本，不是 yield）

| Corner | Hard dynamic | SNR budget | Resized SNDR P50 (dB) | Paired SNDR ΔP50 (dB) |
|---|---:|---:|---:|---:|
| TT_3P3_27C | 19/20 | 18/20 | 48.4048 | +0.9217 |
| SS_3P0_125C | 20/20 | 19/20 | 48.3026 | -0.1346 |
| FF_3P6_M40C | 20/20 | 18/20 | 48.6010 | +4.7556 |

60/60 完成、frame0 60/60 PASS、PVT pairing PASS、最终 manifest PASS。
正式批次墙钟 22.01 分钟。

## FULL255 STATIC

| Case | PVT | Gate | max abs DNL (LSB) | max abs INL (LSB) | Missing | Reversal |
|---|---|---:|---:|---:|---:|---:|
| S044_TT | TT_3P3_27C | PASS | 0.6104 | 0.6866 | 0 | 0 |
| S116_TT | TT_3P3_27C | PASS | 0.4226 | 0.3580 | 0 | 0 |
| S180_TT | TT_3P3_27C | PASS | 0.4695 | 0.4519 | 0 | 0 |
| S106_TT | TT_3P3_27C | PASS | 0.1467 | 0.0939 | 0 | 0 |
| S044_SS | SS_3P0_125C | FAIL | 1.4963 | 1.5726 | 1 | 1 |
| S044_FF | FF_3P6_M40C | PASS | 0.3288 | 0.4168 | 0 | 0 |

共计算 6 条唯一曲线、1530 个 transition。seed44 TT 同时服务于“TT seeds”
与“seed44 PVT”的 TT 项，复用前已确认 candidate hash、seed、corner、2-frame、
50 ps 和 0.02 LSB bracket 方法完全相同。

## 声明边界

- MC200 才是固定 TT LOW/W4 population 结果。
- PVT3 MC20 是选定的诊断 seeds，不能外推生产 yield。
- FULL255 是确定性 seed/corner 静态曲线。
- seed44 SS 的 static FAIL 阻止 promotion。
- 不作 layout、PEX、silicon、production-yield、tapeout 或 signoff 声明。
