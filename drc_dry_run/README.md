# A44 Chipathon 2026 DRC dry-run input

This directory documents the Team A44 padless top-level GDS submitted for the
Chipathon 2026 DRC/LVS dry run.

## Bound design

- Top cell: `A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR`
- Bounding box: `0,0 - 1000,1000 um`
- PDK: GF180MCU
- Baseline: `R3B_CHILD_ECO1_PREFILL_R1`
- Fill state: pre-fill; no new top-owned COMP/Poly2 or metal dummy fill
- I/O pads: absent, as required for the current dry-run top-level GDS

Pins:

- Power/ground: `VDD`, `GND`
- Analog inputs/references: `VINP`, `VINN`, `VREFP`, `VREFN`
- Clock: `CLKS`
- Outputs: `DOUT[7:0]`

## Repository bindings

- Project entry point: [`../info.yaml`](../info.yaml)
- LVS configuration: [`../lvs_config.json`](../lvs_config.json)
- GDS: [`../gds/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.gds`](../gds/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.gds)
- LEF: [`../lef/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.lef`](../lef/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.lef)
- LVS source: [`../netlists/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.spice`](../netlists/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.spice)
- Physical black box: [`../verilog/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.blackbox.v`](../verilog/A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR.blackbox.v)
- Structured receipt: [`SUBMISSION.json`](SUBMISSION.json)
- SHA-256 manifest: [`MANIFEST.sha256`](MANIFEST.sha256)
- Read-only verifier: [`verify_submission.py`](verify_submission.py)

Run the package consistency check in an environment that provides the KLayout
Python module:

```sh
python3 drc_dry_run/verify_submission.py
```

The exact local pre-fill GDS and LVS-source binding was independently audited
before publication. The retained evidence record is
[`evidence/PREFILL_G7_FULL_LVS_INDEPENDENT_GATE.json`](evidence/PREFILL_G7_FULL_LVS_INDEPENDENT_GATE.json).

## Exclusions and claim boundary

This dry-run package intentionally excludes:

- I/O pads and the workshop full-die/padring GDS
- DEF and OAS outputs
- the post-fill R4 manual-review candidate
- report-only layout PNGs

The organizer dry-run DRC result is pending. This repository state does not
claim organizer acceptance, final fill ownership, fill-aware PEX closure,
manual layout approval, promotion, foundry signoff, or tapeout readiness.
