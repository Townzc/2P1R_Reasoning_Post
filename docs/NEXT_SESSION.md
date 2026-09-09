# Next session — C016 data ready; prepare the bounded execution release on CPU

## Current: do not ask for server startup yet

Read [C016 findings and interpretation](../reports/RELATION_C016_CPU_READY.md),
[frozen registration](experiments/C016_relation_diagnostics.md),
[CPU release identities](../configs/diagnostics/relation_c016_release.json) and
[exact examples](../reports/RELATION_C016_EXAMPLES.md). All288 retained rows,
state masks and exact exposure schedules are frozen. Independent audit from
a clean published checkout agrees;53 focused tests pass without skips.

The owner approved CPU preparation only in this round. No GPU task is queued.
The next concrete CPU implementation is a diagnostic runner plus raw-token
auditor using these frozen inputs and score functions. Default to inspection;
require explicit execution after owner review and an owner-started instance.
Do not point the E011 launcher at these new tasks or reuse its completed ID.

Preserve the proposed order: single_step, given_route, fixed_reference. Each
starts from the original pinned1.5B base, never E011/preceding tuned weights.
Prepare one360-second process cap plus15-second guard per arm, no retry,
and stop after any failed/incomplete training gate. Up to1125 total reservation
seconds fit in the1229 remaining; do not create a new allowance. Future launch
guards must compare the current receipt chain under lock, not reuse an initial
ledger hash after a completed diagnostic changes it.

Current ledger:5971/7200 used,16 receipts,zero reservations,SHA256
`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
The independent local backup remains authoritative; cloned disks are not a
budget reset. E011 checkpoint has12 verified files/6190803414 bytes backed up.
C016 made no server connection or checkpoint change; the last authenticated
provider state is stopped in the retained E011 shutdown receipt.

C016 manifestSHA256:
`cb923a3e11817682f77b4116d7524e615bdffee29e04e5848b3815352aa8133e`.
Sourcef073955 was published before CPU extraction. Data4a5ad97 were then
verified from a clean checkout. Do not overwrite or regenerate the registered
attempt. Shared code hashes are pinned; keep historical runtime dependencies
unchanged and register revisions rather than silently editing frozen inputs.

Operational cautions for later implementation: strictly enforce the supplied
route, accept any legal route for fixed-reference scoring, count lookup
parents as all four subproblems, retain all raw IDs through EOS, distinguish
free-generation proof correctness from gold-prefix field metrics, and audit
parseable steps even when the final line is missing. All supervised field
positions use exact full serialization and logits[j-1]. No packing/truncation
or loss reweighting. Train/development table overlap is known and documented;
these are not new holdout groups or independent-row generalization results.

Before a later server run, verify current published source, original pinned
model/environment/tokenizer, idle A80080GB, latest ledger and measured free
disk. Preserve independently verified checkpoint copies before any cleanup.
Signal the owner to start/provide a server only once the execution release is
fully implemented, tested, published and concretely reviewable.

## Historical: E011 failed learning gate; no GPU phase queued

Read [full results and analysis](../reports/RELATION_E011_RESULTS.md),
[CPU verification](../reports/relation_e011_output_verification.json),
[ledger reconciliation](../reports/relation_e011_ledger_verification.json) and
[checkpoint backup](../reports/relation_e011_checkpoint_backup.json).
Run `relation_overfit_e011_r1` completed normally from published33820d9,with
256 updates/103424 supervised tokens. It failed the engineering gate:0/32
complete train proofs and0/16 for each dev view; every parseable generated
step result was2. No additional GPU run is authorized automatically.

**Current ledger:5971/7200 used,1229 remaining,16 receipts,zero reservations.**
SHA256:`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
The prior5740 balance and E011's launch config are historical; its guard should
reject replay. Restore the latest independently retained ledger on a clone.
All12 checkpoint files (6190803414 bytes) are independently backed up with
SHA256 verification. Compact outputs are fully tracked; weights remain private.
The authenticated provider console confirms **已关机** after publication and
preservation; see [closeout](../reports/relation_e011_shutdown_closeout.json).
No server is needed for the next CPU preparation. On any later restart or
clone,fetch current Git and restore the latest5971-second ledger before work.

Next do CPU diagnosis/preparation. Keep the original full-graph task and failed
run. Consider one fixed reference per original prompt at the same dose,
a supplied-route propagation diagnostic,and a one-edge table lookup gate.
Different diagnostic tasks are not comparable scientific treatment effects.
Predeclare selection,semantic-field measurements,proof/EOS criteria and complete
resource caps before any new model evaluation. Do not claim impossibility,
causal route effects or ICLR readiness from this engineering failure.

The cached CPU audit adapter at ecc7867 memoizes only immutable vocabulary size;
the original scorer and frozen runtime hashes remain unchanged. All96 outputs
produce byte-identical server/local audits. All42 Linux tests passed after a
private tokenizer-path symlink fixed one retained initial skip. No GPU retry.

## Historical: E011 CPU release complete — request owner-started A800

Read [ready report](../reports/RELATION_E011_READY.md),[registration](experiments/E011_relation_engineering.md),
[release hashes](../configs/relation_engineering_e011/release.json) and
[CPU verification](../reports/relation_engineering_c015_verification.json).
Preparation source `8eeb0f9883759a69ca42540932b98d71b2c64414` preceded extraction.
`runs/relation_engineering_c015_r1` is immutable and fully tracked; do not rerun.
Its manifest SHA256 is`ddb0068a2ddef8150948b7f8eaf0f2b86d3c3f9a42268c7d7725f44ee1afb854`.

No server operation/GPU spending occurred. One registered job remains not_run:
`relation_overfit_e011_r1`. One A80080GB is appropriate for the planned recipe;
actual long-prompt memory/time is unmeasured. Ask the owner to start/provide it
now that CPU preparation is complete. Do not reuse any completed queue.

On connection:

1. Fetch and verify the latest published main; do not rely on a cloned checkout.
2. Restore the independently retained15-receipt ledger:5740 used/1460 remaining,
 zero reservations,SHA256`1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
 Never initialize a fresh allowance. Restore the pinned original base,not tuned weights.
3. Verify recorded Python3.12/PyTorch2.8.0+cu128 environment and requirements,
 idle A80080GB,and12GiB free after model/environment setup. Keep backups before
 any cleanup; request expansion only if the measured free space requires it.
4. Run all42 focused tests with the real tokenizer on Linux,including both
 GNU-timeout integrations. Run launcher inspection,then the fixed `--execute`
 command below. It reserves at most735 seconds and never auto-retries.
5. Collect stdout,raw token predictions,history,metrics,checkpoint manifest and
 process receipt on completion or failure. Independently audit/reconcile/back up,
 publish the complete result and follow the owner's normal-shutdown preference.
 Process timeout alone does not power off the instance. Do not expose credentials
 or private endpoints in tracked files. No automatic scientific follow-up.

```bash
# Set TOKENIZER_DIR to the verified local pinned snapshot; activate the GPU runtime.
RELATION_ENGINEERING_TOKENIZER_DIR="$TOKENIZER_DIR" python -m unittest tests.test_relation_engineering tests.test_relation_transport tests.test_relation_cpu_audit tests.test_sft_data tests.test_budget_guard -v
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --tokenizer-dir "$TOKENIZER_DIR"
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --execute
python -m scripts.audit_relation_engineering_outputs --run-dir runs/relation_overfit_e011_r1 --tokenizer-dir "$TOKENIZER_DIR" --out reports/relation_e011_output_verification_r1.json
```

The fixed256 updates and96 generations test engineering feasibility only.
32/32 complete EOS-terminated train proofs,NLL<.2 and complete profile/dose are
required for the gate. Preserve even zero dev accuracy; do not select by the
16 diagnostic parents. Report causes of failure before designing a bounded
repair; a success supports a separately reviewed fresh-group scientific pilot.
Max remains the recommendation for execution/verification; no mode switch is asserted.

## Historical C015/E011 source milestone — publish before extracting inputs

The next executable engineering phase is registered in
[E011](experiments/E011_relation_engineering.md). Fixed32 train/16 diagnostic
worlds from declared C014 seed prefixes,256 updates, multi-route only,
strict32/32 overfit gate and measured long-context profile. One720-second
process plus15-second guard fits1460 remaining. No scientific pair is queued.

Publish source, materialize immutable `runs/relation_engineering_c015_r1`,
independently reload/check the compact bundle, freeze the release hash and
publish the complete CPU-ready record before asking the owner to start A800.
Use the exact retained15-receipt ledger (5740 used), never a fresh or cloned
stale ledger. Source/inputs are prepared locally; no server operation occurred.

## Historical: C014 complete, independently verified, no GPU queued

Read [C014 results](../reports/RELATION_TRANSPORT_C014_RESULTS.md),
[registration](experiments/C014_relation_transport_cpu_audit.md),
[summary](../reports/relation_transport_c014_r1/summary.json) and
[independent receipt](../reports/relation_transport_c014_verification.json).
Source `6c24d4c1379a421be7b44151c653842a6cd9aabf` was published before execution.
Do not rerun or overwrite `relation_transport_c014_r1`.

All10,000 intended worlds were retained with four valid length-four evidence
routes and101 supervised tokens per clean reference. Full clean serialized
length is1137, versus the old arithmetic384-token cap. Useful/irrelevant
deletion both have949 prompt tokens. All40 predefined CPU probe tests remain
unflagged; separate verification retokenized40,000 references and50,000 views
and checked80,000 predictions. This is an observed CPU sandbox; never relabel
its2,000 audit worlds as an untouched final test. The8,000-update schedule is
accounting only, not a training queue.

Next implement and freeze a small32-world engineering/profile runner with
the same pinned1.5B base, full FP32 AdamW/BF16 recipe and new serialization.
Prepare exact inputs, strict proof metrics, context/generation caps and a
complete per-job budget before requesting an A800. Existing arithmetic memory/
throughput measurements do not establish the cost of1137-token examples.
Do not launch a scientific pair, change optimizer/model, or extend the total
7200-second allowance. Remaining1460 seconds has zero reservations. The server
was confirmed stopped after E010; no server operation occurred in C014.

State/table exposure remains unequal under route allocation despite exact
tokens; do not select a more balanced seed after observing residuals. The
claim is evidence-route allocation within one algorithm and topology. A
separate final scientific population/protocol and novelty case remain pending.
The implementation/verification task fits Max; no setting change is asserted.

## Historical P003 decision and C014 preparation

### P003 reviewed; no GPU queue at the design milestone

The owner requested immediate task/control redesign. Read
[the integrated proposal](CONTROL_REDESIGN_PROPOSAL_20260909.md) first, then
the three linked independent reviews. The current arithmetic study is retained
as a restricted boundary result; do not add seeds to seek a preferred sign.
The selected **CPU candidate** is permutation relation transport with four
equal-length evidence routes, a repeated-route allocation control, and
predeclared useful/irrelevant evidence deletion. It is not a semantic-strategy
benchmark, and anonymous slot balancing is not global strategy coverage.

Prepare one bounded CPU implementation/registration and publish source and
config before materialization. The 10,000-instance audit size in the proposal
is prospective, not a completed result. Freeze probe definitions/thresholds,
seed list, serialization, symmetry groups and solver negatives. Independently
verify full support, counterfactuals, exact tokens, schedules and leakage;
retain every generation attempt and every failure. No selective token filtering.
Report state/table-exposure residuals and the limitations of fixed-topology IID
evaluation. No existing holdout access or automatic training is authorized.

The task recommendation is Ultra for separable scientific review and Max for
the bounded implementation/verification stage; no setting change is asserted.
Only after CPU receipts pass should a concrete training/profile/replication
and resource proposal be prepared. Remaining GPU allowance is1460 seconds;
there is no new reservation, startup or extension.

The E010 provider instance is **confirmed stopped** at approximately20:00 UTC;
the confirmation heartbeat is **paused**. See the
[sanitized closeout](../reports/absent_boundary_seed31_shutdown_closeout.json).
Do not reopen it merely to complete documentation or CPU development.

## Historical E010 state,2026-09-09 UTC

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

## Preservation and shutdown verification complete

All compact outputs and the final ledger are independently local and published
at result commit `3585ad2d2f6424180b4b3ec345904dc0fc21fea6`, also synchronized
cleanly onto the server. Both checkpoints have independent SHA256 verification:
24 files,12,381,607,162 bytes. See the [backup summary](../reports/absent_boundary_seed31_checkpoint_backup_summary.json)
and [fresh idle/ledger check](../reports/absent_boundary_seed31_final_server_check.json).
No required unique experiment state remains only on the instance.

The vendor's `/usr/bin/shutdown` command was executed at19:00:27 UTC with
exit0 after fresh instance/GPU/ledger/source checks. The server had preservation
commit `b27a85c3ee20c208a1b12a7653dd971c152c7f15`. A prior45-second GitHub-pull
timeout was recovered with a verified incremental bundle; the first shutdown
precondition rejected the stale HEAD before any command executed. At19:01:07
UTC SSH was no longer accessible. See the [shutdown request](../reports/absent_boundary_seed31_shutdown_request.json)
and [connectivity receipt](../reports/absent_boundary_seed31_after_shutdown_connectivity.json).

The Mac lock initially prevented confirmation. During the later CPU design
review, Computer Use read the authenticated provider instance list and matched
the exact instance against the private gate: it displayed **已关机**. Confirmation
was recorded at20:00:03 UTC and the heartbeat paused. No second shutdown command,
server start, deletion or release occurred. This verifies provider stopped
state, not an itemized billing-history reconciliation. The prior pending-state
receipts remain historical. Do not reopen the instance for CPU work.

All earlier seed17/23 scientific weights and engineering weights remain backed
up outside Git. Current weights also are model/tokenizer only, not exact
optimizer/RNG resume checkpoints. See [artifact inventory](../reports/ARTIFACTS.md)
and [migration protocol](MIGRATION.md). Public Git excludes private connection
information, credentials, local user paths, live ledger and weights.

## Historical motivation for P003 — CPU only

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
