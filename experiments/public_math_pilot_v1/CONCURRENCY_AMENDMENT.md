# Owner-requested overlapping execution

Current batch policy after the first128-way GSM batch failed with concurrent
CUDA OOM:64-way GSM with26GiB admission;256-way MATH with64GiB admission;
16-way dev with22GiB admission. Read INFRASTRUCTURE_RECOVERY.md. The original
failed128 attempts remain charged and the one bounded retry is evidence-bound.
The128-way proposal below records the initial choice and is superseded.

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
reservation48.30GiB); generation admission requires32GiB for128-way GSM,64GiB for
256-way MATH,22GiB for16-way dev. The initial Base-dev reservation was about17GiB;
the long-running preparation process later reserved about29GiB. During observed
overlap the two processes used about71GiB combined and GPU utilization reached100%.
Record actual device memory and throughput under overlap. Spare memory alone
does not establish a speedup. If contention defeats progress, restore serial
scheduling at committed boundaries without changing scientific parameters.

The evaluation queue may start Base GSM after Base-dev, then consume each final
trained arm when its128 checkpoint is committed. CPU scoring continues alongside
GPU work. Training and inference process wall times overlap and must not be
summed as billed GPU hours. Preserve the complete powered-window accounting.
The midnight stop, finite requests, all official denominators and artifact
retention rules remain in force.

Before the first public-benchmark generation, the waiting evaluator was replaced
to use128-way GSM and256-way MATH batches uniformly across all five states. Dev
stays16-way, preserving the already-running Base-dev stream. Installed
Transformers4.56.2 automatically uses Qwen2's supported logits_to_keep=1 during
generation; this avoids materializing full-sequence vocabulary logits. The
larger public batches are an engineering throughput choice, not a score-based
choice. All IDs, seeds, draw counts, decode limits and scientific comparisons
are unchanged. Batch shape is bound into each immutable generation request;
sampled token streams need not equal the unexecuted64-way proposal. The64GiB
MATH admission effectively reserves the GPU for inference after training.
All82 CPU checks passed before deploying this evaluator. Actual first-batch
throughput and memory remain to be measured; a failed reserved batch must not
be silently regenerated.
