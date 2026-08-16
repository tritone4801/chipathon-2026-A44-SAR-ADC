# Team A44 Successive-Approximation-Register Analog-to-Digital Converter Progress and Performance

## Status summary

The current resized converter circuit set and the fixed simulation campaigns
are assembled under
[the current electrical simulation package](../verification/a44_r2).

The following activities are complete:

- collection of the current resized circuit files;
- a 200-sample Monte Carlo mismatch dynamic simulation at the
  typical-typical process corner, 3.3 volts, and 27 degrees Celsius;
- a three-corner process-voltage-temperature dynamic simulation using 20
  selected Monte Carlo mismatch samples per corner;
- six unique full 255-transition static transfer-curve simulations;
- a Circuit Automatic Characterization Engine Xschem-to-ngspice package
  preflight;
- a 130-record quick result-reproduction run;
- staging of the complete campaign without dispatching the simulation matrix.

Every prescribed simulation has executed. The present design does not meet
the full electrical acceptance criteria and is not promoted. The full static
transfer curve passes on its sole qualification case, seed 44 at the
typical-typical process corner, 3.3 volts, and 27 degrees Celsius. The
no-promotion disposition remains because the 200-sample Monte Carlo mismatch
dynamic simulation has three hard-dynamic failures.

## Fixed simulation methods

### 200-sample Monte Carlo mismatch dynamic simulation at the typical-typical process corner

- Operating point: typical-typical transistor models, 3.3 volts, and
  27 degrees Celsius.
- Signal scope: low differential-input band.
- Maximum transient step: 50 picoseconds.
- Population: mismatch seeds 1 through 200.
- Event-noise seed: 100000 plus the mismatch seed.
- Conversions per sample: 68.
- Startup and diagnostic conversions: 0 through 3.
- Formal steady-state measurement window: conversions 4 through 67,
  providing 64 retained conversion records.

This is a low-input-band population result at one operating point. It is not a
two-band die-level yield result.

### Three-corner process-voltage-temperature dynamic simulation with 20 selected samples per corner

- Dynamic method: the same 68-conversion method, 50-picosecond maximum step,
  and formal steady-state conversions 4 through 67 used above.
- Typical-typical corner: 3.3 volts and 27 degrees Celsius.
- Slow-slow corner: 3.0 volts and 125 degrees Celsius.
- Fast-fast corner: 3.6 volts and minus 40 degrees Celsius.
- Population: 20 selected mismatch seeds per corner, for 60 completed jobs.

These selected samples provide diagnostic corner visibility. They are not a
200-sample population and cannot support performance acceptance, production
yield, promotion, or signoff claims.

### Full 255-transition static transfer-curve simulation

Each static curve uses a formal search over all 255 code transitions. Seed 44
at the typical-typical process corner, 3.3 volts, and 27 degrees Celsius is the
sole qualification case. It is computed once and reused in the typical-corner
multi-seed view and the seed-44 process-voltage-temperature view.

The other typical-corner seeds and the seed-44 slow-slow and fast-fast corner
curves are diagnostic only. Their threshold outcomes may be reported, but they
cannot establish or overturn the static qualification result.

## Dynamic performance

### 200-sample Monte Carlo mismatch dynamic simulation

| Metric | Value |
| --- | ---: |
| Completed samples | 200/200 |
| Execution exceptions | 0 |
| Hard-dynamic passes | 197 |
| Hard-dynamic failures | 3 |
| Failing mismatch seeds | 65, 68, 141 |
| Signal-to-noise-and-distortion ratio, first percentile | 46.8729 decibels |
| Signal-to-noise-and-distortion ratio, fifth percentile | 47.2961 decibels |
| Signal-to-noise-and-distortion ratio, tenth percentile | 47.4636 decibels |
| Signal-to-noise-and-distortion ratio, median | 48.4065 decibels |

Result files are under
[the 200-sample dynamic simulation directory](../verification/a44_r2/02_SIMULATION_RESULTS/01_MC200_TT_LOW_W4).

### Three-corner process-voltage-temperature dynamic simulation

| Process corner and operating point | Completion | Hard-dynamic passes | Median signal-to-noise-and-distortion ratio |
| --- | ---: | ---: | ---: |
| Typical-typical, 3.3 volts, 27 degrees Celsius | 20/20 | 19/20 | 48.4048 decibels |
| Slow-slow, 3.0 volts, 125 degrees Celsius | 20/20 | 20/20 | 48.3026 decibels |
| Fast-fast, 3.6 volts, minus 40 degrees Celsius | 20/20 | 20/20 | 48.6010 decibels |

Result files are under
[the three-corner selected-sample directory](../verification/a44_r2/02_SIMULATION_RESULTS/02_PVT3_MC20_LOW_W4).

## Static performance

| Simulation case | Seed | Maximum absolute differential nonlinearity | Maximum absolute integral nonlinearity | Missing codes | Reversals | Qualification use |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Typical-typical process, 3.3 volts, 27 degrees Celsius | 44 | 0.610351 least-significant-bit units | 0.686645 least-significant-bit units | 0 | 0 | Pass; sole qualification basis |
| Typical-typical process, 3.3 volts, 27 degrees Celsius | 116 | 0.422577 least-significant-bit units | 0.358017 least-significant-bit units | 0 | 0 | Diagnostic only |
| Typical-typical process, 3.3 volts, 27 degrees Celsius | 180 | 0.469508 least-significant-bit units | 0.451902 least-significant-bit units | 0 | 0 | Diagnostic only |
| Typical-typical process, 3.3 volts, 27 degrees Celsius | 106 | 0.146719 least-significant-bit units | 0.093900 least-significant-bit units | 0 | 0 | Diagnostic only |
| Slow-slow process, 3.0 volts, 125 degrees Celsius | 44 | 1.496350 least-significant-bit units | 1.572634 least-significant-bit units | 1 | 1 | Diagnostic only; threshold failure is not a qualification gate |
| Fast-fast process, 3.6 volts, minus 40 degrees Celsius | 44 | 0.328772 least-significant-bit units | 0.416836 least-significant-bit units | 0 | 0 | Diagnostic only |

Result files are under
[the simulation-results directory](../verification/a44_r2/02_SIMULATION_RESULTS).

## Result reproduction

The Circuit Automatic Characterization Engine preflight executed the
Xschem-to-ngspice path and produced a final voltage of 1.250 volts, inside the
allowed range of 1.249 to 1.251 volts.

The quick result-reproduction run compares:

- 25 retained records from the 200-sample Monte Carlo mismatch dynamic
  simulation;
- 75 retained records from the three-corner selected-sample dynamic
  simulation;
- 30 transition records from the six full static transfer curves.

All 130 compared records match their stored reference values.

## Claim boundaries and remaining work

The package does not support claims of:

- two-band die-level yield;
- production-yield qualification;
- layout or parasitic-extraction signoff;
- silicon validation;
- tapeout readiness;
- full-converter signoff.

The unresolved electrical items are the three hard-dynamic failures in the
200-sample Monte Carlo mismatch dynamic simulation. The seed-44 slow-slow
static threshold failure remains useful diagnostic information, but it is not
the governing static qualification case.
