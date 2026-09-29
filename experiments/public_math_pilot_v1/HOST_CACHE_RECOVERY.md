# TrimSFT checkpoint admission: clean file-cache recovery

The original trainer stopped at TrimSFT step64 before saving that checkpoint:
`Insufficient RAM for verified checkpoint`. SFT128 and DFT128 are already fully
committed; TrimSFT32 is the latest verified recovery. The process exited1 after
2180seconds. The32 completed but uncommitted TrimSFT updates33–64 remain in their
original immutable attempt directory. No scientific endpoint or result is deleted.

The cgroup has120GiB RAM. After process exit, memory.current was about68.2GiB,
of which about67.3GiB was clean file cache and0.67GiB anonymous memory. No dirty
or writeback bytes were observed. The frozen trainer conservatively subtracts
all cgroup usage from its limit, including reclaimable checkpoint file cache,
and requires48GiB of headroom before a verified save. Accumulated saved/reloaded
checkpoints can therefore trip admission without true anonymous-memory exhaustion.

Keep the exact original trainer source, scientific contract,48GiB gate, optimizer,
RNG and data order. A separate bounded CPU helper advises POSIX_FADV_DONTNEED
only for existing components on committed checkpoint ancestry in this owned phase.
It follows owner/manifest/path/size checks, rejects symlinks, ignores pending and
unrelated files, never deletes or rewrites data, and records measured cache/headroom
before and after advice. It runs only while training remains incomplete and before
the existing daytime cutoff. This manages cache residency rather than changing
the scientific implementation or bypassing the RAM gate.

Once headroom is restored, resume from TrimSFT32 using the same published source
and saved model/AdamW/RNG. SFT and DFT finals are verified and skipped. Exactly32
uncommitted updates must be recomputed to obtain the prescribed final128-update
TrimSFT state. Final committed scientific dose remains512 updates across four
arms; physical completed-update records will total544 including the32 lost work.
Preserve both attempt histories and their distinct receipts. QDW-v0 still starts
fresh from the public base. This is one bounded infrastructure recovery, not a new
seed, extra training epoch, checkpoint choice or outcome-based extension.

The dependent evaluator exited before model loading when the trainer failed.
After the training recovery is queued, requeue its identical published source and
frozen evaluation contract behind TRAINING_COMPLETE.json, preserving the same
one-time GSM OOM retry evidence and all generation accounting. CPU scoring stays
running. Report all results to the owner after the finite evaluation, then wait
for their next-direction decision; no optional experiment follows automatically.

The first cache pass reduced cgroup usage from73.25GB to1.73GB without changing
any checkpoint bytes. The recovered TrimSFT64 checkpoint subsequently committed
successfully. A passive comparison of the32 recomputed update records confirms
unchanged row identities, dose, learning rates and source. Scalar losses and
gradient norms match through step48, but the later GPU numerical trajectory
diverges; it is not bitwise equivalent. The cause of that divergence was not
isolated. Preserve the per-step measurements in
reports/public_math_pilot_v1/GPU_RECOVERY_COMPARISON.json and do not generalize
the exact CPU toy recovery test to full GPU trajectory reproducibility. The
recovery point was chosen from durable state before any public benchmark score,
not from either trajectory's performance. This execution limitation accompanies
the one-training-seed result in the final report.
