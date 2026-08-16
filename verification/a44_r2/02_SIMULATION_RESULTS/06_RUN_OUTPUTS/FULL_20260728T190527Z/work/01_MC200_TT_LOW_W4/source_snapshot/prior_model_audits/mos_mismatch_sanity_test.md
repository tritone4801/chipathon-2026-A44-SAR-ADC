# MOS Mismatch Sanity Test

- Generated UTC: `2026-07-01T19:32:43+00:00`
- Model: GF180 ngspice MOS local mismatch path.
- Observable: relative drain-current mismatch between identically biased, same-size device pairs.
- Pair count per case: `200`
- Pair metrics CSV: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\csv\mos_mismatch_pair_metrics.csv`
- Area scaling CSV: `D:\PICO\SAR_SUM_process_typicality_20260701_initial_gate\csv\mos_mismatch_area_scaling.csv`
- Reproducibility: `REVIEW`
- Reproducibility note: repeat execution of the same generated deck was not bit-identical even with `setseed`; use these results for aggregate primitive screening, not selected-seed replay.

## Control Status

| Device | Negative mismatch-off | Positive x2 | x2 sigma ratio | Area scaling | corr(sigma, 1/sqrt(area)) |
|---|---|---|---:|---|---:|
| NMOS | `PASS` | `PASS` | 2.107 | `PASS` | 0.987 |
| PMOS | `PASS` | `PASS` | 2.177 | `PASS` | 0.992 |

## Area Scaling Summary

| Case | Device | Area factor | mismatch scale | sigma(delta I/I) | max abs(delta I/I) |
|---|---|---:|---:|---:|---:|
| `nmos_mismatch_on_area1` | NMOS | 1 | 1.0 | 0.0209123 | 0.0570673 |
| `nmos_mismatch_on_area2` | NMOS | 2 | 1.0 | 0.0167032 | 0.049743 |
| `nmos_mismatch_on_area4` | NMOS | 4 | 1.0 | 0.0102405 | 0.0329665 |
| `nmos_mismatch_on_area8` | NMOS | 8 | 1.0 | 0.00763224 | 0.0237739 |
| `nmos_negative_mismatch_off_area1` | NMOS | 1 | 0.0 | 0 | 0 |
| `nmos_positive_mismatch_x2_area1` | NMOS | 1 | 2.0 | 0.0440632 | 0.115631 |
| `pmos_mismatch_on_area1` | PMOS | 1 | 1.0 | 0.0185604 | 0.0539057 |
| `pmos_mismatch_on_area2` | PMOS | 2 | 1.0 | 0.0135965 | 0.0401246 |
| `pmos_mismatch_on_area4` | PMOS | 4 | 1.0 | 0.0081915 | 0.0258515 |
| `pmos_mismatch_on_area8` | PMOS | 8 | 1.0 | 0.00677026 | 0.017983 |
| `pmos_negative_mismatch_off_area1` | PMOS | 1 | 0.0 | 0 | 0 |
| `pmos_positive_mismatch_x2_area1` | PMOS | 1 | 2.0 | 0.0404118 | 0.119954 |

Claim boundary: this proves the primitive MOS local mismatch model responds to mismatch enable/scale and device area. It does not provide comparator offset yield or ADC Monte Carlo mismatch simulation signoff.
