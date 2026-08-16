# MIM Capacitor Mismatch source validation

- Generated UTC: `2026-07-01T19:23:15+00:00`
- Finding: GF180 MIM statistical variation is runnable for global capacitance variation, but local per-instance MIM mismatch was not found in the included MIM subcircuits.
- PDK statistical source: `/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice`, section `mimcap_statistical`.
- MIM subcircuit source: `/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064_mim.ngspice`, section `cap_mim_new`.
- Observed global terms: `mc_c_cox_1p0fF`, `mc_c_cox_1p5fF`, `mc_c_cox_2p0fF` driven by `sw_stat_global` and `cap_mc_skew`.
- Observed local mismatch control in MIM subcircuits: `NOT_FOUND` for `sw_stat_mismatch` or per-instance `agauss` terms.
- CDAC mismatch branch selected: `CDAC_MISMATCH_ENGINEERING_SENSITIVITY`, an engineering sensitivity model.

Claim boundary: this validation does not say the real process lacks MIM mismatch; it says the local open-source ngspice model path used here did not expose a verified per-instance MIM mismatch model.
