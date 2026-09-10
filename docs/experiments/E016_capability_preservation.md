# E016: independent capability-preservation calibration

2026-09-10 UTC. The owner requested the next experiment or offline planning,
with startup notification. Prepare this single diagnostic offline; only an
explicit launch on an owner-started instance executes it. This is the next
development calibration in P005, not a main grid or final-test evaluation.

## Fixed question and endpoints

Does the original pinned Qwen2.5-1.5B base demonstrate measurable capability
under our serialization, and does the passing E015 overfit endpoint retain it?
C019 revealed substantial E013 degradation masked by an overly restrictive
historical score. E015 has no development results yet. This experiment measures
two fixed endpoints; it does not continue training or isolate an LR mechanism.

- One run: `gsm8k_capability_e016_r1`, base first and E015 second; 64 prompts each.
- C017 GSM8K development ranks **17–80**, after the original 16 observed parents.
  All 64 groups are distinct from those 16, the acquired/fresh training draws,
  other training reserves and official-test groups under the frozen C017 rule.
  Selection ignores answer success and solution availability. All 64 remain in
  the denominator. The remaining 432 development parents stay reserved.
- Original pinned base; E015's exact 12-file weights manifest. No silent model,
  Instruct, tokenizer, precision, checkpoint or prompt substitution.
- Same `Problem: {prompt}\nSolution:\n` prompt, FP32 weights/BF16 autocast,
  SDPA, TF32 off, greedy batch 8, one beam, 768 generated-token maximum,
  context 1024, native EOS only, no extra inference stop strings. Seed 17 is
  reset before each model load; this does not promise bitwise GPU determinism.
- No SFT, optimizer, reference-conditioned logits, intermediate checkpoint
  selection, sampling, teacher, test decode, new weight file or automatic retry.

These are previously undecoded questions in this project; unknown exposure
during base-model pretraining is not ruled out.

The public CPU release stores original prompt/reference hashes, complete
serialized prompts and token IDs before any model generation. Only the already
cached original **training** JSONL is opened for text; official tests are not
opened anew. No references enter model prompts. A context failure blocks all
preparation rather than dropping that question.

## Measurements and prospective decision rules

Keep the original strict score in every raw generation and separately record
C019's frozen `marked_answer_v1`. Primary screening endpoint: marked numeric
answer equals the gold, actual EOS, no truncation, no generated new-problem
continuation. Report all 64 parents, parsed/unresolved/conflicting outputs,
answer-only correctness, EOS and truncation as separate counts. Marked-answer
agreement does not validate intermediate reasoning; extraction is gold-blind.
Do not alter the extractor or prompt after seeing these 64 answers.

1. **Base non-floor screen:** at least 8/64 clean correct, at least 48/64 parsed,
   and at most 8/64 truncated. Failure separates format problems from a low
   mathematical endpoint count; no automatic model substitution or prompt sweep.
2. **E015 retention screen:** base passes; E015 meets the same parse/truncation
   and 8-correct minima, retains at least 75% of the base clean-correct count,
   and loses at most eight net correct answers. Also report paired lost and
   gained questions, not just a difference of percentages.
3. These are **operational screens**, not a powered equivalence/noninferiority
   test. At n=64, proportion uncertainty near 50% is roughly ±12 percentage
   points. No generalization, causal LR, reasoning-strategy or scientific-arm
   superiority claim follows from passing. Preserve every result and failure.

Run both fixed endpoints within the one cap even if the first screen fails;
the second is needed to identify the observed difference. A timeout is an
incomplete calibration, not 0/64, and it does not authorize a smaller denominator
or another job. Subsequent scoring/prompt revisions would make this an observed
development set; they must not be presented as fresh confirmation.

## Complete finite budget and shutdown

The unchanged ledger has 19 reconciled receipts, 6686/7200 process seconds used,
514 available. Reserve **470 seconds + 15 guard = 485**, leaving at least 29.
The guard uses the existing ledger hash under lock and refuses a stale ledger,
existing run ID or shortened allowance. Nothing resets historical receipts.

Observed E013 generation was 38.18 seconds for 16 base prompts and 37.11 for 16
tuned prompts. Four times their sum is **301.13 seconds** for 128 prompts, before
model loads, overhead and changed lengths. This is a linear planning proxy,
not a measured E016 duration or confidence bound. The 470-second process cap
allows roughly 56% more time than that proxy. At most 98,304 new tokens; retain
all raw generation/config/profile records. Startup validates the same Linux
runtime, GNU timeout, idle A800 and driver, and rehashes both endpoints.

**Whole GPU rental target: 15 minutes / CNY2.00; planned ceiling: 20 minutes /
CNY2.67**, at the owner's CNY8/hour, before provider rounding or other fees.
Require at least 785 seconds left at admission: 485 guarded process, 120 compact
export and 180 shutdown/slack. Thus staging/preflight must finish within 415
seconds of the evidence-backed startup time. A blocked connection/preflight
ends the window; do not spend the rental debugging. Set a provider stop timer
as a backstop before launch; obtain provider-confirmed shutdown after exporting
compact records and the current ledger. No unique new checkpoint is written.

The inference-only scratch gate is 256 MiB, explicitly different from E015's
12 GiB checkpoint-writing gate; it permits no cleanup. Old checkpoints and the
original base remain intact. E015 independent weights recovery is still pending
and is planned separately in [the recovery plan](../E015_RECOVERY_PLAN.md).
Do not try to transfer 6.19GB on this GPU rental window or delete the instance.
Read-only inference does not itself supply an independent checkpoint backup.

## Conditional next research decision

If base passes and E015 fails, review a single broader SFT calibration with a
fresh base, lower integrated update strength and a development retention
measurement, before adopting its recipe for all three arms. Keep changes and
calibration data-policy selection explicit; no hyperparameter search can
consume final-test data. Partial parameter freezing or a task-matched small
model is a separately reviewed alternative, not an automatic fallback.

If both pass, price a complete Repeat256x1 / Solutions256x4 / Breadth1024x1
comparison and its replication, including all evaluation/startup/preservation.
Keep actual 253/996/1013 selected-pair counts, 524288 supervised tokens and 256
updates per proposed arm. Do not infer equal LR strength, equal runtime or
reasoning diversity from equal token budgets. Full scientific protocol changes
remain subject to the concrete review required by AGENTS.md. E016 automatically
authorizes neither training nor a new process allowance.


## Appended outcome — 2026-09-10 UTC; registration above retained

The single owner-started run completed all128 generations from84e9ea3. Base/E015
clean correct26/64 versus0/64; marked numeric correct39/64 versus0/64; paired
losses26/gains0. The base fails its14/64 truncations against the8/64 maximum,
so both registered screens fail. No base-pass training branch or grid follows.
All42 Linux checks and both raw-token audits pass;235seconds charged,20 receipts
6921used/279left. Compact outputs/current ledger are independently verified and
provider shutdown is confirmed. E015 weights recovery remains incomplete.
No thresholds, original raw scores, prompt or runtime inputs were revised.
[Full result and limits](../../reports/REAL_MATH_E016_RESULTS.md).
