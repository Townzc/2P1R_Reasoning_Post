# AI assistance log

## 2026-09-05 UTC — repository bootstrap
Codex imported user-provided CPU arithmetic code and synthetic fixtures, summarized the updated SFT-only protocol, and established public-repository hygiene and compute accounting. Source fixtures are CPU examples, not model results. Private correspondence and server credentials were excluded. Human decisions: start implementation, use this repository for progress, cap initial GPU jobs at two GPU-hours. Validation and actual outcomes are recorded separately in reports and run directories.

## 2026-09-05 UTC — engineering implementation
Codex implemented exact response-token labels and exposure accounting, bounded subprocess execution with a persistent budget ledger, strict generation scoring, engineering overfit/profile entry points, and targeted correctness tests. It reproduced the CPU fixture byte-for-byte, pinned model revisions against the official API, and read targeted sections of three closest papers. Human review of the causal comparison and global-coverage exposure definition remains pending. No treatment effect has been inferred from fixtures or tests.

## 2026-09-05 UTC — first GPU attempt and overfit diagnostic
A launch during an incomplete server fetch exposed an untracked-source provenance gap. Codex stopped and invalidated that attempt, conservatively charged 120 seconds after confirming no run/GPU processes remained, added an explicit tracked-source guard, and synchronized the published Git history using a bundle. The subsequent committed-code run completed 400 updates: 25/32 train correctness, 0/16 greedy dev correctness, reference train NLL 0.011995. The 95% overfit gate failed. Raw outputs show malformed/incorrect arithmetic expressions, not a reason to relax the verifier. A new engineering run is configured from the same base with a lower learning rate (5e-5) and up to 800 updates to address oscillation; no scientific treatment comparison or dev-based model selection is implied.

## 2026-09-05 UTC — completed engineering gates
The lower-LR debug run passed its prespecified >=95% train correctness / <0.2 NLL gate at 300 updates (31/32, NLL 0.000996), with zero greedy or sampled development successes. Codex retained all negative results and did not interpret this as a treatment effect. The intended 1.5B full-FP32 AdamW profile failed before any update on 24 GB; no optimizer-precision or adaptation-method substitution was made. Model file identities, raw outputs, exact trace summaries, compute accounting and migration safeguards were recorded. Remaining work is main-model capability/profile on suitable hardware and a reviewed scientific control/data design.

Both completed debug checkpoints were separately backed up locally and verified against their SHA-256 manifests. These are weights-only artifacts, not optimizer-resume checkpoints. Saved-run metrics, actual token budgets and completed-update histories were cross-checked on CPU; all 37 server tests passed.

## 2026-09-05 UTC — A800 migration and main-model preparation
At the owner's request, Codex connected the supplied A800 80GB server, configured project SSH-key access outside Git, and transferred published history and the existing budget ledger. The new image matches Python 3.12 / PyTorch 2.8.0+cu128; the driver is recorded separately. A main-model overfit configuration retains the adaptation recipe and uses the debugged learning rate. Optional pre-training sampled development evaluation was added to pair with the existing post-training sampling. No scientific treatment comparison is authorized by a successful engineering check alone.

Codex implemented a CPU-only candidate search for shared four-structure blocks and an explicit per-update tokenizer audit for four proposed arms. Three targeted tests check disjoint problem selection, rejection of length mismatch, and rejection of partial structure overlap. The search keeps full canonical structures and reports selection restrictions; the step-label-only surface control remains a review limitation. This is preparation for scientific design review, not a treatment result.

## 2026-09-05 UTC — verified A800 engineering outcomes
Codex completed the identical 1.5B profile and main-model overfit gate on A800. The latter reached 32/32 train correctness and exact reference trace at 500 updates, but remained 0/16 greedy and 0/64 sampled on development; development NLL increased. All outputs and negative results were retained, and raw scoring/budget/provenance consistency was recomputed on CPU. The A800 runs charged 436 seconds, bringing the shared total to 1173/7200 seconds.

The CPU candidate search found 256 disjoint problems with exact per-update response-token equality across four proposed arms and exact Within-Paths/GCM structural equality. Only 25% of the candidate pool was selected; target-distribution shift and weak label-only rendering were reported. The search began after the training throughput measurement window. No final split was frozen and no scientific arm comparison was launched. Main checkpoint transfer and SHA-256 verification are tracked separately in the artifact inventory.

A subsequent operator audit showed that the first selected candidate pool is additive-only. Codex corrected an operator-count summary to count parsed binary operations instead of symbols in AC-flattened signatures (the latter undercounts associative operations), retained the immutable candidate data, and added an explicit multiply/divide-per-block sensitivity filter with two focused tests. This is a CPU design diagnostic, not a change to scientific training.

The multiply/divide-constrained CPU search selected 64/1024 candidate groups, then 256/4096 after expanding the pool. Per-update matching held in both; the larger result has 31 full structures and 66416 supervised tokens per arm per cycle. All selected expressions, structure identities and binary operator totals were rechecked. Final main-model development errors were categorized from saved predictions without additional model inference. The resulting suite has 42 passing tests. No scientific grid or extra GPU job was launched.

The main A800 checkpoint backup completed after a slow, resumed SSH transfer. All 12 files were checked with the artifact verifier on both A800 and the local backup; the reports are identical. Public records contain hashes and sizes only, not checkpoint weights or connection information. The latest 1173-second private ledger is backed up locally.

## 2026-09-05 UTC — shutdown and replacement-instance handoff
The owner emphasized frequent server replacement and Git-based continuity, and planned to pause the instance before discussing the next stage. Codex confirmed no active GPU/data job or unresolved ledger entry, checked that the previously verified local backups still exist at their recorded sizes, and added a next-session handoff plus durable repository workflow rules. The owner can shut down the instance; no new experiment, automated restart or rental was initiated.

## 2026-09-08 — local pilot preparation and bounded research workflow

The owner approved the staged data/calibration/four-arm pilot plan and suggested
karpathy/autoresearch. Codex inspected the primary repository and adapted compact
run logging, fixed evaluation and bounded iteration; no upstream code or data
was imported. The project retains all results in Git and preserves token/update
matching, cumulative spending limits and holdout separation.

Codex implemented presolver group allocation, exact four-arm schedules, richer
sentence-frame controls, a frozen artifact loader, a GPU calibration/pilot mode,
a finite queue with a stale-ledger gate, and JSON/TSV result snapshots. Two CPU
preparations failed (original tokenizer hash requirement; insufficient dev blocks)
and were retained. The third produced 256 train, 64 matched dev and 64 broader
dev problems, with 2048 unsolved holdout groups reserved in advance. Selection
shifts and the narrow Surface interpretation are explicit. No model weights were
loaded and no GPU or prior-server connection was used in this preparation.

Local verification completed: 50 tests ran, 48 passed and two GNU-timeout tests
were skipped pending the Linux server. Full frozen-artifact verification and
both queue dry runs passed; no GPU execution or comparison outcome is claimed.

## 2026-09-08 — replacement A800 calibration

Codex recovered the published Git history and existing 1173-second ledger on the
owner's cloned A800 through authenticated Jupyter after SSH banner timeouts. All
nine model files and frozen data were verified; all 50 Linux tests passed. The
approved bounded calibration completed 1024 updates, charging 546 seconds and
passing the fixed feasibility gate (14/64 matched dev, 2/64 broader dev). The
update-512 matched score was higher; no checkpoint selection or shortened dose
was used. Codex preserved raw outputs, backed up the ledger, added CPU checks
that rescore saved predictions and reconcile training exposure accounting, and
extended the run registry to distinguish calibration/scientific-pilot records.
The fixed four-arm phase remains the next already-authorized action; no treatment
ordering, holdout result or general arithmetic capability is inferred.
