# Training-support lineage correction

The frozen release audit incorrectly named a released-data superunion as actual endpoint training support. Its `C0_calibration_fit` scope is the32-row E030 engineering calibration-fit dataset. E030 is an independent child of original C0; it is **not** an ancestor of E031–E036. Original C0 is the untrained LoRA initialization.

For each E033–E036 endpoint, actual unique source-row support is its256 prep rows plus512 main rows: **768 rows and512 distinct number multisets**, each with exactly1 observed target. The earlier800 rows/544 groups included32 unrelated calibration-fit rows. Epoch repetition does not change these support counts.

The original frozen audit, source and release manifest remain unchanged for provenance. The accompanying JSON supplies corrected scopes, histograms, actual parent-manifest hashes and the published registration/amendment evidence. The32-row calibration-fit scope remains a valid descriptive dataset audit, but its C0-ancestor label is withdrawn.

The separate main-training conclusions remain correct: Surface and Paths each cover256 number multisets with1 target each; they respectively have1 and2 ordered programs per number-target. This describes finite observed supervision and does not establish that models ignore targets.

This correction changes no evaluation data, prompts, tokenizer candidates, endpoint weights, strict scores, or result. Calibration identities remain excluded during leakage checks, which is appropriate even though calibration is not ancestral training. No model call or training was added.
