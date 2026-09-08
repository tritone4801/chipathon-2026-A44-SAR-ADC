# A44 current-driven PG repair publication

This package publishes the retained local `DRIVER_R2` layout candidate on top
of GitHub `main` commit `5a30eed`. The external interface, `info.yaml`,
`lvs_config.json`, mixed-signal LVS sources, DEF and LEF remain unchanged.

The update adds 209 metal rectangles and 1,924 ordinary via cuts relative to
the previous GitHub GDS. The changed owner cells are `A44_A`,
`A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR`, and
`A44_COMP_PEX_ECO1_SD_REQUIRED_G6_FULL_R9`; the other public component cells
remain the existing current versions.

The source candidate already records Magic DRC 0, KLayout DRC/antenna 0 and a
unique Netgen LVS result. After the initial layout commit is pushed, the
repository will be checked again from a clean GitHub-derived checkout. That
check reads `info.yaml`, follows its `lvs_config.json` binding, uses the GDS,
SPICE and powered gate-level Verilog named there, and reruns Magic/KLayout DRC
and mixed-signal Netgen LVS. Results are pending until that post-push run.

This publication and verification do not constitute PEX, performance,
density, ESD-stress, foundry signoff, promotion or tapeout approval.
