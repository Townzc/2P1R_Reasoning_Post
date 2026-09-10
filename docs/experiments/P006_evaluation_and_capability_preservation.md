# P006: fix task completion, then test retained learning

2026-09-10 UTC. Concrete review proposal after E016; CPU planning is authorized.
**No GPU job is queued or training release is ready. Keep the server off.**
Original E016 scores and failed gates remain unchanged. The user asked to
improve evaluation and capability preservation, not to start a scientific grid.
[Exact review-only configuration](../../configs/diagnostics/real_math_p006_proposal.json)
records all proposed thresholds, LR values, sample identities and rental caps.
[Local consistency checks](../../reports/real_math_p006_proposal_checks.json)
verify the declared arithmetic and unchanged historical dependencies; they do
not establish GPU stopping or training readiness.

## What is ready and what is proposed

[C020](../../reports/REAL_MATH_C020_COMPLETION_AUDIT.md) independently checks160
saved streams.13/14 E016 base truncations begin after a new-question header.
The CPU candidate counts39/64 correct first-task prefixes versus E0150/64;
these are post-hoc counts, not GPU results. A CPU completion oracle,16 fixtures,
an independent verifier, exact proposed dose and adapter-size estimates exist.
Production batched stopping, a training runner and frozen execution releases do
not yet exist. The432 unused dev parents remain untouched by new evaluation.

## Stage A: E017 stop-only implementation calibration

Recommended first GPU job after reviewed implementation: original pinned base,
the same64 observed E016 parents (ranks17–80),64 greedy generations,zero training.
Do not replay E015: none of its64 saved streams has a new-question boundary and
stopping alone leaves its zero correct count unchanged in C020.

Keep prompt, tokenizer, native EOS, precision, seed17, batch8, context1024,
768-token cap and numeric extractor unchanged. Add only per-row stopping at the
first complete header recognized by the existing line-anchored boundary rule.
Record raw prefix tokens including the trigger, rendered pre-boundary text and
stop reason. Boundary stopping never fabricates EOS. Do not stop at the first
answer marker, search unmarked reasoning for the gold, or silently add few-shot
examples. Compare native-EOS and new task-completion metrics explicitly.

Before startup, the production implementation must pass CPU/real-token tests for
split delimiters, prompt boundaries, mixed finished/unfinished batch members,
native EOS, special tokens, contradictions, and output-file/auditor agreement.
Keep batch membership/order fixed with no row compaction. The independent CPU
oracle must reproduce every recorded stop from the actual new token stream.
Compare retained prefixes with E016 descriptively and preserve any numerical
differences; old streams are not promises of exact GPU replay.

Proposed operational usability screen: all64 valid records, at least48 parsed,
at least8 task-answer-correct and at most8 actual length-cap stops; zero falsely
reported EOS or invalid stop receipts. These integer thresholds are screening
tolerances, not statistical proof. The completion definition is a prospective
protocol change; it must not retroactively turn E016 into a passed experiment.
Failure ends this stage without a prompt sweep or training. If prompt formatting
remains the obstacle, a single explicitly registered demonstration/format
alternative is a later choice with its own token/context audit.

Cap240+15=255 process seconds within279 remaining, leaving at least24. Plan a
12-minute target and15-minute whole-rental ceiling (CNY1.60 target/CNY2 ceiling).
At admission require555 seconds left:255 guarded process,120 compact export and
180 shutdown/slack. Stop on failed preflight; set a provider backstop before
the model; export small outputs/current ledger, then confirm shutdown. No
checkpoint or full-weight transfer. Token-tail savings are not budget guarantees.

## Stage B: E018 one LoRA capability-preservation recipe

Only after StageA establishes a usable contract and a separately reviewed
training release. Start from the original pinned base with a fresh adapter;
never continue from E015. This changes data breadth, repetition, adaptation,
batch and LR together: it is a recipe feasibility calibration, not a causal
estimate of any one change versus E015.

| Factor | Proposed fixed value |
|---|---|
| Training data | Existing C017 single-response anchors; nominal256 parents,253 available,3 unavailable retained in coverage accounting |
| Exposure |2 complete epochs;506 presentations;64 updates;77,192 supervised tokens;109,434 nonpadding processed tokens |
| Batching |8 examples/update,microbatch1;each epoch ends with5 examples;normalize by total supervised tokens in the update;no packing or target truncation |
| Adaptation |LoRA rank16,alpha32,dropout0,bias none;q/k/v/o/gate/up/down adapters;all base embeddings,head,norms and weights frozen |
| Precision |Original FP32 base and adapter weights,BF16 autocast,SDPA,TF32 off;no quantization or silent model substitution |
| Optimizer |Fresh AdamW over adapters only,betas(0.9,0.999),eps1e-8,weight decay0,clip norm1.0 |
| LR |Peak1e-4;4-step linear warmup;cosine decay oversteps5–64 to1e-5;all64 updates nonzero;sum of declared LR0.003505 |
| Randomness |Initialization/training seed17;epoch permutations17/18;record actual parameter names and input order |
| Endpoint |Final fixed64-update endpoint only;no best-checkpoint selection,rank/LR sweep,teacher generation or automatic retry |

The exact metadata schedule and proposed parameter shapes are in
[C020 dose](../../reports/real_math_c020_completion_r1/proposed_training_dose.json).
The proposal configuration also enumerates all64 LR values. Adapters are
estimated at18,464,768 trainable parameters/70.44MiB FP32 tensor bytes, excluding
serialization metadata and optimizer state. Actual PEFT version, compatible
offline wheels, parameter inventory, frozen-base equality, zero-adapter identity,
save/reload equality and actual serialized size must be checked before release.
LoRA is not assumed faster or more capable simply because its export is smaller.

Before training, reconstruct all253 selected prompt/response bytes from the
cached source, verify response hashes/token masks/EOS and group disjointness,
and inspect a fixed32-row hash-order quality sample. Record existing ambiguity
flags. A discovered material reference/solution problem triggers a documented
new data decision; no silent correction, post-outcome filtering or backfill.
The schedule currently certifies metadata counts only, not complete reasoning.
Both the quality sample and final training-decode sample are fixed now by
separate SHA256 namespaces and32 IDs each in the proposal configuration.

Measure base and final adapter on the same64 observed development parents under
the reviewed StageA contract. Also measure reference NLL on all253 training
anchors before/after and decode a fixed32-parent training subset at the final
endpoint. Maximum160 free generations; reference-conditioned measurements are
separate and never counted as free-generation successes.

Proposed paired retention screen: the base passes StageA-style criteria; the
adapter meets the same usability screen, and at least90% of the questions the
base answered correctly remain correct for the adapter. Use the exact integer
rule `10 * both_correct >= 9 * base_correct`, plus net correct loss no greater
than4. New successes cannot offset lost answers in the first rule. Always
publish both-correct, lost, gained and both-wrong counts. Require a learning
signal as well:64 positive-LR updates, finite losses/gradients, changed adapter
weights, unchanged base weights and training reference NLL at least10% below
the base. Pool NLL by total unmasked target tokens, including EOS, across all253
anchors; use identical serialization/masks before and after.
This prevents an unchanged model from passing solely by doing nothing. NLL is
only a learning indicator; it is not a reasoning score or a return to the
32-example near-zero-loss memorization objective. Report every metric even on
failure. Operational tolerances are not powered noninferiority claims.
Report question-level paired bootstrap95% intervals for accuracy difference
and retained fraction (10,000 paired resamples,seed17020); count resamples with
zero baseline successes as undefined. This is descriptive development
uncertainty, not a statistical certification that forgetting is absent.

Proposed cap900+15=915 process seconds and30-minute whole-rental ceiling/CNY4,
including startup,evaluation,hashes,export and shutdown. Require1215 seconds
remaining at admission. This cap is conservative planning, not a measured
LoRA speed. Stop on budget/failure; no second recipe in the same rental.
Export compact results first. Attempt the small adapter export only within a
120-second whole-copy bound with measured adequate throughput; otherwise retain
it on the stopped volume and use a separate no-card recovery window. Hash every
adapter file and retain the exact base revision/config; never claim a partial
export is complete or release an instance with unique unbacked state.

## Stage C: one untouched development confirmation, then scientific review

If the fixed StageB endpoint passes, freeze that recipe without further tuning.
Propose64 development parents at ranks81–144, selected independently of
responses/success, and base versus this same adapter (128 generations). They
have not been evaluated or opened anew in this phase. Freeze all exact inputs
before generation; use the same operational retention and parse/cap rules.
Afterward368 development parents remain reserved. If it fails, publish failure
and do not tweak/retest the same set as fresh confirmation.

Proposed cap420+15=435 process seconds;20-minute whole-rental ceiling/CNY2.67.
Require735 seconds remaining at admission:435 process,120 export,180 shutdown.
These64 parents are development confirmation, not final test or adequate power
for a small allocation effect. A scientific comparison still needs a fixed
question-level uncertainty/power plan and its own complete-phase review.
Later allocation arms must share the selected adaptation/optimizer/evaluation
recipe and each start afresh from the same base. Do not initialize them from
the calibration adapter. Calibration on single-response anchors is itself a
selection limitation and must remain in the reported selection history.

StageA fits the historical ledger. StagesB+C require a separately recorded
phase allowance of at most1350 process seconds, linked to the current20-receipt
ledger hash; preserve the old7200-second configuration and every receipt. Do
not reset the ledger or silently edit a frozen budget dependency. Within the
existing CNY3000 overall ceiling, these three optional GPU windows total at
most aboutCNY8.67 in planned rental time before fees and separate preservation.
This is a review proposal, not an additional executed allowance or auto-queue.

## Alternatives and explicit stopping rules

| Observation after the fixed candidate | One next route for review | Main tradeoff |
|---|---|---|
| LoRA retains answers but shows weak learning |Same253-parent/2-epoch full SFT at peak1e-5 with its own frozen warmup/decay and retention check |Greater adaptation capacity; larger optimizer/checkpoint cost and renewed forgetting risk |
| Substantive capability loss persists |HFT with an explicit tensor-selection mask, or a small verified replay mixture; select one |Mask needs exact scope; replay changes the training token allocation and adds generation/verification cost |
| Incumbent still lacks a usable evaluation contract |One task-matched small-model or one fixed demonstration-prompt calibration |A new baseline and all-arm consistency are required; no silent Instruct/Math swap |

The [ICLR/ACL/TMLR review](../../reports/LITERATURE_CAPABILITY_PRESERVATION_20260910.md)
motivates these routes but proves none will work here. Do not automatically run
all alternatives. The512-step memorization fallback and the allocation grid stay
paused. All mathematical-retention claims are limited to this evaluation;
broader knowledge/language retention requires separate out-of-domain tests.

E015's independent full checkpoint backup remains incomplete. Its prior server
hash audit and confirmed-off state are retained; do not reopen the GPU or dispose
of the instance for this planning work. Follow the separate no-card recovery
plan before its retention deadline. Current ledger SHA256:
`c33623087b752f0bbc82a32bb90ac8f11a489fc910b2ebdaacb57000c0893106`.
