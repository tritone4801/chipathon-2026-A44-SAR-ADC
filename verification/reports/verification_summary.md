# SAR ADC CDAC + Comparator Integrated Verification Summary

Decision: **GO_AUTOMATED_ACTUAL_CDAC_CMP_TIME_FREQUENCY_SCOPE**

The actual-CDAC+actual-comparator wrapper acceptance package is scoped here to
time-domain waveform evidence and frequency-domain spectrum evidence. Static
DNL/INL, transfer-curve, protocol, symbol, hierarchy, and power plots are not
promoted by this review update. Evidence classes remain separate from full ADC
transistor/PEX signoff.

## 1. Configuration Boundary

The promoted GitHub review update does not include verification scripts,
generated decks, testbenches, or rerun configuration files. This report keeps
only the compact review decision, result tables, and plot references.

## 2. Design Files Untouched Check

The review branch keeps engineering handoff files separate from compact
simulation results. It does not claim that rerunning the verification package is
possible from this branch alone.

## 3. Simulation Modes

| Mode | Status | Evidence class | Notes |
| --- | --- | --- | --- |
| `IDEAL_ADC` | `PASS` | `IDEAL_BASELINE_REFERENCE` | Existing ideal_sar metrics plus regenerated plot artifacts. |
| `ACTUAL_CDAC_CMP_ADC_FIXED_B2_SMOKE` | `PASS` | `ACTUAL_ELECTRICAL_AUTHORITY` | Same-run fixed-code smoke proves actual CDAC, bootstrap switch, and actual comparator elaborate and resolve VFOP>VFON under fixed ideal B2 controls. |
| `ACTUAL_CDAC_CMP_ADC` | `PASS` | `ACTUAL_ELECTRICAL_AUTHORITY` | Closed-loop smoke passed after warm-up: actual CDAC + actual comparator + ideal SAR logic produced all checked codes with no illegal comparator state. |
| `ACTUAL_CDAC_CMP_ADC` | `PASS_SMOKE_ONLY` | `ACTUAL_ELECTRICAL_AUTHORITY` | Integrated smoke is summarized in the compact result table; static metric acceptance is outside this update scope. |
| `ACTUAL_CDAC_CMP_ADC` | `PASS` | `ACTUAL_ELECTRICAL_AUTHORITY` | Actual closed-loop midband full dynamic run completed from ngspice .meas DOUT samples. |
| `ACTUAL_CDAC_CMP_ADC` | `PASS` | `ACTUAL_ELECTRICAL_AUTHORITY` | Actual closed-loop near_nyquist full dynamic run completed from ngspice .meas DOUT samples. |

## 4. Smoke Results

- Smoke summary source: `verification/reports/metrics_summary.csv`
- Fixed-B2 same-run smoke plot: `verification/plots/actual_cdac_cmp_fixed_b2_smoke.png`
- Fixed-B2 same-run smoke status: `PASS`
- Closed-loop smoke plot: `verification/plots/actual_cdac_cmp_closed_loop_smoke.png`
- Closed-loop smoke status: `PASS`
- Closed-loop measured codes after warm-up: `[0, 1, 64, 127, 128, 129, 178, 192, 254, 255, 128, 178, 77, 220, 33, 240]`

## 5. Timing Results

- Ideal timing plot: `verification/plots/ideal_detailed_timing_cycle_0.png`
- Actual closed-loop timing plot: `verification/plots/actual_detailed_timing_cycle_0.png`
- Actual fixed-B2 smoke plot: `verification/plots/actual_cdac_cmp_fixed_b2_smoke.png`
- Actual closed-loop smoke plot: `verification/plots/actual_cdac_cmp_closed_loop_smoke.png`

## 6. Dynamic Results

- Ideal spectrum: `verification/plots/ideal_spectrum_midband.png`
- Actual midband spectrum: `verification/plots/actual_spectrum_midband.png`
- Actual midband status: `PASS`
- Actual near-Nyquist spectrum: `verification/plots/actual_spectrum_near_nyquist.png`
- Actual near-Nyquist status: `PASS`
- Dynamic metrics CSVs: `verification/reports/dynamic_metrics_midband.csv`, `verification/reports/dynamic_metrics_near_nyquist.csv`

## 7. Out-of-Scope Result Types

This GitHub review update intentionally promotes only time-domain and
frequency-domain test results and plots. Static linearity, DNL/INL,
transfer-curve, protocol, symbol, hierarchy, and power plot updates are left
out of the promoted result/plot scope.

## 8. Required Plots

| Plot | Status | Notes |
| --- | --- | --- |
| `verification/plots/ideal_time_domain_input_output.png` | `PASS` | generated ideal/reference artifact |
| `verification/plots/actual_time_domain_input_output.png` | `PASS` | summarized by the full actual midband dynamic result table |
| `verification/plots/ideal_detailed_timing_cycle_0.png` | `PASS` | generated ideal/reference artifact |
| `verification/plots/actual_detailed_timing_cycle_0.png` | `PASS` | summarized by actual closed-loop smoke timing |
| `verification/plots/ideal_spectrum_midband.png` | `PASS` | generated ideal/reference artifact |
| `verification/plots/actual_spectrum_midband.png` | `PASS` | summarized by full actual midband dynamic FFT |
| `verification/plots/ideal_spectrum_near_nyquist.png` | `PASS` | generated ideal/reference artifact |
| `verification/plots/actual_spectrum_near_nyquist.png` | `PASS` | summarized by full actual near-Nyquist dynamic FFT |

## 9. Pass/fail Table

| Requirement | Status |
| --- | --- |
| ideal baseline passes all ideal checks | `PASS` |
| actual CDAC+comparator fixed-code same-run smoke completes | `PASS` |
| actual_cdac_cmp integrated run completes | `PASS_SMOKE_ONLY` |
| closed-loop smoke checked-code sequence | `PASS` |
| standard input does not clip | `PASS_SMOKE_ONLY` |
| SNDR >= 44 dB | `midband PASS; near-Nyquist PASS` |
| ENOB >= 7.0 bit | `midband PASS; near-Nyquist PASS` |
| time-domain and frequency-domain plots generated separately for ideal and actual ADC | `PASS` |
| production design files unchanged | `PASS` |

## 10. Open Issues

1. No automated open issue remains in this verification package; review residual assumptions before signoff reuse.

## 11. Rerun Boundary

Verification implementation files, generated decks, and rerun scripts are not
part of this staging update. The promoted update is limited to engineering
files plus compact simulation results and plots.
