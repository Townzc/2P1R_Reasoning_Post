# E013 — fixed GSM8K overfit and runtime profile

Registered 2026-09-10 UTC, before CPU materialization or model execution.
The owner requested the next experiment following C017. This authorizes one
finite engineering run using the existing allowance. E012 remains paused;
C017's four-arm scientific schedules still require a measured complete-phase
budget and review. Max was recommended for implementation and auditing; no
settings change is claimed.

## Frozen inputs and training

Use the exact 32 entries in C017's `engineering_32_rows.jsonl`: first available
parents by frozen GSM8K audit rank, one first accepted released response each.
This availability selection is appropriate for an engineering memorization
check; it is not a new scientific pool. Retain original wording and native
numeric answers. Use the first 16 original-train parents by frozen development
rank, independently of answers or model outputs. Validate parent groups,
candidate locations, hashes and C017 token counts. Official tests and fresh
reserves never enter model inputs. Public compact data carry source attribution.

Pinned Qwen/Qwen2.5-1.5B base revision
`8faed761d45a263340a0528343f099c05c9a4323`, full FP32 trainable parameters,
BF16 CUDA autocast, SDPA, nonreentrant gradient checkpointing, TF32 disabled,
AdamW (`foreach=False`), lr 5e-5, weight decay .01, clipping 1.0. No scheduler,
LoRA, optimizer-precision change, fine-tuned initialization or teacher call.
Seed 17, 256 updates, four responses per update, microbatch one. Shuffle all
32 rows each epoch; each appears exactly 32 times. No packing or truncation.
Exact serialization is `Problem: {prompt}\nSolution:\n{response}`. Mask prompt
and padding, supervise terminal EOS, and divide accumulated shifted response
loss by total response tokens in the update. Planned totals are 167,232
supervised tokens and 229,056 processed nonpadding tokens, with zero padding.

Context cap 1024; greedy generation uses 768 new tokens, batch eight, one beam,
explicit original EOS/pad IDs, and no chat template. Check prompt plus allowance
fits the context before loading weights. Baseline: 16 development generations
and train reference NLL. Final only: all 32 train and 16 development generations,
plus train reference NLL. No sampled pass@k or intermediate checkpoint selection.
There are 64 generated sequences total. Record raw generated IDs and text,
EOS, truncation, exact reference match when available, timings and memory.

## Scoring and gate

The last explicit `\\boxed{...}`, `\\fbox{...}` or `####` marker wins; only an
exact scalar numeric literal/fraction is scored. Do not extract a number from
unmarked working, discard a later bad marker, join separated numeric tokens,
remove units or execute expressions. Embedded special tokens fail parsing.
Conservative format failures remain in denominators. This is numeric endpoint
agreement, not verification of the intermediate reasoning. The prompt contains
no new formatting instruction, so baseline format compliance is reported.

Pass requires the complete 256-update dose, a complete profile, at least 31/32
correct train answers ending in EOS, zero truncated train outputs, and finite
train reference NLL < .1. Profile updates 9–72 exclude eight warmup updates.
Development results are descriptive at n=16 and never select a checkpoint or
trigger extra steps. Preserve every failure/timeout; no automatic retry. A
completed process with a failed gate remains a failed engineering gate.

## Runtime and recovery

Only one idle A800 80GB with the recorded Python3.12/PyTorch2.8.0+cu128 recipe.
Hash every original model/tokenizer file and check exact dependency versions.
Existing cumulative ledger: 16 receipts, 5971/7200 seconds used, 1229 remaining,
zero reservations; SHA256
`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
Reserve the full 900-second process cap plus 15-second guard (915 maximum;
314 seconds remain unreserved). Actual elapsed process time is charged.
The cap is a safety bound, not a prediction that completion is guaranteed.

The launcher inspects by default. Explicit execution rechecks the ledger under
the wrapper lock, uses GNU timeout, refuses shortening, and creates only
`runs/gsm8k_overfit_e013_r1`. A new instance inherits the same ledger and needs
verified source, original base cache and compact data. No automatic rental,
instance startup, other queue or extra budget. Preserve model weights and
manifest off-instance before considering it disposable; checkpoints are not
an exact optimizer/RNG resume and never enter Git.

Training-only extrapolations to the four C017 arms use both supervised-token
and processed-token ratios. They are proxies, not complete-phase bounds or
confidence intervals. A scientific phase must add its frozen development
evaluation, model loads, checkpointing, verification and watchdog margins.
No large grid is launched from a good overfit score.

## Commands

Source must be published and synchronized before CPU preparation. Set
`E013_SNAPSHOT` to the verified original base snapshot. Private cached sources
need not be uploaded to the GPU once compact inputs are published.

```sh
python -m scripts.prepare_real_math_engineering --parents .local/real_math_c017_parents_r2/problem_records.jsonl --candidates .local/real_math_c017_solutions_r2/raw_candidates.jsonl --tokenizer-dir "$E013_SNAPSHOT"
python -m unittest tests.test_real_math_engineering tests.test_real_math_audit tests.test_sft_data tests.test_relation_engineering.DoseTests tests.test_relation_engineering.LedgerTests tests.test_budget_guard -v
python -m scripts.run_real_math_engineering --tokenizer-dir "$E013_SNAPSHOT"
python -m scripts.run_real_math_engineering --tokenizer-dir "$E013_SNAPSHOT" --execute
python -m scripts.audit_real_math_engineering_outputs --tokenizer-dir "$E013_SNAPSHOT" --out runs/gsm8k_overfit_e013_r1/record_verification.json
```

The two GNU-timeout integration tests are mandatory on Linux before launch;
they may be skipped on macOS without GNU timeout. CPU release verification
also independently decodes raw tokenizer offsets to count labels/EOS, checks
all 32 candidate source rows and 16 original development rows, and tests
tampered identities/splits/answers/schedules. Inspect-only commands allocate no
GPU process budget. Publish source first, then immutable input/release hashes,
then preflight/run/verification receipts and the current handoff.
