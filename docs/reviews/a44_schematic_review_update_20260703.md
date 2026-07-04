# A44 JST SAR ADC Schematic Review Update Draft

This file is a staging draft for review before updating the official Team A44
GitHub issue and lead repository links.

Source slide deck: `A44_Team_JST_schematic_review.pptx`

Date prepared: 2026-07-03

Repository artifact index:
`docs/reviews/a44_confirmed_artifact_index_20260703.md`

## Repository Update Draft

### Project Summary

Team A44 JST is developing an 8-bit, 2-MS/s, 3.3-V fully differential
capacitive SAR ADC in GF180MCU for Chipathon 2026 Track A.

The current schematic-review architecture uses:

| Area | Current schematic-review content |
|---|---|
| Process / architecture | GF180MCU, top-plate sampled capacitive SAR ADC |
| Resolution / sample rate | 8 bit, 2 MS/s nominal, 500 ns sample frame |
| Supply / common-mode | 3.3 V analog and digital, VCM = 1.65 V |
| Reference / full scale | VREFP = 2.50 V, VREFN = 0.80 V, VFS_NOM = 3.4 Vpp,diff |
| External interface | VINP, VINN, VREFP, VREFN, CLKS, DOUT[7:0] |
| Clocking contract | CLKS high samples/resets; falling edge starts self-timed conversion |
| Dynamic target | SNDR >= 44 dB, ENOB >= 7.0 bit |
| Linearity target | DNL < +/-1 LSB, INL < +/-1.5 LSB, no missing codes |
| Removed normal pins | No normal READY, CONVST, SAR_CLK, CLKC, or VCM external pin |

### Schematic Review Snapshot

The review deck shows the following current schematic hierarchy and block-level
content:

| Item | Current content |
|---|---|
| System overview | Differential CDACs, StrongARM comparator, event-toggle SAR logic, active-low CDAC controls |
| CDAC / bootstrap | Bi-directional CDAC side, top-plate sampled array, active-low bottom-plate reference switching, bootstrapped sampling switch |
| Comparator | StrongARM-style dynamic comparator integrated in the TOP path |
| SAR logic | Actual RTL/PEX wrapper integrated in the TOP path with self-timed conversion protocol checks |
| Review focus | Pin contract, conversion timing, comparator-to-SAR handoff, and CDAC control convention |

### Simulation and Verification Items

The following table mirrors the schematic-review slide content. Status labels
are attached to individual simulation or verification items, not to a whole
block-level signoff claim.

| Item | Specific simulation / verification |
|---|---|
| TOP functionality | [Completed] Clean top-level interface and instance audit;<br>[Completed] Static smoke and selected single-conversion sweep;<br>[Completed] 64-frame closed-loop functional transient;<br>[Completed] Short coherent-sine dynamic screening; |
| Performance | [Completed] Ideal dynamic reference baseline;<br>[Questionable] Preliminary actual TOP dynamic screening pending review;<br>[Questionable] Output-valid timing and fixed-latency alignment review;<br>[Incomplete] Static DNL/INL and missing-code verification; |
| Digital SAR logic | [Completed] Actual RTL/PEX wrapper integrated in TOP path;<br>[Completed] Self-timed conversion protocol checks;<br>[Completed] SAR decision and CDAC-update sequence evidence;<br>[Incomplete] Corner and timing-margin extension; |
| CDAC / bootstrap | [Completed] Active-low CDAC selector convention verified;<br>[Completed] Bootstrap switch resolved in final CDAC path;<br>[Completed] Settling, glitch, and reference-overlap screening;<br>[Incomplete] CDAC mismatch, PEX, and layout matching verification; |
| Comparator | [Completed] StrongARM comparator integrated in TOP path;<br>[Completed] Standalone delay/reset/kickback/metastability screening;<br>[Completed] Comparator decision sanity checks in current TOP screening;<br>[Incomplete] Comparator noise, offset, and Monte Carlo verification; |
| Integrated mixed signal | [Completed] Final-used module package assembled for review;<br>[Completed] Actual CDAC + comparator + SAR logic closed-loop path demonstrated;<br>[Questionable] Screening-result review before signoff expansion;<br>[Incomplete] PVT, Monte Carlo, layout/PEX, and final signoff table; |

### Evidence Boundary

The schematic-review update should be treated as current review evidence, not
as final silicon or full-chip signoff.

Current review evidence supports:

- clean top-level interface and instance audit;
- schematic hierarchy review;
- block-level schematic review of CDAC/bootstrap, comparator, and SAR logic;
- current repaired/TOP-path closed-loop screening evidence;
- preliminary dynamic screening and protocol checks.

Current review evidence does not yet claim:

- final actual TOP static DNL/INL or missing-code signoff;
- full PVT/corner timing closure;
- CDAC mismatch, PEX, and layout matching signoff;
- comparator noise, offset, and Monte Carlo signoff;
- integrated PEX/layout/Monte Carlo/yield signoff;
- final production-source signoff.

### Repository Paths Updated In This Staging Package

| Area | Path |
|---|---|
| GitHub entry point | `README.md` |
| Frozen design target | `current_goal.md` |
| Current schematic design source | `design/xschem/sar_logic` |
| Current RTL/PEX SAR logic package | `sar_logic_actual_RTL` |
| SAR logic validation package | `verification/sar_logic_actual` |
| Actual CDAC + comparator time/frequency reports | `verification/reports` |
| Actual CDAC + comparator time/frequency plots | `verification/plots` |
| Ideal SAR time/frequency baseline reports and plots | `verification/ideal_sar` |
| Time/frequency result and plot scope | `docs/reviews/a44_time_frequency_result_plot_scope_20260703.md` |
| Artifact index | `docs/reviews/a44_confirmed_artifact_index_20260703.md` |

## Draft GitHub Issue #114 Update

Suggested comment body for
`https://github.com/sscs-ose/sscs-chipathon-2026/issues/114`:

```markdown
## Team A44 JST - Schematic Review Update

We have prepared the schematic-review package for the A44 JST 8-bit,
2-MS/s, 3.3-V fully differential SAR ADC in GF180MCU.

### Current Architecture

- Process / architecture: GF180MCU, top-plate sampled capacitive SAR ADC.
- Resolution / sample rate: 8 bit, 2 MS/s nominal.
- Supply / common-mode: 3.3 V analog and digital, VCM = 1.65 V.
- References / full scale: VREFP = 2.50 V, VREFN = 0.80 V,
  VFS_NOM = 3.4 Vpp,diff.
- External interface: VINP, VINN, VREFP, VREFN, CLKS, DOUT[7:0].
- Clocking contract: CLKS high samples/resets; falling edge starts
  self-timed conversion.
- Removed normal pins: no normal READY, CONVST, SAR_CLK, CLKC, or VCM
  external pin.

### Schematic Review Content

- System overview: differential CDACs, StrongARM comparator,
  event-toggle SAR logic, and active-low CDAC controls.
- CDAC/bootstrap: bi-directional top-plate sampled CDAC side, active-low
  bottom-plate reference switching, and bootstrapped sampling switch.
- Comparator: StrongARM-style dynamic comparator integrated in the TOP path.
- Digital SAR logic: actual RTL/PEX wrapper integrated in the TOP path.
- Review focus: pin contract, conversion timing, comparator-to-SAR handoff,
  and CDAC control convention.

### Simulation / Verification Items

| Item | Specific simulation / verification |
|---|---|
| TOP functionality | [Completed] Clean top-level interface and instance audit;<br>[Completed] Static smoke and selected single-conversion sweep;<br>[Completed] 64-frame closed-loop functional transient;<br>[Completed] Short coherent-sine dynamic screening; |
| Performance | [Completed] Ideal dynamic reference baseline;<br>[Questionable] Preliminary actual TOP dynamic screening pending review;<br>[Questionable] Output-valid timing and fixed-latency alignment review;<br>[Incomplete] Static DNL/INL and missing-code verification; |
| Digital SAR logic | [Completed] Actual RTL/PEX wrapper integrated in TOP path;<br>[Completed] Self-timed conversion protocol checks;<br>[Completed] SAR decision and CDAC-update sequence evidence;<br>[Incomplete] Corner and timing-margin extension; |
| CDAC / bootstrap | [Completed] Active-low CDAC selector convention verified;<br>[Completed] Bootstrap switch resolved in final CDAC path;<br>[Completed] Settling, glitch, and reference-overlap screening;<br>[Incomplete] CDAC mismatch, PEX, and layout matching verification; |
| Comparator | [Completed] StrongARM comparator integrated in TOP path;<br>[Completed] Standalone delay/reset/kickback/metastability screening;<br>[Completed] Comparator decision sanity checks in current TOP screening;<br>[Incomplete] Comparator noise, offset, and Monte Carlo verification; |
| Integrated mixed signal | [Completed] Final-used module package assembled for review;<br>[Completed] Actual CDAC + comparator + SAR logic closed-loop path demonstrated;<br>[Questionable] Screening-result review before signoff expansion;<br>[Incomplete] PVT, Monte Carlo, layout/PEX, and final signoff table; |

### Evidence Boundary

This is a schematic-review update, not final full-chip signoff. Remaining
items include static DNL/INL and missing-code verification, PVT/corner
extension, CDAC PEX/mismatch/layout matching, comparator noise/offset/Monte
Carlo, integrated PEX/layout/Monte Carlo/yield, and final production-source
signoff.

The test-result and plot updates promoted by this GitHub package are limited
to time-domain waveforms and frequency-domain spectra. Static DNL/INL,
transfer-curve, protocol, symbol, hierarchy, and power plots are intentionally
outside this update scope.
```

## Intended Official Updates After Review

After the draft is approved, the intended official updates are:

1. Add the schematic-review update to the official team repository.
2. Add or update the schematic-review slide link in issue #114.
3. Post the issue update comment above, adjusted with the final slide/video
   links.
4. Preserve the evidence boundary so that screening, schematic review, and
   full signoff claims remain separated.
