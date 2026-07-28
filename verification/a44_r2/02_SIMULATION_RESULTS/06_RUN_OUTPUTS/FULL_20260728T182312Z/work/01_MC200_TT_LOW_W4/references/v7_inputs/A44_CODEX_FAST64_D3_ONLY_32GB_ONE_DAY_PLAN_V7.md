# A44 SAR ADC — Codex FAST64 Dynamic D3-Only Measurement Plan — 32-GB / One-Day Profile

**Document ID:** `A44_CODEX_FAST64_D3_ONLY_32GB_ONE_DAY_PLAN_V7`  
**Supersedes for this campaign:** `A44_CODEX_FAST64_DYNAMIC_ONLY_32GB_ONE_DAY_PLAN_V6`  
**Scope:** dynamic performance only, **D3 only**  
**Primary DUT lane:** transistor-level sampler + differential CDACs + StrongARM comparator + fixed TT timed-behavioral SAR controller, No-R6  
**Formal electrical matrix:** `NOISE + MC200 mismatch` only  
**Dynamic method:** `FAST64` only  
**Evidence class:** `FAST64_D3_ONLY_MC200_MODEL_CONDITIONAL`

---

## 0. Executive directive

Codex shall execute one fixed formal dynamic matrix only:

```text
D3  MC200 mismatch ON + qualified temporal noise ON
```

No formal D0, D1, or D2 campaign is included in this version.

Every formal FAST64 record shall measure and report at least:

```text
SNR
SNDR
ENOB_raw
SFDR
THD
HD2
HD3
fundamental amplitude
largest spur
DC code offset
mean/max conversion time
frame/protocol integrity flags
```

Non-negotiable execution rules:

```text
1. Do not run static DNL, INL, offset, ramp, transition-search, or histogram jobs.
2. Do not run FAST32, FAST128, or FAST256.
3. Do not run D0, D1, or D2 as formal categories.
4. Do not add result-triggered P95 replay, tail upgrade, or extra corners.
5. Do not stop the campaign after a performance failure.
6. Complete all 200 mismatch dies in both LOW and NEAR_NYQUIST bands.
7. Use the same frozen mismatch realization and the frozen per-die noise sequence for both bands of a die.
8. Retry only infrastructure failures; never retry a valid performance FAIL.
9. Never remove invalid, aborted, or unresolved required jobs from the denominator.
10. Preserve source, model, configuration, seed, analyzer, and result hashes.
```

### 0.1 Meaning of this D3-only campaign

This campaign measures only the combined case:

```text
mismatch ON
qualified temporal noise ON
```

It does **not** attempt, in this version, to decompose the result into mismatch-only or noise-only contributions. It is a **formal MC200 combined dynamic population run**.

---

## 1. Frozen system conditions

```text
Resolution                  = 8 bit
Sampling rate               = 2 MS/s
Frame period                = 500 ns
Nominal supply              = 3.3 V
Input common-mode           = 1.65 V
VREFP / VREFN               = 2.50 V / 0.80 V
Nominal full scale          = 3.4 Vpp,diff
Dynamic input               = 3.0 Vpp,diff
Output code                 = 8-bit straight binary
DOUT measurement aperture   = frame start + 480 ns
```

Dynamic input waveform:

```text
VINP = 1.65 V + 0.75 V * sin(2*pi*fin*t + phase)
VINN = 1.65 V - 0.75 V * sin(2*pi*fin*t + phase)
VID  = 3.0 Vpp,diff
```

The input is approximately `-1.09 dBFS` relative to `3.4 Vpp,diff`. `ENOB_raw` shall not be corrected for this backoff.

---

## 2. Frozen numerical and FAST64 parameters

### 2.1 Parameters that shall not be rescanned

When the qualification-cache hash remains valid, reuse these frozen values directly:

```text
frame period          = 500 ns
startup frames        = 0
DOUT aperture         = 480 ns
bulk maxstep          = 0.10 ns
strict maxstep        = 0.05 ns
FFT length            = 64
FFT window            = rectangular
input phase           = pi/4
input amplitude       = 3.0 Vpp,diff
```

Do not repeat:

```text
frame-length search
startup-frame search
DOUT-aperture search
phase search
FFT-length comparison
maxstep sweep
```

### 2.2 FAST64 bands

| Band | NFFT | Coherent bin | Input frequency | Distinct input phases |
|---|---:|---:|---:|---:|
| `LOW` | 64 | 7 | 218.75 kHz | 64 |
| `NEAR_NYQUIST` | 64 | 29 | 906.25 kHz | 64 |

Both coherent bins are coprime with 64.

### 2.3 Numerical profile

```text
Formal population jobs:
    maxstep = 0.10 ns, only if the numerical qualification-cache hash is valid

Qualification / fallback:
    maxstep = 0.05 ns
```

If the cache is invalid, run the fixed pilot in Section 8. If the `0.10 ns` profile does not reproduce the `0.05 ns` code streams and metrics within tolerance, all formal jobs shall use `0.05 ns`. Do not search another maxstep.

### 2.4 Qualified noise model

Noise-on results are formal only when the frozen noise-model qualification hash is valid:

```text
sample-noise sigma        = 64.681 uVrms,diff
comparator-noise sigma    = 1.500 mVrms,diff
sample draw ownership     = one draw per conversion frame
comparator draw ownership = one draw per SAR decision
```

If the noise model is not qualified, stop before the formal campaign and emit:

```text
BLOCKED_NOISE_MODEL_NOT_QUALIFIED
```

---

## 3. Dynamic metric definitions

### 3.1 Required linear-power primitives

For every record, the analyzer shall save:

```text
Pfund_linear
Pnoise_linear
Pharm_linear
Perror_linear
Pspur_max_linear
```

Use one verified one-sided FFT normalization with a Parseval consistency check. DC is excluded from all AC metrics.

### 3.2 Harmonic-bin treatment

Use harmonics `h = 2...5`.

For each harmonic:

```text
raw_bin    = (h * fundamental_bin) mod NFFT
folded_bin = raw_bin,                    if raw_bin <= NFFT/2
             NFFT - raw_bin,             otherwise
```

Then:

```text
remove DC bin
remove the fundamental bin
remove duplicate folded harmonic bins
```

The same harmonic-folding function and hash shall be used for LOW and NEAR.

### 3.3 SNR

Noise power excludes DC, the fundamental, and the declared harmonic bins:

\[
SNR=10\log_{10}\left(\frac{P_{fund}}{P_{noise}}\right)
\]

SNR is mandatory for every record and every summary table.

### 3.4 SNDR and ENOB

\[
SNDR=10\log_{10}\left(\frac{P_{fund}}{P_{error}}\right)
\]

where:

\[
P_{error}=P_{noise}+P_{harm}
\]

and:

\[
ENOB_{raw}=\frac{SNDR-1.76}{6.02}
\]

### 3.5 THD and SFDR

\[
THD=10\log_{10}\left(\frac{P_{harm}}{P_{fund}}\right)
\]

`SFDR` is the ratio of the fundamental to the largest non-DC, non-fundamental spectral bin.

### 3.6 Dynamic targets and result classes

Hard project dynamic gate:

```text
SNDR       >= 46.91 dB
ENOB_raw   >= 7.50 bit
valid      = 64 / 64 frames
clipping   = 0
invalid    = 0
timeout    = 0
missing    = 0
duplicate  = 0
```

SNR/nonideality budget target:

```text
SNR >= 48.14 dB
```

Preferred nominal target:

```text
SNR       >= 48.14 dB
SNDR      >= 47.75 dB
ENOB_raw  >= 7.64 bit
```

Every record shall therefore have separate fields:

```text
hard_dynamic_pass
snr_budget_pass
preferred_nominal_pass
```

---

## 4. Formal dynamic measurement matrix — D3 only

At TT:

```text
mismatch seed i = virtual die i
noise seed      = 100000 + i
```

Per die:

```text
LOW FAST64
NEAR_NYQUIST FAST64
```

Total formal population:

```text
200 dual-band electrical cases
400 FAST64 records
```

For each die define:

```text
SNR_WORST_BAND  = min(SNR_LOW,  SNR_NEAR)
SNDR_WORST_BAND = min(SNDR_LOW, SNDR_NEAR)
ENOB_WORST_BAND = min(ENOB_LOW, ENOB_NEAR)
```

A die passes the hard dynamic gate only when both bands pass:

```text
LOW:
    SNDR >= 46.91 dB
    ENOB_raw >= 7.50 bit
    protocol/frame flags clean

NEAR_NYQUIST:
    SNDR >= 46.91 dB
    ENOB_raw >= 7.50 bit
    protocol/frame flags clean
```

Population acceptance:

```text
required valid dies    = 200
minimum passing dies   = 190
observed pass rate     >= 95%
```

Also report, separately:

```text
SNR budget pass count at 48.14 dB
LOW SNR pass count
NEAR SNR pass count
worst-band SNR pass count
```

Do not describe `190/200` as proof of production yield. Report the exact binomial confidence interval separately.

---

## 5. Low-memory ngspice session design

### 5.1 Sequential-record rule

A parsed ngspice session may retain only one FAST64 record in memory at a time.

For every record:

```text
1. run 64 conversion frames;
2. sample and write the 64 DOUT codes;
3. write protocol and conversion-time scalars;
4. compute or save the linear FFT power primitives;
5. checksum the compact output;
6. destroy all transient vectors;
7. reset deterministic state;
8. load the next frozen stimulus/noise sequence.
```

Do not retain a continuous multi-record raw database in RAM.

### 5.2 Approved session type

```text
D3_DUAL_BAND_SESSION for die i:
    D3 noise+mismatch LOW
    D3 noise+mismatch NEAR
```

One die corresponds to one parsed session.

### 5.3 Session-equivalence qualification

Before the main population, compare sequential-session and separate-process execution for:

```text
mismatch seed 1
mismatch seed 44
```

Acceptance:

```text
64/64 output codes identical for every record
all protocol/frame flags identical
|delta SNR|  <= 0.01 dB
|delta SNDR| <= 0.01 dB
|delta ENOB| <= 0.002 bit
mismatch checksum identical
noise-draw checksum identical to the frozen manifest
```

If equivalence fails, use separate processes. Do not change the electrical matrix.

---

## 6. 32-GB memory scheduler

### 6.1 Memory budget

```text
Physical RAM                         = 32 GB
OS and filesystem-cache reserve      = 7 GB
Python / manifest / aggregation      = 2 GB
Global ngspice RSS token budget      = 22 GB
Unallocated safety                   = 1 GB
Swap as a throughput mechanism       = prohibited
```

### 6.2 RSS-token calculation

The fixed pilot shall measure peak RSS (`VmHWM`) for:

```text
one D3 dual-band session
one compact post-processing batch
```

For the simulator class:

\[
TOKEN_{job}=\left\lceil\frac{1.25\,RSS_{P95,job}}{0.5\ \mathrm{GB}}\right\rceil
\]

The scheduler shall launch a session only when enough 0.5-GB tokens are free.

### 6.3 Dynamic-only concurrency profiles

| Profile | Concurrent dynamic sessions | Admission condition |
|---|---:|---|
| `MINIMUM_32G` | 2 | use only when session RSS is high |
| `SAFE_32G` | 3 | conservative default fallback |
| `BASELINE_32G` | 4 | recommended default |
| `FAST_32G` | 5 | pilot total, including 25% margin, <=22 GB |
| `MAX_32G` | 6 | allowed only with measured RSS and no swap growth |

Useful RSS limits after the 25% margin are approximately:

```text
4 sessions require raw P95 RSS <= 4.40 GB/session
5 sessions require raw P95 RSS <= 3.52 GB/session
6 sessions require raw P95 RSS <= 2.93 GB/session
```

### 6.4 Runtime-protection rules

Pause new submissions when any condition occurs:

```text
MemAvailable < 5 GB
swap used > 512 MB
major page-fault rate rises continuously for 60 s
active output-path latency exceeds 2x the pilot P95
```

Resume only after memory and I/O return to the safe region.

All workers shall be single-threaded unless the pilot proves a lower-RSS alternative:

```bash
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

---

## 7. Netlist, storage, and post-processing efficiency

### 7.1 Base-netlist reuse

Generate one structural base netlist per dependency hash. Per-session includes shall contain only:

```text
PVT selection
mismatch seed or explicit mismatch parameter include
noise-sequence include
LOW/NEAR stimulus selector
output path
```

Do not invoke Xschem or regenerate the complete hierarchy for each die.

### 7.2 Compact-save population mode

For ordinary D3 records, save only:

```text
64 DOUT codes
conversion-complete and protocol flags
mean/max conversion time
Pfund / Pnoise / Pharm / Perror
metric and seed metadata
```

Do not save all transistor-level internal nodes for the 200-die population.

Fixed full-waveform audit records:

```text
seed 1 LOW
seed 1 NEAR
seed 44 LOW
seed 44 NEAR
seed corresponding to median worst-band SNDR
seed corresponding to worst observed worst-band SNDR
```

These audit records do not alter population counts.

### 7.3 Raw-file policy

```text
active raw directory = local SSD/NVMe, never tmpfs
ordinary raw file    = delete after compact-output checksum passes
formal compact CSV   = retain
plot source CSV      = retain
```

### 7.4 Streaming analysis

```text
FFT per record        = immediately after code extraction
population aggregate  = append-only / chunked
plot generation       = one worker after simulator load decreases
```

The final report must be reproducible from compact code and metric tables without reopening population raw files.

---

## 8. Qualification cache and fixed-parameter efficiency

### 8.1 Dependency hash

The qualification cache key shall include:

```text
production analog netlist hash
PDK/model hash
behavioral-SAR/controller hash
noise-adapter hash
testbench-template hash
FFT/analyzer hash
ngspice version
solver-profile hash
```

### 8.2 Reuse policy

If the cache key is unchanged, do not repeat:

```text
frame-length search
startup-frame search
DOUT-aperture search
input-phase search
FFT-length comparison
maxstep sweep
noise-model amplitude/timing qualification
session-equivalence qualification
```

### 8.3 Fixed pilot when the cache is invalid

Run only this fixed pilot:

```text
P0  D3 dual-band session for mismatch seed 1 at 0.10 ns
P1  the same D3 dual-band session for mismatch seed 1 at 0.05 ns
P2  D3 dual-band session for mismatch seed 44 at 0.10 ns
P3  D3 dual-band session for mismatch seed 44 at 0.05 ns
```

Numerical acceptance:

```text
0.10-ns and 0.05-ns code streams identical for both bands
all flags identical
|delta SNR|  <= 0.01 dB
|delta SNDR| <= 0.01 dB
|delta ENOB| <= 0.002 bit
```

If the pilot fails, use `0.05 ns` for the formal matrix. Do not search additional values.

---

## 9. Formal workload

| Category | Electrical cases | FAST64 records | Preferred parsed sessions |
|---|---:|---:|---:|
| D3 noise+mismatch MC200 | 200 dual-band | 400 | 200 |
| **Total** | **200 dual-band-equivalent cases** | **400 records** | **200 main sessions** |

Qualification records are outside the formal population and shall be reported separately.

---

## 10. Required output files

Recommended directory structure:

```text
A44_FAST64_D3_ONLY_MC200_V7/
├── config/
│   ├── frozen_dynamic_config.yaml
│   ├── dependency_hashes.json
│   └── qualification_cache.json
├── manifests/
│   ├── mismatch_seed_manifest.csv
│   ├── noise_seed_manifest.csv
│   └── job_matrix.csv
├── csv/
│   ├── dynamic_master.csv
│   ├── d3_combined_summary.csv
│   ├── population_percentiles.csv
│   └── representative_spectra_manifest.csv
├── plots/
├── reports/
│   └── FINAL_FAST64_DYNAMIC_REPORT.md
└── results/
    └── final_status.json
```

### 10.1 Dynamic master table

```csv
category,pvt,mismatch_seed,noise_seed,band,nfft,bin,fin_hz,phase_rad,input_vpp_diff,maxstep_ns,pfund_linear,pnoise_linear,pharm_linear,perror_linear,fundamental_dbfs,snr_db,sndr_db,enob_raw,sfdr_dbc,thd_db,hd2_dbc,hd3_dbc,largest_spur_bin,largest_spur_hz,noise_floor_dbfs_per_bin,dc_code_offset,mean_conversion_time_ns,max_conversion_time_ns,invalid_count,timeout_count,clipping_count,missing_frame_count,duplicate_frame_count,valid_frame_count,hard_dynamic_pass,snr_budget_pass,preferred_nominal_pass,status
```

### 10.2 Population summary

For D3, report separately for LOW, NEAR, and WORST_BAND:

```text
valid count
hard pass count / fail count
SNR-budget pass count / fail count
mean
standard deviation
P1
P5
P10
P50
P90
P95
P99
worst observed value
worst seed
exact binomial interval for the hard pass rate
```

---

## 11. Standardized plots

Every formal figure shall be delivered as:

```text
vector PDF or SVG
300-dpi PNG
source CSV
```

No smoothing or spline interpolation is allowed.

### 11.1 Spectrum plot style — required format

All representative FFT spectra shall follow a unified presentation style modeled on the reference image supplied in the chat.

#### Canvas and typography

```text
single-axes figure only
recommended size      = 10.0 in × 6.2 in
background            = light gray figure background
axes background       = light gray or near-light-gray
font family           = serif (Times New Roman preferred; fallback DejaVu Serif)
title                 = optional, compact, not required inside the axes
```

#### Curve style

```text
plot type             = line plot connecting one-sided FFT bins
line color            = blue
line width            = 2.0 pt
markers               = none
smoothing             = forbidden
```

#### Axes and grid

```text
x-axis label          = Frequency (Hz)
y-axis label          = Magnitude (dB)
x-axis range          = 0 ... Fs/2 = 0 ... 1.0 MHz
major x ticks         = 0, 250 kHz, 500 kHz, 750 kHz, 1.0 MHz
major y ticks         = 10 dB spacing
recommended y range   = -100 dB ... +10 dB
grid                  = major grid only, light-gray dotted lines
spines                = black
```

If a particular record contains bins below `-100 dB`, the y-axis may be extended downward in 10-dB steps, but the upper limit shall remain `+10 dB`.

#### Annotation box

Place one metrics box inside the top-right corner of the axes.

Required style:

```text
box facecolor       = white
box edgecolor       = black
box line width      = 1.5 pt
text alignment      = left
```

Required contents, one line each:

```text
SNR  = xx.xx dB
SNDR = xx.xx dB
ENOB = xx.xx bits
SFDR = xx.xx dB
```

Optional fifth line:

```text
THD  = xx.xx dB
```

Do not omit `SNR`; it is mandatory in this V7 campaign.

#### Spectrum source CSV

For every plotted spectrum, save a source CSV with at least:

```csv
freq_hz,magnitude_db,is_fundamental,is_hd2,is_hd3,is_largest_spur
```

### 11.2 Required representative spectra

Generate at least these spectra:

```text
LOW:
    P50 worst-band SNDR die
    best passing die nearest the SNDR hard threshold
    failing die nearest the SNDR hard threshold, if any
    worst observed die

NEAR_NYQUIST:
    P50 worst-band SNDR die
    best passing die nearest the SNDR hard threshold
    failing die nearest the SNDR hard threshold, if any
    worst observed die
```

If no failing die exists in a band, replace the “failing die nearest threshold” spectrum with the worst passing die.

### 11.3 Population plots

For D3, separately for LOW, NEAR, and WORST_BAND:

```text
SNR histogram
SNR empirical CDF
SNDR histogram
SNDR empirical CDF
ENOB histogram
ENOB empirical CDF
seed-by-seed SNR
seed-by-seed SNDR
hard pass/fail map
SNR-budget pass/fail map
```

Reference lines:

```text
SNR  = 48.14 dB
SNDR = 46.91 dB
SNDR = 47.75 dB preferred nominal
ENOB = 7.50 bit
ENOB = 7.64 bit preferred nominal
```

---

## 12. Completion and status rules

### 12.1 Complete campaign

A campaign is complete only when:

```text
200/200 D3 dies terminal
all 400 required FAST64 records valid or explicitly unresolved
all required compact tables generated
all required plots generated
final report and status JSON generated
```

### 12.2 Job states

```text
VALID_PASS
VALID_FAIL
SIM_ERROR_RETRYABLE
SIM_ERROR_UNRESOLVED
MODEL_BLOCKED
MEASUREMENT_BLOCKED
```

A valid performance FAIL is terminal and shall not be retried.

### 12.3 Campaign status

```text
PASS_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95
FAIL_PROJECT_DEFINED_FAST64_DYNAMIC_MC200_95
BLOCKED_INCOMPLETE_DYNAMIC_POPULATION
BLOCKED_NOISE_MODEL_NOT_QUALIFIED
BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED
BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION
```

Recommended complete claim string:

```text
FAST64_DYNAMIC_ONLY
D3_NOISE_PLUS_MISMATCH_MC200
WITH_FIXED_TT_TIMED_BEHAVIORAL_SAR
NO_R6
MODEL_CONDITIONAL
```

This campaign does not claim:

```text
static DNL/INL/offset characterization
noise-only or mismatch-only decomposition
FAST128/FAST256 long-record closure
actual self-timed SAR full-IP closure
PEX/layout signoff
package/PCB performance
silicon production yield
```

---

## 13. 32-GB runtime estimate

### 13.1 Historical measured basis

The archived noncached single-band FAST64 jobs have approximately:

```text
median runtime = 95.42 s/record
P95 runtime    = 144.58 s/record
```

For 400 formal FAST64 records:

```text
median-based dynamic core time = 10.60 core-hours
P95-based dynamic core budget  = 16.06 core-hours
```

### 13.2 Wall-time estimate

Add `1.0...2.0 h` for the fixed pilot, process-launch overhead, ordinary infrastructure retry, streaming aggregation, and standardized plots.

| Concurrent sessions | Median record bound | P95 record bound | Practical total estimate |
|---:|---:|---:|---:|
| 2 | 5.3 h | 8.0 h | **6.5...10.5 h** |
| 3 | 3.5 h | 5.4 h | **5.0...8.0 h** |
| 4 | 2.7 h | 4.0 h | **4.0...6.5 h** |
| 5 | 2.1 h | 3.2 h | **3.5...5.5 h** |
| 6 | 1.8 h | 2.7 h | **3.0...5.0 h** |

Recommended default:

```text
BASELINE_32G = 4 concurrent dynamic sessions
```

Expected completion:

```text
valid 0.10-ns qualification cache: approximately 4...6.5 h
all formal records forced to 0.05 ns: approximately 7...12 h with four sessions
```

### 13.3 One-day admission gate

Before the formal population, use measured pilot values to calculate:

\[
T_{projected}=\frac{400\,t_{record,P95}}{N_{sessions}}+T_{overhead}
\]

Require:

```text
T_projected <= 24 h
measured session RSS with 25% margin <=22 GB token budget
no swap growth during a 20-minute mixed-load pilot
local SSD/NVMe active output path
```

If the gate fails, do not silently delete measurements. Emit:

```text
BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION
```

---

## 14. Frozen configuration template

```yaml
campaign:
  id: A44_CODEX_FAST64_D3_ONLY_32GB_ONE_DAY_PLAN_V7
  dynamic_only: true
  performance_early_stop: false
  formal_categories: [D3_ONLY]
  dynamic_method: FAST64_ONLY
  primary_lane: TT_TIMED_BEHAVIORAL_SAR_NO_R6
  evidence_class: MODEL_CONDITIONAL

system:
  resolution_bit: 8
  sample_rate_hz: 2000000
  frame_period_ns: 500
  startup_frames: 0
  dout_aperture_ns: 480
  vcm_v: 1.65
  vrefp_v: 2.50
  vrefn_v: 0.80
  nominal_full_scale_vpp_diff: 3.4
  input_vpp_diff: 3.0
  input_phase_rad: 0.7853981633974483

numerical:
  formal_maxstep_ns_if_cache_valid: 0.10
  strict_maxstep_ns: 0.05
  rescan_frame: false
  rescan_startup: false
  rescan_aperture: false
  rescan_phase: false
  rescan_fft_length: false

fast64:
  nfft: 64
  window: rectangular
  bands:
    LOW: {bin: 7, fin_hz: 218750}
    NEAR_NYQUIST: {bin: 29, fin_hz: 906250}
  harmonics: [2, 3, 4, 5]
  require_parseval_check: true

noise_model:
  sample_sigma_v_rms_diff: 0.000064681
  comparator_sigma_v_rms_diff: 0.0015
  sample_draws_per_frame: 1
  comparator_draws_per_decision: 1
  qualification_required: true

matrix:
  D3:
    category: NOISE_PLUS_MISMATCH_MC200
    pvt: TT_3P3_27C
    mismatch_seeds: 200
    noise_seed_rule: 100000_plus_mismatch_seed

metrics:
  mandatory:
    - SNR
    - SNDR
    - ENOB_RAW
    - SFDR
    - THD
    - HD2
    - HD3
  snr_budget_target_db: 48.14
  sndr_hard_min_db: 46.91
  enob_raw_hard_min_bit: 7.50
  sndr_preferred_nominal_db: 47.75
  enob_raw_preferred_nominal_bit: 7.64

acceptance:
  D3_required_valid_dies: 200
  D3_minimum_pass_count: 190
  D3_minimum_observed_pass_rate: 0.95
  require_both_bands: true
  require_clean_protocol_flags: true
  snr_budget_is_separate_gate: true

session_mode:
  enabled: true
  destroy_vectors_after_each_record: true
  one_die_per_parsed_session: true
  require_session_equivalence: true

memory_32gb:
  physical_ram_gb: 32
  ngspice_token_budget_gb: 22
  os_cache_reserve_gb: 7
  python_reserve_gb: 2
  safety_gb: 1
  token_quantum_gb: 0.5
  token_rss_margin: 1.25
  default_dynamic_sessions: 4
  safe_dynamic_sessions: 3
  fast_dynamic_sessions: 5
  memavailable_pause_gb: 5
  swap_pause_mb: 512
  threads_per_process: 1

storage:
  compact_population_output: true
  save_all_internal_nodes: false
  active_path_must_be_local_ssd: true
  use_tmpfs: false
  delete_ordinary_raw_after_checksum: true
  streaming_postprocess: true

completion:
  no_failed_job_dropping: true
  no_performance_retry: true
  infrastructure_retry_max: 1
  unresolved_required_job_means_blocked: true
```

---

## 15. Final Codex checklist

```text
[ ] Dependency hashes generated
[ ] Qualification cache accepted or fixed pilot completed
[ ] FAST64 analyzer Parseval and harmonic-folding checks passed
[ ] SNR is present in every dynamic record and every summary
[ ] 32-GB RSS pilot completed
[ ] Session-equivalence checks passed or fallback documented
[ ] D3 200/200 dies complete
[ ] All 400 formal FAST64 records accounted for
[ ] D3 hard pass count and SNR-budget pass count reported separately
[ ] Dynamic master schema validated
[ ] Standardized PDF/SVG, PNG, and source-CSV plots generated
[ ] FFT spectra match the required reference-image style
[ ] Final status is PASS, FAIL, or BLOCKED
[ ] Claim boundary states FAST64-only and model-conditional evidence
```
