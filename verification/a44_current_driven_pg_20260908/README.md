# A44 current-driven PG repair publication

This package publishes the retained local `DRIVER_R2` layout candidate on top
of GitHub `main` commit `5a30eed`. The external interface, `info.yaml`,
`lvs_config.json`, mixed-signal LVS sources, DEF and LEF remain unchanged.

The update adds 209 metal rectangles and 1,924 ordinary via cuts relative to
the previous GitHub GDS. The changed owner cells are `A44_A`,
`A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR`, and
`A44_COMP_PEX_ECO1_SD_REQUIRED_G6_FULL_R9`; the other public component cells
remain the existing current versions.

The source candidate already recorded Magic DRC 0, KLayout DRC/antenna 0 and a
unique Netgen LVS result. The initial layout was published as commit
`f221089b9738ea45f94f1fde199e762975e49db9` and then cloned back from GitHub for
an independent post-push check. The check read `info.yaml`, followed its
`lvs_config.json` binding, used the GDS, SPICE and powered gate-level Verilog
named there, and reran Magic/KLayout DRC and mixed-signal Netgen LVS.

The GitHub-derived run passed: Magic DRC reported 0 errors, KLayout main DRC
and antenna reports each contained 0 items, and Netgen reported a unique LVS
match. Compact evidence is retained under
`reports/GITHUB_CONFIG_DRC_LVS_R1/`.

This publication and verification do not constitute PEX, performance,
density, ESD-stress, foundry signoff, promotion or tapeout approval.
