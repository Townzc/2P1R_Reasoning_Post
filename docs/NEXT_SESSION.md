# Next session — E010 preserved; confirm normal shutdown, then review design

## Current verified state,2026-09-09 UTC

The owner restarted the A800 and authorized the frozen seed31 pair. Both runs
completed normally from the prepublished clean commit
`9217685f6bdb4d0c67a0d76513c12f89898593cb` at18:41:53 UTC:
`absent_boundary_paths_seed31_r1` and `absent_boundary_gcm_seed31_r1`.
**Do not launch these run IDs or any earlier queue again.**

Read [the full analysis](../reports/ABSENT_BOUNDARY_SEED31_RESULTS.md),
[E010](experiments/E010_absent_boundary_seed31.md), [status](../reports/STATUS.md)
and [the journal](RESEARCH_JOURNAL.md). The task-mode recommendation is Max for
execution/recovery and Ultra for a later broad, separable scientific redesign;
this recommendation does not assert a changed setting or authorize delegation.

| Endpoint | Paths | GCM |
|---|---:|---:|
| Matched greedy expression, primary |7/64 |5/64 |
| Matched complete trace |4/64 |4/64 |
| Broader expression and trace |0/64 |2/64 |
| Matched sampled pass@4 |11/64 |7/64 |
| Complete sampled traces |13/256 |15/256 |

All294 Linux preflight tests passed. Both arms completed1024 updates,4096
presentations,277760 EOS-inclusive supervised tokens,482848 processed tokens
and3734 padding tokens. Server and independent local audits of all800 saved
predictions are byte-identical across10 files. No technical GPU failure, retry,
nonfinite training or generation truncation occurred. The2048 raw holdout
groups remain unsolved and unevaluated. Identity absence still permits
cancellation/computed constants; matching does not eliminate numerical or
population selection. The old256-question pair is not a causal control for
this128-question pair.

## Budget and migration — never restore the stale pre-run balance

Each new run charged512 seconds. The current cumulative private ledger is
**5740/7200 charged,1460 remaining**,15 receipts,zero reservations. SHA256:
`1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
The [public ledger proof](../reports/absent_boundary_seed31_ledger_verification.json)
checks every receipt and preserves the prior13 jobs unchanged. The old4716-second
ledger is historical; do not restore it as current or initialize a new ledger
on a clone. The current2130-second pair reservation exceeds the1460 balance.
A new scientific plan and resource review are required before more training.

## Preservation complete; shutdown verification is the remaining gate

All compact outputs and the final ledger are independently local and published
at result commit `3585ad2d2f6424180b4b3ec345904dc0fc21fea6`, also synchronized
cleanly onto the server. Both checkpoints have independent SHA256 verification:
24 files,12,381,607,162 bytes. See the [backup summary](../reports/absent_boundary_seed31_checkpoint_backup_summary.json)
and [fresh idle/ledger check](../reports/absent_boundary_seed31_final_server_check.json).
No required unique experiment state remains only on the instance.

The owner's normal-shutdown authorization persists. The Mac is currently locked
and the tool cannot operate the authenticated console; the owner has been asked
to unlock it. The provider officially documents `/usr/bin/shutdown`; the installed
helper is inspected and its trash path does not exist. After preservation is
published, use that helper with fresh idle/ledger/identity checks if the UI is
still blocked. Do not delete/release the instance. Record whether shutdown was
requested, and do not treat an SSH disconnect as verified provider stopped state.

Inspect the private E010 shutdown gate and any appended public closeout before
another action. The existing heartbeat must only confirm/finish this phase's
normal shutdown, never train or target another instance. When the console is
available, independently match the known current instance and confirm stopped
state; if it still runs and remains idle, complete the authorized normal shutdown.
Pause the heartbeat only after verified stopped state so it cannot affect later
experiments. Do not repeatedly try to reconnect to a stopped server or start it.

All earlier seed17/23 scientific weights and engineering weights remain backed
up outside Git. Current weights also are model/tokenizer only, not exact
optimizer/RNG resume checkpoints. See [artifact inventory](../reports/ARTIFACTS.md)
and [migration protocol](MIGRATION.md). Public Git excludes private connection
information, credentials, local user paths, live ledger and weights.

## Proposed next scientific work — CPU only

The evidence does not justify scaling from the small favorable primary count:
trace results tie and broader results favor GCM. Preserve that weak boundary
result; do not search seeds or learning rates for a preferred sign.

Prepare a concrete task/estimand design for owner review. Assess a graph/relational
or controlled symbolic generator with multiple valid paths by construction,
rather than conditioning most questions on rare shared support. Audit gold
solver correctness, nuisance difficulty, shortcuts, population coverage and
train/development separation before model execution. Target multiplicity is
part of the allocation treatment; do not blindly match it away or interpret
lower repetition-training NLL as independent evidence of better reasoning.

No new benchmark or treatment is approved by this suggestion. Keep E010's
unchanged development endpoints and untouched holdout intact. The CPU search
failures, complete support archives, materialized data and source hashes are
recoverable from Git; normal training recovery needs no large CPU witness stream.
