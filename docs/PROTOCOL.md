# Protocol v0.5 — fixed pilot complete; C009 CPU matching gate measured

The fixed seed23 replication is complete: matched-dev Paths/GCM final-expression
correctness is 22/64 versus 17/64, with 18/64 versus 16/64 complete traces;
broader final correctness is 1/64 each. See the immutable completed run reports.
C009 subsequently measured fixed-inventory CPU matching loss: 131 raw-support
questions become 67 after exact token matching and 66 after structure matching.
Its global key search reached the predeclared cap; one four-question witness
is not a maximum packing or an approved training set. See
[the report](../reports/FAMILY_MATCHING_20260909.md) and
[C009's frozen design plus appended results](experiments/C009_token_structure_block_matching.md).
No new GPU grid, path-family training comparison or holdout evaluation is approved.

The owner approved staged pilot preparation on 2026-09-08. PILOT_V1.md and
configs/pilot_v1 are authoritative for this finite pilot; older draft issues
below are retained as background. The completed single-seed pilot is reported in
../reports/PILOT_V1_RESULTS.md; no holdout result or general effect is claimed.

## Question and tasks

Does within-problem structural path diversity provide benefits beyond global strategy coverage, exact repetition and surface rendering at matched SFT supervision and update budgets? Arithmetic expression construction is Task A. Typed graph/relational derivations are planned Task B. Real-math external validation is conditional on the controlled core. RL is excluded.

## Conditions

Repeat, Surface, Within-Problem Paths, Global-Coverage Matched; Breadth and Balanced are secondary. Shared anchors and paired seeds are required. Single-path coverage matching must report structural-frequency, length and operator-distribution residuals. The draft's fixed-set single-path R=1 row cannot by itself match the token budget of multiple paths; actual exposure allocation must be specified before any causal comparison. This remains a scientific decision, not a silent sampler default.

Pilot v1 explicitly assigns four presentations per problem per cycle in all
conditions, with four shared cycles. Exact matching is verified on committed
data. Repeat anchors and GCM assignments are seeded. Surface changes complete
sentence frames while preserving calculation content and order.

## Budgets and labels

Primary: supervised response tokens including terminal EOS and optimizer updates. Also record prompt+response processed tokens, padding, actual sample/path exposure, runtime and memory. Do not truncate valid answers or pad useful-token budgets. Do not pack examples initially. Each update's summed shifted target loss is divided by that update's total nonignored response targets, across accumulation microbatches.

## Models

Engineering: Qwen/Qwen2.5-0.5B base. Main: Qwen/Qwen2.5-1.5B base. Second: allenai/OLMo-2-0425-1B base, decisive comparisons only. Freeze exact model/tokenizer revisions. Use the same adaptation method within scientific comparisons. Full-parameter FP32 parameters with BF16 autocast and AdamW is the initial engineering baseline. A larger GPU is preferred to a hidden optimization change if the main model cannot fit.

## Evaluation

Fixed development-only subsets first. Greedy correctness, parse failures, EOS/termination, truncation, output lengths and reference NLL. Sampled pass@k on a common problem set, with independent samples per problem and problem-level aggregation. No final-test tuning; compositional OOD is not implemented by random IID splits.

## Gates

CPU correctness -> token/loss audit -> 32-example overfit and measured profile -> base capability calibration -> reviewed coverage/budget design -> single paired-seed scientific pilot -> human review before more seeds. Engineering smoke tests are not scientific treatment comparisons.


## 2026-09-09 boundary preparation extension

C010/C011/C012 were published before their CPU execution; C013 separately
replaces the computational representation after C010's retained deadline
failure. These are fixed-pool diagnostics, not model outcomes or holdout tuning.
The finite old join is complete, but its population remains strongly selected.

The next proposed finite training pair follows
[the absence-family training plan](ABSENT_BOUNDARY_TRAINING.md) and frozen
[queue](../configs/absent_boundary_seed31/queue.json):128 questions, seed31,
1024 updates,277760 response tokens, Paths/GCM only. Both development sets and
evaluation seed17 remain fixed. Identity absence is a numerical trajectory
label and can include cancellation/computed constants. Claim allocation effects
only within the selected pool; do not treat old models as an identity-removal
control. Report all endpoints and residual numerical exposures. No additional
GPU allowance, main grid or holdout evaluation is authorized by preparation.


## E011 engineering extension —2026-09-09

The owner requested preparation of the next step before server startup. C015
has frozen a small observed C014 subset for a standalone relation engineering
trajectory. Follow [E011](experiments/E011_relation_engineering.md):32 training
worlds,256 fixed updates,strict full-proof/EOS/NLL overfit gate,measured long-
prompt profile,720-second process cap plus15-second guard. This is no scientific
arm comparison or final-test result. The previous arithmetic protocols remain
historical; do not reuse their queues or infer an identity-removal effect.
Original ledger remains5740/7200 used,1460 left; no new budget is authorized.


## E012 engineering extension — 2026-09-09

The owner requested execution of the finite C016 diagnostic ladder. Follow
[E012](experiments/E012_relation_diagnostic_ladder.md): one-edge lookup, original
full graph with supplied route, then original full graph with fixed-reference
training, stopping after any failed/incomplete gate. Every stage uses a fresh
original1.5B base and the frozen256-update recipe. Raw-token and semantic-field
measurements complement strict complete-proof/EOS gates; no scientific effect
or fresh-holdout inference follows. Source/release verification precedes startup.

The current initial ledger is5971/7200 used,1229 remaining,16 receipts,zero
reservations. Maximum three360-second process caps plus15-second guards total
1125. No new allowance, model variant, retry, automatic rental or main grid.
Historical phase-specific balances above remain historical.
