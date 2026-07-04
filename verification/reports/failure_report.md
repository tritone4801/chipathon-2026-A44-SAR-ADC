# Failure Report

## Failure summary

No active automated failure remains for the `ACTUAL_CDAC_CMP_ADC` verification package.

## Closed evidence

- closed-loop smoke status: `PASS`
- full midband dynamic status: `PASS`, SNDR `48.68344813019537` dB, ENOB `7.79459271265704`
- full near-Nyquist dynamic status: `PASS`, SNDR `48.683448130195366` dB, ENOB `7.794592712657038`

## Evidence

- summary: `verification/reports/metrics_summary.csv`
- verification summary: `verification/reports/verification_summary.md`
- midband dynamic table: `verification/reports/dynamic_metrics_midband.csv`
- near-Nyquist dynamic table: `verification/reports/dynamic_metrics_near_nyquist.csv`

## Residual scope note

This GO is limited to the actual CDAC + actual comparator + ideal SAR logic verification wrapper. It is not a full ADC transistor-level, post-layout, or PEX signoff claim.

Static DNL/INL and transfer-curve evidence is outside the promoted
time-domain/frequency-domain result scope for this GitHub review update.
