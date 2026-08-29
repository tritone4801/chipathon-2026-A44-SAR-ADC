# Contract and coverage

- [`BASELINE_STATUS.json`](BASELINE_STATUS.json) is the source baseline's
  current working-status record.
- [`CONFIRMED_SIMULATION_METHODS.json`](CONFIRMED_SIMULATION_METHODS.json)
  freezes the input fixture, acquisition criterion, transient method, and
  claim boundaries.
- [`SIMULATION_COVERAGE_CURRENT_VS_OLD.csv`](SIMULATION_COVERAGE_CURRENT_VS_OLD.csv)
  separates completed current-capacitor work from historical results, open
  gates, and out-of-scope items.

These files are copied from the named baseline without upgrading any partial
or diagnostic result. In particular, schematic comparison data are not
parasitic extraction, acquisition completion is not full ADC performance, and
package integrity is not electrical signoff.
