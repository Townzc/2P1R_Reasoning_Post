# E037 frozen goal probe

Completed; provider off; no further training is authorized by this phase.
Read CURRENT_STATUS.md and ../../reports/post_e036_goal_probe/RESULTS.md.

The published execution commit is0a6770f5fceb929aff6d425b9ce8af293c12e71b.
The data builder and release remain exactly as frozen for provenance. **Do not
interpret its C0_calibration_fit or *_training_support_union labels as the actual
endpoint ancestry.** E030 is a non-ancestor sibling. Canonical corrected support:
../../reports/post_e036_goal_probe/TRAIN_TARGET_SUPPORT_AUDIT.json and
TRAIN_SUPPORT_LINEAGE_CORRECTION.{json,md}. Preserve this historical correction
when designing a later builder; do not repeat the invalid union assumption.
The error does not affect selected questions, leakage exclusions or model results.

Offline replay: python -m experiments.post_e036_goal_probe.analyze
--tokenizer-dir PINNED_TOKENIZER --run-dir runs/post_e036_goal_probe_v1
--output NEW_UNUSED_REPORT_DIRECTORY. This creates reports exclusively and calls
no model. plot_results.py draws the checked PNG from final result JSON files.

The launcher remains a historical execution entrypoint, not an auto-resume
instruction. New phase authority and budget must come from the owner's next plan.
