# 2P1R Reasoning Post-Training

**Problems, Paths, or Repeats?** A research workbench for controlled reasoning supervised fine-tuning (SFT).

The central question is whether within-problem structural path diversity helps beyond global strategy coverage, exact repetition, and surface diversity under matched supervision and optimizer-update budgets. Arithmetic is the first task; graph/relational reasoning and a second model family are planned boundary-condition checks. RL is outside the current scope.

## Current status

The CPU generator is reproduced and 35 server-side tests pass. Exact-token audits and bounded engineering SFT are implemented. No scientific treatment result is claimed. See [reports/STATUS.md](reports/STATUS.md) for verified progress and [docs/PROTOCOL.md](docs/PROTOCOL.md) for the current protocol and unresolved decisions.

```bash
python -m unittest discover -s tests -v
python src/countdown_smoke.py --out runs/new_cpu_smoke/data --train 128 --dev 16 --test 32
```

Choose a new output directory for each run. The imported `fixtures/smoke_handoff` data is immutable and is only a small CPU example, not the final scientific test set.

Code, configurations, small raw predictions, metrics, manifests and run records belong in Git. Model weights, optimizer checkpoints, environments and credentials do not. Migration instructions will be maintained in `docs/MIGRATION.md`.

## Interpretation limits

Presentation matching is not token matching. P/T/R are coupled at a fixed budget. Canonical arithmetic syntax is an operational proxy for structure, not proof of distinct human strategies. All empirical claims must link to actual run records; negative and failed runs are retained.

## Bounded engineering run

Use Python 3.12 and a compatible PyTorch 2.8.0+cu128 base image; `bash scripts/bootstrap.sh` checks the base and creates a project overlay. See `reports/environment_4090.json` for the actual image package inventory. Set `HF_HOME` to a persistent model cache outside Git.

```bash
python scripts/download_model.py --role debug
python scripts/verify_model.py --role debug --out reports/new_model_verification.json
python -m scripts.audit_tokens --data runs/cpu_reproduction_20260905/data --out reports/new_token_audit.json
# Commit code first. Use a new run ID and the same budget ledger for every job.
python scripts/run_bounded.py --run-id overfit_example --max-seconds 1800 -- \
  python -m src.experiment --config configs/overfit_debug.json --out runs/overfit_example
```

The run wrapper requires GNU `timeout`, reserves runtime persistently, forbids concurrent or unresolved jobs, and caps cumulative process time at the approved 7200 seconds. Instance idle billing is separate. Weights are excluded from Git; the initial engineering checkpoint saves model weights only and cannot resume optimizer state.
