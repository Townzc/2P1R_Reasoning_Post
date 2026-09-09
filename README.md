# 2P1R Reasoning Post-Training

**Problems, Paths, or Repeats?** A research workbench for controlled reasoning supervised fine-tuning (SFT).

The central question is whether within-problem structural path diversity helps beyond global strategy coverage, exact repetition, and surface diversity under matched supervision and optimizer-update budgets. Arithmetic is the first task; graph/relational reasoning and a second model family are planned boundary-condition checks. RL is outside the current scope.

## Current status

**2026-09-09 UTC:** The fixed seed23 Paths/GCM replication is complete.
Matched-dev greedy correctness is **22/64 versus 17/64**; broader-dev is
**1/64 for each arm**. Strict complete-trace verification is 18/64 versus
16/64 on matched dev and 0/64 versus 1/64 on broader dev. All 800 saved
predictions passed independent CPU scoring and the frozen pair audit.
See the [result analysis](reports/PILOT_REPLICATION_SEED23_RESULTS.md),
[result snapshot](reports/pilot_replication_seed23_after_gpu/results.json)
and [complete-pair audit](reports/pilot_replication_seed23_after_gpu_audit/summary.json).

The two runs charged **1004 process-seconds**. Cumulative usage is
**4716/7200 seconds**, with **2484 remaining**. New checkpoint downloads and
independent SHA-256 verification are **pending**. The private ledger has been
[reconciled against all 13 receipts](reports/replication_seed23_ledger_verification.json),
with zero unresolved reservations. Keep the instance until checkpoint backups
and publication are complete. No further GPU job or holdout
evaluation is scheduled. See [status](reports/STATUS.md),
[artifact recovery](reports/ARTIFACTS.md) and the [handoff](docs/NEXT_SESSION.md).

The [research journal](docs/RESEARCH_JOURNAL.md) separates motivations, designs,
results and interpretation. The [seed23 entry](docs/experiments/E009_seed23_paired_replication.md)
was recorded before its model outputs. Both arms used the same pinned base,
1024 updates and 267456 supervised response tokens. Seed17's corresponding
matched scores were 23/64 versus 18/64; these are two paired seeds on the same
restricted problem pool, not evidence of broad arithmetic generalization.

Next work is CPU construction of legal path families and shared problem support.
A numerical identity operation may be necessary to consume an input legally;
it is not automatically a Surface variant or an invalid strategy. The
[trace audit](reports/pilot_v1_trace_audit_20260909/FINDINGS.md),
[exposure audit](reports/PAIRING_SEED_SEMANTIC_AUDIT_20260909.md) and
[prior-work review](reports/ICLR_POSITIONING_20260909.md) limit the current claim.
The [ICLR evidence roadmap](docs/ICLR_EXPERIMENT_ROADMAP.md) describes later
scientific decisions; it does not authorize another training phase.

The earlier 1.5B engineering gate reached 32/32 train correctness on A800;
its FP32 AdamW recipe exceeded 4090 memory. Historical failed/negative runs
remain available in [reports/A800_SESSION.md](reports/A800_SESSION.md).

```bash
python -m unittest discover -s tests -v
python src/countdown_smoke.py --out runs/new_cpu_smoke/data --train 128 --dev 16 --test 32
```

Choose a new output directory for each run. The imported `fixtures/smoke_handoff` data is immutable and is only a small CPU example, not the final scientific test set.

Code, configurations, small raw predictions, metrics, manifests and run records belong in Git. Model weights, optimizer checkpoints, environments and credentials do not. Migration instructions will be maintained in `docs/MIGRATION.md`.

For resuming after shutdown, server replacement or an instance clone, start with [docs/NEXT_SESSION.md](docs/NEXT_SESSION.md). It records independently retained state, the current shared budget and the next decisions.

## Interpretation limits

Presentation matching is not token matching. P/T/R are coupled at a fixed budget. Canonical arithmetic syntax is an operational proxy for structure, not proof of distinct human strategies. All empirical claims must link to actual run records; negative and failed runs are retained.

## Bounded engineering run

Use Python 3.12 and a compatible PyTorch 2.8.0+cu128 base image; `bash scripts/bootstrap.sh` checks the base and creates a project overlay. See `reports/environment_4090.json` for the actual image package inventory. Activate the created environment with `source "${RUNTIME_ROOT:-$PWD/.local/runtime}/train/bin/activate"` (default `RUNTIME_ROOT="$PWD/.local/runtime"`). Set `HF_HOME` to a persistent model cache outside Git. All `python` commands below refer to that activated environment.

```bash
python scripts/download_model.py --role debug
python scripts/verify_model.py --role debug --out reports/new_model_verification.json
python -m scripts.audit_tokens --data runs/cpu_reproduction_20260905/data --out reports/new_token_audit.json
# Commit code first. Use a new run ID and the same budget ledger for every job.
python scripts/run_bounded.py --run-id overfit_example --max-seconds 1800 -- \
  python -m src.experiment --config configs/overfit_debug_low_lr.json --out runs/overfit_example
```

The run wrapper requires GNU `timeout`, reserves runtime persistently, forbids concurrent or unresolved jobs, and caps cumulative process time at the approved 7200 seconds. Instance idle billing is separate. Weights are excluded from Git; the initial engineering checkpoint saves model weights only and cannot resume optimizer state.
