# 2P1R Reasoning Post-Training

**Problems, Paths, or Repeats?** A research workbench for controlled reasoning supervised fine-tuning (SFT).

The central question is whether within-problem structural path diversity helps beyond global strategy coverage, exact repetition, and surface diversity under matched supervision and optimizer-update budgets. Arithmetic is the first task; graph/relational reasoning and a second model family are planned boundary-condition checks. RL is outside the current scope.

## Current status

The owner has now supplied an A800 for the fixed pair. All 96 Linux tests,
model/data checks and the cumulative-ledger check passed. Verified duplicate
remote checkpoints were removed, leaving 41.16 GiB free without expansion.
The [research journal](docs/RESEARCH_JOURNAL.md) separately records motivations,
designs, evidence, failed attempts and interpretation. The [seed23 entry](docs/experiments/E009_seed23_paired_replication.md)
is recorded before its model outcomes; the original CPU preparation follows.

**2026-09-09 UTC:** The seed23 Paths/GCM replication is prepared and CPU-verified,
with the same problems, exact token/update dose and fixed evaluation seed17.
The two-job phase reserves 2130 of the remaining 3488 process-seconds; no GPU
job has started. See the [executable proposal](docs/PILOT_REPLICATION_PROPOSAL.md)
and [next-session handoff](docs/NEXT_SESSION.md).

Independent [trace](reports/pilot_v1_trace_audit_20260909/FINDINGS.md) and
[structure](reports/pilot_v1_structure_bias_20260909/summary.json) audits expose
incorrect intermediate calculations and restrictive selection. The broad
question also overlaps [recent prior work](reports/ICLR_POSITIONING_20260909.md).
Our [ICLR evidence roadmap](docs/ICLR_EXPERIMENT_ROADMAP.md) therefore requires
a substantive semantic-path intervention and broader replication; another
positive seed on the present slice would not establish novelty.

The approved seed17 four-arm pilot is complete. Matched-dev greedy
correctness is Repeat 14/64, Surface 12/64, Paths 23/64 and GCM 18/64;
broader-dev scores are 2/64, 0/64, 4/64 and 1/64. All arms used the same
1024 updates and 267456 supervised response tokens. This is one paired seed
on restricted development sets, not a general treatment-effect claim.
The cumulative budget is 3712/7200 process-seconds used, 3488 remaining.
See [results](reports/PILOT_V1_RESULTS.md), [status](reports/STATUS.md) and
[artifact recovery](reports/ARTIFACTS.md). No further GPU job is scheduled.

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
