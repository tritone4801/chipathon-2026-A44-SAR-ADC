# Chipathon 2026 A44 SAR ADC

This repository combines the Chipathon 2026 workshop padring fork of the
wafer-space `gf180mcu-project-template` with the current Team A44 8-bit,
2 MS/s, 3.3 V fully differential capacitive SAR ADC design and verification
evidence.

No PRs are planned against upstream; all chipathon-specific material
stays in this fork.

## Current A44 SAR ADC package

The current transistor-level/electrical handoff is:

[`verification/a44_r2`](verification/a44_r2)

It contains the current resized `.sch`/`.sym` circuit set, SPICE and RTL
bindings, frozen simulation results, CACE and simulation tooling, one-click
launchers, method documentation, and SHA-256 audits.

Current disposition:

```text
COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION
```

Execution, package integrity, and reproducibility are complete. Promotion
remains blocked by three MC200 hard-dynamic failures; this is not a layout,
PEX, silicon, tapeout, production-yield, or full-signoff claim.

### Governing performance summary

| Evidence set | Completion | Current interpretation |
|---|---:|---|
| MC200 TT LOW/W4 | 200/200 | 197 hard-dynamic PASS; 3 FAIL: Seeds 65, 68, 141 |
| FULL255 static | 6 unique curves | **PASS based only on Seed 44 TT (`S044_TT`)** |
| PVT3 selected MC20 LOW/W4 | 60/60 | Diagnostic-only; not a PASS, yield, promotion, or signoff basis |
| CACE package preflight | 1/1 | PASS, `final_v = 1.250 V` |
| Quick reproducibility | 130/130 | PASS |
| Package manifest readback | 4,846 records | PASS, zero mismatches |

For FULL255 qualification, `S044_TT` is the sole governing case:
maximum `|DNL| = 0.610351 LSB`, maximum `|INL| = 0.686645 LSB`,
zero missing codes, and zero reversals. Other TT seeds and the Seed 44 SS/FF
curves are diagnostic-only. PVT cannot establish or overturn FULL255 PASS.

Review entry points:

| Artifact | Purpose |
|---|---|
| [`current_goal.md`](current_goal.md) | Frozen A44 SAR ADC project target, interface, timing contract, and pad plan |
| [`docs/A44_SAR_ADC_R2_PROGRESS_AND_PERFORMANCE.md`](docs/A44_SAR_ADC_R2_PROGRESS_AND_PERFORMANCE.md) | Current fixed methods, progress, metrics, evidence paths, and claim boundaries |
| [`docs/A44_SAR_ADC_Project_Tracker_20260728_R2.xlsx`](docs/A44_SAR_ADC_Project_Tracker_20260728_R2.xlsx) | English project tracker with dashboard and governing verification-status sheet |
| [`docs/reviews/a44_ppt_progress_summary_20260703.md`](docs/reviews/a44_ppt_progress_summary_20260703.md) | GitHub table summary extracted from the schematic-review PPT |
| [`docs/reviews/a44_issue_114_update_20260704.md`](docs/reviews/a44_issue_114_update_20260704.md) | Issue-ready update text for official Chipathon issue #114 |
| [`docs/reviews/a44_schematic_review_update_20260703.md`](docs/reviews/a44_schematic_review_update_20260703.md) | Schematic-review status and design boundary |
| [`docs/reviews/a44_confirmed_artifact_index_20260703.md`](docs/reviews/a44_confirmed_artifact_index_20260703.md) | Confirmed artifact index for design files, result summaries, and plots |
| [`verification/reports/verification_summary.md`](verification/reports/verification_summary.md) | Compact actual CDAC + comparator integrated result summary |
| [`docs/reviews/a44_time_frequency_result_plot_scope_20260703.md`](docs/reviews/a44_time_frequency_result_plot_scope_20260703.md) | Explicit time-domain and frequency-domain plot/result scope |

### One-click package entry points

From `verification/a44_r2` on Windows:

```powershell
.\RUN_QUICK_VERIFY.ps1
```

The complete campaign launcher is long-running:

```powershell
.\RUN_FULL_CAMPAIGN.ps1
```

The earlier review reports and plots remain historical review artifacts. The
R2 report and package are the current authority for simulation methods,
metrics, qualification scope, and result locations.

## Credits

This repository is a **derivation**. The template, Nix flake, and
LibreLane flow are the work of Leo Moser and the wafer-space
contributors; the workshop pad layout is a port of Juan Moya's
`padring_gf180`. Both are Apache-2.0.

- Upstream template — https://github.com/wafer-space/gf180mcu-project-template
  pinned at commit `8bd0f6ff28947bf222c5288343f8f3ee1fc04632`
  (`chore: update flake to librelane 3.0`, 2026-03-26).
- Workshop pad layout — https://github.com/JuanMoya/padring_gf180
  (`Workshop_CASS/padring/workshop_padring.cfg`).

See `CREDITS.md` for the per-artifact attribution and `NOTICE` for
the formal Apache-2.0 notice.

## Workshop infrastructure changes vs upstream

The workshop padring infrastructure originally changed these six files:

| File | Change |
|------|--------|
| `src/slot_defines.svh` | add `SLOT_WORKSHOP` block (NUM_INPUT=1, BIDIR=20, ANALOG=60, 4/4 DVDD/DVSS) |
| `src/chip_core.sv` | replace example counter with a 20-bit counter driving the 20 bidir pads; analog pads float through |
| `librelane/slots/slot_workshop.yaml` | **new** slot (DIE 2935x2935 um, CORE 2051x2051 um, VERILOG_DEFINES=SLOT_WORKSHOP) |
| `librelane/config.yaml` | drop SRAM `MACROS` entry and PDN macro connections - not used in this slot |
| `librelane/pdn_cfg.tcl` | drop SRAM-specific `define_pdn_grid` blocks |
| `Makefile` | `AVAILABLE_SLOTS += workshop` |

`git log upstream/main..main` shows the single derivation commit;
`git diff upstream/main..main` shows the delta.

## Workshop slot - pad map at a glance

- Die: **2935 x 2935 um** (same as Juan Moya's reference).
- **60 x analog** (`gf180mcu_fd_io__asig_5p0`)
- **20 x bidir** (`gf180mcu_fd_io__bi_24t`)
- **4 x DVDD** + **4 x DVSS** (`gf180mcu_ws_io__dvdd` / `__dvss`)
- **clk_pad** (`gf180mcu_fd_io__in_s`), **rst_n_pad** (`gf180mcu_fd_io__in_c`)
- **1 x input_pad** - Yosys zero-width-vector workaround; chipathon
  participants can ignore it (documented in `docs/workshop-slot-spec.md`).
- **4 x corner** (`gf180mcu_fd_io__cor`, inserted by LibreLane).

Pad ordering in `PAD_NORTH` and `PAD_WEST` is **reversed** relative to
Juan Moya's standalone `workshop_padring.cfg` because LibreLane reads
pad lists clockwise from the SW corner. Full pad-by-pad mapping in
`docs/workshop-slot-spec.md`.

## Quickstart

### Build the workshop slot (native, nix-shell)

```bash
git clone <this-repo-url> chipathon-2026-gf180mcu-padring
cd chipathon-2026-gf180mcu-padring
nix-shell               # provides LibreLane 3.0.0
make clone-pdk          # clones wafer-space/gf180mcu @ 1.8.0
SLOT=workshop make librelane
```

Runtime on a modern laptop: **~2h 15m** for the full signoff run
(Magic DRC + KLayout DRC + LVS + antenna + STA across 3 corners).

Final artifacts land in `final/`:
- `final/gds/chip_top.gds` (~85 MB)
- `final/metrics.csv` (signoff metrics)
- `final/*.log` (per-stage logs)

### Inspect a built GDS (Docker, hpretl/iic-osic-tools)

`scripts/run_docker_iic.sh` spawns the iic-osic-tools container with
this repo mounted; inside the container run `klayout final/gds/chip_top.gds`
or `magic -T .../gf180mcuD.magicrc ...`.

See `docs/reproducing-native.md` and `docs/reproducing-docker.md` for
the detailed walkthroughs.

### Use the workshop slot for your own RTL

Swap `src/chip_core.sv` with your design, keeping the port list
(NUM_INPUT=1, NUM_BIDIR=20, NUM_ANALOG=60, clk, rst_n), and re-run
`SLOT=workshop make librelane`. Padring stays fixed.

## Verification

The repository was validated **end-to-end** against a known-good
reference build. To re-run the pragmatic check (byte-compare the
six tracked files against the reference tree):

```bash
scripts/verify_workshop_slot.sh /path/to/reference/template
```

The reference build (DRC/LVS/antenna/STA signoff on 2026-04-23 with
LibreLane 3.0 + wafer-space PDK 1.8.0) is the source of truth for
"clean". As long as the fork's six files byte-match that reference,
a fresh build on a compatible host will reproduce the same result.

If you do not have the reference tree, the repo itself is the ground
truth - this fork *is* those six files.

## Repository layout

```
.
|-- README.md                       # this file
|-- NOTICE                          # Apache-2.0 attribution
|-- CREDITS.md                      # detailed credits
|-- AUTHORS.md                      # copyright holders (upstream + fork)
|-- LICENSE                         # Apache-2.0
|-- docs/
|   |-- workshop-slot-spec.md       # full pad-by-pad mapping
|   |-- reproducing-native.md       # nix-shell walkthrough
|   `-- reproducing-docker.md       # iic-osic-tools walkthrough
|-- examples/
|   `-- rtl2gds_chipathon_padring.ipynb   # standalone notebook
|-- scripts/
|   |-- run_docker_iic.sh           # iic-osic-tools launcher
|   `-- verify_workshop_slot.sh     # pragmatic end-to-end check
|-- librelane/
|   |-- config.yaml                 # top-level LibreLane config (patched)
|   |-- pdn_cfg.tcl                 # PDN generator (patched)
|   |-- chip_top.sdc                # upstream, unchanged
|   `-- slots/
|       |-- slot_0p5x0p5.yaml       # upstream, unchanged
|       |-- slot_0p5x1.yaml         # upstream, unchanged
|       |-- slot_1x0p5.yaml         # upstream, unchanged
|       |-- slot_1x1.yaml           # upstream, unchanged
|       `-- slot_workshop.yaml      # new (this fork)
|-- src/
|   |-- chip_top.sv                 # upstream, unchanged
|   |-- chip_core.sv                # patched (counter->bidir)
|   `-- slot_defines.svh            # patched (SLOT_WORKSHOP)
|-- Makefile                        # patched (AVAILABLE_SLOTS += workshop)
`-- (upstream infra: flake.nix, gf180mcu/, ip/, cocotb/, scripts/, ...)
```

## License

Apache-2.0, inherited from upstream. See `LICENSE` for the full text,
`NOTICE` for attribution of third-party material, and `AUTHORS.md`
for the list of copyright holders.
