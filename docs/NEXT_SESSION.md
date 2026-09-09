# Morning handoff — CPU work complete, finite A800 pair ready

## Execution update —2026-09-09

The owner has now restarted the A800 and explicitly authorized the frozen new
pair. [E010](experiments/E010_absent_boundary_seed31.md) records the execution
envelope. SSH works, current Git is restored, and the original4716-second
ledger is unchanged. All294 Linux tests and pinned-model/data/queue checks passed and were published
at `9217685`. The queue launched at18:24:48 UTC from that clean commit.
Do not launch it again; inspect its existing run directories and private ledger. The historical wait for
owner launch instruction is satisfied. Preserve the recovery/shutdown gates.
Task-mode recommendation: Max for this frozen execution, verification and
recovery workflow; reassess for a later substantial scientific redesign.

## Current state,2026-09-09 UTC

The owner's request was to resolve avoidable matching selection and prepare
training while the server is off. C011/C012 and the optimized C013 CPU searches
are complete. The new dataset, bounded queue, independent CPU checks and future
output auditor are ready. **No new GPU run has started.** The last authenticated
provider check confirmed shutdown at07:37 UTC; the C009 backstop is paused.
This session did not connect to or start a server.

Read [the full research analysis](../reports/MATCHING_COMPLETION_AND_TRAINING_20260909.md),
[training plan](ABSENT_BOUNDARY_TRAINING.md) and [current status](../reports/STATUS.md).
The research journal records each idea, failure, design, result and interpretation.
Final [release verification](../reports/matching_completion_release_verification_20260909.json)
records292 passing tests out of294 (two GNU-timeout checks require Linux) and a
successful clean-Git-checkout data/queue recovery test with the real tokenizer.
Do not replay completed seed17/23 queues. A cloned server's old commit may be
`fc96885c`; fetch current main or synchronize a verified current Git bundle.
Starting or cloning a server must not automatically launch any experiment.
Keep full Git history available: historical provenance checks need the recorded
source snapshots; a shallow clone must fetch the required history first.

## Fixed next pair and immutable inputs

| Item | Frozen value |
|---|---|
| Dataset | `runs/absent_boundary_seed31_20260909_r1` |
| Data manifest SHA256 | `cd9a72d187dbb18f2b75b743ccc0cf85c94951ee574c07e55ed8ddf1f4a1ab97` |
| Preparation source | `d537c31cf6c5498e6ca7d8e8045b976b0fadb1f9` |
| Queue | `configs/absent_boundary_seed31/queue.json` |
| New run IDs | `absent_boundary_paths_seed31_r1`, `absent_boundary_gcm_seed31_r1` |
| Conditions | identity-absent Paths/GCM only; Repeat/Surface files are compatibility audits |
| Training |128 questions,32 blocks,8 complete cycles,1024 updates,batch4,microbatch2 |
| Exposure |4096 presentations; each question32 times; Paths four paths eight times each; GCM one path32 times |
| Tokens per arm |277760 EOS-inclusive supervised;482848 nonpadding processed;3734 padding |
| Seeds |selection/assignment/order/training31; evaluation17 |
| Model |Qwen2.5-1.5B base; pinned revision `8faed761d45a263340a0528343f099c05c9a4323` |
| Recipe |FP32 AdamW parameters, BF16 autocast,LR5e-5,WD0.01,clip1; limits384 |
| Development |Original64 matched and64 broader references, byte-identical |
| Holdout |2048 reserved raw groups remain unsolved/unevaluated |

[Independent CPU verification](../reports/absent_boundary_cpu_verification_20260909.json)
passed all512 references, seed selection/schedule, per-question exposure and
per-update tokens, padding, structures and operator histograms. The primary
endpoint remains matched greedy final-expression correctness; always retain
broader development, full traces and sampled pass@1/2/4 as separately labeled
outcomes. No validation-based early stopping or checkpoint selection is added.

The selected population remains restricted:33/128 large targets,55/128 targets
equal an input, and all7 preview-template questions remain. Numerical magnitude
and some per-question depth/negative exposure differ despite matched batch
structure totals. These residuals are recorded, not tuned away. This pair is
an exploratory boundary allocation test, not a causal identity-removal test,
a replication on the original256 questions, or an ICLR-ready main result.

## Startup and migration gates

The owner will start or provide an A800. Until then do local CPU/documentation
work only. On the actual server, first establish the correct instance and
inspect GPU/process/disk state. Fetch the published commit and verify clean
tracked files. Never overwrite a unique checkpoint or run record on a clone.

Restore the original private ledger through the existing private transfer
channel. Its latest verified SHA256 is
`995d1ec3d484671bb391f3997640712201d6341b97a00e1feafed5378b22633e`:
4716/7200 charged,2484 remaining,13 receipts,zero reservations. **Never initialize
a fresh ledger or replay old run IDs.** A clone is not a new budget.

Keep the measured Python3.12/PyTorch2.8.0+cu128 environment and pinned model
bytes. `requirements.txt` keeps the GPU recipe pins; `requirements-diagnostics.txt`
adds SciPy1.18.0 for CPU packing/tests. The CPU search used NumPy2.5.3/NetworkX3.6.1;
the GPU environment retains its original NumPy2.3.2/NetworkX3.5 pins. Selection is
already frozen and need not be re-solved on the GPU server. Run the full Linux
suite, including the two GNU-timeout budget integration checks skipped on macOS.

Require18GiB free **after** environment and base-model setup. The50GB data disk
only needs the base model, runtime, current source/data and two new checkpoints.
Do not copy old scientific weights or CPU inventory/key streams onto it. Prior
weights are already independently backed up. If verified duplicates cannot
provide enough space, report the shortfall and request expansion before training.

## Commands after environment/model/ledger verification

Run from the repository root in the verified training environment. Set
`TOKENIZER_DIR` to the verified local pinned model snapshot. This variable is
not a download location or an invitation to change revisions. Keep verification
output directories outside tracked files, and use fresh names for every check.

```bash
python -m unittest discover -s tests -v
python -m scripts.verify_absent_boundary \
  --data runs/absent_boundary_seed31_20260909_r1 \
  --tokenizer-dir "$TOKENIZER_DIR" \
  --out .local/new_server_absent_cpu_check.json
python -m scripts.run_pilot_queue \
  --queue configs/absent_boundary_seed31/queue.json \
  --phase comparison --ledger .local/resource_ledger.json
```

The queue defaults to inspection. Expect4716 used,2484 remaining and2130 seconds
required for the complete pair (1050+15 for each arm). Recheck the historical
calibration's completed metrics/config/receipt; execution enforces this gate.
New jobs start from the pinned base, never from a previous pilot checkpoint.
Only after the owner's later launch instruction and all gates pass:

```bash
python -m scripts.run_pilot_queue \
  --queue configs/absent_boundary_seed31/queue.json \
  --phase comparison --ledger .local/resource_ledger.json --execute
```

Use the existing bounded wrapper and keep the process/log alive independently
of an interactive SSH connection. Do not auto-retry, shorten an arm, run a third
model or rerun calibration under this queue. Failure stops the phase and retains
the reservation/receipt for reconciliation. The2130-second reservation is not
a charge or a promise that both jobs will finish under every server condition.

## Completion and recovery

After both runs finish, run the new data-aware audit, not the historical
seed23-specific audit:

```bash
python -m scripts.audit_absent_boundary_outputs \
  --queue configs/absent_boundary_seed31/queue.json \
  --out reports/absent_boundary_seed31_after_gpu_audit_r1
python -m scripts.report_pilot \
  --queue configs/absent_boundary_seed31/queue.json \
  --out reports/absent_boundary_seed31_after_gpu_r1
```

The complete-pair audit requires all800 predictions, matching commits/recipes,
full new277760-token dose, raw generations, original development identities,
final-expression rescoring and complete displayed traces. It refuses missing
outputs. Preserve both favorable and adverse endpoints; do not read holdout.

Transfer compact run records, logs and the latest ledger locally, verify all
receipts, and publish code/results/analysis to GitHub. Independently back up both
new checkpoints with SHA256 verification before declaring the server disposable.
Weights remain outside Git and do not include optimizer/RNG state for exact
mid-run resume. Carry out normal shutdown after the owner's authorized finite
round and recovery checks; confirm actual provider stopped state and pause any
backstop. Never delete/release the instance as a substitute for shutdown.

## CPU search recovery sources

C010's600-second failed attempt is retained. C013 completely covers the same
48,429,084 grid in4.833 seconds, finding1,019,005 keys/63 questions/15 blocks.
C011 demonstrates both length and structure selection; C012 independently
finds33 absence-only blocks. These results were not chosen by model outcomes.

Git contains all materialized training bytes, configs, manifests, compact raw
records and lossless public CPU output archives. C013 stores every key in six
base64 parts with exact compressed/stream hashes; catalog and support-group
archives restore the original JSON. C011/C012 verifiers support their public
archives when original JSON is absent. Original tokenized/ordered solution
streams stay private with public hashes and reproducible source snapshots.
A normal training launch requires none of those CPU streams.

All six previous scientific checkpoints and earlier engineering backups are
independently retained locally outside Git. See [ARTIFACTS](../reports/ARTIFACTS.md),
[MIGRATION](MIGRATION.md) and the historical ledger/checkpoint receipts. Current
connection details, local absolute user paths and credentials never enter Git.
