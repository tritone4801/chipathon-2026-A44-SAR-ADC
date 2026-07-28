# A44 SAR ADC R2 Progress and Performance

## Status summary

The current resized SAR ADC circuit set and the fixed verification campaigns
have been assembled into the self-contained package at
[`verification/a44_r2`](../verification/a44_r2).

The following activities are complete:

- current resized circuit collection, including four `.sch` files and five
  `.sym` files;
- MC200 TT LOW/W4 execution;
- selected PVT3 MC20 LOW/W4 execution;
- six unique FULL255 static transfer-curve executions;
- CACE 2.9 Xschem-to-ngspice package preflight;
- 130-record quick reproducibility run;
- full-campaign staging dry-run;
- package source-copy, dependency-closure, root-layout, and SHA-256 audits.

The final campaign disposition is:

```text
COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION
```

This status separates execution completeness from performance qualification.
All prescribed matrices were completed. FULL255 static passes on its sole
qualification case, seed 44 TT; the current no-promotion disposition remains
because the MC200 hard-dynamic gate has three failures.

## Fixed simulation methods

### MC200 TT LOW/W4

- Method: `FAST64_SS_W4`
- PVT: TT, 3.3 V, 27 degrees C
- Signal scope: LOW band
- Maximum transient step: 50 ps
- Population: mismatch seeds 1 through 200
- Event-noise seed: `100000 + mismatch seed`
- Frames per job: 68
- Startup/diagnostic frames: 0 through 3
- Formal W4 window: frames 4 through 67, 64 records

The MC200 result is a TT LOW-band population. It is not a two-band die-level
yield result.

### PVT3 selected MC20 LOW/W4

- Method: the same `FAST64_SS_W4` method and 50 ps maximum step
- Formal window: frames 4 through 67
- Corners: TT/3.3 V/27 degrees C, SS/3.0 V/125 degrees C, and
  FF/3.6 V/-40 degrees C
- Population: 20 selected seeds per corner, 60 records total

The selected MC20 sets are diagnostic corner samples. They are not MC200
populations and cannot support performance PASS, production-yield, promotion,
or signoff claims. PVT results are reported for diagnostic visibility only and
are not a PASS basis.

### FULL255 static

Each static curve uses a formal 255-transition search. The sole FULL255 static
qualification case is seed 44 at TT/3.3 V/27 degrees C (`S044_TT`). It is
computed once and reused in the four-seed TT view and the seed-44 PVT view
after exact method and hash checks.

The other TT seeds and the seed-44 SS/FF curves are diagnostic-only. Their
threshold outcomes may be recorded, but they cannot establish or overturn
FULL255 qualification PASS. The package contains six unique formal curves,
while only `S044_TT` is used for qualification.

## Dynamic performance

### MC200 TT LOW/W4

| Metric | Value |
| --- | ---: |
| Completed records | 200/200 |
| Exceptions | 0 |
| Hard-dynamic PASS | 197 |
| Hard-dynamic FAIL | 3 |
| Failing seeds | 65, 68, 141 |
| SNDR P1, Type-7 | 46.8729 dB |
| SNDR P5, Type-7 | 47.2961 dB |
| SNDR P10, Type-7 | 47.4636 dB |
| SNDR P50, Type-7 | 48.4065 dB |

Authoritative result directory:
[`02_SIMULATION_RESULTS/01_MC200_TT_LOW_W4`](../verification/a44_r2/02_SIMULATION_RESULTS/01_MC200_TT_LOW_W4)

### PVT3 selected MC20 LOW/W4

| Corner | Completion | Hard-dynamic PASS | SNDR P50 |
| --- | ---: | ---: | ---: |
| TT, 3.3 V, 27 degrees C | 20/20 | 19/20 | 48.4048 dB |
| SS, 3.0 V, 125 degrees C | 20/20 | 20/20 | 48.3026 dB |
| FF, 3.6 V, -40 degrees C | 20/20 | 20/20 | 48.6010 dB |

Authoritative result directory:
[`02_SIMULATION_RESULTS/02_PVT3_MC20_LOW_W4`](../verification/a44_r2/02_SIMULATION_RESULTS/02_PVT3_MC20_LOW_W4)

## Static performance

| Case | PVT | Seed | Maximum absolute DNL | Maximum absolute INL | Missing codes | Reversals | Qualification use |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| S044_TT | TT/3.3 V/27 degrees C | 44 | 0.610351 LSB | 0.686645 LSB | 0 | 0 | **PASS — sole qualification basis** |
| S116_TT | TT/3.3 V/27 degrees C | 116 | 0.422577 LSB | 0.358017 LSB | 0 | 0 | Diagnostic only |
| S180_TT | TT/3.3 V/27 degrees C | 180 | 0.469508 LSB | 0.451902 LSB | 0 | 0 | Diagnostic only |
| S106_TT | TT/3.3 V/27 degrees C | 106 | 0.146719 LSB | 0.093900 LSB | 0 | 0 | Diagnostic only |
| S044_SS | SS/3.0 V/125 degrees C | 44 | 1.496350 LSB | 1.572634 LSB | 1 | 1 | Diagnostic only; threshold failure is not a qualification gate |
| S044_FF | FF/3.6 V/-40 degrees C | 44 | 0.328772 LSB | 0.416836 LSB | 0 | 0 | Diagnostic only |

FULL255 static therefore qualifies as PASS based only on `S044_TT`. The SS and
FF curves are PVT diagnostics and do not contribute to a PASS/FAIL or promotion
decision.

Authoritative result directory:
[`02_SIMULATION_RESULTS/03_FULL255_STATIC`](../verification/a44_r2/02_SIMULATION_RESULTS/03_FULL255_STATIC)

## Reproducibility and integrity

The CACE 2.9 preflight executed the Xschem-to-ngspice path and passed with
`final_v = 1.250 V`, inside the allowed 1.249 V to 1.251 V range.

The quick reproducibility run compares:

- 25/25 MC200 records;
- 75/75 PVT3 records;
- 30/30 FULL255 static records.

The aggregate result is 130/130 matches with status:

```text
PASS_QUICK_REPRODUCIBILITY_ALL_LANES
```

The package audit also reports:

- package integrity: PASS;
- R1-to-R2 relocation: 3,086 exact copies plus eight declared path-only
  portability patches;
- generated-deck dependency closure: PASS;
- package-owned GF180 ngspice model hashes: PASS;
- SHA-256 manifest readback: 4,846 records, zero mismatches;
- full-run staging: `STAGED_DRY_RUN_PASS`.

Primary audit files:

- [`PACKAGE_STATUS.json`](../verification/a44_r2/05_PACKAGE_AUDIT/PACKAGE_STATUS.json)
- [`manifest_readback_latest.json`](../verification/a44_r2/05_PACKAGE_AUDIT/manifest_readback_latest.json)
- [`dependency_closure_audit.json`](../verification/a44_r2/05_PACKAGE_AUDIT/dependency_closure_audit.json)
- [`source_copy_audit.json`](../verification/a44_r2/05_PACKAGE_AUDIT/source_copy_audit.json)
- [`package_manifest_sha256.csv`](../verification/a44_r2/05_PACKAGE_AUDIT/package_manifest_sha256.csv)

The files under `verification/a44_r2` are frozen, hash-audited evidence. Where
the frozen `PACKAGE_STATUS.json` describes the diagnostic seed-44 SS curve as a
promotion blocker, this repository-level report is the current governing
interpretation: only seed 44 TT is used for FULL255 qualification, and PVT is
not a PASS/FAIL basis. The frozen file is retained unchanged to preserve audit
integrity.

## Claim boundaries and remaining work

The following statements are not supported by this package:

- two-band die-level yield;
- production-yield qualification;
- layout or PEX signoff;
- silicon validation;
- tapeout readiness;
- full ADC signoff.

The unresolved electrical items are the three MC200 hard-dynamic failures.
The seed-44 SS FULL255 threshold failure remains useful diagnostic evidence but
is not a qualification failure and does not block promotion.
