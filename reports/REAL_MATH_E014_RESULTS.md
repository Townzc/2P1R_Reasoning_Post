# E014 results — reproducible failures and local reference-fit gaps

The single authorized saved-checkpoint diagnostic completed on 2026-09-10 UTC.
All32 batch8 outputs reproduce E013 token-for-token. Changing the ten selected
cases to batch1 changes three streams but fixes none of the eight failures.
The reference forward pass exposes17 non-top-one targets across12 rows despite
mean NLL0.014206. All32 reference-conditioned EOS targets are top-one.
E013's failed engineering gate remains unchanged; scientific scaling is deferred.

## Execution and preflight correction

Run `gsm8k_generation_e014_r1` used published source
`d78aa7731af7e42d73e532348a123c4f1d4ce868`, active
[r2 release](../configs/real_math_e014/release_r2.json) SHA256
`597ff235abe5364db173c19307823ea84ad594b1b1469f650f193e89db84633a`
and input manifest SHA256
`281170f0553d43d79e6da26d23598030f1e9dec94ce838b0d41fecde495d5b48`.
The original E013 checkpoint and tokenizer, decoder, seed17, FP32/BF16/SDPA,
TF32-off setting,768-token cap and1024 context were preserved. No optimizer,
training, teacher, development/test generation or new checkpoint was involved.

Before launch, the original source passed54 Linux tests, but CPU-only inspection
exceeded45 seconds and a profiled180-second check also timed out. Stack samples
located repeated `len(tokenizer)` calls inside the historical raw-output audit;
16 calls took0.364809 seconds. D023/source d9c0bb4 adds an audit-only view that
snapshots vocabulary size once and delegates decoding/EOS to the original
tokenizer. Model-facing tokenization and every historical src/scripts file stay
unchanged. Accepted and invalid token/type/EOS/text/score fixtures agree with the
original auditor. Both timeouts and r1 inputs remain immutable.

The r2 cases and CPU evidence are byte-identical to r1. All55 amended Linux
tests pass, and full CPU inspection including all12 checkpoint hashes completes
in10.3797 seconds. This correction preceded the sole GPU reservation and did
not increase its registered360-second process cap or15-second guard.
[Preflight and equivalence evidence](real_math_e014_execution_r1/).

## Raw generation results

| Population and decode | Correct and terminated | Truncated | Exact reference | Generated tokens |
|---|---:|---:|---:|---:|
| Original E013, all32, batch8 |24/32|5/32|20/32|8652|
| E014 replay, all32, batch8 |24/32|5/32|20/32|8652|
| Same selected ten, batch8 |2/10|5/10|1/10|5152|
| Same selected ten, batch1 |2/10|5/10|1/10|4905|

All32 original/replay token streams match, permitting a descriptive batch
contrast. Batch1 changes `gsm8k/train/02301`, `04719` and `03893`. The first
still truncates; the latter two still terminate with wrong numbers. All five
original truncations remain truncations, all three wrong-answer failures remain
wrong, and both fixed successful controls stay correct. This selected set is
post-hoc; its2/10 is not an all32 batch1 score or a new evaluation estimate.

## Reference-token measurements

The5226 targets contain5209 top-one matches and17 mismatches across12 rows.
Those12 are exactly the non-reference-exact replay rows: eight failures and
four correct alternative completions. A reference mismatch therefore does not
by itself mean that the generated answer is wrong. The aggregate NLL is
0.014205516349502212, only1.25e-10 above E013's recorded value.

All27 selected first-difference query records favor the actually generated
alternative over the reference target, with the generated alternative also
the full-reference argmax. These are repeated records at10 distinct
problem/position/alternative combinations, not27 independent observations.
They show local fit gaps at every measured first divergence. For example,
03552 assigns probability0.000276 to reference token `4` while preferring `1`;
the reference-minus-alternative logit margin is−8.1875.

| Failed parent suffix | Batch1 first difference, zero-based | Reference token | Generated token | Reference minus alternative logit |
|---|---:|---|---|---:|
|03552|123|`4`|`1`|−8.1875|
|02301|96|` five`|` *`|−1.125|
|06477|46|`So`|`$`|−7.75|
|04768|72|`So`|`The`|−2.5|
|02775|145|` *`|`6`|−1.75|
|04719|61|`,`|`.\n`|−0.125|
|02262|65|`Thus`|`Since`|−3.375|
|03893|355|`Thus`|`However`|−4.4375|

For04719, batch8 follows the reference through position91, while batch1 first
differs at61. The full-reference pass also prefers the alternative at61 by
0.125, so full-forward and cached/batched numerical behavior are not identical
at every position. Nevertheless both streams later fail, and the measured first
divergences do not require a cached-only error to explain their token choice.

All32 reference EOS targets are top-one; their target probabilities range from
0.591215 to0.999995. This is evidence about termination **after the correct
reference prefix**. It does not measure EOS after a generated loop or prove
termination behavior is healthy there. Full-reference logits are not a rerun of
the exact incremental kernel, and the result does not establish a software bug
or a complete causal explanation for looping. The supported interpretation is
that low average NLL hides local reference-fit gaps; changing batch size alone
does not repair the observed failures.

## Cost, verification and preservation

The guarded process takes169.8054 seconds and charges170. Internal wall time is
164.9683 seconds: checkpoint load1.1890, batch8 replay61.5887, selected batch1
95.4544 and all-reference measurement0.8156 seconds. Internal wall also includes
weight verification and setup. Peak allocated/reserved memory is
9343.81/10696.00MiB. CPU preflight and instance idle billing are separate.

Server and local CPU auditors both pass all42 generation streams,32 reference
records and5226 targets, including token/text/score, causal-index/probability,
manifest and receipt consistency. This is record verification, not an
independent pretrained-logit rerun or mathematical proof audit. Separate raw
calculations verify the17 mismatches,27 query records/10 distinct positions and
the proposed next-dose counts.

All18 receipts reconcile: **6467/7200 used,733 remaining,zero reservations**.
The latest ledger SHA256 is
`8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9`.
The private recovery ledger is updated; its pre-E01417-receipt snapshot remains
retained. Compact run artifacts are independently downloaded. The12 unchanged
E013 checkpoint files,6,190,803,414 bytes, are independently backed up and pass
post-run server hashes. GPU execution is stopped; no next job is queued.

## Next experiment proposed for review

[E015 proposal](../configs/diagnostics/real_math_e015_proposal.json) specifies
one512-update calibration from the original pinned base, retaining the32
parents, seed17, LR5e-5, batch4/microbatch1 and existing decoder/scorer. A fresh
base trajectory makes the longer dose explicit; the weights-only E013 backup
cannot restore its optimizer state. CPU schedules give64 exposures per row,
334464 supervised and458112 processed tokens. Score only the final32 training
prompts, with all-token/EOS diagnostics; no new dev/test decode, early stopping,
intermediate checkpoint selection or automatic retry.

Proposed cap600+15 seconds would leave118 of the733 balance unreserved.
Training-only extrapolation is334.3 seconds; a sum of comparable E013 phases is
412.3 seconds. These are planning proxies, not runtime upper bounds or a promise
that longer training will pass. The proposed checkpoint-writing run retains
the12GiB free-space check; E014 preflight had6.29GiB, so preservation capacity
must be resolved before any launch without losing unique state. This is a
review-only proposal, not a registered implementation or server-start request.

The original requirement of at least31/32 correct terminated outputs, zero
truncation, NLL below0.1 and complete dose/profile remains the engineering gate.
C017's four-arm training-only proxy is2096–2165 seconds before other costs,
well beyond733 seconds; E012 remains paused and scientific scale stays unset.

Raw records: [diagnosis](../runs/gsm8k_generation_e014_r1/diagnosis.json),
[reference records](../runs/gsm8k_generation_e014_r1/reference_tokens.jsonl),
[descriptive findings](real_math_e014_execution_r1/findings.json),
[local audit](real_math_e014_execution_r1/local_record_verification.json),
[ledger reconciliation](real_math_e014_execution_r1/ledger_verification.json).
