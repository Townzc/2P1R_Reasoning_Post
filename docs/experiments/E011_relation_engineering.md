# E011 — relation overfit and measured profile; C015 input preparation

Status at source registration: CPU implementation prepared; inputs not yet
materialized and GPU run **not_run**. This is repository provenance before
execution, not external preregistration. Append later evidence without rewriting
the original design. The owner requested preparation before starting a server.
Max is appropriate for this bounded implementation and verification task.

## Motivation and scope

C009–C013 exposed severe arithmetic support/selection constraints; E010 produced
weak, endpoint-dependent results. C014's constructive relation task retained
10,000 worlds and passed its declared CPU gates. Those facts do not establish
learnability by the pinned base model or the cost of its 1137-token serialization.
Old arithmetic throughput at a384-token cap cannot answer either question.

One small engineering trajectory now tests whether the unchanged1.5B training
recipe can learn complete four-step certificates on32 fixed prompts, and measures
its actual memory and throughput. This does **not** compare allocation arms,
test a treatment effect, establish novelty, or authorize a main grid. A passing
overfit gate can reflect memorization and is necessary but insufficient.

## C015 CPU preparation, fixed before materialization

Read published C014 archives; select seed401 indices0–31 from `probe_fit` for
training and seed481 indices0–15 from `probe_audit` for development diagnostics.
No score, label balance, token length or difficulty filtering; no replacement.
Every selected record must exactly equal its original archived record. Verify
exposed-table labels, all four proofs, counterfactual/deletion identities, exact
token masks and conservative world groups again. No arithmetic holdout access.
These worlds are part of an observed CPU sandbox, never an untouched final test.

Write immutable `runs/relation_engineering_c015_r1` with48 losslessly compressed
worlds, a256-update schedule, exact exposure/token accounting, source hashes and
a manifest. The launcher rederives model-facing rows from this archive, compares
them to the source shards and rechecks token accounting. Publish source/config
first, then compact inputs and a release hash before requesting a server.

## Fixed model and training recipe

- Fresh `Qwen/Qwen2.5-1.5B` base at revision
  `8faed761d45a263340a0528343f099c05c9a4323`; all original snapshot files verified.
- Full-parameter FP32, BF16 CUDA autocast, SDPA, nonreentrant gradient
  checkpointing, TF32 disabled. AdamW lr5e-5, weight decay.01, foreachFalse,
  gradient clipping1.0; constant learning rate, no warm-start or adaptation change.
- Training/model seed41; allocation/order seed81401.32 questions × four complete
  routes. Eight cycles of the C014 Latin route-slot allocation, **multi-route only**:
  256 updates, batch4, microbatch2,1024 presentations, each route8 times.
- Exact expected budgets:103,424 EOS-inclusive supervised tokens,1,164,288
  nonpadding processed tokens, zero padding. Each reference101 supervised tokens
  and1137 total. Per-update loss sums shifted valid-token CE over both microbatches
  and divides by that update's response-token count. No truncation or packing.
- Serialization stays `Problem: {prompt}\nSolution:\n{response}` plus terminal
  EOS; max context1536. PAD is set to EOS and attention/label masks distinguish it.
- Full256 updates, final-only evaluation; no early success stop, dev selection,
  dose extension, optimizer fallback, second attempt or seed search.

## Evaluation and engineering gate

Greedy generation only, beam1,128 new tokens maximum, batch4, left-padded prompts.
Record every generated token ID through the first EOS, raw text, length,
termination and score. Do not remove internal special tokens or repair output.
Only outer ASCII whitespace is stripped for scoring. Exact exposed-table proof
verification accepts any legal complete route, not only a chosen reference.

Before training:16 clean development prompts. After training:32 clean training
prompts and16 development parents × clean/useful-delete/irrelevant-delete
views (48 prompts). **96 total generations**, no sampled pass@k. Compute final
teacher-forced NLL on all128 training references, each once. Development scores
are descriptive; each set of three views shares a parent, not independent units.
Useful/irrelevant deletion is diagnostic here; one overfit arm supplies no causal
allocation contrast. No new source/target model counterfactual evaluation this run.

Engineering gate requires all256 updates, complete profile, **32/32 complete
valid EOS-terminated training proofs**, zero training truncations and training
reference NLL<.2. Answer-only correctness is separately reported and cannot pass
the gate. Exact text-match is not required because all four routes are valid.
Even zero dev correctness must be retained; no threshold selects the dataset.

Exclude updates1–8 from throughput; measure updates9–72 (64 updates) on the
same training trajectory. Report response and processed tokens/second, actual
window seconds and peak allocated/reserved GPU memory across training. Retain
each update's timing, loss, gradient norm and tokens. Report final evaluation
peak separately. These measures exclude setup/generation/checkpoint time;
the cumulative process receipt includes those operations inside the watchdog.

## Resource and migration rules

Original7200-second single-GPU allowance:5740 used,1460 left,15 completed
receipts,zero reservations. Launch **one** `relation_overfit_e011_r1` process
with720-second watchdog plus15-second conservative guard: maximum reservation
735,leaving725 unreserved. This cap is not a measured runtime forecast and is
not a new budget. Charge actual rounded process time using the existing locked
ledger. CPU preparation adds zero GPU process-seconds. Instance idle billing and
storage are separate; A800 price must not be inferred from the old4090 quote.

Do not contact/start a server during preparation. Once the owner starts/provides
an A80080GB, fetch current Git, require the exact retained15-receipt ledger hash,
check the pinned Linux environment and original base, idle GPU, GNU timeout and
at least12GiB free on the run filesystem **after** cache/environment setup. A50GB
data disk may suffice but this must be measured. Save one approximately6.2GB FP32
checkpoint plus tokenizer; preserve earlier uniquely required artifacts. Cleanup
requires already verified independent copies; ask for expansion if necessary.

The launcher defaults to inspection. It rejects absent/stale ledger, duplicate
run ID, unresolved reservation, changed data/source/config and inability to
reserve the full job. It never starts a server or automatically retries. An OOM,
nonfinite gradient, timeout, incomplete dose or failed gate is a retained failed
or inconclusive engineering attempt, not permission to change the recipe.

After any run, retrieve compact outputs and receipt, reconcile the cumulative
ledger against all prior receipts, independently re-score outputs on CPU and
verify checkpoint files plus a separate backup before declaring the server
disposable. Save weights only, not optimizer/RNG resume state. Publish failures
as well as successes. Follow the owner's existing normal-shutdown preference
after preservation; a training-process timeout itself does not power off the
provider instance. No new scientific phase follows automatically.

## Decision after the run

If completion/gate/profile fails, classify the actual failure (budget, memory,
optimization or output validity) and prepare a bounded repair proposal. If the
gate passes, examine base versus final development behavior and failure types,
then prepare a separately reviewed paired multi-route/repeated-route pilot with
fresh frozen scientific groups and its complete cost. Do not use favorable
engineering cases to design the primary comparison or claim ICLR readiness.

## Execution commands

All commands run from the repository root in the appropriate recorded Python
environment. `TOKENIZER_DIR` is a local pinned snapshot path, not a credential.

```bash
# CPU source milestone only; refuses an existing data directory.
python -m scripts.prepare_relation_engineering --tokenizer-dir "$TOKENIZER_DIR"
# Once compact inputs and release are published, inspection does not launch a model.
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --tokenizer-dir "$TOKENIZER_DIR"
# Only on the owner-started A800, after migration checks and mandatory Linux tests:
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --execute
python -m scripts.audit_relation_engineering_outputs --run-dir runs/relation_overfit_e011_r1 --tokenizer-dir "$TOKENIZER_DIR" --out reports/relation_e011_output_verification_r1.json
```

Results at source registration: **none**. CPU release verification and actual
GPU outcomes belong in separate immutable receipts and appended journal entries.


## Appended C015 completion —2026-09-09; E011 remains not_run

The source registration and executable code were published at
`8eeb0f9883759a69ca42540932b98d71b2c64414` before extraction. The fixed48 worlds
were retained; independent verification rechecked192 references and240 views,
original archive identities,world separation and exact dose. Input manifest
SHA256:`ddb0068a2ddef8150948b7f8eaf0f2b86d3c3f9a42268c7d7725f44ee1afb854`.
Extraction0.824s; independent check3.374s.42 focused tests:40 pass,2 mandatory
GNU-timeout integrations deferred to Linux. No real model execution/server
contact/GPU charge/reservation occurred. See [release report](../../reports/RELATION_E011_READY.md)
and [CPU receipt](../../reports/relation_engineering_c015_verification.json).
The owner can now start/provide A800 for the frozen engineering gate.


## Appended E011 result —2026-09-09

The owner started A800 and authorized execution. Clean published33820d9
completed the fixed256 updates and charged231 seconds. The gate fails:
0/32 complete train proofs;0/16 on each development view;train NLL.1193898.
All96 outputs and full dose were independently rechecked on server/locally
with byte-identical reports. All333 parseable generated step results were2;
the gold state inventory is varied. Preserve the failed gate and original
thresholds. No GPU retry,holdout access,recipe change or new scientific pair.
All12 checkpoint files are independently SHA256-backed up. Current ledger
5971/7200 used,1229 left,zero reservations. See the
[full analysis](../../reports/RELATION_E011_RESULTS.md) for post-hoc diagnostics,
CPU audit performance repair,resource costs and subsequent proposal.
