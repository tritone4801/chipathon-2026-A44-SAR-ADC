# CMP_XM5_XM6_W8P2524_XM7_XM11_W16P8587 三 PVT MC20 性能测量报告

- 完成状态：`COMPLETE_AS_EXECUTED`
- 执行：60/60，固定 50 ps，LOW/FAST64_SS_W4。
- frame 0 独立于 W4 FFT 汇报。
- MOS corner 为 typical/ss/ff，MIM 分别为 mimcap_typical/mimcap_ss/mimcap_ff。
- 数字逻辑保持固定 TT 时序，逻辑电平及 bridge threshold 随各 corner VDD 缩放。
- 与 `CMP_IN_A2P25_W_T1P000` 按相同 seed、corner、CDAC mismatch checksum、事件噪声 checksum 和 FAST64 方法逐条配对。

## 每个 corner 的结果

- `TT_3P3_27C`：hard dynamic 基线 14/20 → resize 19/20（FAIL→PASS 6，PASS→FAIL 1）；SNR budget 基线 10/20 → resize 18/20；SNDR 配对中位数 Δ=+0.922 dB；ENOB 配对中位数 Δ=+0.1531 bit；frame0 20/20。
- `SS_3P0_125C`：hard dynamic 基线 18/20 → resize 20/20（FAIL→PASS 2，PASS→FAIL 0）；SNR budget 基线 16/20 → resize 19/20；SNDR 配对中位数 Δ=-0.135 dB；ENOB 配对中位数 Δ=-0.0224 bit；frame0 20/20。
- `FF_3P6_M40C`：hard dynamic 基线 2/20 → resize 20/20（FAIL→PASS 18，PASS→FAIL 0）；SNR budget 基线 1/20 → resize 18/20；SNDR 配对中位数 Δ=+4.756 dB；ENOB 配对中位数 Δ=+0.7900 bit；frame0 20/20。

## 跨 PVT 结果

- TT 通过：19/20。
- TT 通过且在 SS、FF 均继续通过：19/19。
- 分类计数：`{"ALL_CORNER_PASS": 19, "PVT_INDUCED_REGRESSION": 0, "PERSISTENT_FAIL": 0, "CORNER_RECOVERY": 1}`。

## 结论边界

- 该 MC20 为定向尾部/边缘/机制诊断样本，不是总体良率。
- 本结果是同一固定 MC20 方法下的 resizing 配对动态比较，不形成 MC200、promotion 或 signoff 结论。
