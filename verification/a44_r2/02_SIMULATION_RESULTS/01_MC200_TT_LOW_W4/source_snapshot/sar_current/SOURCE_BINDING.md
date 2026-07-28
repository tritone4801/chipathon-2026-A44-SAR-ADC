# Current SAR ADC Source Binding

## Accepted hierarchy

```text
SAR_ADC_TOP_FIXED
|-- XCDACP: CDAC
|   `-- SWITCH_BOOT_SP
|-- XCDACN: CDAC
|   `-- SWITCH_BOOT_SP
|-- XCMP: Comparator_StrongARM, production sizing
`-- XLOGIC: SAR_LOGIC_ACTUAL_RTL, current accepted SS RTL/PEX binding
```

Frozen TOP interface and order:

```text
VDD GND VREFP VREFN VINP VINN CLKS DOUT[7] DOUT[6] DOUT[5] DOUT[4]
DOUT[3] DOUT[2] DOUT[1] DOUT[0]
```

The interface above is taken from the accepted `SAR_ADC_TOP_FIXED.spice`, not
inferred from directory names or a legacy symbol.

## Project-local transformations

Only these project-copy transformations are intentional:

1. `SAR_ADC_TOP_FIXED.sch` symbol references were changed from the old
   workspace paths to root-local `A44_Comparator_StrongARM.sym`,
   `A44_CDAC.sym`, and `A44_SAR_LOGIC_ACTUAL_RTL_REPAIR.sym`.
2. `CDAC.sch` now references root-local `A44_SWITCH_BOOT_SP.sym`.
3. `A44_SAR_ADC_TOP_FIXED.sym` was created for this package from the frozen accepted
   TOP interface and pin order.
4. The package-local TOP and SAR logic symbols use 20-unit-grid pin centers and
   explicit orthogonal lines from every pin box to the body. This is a display
   geometry repair only; the TOP pin order and the explicit flattened logic
   subcircuit order are unchanged.
5. Absolute include roots under the completed measurement campaign were
   changed to `/foss/designs/manual_goal/analog/SAR_CURRENT/netlists/accepted`
   in the runnable netlist copy.
6. The unused legacy `SAR_ADC_TOP_RC_HEAVY_WRAPPER.spice` was excluded; it is
   not in the current include chain and points to the obsolete
   `actual_fixed_top_wrapped_local.cir`. The active wrapper is
   `SAR_ADC_TOP_RC_HEAVY_CURRENT_RTL_WRAPPER.spice`.
7. All five active project symbols use an `A44_` filename, `symname`, and
   visible-name prefix. `default_schematic=ignore` plus explicit instance
   `schematic=` selection decouples symbol names from the original electrical
   subcircuit names. Standard-library/PDK symbols and immutable source snapshots
   retain their upstream names.

Unmodified originals and their fixed hashes are retained under
`source_snapshot/authoritative/` and audited by
`manifests/source_manifest.csv`.

The exact symbol geometry is exercised by the two schematics under
`verification/`; actual Xschem GUI captures are retained under
`reports/images/`. The repair does not modify any file under `D:/PICO/SAR_SUM`.

## Source authority

The binding follows the completed
`cace_actual_sar_mc_noise_perf_v1` measurement package and its source manifest.
The user-mentioned guide was no longer present at its original `D:/PICO` path;
the immutable guide snapshot from that completed package is included under
`source_snapshot/guide/`.

## Non-claims

- This is not a comparator-resize candidate package.
- This does not substitute an ideal comparator, ideal CDAC, or legacy logic.
- Xschem-generated smoke netlists are structural checks only; the accepted
  campaign netlists under `netlists/accepted/` remain the simulation binding.
- No new static, dynamic, noise, Monte Carlo, PEX, RCX, or signoff result is
  claimed by this assembly operation.
