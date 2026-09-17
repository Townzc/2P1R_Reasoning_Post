# Owner-requested overlapping execution

The owner explicitly requested maximizing server utilization by evaluating while
performing the next step. Replace the previous strictly serial execution order
with one training process and one generation process on the same A800, plus
CPU-only scoring. Do not add scientific arms, updates, data or generations.

All4096 masks and the fixed64 audit have completed before formal training.
Base-dev completion is no longer a prerequisite for training; its remaining
frozen16-way batches finish concurrently. The trainer never generates or consumes
dev/test outcomes. Its process-local seed/optimizer/dose remain fixed and each
arm still starts from the public base. Separate GPU locks permit at most one
trainer and one generator. Generation consumes only immutable committed64/128
weights, never live tensors from a running optimizer.

Training admission requires50GiB currently free (measured longest engineering
reservation48.30GiB); generation admission requires32GiB for64-way GSM,40GiB for
64-way MATH,22GiB for16-way dev. The already-running Base-dev peak was about17GiB.
Record actual device memory and throughput under overlap. Spare memory alone
does not establish a speedup. If contention defeats progress, restore serial
scheduling at committed boundaries without changing scientific parameters.

The evaluation queue may start Base GSM after Base-dev, then consume each final
trained arm when its128 checkpoint is committed. CPU scoring continues alongside
GPU work. Training and inference process wall times overlap and must not be
summed as billed GPU hours. Preserve the complete powered-window accounting.
The midnight stop, finite requests, all official denominators and artifact
retention rules remain in force.
