# A10 training-path candidate: waiting for S1 data

This is preparation, not a complete review submission. Candidate source is isolated; the active runner remains unchanged. A10 requires the complete selected data, nesting checks, per-cell supervised-token totals and this diff to be reviewed together before training.

Changes: add the (512,1,8) R8 parameter; label LogiQA evaluation with its own protocol; require frozen single-user-message prompts and full1572 greedy outputs; omit original prompt text and reversible prompt tokens from public training previews and generation evidence. Existing rendering, prompt masks, optimizer, schedule and model-sampling parameters remain unchanged.

CPU_CHECKS covers all1572 actual frozen test prompts without model calls, two invalid-dose guards, byte-identical legacy MATH generation artifacts with a fake client, private training previews, unchanged rendering/optimization helpers and R8 dose512. No training data have been frozen yet.

The complete1572 evaluation conversations are privately frozen; only safe identities and hashes are public. Baseline4096 forecasts totalUSD5.2757including1.5margin, belowcap6; not admitted before review. score_logiqa.py reuses the unchanged audited pilot letter scorer and adds A10 protocol/input/prediction bindings plus normal-termination metrics. Five synthetic binding checks pass. ACCEPTED_REVIEW.json does not exist; no real scoring or new baseline call is authorized by this candidate. freeze_data.py verifies original responses and labels before selecting first4distinct correct solutions and producing nested private files; it has not run while S1 is incomplete.
