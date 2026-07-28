# A44 SAR ADC — Codex Simulation Execution Guide
## TT Timed-Behavioral SAR Control / No-R6 / MC200 / FAST64 Schematic Analog-Core Signoff Plan

- **Document status:** Execution Guide / Frozen Verification Plan
- **Revision date:** 2026-07-18
- **Applicable project:** Chipathon 2026 Team A44, GF180MCU 8-bit fully differential asynchronous SAR ADC
- **Intended executor:** Codex
- **Expected completion label:** `PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200`

> [!IMPORTANT]
> This document contains an explicit scope override for this verification campaign: **actual transistor-level or gate-level SAR LOGIC is not part of the signoff criteria for this campaign.**
> All claim-bearing static, dynamic, PVT, Monte Carlo, and noise simulations shall use a timed behavioral controller derived from **TT / 3.3 V / 27 °C SAR-logic timing evidence**.
> The signoff scope is therefore **schematic analog-core performance signoff with timed behavioral SAR control**. It is not full-integrated actual-SAR-logic schematic signoff, and it is not PEX, layout, package, or tapeout signoff.

---

# 0. Highest-Priority Execution Instructions

## 0.1 Mandatory completion items

Codex shall close all of the following items:

1. Freeze and audit all production sources, the PDK, simulators, random seeds, and configuration files.
2. Use one and only one timed behavioral controller: `SAR_LOGIC_BEH_TT_3P3_27C`.
3. Remove `R6_FULL_RC_HEAVY`, while retaining explicit, traceable input, reference, and digital-interface equivalent loads.
4. Complete TT nominal full 255-transition DNL/INL extraction.
5. Complete an efficient analog-PVT screen and perform claim-bearing full-transition extraction at the static-worst corner.
6. Complete MC200 static screening, full-transfer reconstruction, and exact-seed model validation.
7. Complete comparator/sample-noise calibration, an event-based noise model, and selected-transition probability testing.
8. Complete MC200 mismatch-plus-noise FAST64 analysis.
9. Complete a small number of FAST256 low-frequency and near-Nyquist closure runs.
10. Generate numerical reports, Monte Carlo statistics, DNL plots, INL plots, and FFT spectrum plots.
11. Automatically issue `PASS`, `FAIL`, or `BLOCKED` according to the gates defined in this document. Ambiguous status wording is prohibited.

## 0.2 Prohibited actions

Codex shall not:

- modify production schematics, symbols, RTL, PEX, GDS, DEF, LEF, or current-goal files;
- add actual SAR-logic simulation as a signoff prerequisite for this campaign;
- build a second behavioral model from SS or FF SAR-logic delay data;
- vary TT logic timing with analog PVT;
- use zero-delay, zero-output-resistance, infinitely fast ideal SAR control;
- allow the behavioral SAR controller to read `VINP/VINN` directly and calculate an ideal code;
- enable temporal noise during formal deterministic DNL/INL transition search;
- change the mismatch seed on every conversion;
- describe unverified MIM mismatch or an arbitrarily selected capacitor sigma as PDK-native Monte Carlo;
- describe an equivalent noise model that has not been calibrated at transistor or block level as actual StrongARM noise;
- call FAST64 the final dynamic reference without FAST256 closure;
- save all internal nodes and very large raw files for bulk Monte Carlo runs;
- describe no-R6 results as loaded-interface, pad, ESD, package, or final-TOP signoff;
- silently discard failed jobs or alter the frozen seed list;
- select a favorable FFT phase, noise seed, or PVT corner to obtain a passing result.

## 0.3 Final claim boundary

Allowed final claim:

```text
A44 8-bit SAR ADC schematic analog-core performance was characterized
and accepted under:
- transistor-level sampler/CDAC/comparator,
- fixed TT timed-behavioral SAR control,
- explicit source/reference/interface loading,
- analog PVT closure,
- MC200 statistical screening,
- calibrated equivalent-noise modeling,
- exact static tail validation,
- FAST64 bulk and FAST256 closure.
```

Prohibited final claims:

```text
full actual-SAR-logic schematic signoff
actual digital timing/coupling signoff
PEX/layout signoff
R6-loaded interface signoff
pad/ESD/package signoff
3-sigma production-yield proof
tapeout readiness
```

---

# 1. Frozen Specifications and Internal Guardrails

## 1.1 Hard system specifications

| Item | Frozen value |
|---|---:|
| Process | GF180MCU |
| Resolution | 8 bit |
| Nominal sample rate | 2 MS/s |
| Sample period | 500 ns |
| Nominal supply | 3.3 V |
| Input | Fully differential |
| `VCM` | 1.65 V |
| `VREFP` / `VREFN` | 2.50 V / 0.80 V |
| Nominal full scale | 3.4 Vpp,diff |
| Standard dynamic input | 3.0 Vpp,diff |
| Output code | 8-bit straight binary |
| SNDR | `>= 44 dB` |
| ENOB | `>= 7.0 bit` |
| DNL | `< ±1 LSB` |
| INL | `< ±1.5 LSB` |
| Missing codes | None |

Definitions:

```text
VID  = VINP - VINN
VICM = (VINP + VINN) / 2
LSB_NOM = 3.4 V / 256 = 13.28125 mV,diff
```

Standard sinusoidal input:

```text
VINP = 1.65 V + 0.75 V * sin(2*pi*fin*t + phase)
VINN = 1.65 V - 0.75 V * sin(2*pi*fin*t + phase)
VID  = 3.0 Vpp,diff
Input level = -1.09 dBFS relative to 3.4 Vpp,diff
```

## 1.2 Block-level guardrails for this campaign

These values are used for model calibration, tail selection, and root-cause diagnosis. Final system acceptance shall still be based on complete-ADC SNDR, ENOB, DNL, INL, and missing-code criteria.

```text
Comparator input-referred noise preferred target:
    <= 1.5 mVrms,diff

Comparator input-referred noise conditional hard ceiling:
    <= 2.0 mVrms,diff, only if full-ADC metrics pass

Total equivalent analog-noise target:
    <= 2.0 mVrms,diff

Engineering noise stress:
    2.5 mVrms,diff

Comparator raw offset preferred statistical target:
    |mu(VOS)| + 3*sigma(VOS) <= 0.5 LSB = 6.640625 mV,diff

Common-mode / bit-cycle-dependent offset shift target:
    <= 0.25 LSB = 3.3203125 mV,diff
```

---

# 2. Sources of Truth, Precedence, and Integrity Rules

## 2.1 Reference inputs

Codex shall use and record the following read-only inputs:

```text
current_goal.md / current_goal (1).md
try_PERFORMANCE.txt
read_measurement_definitions.txt
A44_Team_JST_schematic_review.pptx
OnChipSAR - Schematic Review.pdf
GF180MCU PDK model files
current production sampler/CDAC/comparator schematic/netlist
current verified TT SAR-logic timing evidence
```

Project source for TT SAR-logic timing data:

```text
Google Drive folder:
https://drive.google.com/drive/folders/1aOTNaBozsa6bGPGpiE1OLD61HPPS80Ty

Required timing condition:
TT_3P3_27C only
```

If a read-only local mirror of the Drive content exists, prefer the local mirror. Do not substitute SS or FF timing if TT data are missing.

## 2.2 Task-level override in this document

If `current_goal.md` normally requires actual asynchronous SAR logic in complete schematic simulations, the user's later explicit instruction overrides that requirement for this campaign:

```text
Actual SAR logic is outside the signoff boundary of this campaign.
The only allowed control model is SAR_LOGIC_BEH_TT_3P3_27C.
```

Codex shall not modify `current_goal.md`. Record this override only in the claim-boundary section of the campaign master report.

## 2.3 Source-file integrity

Generate before and after execution:

```text
manifests/source_hashes_before.json
manifests/source_hashes_after.json
reports/source_integrity.md
```

If any production-source hash changes:

```text
STOP
status = BLOCKED_PRODUCTION_SOURCE_CHANGED
```

Only the following may be created in a new verification workspace:

- testbenches;
- copied netlists;
- behavioral models;
- scripts;
- configuration files;
- logs;
- raw data;
- CSV files;
- plots;
- reports.

---

# 3. Signoff DUT and Fixture

## 3.1 DUT definition

The DUT for this campaign shall be:

```text
actual transistor-level bootstrapped sampler
+ actual transistor-level P-side CDAC
+ actual transistor-level N-side CDAC
+ actual transistor-level StrongARM comparator/output buffers
+ SAR_LOGIC_BEH_TT_3P3_27C
- actual SAR logic transistor/gate/PEX netlist
- R6_FULL_RC_HEAVY
- pad / ESD / package models
```

## 3.2 No R6 does not mean zero loading

The following shall remain in the fixture:

```text
input source impedance
reference source impedance
reference decoupling, if present in the accepted fixture
comparator-output equivalent logic input capacitance
finite DCTRL source resistance
finite DCTRL rise/fall time
actual CDAC switch-gate loading
representative DOUT/output-register load if it affects the modeled interface
finite CLKS rise/fall time
```

Values shall come from an accepted verification fixture, a project specification, or an explicitly approved configuration. They shall not be set to zero without evidence.

If no input or reference source model can be established:

```text
STOP
status = BLOCKED_SOURCE_IMPEDANCE_NOT_DEFINED
```

## 3.3 Analog PVT

Use:

```text
TT_3P3_27C
SS_3P0_125C
FF_3P6_M40C
```

All analog-PVT runs shall use the same frozen TT logic timing:

```text
logic delays/slopes = frozen TT values
logic HIGH level    = current analog-corner VDD
logic LOW level     = 0 V
```

Label results explicitly, for example:

```text
ANALOG_SS_3P0_125C_WITH_FIXED_TT_LOGIC_TIMING
ANALOG_FF_3P6_M40C_WITH_FIXED_TT_LOGIC_TIMING
```

---

# 4. `SAR_LOGIC_BEH_TT_3P3_27C` Model Contract

## 4.1 Functional contract

The behavioral model may read only:

```text
CLKS
DCMPP
DCMPN
```

It shall generate:

```text
CMPCK
DCTRLP[7:1]
DCTRLN[7:1]
DOUT[7:0]
EOC_INT or equivalent internal completion marker
optional debug flags
```

It shall implement:

```text
8 comparator decisions
7 physical CDAC adjustments
first decision before any CDAC adjustment
first adjustment is the required upward bi-directional transition
subsequent adjustments follow the frozen downward switching algorithm
active-low DCTRLP/DCTRLN convention
straight-binary polarity
atomic DOUT update after D0
previous DOUT held during next conversion
conversion abort/reset if next sample starts before completion
```

The behavioral model shall not read `VINP`, `VINN`, `VFOP`, or `VFON` to calculate an ideal code.

## 4.2 Timing contract

Extract and freeze the following values from TT evidence:

```text
t_CLKS_fall_to_first_CMPCK
t_CMPCK_high[7:0]
t_decision_aperture[7:0]
t_DCMP_to_DCTRL[7:1]
t_DCTRL_rise[7:1]
t_DCTRL_fall[7:1]
t_DCTRL_to_next_CMPCK[7:1]
t_last_CMPCK_to_DOUT
```

The existing TT inter-CMPCK interval of approximately 19 ns may be used as an initial sanity value. Final configuration shall come from TT evidence and shall not be reduced to an unsupported single average delay.

For each bit, use the shortest measured settling window across representative TT input sequences:

\[
T_{\mathrm{settle},b}^{\mathrm{model}}
=
\min
\left(t_{\mathrm{CMPCK},b-1}-t_{\mathrm{DCTRL},b}\right)
\]

## 4.3 Electrical-interface contract

The model shall include:

```text
CLOGIC_IN_P / CLOGIC_IN_N on DCMPP/DCMPN
finite DCTRL output resistance
finite DCTRL rise/fall time
finite CMPCK rise/fall time
corner-dependent output HIGH level
```

The following are prohibited:

```text
ideal zero-ohm DCTRL voltage sources
zero-time edges
infinite-strength drivers
unloaded comparator outputs
```

## 4.4 Invalid-state handling

At every comparator decision aperture, detect:

```text
DCMPP=1, DCMPN=0 -> valid P decision
DCMPP=0, DCMPN=1 -> valid N decision
both-high          -> invalid
both-low at timeout-> unresolved/timeout
```

Invalid or unresolved decisions shall be recorded. Do not randomly or deterministically force one code branch.

The model shall output:

```text
invalid_decision_count
timeout_count
conversion_complete
```

---

# 5. Evidence Classification

Every report row shall carry an `evidence_tier` field:

| Tier | Definition in this campaign | Permitted claim |
|---|---|---|
| T0 | PDK-native MOS corner, mismatch, or noise | Direct model evidence under the recorded PDK and simulator |
| T1 | Analytical budgets such as kT/C or jitter | First-order physical risk assessment |
| T2 | Approved MIM mismatch model or equivalent-noise sensitivity model | Engineering evidence under explicit assumptions |
| T3 | TT timed-behavioral SAR integration or transfer reconstruction | System statistics and tail selection under the model |
| T4 | Transistor-level sampler/CDAC/comparator exact replay with behavioral control | Claim-bearing electrical closure for this campaign |
| T5 | All gates in this document passed | Schematic analog-core signoff candidate |

If MIM local mismatch is not PDK-native, the report shall retain:

```text
CDAC mismatch evidence = T2 engineering model
```

It shall not be promoted to GF180 process-typical native-MIM signoff.

---

# 6. Workspace Structure

Create a separate directory, for example:

```text
/foss/designs/manual_goal/verification/
A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_202607xx/
```

Equivalent Windows path:

```text
D:\PICO\A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_202607xx
```

Directory structure:

```text
A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_202607xx/
├── README.md
├── config/
│   ├── run_config.yaml
│   ├── timing_tt_3p3_27c.json
│   ├── source_load_model.yaml
│   ├── cdac_mismatch_model.yaml
│   ├── noise_model.yaml
│   ├── mc_seeds.csv
│   ├── noise_seeds.csv
│   └── plot_style.yaml
├── models/
│   ├── SAR_LOGIC_BEH_TT_3P3_27C.va
│   └── interface_loads.spice
├── tb/
│   ├── tb_preflight.spice
│   ├── tb_static_transition_template.spice
│   ├── tb_static_packed_mc_template.spice
│   ├── tb_static_ramp_template.spice
│   ├── tb_dynamic_fast64_template.spice
│   ├── tb_dynamic_fast256_template.spice
│   ├── tb_comparator_probability_template.spice
│   ├── tb_sample_noise_template.spice
│   └── tb_top_transition_probability_template.spice
├── scripts/
│   ├── audit_environment.py
│   ├── hash_sources.py
│   ├── audit_pdk_variation.py
│   ├── validate_behavior_contract.py
│   ├── make_seed_tables.py
│   ├── make_job_matrix.py
│   ├── run_jobs.py
│   ├── pack_static_vectors.py
│   ├── search_transitions.py
│   ├── reconstruct_transfer.py
│   ├── validate_transfer_model.py
│   ├── analyze_fft.py
│   ├── fit_transition_probability.py
│   ├── aggregate_mc.py
│   ├── select_tail_seeds.py
│   ├── make_plots.py
│   └── make_master_report.py
├── jobs/
├── logs/
├── raw/
├── csv/
├── plots/
├── reports/
└── manifests/
```

---

# 7. Unified Configuration File

`config/run_config.yaml` shall contain at least:

```yaml
project: A44_8b_2MSps_GF180
signoff_label: SCHEMATIC_ANALOG_CORE_WITH_TT_BEHAVIORAL_SAR

adc:
  bits: 8
  fs_hz: 2000000
  frame_s: 500e-9
  vdd_nom_v: 3.3
  vcm_v: 1.65
  vrefp_v: 2.50
  vrefn_v: 0.80
  vfs_pp_diff_v: 3.4
  dynamic_input_pp_diff_v: 3.0
  lsb_diff_v: 0.01328125

logic_model:
  name: SAR_LOGIC_BEH_TT_3P3_27C
  timing_file: config/timing_tt_3p3_27c.json
  logic_pvt_variation: disabled
  actual_logic_signoff: disabled

fixture:
  r6_full_rc_heavy: disabled
  source_load_file: config/source_load_model.yaml

pvt:
  - {name: TT_3P3_27C, process: TT, vdd_v: 3.3, temp_c: 27}
  - {name: SS_3P0_125C, process: SS, vdd_v: 3.0, temp_c: 125}
  - {name: FF_3P6_M40C, process: FF, vdd_v: 3.6, temp_c: -40}

numerical:
  bulk_maxstep_s: 0.10e-9
  strict_maxstep_s: 0.05e-9
  static_final_tolerance_lsb: 0.02
  transition_pack_size: 32

mc:
  mismatch_seeds: 200
  exact_validation_initial: 8
  exact_validation_expand: 16

noise:
  comparator_target_rms_diff_v: 1.5e-3
  total_target_rms_diff_v: 2.0e-3
  stress_rms_diff_v: 2.5e-3

dynamic_fast64:
  retained: 64
  startup_default: 1
  low_bin: 7
  low_fin_hz: 218750
  near_nyquist_bin: 29
  near_nyquist_fin_hz: 906250
  window: rectangular
  dout_aperture_s: 480e-9

dynamic_fast256:
  retained: 256
  low_bin: 29
  low_fin_hz: 226562.5
  near_nyquist_bin: 117
  near_nyquist_fin_hz: 914062.5
  window: rectangular

spec:
  sndr_min_db: 44
  enob_min_bit: 7.0
  dnl_abs_max_lsb: 1.0
  inl_abs_max_lsb: 1.5
  missing_codes_max: 0
```

Codex shall write the final values actually used back into a frozen configuration copy. Reports shall not depend on unrecorded script defaults.

---

# 8. Phase A — Preflight and Environment Audit

## 8.1 Tool and platform inventory

Record the following in machine-readable form and in `reports/environment_audit.md`:

```text
ngspice version and executable path
Xyce version and executable path, if used
Python version
numpy, scipy, pandas, and matplotlib versions
PDK path, revision, and Git hash when available
CPU model and physical/logical core count
installed RAM
filesystem type, free space, and output path
```

Also create:

```text
reports/tool_versions.txt
```

## 8.2 DUT binding audit

Automatically verify all of the following:

```text
2 CDAC instances
1 StrongARM comparator
actual transistor-level sampler hierarchy present
actual SAR-logic hierarchy absent
SAR_LOGIC_BEH_TT_3P3_27C present
R6_FULL_RC_HEAVY absent
input and reference source/load models present
8-bit straight-binary DOUT present
```

Write:

```text
reports/dut_binding_audit.md
```

If actual SAR logic or R6 is unexpectedly present:

```text
STOP
status = BLOCKED_WRONG_DUT_BINDING
```

## 8.3 Behavioral-contract smoke test

Run at least:

```text
negative full scale
zero differential
positive full scale
selected inputs around 31/32, 63/64, 127/128, and 191/192
```

Check:

```text
VID increases -> DOUT increases
exactly 8 comparator decisions
exactly 7 CDAC adjustments
atomic DOUT update
previous DOUT retained during conversion
no deadlock
no extra CMPCK after EOC
invalid/timeout flags operate correctly
```

---

# 9. Phase B — PDK, Mismatch, and Noise-Model Gates

## 9.1 MOS statistical-model sanity

Before using the model in the ADC, verify at primitive level:

```text
mismatch disabled -> distribution collapses
seed reproducibility
sigma decreases approximately as 1/sqrt(WL) as area increases
2x mismatch scaling approximately doubles sigma, if that control exists
mean remains physically plausible and near the expected value
```

## 9.2 MIM mismatch model

Classify the available CDAC mismatch path as one of:

```text
PDK_NATIVE_VERIFIED
APPROVED_ENGINEERING_MODEL
UNAVAILABLE
```

For `APPROVED_ENGINEERING_MODEL`, record:

```text
sigma_C/C or A_C/sqrt(area)
area scaling
P-side/N-side correlation assumption
within-array correlation assumption
systematic gradient assumption
source document, measurement, or explicit user approval
```

If no defensible model exists:

```text
STOP before static-MC signoff
status = BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE
```

## 9.3 Noise-model prerequisites

Establish separately:

```text
comparator decision-noise model
sample/hold noise model
reference-noise model, if included in the budget
```

Equivalent event-based noise shall not enter T5 signoff until calibrated to block-level electrical evidence.

Required outputs:

```text
reports/pdk_mc_noise_capability.md
config/cdac_mismatch_model.yaml
config/noise_model.yaml
```

---

# 10. Phase C — Numerical-Convergence and Runtime Pilot

## 10.1 Pilot matrix

Run at least:

```text
nominal
2 fixed random mismatch seeds
1 predicted static-tail seed
1 predicted dynamic-tail seed
```

For each case compare:

```text
maxstep = 0.10 ns
maxstep = 0.05 ns
```

Static pilot transitions:

```text
63/64
127/128
191/192
```

Dynamic pilot:

```text
FAST64, coherent bin k=7
```

## 10.2 Gate for bulk use of 0.10 ns

All of the following shall pass:

```text
|delta SNDR|       <= 0.30 dB
|delta SFDR|       <= 0.50 dB
|delta THD|        <= 0.50 dB
|delta transition| <= 0.05 LSB
DOUT streams       identical
timeout/invalid     identical
```

If passed:

```text
bulk MC and screening = 0.10 ns
final transition rounds, boundary replays, and FAST256 = 0.05 ns
```

If not passed:

```text
bulk MC = 0.05 ns
update the runtime estimate before launching the full matrix
```

## 10.3 Static-frame shortening gate

Compare:

```text
500 ns reference frame
320 ns candidate
300 ns candidate
280 ns candidate
```

A shorter frame may be used only if:

```text
transition shift <= 0.02 LSB
sampled-input error <= 0.01 LSB
all 8 decisions complete
DOUT stable margin >= 20 ns
no history/reset difference
```

Freeze the shortest passing static frame. Dynamic tests shall remain at the specified 500 ns sample period.

## 10.4 Startup-frame gate

Compare FAST64 using:

```text
startup = 0, 1, 2, and 4 frames
```

Select the minimum setting satisfying:

```text
|delta SNDR| <= 0.10 dB relative to the next-longer setting
|delta SFDR| <= 0.20 dB
all retained frames valid
```

The expected default is one startup frame; zero startup frames require explicit evidence.

Required outputs:

```text
reports/numerical_convergence.md
csv/numerical_convergence.csv
reports/runtime_pilot.md
```

---

# 11. Phase D — Efficient Analog-PVT Screening

All analog corners use the same fixed TT logic timing model.

## 11.1 Packed static PVT screen

At each corner, test at least:

```text
-FS
0
+FS
31/32
63/64
127/128
191/192
223/224
```

For each major transition, test:

```text
predicted center - 0.75 LSB
predicted center
predicted center + 0.75 LSB
```

Extract screening proxies:

```text
coarse offset and gain
major-transition displacement
selected local-width proxy
tested-point monotonicity
conversion validity
timeout/invalid flags
```

## 11.2 Dynamic PVT FAST64

At every corner, run:

```text
low-frequency: k=7, fin=218.75 kHz
near-Nyquist:  k=29, fin=906.25 kHz
```

Use the results to identify:

```text
PVT_STATIC_WORST_DNL
PVT_STATIC_WORST_INL
PVT_DYNAMIC_WORST
```

If worst DNL and worst INL occur at different corners, exact static extraction shall be performed at both corners.

Required outputs:

```text
csv/pvt_static_screen.csv
csv/pvt_dynamic_fast64.csv
reports/pvt_screen.md
```

---

# 12. Phase E — Exact Nominal and Worst-PVT Static Characterization

## 12.1 Primary method

Search all internal transition levels:

\[
T_1,T_2,\ldots,T_{255}
\]

Every decision shall execute a complete sample-and-convert sequence and read DOUT at the fixed aperture.

Decision rule:

```text
DOUT < k
DOUT >= k
```

## 12.2 Transition-search algorithm

For every transition:

1. Obtain `T_pred` from the ideal, behavioral, or reconstructed transfer.
2. Start with `T_pred ± 0.5 LSB`.
3. If the interval does not bracket the transition, expand geometrically to `±1, ±2, ±4, ... LSB`.
4. Early rounds may use the bulk numerical profile.
5. The final two rounds shall use `maxstep=0.05 ns`.
6. Stop only when the final bracket width is `<= 0.02 LSB`.
7. Independently replay all missing-code candidates, nonmonotonic candidates, and unresolved decisions using the strict profile.

## 12.3 Parallel sharding

Use:

```text
32 transitions per shard
255 transitions -> 8 shards per search round
```

Run shards in parallel. Do not launch one long-lived simulator process for every code edge.

## 12.4 Mandatory exact curves

### TT nominal

```text
low-to-high: full T1...T255
high-to-low: full T1...T255
noise: off
mismatch: off
```

### Static-worst PVT corner

```text
low-to-high: full T1...T255
high-to-low selected transitions:
    31/32
    63/64
    127/128
    191/192
    223/224
    worst-DNL transition
    worst-INL transition
```

If:

```text
max |T_up - T_down| > 0.10 LSB
```

trigger a complete high-to-low search at that corner.

## 12.5 DNL and INL definitions

Code width:

\[
W_k=T_{k+1}-T_k
\]

Endpoint LSB:

\[
Q_{EP}=\frac{T_{255}-T_1}{254}
\]

DNL:

\[
DNL_k=\frac{W_k}{Q_{EP}}-1
\]

Endpoint INL:

\[
INL_{k,EP}=
\frac{T_k-[T_1+(k-1)Q_{EP}]}{Q_{EP}}
\]

Also fit a least-squares straight line to all transitions and output `INL_BF`.

## 12.6 Ramp correlation

Run one TT nominal triangular ramp:

```text
low -> high -> low
at least 1 sample per code per direction
use the shortest validated static frame
```

Use it only for:

```text
polarity
code coverage
continuous-frame behavior
endpoint consistency
gross missing-code cross-check
```

Do not derive final DNL or INL from this low-density ramp.

Required outputs:

```text
csv/transitions_tt_nominal_up.csv
csv/transitions_tt_nominal_down.csv
csv/transitions_pvt_worst_up.csv
csv/dnl_inl_tt_nominal.csv
csv/dnl_inl_pvt_worst.csv
reports/static_exact.md
```

---

# 13. Phase F — Static MC200

## 13.1 Seed discipline

Freeze an explicit reproducible list:

```text
mismatch_seed = 1...200, or another recorded list of 200 values
```

Each seed represents one fixed virtual die:

```text
same MOS mismatch throughout every test of the die
same CDAC mismatch throughout every test of the die
same die seed reused in static and dynamic cohorts
```

Do not change mismatch realization on every conversion.

## 13.2 MC200 packed electrical screen

For every seed, run one packed deck of approximately 20 frames:

```text
Broad transfer:
    -0.75 FS
    0
    +0.75 FS

Major transitions:
    31/32
    63/64
    127/128
    191/192
    223/224

For each major transition:
    predicted -0.75 LSB
    predicted center
    predicted +0.75 LSB

History stress:
    -0.75 FS -> +0.75 FS
```

Extract:

```text
coarse offset and gain
major-transition bracket status
selected code-width proxy
history/reset flags
invalid/timeout flags
```

## 13.3 Full-transfer reconstruction

Implement `reconstruct_transfer.py` using a traceable physical model containing:

```text
approved CDAC mismatch realization
effective CDAC bit weights
sampler offset, gain, and asymmetry
comparator VOS versus VICM
fixed TT decision apertures
finite-settling residue model
frozen actual switching algorithm
```

For each seed, output:

```text
T1...T255 reconstructed
DNL_EP[code]
INL_EP[code]
INL_BF[code]
offset
gain
minimum code width
missing-code count
worst code
```

Do not use an unphysical polynomial interpolation of the packed points and call it a complete transfer function.

## 13.4 Exact-validation cohort

Initial cohort: eight seeds.

```text
2 pre-declared random seeds
P10 static-risk seed
P50 seed
P90 static-risk seed
predicted worst-DNL seed
predicted worst-INL seed
predicted worst-settling or worst common-mode-offset-shift seed
```

For every selected seed, run:

```text
full T1...T255, low-to-high
selected reverse major transitions
noise off
final tolerance 0.02 LSB
```

Model-validation gate:

```text
maximum transition error <= 0.10 LSB
maximum DNL error        <= 0.15 LSB
maximum INL error        <= 0.20 LSB
missing-code classification identical
tail ranking not materially incorrect
```

If any condition fails:

```text
expand exact cohort from 8 to 16 seeds
recalibrate the reconstruction model
rerun validation
```

Every reconstructed failure or boundary seed shall receive exact replay regardless of cohort size.

Required outputs:

```text
csv/static_mc200_reconstructed.csv
csv/static_mc_exact_validation.csv
reports/static_mc200.md
reports/transfer_model_validation.md
```

---

# 14. Phase G — Noise Calibration and Selected-Transition Probability

## 14.1 Standalone comparator decision probability

Test at least:

```text
VICM = 1.6500 V
       1.8625 V
       2.0750 V
```

Extract all three points at TT. Retest the worst common-mode point at the analog noise-worst PVT corner.

Fit:

\[
P(D=1|V_D)=\Phi\left(\frac{V_D-V_{OS}}{\sigma_{cmp}}\right)
\]

Report:

```text
VOS
sigma_cmp, input-referred differential RMS
95% confidence interval
timeout/metastability probability
```

## 14.2 Sample/CDAC noise

Extract:

```text
sampled input variance
consistency with the kT/C estimate
input-amplitude dependence
TT versus noise-worst-PVT difference
```

## 14.3 Event-based top-level noise model

Use:

```text
sample noise:
    one Gaussian draw per frame, held throughout conversion

comparator noise:
    one Gaussian draw per bit decision, held throughout the evaluate aperture
```

Do not use a continuously updated 1 ns TRRANDOM source as the bulk signoff model.

Calibration gate:

```text
sigma error <= 10% preferred, 15% maximum
T50 error   <= 0.10 LSB
```

## 14.4 Top-level selected-transition probability

Virtual dies:

```text
nominal
worst-static seed
```

Transitions:

```text
63/64
127/128
seed-specific worst-DNL transition
```

Initial sampling:

```text
5 voltage points:
    T50 -0.30 LSB
    T50 -0.15 LSB
    T50
    T50 +0.15 LSB
    T50 +0.30 LSB

64 conversions per point
```

Only when confidence intervals are inadequate may the test adaptively expand to 7–9 points or 128 conversions per point.

Required outputs:

```text
csv/comparator_noise_probability.csv
csv/sample_noise.csv
csv/top_transition_probability.csv
reports/noise_calibration.md
reports/top_transition_noise.md
```

---

# 15. Phase H — Dynamic MC200 FAST64

## 15.1 Ideal-quantizer baseline

Run an ideal 8-bit quantizer in Python under identical analysis conditions:

```text
NFFT = 64
input = 3.0 Vpp,diff
coherent bin = 7
straight-binary convention
same saturation convention
same FFT normalization
same harmonic folding
```

Sweep 16 initial phases and freeze a phase whose SNDR and SFDR are near the median, not the best phase.

## 15.2 FAST64 bulk configuration

```text
NFFT             = 64
Fs               = 2 MS/s
fin              = 7/64 * Fs = 218.75 kHz
input            = 3.0 Vpp,diff
window           = rectangular
startup          = minimum passing value from the pilot
DOUT aperture    = frame start + 480 ns, unless the pilot freezes another value
logic model      = SAR_LOGIC_BEH_TT_3P3_27C
```

## 15.3 Main population

```text
200 fixed mismatch dies
1 independent temporal-noise seed per die
```

Recommended mapping:

```text
mismatch_seed = i
noise_seed    = 100000 + i
```

Total:

```text
200 combined mismatch-plus-noise FAST64 jobs
```

## 15.4 Noise-repeat diagnostic

Select four dies:

```text
median die
P10 SNDR die
P1 SNDR die
worst-SNDR die
```

Run eight noise seeds per die:

```text
4 x 8 = 32 FAST64 jobs
```

Use these runs to separate:

```text
die-to-die mismatch variance
within-die temporal-noise variance
FAST64 record variance
```

## 15.5 Mandatory output from every dynamic job

```text
fundamental_dBFS
SNR_dB
SNDR_dB
ENOB_bit
SFDR_dBc
THD_dB
HD2_dBc
HD3_dBc
largest_spur_bin
largest_spur_frequency_Hz
noise_floor_dBFS_per_bin
DC_code_offset
mean_conversion_time_ns
max_conversion_time_ns
invalid_decision_count
timeout_count
clipping_count
missing_frame_count
duplicate_frame_count
```

Bulk jobs shall not save complete internal waveforms. Save only:

```text
64 retained output codes
valid/timeout/invalid flags
conversion time per frame
minimal provenance
```

Required outputs:

```text
csv/dynamic_mc200_fast64.csv
csv/dynamic_noise_repeat.csv
reports/dynamic_mc200_fast64.md
```

---

# 16. Phase I — FAST256 Dynamic Closure

FAST64 is the bulk estimator. A small FAST256 set provides the final dynamic reference.

## 16.1 Mandatory PVT cases

Use strict `maxstep=0.05 ns`:

```text
TT low-frequency FAST256
TT near-Nyquist FAST256
PVT_DYNAMIC_WORST low-frequency FAST256
PVT_DYNAMIC_WORST near-Nyquist FAST256
```

Recommended coherent settings:

```text
low frequency:
    N=256, k=29, fin=226.5625 kHz

near Nyquist:
    N=256, k=117, fin=914.0625 kHz
```

## 16.2 Monte Carlo tail cases

Also run FAST256 for:

```text
MC median seed
MC worst-SNDR seed
MC worst-SFDR seed
```

## 16.3 Closure gate

Because FAST64 and FAST256 may use close but not identical coherent frequencies, compare both absolute specifications and trends:

```text
all required FAST256 SNDR >= 44 dB
all required FAST256 ENOB >= 7.0 bit
no clipping, frame, invalid-decision, or timeout failure
FAST64-vs-FAST256 SNDR discrepancy <= 0.5 dB where directly comparable
FAST64-vs-FAST256 SFDR discrepancy <= 1.0 dB where directly comparable
principal spur mechanism and ordering consistent
```

If the gate fails, do not rerun all 200 dies. Upgrade only:

```text
P5-and-below SNDR cohort
boundary SFDR/THD cohort
```

to FAST128 or FAST256.

Required outputs:

```text
csv/dynamic_fast256_closure.csv
reports/dynamic_fast256_closure.md
```

---

# 17. Phase J — Minimum PVT × MC Interaction Closure

Do not run `200 seeds × 3 corners`.

Run only:

| Seed | Corner | Test |
|---|---|---|
| worst-DNL | PVT_STATIC_WORST_DNL | worst transition plus major carries |
| worst-INL | PVT_STATIC_WORST_INL | transitions around the INL extrema |
| worst-offset | PVT_STATIC_WORST_DNL | T1, T128, and T255 |
| worst-SNDR | PVT_DYNAMIC_WORST | FAST64 low-frequency and near-Nyquist |

If any case fails, expand only around the observed failure mechanism. Do not launch the full Cartesian matrix.

Required outputs:

```text
csv/pvt_mc_tail_replay.csv
reports/pvt_mc_interaction.md
```

---

# 18. FFT Calculation Contract

Use a one-sided power spectrum with consistent Parseval normalization.

Definitions:

```text
Pfund = fundamental-bin power
Pdc   = DC-bin power
Pharm = sum of folded harmonic-bin powers, excluding DC and fundamental
Pnoise= all remaining non-DC, non-fundamental, non-harmonic power
Perr  = all non-DC, non-fundamental power
Pspur = largest single non-DC, non-fundamental bin power
```

Metrics:

\[
SNR=10\log_{10}\frac{P_{fund}}{P_{noise}}
\]

\[
SNDR=10\log_{10}\frac{P_{fund}}{P_{err}}
\]

\[
THD=10\log_{10}\frac{P_{harm}}{P_{fund}}
\]

\[
SFDR=10\log_{10}\frac{P_{fund}}{P_{spur}}
\]

\[
ENOB=\frac{SNDR-1.76}{6.02}
\]

Requirements:

- Fold harmonics correctly into the first Nyquist zone.
- Do not count any FFT bin twice.
- Exclude DC from SNR and SNDR.
- Use zero-padding for display only, never for metric extraction.
- Label spectrum amplitude in `dBFS/bin`.
- Freeze and record the raw-code interpretation, code-to-voltage mapping, and full-scale definition.

---

# 19. Monte Carlo Statistical Contract

For every metric, report:

```text
count
mean
standard deviation
median
P1
P5
P10
P90
P95
P99
minimum
maximum
worst seed
95% bootstrap confidence interval
```

Use a binomial confidence interval for pass/fail statistics.

If all 200 samples pass, the only allowed wording is:

```text
0 failures observed in 200-run screening.
The one-sided 95% lower confidence bound on pass probability is approximately 98.5%.
```

Do not claim that 99.73% or 3-sigma production yield has been proven.

---

# 20. Formal Plotting Standards

## 20.1 DNL plot

```text
x-axis: Output Code
y-axis: DNL [LSB]
```

Requirements:

- Use exact full-transition data.
- Draw a 0 LSB reference line.
- Draw `+1 LSB` and `-1 LSB` specification lines.
- Mark maximum and minimum DNL and their code indices.
- Do not use spline interpolation or smoothing.
- Center the y-axis around zero and use symmetric limits.
- Use a major x-axis tick approximately every 32 codes.
- Include at least TT nominal and the exact worst-DNL seed in the formal report set.
- Plot a reconstructed MC envelope only after model-validation passes, and label it explicitly as reconstructed.

## 20.2 INL plot

```text
x-axis: Output Code
y-axis: INL [LSB]
```

Requirements:

- Use endpoint INL as the primary plot.
- Output best-fit INL separately.
- Draw a zero line and `±1.5 LSB` specification lines.
- Mark extrema and their code indices.
- Do not smooth.
- State the offset/gain-removal convention in the caption.

## 20.3 FFT spectrum plot

```text
x-axis: Frequency [MHz]
y-axis: Amplitude [dBFS/bin]
x-range: 0 to 1 MHz
```

Requirements:

- Display discrete FFT bins, not a fictitious smoothed continuous spectrum.
- Mark the fundamental, HD2, HD3, and largest spur.
- Recommended y-axis range: 0 to -90 or -100 dBFS.
- Include an information box containing:

```text
NFFT
Fs
fin
input amplitude and dBFS level
window
RBW
analog PVT
logic model
mismatch seed
noise seed
SNR
SNDR
ENOB
SFDR
THD
```

## 20.4 File formats and style

For every formal figure, generate:

```text
PDF or SVG vector file
PNG at 300 dpi
source CSV
```

Recommended style:

```text
axis labels: 9–10 pt
tick labels: 8–9 pt
line width: 1.0–1.5 pt
marker size: 2–3 pt
color-blind-safe palette
gray-scale distinguishable line styles
no 3D, gradients, or heavy background
```

Generate at least:

```text
plots/dnl_tt_nominal.pdf
plots/dnl_worst_exact_seed.pdf
plots/inl_endpoint_tt_nominal.pdf
plots/inl_endpoint_worst_exact_seed.pdf
plots/inl_bestfit_tt_nominal.pdf
plots/spectrum_fast64_nominal.pdf
plots/spectrum_fast64_worst_sndr.pdf
plots/spectrum_fast256_pvt_worst_near_nyquist.pdf
plots/mc_sndr_cdf.pdf
plots/mc_sfdr_cdf.pdf
```

---

# 21. Bulk Raw-Data and I/O Efficiency Rules

## 21.1 Bulk MC200

Save only:

```text
DOUT code at aperture
frame-valid flag
timeout/invalid flag
conversion time
minimal VFOP/VFON aperture sample if required
```

## 21.2 Tail, boundary, and failure cases

Save:

```text
full VFOP/VFON waveform
DCTRLP/N
DCMPP/DCMPN
local VREFP/VREFN
CLKS/CMPCK
supply or reference current when needed
```

## 21.3 Permanent retention

Permanently retain:

```text
all configuration files
seed tables
logs
summary CSV files
failure and tail raw data
plot-source CSV files
hash manifests
reports
```

Ordinary successful bulk raw data may be compressed or deleted after parsing, hashing, and audit completion.

---

# 22. Job-Scheduling Rules

- One mismatch seed shall run in one independent simulator process.
- Every job shall write to its own directory.
- Raw files shall never be shared across jobs.
- Random state shall not leak from one job to another.
- Run a five-job pilot to measure RAM and I/O before launching the full matrix.
- Limit concurrency by RAM and disk bandwidth, not by CPU-core count alone.
- Support checkpointing, resume, and failure-only reruns.
- Preserve the deck and log for every failed job.

Recommended command contract:

```bash
python scripts/audit_environment.py --config config/run_config.yaml
python scripts/make_seed_tables.py --config config/run_config.yaml
python scripts/make_job_matrix.py --phase all --config config/run_config.yaml
python scripts/run_jobs.py --workers 16 --resume jobs/job_matrix.csv
python scripts/aggregate_mc.py --config config/run_config.yaml
python scripts/select_tail_seeds.py --config config/run_config.yaml
python scripts/make_plots.py --config config/run_config.yaml
python scripts/make_master_report.py --config config/run_config.yaml
```

Arguments may be adjusted, but the final `README.md` shall record the exact commands, logs, and configuration used.

---

# 23. Mandatory Numerical Deliverables

## 23.1 Per-seed fields

```text
mismatch_seed
noise_seed
analog_pvt
logic_model
maxstep
startup_frames
static_frame

offset_LSB
gain
max_DNL_LSB / code
min_DNL_LSB / code
max_INL_EP_LSB / code
min_INL_EP_LSB / code
max_INL_BF_LSB / code
min_code_width_LSB
missing_code_count
max_hysteresis_LSB

fundamental_dBFS
SNR_dB
SNDR_dB
ENOB_bit
SFDR_dBc
THD_dB
HD2_dBc
HD3_dBc
largest_spur_frequency_Hz

mean_conversion_time_ns
max_conversion_time_ns
invalid_decision_count
timeout_count
clipping_count
missing_frame_count
duplicate_frame_count

pass_fail
evidence_tier
```

## 23.2 Master reports

```text
reports/00_executive_summary.md
reports/01_source_integrity.md
reports/02_model_and_fixture_audit.md
reports/03_numerical_convergence.md
reports/04_pvt_screen.md
reports/05_static_exact.md
reports/06_static_mc200.md
reports/07_noise_calibration.md
reports/08_dynamic_mc200_fast64.md
reports/09_fast256_closure.md
reports/10_pvt_mc_interaction.md
reports/11_plot_audit.md
reports/12_signoff_matrix.md
reports/MASTER_SIGNOFF_REPORT.md
```

---

# 24. Signoff Gates

Only after every gate passes may Codex output:

```text
PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200
```

## Gate A — Source and DUT

```text
production hashes unchanged
correct transistor-level analog core bound
actual SAR logic absent
TT behavioral SAR model present
R6 absent
source, reference, and interface loads explicitly defined
```

## Gate B — Behavioral control

```text
8 decisions
7 adjustments
correct code polarity
correct frozen switching sequence
atomic DOUT update
no deadlock
invalid and timeout detection active
TT timing provenance recorded
```

## Gate C — Numerical convergence

```text
bulk-versus-strict comparison within limits
final transition rounds use strict settings
startup-frame convergence passed
static-frame convergence passed
```

## Gate D — Nominal and PVT static performance

```text
TT full T1...T255 up/down complete
static-worst PVT full T1...T255 complete
DNL < ±1 LSB
INL_EP < ±1.5 LSB
no missing code
selected hysteresis <= 0.10 LSB, or triggered full reverse sweep passes
```

## Gate E — Static MC200

```text
200/200 packed jobs valid
200 transfers reconstructed
approved CDAC mismatch model used
8-seed exact-validation gate passed, or expanded 16-seed gate passed
all reconstructed boundary and failure seeds replayed exactly
no confirmed static specification failure
```

## Gate F — Noise

```text
comparator and sample noise calibrated
calibration error within limits
selected-transition probability completed
no unacceptable timeout or metastability behavior
```

## Gate G — Dynamic performance

```text
200/200 FAST64 jobs valid
SNDR >= 44 dB for all required claim-bearing cases
ENOB >= 7.0 bit for all required claim-bearing cases
no clipping
no missing or duplicate frame
no invalid decision or timeout
noise-repeat diagnostic completed
```

## Gate H — FAST256 and frequency coverage

```text
TT low-frequency and near-Nyquist FAST256 pass
PVT_DYNAMIC_WORST low-frequency and near-Nyquist FAST256 pass
MC median and worst-tail FAST256 pass
FAST64-to-FAST256 closure acceptable
```

## Gate I — Selected PVT × MC closure

```text
worst-DNL, worst-INL, worst-offset, and worst-SNDR tail replays pass
```

## Gate J — Evidence and reporting

```text
all configurations, seed lists, hashes, and logs present
DNL, INL, and spectrum figures pass format audit
claim boundary stated explicitly
no unsupported PEX, actual-logic, package, or production-yield claim
```

---

# 25. FAIL and BLOCKED Handling

## 25.1 FAIL statuses

Use when the circuit or measured performance violates a requirement:

```text
FAIL_DNL
FAIL_INL
FAIL_MISSING_CODE
FAIL_SNDR
FAIL_ENOB
FAIL_TIMEOUT
FAIL_INVALID_DECISION
FAIL_CLIPPING
FAIL_MODEL_VALIDATION
FAIL_FAST64_FAST256_CLOSURE
```

## 25.2 BLOCKED statuses

Use when required evidence, models, or execution resources are incomplete:

```text
BLOCKED_PRODUCTION_SOURCE_CHANGED
BLOCKED_TT_TIMING_EVIDENCE_MISSING
BLOCKED_SOURCE_IMPEDANCE_NOT_DEFINED
BLOCKED_CDAC_MISMATCH_MODEL_UNAVAILABLE
BLOCKED_NOISE_CALIBRATION_UNAVAILABLE
BLOCKED_PDK_MODEL_INVOCATION
BLOCKED_INSUFFICIENT_DISK_OR_RAM
```

Codex shall not convert `BLOCKED` into `FAIL`, and shall not convert `FAIL` into `PASS_WITH_REVIEW`.

---

# 26. Execution Order and Dependencies

```text
1. Source-hash and environment audit
2. DUT-binding and behavioral-contract smoke test
3. PDK/MOS/MIM/noise capability audit
4. Numerical, maxstep, static-frame, startup-frame, and runtime pilot
5. Analog-PVT packed-static and FAST64 screen
6. TT nominal exact full-static extraction
7. Static-worst PVT exact full-static extraction
8. Launch MC200 packed-static and MC200 FAST64 in parallel
9. Reconstruct MC200 transfers and select exact-validation seeds
10. Run 8-seed exact-static validation; expand only when required
11. Run comparator and sample-noise calibration
12. Run top-level selected-transition probability
13. Run the 4-die × 8-noise-seed diagnostic
14. Select dynamic tail seeds
15. Run FAST256 closure
16. Run selected PVT × MC tail closure
17. Aggregate, plot, audit, and issue the master report
```

Do not launch the full MC200 matrix before the model and numerical gates pass.

---

# 27. Estimated Completion Time

Assumptions:

```text
16 independent SPICE workers
64–128 GB RAM
local SSD
no R6 Heavy
bulk 0.10 ns gate passes
strict jobs use 0.05 ns
bulk minimal-save policy
automated job generation, resume, and post-processing are available
```

Estimated wall-clock time with parallel execution:

| Phase | Estimated wall-clock time |
|---|---:|
| Preflight and model audit | 2–4 h |
| Numerical and runtime pilot | 2–4 h |
| Analog-PVT screen | 1–3 h |
| MC200 packed static | 1–3 h |
| MC200 FAST64 | 6–12 h |
| TT plus worst-PVT exact static | 2–6 h |
| Eight-seed exact static validation | 4–8 h |
| Noise calibration and probability testing | 2–5 h |
| FAST256 closure | 2–5 h |
| PVT×MC tail tests | 1–3 h |
| Aggregation, plots, and reporting | 2–4 h |

Expected critical path:

```text
16 workers, normal pure simulation: 24–48 h
16 workers, complete end-to-end flow: 1.5–3 days
recommended project schedule: 3 calendar days
```

Conservative triggers:

```text
bulk simulations require 0.05 ns
DNL-worst and INL-worst PVT corners differ
eight-seed model validation expands to 16 seeds
FAST64/FAST256 closure fails and the boundary cohort expands
```

Conservative schedule:

```text
3–5 calendar days on 16 workers
```

After the five-job pilot, Codex shall update `reports/runtime_pilot.md` with a measured completion estimate and uncertainty range.

---

# 28. Mandatory Final Format of the Master Report

The end of `reports/MASTER_SIGNOFF_REPORT.md` shall use this structure:

```text
Final status:
    PASS / FAIL / BLOCKED

Pass label, if applicable:
    PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200

Scope:
    transistor-level sampler/CDAC/comparator
    fixed TT timed behavioral SAR control
    no R6 external RC fixture
    analog PVT
    MC200
    calibrated equivalent noise
    FAST64 bulk + FAST256 closure

Explicit non-claims:
    no actual-SAR-logic signoff
    no PEX/layout/package signoff
    no production-yield proof
    no tapeout-readiness claim

Open risks:
    list every remaining risk; write NONE only when no risk remains inside the stated scope
```

---

# 29. Methodological References

The methodology in this plan is based on these project sources and engineering principles:

- `current_goal.md`: A44 frozen specifications, static/dynamic targets, and verification hierarchy;
- `try_PERFORMANCE.txt`: capabilities and limitations of the previous Fast32, sparse-static, four-mismatch-seed, and equivalent-noise campaign;
- the uploaded measurement-definition discussion file: full-transition search, ramp correlation, selected-transition probability, fixed-virtual-die Monte Carlo, and endpoint/best-fit INL;
- Behzad Razavi, *Analysis and Design of Data Converters*: ADC static and dynamic metrics, SAR nonidealities, comparator noise and offset, and CDAC mismatch;
- A23 OnChipSAR schematic review: low-cost dynamic testing near `Fs/10` and a 64-point FFT example;
- Peter Kinget, *Design Databases and More*: source integrity, simulation configuration, scheduling, and evidence-traceability discipline.

---

# 30. Codex Definition of Done

Codex may terminate the task only after every required artifact exists:

```text
complete source-integrity manifest
frozen configurations and seed lists
all mandatory numerical CSV files
all required DNL, INL, and FFT plots in vector, PNG, and CSV form
all phase reports
master signoff matrix
MASTER_SIGNOFF_REPORT.md
machine-readable final_status.json
```

Example `final_status.json`:

```json
{
  "status": "PASS",
  "label": "PASS_AS_SCHEMATIC_ANALOG_CORE_SIGNOFF_WITH_TIMED_BEHAVIORAL_SAR_CONTROL_MC200",
  "scope": "TT-timed behavioral SAR control; transistor-level analog core; no R6",
  "mc_samples": 200,
  "bulk_fft": 64,
  "closure_fft": 256,
  "actual_sar_logic_signoff": false,
  "pex_signoff": false,
  "production_yield_proven": false
}
```
