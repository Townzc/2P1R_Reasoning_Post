# Activated after owner hardware upgrade

On2026-09-18 00:39UTC, after the owner reopened the same instance with two A800s,
the previously published abfff696 scheduler was deployed and launched in tmux.
Ten Linux checks passed, and both workers resumed the frozen remaining evaluation.
Read [the activation receipt](../../reports/public_math_pilot_v1/DUAL_GPU_RESUME.json).
The preparation text below records the earlier proposal and its preserved design.

# Optional temporary upgrade to two A800 GPUs in the same instance

The owner asked whether an additional A800 would help and clarified that it
would be an in-place change to two GPUs, requiring shutdown. This document and
the new scheduler are preparation for that possible change. The current single
GPU evaluator continues; no upgrade, maintenance pause or new GPU job is implied
by publishing this preparation. Recommend temporary capacity for this evaluation,
then reassess longer-term needs after the owner reviews the complete results.

All four128-update training endpoints are now committed and the original trainer
has verified their complete recoveries. Its recovery process exited0 after1534
seconds. The first saved formal GSM batch contains64 outputs and71587 output
tokens, taking155.304 seconds with20029231104 bytes peak active GPU allocation.
At that one-batch rate, all6595 GSM outputs would take about4.45 hours, excluding
loading and other datasets. This extrapolation is provisional; it is not a
measured total evaluation duration or a measured two-GPU speedup.

## Scheduling

The new `parallel_evaluate.py` assigns whole jobs from the original53-job roster
by alternating index. It does not split a sampled draw or alter its batching,
seed, decoding, rows, endpoint or original generation code. The512 completed
Base-dev outputs remain reused.

| Worker | GSM runs | MATH draws | Dev runs | Assigned outputs |
|---|---:|---:|---:|---:|
| 0 | 3 | 20 | 4 | 16005 |
| 1 | 2 | 20 | 4 | 14686 |

Both GPUs use the existing data volume. No model/recovery transfer through the
Mac is required. Each fresh child process sees exactly one physical GPU through
CUDA_VISIBLE_DEVICES, preserving the one-device RNG topology of saved batches.
Every run uses the original immutable generation implementation and original
scientific identity. New execution provenance and the two-worker scheduling
amendment are bound separately in DUAL_GPU_CONTRACT.json. The old contract's
single-generator concurrency description remains historical, explicitly
superseded only when this optional scheduling amendment is actually activated.

The coordinator and both children retain the original phase GPU lock, excluding
the old evaluator and another coordinator even if the coordinator exits first.
Per-worker locks prevent duplicate rank execution, and the original physical
ledger serializes reservations under a file lock. Completed outputs are checked
and reused. Ambiguous reserved calls remain errors; only the previously recorded
128 failed GSM reservations have their existing one-time retry allowance.

Each child has its own hard timeout and durable log/receipt. A sibling failure
does not kill healthy in-flight generation. Final closeout requires both exact
partitions, unchanged completion hashes and all original53 jobs in the original
ordering. The CPU scorer and scientific denominators remain unchanged. Final
scientific dose512, physical completed training records544, logical outputs31203,
and generation cap31331 remain the registered totals.

## Transition and retention

Changing GPU configuration requires an explicit owner decision about timing.
Do not shut down during an unfinished generation. Pause the old evaluator only
at a verified durable boundary with every active reservation accounted for;
record the intentional pause and preserve its source, outputs, RNG and receipt.
Verify retained final model/optimizer/RNG files and sync the data volume before
reporting that the owner can shut down and change configuration. Never delete
or release the instance or its volume. The existing nightly cutoff remains in
force unless the owner explicitly changes it.

After the owner reopens the instance, verify its persistent volume and exact
assets, two distinct A80080GB UUIDs, CUDA/software identities, checkpoints and
the old phase lock. Deploy only an independently inventoried, published source
archive. Start the coordinator in a detached tmux session; both subprocesses
write logs and have independent hard deadlines. The current model deadline is
2026-09-18 06:35UTC, hard GPU deadline06:45UTC and provider timer06:58UTC.
Recheck the provider timer after hardware changes; no automatic overnight restart.

The new scheduler also accepts EVALUATION_PAUSE_AFTER_RUN.json, checked before
each whole run. This feature does not retrofit pause support into the already
running original evaluator. A maintenance pause must preserve unfinished work
explicitly; never count missing answers as wrong or repeat completed generations.

## Validation and limits

All98 public-math CPU checks pass, including10 new checks for complete/disjoint
coverage, original-contract parity, independent device isolation, physical-ledger
concurrency, inherited exclusion locks, completion integrity and pause admission.
No two-GPU model execution or throughput measurement has occurred. Actual speedup
will depend on generation lengths, per-GPU utilization and shared host I/O.
The original TrimSFT GPU replay numerical limitation remains part of the final
result; this scheduling preparation does not establish bitwise CUDA equivalence.
