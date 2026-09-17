# Public-math execution is active and incomplete

The owner reopened the expanded A800, removed mandatory Mac checkpoint downloads,
deprioritized cost until the abstract deadline, and requested concurrent work to
use the server efficiently. The frozen four-arm scientific scope remains intact.
The timestamped observation is [LIVE_PROGRESS.json](LIVE_PROGRESS.json).

SFT and DFT each completed128 updates with committed, verified full recoveries.
TrimSFT is training; QDW-v0 follows from its separate fresh public base.
All4096 frozen masks and8192 annotation forwards are complete. The fixed64
technical audit passed, without changing masks. All512 Base-dev outputs are
durable, including32 preflight outputs reused exactly once; CPU scoring completed
that run. None of these statements is a public benchmark performance result.

The first128-way Base GSM batch failed with concurrent CUDA OOM before saving
any public output. Its257seconds and128 physical reservations remain recorded.
Training was not interrupted. The replacement uses64-way GSM uniformly across
all five states and an expandable CUDA allocator; it waits if less than26GiB
is free. Training caches later approached70GiB, so the unchanged evaluator is
now queued after all four arms complete. The stopped admission-only process
ran456seconds and added zero model calls. MATH uses256-way batches with64GiB
admission after training, and dev stays16-way. The one evidence-bound retry preserves the initial failed attempt.
See [the recovery record](../../experiments/public_math_pilot_v1/INFRASTRUCTURE_RECOVERY.md).
Maximum physical generation attempts are31,331 for31,203 logical outputs.

The detached trainer, evaluator and isolated four-worker CPU scorer survive an
SSH disconnection. Do not restart a live worker or repeat a completed output.
Raw batch identities, reserved call IDs, post-batch RNG and committed checkpoint
ancestry control resumption. Source commits are recorded in LIVE_PROGRESS.json;
new report commits do not replace the actual execution sources.

The server will retain all four final FP32 model/AdamW/RNG recoveries. Scientific64
weights remain until their required512 dev outputs and final recovery are verified.
Only verified superseded rolling files from this phase may be pruned. Compact
progress/receipts may be mirrored locally; no large checkpoint download is required.

GPU cutoff is2026-09-18 06:45UTC, CPU cutoff06:50UTC, and the exact current
instance's provider shutdown timer was confirmed for06:58UTC (23:58PDT).
A15-minute follow-up checks meaningful changes and completes authorized closeout.
At the nighttime boundary preserve unfinished coverage explicitly; do not drop
questions, shorten draws, count missing answers as wrong, or restart overnight.
Full completion also requires independent reconciliation and provider-off evidence.

The prior EXECUTION_SUMMARY_ZH.md and COST_AND_CLOSEOUT.json describe the earlier
zero-model startup window. They remain historical evidence. Current process
durations overlap and are not additive billed GPU hours; final accounting remains
open until the active processes and powered window close.

The queued evaluator uses a06:35UTC model deadline and a06:45UTC hard timeout,
leaving600seconds of additional completion reserve for larger batches. Its
per-batch admission check prevents starting new batches about240seconds before
the model deadline. This changes scheduling only, not any scientific output ID.
