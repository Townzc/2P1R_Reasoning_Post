# September11 supplement — E017 execution source and sprint decisions

Read the [ICLR next-run supplement](tracks/iclr_2027/NEXT_RUN_HANDOFF.md) before
using the unchanged E017 commands below. Its frozen launcher requires
`HEAD == origin/main`; a research branch with new planning documents must not
be substituted or relabeled as main. The existing published execution snapshot
is `73170a459e9fed2c5fdea6a9afb40b4b80837bb2`. Resolve source routing offline and
reuse the verified release. No new experiment check or repeated local test suite
is required merely because research proceeds on separate branches.

E017 is still prepared, not run, and already authorized after owner startup.
The [sprint plan](tracks/iclr_2027/SPRINT_PLAN.md) and
[next-phase packet](tracks/iclr_2027/NEXT_PHASE_REVIEW.md) add no automatic
training, reserved-data access or budget. Historical ledger:20 receipts,
6,921 used/279 remaining,zero reservations. E015 full weights recovery remains
incomplete. No server/model action or provider-state recheck occurred here.

# Next session — E017 release ready; one owner-started A800 window

Read [readiness](../reports/REAL_MATH_E017_READY.md) and
[E017 registration](experiments/E017_task_completion_calibration.md).
The user accepted the next P006 step and requested notification before startup.
**Notify the owner that the existing A800 is now needed.** There has been no
server contact or new model run in preparation; the last verified provider
state remains off. Only E017 is ready, not E018 training or the scientific grid.

Run `gsm8k_stop_e017_r1`: original pinned base, exactly 64 previously observed
E016 development parents, ranks 17–80, same prompts and generation configuration.
Add per-row boundary stopping, retain trigger tokens, and record subsequent
batch padding separately from actual EOS. No E015 weights load, training,
teacher call, new checkpoint, prompt sweep or final-test evaluation.

Source `b365bd8` and input release `410ee3e` are published. Release SHA256:
`daeb946c7e3d01afe54552224770f3429129ab05022adeb76138222b87ce56af`.
62 CPU tests pass; two GNU-timeout integrations await Linux. Independent checks
reconstruct all 64 input streams and 20 ledger receipts; 160 saved outputs
exercise 8,064 incremental stop calls matching the C020 oracle. This is recorded
replay, not new GPU accuracy. Preserve old E016 clean26/64 versus0/64 and both
failed gates; keep all 432 reserved development parents untouched.

## Startup and admission

Whole-rental target 12 minutes/CNY1.60, cap 15 minutes/CNY2 at CNY8/hour. Set a
provider shutdown backstop before the model job. Record actual power-on time
when available, or label the owner startup notification as a proxy. Require
555 seconds remaining: 255 guarded process + 120 compact export + 180 shutdown.
No launch after 345 elapsed seconds; failed preflight ends the window promptly.
Only the exact original model/software and one idle A80080GB are allowed. Verify
256MiB scratch space; there is no cleanup or full-weight transfer in this run.

The current ledger has **20 full receipts, 6,921 used / 279 left, zero reservations**,
SHA256 `c33623087b752f0bbc82a32bb90ac8f11a489fc910b2ebdaacb57000c0893106`.
Restore this exact state if a clone is older; never reset it or restore the
19-receipt history as current. E017 reserves at most 240+15=255, leaving at least
24. No additional phase allowance has been recorded. Future E018 requires its
own reviewed training release and explicit additive accounting, preserving all
historical receipts and the overall CNY3,000 financial ceiling.

The last server source is `84e9ea35fc54a0d94e70d4efca74b5f15783091b`.
A clean checkout seeded with only that history successfully imports the E017
release bundle. The current final transfer bundle and publication verification
are private `.local/e017_ready.bundle` and
`.local/e017_final_publication_verification.json`. Import the final published
commit; require `HEAD == origin/main`, a clean tracked checkout, and all release
inputs tracked. Preserve remote unique outputs while synchronizing.
The private `.local/e015_connection.json` holds existing connection details;
never publish its credentials, endpoints or instance identifiers.

Use the verified training interpreter and pinned original model snapshot. After
all 64 focused checks pass on Linux, run the fixed commands below. Variables
stand for paths/timestamps verified in that session, never guessed values.

```sh
python -m unittest tests.test_e017 tests.test_completion_contract tests.test_gsm8k_answer_audit tests.test_e016 tests.test_e014 tests.test_real_math_engineering tests.test_budget_guard -v
python -m analyses.e017 inspect --tokenizer-dir "$E017_SNAPSHOT" --ledger .local/resource_ledger.json
python -m analyses.e017 launch --execute --tokenizer-dir "$E017_SNAPSHOT" --ledger .local/resource_ledger.json --power-on-at-utc "$E017_POWER_ON_UTC" --power-on-time-source owner_start_notification
python -m analyses.e017 audit --tokenizer-dir "$E017_SNAPSHOT" --out .local/e017_server_record_verification.json
```

Use `provider_timestamp` if the power-on timestamp came from the provider.
Default inspection and launch without `--execute` perform no server/model action.
The run audits its output before completion; the post-run audit also checks the
completed receipt. Independently export all compact records/current ledger,
verify hashes and provider shutdown, then repeat the CPU audit and publish
locally. Preserve failures; never retry or chain E018 in the same rental.
No task accuracy or GPU runtime has yet been measured for this implementation.

## Unique checkpoint recovery remains separate

E015's complete 12-file/6.19GB checkpoint remains uniquely on the retained,
last-confirmed stopped volume. The independent copy is partial. Do not release
or delete the instance; follow the [no-card recovery plan](E015_RECOVERY_PLAN.md)
before its verified retention deadline. E017 does not require those weights and
must not spend its GPU window on a full transfer. No recovery or provider-state
recheck occurred during this offline preparation.

# Historical E016 closeout — retained evidence and weights-recovery obligation

Read [E016 results](../reports/REAL_MATH_E016_RESULTS.md). The single authorized
run completed from84e9ea35fc54a0d94e70d4efca74b5f15783091b. All128 generation
records and42 Linux checks pass; server/local raw-token audit reports agree
byte for byte. The registered base/E015 clean-correct counts are26/64 versus0/64,
with26 paired losses/no gains. Base marked-answer correctness is39/64, but14
truncations exceed the8/64 limit. **Both registered screens fail.** The base-pass
conditional training branch was not reached. E015 is62/64 parseable yet0 correct.

Provider normal shutdown was confirmed by18:41:10UTC and the temporary timer
was cancelled. Keep the server off. All25 compact/auxiliary files, including13
run files and the latest ledger, were independently exported/verified. No new
weights, training, teacher calls, official-test evaluation, retry or next job.
The notification-to-confirmation span is721seconds (~CNY1.60 atCNY8/hour), not
an exact invoice; actual power-on time and historical billed spend are unknown.

Current private ledger backup: **20 receipts,6921used/279left,zero reservations**.
SHA256 `c33623087b752f0bbc82a32bb90ac8f11a489fc910b2ebdaacb57000c0893106`.
The pre-E01619-receipt backup remains private as history; never restore it as
current or reset receipts. The stopped server already has the current20-entry
ledger and the E016 execution source84e9ea3. Post-shutdown publication is newer;
synchronize published source before any later separately authorized use.
Private connection/closeout details remain under `.local/e015_connection.json`
and `.local/e016_session_r1`; do not publish credentials or endpoint details.

Next useful work is local, with no startup needed yet:

1. Diagnose the base's missing-marker/continuation/truncation behavior from the
   existing80 observed development parents. Prepare one explicit prompt/output
   contract proposal; do not rescore E016 or call these parents fresh again.
2. Prepare a capability-preserving SFT calibration for review, considering lower
   integrated update strength and broader training coverage; partial freezing
   is a separate literature-motivated alternative. Do not execute the old512-step
   fallback or the scientific allocation grid. Preserve the432 reserved dev
   parents and untouched official tests for their registered future roles.
3. Price the complete chosen phase, including preparation, evaluation/export and
   shutdown, before asking for GPU startup. The279 historical process seconds
   are not a permanent monetary ceiling; future allowance must be explicit and
   additive, retaining all20 receipts. CNY3000 remains an overall ceiling.

**E015 independent weights recovery is still open.** E016 rehashed the12 complete
files/6190803414bytes before inference. They remain on the retained stopped
volume; the local five small files and partial shard are not a full backup.
Do not release/delete the instance. Its post-stop UI showed14days23hours58minutes
of retention; recheck the exact deadline before recovery. Follow the separate
[bounded no-card plan](E015_RECOVERY_PLAN.md), not a GPU-window full transfer.
No no-card restart or checkpoint transfer occurred in E016.

Reproduce the frozen raw-token audit with `python -m analyses.e016 audit` and
the original tokenizer. Rebuild paired tables/all20 receipt checks with
`python -m analyses.e016_result_summary --ledger PRIVATE_CURRENT_LEDGER --out-dir NEW_OUTPUT_DIRECTORY`.
Public result verification is in `reports/real_math_e016_execution_r1/`;
raw streams/profiles are in `runs/gsm8k_capability_e016_r1/`. Preserve all frozen
runtime/input bytes and completed outputs. No automatic model job is queued.

# Historical E016 startup handoff — completed, do not replay

Read [E016 readiness](../reports/REAL_MATH_E016_READY.md) and
[the registration](experiments/E016_capability_preservation.md). C019 completed
locally: the post-hoc diagnostic finds 10/16 clean base successes versus E013
0/16; all original strict scores and raw streams remain unchanged. This is
observed development, not a result for E015. Do not scale from memorization.

The next single run is `gsm8k_capability_e016_r1`: original pinned base then
exact E015 checkpoint, the same 64 new development parents (C017 ranks17–80),
128 greedy generations, zero training or checkpoint writes. Scoring and
operational floor/retention gates are frozen. No automatic fallback or grid.
Implementation d27c17c and input release32240fd are public. Release SHA256:
`c95f7c6d48c5aac11b330bab4989d4efe8a231ec1e4c18e3f8b8bbb21a9204ac`.
Independent CPU reconstruction and clean-checkout bundle import pass;40 focused
tests pass,2 GNU-timeout integrations await Linux.432 development parents remain
reserved. No server contact/model call occurred in this preparation.

Notify the owner that the existing A800 is now needed for this diagnostic.
Whole GPU window targets15minutes/CNY2, caps20minutes/CNY2.67 atCNY8/hour.
Set a provider stop backstop; record the power-on time and evidence source.
Admission needs785seconds remaining:485 guarded process,120 compact export,
180 shutdown/slack. A blocked connection/preflight ends the window. No paid
GPU weight-transfer attempt, troubleshooting session or second job.

The current private ledger backup remains19 receipts,6686used/514left,zero
reservations, SHA256
`ad45fa615091d9f47d16b5b80b07aa23313f356b5ab96bdcab4fa74ff60891d0`.
E016 reserves470+15=485 at most. Restore this exact ledger into an older clone;
never reset it. The stopped instance's execution source is e508321. The local
`.local/e016_ready.bundle` is based on that prerequisite; final staging metadata
is `.local/e016_final_publication_verification.json`. Import the final published
commit before launch, set origin/main to the verified published commit, require
a clean tracked tree and verify that the release plus every input file is tracked.
Do not overwrite remote unique outputs while synchronizing source.

Private `.local/e015_connection.json` identifies the existing instance; never
publish credentials or endpoints. Use its existing pinned training interpreter
(the nonlogin default Python is unsuitable), original model snapshot and the
E015 `checkpoint_final` directory. After the two Linux watchdog tests and the
entire focused suite pass, use the frozen CLI below. Arguments here are names
for already verified local server paths/timestamps, not values to guess.

```sh
python -m unittest tests.test_e016 tests.test_gsm8k_answer_audit tests.test_e014 tests.test_real_math_engineering tests.test_budget_guard -v
python -m analyses.e016 inspect --tokenizer-dir "$E016_SNAPSHOT" --ledger .local/resource_ledger.json
python -m analyses.e016 launch --execute --tokenizer-dir "$E016_SNAPSHOT" --checkpoint "$E016_CHECKPOINT" --ledger .local/resource_ledger.json --power-on-at-utc "$E016_POWER_ON_UTC" --power-on-time-source owner_start_notification
python -m analyses.e016 audit --tokenizer-dir "$E016_SNAPSHOT" --out .local/e016_server_record_verification.json
```

Use `provider_timestamp` instead when an actual provider start timestamp is the
recorded source. The launcher checks idle A80080GB/driver580.126.09, pinned
packages, original base hashes, every E015 checkpoint file, current ledger and
whole-rental admission. The256MiB scratch gate writes no checkpoint and permits
no cleanup. Inspect defaults to no execution. Preserve failed/incomplete runs;
no automatic retry. Export all compact records and updated ledger, obtain
provider-confirmed shutdown, then analyze/publish locally. Compare saved raw
streams and original/marked scores on both server and local CPU before claims.

**E015 independent weights backup is still incomplete.** The full12files/6.19GB
remain on the stopped volume; local five small files plus a partial shard are
not a backup. Do not release/delete the instance. E016 only reads these weights.
The separate [no-card recovery plan](E015_RECOVERY_PLAN.md) has a two-hour/CNY0.20
planning cap, two bounded throughput probes and one admitted verified copy.
It is not part of E016's GPU window. Recheck the displayed retention deadline
(approximately2026-09-25UTC); keep recovery open until all12 local hashes pass.

# Historical E015 closeout and startup handoffs

# Next session — E015 complete; server off; weights recovery still open

Read [E015 results](../reports/REAL_MATH_E015_RESULTS.md). The owner-supplied
new clone ran one frozen E015 job frome508321 after all112 Linux tests passed.
The unchanged engineering gate passes:32/32 correct/terminated,zero truncations,
NLL0.001106,31exact references. Server/local output audits verify all32 streams,
5226 targets and256 updates. No dev/test generation or next scientific job.

Important attribution limit: base reference measurements agree exactly, but
training gradient norms diverge from E013 atstep3 and NLL atstep4, before terminal
LR decay. Treat E015 as a successful engineering configuration; do not claim
an isolated causal LR repair, deterministic GPU replay or generalization gain.

**Provider shutdown is confirmed. Keep the server off during local work.**
The complete E015 checkpoint,12files/6190803414bytes, passed server hashes and
remains on that stopped volume. Independent backup is incomplete because the
new transfer route was too slow. The local path
`.local/checkpoint_backups/gsm8k_terminal_decay_e015_r1` has five verified small
files, one partial weight shard and a failure receipt; never treat it as full.
The original E013 independent backup remains complete. Do not release/delete
the new instance before recovery; its displayed retention deadline is about
2026-09-25UTC and must be verified before a later recovery window.

The owner explicitly requested end-of-round shutdown; it was performed via the
provider UI, then the temporary stop timer was cancelled. No CPU/no-card or GPU
restart followed. Private `.local/e015_connection.json` identifies the stopped
instance; do not publish credentials, SSH endpoints or instance identifiers.
The last optional read-only SSH check timed out, so use the completed server
weight audit and provider UI stop evidence, not invented fresh verification.
A separately bounded no-card transfer is the economical next preservation route;
first measure real throughput and avoid another full unbounded copy attempt.

All19 public receipts match the private current ledger: **6686/7200 used,
514remaining,zero reservations**. SHA256:
`ad45fa615091d9f47d16b5b80b07aa23313f356b5ab96bdcab4fa74ff60891d0`.
The pre-E01518-receipt snapshot is preserved. Restore the latest balance into
any older clone; never reset it or replay E015/E014/E013/E012. The server's
execution source remainse508321; post-shutdown result publication is on GitHub,
so synchronize before any future authorized use.

Current money authorization: CNY8/hour, CNY3000 overall ceiling, not a spending
target. Historical spend is unknown. The notification-to-final-check span was
about23minutes (~CNY3.07 at the stated rate), not the exact provider invoice.
Future finite phases may be priced within the ceiling while retaining receipts;
514process seconds is not a permanent financial restriction.

Next research work is local: inspect saved format-limited baseline outputs,
freeze a separate held-out capability/profile check before generation, and price
the complete P005 three-arm minimum only after a non-floor capability gate.
Selection/curriculum or a task-matched small student remain conditional routes.
Do not add a512-step sweep or infer that32-example memorization fixes test-time
reasoning. Full comparison and ledger reports reproduce through
`python -m analyses.e015_result_comparison --tokenizer-dir ... --ledger ... --out-dir ...`
using a fresh output directory. All original runtime sources/inputs remain frozen.

## Historical E015 startup handoff


The owner authorized P005's single terminal-decay repair and supplied CNY8/hour,
CNY3000 overall ceiling. Read [E015 readiness](../reports/REAL_MATH_E015_READY.md),
[registration](experiments/E015_terminal_decay.md) and
[storage/rental instructions](E015_STORAGE_AND_RENTAL.md). Implementation09a00c0
and immutable release73b054b are published. Independent raw-tokenizer checks,
default inspection and fresh-checkout bundle import pass. The112-test CPU suite
has110 passes; two GNU-timeout integrations must pass on Linux before execution.
No server, pretrained model, new process receipt or reservation in this phase.

Notify the owner to start the existing A800 for **only**
`gsm8k_terminal_decay_e015_r1`. Same32 parents,256 updates and original dose,
only terminal LR changes. No dev/test generation,512-step fallback, retry or
model substitution. E012 stays paused and E013/E014 must not repeat.

The conservative whole-rental plan targets40minutes (~CNY5.33), with45minutes
(~CNY6) as planned ceiling. Record power-on time/source; require2040seconds left
for375seconds guarded process,1320seconds export/verification and345seconds
shutdown/slack. The prior export took16.24minutes. Do full analysis/publication
locally after shutdown, and verify provider state before claiming billing stopped.

Preserve the exact18-receipt ledger:6467/7200 used,733remaining,zero reservations;
360+15 fits and leaves at least358. SHA256:
`8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9`.
All12 E013 independent backup files were freshly rehashed locally. Before the
next model reservation, publish/stage code, export a cleanup preview locally,
then reclaim only the exact verified E013 server duplicate if needed. Recheck
actual free space; the predicted12GiB margin is only59.6MiB. Preserve the original
base and unique files. Use an unused new export destination with the whole-copy
deadline; never call partials a backup or dispose of unbacked unique weights.

Final bundle: `.local/e015_ready.bundle`; final verification:
`.local/e015_final_publication_verification.json`. The private transport adapter
`.local/e015_ssh_export.py` passes five local subprocess fixtures. Import its
`make_open_remote` with already supplied authenticated SSH argv and the exact
remote E015 checkpoint path, then pass the opener into public `copy_checkpoint`.
It uses eight concurrent16MiB ranges and a20-second inactivity bound inside the
1320-second whole-export deadline. Do not load connection code at import or
contact the server before owner startup. Use a new local destination beneath
`.local/checkpoint_backups/gsm8k_terminal_decay_e015_r1`. Record progress at least
every20seconds; preserve failures without retry. Private transport preparation
is under`.local/`. The public
fresh-checkout verification identifies the release bundle; refresh/import the
final handoff bundle before use. Verify driver580.126.09, idle A80080GB, original
snapshot and pinned runtime. Exact Linux suite:

```sh
python -m unittest tests.test_e015 tests.test_e015_core tests.test_e015_audit \
  tests.test_e015_storage tests.test_e015_export tests.test_e014 \
  tests.test_real_math_engineering tests.test_sft_data \
  tests.test_relation_engineering.ScoringTests tests.test_relation_engineering.DoseTests \
  tests.test_relation_engineering.LedgerTests tests.test_relation_engineering.OutputAuditTests \
  tests.test_budget_guard -v
```

The financial ceiling is known; historical spend and remaining money are not.
Later finite phases can be priced within it while retaining historical process
receipts. A usable recipe and separately frozen held-out capability check still
precede scientific scale; no automatic grid follows E015.

## Historical P005 planning handoff


No server is needed for the current work. The owner corrected billing: the
whole powered-on window is charged, including CPU work and idle time. Read
[the rental workflow](RENTAL_WALL_CLOCK.md),
[P005](experiments/P005_literature_guided_next_phase.md) and
[the eleven-paper review](../reports/LITERATURE_NEXT_EXPERIMENT_20260910.md).
This milestone used no SSH/server/model call and changed no compute allowance.
Shutdown/provider billing state has not been inspected or confirmed here.

C018 completed on local CPU: 15,308 accepted response hashes match cached text.
GSM8K references are already short (median 143 tokens); a 128-token cutoff
reduces covered parents from 1,013 to 629. Fixed-parent surface-diverse selection
retains the same 996 pairs as random with 1.04% more tokens per traversal.
This is selection feasibility, not a downstream learning effect or strategy proof.
Read [the audit](../reports/REAL_MATH_C018_SELECTION_AUDIT.md).

Recommended first repair for review: original 256-update E013 recipe with only
terminal LR decay (192 constant updates, 64 cosine decay updates). The proposed
360+15 process reservation fits the existing 733-second balance, leaving 358.
The review-only JSON is `configs/diagnostics/real_math_terminal_decay_proposal.json`.
No implementation, registration, launch, fresh development/test decode or next
allowance follows from this plan. The old 512-update E015 proposal is retained
as a fallback, not the default and not an automatic second job.

Before startup, finish a reviewed frozen implementation, meaningful CPU/Linux
validation and staged transfer bundle. Resolve checkpoint preservation: the last
6.29 GiB free fails the inherited 12 GiB gate. Hourly rate and money cap are
still unknown. The illustrative 20-minute total power-on window is conditional,
not a quote or approved expense. Notify the owner only when an actual finite
queue, rate/cap and safe export/shutdown plan are ready; do not contact or start
the server to do literature review or open-ended debugging.

E014 is complete and must not repeat. All 32 batch8 streams replay exactly;
batch1 rescues zero of eight failures; 17/5,226 reference targets lose top-one.
All 32 reference-conditioned EOS targets win. The original E013 gate is failed.
The 55 Linux tests and full server/local output audits passed at execution.
Latest source/result publication before this planning milestone: d2ddb6a.

Current ledger: **6,467/7,200 process seconds used, 733 remaining, 18 receipts,
zero reservations**. Latest private backup SHA256:
`8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9`.
The 12 E013 checkpoint files (6,190,803,414 bytes) remain independently retained
at `.local/checkpoint_backups/gsm8k_overfit_e013_r1`; E014 created no new weights.
Do not restore older ledger balances or launch paused E012. A clone is not a
new allowance. Prior backup/hash verification remains evidence, not a new server
inspection this turn.

The prospective scientific minimum is three arms: Repeat256x1, Solutions256x4,
Breadth1024x1, then conditional selection/curriculum or model/objective checks.
A usable recipe, held-out capability calibration and a priced complete phase
must precede it. Existing training projections exceed 733 seconds. Final scale
and additional allowance remain unset; no underfunded grid is queued.

## Historical: CPU work complete; owner-started A800 needed

Read [E014 readiness](../reports/REAL_MATH_E014_READY.md) and the
[registration](experiments/E014_generation_diagnostic.md). The owner requested
generation-anomaly inspection, next-experiment preparation and notice when the
server is needed. Implementation3dd0034 and releasee79a0e1 are published.
Independent raw-tokenizer checks and published default inspection pass;52
focused CPU tests pass, with two GNU-timeout integrations pending Linux.
No server was contacted and no pretrained inference or reservation occurred.

Execute only `gsm8k_generation_e014_r1` after the owner supplies/starts the
existing A800 for this phase. It loads the **failed E013 checkpoint**, replays
all32 training prompts at batch8, decodes the fixed10 cases at batch1 and
measures all32 reference token/EOS distributions. No optimizer/training,
development/test decode, teacher call, new checkpoint or automatic next job.
Keep original max_new_tokens768, context1024, FP32/BF16/SDPA, seed17 and masks.
Do not relax the original E013 score or infer a passed gate from this diagnostic.

Current ledger SHA256:
`a332e3ff326f768c6d985786c41fd6352df1c52fc73f34bae9f47d7d264ba614`.
All17 receipts reconcile:6297/7200 used,903 left,zero reservations. Maximum
reservation360+15=375 leaves528. Restore the latest private ledger if needed;
never initialize a fresh allowance or restore the older16-receipt ledger.

Synchronize published main first. If direct fetch is unavailable, transfer a
hash-verified Git bundle from the current local clone. Do not overwrite unique
outputs or checkpoint files. The latest known server already retained E013's
12 checkpoint files and original tokenizer; recheck their content and source
before relying on that state. Independently retained weights are in
`.local/checkpoint_backups/gsm8k_overfit_e013_r1`; all12 hashes were rechecked
during CPU preparation and published inspection. No new base-model download
or storage expansion should be needed; at least2GiB free is required.

Set repository-relative paths on the server, using the existing pinned runtime:

```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
E014_TOKENIZER=.local/hf-cache/hub/models--Qwen--Qwen2.5-1.5B/snapshots/8faed761d45a263340a0528343f099c05c9a4323
E014_CHECKPOINT=runs/gsm8k_overfit_e013_r1/checkpoint_final
E014_LEDGER=.local/resource_ledger.json
python -m unittest tests.test_e014 tests.test_real_math_engineering tests.test_sft_data \
  tests.test_relation_engineering.ScoringTests tests.test_relation_engineering.DoseTests \
  tests.test_relation_engineering.LedgerTests tests.test_relation_engineering.OutputAuditTests \
  tests.test_budget_guard -v
python -m analyses.e014 inspect --tokenizer-dir "$E014_TOKENIZER" --checkpoint-dir "$E014_CHECKPOINT" --ledger "$E014_LEDGER"
python -m analyses.e014 launch --execute --tokenizer-dir "$E014_TOKENIZER" --checkpoint-dir "$E014_CHECKPOINT" --ledger "$E014_LEDGER"
python -m analyses.e014_audit --tokenizer-dir "$E014_TOKENIZER" --out runs/gsm8k_generation_e014_r1/record_verification.json
```

Require all54 tests on Linux, the recorded driver580.126.09 and package recipe,
and one idle A80080GB. The launcher checks current source/input/weight hashes
and exact ledger, then uses the existing cumulative watchdog. Preserve any
failure/timeout without retry. Reconcile the next receipt, update the private
ledger backup, audit/publish compact outputs and refresh this handoff. The
checkpoint is read-only and remains independently preserved. Inspect the
registration's decision table before proposing a later repair; the remaining
budget does not authorize a training sweep or the four-arm comparison.

## Historical: E013 finished, no automatic next model job

Read [the result](../reports/REAL_MATH_E013_RESULTS.md). The owner restored the
existing A800 and E013 completed from source
`4fa838a368f8197338d8a20513a21755830dfc7d`. All40 Linux tests and64 raw-output /
256-update checks pass. The overfit gate fails:24/32 train answers correct and
terminated, five truncations, three wrong numeric finals, NLL0.014206. Final
development is0/16. Its base0/16 is format-limited; do not claim zero underlying
base ability. No changed scorer, cap, checkpoint selection or retry.

All17 receipts reconcile: **6297/7200 used,903 remaining,zero reservations**.
Current ledger SHA256 is
`a332e3ff326f768c6d985786c41fd6352df1c52fc73f34bae9f47d7d264ba614`.
The current private ledger backup is updated; an immutable pre-E013 copy is
retained. Do not restore the former16-receipt ledger or replay E013/E012.

GPU execution has stopped. Compact outputs are in
`runs/gsm8k_overfit_e013_r1`; preflight/test evidence is in
`reports/real_math_e013_execution_r1`. All12 checkpoint files (6,190,803,414
bytes) have independent SHA256-verified backups; see
`reports/real_math_e013_checkpoint_backup.json`. The local recovery directory
is `.local/checkpoint_backups/gsm8k_overfit_e013_r1`. It contains weights and
tokenizer files, not an optimizer/RNG resume. Verify current publication and
ledger before shutdown/replacement; do not mistake this failed checkpoint
for the original base snapshot.

The four-arm training-only proxy is2096–2165 seconds versus903 available,
excluding scientific evaluation and overhead; the failed gate also blocks
scaling. A proposed next step is a separately frozen inference diagnostic on
this saved checkpoint: reproducibility at batch8, selected-case batch1 decoding,
and teacher-forced first-divergence token probabilities. No new model run is
registered/launched by this handoff. Preserve C017's existing pool and proposal.

The concrete review-only parameters are in
`configs/diagnostics/real_math_e014_proposal.json`: original32-prompt batch8
replay, eight failed cases plus two predetermined successful controls decoded
individually, and reference-conditioned divergence/EOS logits. Proposed cap
360+15 seconds; no new training, dev/test scoring or teacher call. It is not a
launchable implementation. The completed post-hoc CPU analysis is
`reports/real_math_e013_execution_r1/failure_analysis.json`.

## Historical preparation: fixed GSM8K engineering, after Linux preflight

The owner requested the next experiment. E013 code and immutable 32-train /
16-development inputs are prepared and CPU-verified. Read the
[ready report](../reports/REAL_MATH_E013_READY.md) and
[registration](experiments/E013_gsm8k_engineering.md). Preparation source commit
is `c11bf824b31c683d823d0d7d3e5627ad368f3fbb`; the release and compact inputs are
under `configs/real_math_e013` and `reports/real_math_e013_inputs_r1`.

The 04:32:40 UTC read-only SSH probe returned connection refused. The owner was
asked to start the existing A800 or provide updated access. Do not repeat
unchanged probes, rent another instance or launch old queues. Once reachable,
fetch and synchronize published main, restore/verify the current 16-receipt
ledger and original base snapshot, and run the registered focused tests,
including both GNU-timeout integrations on Linux. The launcher requires the
recorded environment, idle A800 80GB, original model hashes and 12 GiB free.
Set `E013_SNAPSHOT` to that snapshot, inspect, then execute this requested run.

```sh
python -m scripts.run_real_math_engineering --tokenizer-dir "$E013_SNAPSHOT"
python -m scripts.run_real_math_engineering --tokenizer-dir "$E013_SNAPSHOT" --execute
python -m scripts.audit_real_math_engineering_outputs --tokenizer-dir "$E013_SNAPSHOT" --out runs/gsm8k_overfit_e013_r1/record_verification.json
```

Run ID `gsm8k_overfit_e013_r1` is unused. Reserve 915 seconds (900 process + 15
guard), leaving 314 of the current 1229 seconds unreserved. No E013 GPU seconds
or reservation exist. Full dose: 256 updates, 167232 response / 229056 processed
tokens, 32 exposures per row. Numeric/EOS/NLL gate, raw IDs and phase timings
are mandatory. Preserve failed gates/timeouts without retries. Back up weights
and their manifest, reconcile the ledger and publish compact results before
ending the instance. Training-only projections do not approve a full scientific
phase. E012 stays paused. This finite experiment is already requested; further
permission is unnecessary once the existing server connection is restored.

## Historical C017 handoff: measured scope and candidate training scale

The owner requested and C017 completed original-problem split, solution coverage
and attrition audits. Read [the findings](../reports/REAL_MATH_CPU_AUDIT_20260910.md)
and [review-only scale proposal](../reports/real_math_c017_scale_proposal_r1/proposal.json).
The accepted freeze is `real_math_c017_parents_r2`; `parents_r1` is superseded.
The accepted measurement is `real_math_c017_solutions_r2`; the first answer-
format pass is retained for comparison. Do not redownload or expand the source
bank, replace zero-success parents, or restart old model queues automatically.

Data capacity: GSM8K audit1,024 parents,1,013 with a usable answer,963 with K>=4;
MATH audit512 parents,486 with a usable answer,481 with K>=4. “Usable” means
conservative final-answer agreement, complete serialization/length and text
uniqueness, not proved reasoning. MATH remaining units/percent/base/mixed-number
formats are unresolved; original-reference and qualitative-review flags are
in the report. No final-test model scoring was performed.

Proposed first study: Repeat256x1, Solutions256x4, Mixed512x2, Breadth1024x1.
Each CPU schedule has524,288 supervised tokens and256 updates, with whole
responses and every accepted selected pair used. Seed17 first; seed23 only
after a measured complete-phase budget. New32-parent GSM8K overfit/profile
comes first, using pinned Qwen2.5-1.5B base and a reviewed scorer/runtime.
The CPU proposal is not a launchable GPU queue. Review scientific residuals,
reference-quality handling and the priced bounded phase before training.

The ledger remains5971/7200 used,1229 left,16 receipts and zero reservations;
its SHA256 is664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5.
No remaining GPU runtime estimate has been established for real-data SFT.
E012 is still paused and unrelated to the proposed GSM8K engineering stage.

Recovery: the ignored source cache is `.local/real_math_c017_sources`; parent
texts are in `.local/real_math_c017_parents_r2`, and raw response candidates in
`.local/real_math_c017_solutions_r2`. These locations are repository-relative,
not server paths. Public source receipts pin every input. Parent manifests and
candidate decisions have adjacent gzip/base64 archives: decode base64, gunzip,
and verify the recorded SHA256 before use. Full reproducibility commands are
in [C017](experiments/C017_real_math_cpu_audit.md). Keep raw third-party text
outside Git; no large model weights or corpus download is needed for CPU reuse.

## Historical: P004 discussion before C017 authorization

Latest data proposal: read the
[dataset evidence review](../reports/DATASET_SELECTION_EVIDENCE_20260910.md).
Keep GSM8K first; propose stratified MATH levels 1–3 for key second-task checks.
The next independent CPU task is a source/split and capped solution-availability
audit specification. Verify original MATH train/test membership rather than
trusting a mirror's merged `train` label. Audit OpenMathInstruct-2 responses
linked to original eligible problems; keep augmented questions separate and
GSM-Symbolic evaluation-only. Draw problem pools before inspecting accepted K_i.
Do not infer a cached large teacher's generation cost from a small local teacher.
This is a scope proposal, not an executable grid or a request for server startup.

Latest constraint: keep the proposed core on small students, with Qwen1.5B
primary and OLMo1B conditional. Read the
[paper/model/compute audit](../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md).
Math7B is no longer the default teacher; inspect reusable multi-solution data
and specify a possible bounded Math1.5B generation calibration. Neither has
run. Cached outputs without attempt/cost logs do not identify effective
generation price. No large-model grid or new GPU job follows from this revision.

The owner's latest instruction is to answer the project-framing and deliverable
questions first, then continue. Read [P004](experiments/P004_cost_aware_sft_allocation_proposal.md).
The full personally addressed reply remains a private unsent draft.
The proposed core is asymmetric acquisition cost for problems versus solutions,
with a specified SFT budget. Models/data, cost assumptions, candidate P/K grid,
selection caveats and course deliverables are concrete but remain proposals.

The latest privately retained reply is the revised bilingual version, which
supersedes the first concise draft. It explicitly states prior synthetic pilots
and failures and distinguishes the tested student checkpoint from untested
teacher/second-family candidates. Review [the model-selection evidence](../reports/MODEL_SELECTION_EVIDENCE_20260910.md).
The proposed GSM8K grid is a tentative range; establish feasibility and actual
cost before fixing its executed subset.

The [revised abstract and deliverables](PROJECT_ABSTRACT_20260910.md) express
this scope for review. The external course document has not been edited, and
the abstract does not itself approve an executable allocation grid.

Next discuss the reply and revised scope with the owner, then prepare a revised
abstract and a bounded acquisition/feasibility protocol with measured cost
estimates. Assess whether E012 is still a necessary engineering diagnostic.
It is paused, not discarded or rerun; frozen inputs/runtime stay unchanged.
The earlier request for server availability does not override this newer pause.
No startup, GPU job, paid API, new budget or main grid follows from this document.
Current ledger remains 5971 / 7200 used, 1229 left, 16 receipts, zero reservations.

## Historical E012 handoff — use only after the owner resumes this sequence

Read [the ready report](../reports/RELATION_E012_READY.md),
[E012 registration](experiments/E012_relation_diagnostic_ladder.md) and
[C016 findings](../reports/RELATION_C016_CPU_READY.md). The owner requested this
conditional engineering sequence; no further budget approval is needed inside
the existing allowance. Server availability/connection is still required.

Source `1fc27d459c8445417e3db73d944a7d2c7c064ffd` was published before release
preparation; release `27a0943fef352e67072e8b2d7db36a3259524246` was published
before the clean-checkout inspection and repeated checks. All 76 local CPU
checks pass, with 2 mandatory GNU-timeout integrations awaiting Linux. See
[verification receipt](../reports/relation_e012_fresh_checkout_verification.json).
No E012 model execution, server connection or reservation has occurred.

After release publication, the prior SSH endpoint returned connection refused
on one read-only probe at 02:11 UTC. Current power state is unconfirmed. The
owner has been asked for startup/updated connection information; no model run
or new reservation occurred. [Receipt](../reports/relation_e012_server_availability.json).

Initial private ledger SHA256:
`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`;
**5971 / 7200 used, 1229 remaining, 16 receipts, zero reservations**. Both public
aggregate summaries have been repaired to include E011. Never restore the
older 5740-second ledger or initialize a new allowance on a clone.

1. Obtain owner-started A800 availability and current connection information.
   Verify the latest GitHub main independently on the local host, then fetch
   or synchronize that exact commit by a verified Git bundle. Preserve private
   keys/endpoints and current ledger outside Git; do not trust cached origin/main.
2. Verify pinned original Qwen2.5-1.5B model bytes (not tuned weights), recorded
   Linux Python 3.12 / PyTorch 2.8.0+cu128 environment, one idle A800 80GB and
   at least 12 GiB free after setup. Confirm any redundant artifact has a verified
   independent backup before cleanup; report measured expansion needs.
3. Run the 78-test focused suite from the verification receipt, setting
   `RELATION_ENGINEERING_TOKENIZER_DIR` to the verified snapshot. Both watchdog
   integration tests skipped on macOS must pass here. Run the default inspection.
4. Launch `single_step` using `--execute` and `--expected-published-commit`
   equal to the independently verified latest commit. Its registered run ID is
   `relation_single_step_e012_r1`; cap 360 seconds plus 15-second guard.
5. Retrieve all compact outputs and the updated ledger, independently re-audit
   raw IDs and field statistics, verify every checkpoint file on an independent
   destination, and publish the result. Update the files listed below. Only a
   complete proof/NLL/profile gate plus preservation permits `given_route`, and
   then `fixed_reference`, each from the fresh base and within its same cap.

Three maximum reservations total 1125 seconds. No shortened run, retry, seed
search, warm start or continuation past a failed gate. The launcher requires
the latest ledger after each job, ordered receipts, published prior outputs
and a matching published backup receipt. Run one explicit stage at a time.
Completed learning failure and incomplete infrastructure execution are distinct;
both preserve all available evidence. No scientific pair/main grid is queued.

For every result or failure update the research journal (question, motivation,
design, result, analysis, decision), detailed phase report, decisions, status,
README, AI-use log, artifact inventory, run registry, compute accounting and
this handoff. Before declaring a server disposable, verify Git publication,
independent checkpoint copies and the latest cumulative ledger. Process timeout
alone does not shut down a paid instance.

E011 had 0/32 complete training proofs and all 333 parseable after-states equal
2. C016 retains all 48 parents / 288 rows and records finite imbalance and
train/dev operation overlap. Complete free generation is separate from gold-
prefix measurements. Low aggregate NLL cannot substitute for proof correctness.
Existing E011/C016 runtime and data bytes remain frozen.

## Historical: E011 failed learning gate; no GPU phase queued

Read [full results and analysis](../reports/RELATION_E011_RESULTS.md),
[CPU verification](../reports/relation_e011_output_verification.json),
[ledger reconciliation](../reports/relation_e011_ledger_verification.json) and
[checkpoint backup](../reports/relation_e011_checkpoint_backup.json).
Run `relation_overfit_e011_r1` completed normally from published33820d9,with
256 updates/103424 supervised tokens. It failed the engineering gate:0/32
complete train proofs and0/16 for each dev view; every parseable generated
step result was2. No additional GPU run is authorized automatically.

**Current ledger:5971/7200 used,1229 remaining,16 receipts,zero reservations.**
SHA256:`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
The prior5740 balance and E011's launch config are historical; its guard should
reject replay. Restore the latest independently retained ledger on a clone.
All12 checkpoint files (6190803414 bytes) are independently backed up with
SHA256 verification. Compact outputs are fully tracked; weights remain private.
The authenticated provider console confirms **已关机** after publication and
preservation; see [closeout](../reports/relation_e011_shutdown_closeout.json).
No server is needed for the next CPU preparation. On any later restart or
clone,fetch current Git and restore the latest5971-second ledger before work.

Next do CPU diagnosis/preparation. Keep the original full-graph task and failed
run. Consider one fixed reference per original prompt at the same dose,
a supplied-route propagation diagnostic,and a one-edge table lookup gate.
Different diagnostic tasks are not comparable scientific treatment effects.
Predeclare selection,semantic-field measurements,proof/EOS criteria and complete
resource caps before any new model evaluation. Do not claim impossibility,
causal route effects or ICLR readiness from this engineering failure.

The cached CPU audit adapter at ecc7867 memoizes only immutable vocabulary size;
the original scorer and frozen runtime hashes remain unchanged. All96 outputs
produce byte-identical server/local audits. All42 Linux tests passed after a
private tokenizer-path symlink fixed one retained initial skip. No GPU retry.

## Historical: E011 CPU release complete — request owner-started A800

Read [ready report](../reports/RELATION_E011_READY.md),[registration](experiments/E011_relation_engineering.md),
[release hashes](../configs/relation_engineering_e011/release.json) and
[CPU verification](../reports/relation_engineering_c015_verification.json).
Preparation source `8eeb0f9883759a69ca42540932b98d71b2c64414` preceded extraction.
`runs/relation_engineering_c015_r1` is immutable and fully tracked; do not rerun.
Its manifest SHA256 is`ddb0068a2ddef8150948b7f8eaf0f2b86d3c3f9a42268c7d7725f44ee1afb854`.

No server operation/GPU spending occurred. One registered job remains not_run:
`relation_overfit_e011_r1`. One A80080GB is appropriate for the planned recipe;
actual long-prompt memory/time is unmeasured. Ask the owner to start/provide it
now that CPU preparation is complete. Do not reuse any completed queue.

On connection:

1. Fetch and verify the latest published main; do not rely on a cloned checkout.
2. Restore the independently retained15-receipt ledger:5740 used/1460 remaining,
 zero reservations,SHA256`1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
 Never initialize a fresh allowance. Restore the pinned original base,not tuned weights.
3. Verify recorded Python3.12/PyTorch2.8.0+cu128 environment and requirements,
 idle A80080GB,and12GiB free after model/environment setup. Keep backups before
 any cleanup; request expansion only if the measured free space requires it.
4. Run all42 focused tests with the real tokenizer on Linux,including both
 GNU-timeout integrations. Run launcher inspection,then the fixed `--execute`
 command below. It reserves at most735 seconds and never auto-retries.
5. Collect stdout,raw token predictions,history,metrics,checkpoint manifest and
 process receipt on completion or failure. Independently audit/reconcile/back up,
 publish the complete result and follow the owner's normal-shutdown preference.
 Process timeout alone does not power off the instance. Do not expose credentials
 or private endpoints in tracked files. No automatic scientific follow-up.

```bash
# Set TOKENIZER_DIR to the verified local pinned snapshot; activate the GPU runtime.
RELATION_ENGINEERING_TOKENIZER_DIR="$TOKENIZER_DIR" python -m unittest tests.test_relation_engineering tests.test_relation_transport tests.test_relation_cpu_audit tests.test_sft_data tests.test_budget_guard -v
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --tokenizer-dir "$TOKENIZER_DIR"
python -m scripts.run_relation_engineering --ledger .local/resource_ledger.json --execute
python -m scripts.audit_relation_engineering_outputs --run-dir runs/relation_overfit_e011_r1 --tokenizer-dir "$TOKENIZER_DIR" --out reports/relation_e011_output_verification_r1.json
```

The fixed256 updates and96 generations test engineering feasibility only.
32/32 complete EOS-terminated train proofs,NLL<.2 and complete profile/dose are
required for the gate. Preserve even zero dev accuracy; do not select by the
16 diagnostic parents. Report causes of failure before designing a bounded
repair; a success supports a separately reviewed fresh-group scientific pilot.
Max remains the recommendation for execution/verification; no mode switch is asserted.

## Historical C015/E011 source milestone — publish before extracting inputs

The next executable engineering phase is registered in
[E011](experiments/E011_relation_engineering.md). Fixed32 train/16 diagnostic
worlds from declared C014 seed prefixes,256 updates, multi-route only,
strict32/32 overfit gate and measured long-context profile. One720-second
process plus15-second guard fits1460 remaining. No scientific pair is queued.

Publish source, materialize immutable `runs/relation_engineering_c015_r1`,
independently reload/check the compact bundle, freeze the release hash and
publish the complete CPU-ready record before asking the owner to start A800.
Use the exact retained15-receipt ledger (5740 used), never a fresh or cloned
stale ledger. Source/inputs are prepared locally; no server operation occurred.

## Historical: C014 complete, independently verified, no GPU queued

Read [C014 results](../reports/RELATION_TRANSPORT_C014_RESULTS.md),
[registration](experiments/C014_relation_transport_cpu_audit.md),
[summary](../reports/relation_transport_c014_r1/summary.json) and
[independent receipt](../reports/relation_transport_c014_verification.json).
Source `6c24d4c1379a421be7b44151c653842a6cd9aabf` was published before execution.
Do not rerun or overwrite `relation_transport_c014_r1`.

All10,000 intended worlds were retained with four valid length-four evidence
routes and101 supervised tokens per clean reference. Full clean serialized
length is1137, versus the old arithmetic384-token cap. Useful/irrelevant
deletion both have949 prompt tokens. All40 predefined CPU probe tests remain
unflagged; separate verification retokenized40,000 references and50,000 views
and checked80,000 predictions. This is an observed CPU sandbox; never relabel
its2,000 audit worlds as an untouched final test. The8,000-update schedule is
accounting only, not a training queue.

Next implement and freeze a small32-world engineering/profile runner with
the same pinned1.5B base, full FP32 AdamW/BF16 recipe and new serialization.
Prepare exact inputs, strict proof metrics, context/generation caps and a
complete per-job budget before requesting an A800. Existing arithmetic memory/
throughput measurements do not establish the cost of1137-token examples.
Do not launch a scientific pair, change optimizer/model, or extend the total
7200-second allowance. Remaining1460 seconds has zero reservations. The server
was confirmed stopped after E010; no server operation occurred in C014.

State/table exposure remains unequal under route allocation despite exact
tokens; do not select a more balanced seed after observing residuals. The
claim is evidence-route allocation within one algorithm and topology. A
separate final scientific population/protocol and novelty case remain pending.
The implementation/verification task fits Max; no setting change is asserted.

## Historical P003 decision and C014 preparation

### P003 reviewed; no GPU queue at the design milestone

The owner requested immediate task/control redesign. Read
[the integrated proposal](CONTROL_REDESIGN_PROPOSAL_20260909.md) first, then
the three linked independent reviews. The current arithmetic study is retained
as a restricted boundary result; do not add seeds to seek a preferred sign.
The selected **CPU candidate** is permutation relation transport with four
equal-length evidence routes, a repeated-route allocation control, and
predeclared useful/irrelevant evidence deletion. It is not a semantic-strategy
benchmark, and anonymous slot balancing is not global strategy coverage.

Prepare one bounded CPU implementation/registration and publish source and
config before materialization. The 10,000-instance audit size in the proposal
is prospective, not a completed result. Freeze probe definitions/thresholds,
seed list, serialization, symmetry groups and solver negatives. Independently
verify full support, counterfactuals, exact tokens, schedules and leakage;
retain every generation attempt and every failure. No selective token filtering.
Report state/table-exposure residuals and the limitations of fixed-topology IID
evaluation. No existing holdout access or automatic training is authorized.

The task recommendation is Ultra for separable scientific review and Max for
the bounded implementation/verification stage; no setting change is asserted.
Only after CPU receipts pass should a concrete training/profile/replication
and resource proposal be prepared. Remaining GPU allowance is1460 seconds;
there is no new reservation, startup or extension.

The E010 provider instance is **confirmed stopped** at approximately20:00 UTC;
the confirmation heartbeat is **paused**. See the
[sanitized closeout](../reports/absent_boundary_seed31_shutdown_closeout.json).
Do not reopen it merely to complete documentation or CPU development.

## Historical E010 state,2026-09-09 UTC

The owner restarted the A800 and authorized the frozen seed31 pair. Both runs
completed normally from the prepublished clean commit
`9217685f6bdb4d0c67a0d76513c12f89898593cb` at18:41:53 UTC:
`absent_boundary_paths_seed31_r1` and `absent_boundary_gcm_seed31_r1`.
**Do not launch these run IDs or any earlier queue again.**

Read [the full analysis](../reports/ABSENT_BOUNDARY_SEED31_RESULTS.md),
[E010](experiments/E010_absent_boundary_seed31.md), [status](../reports/STATUS.md)
and [the journal](RESEARCH_JOURNAL.md). The task-mode recommendation is Max for
execution/recovery and Ultra for a later broad, separable scientific redesign;
this recommendation does not assert a changed setting or authorize delegation.

| Endpoint | Paths | GCM |
|---|---:|---:|
| Matched greedy expression, primary |7/64 |5/64 |
| Matched complete trace |4/64 |4/64 |
| Broader expression and trace |0/64 |2/64 |
| Matched sampled pass@4 |11/64 |7/64 |
| Complete sampled traces |13/256 |15/256 |

All294 Linux preflight tests passed. Both arms completed1024 updates,4096
presentations,277760 EOS-inclusive supervised tokens,482848 processed tokens
and3734 padding tokens. Server and independent local audits of all800 saved
predictions are byte-identical across10 files. No technical GPU failure, retry,
nonfinite training or generation truncation occurred. The2048 raw holdout
groups remain unsolved and unevaluated. Identity absence still permits
cancellation/computed constants; matching does not eliminate numerical or
population selection. The old256-question pair is not a causal control for
this128-question pair.

## Budget and migration — never restore the stale pre-run balance

Each new run charged512 seconds. The current cumulative private ledger is
**5740/7200 charged,1460 remaining**,15 receipts,zero reservations. SHA256:
`1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
The [public ledger proof](../reports/absent_boundary_seed31_ledger_verification.json)
checks every receipt and preserves the prior13 jobs unchanged. The old4716-second
ledger is historical; do not restore it as current or initialize a new ledger
on a clone. The current2130-second pair reservation exceeds the1460 balance.
A new scientific plan and resource review are required before more training.

## Preservation and shutdown verification complete

All compact outputs and the final ledger are independently local and published
at result commit `3585ad2d2f6424180b4b3ec345904dc0fc21fea6`, also synchronized
cleanly onto the server. Both checkpoints have independent SHA256 verification:
24 files,12,381,607,162 bytes. See the [backup summary](../reports/absent_boundary_seed31_checkpoint_backup_summary.json)
and [fresh idle/ledger check](../reports/absent_boundary_seed31_final_server_check.json).
No required unique experiment state remains only on the instance.

The vendor's `/usr/bin/shutdown` command was executed at19:00:27 UTC with
exit0 after fresh instance/GPU/ledger/source checks. The server had preservation
commit `b27a85c3ee20c208a1b12a7653dd971c152c7f15`. A prior45-second GitHub-pull
timeout was recovered with a verified incremental bundle; the first shutdown
precondition rejected the stale HEAD before any command executed. At19:01:07
UTC SSH was no longer accessible. See the [shutdown request](../reports/absent_boundary_seed31_shutdown_request.json)
and [connectivity receipt](../reports/absent_boundary_seed31_after_shutdown_connectivity.json).

The Mac lock initially prevented confirmation. During the later CPU design
review, Computer Use read the authenticated provider instance list and matched
the exact instance against the private gate: it displayed **已关机**. Confirmation
was recorded at20:00:03 UTC and the heartbeat paused. No second shutdown command,
server start, deletion or release occurred. This verifies provider stopped
state, not an itemized billing-history reconciliation. The prior pending-state
receipts remain historical. Do not reopen the instance for CPU work.

All earlier seed17/23 scientific weights and engineering weights remain backed
up outside Git. Current weights also are model/tokenizer only, not exact
optimizer/RNG resume checkpoints. See [artifact inventory](../reports/ARTIFACTS.md)
and [migration protocol](MIGRATION.md). Public Git excludes private connection
information, credentials, local user paths, live ledger and weights.

## Historical motivation for P003 — CPU only

The evidence does not justify scaling from the small favorable primary count:
trace results tie and broader results favor GCM. Preserve that weak boundary
result; do not search seeds or learning rates for a preferred sign.

Prepare a concrete task/estimand design for owner review. Assess a graph/relational
or controlled symbolic generator with multiple valid paths by construction,
rather than conditioning most questions on rare shared support. Audit gold
solver correctness, nuisance difficulty, shortcuts, population coverage and
train/development separation before model execution. Target multiplicity is
part of the allocation treatment; do not blindly match it away or interpret
lower repetition-training NLL as independent evidence of better reasoning.

No new benchmark or treatment is approved by this suggestion. Keep E010's
unchanged development endpoints and untouched holdout intact. The CPU search
failures, complete support archives, materialized data and source hashes are
recoverable from Git; normal training recovery needs no large CPU witness stream.
