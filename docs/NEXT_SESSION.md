# Next-session handoff

## Current — 2026-09-08: calibration complete, comparison next

Read reports/PILOT_CALIBRATION.md and configs/pilot_v1/queue.json. The frozen
1024-update Repeat calibration passed with 14/64 matched-dev and 2/64 broader-dev
correctness. This is not the scientific Repeat arm. Raw outputs, preflight records
and the private ledger are independently backed up. All 50 Linux tests passed;
the new output verifier reproduced saved scores and exposure accounting.

The current ledger has 1719 seconds used and 5481 remaining, with no unresolved
reservation at this milestone. Preserve this ledger across any clone/replacement.
The owner already approved the finite four-arm comparison if the calibration gate
and full-phase budget pass; both passed. After publishing this milestone, sync the
clean current main and run the comparison phase. Four 1050-second jobs plus guards
reserve 4260 seconds. No further approval is needed for this already approved phase.

Use the current private connection settings; the supplied instance is reachable
through authenticated Jupyter terminal/file access while external SSH stalls before
authentication. Git bundles provide the published history when remote GitHub fetch
is unavailable. Do not reset authentication or weaken server protections.

Do not reuse an active/completed run ID. Inspect the ledger and GPU processes before
launching or shutting down. Keep all comparison predictions and four final weights,
verify independent checkpoint copies, publish results and refresh this handoff before
declaring the server disposable. No final holdout, extra seeds or main grid are approved.

Historical backup/shutdown information follows; its older 1173-second balance and
open-design questions are superseded by the current ledger and approved pilot.

## Shutdown-ready milestone — 2026-09-05 UTC

No GPU training or candidate-audit process was active at the final check. GPU memory and utilization were zero; the ledger had no unresolved job. The owner can shut down the current instance. No background experiment or scheduled GPU restart is requested.

The completed experiment/backup milestone is commit `c8a76eeb86e362d992acb6e6d294110610c41bca`; subsequent documentation is on `main`. Individual run manifests record their actual training source commit. Always fetch the current published branch rather than assuming an old cloned checkout is current.

Read `reports/STATUS.md` and `reports/A800_SESSION.md` for evidence. Main 1.5B overfit reached 32/32 train correctness, but development remained 0/16 greedy and 0/64 sampled. The latest operator-constrained candidate audit finds 256 matched problems from 4096 candidates, with 66416 supervised tokens per arm per cycle. No scientific treatment comparison has run.

## State retained independently of the instance

| State | Recovery source |
|---|---|
| Source, configs, tests, exact model revisions | GitHub `main`; per-run commit for reproduction |
| Synthetic candidate data, raw predictions, logs and metrics | Versioned `runs/` and `reports/` |
| Three saved overfit checkpoints (two debug, one main) | Verified local backups outside Git; manifests in each run and verification reports in `reports/` |
| Current cumulative resource ledger | Latest private local backup or active-server copy: 1173 seconds used, 6027 seconds remaining |
| Model/tokenizer base weights | Exact revisions and official expected file digests in `configs/models.lock.json`; verified cache if preserved, otherwise re-download |
| Environment | Pinned requirements/bootstrap and `reports/environment_a800.json` |

The main checkpoint has 12 files, totaling 6190803581 bytes, verified on the server and in the independent local copy. Previous verification reports and current backup file sizes were rechecked before shutdown. Checkpoints are weights/tokenizer only, without optimizer/RNG/sampler state; they do not support exact optimizer resume.

## Reuse, replace or clone an instance

1. Update the private connection configuration if needed. Keep credentials, endpoints and private paths outside Git.
2. Fetch GitHub and fast-forward a clean checkout. For a new checkout, clone this repository; use the documented Git-bundle fallback if GitHub is unavailable. Compare the remote checkout commit with the intended published commit before execution.
3. Inspect a cloned instance's actual environment and storage contents. Reuse matching packages/cache when valid; do not assume cloning preserved every required file. Verify model/checkpoint manifests at the destination. Rebuild/download only what is missing or incompatible.
4. Restore the latest cumulative ledger. An old 4090 image may contain a stale 737-second ledger; do not treat that as the current balance or start a fresh budget. Only one GPU job may run across all copies.
5. Restore a trained checkpoint only if the next task needs it, such as re-evaluation. A new independent training run should initialize from the pinned base model. This avoids unnecessary transfer of multi-gigabyte trained weights.
6. Run the relevant correctness/environment checks before starting new work. All GPU jobs remain bounded by `scripts/run_bounded.py` and need fresh run IDs. Do not overwrite recorded datasets or old run directories.

See `docs/MIGRATION.md` and `reports/ARTIFACTS.md` for commands and backup verification.

## Next discussion before more GPU work

- Whether to accept the restricted exact-match candidate domain and how to measure its selection bias.
- Stronger surface renderings, or an explicitly narrow interpretation of the existing label-only control.
- Group-disjoint train/development/sealed-holdout construction before augmentation.
- Common training dose, evaluation configuration and a measured single paired-seed pilot budget within the remaining 6027 seconds.

Resume with this design discussion; cloning or restarting an instance alone does not approve or launch the scientific comparison.
