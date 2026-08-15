# Chipathon 2026 A44 SAR ADC

This repository contains the Team A44 8-bit, 2 MS/s, 3.3 V fully differential
capacitive SAR ADC design and its verification evidence.

## Current layout review

The current Chipathon 2026 layout-review baseline is the no-pad, pre-fill CORE
layout bound by `info.yaml` and `lvs_config.json`:

- [CORE GDS](gds/A44_SAR_ADC_CORE_1000.gds)
- [Component GDS](gds/components)
- [Layout catalog, integration views, and images](layout/README.md)
- [Layout-review presentation](docs/slides/A44_SAR_ADC_LAYOUT_REVIEW_20260821.pptx)

This publication is for layout review. It does not claim density/fill closure,
padframe or ESD completion, full-chip signoff, Channel Partner acceptance, or
tapeout readiness.

## Current project status

The current transistor-level/electrical package is:

[`verification/a44_r2`](verification/a44_r2)

It contains the current resized circuit set, all frozen simulation results,
CACE and simulation tooling, one-click launchers, documentation, and SHA-256
audits. The package is organized as follows:

- `01_CURRENT_CIRCUIT_FILES`: current resized `.sch`, `.sym`, SPICE, and RTL
  files.
- `02_SIMULATION_RESULTS`: MC200, PVT3 MC20, FULL255 static, CACE-generated,
  quick-reproduction, and staging results.
- `03_CACE_AND_SIMULATION_TOOLS`: CACE configuration, package-owned GF180
  ngspice model snapshot, scripts, and Makefile.
- `04_PACKAGE_DOCS`: method, result, and file indexes.
- `05_PACKAGE_AUDIT`: source-copy, dependency, layout, and SHA-256 audits.

The package-level integrity and reproducibility checks pass. The electrical
performance campaign is complete as executed but does **not** pass promotion:

```text
COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION
```

See [A44 R2 progress and performance](docs/A44_SAR_ADC_R2_PROGRESS_AND_PERFORMANCE.md)
for the exact method, metrics, evidence paths, and claim boundaries.

The current project tracker is available at
[A44 SAR ADC Project Tracker R2](docs/A44_SAR_ADC_Project_Tracker_20260728_R2.xlsx).

## Current electrical results

| Evidence set | Completion | Current interpretation |
| --- | ---: | --- |
| MC200 TT LOW/W4 | 200/200 | 197 hard-dynamic PASS; 3 FAIL: Seeds 65, 68, and 141 |
| FULL255 static | 6 unique curves | **PASS based only on Seed 44 TT (`S044_TT`)** |
| PVT3 selected MC20 LOW/W4 | 60/60 | Diagnostic-only; not a PASS, yield, promotion, or signoff basis |
| CACE package preflight | 1/1 | PASS, `final_v = 1.250 V` |
| Quick reproducibility | 130/130 | PASS |
| Package manifest readback | 4,846 records | PASS, zero mismatches |

For FULL255 qualification, `S044_TT` is the sole governing case:
maximum `|DNL| = 0.610351 LSB`, maximum `|INL| = 0.686645 LSB`,
zero missing codes, and zero reversals. Other TT seeds and the Seed 44 SS/FF
curves are diagnostic-only. PVT cannot establish or overturn FULL255 PASS.

Package integrity, CACE execution, and quick reproducibility PASS do not imply
electrical performance PASS, population yield, layout/PEX signoff, silicon
signoff, tapeout readiness, or production readiness.

## One-click package entry points

From `verification/a44_r2` on Windows:

```powershell
.\RUN_QUICK_VERIFY.ps1
```

The full campaign launcher executes the complete campaign and can be
long-running:

```powershell
.\RUN_FULL_CAMPAIGN.ps1
```

To stage and validate the full campaign without dispatching the complete
matrix:

```powershell
docker exec iic-osic-tools_a44_xvnc bash --noprofile --norc -lc "cd /foss/designs/chipathon-2026-A44-SAR-ADC/verification/a44_r2 && make -C 03_CACE_AND_SIMULATION_TOOLS full-dry-run"
```

## Ideal reference model

The earlier ideal reference flow remains available under
[`verification/ideal_sar`](verification/ideal_sar). It is useful as an ideal
system-level baseline, but it is not transistor-level electrical authority and
must not override the R2 circuit campaign results.
