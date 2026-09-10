# E013 — full GSM8K trajectory completed; overfit gate failed

Run `gsm8k_overfit_e013_r1` completed on 2026-09-10 UTC from published commit
`4fa838a368f8197338d8a20513a21755830dfc7d`. The process exited normally, but
**the registered engineering gate failed**. Do not launch the four-condition
scientific study from this result.

| Evaluation | Correct numeric final | Parsed final | Ended with EOS | Truncated |
|---|---:|---:|---:|---:|
| Base development | 0/16 | 0/16 | 14/16 | 2/16 |
| Final training | 24/32 | 27/32 | 27/32 | 5/32 |
| Final development | 0/16 | 11/16 | 11/16 | 5/16 |

All 24 correct training answers also ended with EOS. Twenty completions exactly
match their training reference after the registered outer-whitespace handling.
Train reference NLL falls from **0.488519 to 0.014206**, but this teacher-forced,
token-averaged loss did not predict stable free generation. The gate required
at least 31/32 correct terminated train completions, no train truncations,
NLL < .1, the full dose and a complete profile. Only the last three requirements
pass. No intermediate checkpoint was selected, cap extended, scorer relaxed,
extra update added or model retried.

The base-development score is dominated by output format: 15 responses have
no explicit final marker and one has an unresolved marked suffix. It is **not
evidence of zero base mathematical ability**. For example, the first frozen
development problem has the correct unboxed answer 2 in the base output and
the incorrect boxed answer 48 after SFT. This is a descriptive example, not a
replacement aggregate metric. Final development includes 11 parsed wrong
numbers and five truncated outputs, so its failure is not merely formatting.
With n=16, neither row supports a scientific treatment/generalization claim.

## What was verified

The original Qwen2.5-1.5B base snapshot, all pinned file hashes and the recorded
Linux/Python3.12/PyTorch2.8.0+cu128 dependencies pass preflight. All 40 focused
Linux tests pass, including both GNU-timeout integrations. An audit-only
PyArrow installation is separate from the model environment. Direct Git fetch
timed out; the already published history was transferred as a checksum-verified
Git bundle and synchronized without changing source bytes.

The exact frozen 32 training responses and 16 original-train development
parents were used. All 256 updates completed with 32 exposures per response:
**167,232 supervised response tokens, 229,056 processed tokens, zero padding**.
FP32 full-parameter training, BF16 autocast, AdamW, learning rate 5e-5,
microbatch one, exact serialization, response masking and EOS are unchanged.
No official test, fresh reserve, teacher call or scientific arm comparison.

Independent CPU record verification reconciles all 64 saved token streams,
their decoded text/scores, every update's token dose, exposure totals, profile,
gate and resource receipt. This verifies record consistency; it does not
independently recompute model NLL or prove intermediate reasoning.

Evidence: [registered design](../docs/experiments/E013_gsm8k_engineering.md),
[metrics](../runs/gsm8k_overfit_e013_r1/metrics.json),
[raw training predictions](../runs/gsm8k_overfit_e013_r1/final_train.jsonl),
[base development](../runs/gsm8k_overfit_e013_r1/base_dev.jsonl),
[final development](../runs/gsm8k_overfit_e013_r1/final_dev.jsonl),
[record verification](../runs/gsm8k_overfit_e013_r1/record_verification.json),
[server preflight](real_math_e013_execution_r1/server_preflight.json), and
[Linux test log](real_math_e013_execution_r1/linux_tests.log).

## Failure inspection and limits

The eight train failures comprise five missing-final truncations and three
parsed wrong answers. Inspection of the frozen raw outputs finds repeated
equations/sentences in four truncations and a repeated decimal digit in the
fifth. Three completed answers are 28 instead of 12, 135 instead of 45, and
26 instead of 21. Some trajectories first compute a correct intermediate
value, then add incorrect reasoning. These are observable output failures;
their causal source is not established by an average NLL or this inspection.

The [reproducible post-hoc CPU analysis](real_math_e013_execution_r1/failure_analysis.json)
preserves all registered scores. Each failed training generation shares
46–355 initial tokens with its reference before diverging. The decimal-loop
case contains 639 consecutive copies of a digit; the other four truncations
repeat exact 16-token segments 8–13 times. These observations narrow the next
diagnostic without establishing a model/runtime/data cause. The
[analysis code](../analyses/real_math_e013_failures.py) was published before this
derived artifact was computed. No model was rerun for this analysis.

Preserve the failed checkpoint for diagnosis. Before another training run,
prepare a bounded inference diagnostic comparing the recorded batch-eight
decoding with individual decoding and inspect teacher-forced probabilities
at the first divergent tokens. This would distinguish reproducibility/batch
sensitivity from failures that persist in single-problem generation. Freeze
the diagnostic, its selected cases and its complete cap first. Do not select
easier training parents or treat post-hoc case selection as a new benchmark.

A [concrete E014 proposal](../configs/diagnostics/real_math_e014_proposal.json)
would replay all 32 train prompts at the original batch size of eight, decode the eight
failures plus the first two successful controls individually, and inspect
reference-conditioned logits at the first divergence/EOS. It proposes a
360-second process cap plus 15-second guard, within the remaining 903 seconds.
This is not implemented, queued or an extension of E013; it requires its own
source/input/weight checks and a request/review before execution. It performs
zero optimizer updates and accesses no development/test data or teacher.

## Measured runtime and scale decision

| Component | Seconds |
|---|---:|
| Original base load | 1.90 |
| Base development generation | 38.18 |
| All optimizer updates | 167.14 |
| Final training generation | 59.41 |
| Final development generation | 37.11 |
| Both reference-NLL passes | 1.26 |
| Checkpoint write and hashing | 15.51 |
| Guarded process elapsed / charged | 325.27 / 326 |

The 64-update profile after eight warmup updates measures **1,003.45 supervised
tokens/s** and **1,374.41 processed tokens/s**. Peak allocated memory is
27,180.86 MiB (**26.54 GiB**); peak reserved memory is 29,830 MiB (29.13 GiB).
These are observed for this exact engineering recipe, not a general A800
capacity estimate. Small startup/logging intervals explain the difference
between listed component times and whole guarded-process time.

The [four-arm training-only projections](../runs/gsm8k_overfit_e013_r1/training_scale_projection.json)
are 2,095.95–2,165.17 seconds (34.93–36.09 minutes) at the existing 524,288-token,
256-update budgets. They are linear supervised/processed-token scaling proxies,
not confidence bounds or complete-phase estimates. Model loads, scientific
development decoding, checkpointing, verification and guards must be added.

The [17-receipt ledger reconciliation](real_math_e013_ledger_verification.json)
is **6297 / 7200 seconds used, 903 remaining, zero reservations**. Thus the
proposed four-arm training-only estimate already exceeds the remaining
allowance, and the overfit gate independently blocks scaling. Keep C017's
audited pool and candidate schedules as proposals; do not set a launchable
scientific scale until the generation/scoring diagnostic and full-phase budget
are resolved. No additional allowance is inferred.

All compact outputs and the updated ledger are preserved. The
[independent checkpoint backup](real_math_e013_checkpoint_backup.json) verifies
all 12 files totaling 6,190,803,414 bytes against the saved SHA256 manifest.
The backup is weights/tokenizer only, not an optimizer/RNG resume. No checkpoint
weights enter Git. The [server closeout](real_math_e013_execution_r1/server_closeout.json)
confirms GPU execution is stopped and no next model job is queued.
The original model/data caches remain available on the server; the verified
backup permits recovery after shutdown or replacement.
