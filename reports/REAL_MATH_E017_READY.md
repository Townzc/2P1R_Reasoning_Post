# E017 ready for one owner-started calibration

2026-09-10 UTC. Offline preparation is complete. The existing A800 is now
needed for one finite base-only stop-contract measurement. No GPU/model/server
call or new reservation occurred during preparation; this is readiness, not a
new accuracy or speed result. E018 training and the scientific grid remain paused.

## Verified execution release

- Implementation commit `b365bd8bc9fca6521946a83c5ed6565fce6a4e45` preceded inputs.
- Input release commit `410ee3e99979402803286901aa9bab6bf00b2247` is published.
- Release SHA256: `daeb946c7e3d01afe54552224770f3429129ab05022adeb76138222b87ce56af`.
- All 64 input rows are byte-identical to observed E016 parents, ranks 17–80.
  Independent reconstruction verifies 4,058 prompt tokens, 6,472 padded prompt
  tokens and a maximum width of 146. The 432 reserved dev parents remain unused.
- A new 104-file runtime freeze includes all 96 unchanged historical dependencies
  and four installed Transformers module hashes. No `src/` or `scripts/` file
  was added or changed. Historic predictions, scores and gates remain untouched.

[Registered run](../docs/experiments/E017_task_completion_calibration.md),
[CPU inputs](real_math_e017_inputs_r1/cpu_evidence.json),
[independent verification](real_math_e017_verification_r1/independent_cpu.json).

## What the checks establish

The 64-test focused suite has **62 passes and 2 Linux-only watchdog tests pending**.
New tests exercise the actual Transformers generation loop using scripted logits,
including mixed row stopping, left padding, prompt exclusion, retained trigger
tokens and post-stop padding. The production output writer feeds the independent
raw-prefix auditor. Tampered tokens, gold, stop records, scores, padding, missing
rows and sidecars are rejected. An unarmed command cannot contact the server.
Inherited tests additionally use tiny random CPU fixtures; no pretrained weights
or GPU measurements are involved. [Test log](real_math_e017_verification_r1/focused_tests.log).

An independent recorded-token replay exercises 8,064 incremental stopping steps
across 160 saved E013/E016 streams: 133 native EOS, 18 question boundaries and
9 length caps. Every event agrees with the separately published C020 oracle.
This is token replay, not 160 new model outputs or a GPU prefix-replay guarantee.

A clean repository was initialized with only the prior server history through
`84e9ea35fc54a0d94e70d4efca74b5f15783091b`, then imported the 232,536-byte release
bundle. Release/token/20-receipt checks pass again; reports agree except measured
CPU replay time. Default inspection agrees exactly and takes about 5.02 seconds.
This release bundle ends at `410ee3e`; the final documentation commit is included
in the separately verified final staging bundle. Read
[clean-checkout evidence](real_math_e017_verification_r1/clean_checkout_evidence.json).

## The single GPU measurement and cost

Run `gsm8k_stop_e017_r1`: original pinned Qwen2.5-1.5B base, 64 observed dev
questions, greedy batch 8, output cap 768/context 1024, FP32/BF16-autocast/SDPA,
seed 17 and TF32 off. Stop each row at actual native EOS or a complete recognized
new-question header. Store raw prefix, trigger and full batch padding separately.
There is no training, E015 checkpoint load, new checkpoint, teacher or test use.

Usability requires all 64 valid records, at least 48 parsed and 8 correct
completed answers, at most 8 actual length-cap stops, and zero invalid/false-EOS
receipts. Report native EOS and task completion separately. Old E016 gates stay
failed. A passing E017 result licenses review of the separate training release,
not automatic LoRA execution or a scientific result.

Maximum process reservation is **240 + 15 = 255 seconds**, fitting the current
279 and leaving at least 24. All 20 complete receipts reconcile; ledger remains
6,921/7,200 used, no reservations, SHA256
`c33623087b752f0bbc82a32bb90ac8f11a489fc910b2ebdaacb57000c0893106`.
Historical accounting and run registry are unchanged because no new run occurred.

Whole-rental target **12 minutes / CNY1.60**, cap **15 minutes / CNY2** at
CNY8 per powered-on hour. Require 555 seconds left at admission, including compact
export and shutdown. Set the provider backstop before generation; stop on failed
preflight; export/hash compact records and the updated ledger, confirm provider
shutdown, then analyze locally. These are planning bounds, not measured new
throughput or an invoice. Linux/software/base hashes and both watchdog tests
remain mandatory at startup. No full-weight transfer or cleanup is planned.

E015 independent full weights recovery remains open; retain its stopped volume
and use the separate no-card recovery plan. No instance disposal is permitted.
[Current startup handoff](../docs/NEXT_SESSION.md).
