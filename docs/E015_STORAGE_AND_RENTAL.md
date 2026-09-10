# E015 storage preservation and rental window

The owner supplied **CNY 8 per powered-on hour** and a **CNY 3,000 overall
spending ceiling** on 2026-09-10 and authorized the next E015 step. These
authorize economical preparation and the finite experiment; they are not a
request to spend the ceiling or leave the instance running. At the stated
rate, CNY 3,000 is 375 powered-on
hours before provider rounding, storage or other fees. Actual historical spend
and provider billing granularity are not yet reconciled; the remaining
financial balance is unknown, not an assumed CNY 3,000 account balance.

This document prepares one E015 terminal-LR repair and its preservation plan.
**No server contact, remote deletion, model execution or startup occurred in
this preparation.** The latest server state below is historical, not a fresh
claim of availability. The fresh local verification is recorded in
[the preservation receipt](../reports/real_math_e015_local_preservation.json).

## Exact duplicate cleanup

The original base model is required for fresh initialization. E013's failed
tuned checkpoint is a historical diagnostic artifact, and its independent
local copy has been reverified: 12 regular files, **6,190,803,414 bytes**, all
SHA256 values matching the published
[checkpoint manifest](../runs/gsm8k_overfit_e013_r1/checkpoint_manifest.json).
This is a weights/tokenizer backup; it does not restore an optimizer/RNG
trajectory. The latest local ledger is separately verified at 18 receipts,
6,467 charged process seconds and zero reservations.

The only remote deletion candidate in this plan is the exact directory
`runs/gsm8k_overfit_e013_r1/checkpoint_final`, after the checks below. There is
no deletion command queued. Routine removal of this fully verified duplicate
preserves the experiment and follows the existing preservation-backed cleanup
practice; it does not authorize deleting unique state or widening this list.

| Quantity | Bytes | GiB |
|---|---:|---:|
| Historical E014 free space | 6,756,548,608 | 6.2925262451 |
| E013 checkpoint logical size | 6,190,803,414 | 5.7656349745 |
| Predicted free space after full reclaim | 12,947,352,022 | 12.0581612196 |
| Required post-setup free space | 12,884,901,888 | 12.0000000000 |

The prediction is only **62,450,134 bytes / 59.557 MiB above the gate**. Logical
size is not guaranteed physical reclamation: hard links, open handles,
filesystem behavior and intervening writes can change it. Do not lower the
12 GiB gate or treat this arithmetic as evidence that it currently passes.

After the owner starts the instance, use this bounded sequence:

1. Stage the published source/input release first. Verify its commit, the
   original pinned base bytes, current ledger and idle process state. Remove
   only the newly created temporary transfer bundle after verified import if
   needed; do not clean unrelated caches or artifacts.
2. Recheck the independent local backup against the exact published manifest.
   On the server, resolve the candidate beneath this checkout's `runs`
   directory and reject symlinked path components, missing/extra entries,
   nested directories, non-regular files or a different 12-file inventory.
   Check every file's length and SHA256 against the same manifest. Confirm
   no job uses these weights; detect hard links/open files that could prevent
   predictable reclamation. Preserve a compact pre-cleanup receipt locally.
3. Delete only those verified duplicate checkpoint files and their now-empty
   checkpoint directory. Retain the surrounding E013 run directory, public
   manifest, predictions and receipts. The base-model cache, all other
   checkpoints, current ledger and independent local backups are excluded.
4. Measure actual free space on the filesystem used by the new run **after
   staging and cleanup**. Require at least 12 GiB before reserving/starting
   E015. Record before/after measurements and the exact removed inventory.
   If the gate fails, do not start training or broaden cleanup; retain the
   failure receipt, shut down through the provider and resolve storage locally.

Prior evidence for this pattern is
[the seed23 duplicate-checkpoint cleanup](../reports/replication_seed23_storage_cleanup_20260909.json).
That history establishes the preservation procedure, not today's remote state.
No disk purchase, larger instance, base re-download or deletion of another
checkpoint is part of this finite queue.

## Evidence-based powered-on allowance

The previous E013 backup took **974.326825 seconds / 16.24 minutes** for the
same 6.19 GB checkpoint, including independent verification, averaging
**6.06 MiB/s** end to end. See
[its measured backup receipt](../reports/real_math_e013_checkpoint_backup.json).
Thus the earlier illustrative eight-minute export and twenty-minute whole
window are not supported by the measured transfer. Reuse the authenticated
range-transfer approach, with bounded connection/read/retry time and an
overall deadline; the old private helper's blocking read alone is insufficient
to enforce a transfer deadline.

Prepare a **40-minute target window (approximately CNY 5.33)** and a
**45-minute hard planned ceiling (CNY 6.00)** before rounding/other fees:

| Phase | Target allowance |
|---|---:|
| Startup, exact release staging and instance checks | 6 minutes |
| One bounded E015 process including guard | 6.25 minutes |
| Compact-output/ledger export, checkpoint transfer and SHA256 verification | 22 minutes |
| Provider shutdown and operating slack | 5.75 minutes |
| Total target | 40 minutes |

The extra five minutes between target and ceiling is preservation/shutdown
contingency, not time for another experiment. The 22-minute export allowance
is about 35% above the measured E013 transfer; it is a planning allowance, not
a guaranteed network throughput. All fees count toward the overall CNY 3,000
ceiling, and future windows need their own finite queue and estimate.

At job admission, require at least **2,040 seconds** before the absolute
powered-on deadline: 375 for the guarded process, 1,320 for export and
verification, and 345 for provider shutdown/slack. Missing that admission
requirement means no model job starts; do not shorten export or shutdown
reserves to fit a delayed preflight.

The existing scientific process ledger remains separate: 733 seconds are left
under its original 7,200-second authorization. E015's 360-second process plus
15-second guard reserves at most 375, leaving at least 358. The
money authorization must not reset historical process receipts or silently
start a larger comparison grid. This current process balance is not a permanent
financial restriction on later scientifically approved finite phases: record
their prospective process caps and complete-phase cost separately, retaining
the original ledger and all historical receipts.

Before notifying the owner that startup is needed, publish the execution
source and pass the offline CPU checks; prepare and locally check the release
bundle, transfer destinations, manifests and finite launcher. Keep at least
7 GiB of local destination headroom for the new checkpoint and compact artifacts.
Confirm that provider stop preserves the attached data volume, and identify
who will perform and confirm that stop; no container command substitutes for
provider confirmation. Do not launch if startup/preflight delay or transfer
readiness makes completion and safe exit within the reviewed window unlikely.

Export the small raw outputs and latest ledger first, then the new checkpoint.
Use a new destination and a new checkpoint manifest; never overwrite the
verified E013 backup. Mark a new backup verified only after every full-file
size and SHA256 matches. Transfer partials are not recovery evidence. Perform
the full CPU analysis, report writing and GitHub publication after shutdown.

## Optional CPU export after releasing the GPU

AutoDL documents a no-card mode for transfers with 0.5 CPU core, 2 GB RAM and
no GPU at CNY 0.1/hour, limited to one such instance per main account. It
requires shutdown before restart in that mode, preserves existing data and
releases the GPU; a later GPU restart can encounter unavailable capacity.
Verify the option, eligibility and displayed rate in the current console
before using it. [Official mode documentation](https://www.autodl.com/docs/save_money/).

After the finite model job, an optional prepared exit is to copy compact
outputs/current ledger, confirm normal shutdown, restart the same instance
without a card, and finish the bounded streaming checkpoint export/hash
verification. This is a transfer option, not another training job. Account
for both intervals and transition time, then confirm the final stop. The
conservative 45-minute GPU-mode plan remains the fallback; no lower actual
bill or successful mode switch is claimed in advance. Reduced CPU resources
may lengthen transfer or hashing; this mode has no measured export timing here.

Ordinary shutdown retains instance data, but the provider's retention rules
and possible local-disk failures make this temporary preservation, not an
independent or indefinite backup. Verify the instance's release deadline and
finish the external copy promptly. Never release/delete the instance while
unique required state remains there.
[Official data-retention documentation](https://www.autodl.com/docs/instance_data/).

## Transfer failure and actual closeout

If export stalls, stop further work and act before the ceiling: preserve the
latest ledger, receipt and partial-transfer state, and use the preconfirmed
provider stop that retains the volume. Do not delete/dispose of an instance
holding unbacked unique weights. Report an incomplete backup explicitly and
prepare a separately bounded recovery window. A planned ceiling is not proof
of stopped billing: record the actual provider-confirmed stop, or explicitly
mark it unverified. Reconcile the actual rental window and process receipt
separately afterward.
