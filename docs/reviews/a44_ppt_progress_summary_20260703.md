# A44 PPT Progress Summary

Prepared: 2026-07-03

Source deck: `A44_Team_JST_schematic_review.pptx`

This page converts the current schematic-review PPT content into GitHub
Markdown tables. It summarizes project progress only; it does not add
verification code, testbenches, generated decks, or rerun instructions.

## Project And Team

| Item | PPT content |
|---|---|
| Team | A44 Team JST |
| Project | 8-bit, 2-MS/s, 3.3-V fully differential SAR ADC in GF180MCU |
| Repository shown in PPT | `github.com/jmack2201/chipathon-2026-A44-SAR-ADC` |
| Official issue shown in PPT | `github.com/sscs-ose/sscs-chipathon-2026/issues/114` |
| Video / full review links | To be filled after recording/review-link finalization |

## Team Roles

| Team member | Affiliation / background | Role |
|---|---|---|
| Jacob Mack | PhD Graduate, University of Michigan | Team lead, Digital Design |
| Shangqi Han | Graduate, Columbia University | Mixed-Signal Design |
| Tashvi Mehta | Undergraduate, University of California, Berkeley | Analog Design |

## Design Targets And Assumptions

| Metric | Current target / assumption |
|---|---|
| Process / architecture | GF180MCU; top-plate sampled capacitive SAR ADC |
| Resolution / sample rate | 8 bit; 2 MS/s nominal; 500 ns sample frame |
| Supply / common-mode | 3.3 V analog and digital; VCM = 1.65 V |
| Reference / full scale | VREFP = 2.50 V; VREFN = 0.80 V; VFS_NOM = 3.4 Vpp,diff |
| External interface | VINP, VINN, VREFP, VREFN, CLKS, DOUT[7:0] |
| Clocking contract | CLKS high samples/resets; falling edge starts self-timed conversion |
| Dynamic target | SNDR >= 44 dB; ENOB >= 7.0 bit |
| Linearity target | DNL < +/-1 LSB; INL < +/-1.5 LSB; no missing codes |
| Removed normal pins | No normal READY, CONVST, SAR_CLK, CLKC, or VCM external pin |

## Schematic Review Snapshot

| Area | PPT progress summary |
|---|---|
| System overview | Differential CDACs, StrongARM comparator, event-toggle SAR logic, and active-low CDAC controls are shown in the top-level Xschem hierarchy. |
| Review focus | Pin contract, conversion timing, comparator-to-SAR handoff, and CDAC control convention. |
| CDAC / bootstrap | Bi-directional CDAC side, top-plate sampled array, active-low bottom-plate reference switching, and bootstrapped sampling switch are included in the schematic summary. |
| Comparator | StrongARM-style dynamic comparator is included in the schematic summary. |
| SAR loop | Self-timed SAR loop is part of the schematic decision set. |

## Progress Table From PPT

| Item | Completed | In review / questionable | Planned / incomplete |
|---|---|---|---|
| TOP functionality | Clean top-level interface and instance audit; static smoke and selected single-conversion sweep; 64-frame closed-loop functional transient; short coherent-sine dynamic screening | None listed in PPT | None listed in PPT |
| Performance | Ideal dynamic reference baseline; preliminary actual TOP dynamic screen | Output-valid timing and fixed-latency alignment | Static DNL/INL and missing-code verification |
| Digital SAR logic | Actual RTL/PEX wrapper integrated in TOP path; self-timed conversion protocol checks; SAR decision and CDAC-update sequence evidence | None listed in PPT | Corner and timing-margin extension |
| CDAC / bootstrap | Active-low CDAC selector convention verified; bootstrap switch resolved in final CDAC path; settling, glitch, and reference-overlap screening | None listed in PPT | CDAC mismatch, PEX, and layout matching verification |
| Comparator | StrongARM comparator integrated in TOP path; standalone delay/reset/kickback/metastability screening; comparator decision sanity checks in current TOP screening | None listed in PPT | Comparator noise, offset, and Monte Carlo verification |
| Integrated mixed signal | Final-used module package assembled for review; actual CDAC + comparator + SAR logic closed-loop path demonstrated | Screening-result review before signoff expansion | PVT, Monte Carlo, layout/PEX, and final signoff table |

## GitHub Update Boundary

| Scope item | Policy for this staging branch |
|---|---|
| Project/design files | Included when they describe the current confirmed design or engineering handoff. |
| Simulation results | Included as compact Markdown, CSV, JSON, and PNG result artifacts. |
| Verification code | Not included in the promoted update. |
| Testbenches / generated decks / rerun scripts | Not included in the promoted update. |
| Final signoff claims | Not claimed. Remaining signoff items stay open in the progress table. |
