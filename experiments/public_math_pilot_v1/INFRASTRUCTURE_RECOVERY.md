# First public batch: recorded infrastructure failure and bounded recovery

The first128-way Base GSM8K batch in source
c9239c86bc929eea8dc40d33a3666f2d387704b9 failed with CUDA OOM before saving any
public output. The process ran257seconds and exited1. Its last allocation asked
for546MiB with545.38MiB free. Training held51.15GiB; inference held27.55GiB,
including21.30GiB allocated and5.76GiB cached but unused. This shows why the
earlier standalone memory profile was insufficient to admit this overlap.
Training continued without interruption or replay.

Preserve the complete failed directory, log, process receipt, evaluation contract
and original physical ledger in a separate immutable incident directory. No
public result was inspected or selected. The owner's original plan explicitly
allows logged infrastructure retries; this recovery creates no new scientific
arm, update, test example or sampled draw.

All five GSM states now use64-way batches, with26GiB admission. The new inference
process uses expandable CUDA allocator segments to reduce fragmentation; this
setting is recorded in every generation identity. The running trainer is unchanged.
If its existing cache leaves insufficient free memory, inference waits at its
admission gate while training continues. Dev remains16,
and MATH remains256 with64GiB admission after training. The replacement generation
source and batch identity are frozen before its first output. The failed128
reservations remain in the original physical ledger. A narrow evidence-checked
ledger permits exactly one additional physical attempt for each of these128
IDs, records a distinct retry namespace, and rejects completed-output retries,
changed evidence, changed prompt/row identities and duplicate retry attempts.
The maximum physical generation attempts become31,331:31,203 required logical
outputs plus128 failed attempts. No generic automatic retry is introduced.

The on-server GSM128_OOM_RETRY.json binds every failure artifact SHA and the128
eligible IDs; its SHA is frozen in the replacement evaluation contract. A network
interruption alone does not authorize another retry. Any further failure must
be diagnosed and recorded separately before a new recovery decision.
