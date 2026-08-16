# PDK Statistical Capability validation

- Generated UTC: `2026-07-01T19:15:53+00:00`
- Original coarse method: `COARSE_TEXT_GREP_ONLY`
- Runnable model invocation: `USED_FOR_TINY_PRIMITIVE_DECKS`
- Source report directory: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\reports`
- Grep log: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\logs\pdk_model_grep.log`
- Text capability CSV: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\csv\pdk_model_capabilities.csv`
- Runnable capability results directory: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\csv`

| Model type | Text presence | Runnable sanity status |
|---|---|---|
| MOS fixed corners | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MOS process Monte Carlo mismatch simulation | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MOS local mismatch | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MOS thermal/flicker noise path | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MIM capacitor nominal | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MIM capacitor process variation | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| MIM capacitor local mismatch | `NOT_FOUND_IN_LOCAL_MIM_SUBCKTS` | `NOT_PDK_NATIVE_FOR_CDAC_LOCAL_MISMATCH` |
| resistor process variation | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| resistor local mismatch | `MANUAL_REVIEW_REQUIRED` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| BJT process variation | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |
| BJT local mismatch | `YES` | `RUNNABLE_SANITY_PASS_NOT_DISTRIBUTION_VALIDATED` |

The runnable validation proves the PDK sections can be invoked by ngspice in tiny primitive decks. The follow-up MIM source validation found runnable global MIM capacitance variation, but did not find a verified per-instance MIM local mismatch control in the included MIM subcircuits. CDAC unit-cap mismatch is therefore routed to `CDAC_MISMATCH_ENGINEERING_SENSITIVITY` / T2 unless a separate verified local MIM mismatch model is provided.

This validation does not authorize PDK-native Monte Carlo distribution claims, ADC statistical signoff, or layout/PEX signoff.

## Phase B MOS Primitive Sanity Supplement

- MOS mismatch sanity report: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\reports\mos_mismatch_sanity_test.md`
- MOS noise sanity report: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\reports\mos_noise_sanity_test.md`
- MOS mismatch model response: `PASS_FOR_AGGREGATE_SCREENING`.
- MOS noise model response: `PASS_FOR_PRIMITIVE_NOISE_PATH_SCREENING`.
- Repeatability limitation: repeat execution of the same generated mismatch deck was not bit-identical even with `setseed`; selected-seed replay is not proven from this ngspice path.

This supplement supports primitive aggregate screening for MOS mismatch/noise response only. Comparator offset/noise and ADC-level statistical claims still require their own block/system results.
