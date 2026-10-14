# P009 complete-answer training-plan preflight

Pure local planning/validation code, not a training runtime or admission. It reuses the original P008 whole-answer schedule and the original published1,024-step LR vector (64warmup updates,1e-4 peak,1e-5 final); no host cosine recomputation. Old files and their bytes remain unchanged.

The new contract is exactly1,024updates and2,097,148supervised targets, seed17or29, all selected answers at least once, each used q or q+1 times, complete separate sequences<=2,048, prompt masked and one native terminalEOS. It rejects missing exposure, q0, changed/fractional metadata, target reduction, missing updates and one-ULP LR alteration. It cannot inherit P008's q0 bridge or0.1% dose reduction. Infeasible exact inventories fail closed. Runtime training/loss/LoRA/model identity and exact scientific input review remain mandatory later.

Seven new authored fixtures passed on the initial candidate. A subsequent integer-metadata tightening added one further fixture, which passed on the final source; its setup also builds and validates a full-dose synthetic plan with final source. The earlier seven fixtures were not rerun. Both original logs are preserved. No actual teacher output, student inventory, schedule release, training, inference, upload or scoring was performed.

Review scope is only the future pure training-plan contract. It does not block P0 or admit Stage1/2. Exact actual selected-data/input/complete runtime/budget gates remain required. Source snapshots preserve original bytes, including historical whitespace.
