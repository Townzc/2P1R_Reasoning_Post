# E014 — frozen-checkpoint generation diagnosis

Registered 2026-09-10 UTC before E014 input materialization or pretrained model
execution. The owner requested local investigation, preparation of the next
experiment, and notification when the existing server is needed. This is one
inference diagnostic, with no training, new allowance, teacher or scientific grid.

## Motivation and observations

[E013](../../reports/REAL_MATH_E013_RESULTS.md) completed its prescribed dose but
failed its engineering gate: 24/32 training completions were correct and ended
with EOS, five reached 768 tokens, and three produced wrong final numbers.
Twenty exactly matched the reference. All eight failures first reproduce 46–355
reference tokens. Four truncations repeat derivations; one repeats the digit 6
639 times. These descriptions do not identify a causal model/runtime/data bug.

Mean teacher-forced NLL 0.014206 averages 5,226 reference targets, of which just
32 are EOS. It does not provide per-row, per-position or termination confidence.
Training and reference NLL use microbatch one; greedy decoding uses batches of
eight. Cached generation and full-reference forward passes can also differ.
Those distinctions motivate measurements rather than a new training sweep.

CPU code inspection checks exact prompt tokenization, shifted response labels,
supervised EOS, explicit attention masks, left padding, cache/position handling,
generation configuration and historical artifact identity. Tiny randomly
initialized Qwen2 fixtures exercise the original generation function on CPU;
they do not reproduce A800/BF16 numerical behavior or measure pretrained ability.
No concrete causal implementation error has been established by this review.

## Fixed inputs, weights and settings

- Weights: the final E013 checkpoint, independently backed up, not the original
  base and not an optimizer/RNG resume. Manifest SHA256
  `b0afd4cf81a8c41a2268d5d797a3f832c8b530206f1fa3a6539a43ddf91fab6a`.
- Original tokenizer revision `8faed761d45a263340a0528343f099c05c9a4323`, checked
  separately from the resaved checkpoint tokenizer. Full checkpoint file hashes
  are checked before use; no download is performed by the diagnostic.
- All original 32 training parents/references and their frozen order. The replay
  uses `src.real_math_experiment.generate` unchanged. No development or test
  prompt is decoded, scored anew or used to select cases. Existing split hashes
  may be read while verifying the original input release.
- Exactly the eight failed training cases and the first two successful cases
  in original order are selected for individual decoding. The control IDs are
  `gsm8k/train/07460` and `gsm8k/train/06803`. These ten are a post-hoc diagnostic
  set; never present their score as a representative new evaluation.
- FP32 parameters, BF16 autocast, SDPA, seed17, eight CPU threads, TF32 disabled,
  model eval mode, no active gradient checkpointing. Greedy, one beam, dynamic
  cache, EOS/pad151643, max_new_tokens768, prompt+generation cap1024. No length
  extension, force-stop, repetition penalty or sampling change.
- The pinned Transformers4.56.2 generation-default merging is checked explicitly.
  Its effective settings must agree with the CPU-inspected saved metadata. The
  checkpoint's saved max_new_tokens2048 is overridden by the explicit768. A
  nonstandard effective cache/stop configuration fails preflight; it is not
  silently corrected. Installed generation/Qwen2 Python source hashes are frozen.

See [configuration](../../configs/real_math_e014/diagnostic.json). The earlier
[review-only proposal](../../configs/diagnostics/real_math_e014_proposal.json)
remains unchanged as history. This registration adds all32 reference-token/EOS
measurements to make the aggregate NLL independently interpretable.

## One finite process

| Phase | Fixed work | Evidence |
|---|---|---|
| Preflight | Published source/input release, current ledger, 12 checkpoint files, original tokenizer, recorded environment, idle A80080GB, at least2GiB free | Hashes, versions, exact reservation arithmetic |
| Batch8 replay | All32 original training prompts in the original four batches | Complete raw IDs, text, scores, EOS, lengths, batch durations |
| Batch1 contrast | Ten fixed cases, in original training order | Complete raw IDs and the same score/termination records |
| Reference logits | All32 references, one at a time, including EOS | Every target NLL and argmax ID; per-row/aggregate NLL and target/EOS top-one counts |
| Focused queries | EOS for all32; first reference difference for each original/replay/single stream on the ten selected cases | Target/alternative log probabilities, strict-greater rank, argmax, margins, top five, exact prefix hash and causal index |
| CPU output audit | All42 free generations and all32 reference records | Token/text/score, prefix/index, arithmetic, manifest and resource consistency |

For response target j, the predictive logit index is `n_prompt+j-1`. The query
context is exactly prompt plus reference targets before j. A first-difference
query therefore uses a shared reference prefix, but its full-forward kernel is
not an exact reproduction of cached generation. Reference-conditioned EOS after
a diverged output is counterfactual; never label it the generated path's EOS
probability. Strict-greater rank1 can include ties; argmax identity is recorded
separately. The CPU auditor checks record consistency, not independently rerun
logits or intermediate mathematical proofs.

A replay mismatch does not trigger an automatic retry. The remaining fixed
phases are still collected within the same process/cap, but the batch contrast
is marked uninterpretable as an isolated batch-size effect. Partial outputs and
timeouts are preserved. Completed diagnostic execution is not a passed overfit
gate and cannot revise E013's registered outcome.

## Budget and preservation

Current accounting:17 receipts,6297/7200 seconds charged,903 remaining,zero
reservations. Expected ledger SHA256:
`a332e3ff326f768c6d985786c41fd6352df1c52fc73f34bae9f47d7d264ba614`.

Reserve at most360 process seconds plus15 guard seconds:375 total, leaving528
unreserved. E013's original32-train decoding took59.4 seconds. Summing each
selected case's original containing-batch duration is an additional conservative
planning proxy, not an upper bound on batch1 runtime. Reloading/hashing the saved
weights, all decoding, reference probes and writes must fit the new guarded
process; no promise of completion follows from this proxy. CPU preflight,
local verification and instance idle billing are separate from GPU-process time.

The existing budget wrapper checks the exact ledger under its lock, requires
the full cap, refuses an old run ID and reserves before launching the child.
Two GNU-timeout integrations must pass on Linux before launch. No new checkpoint
is written, so2GiB of free disk is required for compact outputs rather than
E013's original12GiB checkpoint-writing allowance. Do not expand storage or
delete existing unique state automatically.

After any outcome, preserve raw records, audit completed outputs where possible,
reconcile the new receipt with the cumulative ledger, update the private backup
and public handoff, and publish the result. The E013 weights remain immutable.

## Decisions after the measurements

| Observation | Supported next step | What it does not establish |
|---|---|---|
| Original batch8 IDs do not reproduce | Check numerical/runtime reproducibility and selected prefix/cache logits before any training | A batch-size effect or a bad checkpoint merely from changed IDs |
| Batch8 reproduces, batch1 changes failures | Localize batch sensitivity, including full versus cached and precision comparisons; freeze any future evaluation change across conditions | A software bug, success on all32, or permission to replace E013's score |
| Failure persists and the reference target/EOS loses top-one | Identify local reference-fit/termination weaknesses; prepare one justified repair/calibration rather than a seed/LR sweep | That low average NLL implies full memorization, or that more training will fix it |
| Full-reference targets win but free generation still fails | Probe cached prefix logits/position/numerical differences before retraining | Equal full-forward and incremental computation, or a proved exposure-bias mechanism |

Any next repair gets a new registration and a complete cost cap, preserving the
same original engineering denominator and failed result. No particular repair
or extra process is queued here. Passing a later engineering check must precede
a priced, reviewed scientific phase. C017's four-arm training-only projection
is2096–2165 seconds before evaluation/overhead, so it cannot fit even the current
903-second balance. E012 remains paused.

## Commands and launch boundary

Publish implementation first, then prepare and publish immutable inputs:

```sh
python -m analyses.e014 prepare --tokenizer-dir "$E014_TOKENIZER" --checkpoint-dir "$E014_CHECKPOINT"
python -m analyses.e014 inspect --tokenizer-dir "$E014_TOKENIZER" --checkpoint-dir "$E014_CHECKPOINT" --ledger "$E014_LEDGER"
```

After the owner starts/provides the existing A800 for this specific diagnostic,
verify its current source, ledger, weights and environment, then run the focused
tests below. The historical E011 release regression is not an E014 dependency:
its source guard correctly rejects the pre-existing C017 change to
`src/sft_data.py`. That failed scope check is retained in
[the failure record](../../reports/real_math_e014_legacy_check_failure.json).
Reuse its component tests while independently verifying the actual E013/E014
input releases. Do not weaken or update the old E011 source freeze.

```sh
python -m unittest tests.test_e014 tests.test_real_math_engineering tests.test_sft_data \
  tests.test_relation_engineering.ScoringTests tests.test_relation_engineering.DoseTests \
  tests.test_relation_engineering.LedgerTests tests.test_relation_engineering.OutputAuditTests \
  tests.test_budget_guard -v
python -m analyses.e014 launch --execute --tokenizer-dir "$E014_TOKENIZER" --checkpoint-dir "$E014_CHECKPOINT" --ledger "$E014_LEDGER"
python -m analyses.e014_audit --tokenizer-dir "$E014_TOKENIZER" --out runs/gsm8k_generation_e014_r1/record_verification.json
```

Inspection is CPU-only and does not reserve budget or contact the server.
Supplying a running instance for this prepared phase permits its single bounded
diagnostic; startup must never auto-launch an old queue or a scientific grid.
