# SFT allocation midpoint preparation

See [P007](../../docs/experiments/P007_midpoint_allocation_plan.md) for the proposed scientific comparisons and resource envelope, and [readiness](../../reports/sft_allocation_midpoint_20261011/READINESS.md) for completed checks.

Current implementation:

- `guard.py`: CPU-only immutable admission/reconciliation; no dispatch and no monetary guarantee beyond correctly supplied reservations.
- `modal_preflight.py`: finite CPU-only contest between two writer attempts, one persisted fixture, independent read and hash verification. There are **no GPU/model functions** in this entry point. It reserves$2 within the$20 engineering stage, uses Volume v1, and requires source published on the assigned branch.
- `scripts/prepare_midpoint_inventory.py`: reconstructs the existing pinned bank and all eight schedules without replacing missing answers or rewriting old records.

The generic training/checkpoint harness and real-GPU recovery profile are not complete. Old E013/E018/Q2 launchers are not substitutes. Do not interpret a CPU fixture as a verified model checkpoint.

The CPU cloud check needs a previously saved campaign JSON with an absolute epoch deadline less than seven days after creation, `total_cap_cents:200`, `stage_caps_cents:{"cpu_preflight":200}`, and two slots `writer`/`reader`, each `{ "stage":"cpu_preflight", "reserved_cents":100 }`. Choose a new immutable campaign ID once, a window with at least240 seconds left, and a new local receipt directory. Cloud claims are never released for automatic replay.

```sh
modal run experiments/sft_allocation_midpoint/modal_preflight.py \
  --plan-json PATH_TO_FIXED_PRIVATE_PLAN \
  --receipt-dir NEW_PRIVATE_RECEIPT_DIRECTORY
```

The writer race and reader use at most three small CPU invocations,120-second function/startup limits, one CPU/1GiB limits, single-use containers and no background deployment. Provider-startup/retry billing still differs from the run guard's application clock; the$2 reserved amount is intentionally conservative and not an invoice. After the command exits, inspect provider app/container state and retain compact outputs. Authentication stays in the SDK's private configuration, never in the image or repository.
