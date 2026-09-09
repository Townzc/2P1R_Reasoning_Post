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

## 2026-09-08 — completed paired four-arm pilot and recovery

Within the owner's approved finite phase and cumulative budget, Codex ran Repeat,
Surface, Paths and GCM independently from the same pinned base/source and fixed
1024-update dose. Matched-dev correctness was 14, 12, 23 and 18 out of 64;
broader-dev correctness was 2, 0, 4 and 1. No checkpoint/dose selection or holdout
inference occurred. Raw outputs, failure categories, paired problem counts,
source/data identities, all exposure histories and runtime receipts were retained.
The comparison charged 1993 seconds; the total is 3712/7200 seconds.

Codex independently rescored outputs on CPU and reconciled the final private
ledger. Reporting now includes sampled pass@1/2/4, both development slices,
train diagnostics and parse/truncation rates. The saved-summary verifier permits
only 1e-12 floating-point roundoff in scalar statistics across operating systems;
identities and correctness remain exact. Local tests passed (48 plus two Linux-only
skips); all 50 had passed on Linux before execution. Authenticated Jupyter file
transfer was used after SSH banner failures; resumable checkpoint downloads are
verified against recorded SHA-256 manifests outside Git. No extra run, rental,
automated restart or expanded research scope is inferred from this pilot signal.

The final independent backups completed for all four scientific checkpoints:
48 files, about 24.8 GB, with full SHA-256 verification against each run manifest.
Codex retained the final 3712-second private ledger, verified no active GPU process
or unresolved reservation, and published a shutdown/replacement handoff. Slow
network transfers were resumed from retained fragments without rerunning GPU jobs.
The owner can stop the instance; no next experiment or automatic restart is launched.

## 2026-09-09 UTC — ICLR positioning, independent audits and fixed replication preparation

The owner requested the next experimental plan before starting or replacing a
GPU server, emphasizing ICLR, speed and quality. Codex reviewed the completed
pilot, recent primary papers/author code and the official ICLR 2027 schedule.
The broad within-problem/global-diversity question overlaps recent work; no
novelty or submission-readiness claim is inferred from tighter accounting.
Codex prepared an evidence roadmap centered on a falsifiable semantic-path
intervention, independent pools/seeds and broader evaluation, with later stages
remaining conceptual and subject to design/resource review.

Independent agents implemented CPU audits of displayed arithmetic and neutral
operations, with root integration and a separate code review. The trace checker
uses exact rationals, enumerates input-consumption provenance and distinguishes
unsupported/possibly equivalent traces from definite contradictions. Review
caught and fixed two classification gaps before this code milestone was
published; 21 focused counterexample tests passed. All 4224 stored references
verify and all 1600 primary prediction scores agree with independent parsing.
Matched full-trace verification is Paths 21/GCM 14 of 64; broader is 1/1. The
identity audit retains 384 per-problem records, all four-arm scores, strata and
block outcomes. Both audits are explicitly post hoc for seed17, not new primary
outcomes or evidence about hidden reasoning mechanisms.

Codex froze a separate seed23 preparation from the identical selected problems,
regenerating assignment/order jointly while retaining the original training
recipe and dose. GCM changes its assignment on 196/256 problems; all 1024 update
orders change. Evaluation keeps seed17. Both original and replication datasets
pass pinned-tokenizer verification, with 267456 response tokens and exact
per-update Paths/GCM structure matching. The immutable two-job queue rejects
stale ledgers and reserves 2130 of 3488 remaining process-seconds, preserving the
original 7200-second cumulative authorization. Both new run IDs remain not_run.
No model inference, GPU process, old-server connection, rental, extra budget,
holdout solution generation, final-test evaluation or submission occurred.

Code/config/data/audit provenance, the finite execution plan and migration
instructions are published together. Existing independently verified model
backups and the 3712-second private ledger remain available. Final local test
and artifact-integrity outcomes are recorded in the preparation verification
report; replacement Linux must execute the GNU-timeout integration checks.

Final local verification ran 96 tests: 94 passed, with only the two GNU-timeout
integration checks skipped on macOS. The pinned-tokenizer tests were enabled.
The new completed-pair output audit passed ten focused tests using actual seed17
outputs, including recipe/code mismatch, corruption, missing results and
overwrite counterexamples. All 25 trace-audit and 24 structure-audit source hashes
matched; original seed17 data/configuration had no Git changes. The release
verification report and test log preserve these checks. No GPU work was added.
