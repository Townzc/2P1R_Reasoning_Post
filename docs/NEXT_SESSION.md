# Next-session handoff — seed23 pair ready for an owner-supplied A800

## Current state — 2026-09-09 UTC

The next experiment is the fixed two-arm replication in
[PILOT_REPLICATION_PROPOSAL.md](PILOT_REPLICATION_PROPOSAL.md). All CPU data and
configuration preparation is complete; no seed23 model run or old-server
connection occurred during preparation. Both proposed scientific jobs remain
`not_run`. The owner will start/reuse/rent an A800 after reviewing this plan.

Read [STATUS](../reports/STATUS.md), the proposal and
[ICLR_EXPERIMENT_ROADMAP.md](ICLR_EXPERIMENT_ROADMAP.md). Recent prior work already
covers the broad per-problem/global-diversity question. Trace and structure audits
also limit interpretation of the first pilot. This pair checks sensitivity to a
new assignment/order/training seed; the later roadmap is not a GPU launch plan.

The completed seed17 primary scores remain Paths 23/64 vs GCM 18/64 matched-dev
and 4/64 vs 1/64 broader-dev. Fully verified broader traces are 1/64 each. Keep
primary and secondary metrics distinct, publish either sign of replication,
and do not search seeds until a positive difference appears.

## Frozen next phase

- Queue: `configs/pilot_replication_seed23/queue.json`, comparison phase only.
- Fresh run IDs: `pilot_replication_paths_seed23_r1`, `pilot_replication_gcm_seed23_r1`.
- Data: `runs/pilot_replication_seed23_20260909_r1`.
- Manifest SHA-256: `0959c217feb4b0c51aebf85c1f08e341e1b6c8034657ee028acb263a2ee18ad4`.
- Same 256 training problems, both 64-problem dev sets, pinned Qwen2.5-1.5B base,
  recipe and 1024 updates / 267456 supervised response tokens per arm.
- New assignment/order/training seed23; sampled evaluation seed stays17.
- Reuse the already completed seed17 calibration receipt. It is a dependency in
  the new queue, not a job to rerun. Do not run the old four-arm queue again.
- Latest ledger: **3712/7200 process-seconds used; 3488 remaining**. Whole-phase
  reservation: **2130 seconds**, using two 1050-second caps plus guards.
- One A80080GB is sufficient. Require **18 GiB free** in the run filesystem after
  environment/base cache setup. Earlier allocated GPU peak was 26.21 GiB.

The [new-data verifier](../reports/pilot_replication_cpu_verification_20260909.json)
and [original-data regression](../reports/pilot_original_cpu_verification_20260909.json)
both passed with the pinned real tokenizer. The parent problem/split/dev files
are byte-identical; exact token and per-update structure constraints hold. Source
file hashes identify preparation code including files not yet committed at build
time; the published milestone supplies the full execution source. Never alter a
frozen input in place. No reserved holdout solution or model output was read.

## Independent recovery sources

| State | Recovery source |
|---|---|
| Source, configs, frozen data, raw predictions, receipts and CPU audits | Latest published GitHub main; verify the actual fetched commit |
| Four completed scientific weights | Independent local SHA-256-verified backups, 48 files / 24.8 GB; see ARTIFACTS.md |
| Three earlier engineering checkpoints | Previously verified local copies outside Git |
| Current cumulative ledger | Private local backup reconciled against 11 receipts, 3712 seconds |
| Base model/tokenizer | Exact revision and official file hashes in configs/models.lock.json |
| Environment | Pinned bootstrap/requirements and actual A800 environment report |

The seed17 four-arm training source was
`c4f4038f0d1582dc3586802af9d5f22fbfaa13c2`. The seed23 pair must use the new
published source. Old weights are not needed for independent base-model training
and should not be transferred merely to set up a replacement. Existing weights
do not contain optimizer/RNG/sampler state and cannot exactly resume training.

## On the supplied instance

1. Keep current connection endpoints and credentials outside Git. Fetch/fast-forward
   the latest published history into a clean checkout. If GitHub cannot be reached,
   use the verified Git-bundle workflow in MIGRATION.md. Confirm completion of sync
   before any launch; a clone may be stale.
2. Inspect the actual GPU, Python/PyTorch packages, base cache and free disk.
   Reuse only verified caches. Bootstrap the pinned overlay if necessary and
   verify the main model against its official file hashes.
3. Restore the **3712-second** ledger to `.local/resource_ledger.json`; reject older
   1173/1719 copies. Inspect processes and reservations; allow only one active job
   across all instance copies. A fresh instance is not a fresh compute allowance.
4. Run the CPU checks below with the pinned tokenizer environment, then the dry
   queue. Linux must run the GNU-timeout integration tests that macOS skips.
5. Once the owner has supplied the instance for the fixed phase and preflight
   passes, run only the bounded comparison command below. An instance boot itself
   must not trigger training. Preserve all technical failures and stop the queue
   on any mismatch, timeout or failed complete-dose check.

Run from the project root with the prepared Python environment:

```bash
# PILOT_TOKENIZER_DIR points to the verified local pinned tokenizer snapshot.
python -m unittest discover -s tests -v
python -m scripts.verify_pilot \
  --config configs/pilot_replication_seed23/paths.json \
  --tokenizer-dir "$PILOT_TOKENIZER_DIR" \
  --out reports/replication_seed23_server_data_verification.json
python -m scripts.run_pilot_queue \
  --queue configs/pilot_replication_seed23/queue.json \
  --phase comparison --ledger .local/resource_ledger.json

# Start only the reviewed pair after the supplied-instance checks pass.
python -m scripts.run_pilot_queue \
  --queue configs/pilot_replication_seed23/queue.json \
  --phase comparison --ledger .local/resource_ledger.json --execute
```

Use a persistent shell/log if the interactive connection may close; the queue's
independent watchdog and persistent budget ledger still apply. The prior instance
supported authenticated Jupyter when SSH stalled before authentication. That is
a fallback to check on the actual new instance, not a promise that old access
still works. No foreground browser tab should be required for sustained work.

## After both jobs

Rescore and reconcile each saved run with `scripts/verify_pilot_outputs.py`,
then create an immutable snapshot with `scripts/report_pilot.py --queue
configs/pilot_replication_seed23/queue.json`. Run the frozen trace/stratum
analysis on both saved outputs:

```bash
python -m scripts.audit_replication_outputs \
  --queue configs/pilot_replication_seed23/queue.json \
  --out reports/pilot_replication_seed23_after_gpu_audit
```

This requires both completed, matching-source jobs, re-verifies official scores
and dose, and rejects changed development bytes or frozen stratum labels. It
cannot produce a result while either job is not_run. Keep all raw generations, including failures;
report greedy primary, sampled pass@1/2/4, complete-trace categories and the
already fixed descriptive strata for each seed separately.

Publish compact artifacts and updated interpretation to GitHub. Independently
copy and SHA-256-verify both new checkpoints and the current ledger before
calling the instance disposable. Check that no job or reservation remains;
then tell the owner the server can be stopped. CPU design of a broader semantic
intervention can continue while the instance is off. No automatic new seed,
main grid, holdout evaluation, larger rental or budget extension is implied.
