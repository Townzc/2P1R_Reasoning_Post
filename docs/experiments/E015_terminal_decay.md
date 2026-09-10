# E015 — terminal learning-rate decay on the original GSM8K engineering task

Registered 2026-09-10 UTC after the owner's instruction to proceed with P005.
Run ID: `gsm8k_terminal_decay_e015_r1`. Source publication precedes immutable
CPU input preparation; a separate readiness report records release verification.
There is no model result in this registration.

## Hypothesis and fixed comparison

E014 reproduced all32 failed-E013 checkpoint outputs and batch1 repaired none
of eight failures.17/5226 reference targets lose argmax despite low mean NLL.
Test whether ending training with smaller steps improves local reference fit
and free-generation termination at the original dose. This is an optimization
hypothesis, not an established software fault or a finding of the reviewed papers.
Compare the final endpoint with immutable E013; no rerun of E013 is needed.

The only training factor changed is the learning-rate sequence. Steps1–192 use
5e-5; steps193–256 use `5e-5*(1+cos(pi*(step-192)/64))/2`. All256 optimizer calls
remain, but the last has zero LR:255 nonzero-LR steps and summedLR0.011175.
Equal token/update counts do not imply equal integrated learning rate.

| Factor | Frozen value |
|---|---|
| Model | Fresh Qwen/Qwen2.5-1.5B base, revision8faed761d45a263340a0528343f099c05c9a4323; fresh optimizer |
| Training data | Exact original32 E013 references and their order; no parent replacement |
| Dose | 256 updates,167232 supervised targets,229056 nonpadding processed tokens,32 exposures per row |
| Recipe | Seed17; all FP32 parameters; BF16 autocast; SDPA; TF32off; batch4/microbatch1; AdamW foreachfalse,wd0.01,clip1 |
| Serialization | Original prompt, response-only shifted labels and supervised EOS; context1024; no truncation/packing |
| Measurements | Base32-reference NLL only; final32 train generations and all5226 reference targets/EOS |
| Decoder | Original greedy batch8, max_new_tokens768; no new base/dev/test generation |
| Checkpoint | Final weights/tokenizer only; no optimizer or RNG resume; no intermediate selection |
| Bounds | One360-second process plus15-second guard; unchanged18-receipt ledger |

The inherited configuration contains the historical16 development-row count so
old release validation remains exact; this runner never decodes that split.
All new implementation lives in `analyses/`, preserving the E013-frozen
`src/` and `scripts/` byte set. Historical512-step and terminal-decay proposal
JSON files remain unchanged; `configs/real_math_e015/terminal_decay.json` is the
registered execution configuration.

## Measurements, validation and decision rule

Log actual LR, row indices, target/processed counts, NLL, gradient norm, time
and memory for every completed update. Record all generated token IDs, original
scores and termination; for every reference target record CE, argmax ID/log
probability, target-minus-argmax and signed target-minus-best-other margins.
Reference-conditioned EOS is not a measurement of EOS on generated loops.

The unchanged engineering gate requires complete256-step dose/profile,
at least31/32 correct and terminated train answers, zero truncations and
reference NLL<0.1. The independent auditor reconstructs dose, LR, raw output
scores, reference margins, metrics, checkpoint manifest and process receipt.
A complete failed gate is a learning outcome; an interrupted process is incomplete.
Retain both without an automatic retry, longer cap or512-step fallback.

| Outcome | Next action |
|---|---|
| Complete and gate passes | Preserve results/weights and stop rental; prepare a separately frozen held-out capability/profile check before the three-arm study. |
| Complete and gate fails | Preserve the failure; review P005's task-matched small-student or objective alternatives. No LR/seed/step sweep. |
| Preflight/storage/time gate fails | No model reservation; return to offline work and stop the powered rental. |
| Interrupted/invalid output | Preserve partial artifacts and charge the actual receipt; no same-ID retry or claims of completed dose. |

Passing memorization does not demonstrate generalization, a multiple-solution
effect or a useful scientific scale. Repeat256x1,Solutions256x4,Breadth1024x1
remain the prospective minimum after capability and full-phase budgeting.
Selection/curriculum are conditional explanatory experiments, not queued jobs.
The monetary ceiling now permits planning finite later phases; preserve ledger
history and assign explicit process caps before any later execution.

## Rental, storage and execution handoff

The owner supplied CNY8/hour and a CNY3000 total ceiling. The conservative
power-on plan targets40minutes (~CNY5.33), with45minutes (~CNY6) as a planned
ceiling before unverified rounding/storage charges. Historical billing totals
are unknown. Before launch, require at least2040seconds remaining for375seconds
process/guard,1320seconds export/verification and345seconds shutdown/slack.
Use an evidence-sourced power-on timestamp, and label owner notification time
as potentially later than actual startup. Never report billing stopped from
process termination or SSH loss alone.

The last6.29GiB free fails the inherited12GiB gate. Fresh local evidence retains
all12 E013 checkpoint files (6190803414bytes) independently. Reclaim only the
exact, rehashed server duplicate via the allowlisted helper; reject unexpected
files, links, open files, ledger mismatch or overlap with the original base.
Recheck actual free space after staging and reclamation; the predicted margin
is only59.6MiB. Never lower the gate or expand deletion to unique files.

After owner startup, synchronize published source and verify the bundle, original
base/tokenizer, exact private ledger, idle A80080GB, driver580.126.09 and pinned
runtime. Run the complete focused Linux suite, including GNU-timeout integration.
Use the existing server runtime and these repository-relative commands:

```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
E015_TOKENIZER=.local/hf-cache/hub/models--Qwen--Qwen2.5-1.5B/snapshots/8faed761d45a263340a0528343f099c05c9a4323
E015_LEDGER=.local/resource_ledger.json
# Set E015_POWER_ON from actual recorded startup evidence, with timezone.
# Set E015_TIME_SOURCE to provider_timestamp or owner_start_notification.
python -m analyses.e015 inspect --tokenizer-dir "$E015_TOKENIZER" --ledger "$E015_LEDGER"
# Only if the verified old duplicate must be reclaimed to meet12GiB:
python -c 'import json,sys; from pathlib import Path; from analyses.e015_storage import reclaim_duplicate; print(json.dumps(reclaim_duplicate(Path(sys.argv[1]),Path(sys.argv[2]),execute=False),indent=2))' "$E015_TOKENIZER" "$E015_LEDGER" > .local/e015_cleanup_preview.json
# Export the preview receipt to local recovery storage before the next command.
python -m analyses.e015 reclaim --execute --tokenizer-dir "$E015_TOKENIZER" --ledger "$E015_LEDGER" --power-on-at-utc "$E015_POWER_ON" --power-on-time-source "$E015_TIME_SOURCE"
python -m analyses.e015 launch --execute --tokenizer-dir "$E015_TOKENIZER" --ledger "$E015_LEDGER" --power-on-at-utc "$E015_POWER_ON" --power-on-time-source "$E015_TIME_SOURCE"
python -m analyses.e015_audit --tokenizer-dir "$E015_TOKENIZER" --out runs/gsm8k_terminal_decay_e015_r1/record_verification.json
```

Default inspect/unconfirmed launch is CPU-only. An executed launch checks the
whole rental window before server preflight and again before its bounded worker.
There is no automatic next job. Export compact records and the updated ledger,
then stream/hash all12 new weights to an unused local directory using the
1320-second whole-transfer deadline. Preserve completed files and partials on
failure; never call a partial export a verified backup. Shut down retaining the
volume if transfer cannot finish; no instance disposal with unique weights.
An optional console-verified no-card export route is described in
[storage/rental instructions](../E015_STORAGE_AND_RENTAL.md).

Completed compact artifacts: planned/actual budgets, train history, throughput,
base reference NLL, final train generations, reference-token records, metrics,
checkpoint manifest and phase timings, plus run manifest and wrapper receipt.
The independent audit records checkpoint hashes separately from independent
backup verification. Preserve source/release hashes and actual power-on/stop
observations in the execution closeout. No current provider state is inferred
from this offline preparation.

## Execution outcome — 2026-09-10 UTC

Sourcee508321 completed one219-second charged job on the owner-supplied clone.
All112 Linux tests and server/local record audits pass.32/32 train answers are
correct/terminated, no truncations,31 exact references, NLL0.001106 and1/5226
reference argmax miss. The original gate passes; no new dev/test measurement.
The early training trajectory differs from E013 before decay (gradient step3,
NLL step4), so causal attribution to the terminal schedule alone is limited.

All19 receipts reconcile to6686used/514left. Compact outputs/current ledger are
independent. The complete12-file checkpoint passed server hashes and remains
on the stopped volume; independent export is incomplete after poor transfer
progress. Provider UI confirms normal shutdown, timer cancelled. No retry,
512-step fallback, scientific grid or server restart. See
[the full result](../../reports/REAL_MATH_E015_RESULTS.md).
