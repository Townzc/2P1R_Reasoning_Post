# C016 — CPU preparation of a finite diagnostic ladder after E011

Status at registration: CPU preparation authorized; source must be published
before materializing `relation_diagnostics_c016_r1`. No model calls, training,
server contact, GPU reservations, new allowance, or final holdout access.
This is an engineering diagnosis, not a paper experiment or main-grid change.

## Failure motivating the design

E011 finished its fixed 256 updates normally and failed: 0/32 complete training
proofs despite mean target NLL 0.11939. All 333 parseable generated step results
were 2. The five-state gold results varied. Only four of 101 supervised tokens
per full proof encode step results. This is evidence of failed free generation;
it does not establish whether lookup, retrieval, propagation, route discovery,
target multimodality, token weighting, or optimization caused the failure.
The failed run, checkpoint and original task remain preserved. No revised score
or easier diagnostic may retroactively make E011 pass.

## Three constructions and what their comparisons mean

All arms retain the original C015 parents: 32 training worlds (seed 401, first
32) and 16 already observed engineering dev worlds (seed 481, first 16).
The C015 manifest is pinned in `configs/diagnostics/relation_c016.json`.
Group/split comes before derivation; no answer, model prediction, loss, or
balance threshold selects, drops or redraws a parent or transition.

Training anchor route `a_i` is E011's original round-zero assignment, seed
81401. Dev assignment uses the same existing four-question allocation algorithm
and seed on its fixed 16-world list. Each four-world block has route slots
0,1,2,3. This is a fixed **reference trajectory**, not a constant final answer.

| Arm | Input | Target and population | Interpretation and remaining changes |
| --- | --- | --- | --- |
| single_step | One original edge table and its queried input state | All four operations along the assigned route: 128 train rows / 64 dev rows, grouped under 32 / 16 parents. One proof step, final answer, EOS. | Tests learning the primitive with little context. Intermediate input state is supplied explicitly from the original valid trace. Shorter prompts/targets and eight repeats per operation differ from full tasks. |
| given_route | Original full 32-edge graph/query, plus the assigned four oriented edge IDs in order | Exactly the same four-step target as fixed_reference; 32 train / 16 dev. No intermediate states or final answer added to input. | Removes route discovery while retaining table retrieval, four-step propagation and distractors. Hint also adds tokens and directs attention, so any gain is an effect of this information package, not a pure reasoning component. |
| fixed_reference | Byte-identical original full prompt/query | One assigned original valid target per parent, repeated. 32 train / 16 dev. | Closest E011 comparison: fixed targets replace four-target exposure while original question order, seed, dose and lengths stay matched. Route/table/state frequencies change; one engineering seed cannot establish a general causal diversity effect. |

The original task paths all traverse tables forward. Primary single-step model
rows preserve that fact, with no extra reverse-direction model evaluation.
The verifier nevertheless receives exhaustive synthetic CPU tests for all
120 permutations × five inputs × two directions. Those tests are mathematical
software fixtures, not evidence that Qwen can perform reverse lookup.

The dev parents are previously inspected engineering data. S5 has only 120
tables; shared tables and table/input operations across parent splits are
reported explicitly, with no unseen-table or independent-row generalization
claim. Report label/state frequencies and constant-2 accuracy descriptively;
do not rebalance after observing these values. Four derived lookup rows are
four correlated subproblems, not four independent worlds.

## Schedule, objective and measurements

Each arm has 256 updates, batch four, microbatch two: 1,024 presentations,
32 per training parent. Fixed_reference and given_route always use `a_i`.
Single_step replaces E011's `(parent, route_slot)` with `(parent, step_position)`
on the assigned route, using its original multi-slot schedule. Each of four
operations gets eight repeats; all four positions occur once in each update.
Parent order and update order exactly match E011. This matches update/parent
dose, not token budget across all three tasks. Report exact EOS-inclusive
supervision, processed tokens, padding and per-field exposure before any GPU.

The future recipe is the pinned Qwen2.5-1.5B base, fresh for **each** arm, seed
41, FP32 full parameters, BF16 autocast, AdamW 5e-5, weight decay .01, clip 1,
SDPA, nonreentrant gradient checkpointing, TF32 off. Preserve existing prompt
serialization and sum-shifted-target-CE / update-target-count normalization.
No loss reweighting, LoRA, warm start, best checkpoint, early stopping, LR/seed
search, packing or truncation. Starting from E011 or a preceding diagnostic
would confound the comparisons and is disallowed.

Greedy evaluation retains raw generated IDs through first EOS, text, row ID,
strict proof checks, answer-only correctness, EOS and truncation. Evaluate all
dev rows before training, and all train plus dev rows after 256 updates. No
deletion views in this diagnostic ladder. Planned generation counts are 256
single_step and 64 each for given_route and fixed_reference (384 total only
if all phases run). Collect the same measurements even on failures.

**Fixed_reference accepts any legal complete route**, not only the memorized
target string; exact-reference match is secondary. Given_route additionally
requires the supplied oriented edge sequence. Single_step requires its one
legal transition. A correct final answer alone cannot pass. Parent success in
single_step requires all four subproblems; report both 128-row and 32-parent
training denominators, never an artificial sample-size gain.

Prospective teacher-forced measurements use each assigned training reference
once, with total NLL and separate loss/count/correctness for edge IDs, from/to
node IDs, before/after states, final-state value, EOS and remaining response
tokens. Record after-state metrics by step. Position j uses logits[j-1]; prompt
positions are excluded. This is gold-prefix correctness, separate from free
generation. Fixed-reference NLL averages a different target distribution from
E011's 128-reference NLL and is not directly an improvement statistic.
Semantic masks measure loss dilution; they do not change training weights.

Inspect all parseable generated steps for local lookup validity even when the
proof is truncated/missing a final line. Retain grounded-line denominators,
all after-state histograms and first proof failure reasons. Local validity
conditional on the line's own input does not establish query correctness or
path continuity. Never discard malformed generations from headline scores.

## Prospective order, stopping and budget (not a launch authorization)

Run single_step first. Its small context offers the least expensive basic
capability check. Continue to given_route only on a complete training gate;
continue to fixed_reference only if given_route passes. Each gate requires:
all 256 updates, complete 64-update profile after eight warmup updates, every
training proof correct with EOS, zero truncations, assigned-reference NLL<.2,
finite measurements and independently audited raw outputs. Strict proof
requirements are 128/128 (all 32 parents) for lookup and 32/32 for the others.
Dev values are descriptive and never determine continuation or checkpoint
selection. A timeout, OOM, incomplete dose or missing outputs is not a learned
failure; retain it as a resource/implementation failure and stop, with no retry.

| First failure / outcome | Permissible interpretation | Next action |
| --- | --- | --- |
| Lookup fails | This frozen recipe has not learned even the short primitive on these retained examples. Does not prove table lookup intrinsically hard. | Inspect formatting versus state-field losses and raw lines; review optimization/target design on CPU. Stop larger jobs. |
| Lookup passes; route given fails | Long-context retrieval and/or multistep propagation or their optimization remains unresolved. | Design a later control separating context length from propagation; do not call this a path-search failure. |
| Both pass; full fixed reference fails | Additional burden from discovering a route without the hint is a plausible contributor; hint/input changes remain a caveat. | Review route supervision and input use, without claiming unique causal localization. |
| All pass; E011 remains failed | Fixed-trajectory training is a viable engineering starting point; differences in target multiplicity/exposure are candidates. | Review a new matched scientific pilot and independent groups. No automatic resumption of the old grid. |

Current ledger is **5971/7200 seconds used, 16 receipts, zero reservations,
1229 remaining**, with the exact hash in the proposal JSON. Maximum proposed
reservation: three × (360-second process cap + 15-second guard) = 1125 seconds,
leaving 104 seconds even if all caps are consumed. These caps are limits, not
runtime predictions or a new authorization. No reservation is made on CPU.
Later job guards must recheck the current receipt chain under lock; after the
first job the initial ledger hash is historical, never reset it for the next.
No shortened jobs, automatic retries or fourth arm.

Before requesting server startup for execution, implement and publish the
diagnostic model runner/raw-output auditor and review the concrete launch
scheme with the owner. This CPU package deliberately has no GPU launch path.
On a later owner-started instance verify its Git commit, pinned environment,
base and tokenizer, retained current ledger and free disk. Keep one checkpoint
slot at a time only after each preceding checkpoint has a verified independent
backup; do not remove sole copies or change rented storage without review.
Reassess free disk on that actual instance instead of inventing current usage.

## Reproduction and evidence boundaries

Publish source/config/tests/this registration before the one immutable CPU
attempt. `python -m scripts.prepare_relation_diagnostics --tokenizer-dir <pinned-local-cache>`
verifies C015, derives all 288 rows, computes exact masks/budgets and runs a
separate reconstruction auditor. Output refuses overwrite and has a 300-second
CPU deadline. The independent auditor imports the original source and tested
tokenizer/scorer, but **does not import the new diagnostic builder**. It recovers
training anchors from archived E011 update order and reconstructs each derived
query/reference. Shared tokenization/scoring dependencies remain an explicit
limit to implementation independence.

`python -m scripts.verify_relation_diagnostics --tokenizer-dir <pinned-local-cache> --output <new-receipt.json>`
checks source/history and artifact hashes and reproduces the entire audit.
Also verify from a clean checkout of the published source/data. Synthetic
tests cover exhaustive forward/inverse maps, wrong states, valid alternative
routes, missing/malformed route hints, truncation, EOS, parent denominators,
lineage/schedule/mask corruption and field-loss masking. Do not claim CPU
fixture success as a GPU result, estimated model accuracy, or ICLR readiness.
