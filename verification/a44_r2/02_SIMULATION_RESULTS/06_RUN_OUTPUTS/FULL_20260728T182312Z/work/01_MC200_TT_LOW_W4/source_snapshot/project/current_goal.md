# Current Goal - Chipathon 2026 8-bit Fully Differential Asynchronous SAR ADC

> **Source of truth for Codex and project implementation.**
> Treat the items marked **Frozen** as architectural requirements. Do not change them unless the user explicitly revises this file.

## 1. Project objective

Design, simulate, lay out, and integrate an **8-bit, 2-MS/s, 3.3-V fully differential capacitive SAR ADC** in the **GF180MCU** process for the Chipathon 2026 `workshop` padring slot.

The ADC shall use:

- top-plate sampling;
- two-level bi-directional CDAC switching;
- a StrongARM dynamic comparator;
- a fully self-timed asynchronous SAR controller;
- one external functional clock, `CLKS`.

The completed ADC must satisfy the dynamic and static performance targets in this document at schematic level and after parasitic extraction.

---

## 2. Frozen system specifications

| Item | Requirement |
|---|---:|
| Process | GF180MCU |
| Resolution | 8 bit |
| Nominal sample rate | 2 MS/s |
| Sample period | 500 ns |
| Analog/digital nominal supply | 3.3 V |
| Input type | Fully differential |
| Input common-mode | `VCM = 1.65 V` |
| Nominal differential full-scale range | `VFS_NOM = 3.4 Vpp,diff` |
| Standard dynamic-test input | `3.0 Vpp,diff` |
| Reference high | `VREFP = 2.50 V` |
| Reference low | `VREFN = 0.80 V` |
| Output code | 8-bit straight binary |
| SNDR | `>= 44 dB` |
| ENOB | `>= 7.0 bit` |
| DNL | `< +/-1 LSB` |
| INL | `< +/-1.5 LSB` |
| Missing codes | None |

Definitions:

```text
VID  = VINP - VINN
VICM = (VINP + VINN) / 2
```

The nominal differential quantization range is:

```text
-1.70 V <= VID <= +1.70 V
```

The nominal differential LSB is:

```text
LSB_NOM = 3.4 V / 256 = 13.28125 mV,diff
```

The standard FFT/SNDR input is:

```text
VINP = 1.65 V + 0.75 V * sin(2*pi*fin*t)
VINN = 1.65 V - 0.75 V * sin(2*pi*fin*t)
```

This produces:

```text
VID = 3.0 Vpp,diff
VINP, VINN range = 0.90 V to 2.40 V
Input level = -1.09 dBFS relative to 3.4 Vpp,diff
```

---

## 3. Frozen top-level architecture

```text
                          +----------------------+
VINP -------------------> | P-side 8-bit CDAC    | ---- VFOP ----+
CLKS -------------------> | top-plate sampled    |                |
DCTRLP[7:1] ------------> | bi-directional       |                v
                          +----------------------+          StrongARM
                                                           comparator
                          +----------------------+                |
VINN -------------------> | N-side 8-bit CDAC    |                |
CLKS -------------------> | top-plate sampled    | ---- VFON ----+
DCTRLN[7:1] ------------> | bi-directional       |
                          +----------------------+
                                                                    |
                                                             DCMPP/DCMPN
                                                                    |
                                                                    v
                                                    Asynchronous SAR logic
                                                    - VALID generation
                                                    - internal CMPCK
                                                    - CLK_BIT[7:0]
                                                    - DCTRLP[7:1]
                                                    - DCTRLN[7:1]
                                                    - EOC_INT
                                                    - DOUT[7:0]
```

The normal ADC architecture shall not use an external SAR clock. `CLKS` is the only required external functional clock.

---

## 4. Frozen external functional interface

### 4.1 Required top-level signals

| Signal | Direction | Width/value | Function |
|---|---|---:|---|
| `VDD` | input | 3.3 V | Functional ADC supply in schematic hierarchy |
| `GND` | input | 0 V | Functional ADC ground in schematic hierarchy |
| `VREFP` | analog input | 2.50 V | CDAC high reference |
| `VREFN` | analog input | 0.80 V | CDAC low reference |
| `VINP` | analog input | differential | Positive analog input |
| `VINN` | analog input | differential | Negative analog input |
| `CLKS` | digital input | 2 MHz nominal | Sampling-frame clock and conversion-start control |
| `DOUT[7:0]` | digital output | 8 bit | Straight-binary conversion result |

### 4.2 Signals that are not part of the normal external interface

Do not add the following as required normal-operation pins:

```text
CLKC
SAR_CLK
CONVST
READY
VCM
```

Internal-only signals include:

```text
CMPCK
VALID
CLK_BIT[7:0]
EOC_INT
DCTRLP[7:1]
DCTRLN[7:1]
VFOP
VFON
DCMPP
DCMPN
```

An optional test-only reset or comparator-clock override may be retained for first-silicon debug, but normal conversion must not depend on it.

### 4.3 Output-valid convention

There is no external `READY` pin in the frozen interface.

- Internal SAR decisions may update during conversion.
- External `DOUT[7:0]` shall be driven by a separate output register.
- The output register shall update atomically at `EOC_INT`.
- `DOUT[7:0]` shall retain the previous complete result throughout the next conversion.
- The new code must be stable before the following `CLKS` rising edge.

The ideal code polarity is:

```text
VID increases  => DOUT increases
negative full scale => approximately 8'h00
zero differential  => approximately 8'h80
positive full scale => approximately 8'hFF
```

---

## 5. Sampling-clock behavior

`CLKS` is the only normal external clock.

```text
CLKS = 1:
    Track/sample VINP and VINN.
    Reset asynchronous conversion-progress state.
    Initialize CDAC bottom-plate controls.
    Force CMPCK low.
    Keep the StrongARM in reset/precharge.
    Keep external DOUT at the previous completed code.

CLKS falling edge:
    End sampling.
    Enter hold.
    After a non-overlap/start guard delay, start the first comparison.

CLKS = 0:
    Perform eight self-timed comparisons.
    Perform seven CDAC adjustments.
    Generate EOC_INT.
    Update the external output register.
```

Initial timing allocation:

```text
Track/acquisition target: 100 ns to 125 ns
Conversion target:        375 ns to 400 ns
Total sample period:      500 ns
```

The exact duty cycle is not frozen and shall be selected from transistor-level and post-layout settling simulations.

If conversion has not completed when the next sampling phase begins, the circuit shall force the asynchronous loop into reset, restore the sampling initial state, discard the incomplete result, and preserve the previous valid `DOUT`.

---

## 6. Frozen CDAC architecture and switching

### 6.1 Array structure

Use two matched, symmetric binary-weighted CDAC arrays.

Each side has the logical weights:

```text
64C, 32C, 16C, 8C, 4C, 2C, C, Cdummy
```

Per-side total capacitance:

```text
CT = 128C
```

Mapping:

| Element | Function |
|---:|---|
| `64C` | Adjustment after `D7` decision |
| `32C` | Adjustment after `D6` decision |
| `16C` | Adjustment after `D5` decision |
| `8C` | Adjustment after `D4` decision |
| `4C` | Adjustment after `D3` decision |
| `2C` | Adjustment after `D2` decision |
| `C` | Adjustment after `D1` decision |
| `Cdummy` | Completes total capacitance; no SAR adjustment |
| `D0` | Final comparison only; no subsequent CDAC adjustment |

Therefore the 8-bit ADC performs:

```text
8 comparator decisions
7 physical CDAC adjustments
```

The unit capacitance value is not frozen. It shall be selected from matching, kT/C noise, top-plate parasitic loading, input-drive, settling-time, reference-bounce, and area requirements.

### 6.2 Switching method

Use two-level bi-directional switching.

```text
logic 0 bottom-plate state = VREFN = 0.80 V
logic 1 bottom-plate state = VREFP = 2.50 V
```

Conceptual sampling-state vectors:

```text
BP[7:0] = 8'b0111_1111
BN[7:0] = 8'b0111_1111
```

Only bits `[7:1]` require physical SAR control outputs:

```text
DCTRLP[7:1]
DCTRLN[7:1]
```

### 6.3 First comparison and upward switch

The first comparison directly determines `D7` before any DAC adjustment.

After comparator-polarity normalization:

```text
if VFOP > VFON:
    D7 = 1
    switch N-side 64C from VREFN to VREFP

if VFOP < VFON:
    D7 = 0
    switch P-side 64C from VREFN to VREFP
```

This is the only upward transition in the conversion.

### 6.4 Later comparisons and downward switches

For `k = 6` down to `1`:

```text
if VFOP > VFON:
    Dk = 1
    switch P-side weight k from VREFP to VREFN

if VFOP < VFON:
    Dk = 0
    switch N-side weight k from VREFP to VREFN
```

After each completed decision for `k = 7 ... 1`, the final physical control states satisfy:

```text
DCTRLN[k] = DOUT[k]
DCTRLP[k] = ~DOUT[k]
```

The `D0` decision is stored digitally and generates `EOC_INT`; it does not produce `DCTRLP[0]` or `DCTRLN[0]`.

### 6.5 CDAC implementation requirements

- P and N arrays must be geometrically and electrically symmetric.
- Bottom-plate switching shall use static retained controls.
- Each active capacitor shall change state at most once per conversion.
- Implement break-before-make where required.
- Never short `VREFP` to `VREFN` through overlapping switches.
- Match P/N local drivers, route lengths, loading, and switch dimensions.
- Shield top-plate nodes from digital clocks and output buses.
- Include reference routing and local decoupling in settling and reference-bounce verification.

---

## 7. Frozen StrongARM comparator behavior

Use a 3.3-V fully differential StrongARM dynamic comparator.

Comparator inputs:

```text
VFOP
VFON
```

Comparator clock:

```text
CMPCK = 0: reset/precharge
CMPCK = 1: evaluate/regenerate
```

The logic-facing output convention is frozen as:

| `DCMPP` | `DCMPN` | Meaning |
|---:|---:|---|
| 0 | 0 | Comparator reset; result invalid |
| 1 | 0 | `VFOP > VFON` |
| 0 | 1 | `VFOP < VFON` |
| 1 | 1 | Illegal state |

If the raw StrongARM outputs precharge high, add the required output inversion/buffering so the SAR logic sees reset state `00`.

The comparator must be verified over the bi-directional-switching input common-mode trajectory. At the frozen references, the approximate range is:

```text
1.65 V <= comparator input common-mode <= 2.075 V
```

Comparator verification shall include:

- decision delay versus differential input and common-mode;
- reset/precharge completion;
- input-referred offset and Monte Carlo yield;
- input-referred noise;
- metastability;
- kickback to both CDAC top plates;
- dynamic memory from incomplete reset;
- process-voltage-temperature and post-layout extraction.

Working comparator targets:

```text
input-referred offset:              preferably < 0.5 LSB = 6.64 mV
common-mode-dependent offset shift: preferably < 0.25 LSB = 3.32 mV
input-referred RMS noise:           target approximately <= 2 to 2.5 mV
kickback residual:                  target < 0.25 LSB
```

These are block-level design targets; final acceptance is based on complete-ADC SNDR, ENOB, DNL, and INL.

---

## 8. Frozen asynchronous SAR logic architecture

The normal logic interface is:

```text
inputs:
    CLKS
    DCMPP
    DCMPN
    VDD
    GND

outputs:
    CMPCK
    DCTRLP[7:1]
    DCTRLN[7:1]
    DOUT[7:0]
```

The logic contains:

1. comparator-valid detection;
2. self-timed comparator-clock generation;
3. comparator-clock delay and buffering;
4. an 8-stage conversion-progress shift register;
5. eight decision-storage elements;
6. seven P-side and seven N-side bottom-plate control latches;
7. internal end-of-conversion generation;
8. an 8-bit external output register;
9. deterministic power-on initialization.

### 8.1 Valid detection

```text
VALID = DCMPP | DCMPN
```

The implementation shall reject or safely handle the illegal `DCMPP=DCMPN=1` condition.

### 8.2 Self-timed comparator-clock generation

Define:

```text
EOC_INT = CLK_BIT[0]
GATE    = CLKS | EOC_INT
CMPCK_PRE = ~(VALID | GATE)
```

`CMPCK_PRE` shall pass through an explicit start/settling delay and a tapered buffer chain before driving the comparator:

```text
CMPCK_PRE -> delay/guard -> tapered buffer -> CMPCK
```

Normal operation:

```text
CLKS high       => GATE high  => CMPCK held low
CLKS falling    => GATE falls => first CMPCK rising edge after guard delay
VALID rising    => CMPCK falls and resets comparator
VALID falling   => next CMPCK rises after guard delay
EOC_INT rising  => GATE high  => CMPCK remains low
```

Do not reintroduce an external `CLKC` as a functional requirement.

### 8.3 Conversion-progress register

Use an 8-stage cumulative-progress shift register:

```text
first-stage D input = logic 1
stage Q drives next-stage D
all stages clocked by VALID rising edge
all stages reset during CLKS high
```

Expected sequence:

```text
before conversion: 0000_0000
comparison 1:      1000_0000
comparison 2:      1100_0000
comparison 3:      1110_0000
...
comparison 8:      1111_1111
```

Each `CLK_BIT[i]` provides one rising edge per conversion and remains high until the next sampling reset.

Mapping:

```text
CLK_BIT[7] rising => capture D7 and perform 64C adjustment
CLK_BIT[6] rising => capture D6 and perform 32C adjustment
...
CLK_BIT[1] rising => capture D1 and perform C adjustment
CLK_BIT[0] rising => capture D0 and assert EOC_INT
```

### 8.4 Bottom-plate control storage

Use seven P-side and seven N-side bottom-plate control units.

Each unit shall:

- capture the relevant comparator decision on its bit-enable event;
- apply the first-bit polarity/cross-coupling required by bi-directional switching;
- update only its assigned CDAC element;
- retain its state until the next sample phase;
- suppress stale-data glitches from the previous conversion.

If the chosen implementation uses a DFF followed by an AND gate and a delayed enable, require:

```text
t_enable_delay > t_CQ_max + t_skew + t_margin
```

All physical delays shall be implemented with GF180 devices/cells, not RTL `#delay` statements.

### 8.5 Asynchronous timing constraint

The asynchronous comparator-clock loop must not outrun the DAC update path.

Require:

```text
T_clk_ring > T_dac_path
```

A useful expanded constraint is:

```text
T_reset + T_valid + 2*T_buffer
    >= T_logic + T_CDAC_settling + T_margin
```

Before each new comparator evaluation:

- the prior decision must be captured;
- the comparator must be fully reset;
- `VALID` must have returned low;
- the selected CDAC bottom plate must have completed switching;
- the differential CDAC residual must settle to the target accuracy;
- the next bit-enable state must be unambiguous.

Target CDAC settling accuracy before the next decision:

```text
|V_DAC - V_final| < 0.25 LSB
```

Delay chains should preferably provide selectable taps for schematic, process-voltage-temperature, and extracted tuning.

---

## 9. Full-scale and parasitic sign-off requirement

Top-plate parasitics may reduce effective CDAC gain and cause premature endpoint-code saturation.

Relevant parasitics include:

- StrongARM input capacitance;
- sampling-switch capacitance;
- CDAC top-plate parasitics;
- top-plate routing capacitance;
- coupling from comparator and digital control lines.

The extracted ADC shall satisfy:

```text
VFS_ACTUAL_SYMMETRIC >= 3.0 Vpp,diff
```

Equivalently, with zero differential center:

```text
positive input boundary >= +1.50 V
negative input boundary <= -1.50 V
```

The fixed standard input of `3.0 Vpp,diff` shall not clip at any required process-voltage-temperature corner after extraction.

Use a differential ramp or code-density method to extract:

- lower and upper actual input limits;
- actual LSB;
- offset;
- gain error;
- DNL;
- INL;
- missing codes;
- positive/negative range asymmetry.

---

## 10. Verification requirements

### 10.1 Ideal and functional verification

Verify:

- all 256 codes;
- straight-binary polarity;
- eight comparator decisions per conversion;
- seven CDAC adjustments per conversion;
- first adjustment is the required upward bi-directional transition;
- subsequent adjustments are monotonic downward transitions;
- correct `CLK_BIT[7:0]` progression;
- no skipped or repeated decision;
- no bottom-plate glitch;
- no additional `CMPCK` pulse after `EOC_INT`;
- atomic external `DOUT` update;
- deterministic reset and restart;
- no asynchronous deadlock.

### 10.2 Transistor-level integration

The complete schematic simulation shall include:

```text
P-side CDAC
N-side CDAC
sampling switches
StrongARM comparator and output buffers
asynchronous SAR logic
reference sources and source impedance
input source and source impedance
output register and representative load
```

Observe at minimum:

```text
CLKS
CMPCK
DCMPP
DCMPN
VALID
CLK_BIT[7:0]
DCTRLP[7:1]
DCTRLN[7:1]
VFOP
VFON
DOUT[7:0]
VREFP current
VREFN current
```

### 10.3 Static acceptance

At required schematic and extracted conditions:

```text
DNL < +/-1 LSB
INL < +/-1.5 LSB
no missing code
```

### 10.4 Dynamic acceptance

Standard test conditions:

```text
Fs    = 2 MS/s
VCM   = 1.65 V
VREFP = 2.50 V
VREFN = 0.80 V
VIN   = 3.0 Vpp,diff
```

Require:

```text
SNDR >= 44 dB
ENOB >= 7.0 bit
```

Also report:

- SFDR;
- THD;
- reference-related spurs;
- clock/control coupling spurs;
- clipping behavior;
- performance versus input frequency up to near Nyquist.

### 10.5 Sign-off hierarchy

Complete at least:

1. ideal functional model;
2. block-level schematic simulations;
3. full schematic transient simulations;
4. process-voltage-temperature simulations;
5. comparator mismatch Monte Carlo;
6. CDAC mismatch Monte Carlo;
7. integrated ADC Monte Carlo;
8. block-level extracted simulations;
9. full-ADC extracted static simulations;
10. full-ADC extracted dynamic simulations.

---

## 11. Physical integration constraints

The ADC must fit within the Chipathon workshop core:

```text
2051 um x 2051 um
4.207 mm^2
```

Recommended logical pad mapping:

| ADC signal | Workshop resource |
|---|---|
| `CLKS` | dedicated `clk_pad` |
| `DOUT[0]` ... `DOUT[7]` | `bidir[0]` ... `bidir[7]` configured as outputs |
| `VINP` | `analog[0]` |
| `VINN` | `analog[1]` |
| `VREFP` | `analog[2]` |
| `VREFN` | `analog[3]` |
| optional test reset | dedicated `rst_n_pad` |

No normal-operation pads are required for `VCM`, `CLKC`, `CONVST`, or `READY`.

Although schematic hierarchy may expose unified `VDD/GND`, physical implementation shall preserve analog/digital supply separation where the padring permits:

```text
AVDD/AVSS: sampling switches, CDAC, comparator, references
DVDD/DVSS: asynchronous logic, output register, output drivers
```

Use:

- symmetric CDAC floorplanning;
- common-centroid/unit-capacitor array techniques where appropriate;
- dummy edge capacitors;
- guard rings and dense substrate contacts;
- short, shielded top-plate routes;
- separated analog and digital return paths;
- local reference and supply decoupling;
- controlled placement of delay cells and clock buffers;
- matched P/N comparator and CDAC routing.

---

## 12. Implementation and tool-flow requirements

Primary circuit implementation is schematic/transistor/gate level in the Chipathon analog tool flow.

Recommended flow:

```text
Xschem schematic entry
ngspice functional/transient/PVT/Monte Carlo simulation
KLayout or Magic layout
DRC/LVS
parasitic extraction
post-layout ngspice verification
Chipathon workshop padring integration
```

Behavioral Python, MATLAB/Simulink, Verilog, or Stateflow models may be used for architecture and regression verification, but they do not replace the transistor-level self-timed logic implementation.

Codex shall:

- preserve the frozen interfaces and signal names;
- avoid adding an external SAR clock;
- keep block testbenches separate from production schematics;
- parameterize resolution-related scripts for 8 bits;
- provide reproducible simulation commands and result extraction;
- avoid hard-coding ideal delays in final implementation;
- document any assumption that is not explicitly frozen here.

---

## 13. Frozen decisions

```text
process                 = GF180MCU
resolution              = 8 bit
sample_rate             = 2 MS/s
supply                  = 3.3 V
architecture            = fully differential asynchronous SAR ADC
sampling                = top-plate sampling
CDAC_switching          = two-level bi-directional
comparator              = StrongARM dynamic comparator
SAR_timing              = fully self-timed asynchronous
external_function_clock = CLKS only
conversion_start        = CLKS falling edge
VCM                     = 1.65 V
VFS_NOM                 = 3.4 Vpp,diff
VREFP                   = 2.50 V
VREFN                   = 0.80 V
dynamic_test_input      = 3.0 Vpp,diff
CDAC_per_side           = 64C/32C/16C/8C/4C/2C/C/Cdummy
comparisons             = 8 per conversion
CDAC_adjustments        = 7 per conversion
CDAC_control_buses      = DCTRLP[7:1], DCTRLN[7:1]
digital_output          = DOUT[7:0]
output_encoding         = straight binary
external_READY          = none
external_CLKC           = none
external_CONVST         = none
external_VCM_pin        = none
```

---

## 14. Items not yet frozen

```text
unit-capacitor value and physical capacitor type
sampling-switch topology and dimensions
bottom-plate switch topology and dimensions
reference-driver and decoupling implementation
StrongARM transistor dimensions
comparator output-buffer dimensions
asynchronous delay-chain topology and selectable taps
exact CLKS duty cycle
power-on-reset circuit
optional test-only reset/clock override
final power target
final ADC macro dimensions
final physical pad-edge assignment
```
