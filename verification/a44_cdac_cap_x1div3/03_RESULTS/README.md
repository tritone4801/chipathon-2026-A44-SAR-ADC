# Current structured results

## Acquisition

The formal reference plane is the external generator. The criterion is an
absolute differential error no greater than 3.3203125 mV, or 0.25 least-
significant-bit units, entering and remaining inside the bound.

| View and input fixture | Generator-plane acquisition |
| --- | ---: |
| Matching schematic, ideal zero-ohm input | 61.763312 ns |
| R8/M6 FULL-RC-CC PEX, ideal zero-ohm input | 76.550952 ns |
| Matching schematic, frozen ESD plus input RC | 134.335424 ns |
| R8/M6 FULL-RC-CC PEX, frozen ESD plus input RC | 151.832300 ns |
| Attempt20 FULL-RC-CC PEX, frozen ESD plus input RC | 151.934940 ns |

The R8/M6 three-point maximum-timestep span is 0.019823 ns; the attempt20
span is 0.020303 ns. These are TT, 3.3 V, 27 degrees Celsius acquisition
results without noise, mismatch, comparator/scope loading, or PVT coverage.

## Direct-input offset

All 100 requested TT seeds completed for whole-ADC upward-T1 transfer offset
with a direct ideal zero-impedance input. The signed mean is 0.430039 LSB, the
population standard deviation is 0.226182 LSB, and the observed range is
-0.134766 to 1.007813 LSB. This is not comparator-only input offset, a PEX
result, unbounded statistical yield, or signoff.

## Unified-TOP conversion

| Scenario | Ideal | Schematic | PEX | Current interpretation |
| --- | --- | --- | --- | --- |
| MIN2 | [0, 1] | [0, 1] | [0, 0] | `FAIL_FUNCTIONAL_CONVERSION`; controlling `FAIL_FORMAL_MIN2` |
| Minimum-maximum-minimum | [0, 255, 0] | [0, 255, 0] | [0, 255, 0] | `PASS_FUNCTIONAL_NOMINAL`; internal settling warning; robust margin not proven |
| 0x7F-0x80-0x7F | [127, 128, 127] | [127, 128, 127] | [127, 128, 127] | `PASS_FUNCTIONAL_NOMINAL`; settling and aperture-sensitivity warnings; robust margin not proven |

Numerical completion, protocol structure, nominal function, internal settling,
signed decision margin, robust margin, and end-to-end ADC performance remain
separate gates. See
[`conversion/LAYERED_CONVERSION_STATUS.json`](conversion/LAYERED_CONVERSION_STATUS.json)
for the machine-readable controlling judgment.

Raw waveforms and long simulator logs remain in the named engineering baseline
and are intentionally not duplicated in this review-sized GitHub package.
