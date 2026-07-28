# Numerical Convergence

- Status: `PASS`
- Predicted static-tail CDAC seed: `105`
- Predicted dynamic-tail CDAC seed: `128`
- 0.10 ns bulk qualification: `PASS`
- Frozen bulk maxstep: `0.10 ns`
- Frozen strict maxstep: `0.05 ns`
- Frozen static frame: `500 ns`
- Frozen startup frames: `0`
- Fixed external-input numerical tie-break: `10.000 uV,diff` (`0.000753 LSB`)

## Maxstep Comparison

| Case | Seed | dSNDR (dB) | dSFDR (dB) | dTHD (dB) | Max dTransition (LSB) | DOUT identical | Status |
|---|---:|---:|---:|---:|---:|---|---|
| NOMINAL | None | 0.000000 | 0.000000 | 0.000000 | 0.000000 | True | PASS |
| FIXED_SEED_001 | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | True | PASS |
| FIXED_SEED_002 | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | True | PASS |
| PREDICTED_STATIC_TAIL_105 | 105 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | True | PASS |
| PREDICTED_DYNAMIC_TAIL_128 | 128 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | True | PASS |

## Static Frame Gate

| Frame (ns) | Valid | Code match | Sample error (LSB) | Stable margin (ns) | Transition shift (LSB) | Status |
|---:|---|---|---:|---:|---:|---|
| 500 | True | True | 0.000000 | 104.515000 | 0.000000 | PASS |
| 320 | False | False | 0.000000 | -inf | NOT_EVALUABLE | FAIL |
| 300 | False | False | 0.000000 | -inf | NOT_EVALUABLE | FAIL |
| 280 | False | False | 0.000000 | -inf | NOT_EVALUABLE | FAIL |

## Startup Gate

| Startup | SNDR (dB) | SFDR (dB) | dSNDR next (dB) | dSFDR next (dB) | Valid | Status |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 49.445181 | 56.392377 | 0.000000 | 0.000000 | 64/64 | PASS |
| 1 | 49.445181 | 56.392377 | 0.000000 | 0.000000 | 64/64 | PASS |
| 2 | 49.445181 | 56.392377 | 0.000000 | 0.000000 | 64/64 | PASS |
| 4 | 49.445181 | 56.392377 | N/A | N/A | 64/64 | REFERENCE |
