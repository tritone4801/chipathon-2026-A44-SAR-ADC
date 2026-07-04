# A44 Confirmed Design, Test, and Plot Artifact Index

Prepared: 2026-07-03

This index lists the current English repository package for review in
`tritone4801/simple_SAR_ADC`. It is a staging package for review before any
official issue or lead-repository update.

Promoted test-result and plot scope:
`docs/reviews/a44_time_frequency_result_plot_scope_20260703.md`

PPT progress summary:
`docs/reviews/a44_ppt_progress_summary_20260703.md`

## Design Sources

| Area | Path | Contents | Current claim boundary |
|---|---|---|---|
| Frozen target | `current_goal.md` | A44 interface, timing, CDAC, comparator, SAR logic, pad, and verification requirements | Project source of truth; not simulation evidence by itself |
| Xschem SAR logic | `design/xschem/sar_logic` | Current schematic SAR logic hierarchy, symbols, and GF180 wrapper symbols | Design source for schematic review |
| Actual SAR RTL | `sar_logic_actual_RTL/rtl` | `sar_logic_async_core_RTL.sv`, wrapper, delay-cell model, and definitions | Digital implementation source |
| RTL physical handoff | `sar_logic_actual_RTL/gds`, `def`, `lef`, `netlist` | GDS, DEF, LEF, synthesized/place-route netlists, and LVS netlist | Digital physical handoff artifacts |
| SAR logic PEX wrapper | `sar_logic_actual_RTL/pex/SAR_LOGIC_ACTUAL_RTL_pex_wrapper.spice` | Wrapper around the Magic PEX core with the reviewed pin order | PEX integration input; not full ADC signoff |
| Imported actual analog blocks | `sar_logic_actual_RTL/imported_actual_adc` | Extracted CDAC, StrongARM comparator, bootstrap switch, and top schematic copy | Actual block sources used by the closed-loop review deck |
| SAR logic validation results | `verification/sar_logic_actual/report`, `verification/sar_logic_actual/results` | Waveform/spectrum CSV evidence, reports, plots, and active manifest/metrics files | Automated SAR-logic review evidence; manual timing review remains separate |
| Ideal reference results | `verification/ideal_sar/report`, `verification/ideal_sar/results` | Ideal baseline reports, CSVs, JSON metrics, and selected plots | Ideal/manual reference and connectivity evidence |

## Test and Result Evidence

| Evidence package | Key files | Status in current reports | Evidence class |
|---|---|---|---|
| Ideal reference harness | `verification/ideal_sar/results/metrics.json`, `verification/ideal_sar/results/csv/metrics.csv`, `verification/ideal_sar/report/ideal_sar_adc_testbench_validation.md` | `PASS` | `IDEAL_BASELINE_REFERENCE` |
| Actual CDAC + comparator integrated flow | `verification/reports/verification_summary.md`, `verification/reports/metrics_summary.csv` | `GO_AUTOMATED_ACTUAL_CDAC_CMP_TIME_FREQUENCY_SCOPE` | Promoted result rows are limited to time-domain and frequency-domain evidence |
| Actual dynamic tests | `verification/reports/dynamic_metrics_midband.csv`, `verification/reports/dynamic_metrics_near_nyquist.csv` | midband `PASS`; near-Nyquist `PASS` | `ACTUAL_ELECTRICAL_AUTHORITY` for actual integrated frequency-domain rows |
| SAR logic RTL/PEX package | `sar_logic_actual_RTL/reports/xschem_ngspice/evidence_status_PathB_RTL.md`, `sar_logic_actual_RTL/reports/xschem_ngspice/pathB_acceptance_audit_RTL.md`, `sar_logic_actual_RTL/SAR_LOGIC_ACTUAL_RTL_XSCHEM_USAGE.md` | Path B acceptance items are documented as passing where claimed | PEX and closed-loop logic evidence, separated from full ADC signoff |
| SAR logic validation package | `verification/sar_logic_actual/report/sar_logic_actual_schematic_validation.md`, `verification/sar_logic_actual/results/metrics.json`, `verification/sar_logic_actual/results/manifest.json` | `GO_AUTOMATED`; manual timing review is `PENDING_USER_REVIEW` | Only waveform/spectrum rows are promoted as result/plot updates; broader rows remain supporting validation context |

## Plot Artifacts

| Plot group | Paths | Purpose |
|---|---|---|
| Actual time-domain review | `verification/plots/actual_time_domain_input_output.png`, `verification/plots/actual_detailed_timing_cycle_0.png`, `verification/plots/actual_cdac_cmp_closed_loop_smoke.png` | Closed-loop input/output and waveform timing review |
| Actual spectra | `verification/plots/actual_spectrum_midband.png`, `verification/plots/actual_spectrum_near_nyquist.png`, plus quick/full variants | Dynamic performance review for midband and near-Nyquist cases |
| SAR logic validation plots | `verification/sar_logic_actual/results/plots/timing_target_B_actual_logic_B2_waveform.png`, `verification/sar_logic_actual/results/plots/adc_time_domain_target_B_actual_logic_low_frequency.png`, `verification/sar_logic_actual/results/plots/adc_spectrum_target_B_actual_logic_calibrated_low_frequency.png`, plus related time/frequency rows | SAR logic waveform and spectrum review |
| Ideal reference plots | `verification/plots/ideal_time_domain_input_output.png`, `verification/plots/ideal_spectrum_midband.png`, `verification/plots/ideal_spectrum_near_nyquist.png` | Baseline time/frequency comparison only |
| Ideal harness plots | `verification/ideal_sar/results/plots/adc_input_output_time_low_frequency.png`, `verification/ideal_sar/results/plots/adc_input_output_time_near_nyquist.png`, `verification/ideal_sar/results/plots/adc_output_spectrum_low_frequency.png`, `verification/ideal_sar/results/plots/adc_output_spectrum_near_nyquist.png` | Ideal time-domain and spectrum baseline plots |

## Files Intentionally Not Treated as Review Source

The repository keeps compact CSV/JSON/Markdown/PNG artifacts for review. Bulky
raw waveform data, compiled simulator outputs, obsolete flow archives, and
LibreLane run directories are not treated as the current review source unless a
report explicitly cites a compact derivative file.

Ignored or excluded examples include:

- `sar_logic_actual_RTL/archive`
- `sar_logic_actual_RTL/flow/runs`
- verification scripts, testbenches, generated decks, and rerun command
  packages
- raw `.raw`, `.vvp`, and large `.dat` simulator outputs
- transient debug scratch files not linked from a current report
- static DNL/INL, transfer-curve, symbol, hierarchy, protocol, and power plots
  are not promoted by this update

## Review-Ready Summary

The current GitHub staging package supports schematic-review discussion of:

- the frozen CLKS-only external interface;
- current SAR logic schematic and RTL/PEX handoff files;
- current SAR logic validation reports, metrics, manifests, and plots;
- actual CDAC + actual comparator integrated closed-loop test evidence;
- ideal baseline comparison evidence;
- time-domain waveform and frequency-domain spectrum plots for review;
- explicit separation between review evidence and final signoff.

It does not claim final PVT, Monte Carlo, extracted full-ADC, layout/yield, or
production-source signoff.
