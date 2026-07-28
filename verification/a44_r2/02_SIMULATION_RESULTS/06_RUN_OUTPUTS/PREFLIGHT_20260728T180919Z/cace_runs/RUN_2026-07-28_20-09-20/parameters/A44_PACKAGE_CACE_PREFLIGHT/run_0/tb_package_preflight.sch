v {xschem version=3.4.8RC file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/code_shown.sym} 40 40 0 0 {name=DECK only_toplevel=false value="
* CACE executable-path preflight. Claim-bearing simulations are dispatched by
* the package-owned Python runners after this CACE parameter passes.
V1 out 0 1.25
R1 out 0 1k
.tran 0.1n 1n
.control
run
set wr_singlescale
setplot const
let row_index = unitvec(1)
let row_index[0] = 0
let final_v = unitvec(1)
let final_v[0] = 1.25
setscale row_index
wrdata /foss/designs/A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R1/06_RUN_OUTPUTS/PREFLIGHT_20260728T180919Z/cace_runs/RUN_2026-07-28_20-09-20/parameters/A44_PACKAGE_CACE_PREFLIGHT/run_0/tb_package_preflight_0.data final_v
quit
.endc
"}
