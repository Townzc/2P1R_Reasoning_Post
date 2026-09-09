# Next finite training pair: identity-absent boundary, seed31

This plan implements [C012](experiments/C012_identity_absent_boundary_preparation.md),
which selected the family, scale tiers and recipe before new support outcomes.
It is a development boundary pilot, not the main ICLR experiment or a new budget.
No GPU is needed for preparation. Starting or cloning a server never launches it.

## Question and control

Does assigning four structurally different, legal identity-absent trajectories
to each training question improve the unchanged development endpoints over
assigning one trajectory per question, when both conditions see the same ordered
questions, response tokens and operator-structure histogram on every update?

Paths rotates all four trajectories. GCM repeats one seeded assignment; Latin
assignment across four questions gives the same four structures per update.
Both start independently from the same pinned Qwen2.5-1.5B base. This compares
allocation within the newly selected population. It does not estimate the effect
of removing identity operations: the old models used another population and
exposure distribution and are not a causal control.

Remove requirements for identity-present alternatives, cross-family AC
disjointness and cross-family equal length because neither arm uses that family.
Keep four distinct numerical AC classes and structures, common response length
within each question, and shared four-question structure blocks. Retain legal
ordered-expression semantics, inputs, targets, rendering, tokenizer and splits.

## Frozen training and evaluation

The complete C012 candidate supplies 33 blocks. Sort by group/structure/question
identities, shuffle with a separate Random(31), and take 32 blocks: 128 questions.
Eight complete cycles give 1024 updates and 4096 presentations at batch4 and
microbatch2. Each question appears 32 times: each of four Paths trajectories
eight times, or the one GCM trajectory 32 times. Assignment, order and training
use seed31; evaluation uses seed17. Compatibility Repeat/Surface files support
existing audits only; their models are not in this queue.

Keep full-parameter FP32 AdamW, BF16 autocast, LR5e-5, weight decay0.01,
gradient clip1, sequence and generation limits384, and the existing sampling
settings (four draws, temperature0.7, top-p0.95). Exact token totals are measured
from the materialized schedule and saved in its manifest; do not reuse the old
267456-token total or shorten an arm to a time budget.

Primary endpoint: signed Paths-minus-GCM greedy final-expression correctness
on the unchanged64 matched-development questions. Report all paired cells.
Also always report the unchanged64 broader-development questions. Complete
displayed-trace validity and sampled pass@1/2/4 are separate secondary endpoints.
Use the existing frozen development strata; do not pick favorable categories
after seeing results. Both directions, null and adverse results are retained.
No inference or scoring on the reserved2048 holdout groups is allowed.

## Interpretation and next decisions

Training preparation must include every selection stage, original and excluded
IDs, input/target/template distributions, and scheduled numerical residuals.
Identity absence permits cancellation and computed constants; equal operator
structure is not equal numerical difficulty or proof of semantic strategies.
Selecting32 of one feasible33-block packing is not uniform sampling from all
feasible populations. No weighting can restore eligibility in unsupported strata.

An incomplete dose, mismatched inputs/tokens, nonfinite training or unverifiable
artifacts invalidates that pair; retain its receipts and diagnose before any
replacement. A complete favorable contrast is one exploratory boundary result,
requiring further independent seeds and a broader independently designed task
before an ICLR claim. A null/adverse result narrows the original observation;
it cannot identify identity operations as the cause because the populations also
changed. Report both development sets even if only one is favorable. No outcome
automatically authorizes more GPU work, a main grid or holdout evaluation.

## Launch and resource gate

Only two new run IDs will be queued, one Paths and one GCM. Each has a1050-second
process limit plus15-second guard: total2130 seconds. The unchanged original
ledger has4716/7200 charged and2484 remaining, leaving354 seconds beyond the
reserved pair. Use the actual retained ledger; do not recreate it on a clone.
Previous measured runtimes are estimates, not permission to reduce these caps.

Before execution, fetch the published commit and frozen data, restore and verify
the retained ledger and pinned base model, inspect the environment and idle GPU,
and run the data/queue CPU checks. Reuse the completed calibration only with
the same measured recipe. Require at least18GiB free after setup for two FP32
checkpoints and write headroom; verify backups before deleting duplicates and
ask about expansion if this cannot be met. The 50GB disk need not hold old model
checkpoints, CPU search streams, or a second redundant model cache.

The queue defaults to inspection. Tomorrow's explicit server connection and
launch follow-up is separate from today's preparation. After execution, retain
raw generations, exact dose and receipts, publish compact results, verify
independent checkpoint backups and the cumulative ledger, then carry out the
owner-authorized normal shutdown. Do not delete or release the instance.
