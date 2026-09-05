# 2P1R Reasoning Post-Training

**Problems, Paths, or Repeats?** A research workbench for controlled reasoning supervised fine-tuning (SFT).

The central question is whether within-problem structural path diversity helps beyond global strategy coverage, exact repetition, and surface diversity under matched supervision and optimizer-update budgets. Arithmetic is the first task; graph/relational reasoning and a second model family are planned boundary-condition checks. RL is outside the current scope.

## Current status

The imported CPU arithmetic generator and verifier are available. No model result is claimed by this initial commit. See [reports/STATUS.md](reports/STATUS.md) for verified progress and [docs/PROTOCOL.md](docs/PROTOCOL.md) for the current protocol and unresolved decisions.

```bash
python -m unittest discover -s tests -v
python src/countdown_smoke.py --out runs/new_cpu_smoke/data --train 128 --dev 16 --test 32
```

Choose a new output directory for each run. The imported `fixtures/smoke_handoff` data is immutable and is only a small CPU example, not the final scientific test set.

Code, configurations, small raw predictions, metrics, manifests and run records belong in Git. Model weights, optimizer checkpoints, environments and credentials do not. Migration instructions will be maintained in `docs/MIGRATION.md`.

## Interpretation limits

Presentation matching is not token matching. P/T/R are coupled at a fixed budget. Canonical arithmetic syntax is an operational proxy for structure, not proof of distinct human strategies. All empirical claims must link to actual run records; negative and failed runs are retained.
