# Next-session handoff

## Current — 2026-09-08: ready to request replacement A800

The owner approved the staged plan and asked to be told when a server is needed.
The prior server may no longer be available. Local CPU preparation is complete;
no old server was contacted. Start with PILOT_V1.md and configs/pilot_v1/queue.json.

The published pilot data has 256 train, 64 matched dev, 64 broader dev and
2048 unsolved reserved holdout groups. Four arms have exact token/update matching
at 267456 tokens / 1024 updates each. Preparation failures and integrity reports
are retained. This is a narrow single-seed pilot, not a generalization result.

On the owner's replacement A800, fetch current main, verify model/environment,
restore the latest private 1173-second ledger (6027 remaining), and run tests plus
the pilot verifier. Reuse verified base-model cache; no old overfit-checkpoint
upload is needed. Comparison checkpoint storage requires 30 GiB free.

Run only the 900-second calibration phase first. Inspect its development gate,
generation truncation and measured costs, publish results, then use the four
1050-second comparison jobs if the gate and full-phase budget checks pass.
No automatic rental, background job or holdout evaluation is configured.

Historical backup/shutdown information follows and remains valid; the old
open-design discussion at the end is superseded by the approved pilot v1 plan.

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
