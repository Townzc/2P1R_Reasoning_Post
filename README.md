# 2P1R Reasoning Post-Training

**Problems, Paths, or Repeats?** A research workbench for controlled reasoning supervised fine-tuning (SFT).

The central question is whether within-problem structural path diversity helps beyond global strategy coverage, exact repetition, and surface diversity under matched supervision and optimizer-update budgets. Arithmetic is the first task; graph/relational reasoning and a second model family are planned boundary-condition checks. RL is outside the current scope.

## Current status

The intended 1.5B base model passed the 32-example engineering gate on A800 (32/32 after 500 updates), using the FP32 AdamW recipe that exceeded 4090 memory. Development remains 0/16 greedy and 0/64 sampled. A CPU search found 256 candidate problems with exact token and Within-Paths/GCM structural matching; final data/control design remains open. See [reports/STATUS.md](reports/STATUS.md), [reports/A800_SESSION.md](reports/A800_SESSION.md) and [docs/PROTOCOL.md](docs/PROTOCOL.md). No scientific treatment result is claimed.

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
