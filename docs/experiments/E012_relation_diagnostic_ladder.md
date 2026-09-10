# E012 — finite diagnostic ladder after failed relation overfitting

The owner asked to begin the next experiment after reviewing C016 and switching
to Max, and explicitly requested continuously maintained rationale, historical
results and analysis records. This authorizes the previously proposed finite
engineering ladder within the remaining original allowance. It does not
authorize a main grid, new allowance, extra rental, alternative model, holdout
evaluation or a search over seeds/learning rates. Prepare and publish this
execution release before requesting an owner-started A800.

## Prior evidence and questions

[E011](../../reports/RELATION_E011_RESULTS.md) completed 256 updates with the
original multi-reference allocation. Complete train proofs were 0/32 despite
mean target NLL 0.11939; all 333 parseable generated after-states were 2. There
was no OOM, nonfinite gradient, shortened dose or training truncation. Retain
that failure; CPU data checks cannot turn it into a successful model result.

[C016](../../reports/RELATION_C016_CPU_READY.md) freezes 288 rows from those
same 32 train / 16 observed dev parents, with independent exposed-fact checks,
exact masks/dose and 53 passing CPU tests. Train step states are 28/16/31/31/22
for values 0..4. The primary lookup train/dev sets share 34 tables and 13
table/input operations. These facts motivate diagnosis, not a generalization
claim or an output-selected rebalance.

The finite questions are: can the recipe learn the one-edge operation; can it
propagate states when a route is supplied among the original distractors; and
can it learn a complete original question with one consistent reference? These
tests identify an engineering failure boundary. They do not uniquely isolate
loss dilution, route diversity, attention, composition or optimization.

## Immutable inputs and stage order

Use `configs/relation_diagnostics_e012/execution.json` and the unchanged C016
release. The data manifest SHA256 is
`cb923a3e11817682f77b4116d7524e615bdffee29e04e5848b3815352aa8133e`.
The final C016 release-file SHA256 is
`22f1f0d1b4c4b8217147dd0f314f6f565b208538267756583020d51a1a51b535`.
Do not regenerate or alter any parent, assigned route, input, target or order.

| Order / registered run | Train / dev rows | Processed / supervised training tokens | Main purpose |
| --- | ---: | ---: | --- |
| 1 — `relation_single_step_e012_r1` | 128 / 64 | 169,984 / 29,696 | One-edge table lookup; all four operations from each assigned route |
| 2 — `relation_given_route_e012_r1` | 32 / 16 | 1,252,352 / 103,424 | Original 32-edge graph plus oriented route hint; lookup/retrieval/propagation retained |
| 3 — `relation_fixed_reference_e012_r1` | 32 / 16 | 1,164,288 / 103,424 | Original byte-identical full prompt, with one assigned reference repeated |

Every stage uses 256 updates, batch four, microbatch two, 1,024 presentations
and 32 presentations per parent. Lookup subproblems each receive eight repeats;
full references receive 32. Only fixed_reference matches E011's exact total
token accounting as well as parent/update order. Given_route adds 86 prompt
tokens but preserves the fixed target. Lookup changes context length, target
length, per-operation exposure and final-state duplication. Report all of these
limits; do not compare raw percentages as controlled treatment effects.

Launch **one stage at a time**. Continue only after the preceding stage's
complete training gate and raw-output audit pass, its compact outputs are
published, and its independent checkpoint backup matches every file hash.
No automatic launch of the next stage. The owner has authorized the finite
conditional sequence; another budget approval is unnecessary for a passing
continuation within its cap. Server availability remains a separate prerequisite.

## Model and fixed dose

Use fresh `Qwen/Qwen2.5-1.5B` base, revision
`8faed761d45a263340a0528343f099c05c9a4323`, separately initialized for each stage.
Never load E011 or a preceding diagnostic's fine-tuned checkpoint as the base.
All model/tokenizer files must match the original lock. Keep the recorded Linux
Python 3.12 / PyTorch 2.8.0+cu128 training environment, one idle A800 80GB and
at least 12 GiB free after setup. Check actual disk usage; do not silently alter
the FP32 recipe to fit storage or memory.

Parameters FP32; BF16 autocast; all parameters trained; AdamW LR 5e-5, weight
decay .01, betas (.9,.999), epsilon 1e-8, foreach false; gradient clip 1;
nonreentrant gradient checkpointing; SDPA; TF32 off; training seed 41. Preserve
the original exact `Problem:` / `Solution:` serialization, prompt/pad masking,
supervised terminal EOS, no packing/truncation, and summed shifted target CE
divided by all supervised tokens in the update. Field measurements do not
reweight the loss. Profile updates 9–72; train exactly 256 without early stopping.

## Free-generation and teacher-forced measurements

Baseline: every observed dev row once before training. Final: every train and
dev row once. Greedy, one beam, batch four. Maximum new tokens are 32 for
lookup and 128 for the others; all gold targets plus EOS fit. This is 256,
64 and 64 generations respectively if all three stages execute. No deletion
views, sampled pass@k, intermediate evaluation, checkpoint selection or final test.

Retain every prompt/reference identity, raw generated IDs through first EOS,
decoded text, strict proof/answer/EOS/truncation checks and parseable-line lookup
diagnostics. Missing final lines must not conceal an earlier local lookup error.
Fixed_reference accepts any legal route; given_route must follow the explicitly
provided oriented sequence. Lookup parent success requires all four subproblems.
Malformed outputs stay in the denominator. Correct final answers alone cannot
pass a complete-proof gate.

The pinned model output vocabulary has 151,936 positions, including positions
without tokenizer entries. Retain such generated IDs as model failures with
`unmapped_output_token` proof status; never let decoder omission make a proof
appear valid. This strict stream check supplements the frozen text grammar.
Tokenizer and model-vocabulary sizes are recorded separately.

Final teacher-forced measurement evaluates every assigned training reference
once. Save per-target position, target ID, argmax model ID and full-vocabulary
CE, bound to exact input IDs and response hashes. Position j uses logits[j-1].
Recompute the disjoint edge-ID, from-node, before-state, to-node, after-state,
final-state, EOS and remaining-token aggregates and after-state position metrics.
Record counts and correctness as well as means. The auditor checks alignment,
finite CE, necessary top-one/CE consistency and every aggregate. It cannot
independently reconstruct original logits from these scalar records; that
limitation remains explicit. Numerical CPU tests verify the actual measurement
routine's shift and padding behavior against direct cross-entropy calculations.

Gold-prefix accuracy is separate from free generation. The assigned-reference
NLL distribution differs from E011's four-reference average. A low total mean
or a favorable field statistic cannot override failed complete proofs.

## Gates and interpretation of failures

Require the complete population and 256-update dose, all 64 profile updates,
finite history/measurements, 128/128 complete EOS-terminated train proofs for
lookup (all 32 parents) or 32/32 for full tasks, no training-output truncation,
and assigned-reference NLL < .2. Development values never select a checkpoint
or decide continuation. A normally completed learning failure is independently
verifiable evidence of a failed gate; it is not an infrastructure failure.

On OOM, timeout, nonfinite values, incomplete dose or missing artifacts, retain
the receipt, exception, stdout, any raw outputs, partial history and partial
accounting. Stop; no retry or shorter fallback. Do not interpret an incomplete
optimization trajectory as a completed learning experiment.

- Lookup fails: the short frozen recipe/dose has not passed. Inspect format,
  after-state loss and raw lines before redesign; do not claim primitive
  impossibility or automatically spend on larger contexts.
- Lookup passes but given_route fails: context/retrieval/propagation and their
  optimization remain mixed causes. A later isolating control needs review.
- Both pass but full fixed-reference fails: route discovery without hints is
  a candidate burden; additional hint information and attention remain caveats.
- All pass while E011 remains failed: fixed-trajectory training becomes a viable
  engineering starting point. Review a new scientific design and independent
  groups; no automatic resumption of a previous pilot/grid.

## Budget, durability and source identity

Initial **5971/7200 process seconds used, 1229 left**, 16 exact public receipts,
zero reservations. Initial private-ledger SHA256:
`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
Each job gets a 360-second process cap plus 15-second guard. All three maximum
reservations total 1125 seconds, leaving 104. These are ceilings, not runtime
estimates or a new allowance. Idle rental time, downloads and backup transfers
remain separately billable; the old 4090 price is not an A800 price estimate.

The launcher verifies the 16 historical receipts and exact ordered subsequent
E012 receipts. After each job it expects the updated ledger, not the original
hash. The entire remaining conditional ladder must fit. The existing watchdog
rechecks that exact latest ledger hash under its lock, reserves the full cap,
and rejects absent/stale ledgers, unresolved reservations or used run IDs.
Only one authorized instance/job may operate across all copies; a local lock
does not enforce a global distributed budget. Independently reconcile the
latest local backup before using a clone.

The default command only inspects inputs/accounting. Actual execution requires
`--execute` and `--expected-published-commit` equal to the GitHub commit just
verified by the orchestrator and synchronized to the server. This supports
servers receiving a verified Git bundle when direct GitHub access fails.
Do not infer latest source from an old clone's cached origin/main alone. Source,
configuration, input hashes and the release are rechecked in the worker.

Checkpoint writes/hashes are inside the bounded process. Raw-output re-audit,
Git publication and independent backups follow outside that GPU-process meter.
No automatic deletion, storage expansion, rental, retry or continuation. If
disk is tight, verify an independent backup before considering redundant
checkpoint cleanup. A backup receipt must contain `status:
verified_independent_backup`, run ID, checkpoint-manifest SHA256, the identical
per-file byte/hash map, file count and total bytes, and be published as
`reports/<run_id>_checkpoint_backup.json`. The server can verify this receipt
against its manifest; actual destination file hashing is done on the independent
copy, not claimed from receipt shape alone.

## Publication, commands and record maintenance

Publish source/config/tests/this registration, then run the CPU release preparer:

```sh
python -m scripts.prepare_relation_diagnostic_execution \
  --tokenizer-dir "$RELATION_TOKENIZER" --ledger "$RELATION_LEDGER"
```

It verifies all C016 inputs and the current ledger and writes an immutable
`configs/relation_diagnostics_e012/release.json`; it does not load model weights
or launch a process. Publish that release, recheck from a clean checkout and
finish CPU regression checks before requesting startup. Two GNU-timeout
integration tests are mandatory on Linux before the first actual model job.

On the verified owner-started instance, use the default inspection command
first, then append execution only with the independently verified commit:

```sh
python -m scripts.run_relation_diagnostics --arm single_step \
  --tokenizer-dir "$RELATION_TOKENIZER" --ledger "$RELATION_LEDGER"
python -m scripts.run_relation_diagnostics --arm single_step \
  --tokenizer-dir "$RELATION_TOKENIZER" --ledger "$RELATION_LEDGER" \
  --execute --expected-published-commit "$RELATION_PUBLISHED_COMMIT"
```

Later arm names are `given_route` and `fixed_reference`, subject to all gates.
Re-audit compact outputs independently with
`scripts.audit_relation_diagnostic_outputs`, then run
`python -m scripts.build_registry` and
`python -m scripts.update_compute_accounting --ledger "$RELATION_LEDGER"`.
These mutable summary files are rebuilt/reconciled from immutable public run
receipts; the live private ledger is never modified by summary generation.

For every completed stage or failure update the research journal (question,
motivation, design, results, analysis, decision), detailed phase report,
decisions, status, README, AI-use log, artifact inventory, compute accounting,
run registry and next-session handoff. Keep earlier contradictory/failed
evidence visible and mark not-run stages explicitly. Publish milestones before
any server replacement or declaring it disposable. No result is a substitute
for ICLR-level novelty, causal controls and independent generalization evidence.
