# C014 — Fixed CPU falsification of the relation-transport construction

**Registered before the 10,000-instance audit; 2026-09-09 UTC.** The owner
approved proceeding with the next CPU implementation/verification stage after
P003 and selected Max. No GPU, model inference, paid API, server start or old
reserved-holdout access is involved. This is a diagnostic sandbox, not the
final scientific SFT training/evaluation population.

## Question, prior failures and fixed decision

Can the precise [P003 construction](../CONTROL_REDESIGN_PROPOSAL_20260909.md)
retain every sampled question, supply four disjoint equal-cost evidence routes,
match actual serialized supervision, and survive independent solver, grouping
and predefined shallow-probe checks? Earlier arithmetic matching selected the
population and left numerical exposure residuals. This attempt does not change
or reinterpret those results. Four routes still share one algorithm and one
bare topology; no semantic-strategy or topology-OOD claim is tested.

Use the frozen [configuration](../../configs/diagnostics/relation_transport_c014.json).
The clean-source commit, every execution/test/config source hash, original
tokenizer blob checks, package versions and start time are recorded before
materialization. Published source must equal fetched origin/main. Run IDs and
outputs are immutable. Unit fixtures use seeds above70000 and are development
correctness tests, not observations of this registered population.

## Population and split before augmentation

- Semantic seeds401–500,100 independent indexed draws each: **10,000** worlds.
- Seeds401–480:8,000 probe-fitting worlds. Seeds481–500:2,000 audit worlds.
  Split by seed before views, proof augmentation or probe fitting.
- Hidden node permutations and the source state are IID uniform. Semantic,
  ID/order rendering and intervention RNG streams are separated by SHA256
  domain separation. Finite label counts may differ; no balancing rejection.
- Exactly four four-edge task chains plus four disconnected four-edge
  distractors:34 nodes,32 edges. Edge bijections permit inverse traversal.
  Initial gold task routes all traverse forward.
- All five views belong to the parent: clean, useful deletion (retain one
  uniformly selected useful route; delete one internal edge from each other
  route), irrelevant deletion (three matched-position distractor edits),
  source-state+1 mod5, and coherent target-potential+1 mod5.
- Source edits and the target five-cycle change every answer. Corrupting one
  route and disconnecting all four are CPU negative fixtures, not new model
  classification labels. Keep every failure and every intended world.

ID codebooks use three-digit node IDs100–133 and edge IDs200–231; state symbols
are digits0–4. This costs three digit tokens per ID under the pinned Qwen
tokenizer. No vocabulary extension or artificial proof padding. Preliminary
format/unit fixtures establish feasibility only; all full serialized rows and
deletion views are checked in this attempt. The **1536-token CPU sequence
ceiling** allows the longer graph prompt and is not a GPU context/profile
approval. Use the original pinned Qwen2.5-1.5B tokenizer revision
`8faed761d45a263340a0528343f099c05c9a4323` and unchanged EOS/masking rules.

## Exact correctness and grouping gates

1. The solver reads only exposed text and builds a lifted `(node,state)` graph.
   It must recover the unique answer, four disjoint length-four routes and no
   shorter route, and agree with every stored gold. The trace checker directly
   looks up table rows/columns and rejects nonexistent edges and wrong states.
2. Each of five views is independently solved. Useful deletion leaves one
   route, irrelevant deletion leaves four. Exactly three old certificates
   become invalid by absent-edge use under useful deletion. Endpoint/query
   counterfactuals and disconnected/inconsistent negative fixtures are checked.
3. Exact whole-text tokenization checks prompt boundaries, EOS, masks, input
   digests and all four clean references. Five view prompts and a valid witness
   per view are tokenized. Full useful/irrelevant prompts must match in tokens;
   equal removed-fact count is insufficient. Maximum length is a hard failure,
   never a truncation or question-exclusion instruction.
4. Group identity is defined by an **exact fixed-topology canonical word**:
   exposed source-rooted chain maps (omit target-incident maps), sorted branch
   words, reversal-normalized distractor words, minimized over all120 global
   state permutations. This conservatively groups all source states and all
   coherent endpoint changes, not merely the two observed query variants.
   Entity/edge renaming, row order, inverse notation and distractor reversal
   are removed. Hidden-potential hashes are never the group key. No arbitrary
   independent relabeling of states at internal nodes is quotiented out.
   Canonical words are retained alongside hashes so a hash collision cannot
   be mistaken for equality. Any duplicate family, even within a split, blocks
   this version; do not silently redraw. The10000 intended worlds remain saved.
5. One world per semantic seed receives an additional combined global-state
   relabeling, node/edge renaming, order reversal and inverse-notation check;
   the solver result and canonical key must transform consistently. Unit
   fixtures exhaust all120 permutations and both traversal directions.

## Allocation accounting, not a proposed training dose

Audit one complete Latin cycle on all8,000 probe-fitting worlds. Seed81401
shuffles four-question blocks and assigns a fixed route permutation per block.
Route-multi rotates through four routes; Route-repeat retains one. This yields
8,000 accounting updates,32,000 presentations per arm, four exposures/question;
it does **not** queue an8,000-update training run. Check per-example and per-update
EOS-inclusive supervised/processed tokens and padding with microbatch2, plus
exact route/exposure counts. Report actual response-state, transition, table
and neutral-step residuals. Do not change assignment seed to balance them.

## Frozen shortcut probes and rejection rule

Fit once on8,000 clean parents. Use no audit score for model/feature selection.
Eight deterministic CPU probes receive **only exposed prompt text**:

| Probe | Features and fixed fit |
|---|---|
| Prior | Fitting-label majority, smallest-label tie break. |
| Query state | Five source-state buckets, additive-one counts and per-bucket majority. |
| Topology ridge | Source/target ID one-hots; row-ordered endpoint IDs and endpoint degrees; source-state one-hot. No edge-table values. |
| Endpoint ridge | Separate120-bin permutation histograms of source-incident and target-incident tables, plus source-state one-hot. At radius one these edges do not connect the endpoints. |
| Table-bag ridge | All120 permutation counts plus source-state one-hot. It observes the whole table bag and is **not** covered by the local-information theorem. |
| Ordered-tables ridge |32 fixed row slots ×25 table-entry indicators, padded with zeros for deleted rows; source-state one-hot. No connectivity features. |
| Template1NN | Euclidean nearest neighbor of fitting-standardized table-bag/source-state features; one neighbor, first fitting-row tie break. |
| Three-step prefix | Choose the smallest-ID source neighbor using topology only, follow degree-two continuation for at most three steps; bucket source state and reached state, with a separate dead-end bucket. No fourth table is used. |

Ridge fits use fitting mean/standard deviation, zero-variance scale one, penalty
100, five one-hot targets, centered target intercept, deterministic linear
solve and argmax tie breaking. No hyperparameter tuning or paid/model API.

Evaluate all eight frozen predictors on each of the five views of the same
2,000 audit parents, retaining all80,000 label/prediction pairs. For each of
the **40** view/probe tests, compute the one-sided exact binomial p-value
against accuracy0.2. **Any Bonferroni-adjusted p≤0.01 flags the version for
shortcut investigation and blocks a GPU-readiness conclusion.** Correction
does not assume independence between probes or views; parents, not views,
are the2000 Bernoulli observations within each test. The null is a diagnostic
benchmark; whole-prompt bags/ordered tables may contain real computation.
Investigate a flag by explicit feature ablations and counterfactuals in a new
record, not by deleting the offending probe or selecting another seed.

Report source/target edit prediction changes and joint correctness descriptively.
Passing this finite probe family does not prove that every shortcut is absent,
or that a large model can learn/generalize. A true graph/path solver is a valid
algorithm, not a forbidden shortcut. The exact theoretical information null
applies only to disconnected observed edge subsets under the stated IID law.

## Limits, receipts and stopping

The complete attempt has a1200-second CPU wall deadline, fixed10,000-world
population and no adaptive retries. Save gzip/base64 JSONL shards with raw and
compressed SHA256 hashes; record attempts, labels, references, view/token/group
receipts, allocation schedule, residual histograms and raw probe predictions.
Output is lossless and reconstructible from Git without the remote server.
An exception/deadline retains a failed partial attempt with source hashes.

A separate verification command reads those saved shards, checks historical
published sources, recomputes exposed-table answers and grouping, retokenizes
all40,000 clean references through the existing `encode_row` implementation,
checks all50,000 view prompts, schedule budgets and80,000 raw probe predictions.
It shares the exposed-table verifier module; it is independent of the generator,
not a claim of a third independent solver implementation.

The CPU gate passes only if population retention, all correctness/token/schedule
checks and conservative grouping pass and no probe flag occurs. Every residual
and claim limitation stays visible. No CPU outcome here establishes ICLR novelty,
training feasibility or a broad diversity effect. After successful receipts,
prepare a separate measured engineering/profile and scientific comparison
proposal; ledger remains5740/7200 GPU seconds used,1460 remaining.

Commands, from the repository root with a local Python environment and original
tokenizer path supplied as `TOKENIZER_DIR`:

```bash
python -m scripts.run_relation_cpu_audit --out reports/relation_transport_c014_r1 --tokenizer-dir "$TOKENIZER_DIR"
python -m scripts.verify_relation_cpu_audit --directory reports/relation_transport_c014_r1 --tokenizer-dir "$TOKENIZER_DIR" --out reports/relation_transport_c014_verification.json
```

Results are appended after execution, preserving this registration and the
published execution-source hash. No results are known at registration.
