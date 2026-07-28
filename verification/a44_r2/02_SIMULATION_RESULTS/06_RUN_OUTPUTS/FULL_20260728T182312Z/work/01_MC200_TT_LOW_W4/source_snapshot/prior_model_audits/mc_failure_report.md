# MC Failure / Stop-Condition Report

- Generated UTC: `2026-07-01T23:57:59+00:00`
- Source files modified: `none`

- `MIM_LOCAL_MISMATCH_UNAVAILABLE`: `CLASSIFIED_LIMITATION`; evidence `reports/mim_mismatch_capability.md`; claim not made: GF180 process-typical CDAC MIM mismatch signoff
- `COMPARATOR_OFFSET_EXTRACTION_FAIL`: `UNAVAILABLE_MODEL_LIMITATION_NO_OFFSET_DISTRIBUTION`; evidence `reports/comparator_offset_mc_report.md`; claim not made: comparator Vos MC distribution
- `COMPARATOR_TRANSIENT_NOISE_UNAVAILABLE`: `NATIVE_TRANSIENT_NOISE_NOT_CLOSED`; evidence `reports/comparator_noise_probability_report.md`; claim not made: StrongARM native transient-noise input-referred signoff
- `TOP_SELECTED_REPLAY_BLOCKED`: `CDAC_T2_SURROGATE_DONE_TOP_NOT_RUN`; evidence `reports/top_selected_worst_seed_replay.md`; claim not made: selected TOP statistical worst-seed replay
- `PVT_TIMING_FAIL`: `FAIL_REVIEW`; evidence `reports/pvt_mc_screening.md`; claim not made: PVT-MC robustness / PVT signoff

These are validation stop/limitation classifications, not production design edits.
