# A44 Time/Frequency Result and Plot Scope

Prepared: 2026-07-03

This file defines the promoted test-result and plot scope for the current
GitHub staging branch. The scope is intentionally limited to time-domain
waveforms and frequency-domain spectra.

## Promoted Result Files

| Type | Path | Role |
|---|---|---|
| Summary | `verification/reports/verification_summary.md` | Human-readable time/frequency review summary |
| Summary CSV | `verification/reports/metrics_summary.csv` | Compact promoted result table |
| Midband dynamic metrics | `verification/reports/dynamic_metrics_midband.csv` | Actual CDAC + comparator frequency-domain evidence |
| Near-Nyquist dynamic metrics | `verification/reports/dynamic_metrics_near_nyquist.csv` | Actual CDAC + comparator frequency-domain evidence |
| SAR logic time/spectrum evidence | `verification/sar_logic_actual/results/csv/adc_time_domain_*`, `verification/sar_logic_actual/results/csv/adc_spectrum_*` | Supporting SAR-logic waveform and spectrum rows |
| Ideal reference time/spectrum evidence | `verification/ideal_sar/results/csv/adc_input_output_time_*`, `verification/ideal_sar/results/csv/adc_output_spectrum_*` | Ideal baseline waveform and spectrum rows |

## Promoted Plot Files

| Type | Path pattern |
|---|---|
| Actual top-level time-domain plots | `verification/plots/actual_*time*.png`, `verification/plots/actual_*timing*.png`, `verification/plots/actual_cdac_cmp_*smoke.png` |
| Actual top-level spectra | `verification/plots/actual_spectrum_*.png` |
| Ideal top-level time-domain plots | `verification/plots/ideal_*time*.png`, `verification/plots/ideal_*timing*.png`, `verification/plots/smoke_timing_ideal.png` |
| Ideal top-level spectra | `verification/plots/ideal_spectrum_*.png` |
| SAR logic waveform plots | `verification/sar_logic_actual/results/plots/*time_domain*.png`, `verification/sar_logic_actual/results/plots/*waveform*.png` |
| SAR logic spectra | `verification/sar_logic_actual/results/plots/*spectrum*.png` |
| Ideal harness time/spectrum plots | `verification/ideal_sar/results/plots/adc_input_output_time_*.png`, `verification/ideal_sar/results/plots/adc_output_spectrum_*.png` |

## Explicitly Out Of Scope

The current GitHub review update does not promote these as test-result or plot
updates:

- static transfer, DNL, INL, missing-code, or histogram plots;
- protocol, symbol, hierarchy, connectivity, or power plots;
- static-ramp CSV/JSON result files;
- full PVT, Monte Carlo, layout/PEX, yield, or signoff reports.

Those items may remain as design-support context elsewhere in the repository,
but they are not part of the current promoted result/plot update.
