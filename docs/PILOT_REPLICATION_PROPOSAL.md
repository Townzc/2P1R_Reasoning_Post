# Proposed next step — Paths/GCM paired replication (not authorized to run)

The first paired pilot scored Paths 23/64 and GCM 18/64 on matched dev, with
12 Paths-only and 7 GCM-only successes. Broader dev remains weak (4/64 vs 1/64).
This supports checking reproducibility before expanding model size or tasks.
The proposal below needs owner review; no queue/config or GPU job is launched.

## Concrete scope

Run only Paths and GCM, with a second prespecified pairing seed, proposed as 23.
Keep the current 256 training problems, shared four-structure blocks, both fixed
64-problem development sets, original tokenizer/model revision, full-parameter
AdamW recipe, 1024 updates, supervision totals and decoding configuration.
Initialize both jobs independently from the pinned base. Do not resume pilot
weights, select a best checkpoint, retune dose/LR, or inspect the reserved holdout.

A different `torch.manual_seed` alone is not a sufficient replication design:
the current training schedule and GCM assignment were frozen with seed 17.
Before running either arm, create a separate immutable seed-23 preparation using
the same selected blocks, regenerate the paired presentation order and GCM path
assignment together, and audit exact per-update Paths/GCM structure and token
matching. Freeze/publish its hashes and both configs before model inference.
Keep the seed-17 artifacts intact. If these controls cannot be reproduced exactly,
stop at CPU preparation and report the mismatch rather than relaxing the match.

This checks the joint sensitivity to the paired order/assignment seed. It does
not isolate order effects from assignment effects and does not test variation
across newly sampled training datasets. Publish both seeds separately, including
an unfavorable replication. Two seeds still provide little seed-level uncertainty.

## Fixed evaluation and acceptance

Primary contrast: Paths minus GCM on the unchanged matched-dev greedy correctness.
Report problem-paired counts, the corresponding broader-dev contrast, sampled
pass@1/2/4, parse and truncation rates, and exact exposure/runtime reconciliation.
Treat a reversal or disappearance of the first contrast as an informative outcome;
do not search further seeds until a positive difference appears. Keep full final
weights and raw predictions, with independent backups before shutdown.

Before additional claims about reasoning traces, separately design and validate
an intermediate-equation audit; the current metric checks only final expressions.
Broader-domain validation and another model family remain later decisions.

## Cost and server plan

Current balance: 3712/7200 process-seconds used, 3488 remaining. Retaining the
existing conservative 1050-second cap per job plus 15-second guard reserves
2130 seconds for the whole two-arm phase and leaves 1358 seconds headroom.
Observed two-arm process time is roughly 1000 seconds, but is not guaranteed.
Another four-arm phase at the existing caps would reserve 4260 seconds and does
not fit this balance. No budget extension or lower per-arm cap is implied.

The current A800 has sufficient memory; measured peak allocated memory was
26.21 GiB under this exact recipe. No larger machine is required for this proposed
replication. Prepare and publish CPU artifacts first; only then request an A800
start/connection if the owner approves the phase. A matching clone may reuse
the verified base cache and environment. Restore the latest ledger, not the older
1173- or 1719-second copies. Two new FP32 weights require about 12.4 GB plus
headroom; check free disk before launching and retain prior verified local backups.
