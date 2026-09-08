# Next-session handoff — completed paired pilot

## Current state — 2026-09-08

Read ../reports/PILOT_V1_RESULTS.md and ../reports/pilot_after_comparison_r1/results.json.
Matched-dev greedy scores: Repeat 14/64, Surface 12/64, Paths 23/64, GCM 18/64.
Broader-dev scores: 2/64, 0/64, 4/64, 1/64. This is one paired seed on restricted
development data. All arms completed the same 1024 updates and supervision dose;
raw predictions and actual exposure accounting were independently checked on CPU.

The finite comparison queue has exited successfully. A800 GPU memory/utilization
were both zero and no experiment/queue process remained. The final ledger has
**3712/7200 process-seconds used, 3488 remaining**, with no unresolved reservation.
The private local ledger backup is current; older 1173/1719-second copies are stale.
No further seed, main grid, holdout evaluation or GPU restart is approved.

Independent checkpoint backups verified so far: repeat, surface.
Remaining weight transfers are in progress. GPU work is finished, but do not
declare the server disposable until all four checkpoint backups are verified.
Publication and the final server check must also be complete.

## Recovery sources

| State | Independent recovery source |
|---|---|
| Code, configs, data, raw predictions and receipts | GitHub main; actual training source is recorded in each run manifest |
| Four scientific pilot weights | Local backups outside Git once each checkpoint verification report is present; see ARTIFACTS.md |
| Three earlier engineering checkpoints | Previously verified local copies outside Git; historical manifests/reports retained |
| Latest cumulative ledger | Current private local backup, reconciled against all 11 receipts: 3712 seconds |
| Base model/tokenizer | Pinned revision and official file hashes in configs/models.lock.json; verified cache or exact re-download |
| Environment | Pinned bootstrap/requirements and the current A800 preflight report |

All four arms trained from commit `c4f4038f0d1582dc3586802af9d5f22fbfaa13c2`.
Fetch the latest published main for continuation; do not assume a cloned checkout
already contains the completed experiment records. The final weights do not
include optimizer/RNG/sampler state and do not support exact optimizer resume.

## Reuse, clone or replace an instance

1. Keep current credentials/endpoints in private connection settings outside Git.
2. Fetch and fast-forward the published history in a clean checkout. If GitHub is
   unavailable remotely, use the verified Git-bundle workflow in MIGRATION.md.
3. Inspect the actual environment, cache and free disk; verify pinned model files
   and any transferred artifact against its manifest. A clone is a convenience,
   not proof that files match or that a new compute budget is available.
4. Restore the latest 3712-second ledger. Permit only one active GPU job across
   copies. Inspect processes/reservations before any new launch.
5. Restore trained weights only if the next approved task needs them. A new
   independent training run starts from the pinned base, so old weights need
   not be uploaded merely to resume project work.
6. Starting/cloning the instance alone must not launch training. Use fresh IDs,
   bounded jobs and a full-phase budget check after owner review of the next phase.

The current server is accessible through authenticated Jupyter while external
SSH stalls before authentication. An independent browser tab and authenticated
file transfers avoid requiring the owner to keep a desktop browser focused.
See MIGRATION.md; never reset authentication or weaken protections to reconnect.

## Next decision

Review PILOT_REPLICATION_PROPOSAL.md: two Paths/GCM jobs with a new paired
order/assignment seed, unchanged selected problems, dose and evaluation. A mere
Torch seed change with the old frozen schedule is insufficient. The proposed
whole phase reserves 2130 of the remaining 3488 seconds. No launch is authorized
by this proposal. Prepare/verify CPU artifacts first, then request server access
only if the owner approves. The present A800 has sufficient memory.
