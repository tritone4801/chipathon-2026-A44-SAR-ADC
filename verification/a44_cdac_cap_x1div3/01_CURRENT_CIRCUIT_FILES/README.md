# Current cap x1/3 circuit delta

This directory is an overlay on the preserved
[`a44_w5p29_trans_driver`](../../a44_w5p29_trans_driver/01_CURRENT_CIRCUIT_FILES)
circuit package. Unchanged comparator, sampling-switch, clock-buffer,
conversion-buffer, SAR-logic, symbol, and RTL files remain available there.

The electrical delta is intentionally narrow:

| File | Current change |
| --- | --- |
| `xschem/A44_C1_SWITCH.sch` | C1 MIM multiplier changes from 18 to 6 |
| `xschem/A44_CDAC_UNIT_TRANS_DRIVER.sch` | Dummy MIM multiplier changes from 18 to 6 |
| `spice/A44_CDAC_UNIT_TRANS_DRIVER_HIER.subckt.spice` | Matching C1 and dummy netlist multipliers change from 18 to 6 |
| `spice/A44_SAR_ADC_TOP_FIXED.spice` | Matching flattened TOP occurrences change from 18 to 6 |

The reference-switch devices remain at multiplier 18; the sampling
transmission gate remains at multiplier 8. The fixed nominal input network,
the acquisition execution view of the primary analog pad, its source receipt,
and the secondary-ESD wrapper are under `input_model/`.

The files retain their baseline circuit and subcircuit names. No behavioral or
mixed-view replacement is introduced by this publication.
