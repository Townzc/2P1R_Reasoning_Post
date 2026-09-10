# E014 — CPU checks complete; saved-model diagnosis needs the A800

Execution amendment: after owner startup, CPU-only inspections timed out in
repeated tokenizer length reads. D023/source d9c0bb4 caches size only inside the
unchanged auditor. Use `release_r2.json` and `real_math_e014_inputs_r2`; original
cases and CPU evidence are byte-identical, and the independent verifier passes.
All12 checkpoint files verify.53 local tests pass; amended55-test Linux suite
and published inspection must pass before the original authorized launch. All
historical r1 evidence below remains retained. No GPU reservation occurred.


The local investigation and executable diagnostic are ready. No pretrained
forward pass, server contact, GPU job, teacher call or reservation occurred.
The causal source of E013's generation failures remains unresolved; the next
measurements require the frozen checkpoint on the recorded A800 environment.

## What the CPU investigation established

- All 32 original training rows re-tokenize identically through the independent
  raw tokenizer API: 1,932 prompt tokens and 5,226 supervised targets including
  32 EOS. Prompt boundaries, masks, first-difference positions and EOS causal
  indices agree. EOS is 0.6123% of reference targets, so low average loss does
  not establish reliable termination or correctness at every position.
- Original batch widths are87/86/84/87, with maximum prompt-plus-generation
  lengths855/854/852/855, below 1024. The source uses left padding with explicit
  masks. Inspection and tiny CPU fixtures found no prompt-token mismatch,
  missing EOS supervision, causal shift or effective-cap override in these
  tested paths. This is not proof that the full CUDA runtime has no defects.
- The failed outputs initially match 123,96,46,72,145,92,65 and355 reference
  tokens. Five then repeat material until the cap; three finish with wrong
  numbers. Existing scores and all eight failures remain unchanged. The
  first-divergence distributions were not saved by E013 and cannot be inferred
  from its average NLL or the raw text alone.
- The checkpoint's saved 2048-token default resolves to the explicit 768 cap.
  Pinned Transformers default merging is checked; effective caching remains
  enabled. Tiny Qwen2 fixtures exercise both the unchanged E013 generator and
  padded/cached position handling. Random CPU fixtures do not establish BF16
  batch invariance for the pretrained checkpoint.
- All 12 checkpoint files, 6,190,803,414 bytes, were rehashed against the preserved
  manifest. The original tokenizer is verified separately. E013's complete
  runtime/data source freeze remains unchanged.

Evidence: [CPU measurements](real_math_e014_inputs_r1/cpu_evidence.json),
[independent token/ledger verification](real_math_e014_independent_verification.json),
[published-checkout inspection](real_math_e014_published_inspection.json),
[original failure analysis](real_math_e013_execution_r1/failure_analysis.json).

## The next experiment is fixed

| Measurement | Scope | Purpose |
|---|---|---|
| Original batch8 replay |32 original training prompts | Check exact raw-token reproducibility after checkpoint reload |
| Individual decoding |8 failed cases + first2 successful controls | Detect selected-case batch sensitivity while preserving settings |
| Full-reference token/EOS measurements |All 32 references,5,226 targets | Locate local fit/termination weaknesses hidden by the average loss |
| First-divergence queries |The fixed ten cases, for original/replayed/single streams | Compare target and chosen-token probabilities, rank and margins under a shared reference prefix |

Use the saved E013 weights, original tokenizer, FP32 parameters/BF16 autocast,
SDPA, seed17, greedy decoding and768-token cap. No training, model substitution,
new development/test scoring or repetition penalty. The two controls are
gsm8k/train/07460 and gsm8k/train/06803; case selection is explicitly post-hoc.

If batch8 does not reproduce, do not isolate a batch-size effect. If it does,
batch1 differences identify batch-sensitive output but not a software bug.
Reference-target or EOS top-one failures would indicate local reference-fit
weakness; a correct full-reference argmax alongside failed free generation
would motivate cached-prefix/numerical checks. Reference-conditioned EOS is
not the probability after a diverged generated prefix. None of these outcomes
automatically launches retraining or changes E013's failed gate.

The [registration and decision table](../docs/experiments/E014_generation_diagnostic.md)
specify each next branch. [Runtime](../analyses/e014.py),
[CPU output auditor](../analyses/e014_audit.py),
[configuration](../configs/real_math_e014/diagnostic.json),
[immutable input release](../configs/real_math_e014/release.json).

## Verification and budget

Implementation source `3dd0034ed33780a883eb7641d0ec8189f1bfad84` was published
before preparing inputs. Release `e79a0e10f77278692c44450fff606f336872fca5`
was then published before the independent verifier and default inspection ran.
Both passed from the synchronized checkout. The release SHA256 is
`c1eb877ad1cd062e96f08cf6617a3390dbb81c579bae445b79f4a18661d6af4d`.

[52 focused CPU tests pass](real_math_e014_cpu_tests.log); two GNU-timeout
integrations are mandatory on Linux before launch. Coverage includes reference
shift/EOS, exact generator behavior, effective settings, cached positions,
checkpoint integrity, raw-token/score/log-probability tampering, a complete
synthetic result audit and budget guards. A separate historical E011 release
check rejected the pre-existing C017 change to sft_data. That [failure](real_math_e014_legacy_check_failure.json)
and [log](real_math_e014_legacy_check_failure.log) are retained; the old freeze
was not weakened. Actual E013/E014 inputs pass their own source checks.

All 17 public receipts reconcile with the current private ledger: **6297 used,
903 remaining,zero reservations**. One360-second process plus15-second guard
reserves at most375 seconds and leaves528 unreserved. The recorded replay time
plus selected containing-batch proxy totals236.6 seconds before loading,
hashing, reference probes and writes. This is planning evidence, not a guaranteed
completion bound. Instance startup/idle billing is separate from process time.

The server is needed now for this one diagnostic. At startup, verify published
main, the current ledger, the original tokenizer, the E013 checkpoint, the
recorded environment and an idle A80080GB. At least2GiB free disk is sufficient
for compact records; no new checkpoint is written. No new server, allowance,
teacher or four-arm run is requested. The four-arm training-only proxy remains
2096–2165 seconds, above the existing balance even before other costs.

[Next-session commands and recovery](../docs/NEXT_SESSION.md).
