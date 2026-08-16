# 理想 SAR ADC 结果证据索引

本文是 `verification/ideal_sar/results/` 的中文审阅索引，对齐
`D:\PICO\CODEX_IDEAL_SAR_ADC_TESTBENCH_VALIDATION.md` 中对结果文件、日志、
时域波形和频谱图的要求。本文不重新定义测量结果；所有数值以自动生成的
`metrics.json`、`csv/metrics.csv`、独立 CSV、日志和 PNG 图为准。

## 当前结论

- 最终判定由 `../report/ideal_sar_adc_testbench_validation.md` 给出。
- 权威全量运行日志为 `logs/run_all_container.log`，应包含 `go_no_go: GO` 和 `EXIT_CODE=0`。
- 单一配置源为 `../config/sar_adc.yaml`。
- 主指标表为 `csv/metrics.csv`，覆盖矩阵为 `csv/coverage_matrix.csv`。
- 动态代表性测试使用 `0.8823529411764706` FS peak，即冻结规范的 `3.0 Vpp,diff` 输入；phase=0.37 rad、M=65536、无窗 coherent FFT。
- 两个 canonical 输入 bin 为 low-frequency `k=997` 和 near-Nyquist `k=32113`。

## 目录与用途

| 路径 | 用途 |
|---|---|
| `metrics.json` | 各阶段结构化结果、工具版本、GO 状态、派生常数和动态频谱摘要。 |
| `csv/metrics.csv` | 主指标表，包含 category、metric、variant、condition、target、measured、status、raw_data_path、plot_path 等字段。 |
| `csv/coverage_matrix.csv` | 文档要求到证据文件的 PASS/FAIL 对照。 |
| `csv/adc_input_output_time_*.csv` | 代表性时域输入/输出数据，含采样时间、`EOC_INT` 时间、VINP/VINN、vdiff、输出码、十六进制码、经理想 DAC 转换后的输出电压、重构电压、量化误差、`CLKS` 下降沿采样标记和 `EOC_INT`。输入/输出波形比较的正式方法是：将 `EOC_INT` 更新后的 DOUT 经过理想重构 DAC 得到 `ideal_DAC(DOUT)`，再与对应采样输入 `x[n]` 比较。 |
| `csv/adc_dac_reconstruction_low_frequency.csv` | 仅使用 low-frequency 输入的 DAC 重构对比数据；这是优先查看的输入/输出波形比较图，因为它清楚展示采样输入、`EOC_INT` 更新后的 DOUT、理想 DAC(DOUT) 输出与量化误差之间的对应关系。 |
| `csv/adc_output_spectrum_*.csv` | 代表性输出频谱逐 bin 数据，含频率、线性功率、dBFS、fundamental/harmonic/largest-spur 分类。 |
| `csv/dynamic_sqnr_sqdr_sweep.csv` | 幅度、频率、相位 sweep 下的 SQNR、SQDR、SQNDR、SNDR、ENOB。 |
| `csv/dynamic_points/*.csv` | 每个动态 sweep 点的 direct/SAR/oracle 独立结果。 |
| `plots/adc_input_output_time_*.png` | 输入和输出的多面板时域波形图。 |
| `plots/adc_fft_*.png` | 按 dBFS 标注的输出频谱图。 |
| `logs/*.log` | preflight、ngspice、cocotb、power proxy 和全量容器运行日志。 |
| `raw/*` | 原始动态输出码、量化误差、cocotb XML 和 power proxy waveform。 |

## 关键动态证据

| 项目 | low-frequency | near-Nyquist |
|---|---|---|
| coherent bin | `997` | `32113` |
| 时域 CSV | `csv/adc_input_output_time_low_frequency.csv` | `csv/adc_input_output_time_near_nyquist.csv` |
| 时域显示样点 | `192` | `64` |
| DAC 重构对比图 | `plots/adc_dac_reconstruction_low_frequency.png` | 输入/输出波形比较的正式方法图 |
| DAC 重构 CSV | `csv/adc_dac_reconstruction_low_frequency.csv` | 输入/输出波形比较的正式方法数据 |
| 频谱 CSV | `csv/adc_output_spectrum_low_frequency.csv` | `csv/adc_output_spectrum_near_nyquist.csv` |
| 频谱 bin 数 | `32769` | `32769` |
| 时域图 | `plots/adc_input_output_time_low_frequency.png` | `plots/adc_input_output_time_near_nyquist.png` |
| 频谱图 | `plots/adc_fft_low_frequency.png` | `plots/adc_fft_near_nyquist.png` |

## 测量基础

- 差分输入定义：`v_diff = VINP - VINN`。
- 波形输入/输出比较定义：使用 `ideal_DAC(DOUT)` 作为 ADC 输出模拟波形；它在内部 `EOC_INT` 时刻更新，并与对应采样输入 `x[n]` 比较。
- 理想差分范围：`-1.70 V <= v_diff <= +1.70 V`。
- `VFS_diff_pp = 3.4 V`，`LSB_diff = 3.4 V / 2^8 = 13.28125 mV`。
- straight-binary 量化：`code = floor((v_diff - v_min)/LSB)`，并饱和到 `0..255`。
- 重构电压：`V_DAC_center(code) = v_min + (code + 0.5)*LSB`。
- 理想满幅动态近似：`SNR_ideal = 6.02*N + 1.76 + 20*log10(A_FS_peak)`。
- `ENOB = (SNDR - 1.76)/6.02`。
- 频谱功率按 one-sided FFT 计算，dBFS 参考为 `P_FS_sine = VFS_diff_peak^2/2`。
- `SQNR_spectral` 使用 fundamental power / nonharmonic quantization-noise power。
- `SQDR` 使用 fundamental power / folded 2nd-through-10th harmonic power。
- `SQNDR` 使用 fundamental power / (noise + distortion)，并与 SNDR 对齐。

## 审阅检查

- 检查 `logs/run_all_container.log` 是否包含 `go_no_go: GO` 与 `EXIT_CODE=0`。
- 检查 `csv/coverage_matrix.csv` 是否全部为 `PASS`，尤其是 `DYN-06` 到 `DYN-08`。
- 检查 `csv/metrics.csv` 是否列出 SQNR、SQDR、SQNDR、输入/输出波形和输出频谱。
- 抽查 `plots/adc_dac_reconstruction_low_frequency.png` 是否把 ideal DAC(DOUT) 作为输入/输出波形比较方法，并展示 sampled input、`EOC_INT` 更新后的 DOUT 和 ideal DAC(DOUT) 的对应关系。
- 抽查 `plots/adc_input_output_time_*.png` 与对应 `csv/adc_input_output_time_*.csv` 是否一致。
- 抽查 `plots/adc_fft_*.png` 与对应 `csv/adc_output_spectrum_*.csv` 是否一致。

## 复现命令

```powershell
python verification\ideal_sar\scripts\run_all.py all
```

权威 Chipathon 容器运行：

```powershell
docker run --rm -v "D:/PICO/simple_SAR_ADC_repo:/work" -w /work hpretl/iic-osic-tools:chipathon26 --skip bash -lc "python3 verification/ideal_sar/scripts/run_all.py all; code=$?; echo EXIT_CODE=$code; exit $code"
```
