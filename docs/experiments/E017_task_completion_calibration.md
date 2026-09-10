# E017: one stop-only implementation calibration

2026-09-10 UTC. The owner accepted the next step after the concrete P006 plan
and requested notification when startup is needed. This authorizes E017
preparation and one finite calibration on owner startup; no training or grid.

## Fixed question and change

Does a gold-blind, per-row task-boundary stop work in the actual GPU generation
loop while preserving auditable first-task answers? Original Qwen2.5-1.5B base,
revision `8faed761d45a263340a0528343f099c05c9a4323`; no E015 checkpoint load.
Use exactly the E016 observed 64 development parents, ranks 17–80, same order,
Problem/Solution serialization, zero-shot prompt, greedy generation, batch 8,
context 1024, cap 768, seed 17, FP32 weights/BF16 autocast, SDPA and TF32 off.
Zero optimizer steps, teacher calls, checkpoint writes or final-test evaluation.

Only task termination changes: stop at actual native EOS or the earliest complete
line-anchored header in the frozen marked extractor. Detect invalid special or
out-of-vocabulary generated IDs as explicit failed stops. Never use gold or an
answer marker to decide stopping. Keep the triggering token, pre-boundary answer
segment and separate native-EOS flag. All old scores and both failed E016 gates
remain unchanged; the C020 39/64 saved-prefix count is post-hoc evidence only.

The implementation uses a per-row `StoppingCriteria`, with fixed batch membership.
Hugging Face's default EOS/pad handling fills finished rows; record full batch
output IDs and the exact retained prefix separately. The C020 CPU oracle checks
all stops independently from actual output tokens. Do not trim at padding before
checking the recorded event, claim boundary padding is actual EOS, or assert
that GPU prefixes must reproduce the old saved streams exactly.

Implementation references: [official generation utilities](https://huggingface.co/docs/transformers/v4.56.2/en/internal/generation_utils)
and the pinned local Transformers 4.56.2 `_sample`/`StoppingCriteriaList` source.
The implementation returns a Boolean vector of shape `(batch_size,)`, matching
the installed list combiner, despite the documentation's `(batch_size, 1)`
annotation. A parameter-free scripted-logit fixture exercises the actual
library generation loop, including mixed stops and left padding. Installed
Qwen/generation/stopping/configuration source hashes are part of the release.

## Immutable inputs and evidence

Publish all implementation/configuration/test source before `prepare`. Copy the
E016 input bytes into a new release; reconstruct all prompt token streams and
retain the parent release hash. The runtime checks both releases, all frozen
source bytes, installed library sources and tracked input files. A separate CPU
verifier reconciles all 20 complete resource receipts and replays 160 saved
streams through incremental stopping, checking against the C020 oracle. Replay
uses recorded tokens, not new model inference. Keep all 432 unused dev parents
reserved. Default `inspect` and unarmed `launch` perform no server/model action.

Before startup, pass the new stop/writer/auditor/admission tests and inherited
parser/generation/budget tests. The two GNU-timeout integrations are mandatory
on Linux before the model job. Test fixtures load no pretrained weights; no
local fixture result is a task accuracy or a GPU measurement.

## Single operational usability screen

Require all 64 valid raw records, at least 48 parsed answers, at least 8 correct
completed task answers, and at most 8 actual length-cap stops. Invalid stops and
false native-EOS records must be zero. Report native EOS, boundary, cap, parse
failures, retained token counts, batch-padding counts and measured throughput
separately. Never count reference-conditioned NLL as free generation.

The integer thresholds are operational tolerances, not powered statistical
claims or an allocation result. This is observed development used to validate a
changed completion contract. On failure, preserve records and stop. On success,
publish/review the result before any separate E018 training release. No automatic
retry, second prompt, model substitution, LoRA run or scientific comparison.

## Process and whole-rental limits

Run ID `gsm8k_stop_e017_r1`; 240 process seconds plus the inherited 15-second
termination guard, maximum reservation 255. Current 20-receipt ledger is
6,921 used / 279 remaining; worst-case remainder 24. Restore the current ledger
by hash and never initialize/reset it. Expected SHA256:
`c33623087b752f0bbc82a32bb90ac8f11a489fc910b2ebdaacb57000c0893106`.

Rental billing includes startup, idle, CPU checks, transfers and shutdown.
Target 12 minutes/CNY1.60; cap 15 minutes/CNY2 at CNY8/hour. Require at least
555 seconds left at admission: 255 guarded process + 120 compact export +
180 shutdown/slack. No model launch more than 345 seconds after recorded power-on;
recheck after preflight. Record actual provider power-on time if available,
otherwise the owner notification as an explicitly labelled proxy. Set a
provider stop backstop before launching; stop promptly on blocked preflight.

Only the original base is needed. Verify the pinned idle A800/driver/software,
base snapshot and 256MiB scratch space. No cleanup, checkpoint load or full-weight
transfer. After the bounded job, independently export compact outputs and updated
ledger, verify hashes and provider-confirmed shutdown, then analyze/publish
locally. Stopping Python/SSH does not establish stopped billing. Retain failed
or incomplete output; every attempt consumes a unique receipt.

E015 full independent backup is still incomplete. Preserve that stopped volume
and the separate no-card recovery obligation; do not dispose of unique weights.
This inference-only window neither completes nor resets that recovery task.
