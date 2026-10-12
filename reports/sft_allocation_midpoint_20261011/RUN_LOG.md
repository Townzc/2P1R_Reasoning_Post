# P007 midpoint execution log

## Motivation and fixed decision

The owner approved a model-engineering pilot followed by the four-condition study on October11. The pilot checks SFT learning, scoring from actual generated tokens, and complete-state recovery before scientific budget is committed. All scientific conditions retain the same adaptation, tokenizer, supervised-target/update budget, evaluation contract and endpoint. Main outcomes had not been generated at admission.

## Engineering result

| Diagnostic | Before | After |
|---|---:|---:|
| Training32 greedy correctness |19/32|32/32|
| Training32 response NLL |0.488519|0.0000311|
| Previously observed development80 correctness |49/80|59/80|

The32-question overfit run completed256 updates and167232 supervised targets. A separate fresh GPU restored step2 and performed the prespecified2 diagnostic updates/1132 additional targets; model, optimizer, RNG, cursor and dose matched the uninterruptedstep4 exactly. These are258 engineering updates, not scientific-grid updates. All224 generated outputs were independently rescored locally; all stopped/scored records agree. Eleven profile checkpoints and one recovery-probe checkpoint were hashed by an independent CPU worker. Complete profile2/4/256 and probe4 states were also downloaded and verified locally. Both engineering GPU containers exited before main admission.

Training compute was226.82s, whole profile1162.46s. The peak allocation was12.04GiB; one longest687-token backward-only diagnostic made no optimizer update. Whole-function rate proxies were approximately$0.950 for the profile and$0.049 for the recovery check. These exclude unmeasured billing/startup details and are not provider invoices. The conservative engineering/preparation reservation remains$13.50 inside its$20 ceiling.

## Failure and reflection

The first model image build was interrupted because the agent changed its source during the build. It performed zero model work, and its lack of a profile claim was reconciled before a fresh build. The failed log and record are retained. Source must remain fixed throughout image construction. A first local scoring-audit invocation also pointed at a nonexistent tokenizer directory; it made no model calls. The corrected invocation verified the locked local tokenizer and all224 already-saved predictions, without regenerating any output.

Fit32 and recovery are engineering evidence. Observed80 improvement did not choose an arm, learning rate or checkpoint and is not the four-arm scientific result. Evaluation and artifact transport make wall time materially longer than gradient computation. The main learning-rate vector is passed as exact frozen numbers, not regenerated independently on different hosts.

## Admitted finite study

See GRID_ADMISSION.json for the unchanged four arms, seeds17/23, exact LR vector and input hashes. Each trajectory has256 updates and524288 supervised targets; all eight together have2048 updates and4194304 targets. Same observed80 learning diagnostics at64/128/256 and one431-question endpoint. The base reference adds431 outputs. In total the main study and base request5799 greedy outputs. This is one procurement draw and development evidence, not a claim of no pretraining contamination.

EXECUTION_BINDING.json adds a finite CPU cloud controller to survive local disconnection. It is a technical execution amendment before any main result: same scientific queue, fixed deadline2026-10-13 04:00UTC, at most two single-GPU tasks. Main slots reserve$72, base$4, independent audit$1, CPU controller$1; including prior engineering/preparation, the current conservative reservation is$91.50. Actual billing remains unknown. This is below P007's$350 presentation-work and$500 project ceilings, not a spending target. No teacher pilot, extra arm or model is part of this finite queue.

After the eight runs, the cloud queue performs the base reference and independent artifact audit, then exits. Failed pairs preserve their evidence and leave future inputs unattempted. Local analysis reports both seeds, primary Solutions−Repeat and Breadth−Solutions contrasts, negative outcomes and conditional question-bootstrap intervals; those intervals do not estimate variation across training seeds or new procurement draws. Results and reflections will be appended after actual completion.

## Main queue started

At 2026-10-12T05:08:18.100065+00:00 the detached finite controller and first pair were independently visible in provider/atomic-ledger records. The first scientific update is saved in MAIN_STARTED.json. Other arms remain queued and are not yet results. The two workers are NVIDIA A10080GB PCIe and SXM4 variants; their environment records are preserved, and runtime is not an exact hardware-controlled comparison. The controller and first pair are the only active main tasks; no duplicate queue was launched.

## First observed diagnostic and live billing — October11 22:16PDT

Repeat seed17 reached105/256 updates and seed23 reached64/256 in the05:16:19UTC provider/ledger snapshot; laterarms remain unclaimed, no failure terminal. Repeat17 step64 scored63/80 (initialbase49/80) on the previously observed development set. All10 raw/scored batch hashes and80 unique scored records were recovered and reconciled to immutable completion receipts. The server independent prefix oracle passed; a full local oracle rescore is still pending. This is an intermediate learning diagnostic, not an allocation comparison; no checkpoint or recipe changes follow.

Authenticated Modal CLI billing now succeeds for the actual experiment workspace. Its October summary atabout22:15PDT reports metered1.96059585USD, credits−1.96000000, egressallowance−0.00059585, andbilled0USD. Ongoing metering maylag and this is not a final invoice or a credit-balance lookup. The hourly detail covers completedintervals and does not include the currentpartialhour. Current twoGPU+host+controller nominal rate is5.9457USD/hour; the original91.50USD finite reservation is retained. Private rawsummary/detail/rate snapshots preserved; INTERIM_20261011_2216PDT.json records the verified distinctions.


## October11 late evening — owner overnight authorization and provider preemption

**Motivation.** The owner delegated overnight monitoring, interpretation against P007's original hypotheses, and justified bounded follow-up experiments, with at least$50 reserved and30-minute stable-state checks. Keep the existing stricter$350 presentation envelope,$100 report allocation,$50 reserve. The current main absolute deadline remains October13 04:00UTC. This supersedes the old heartbeat's prohibition on any follow-up science; it does not permit indefinite expansion or automatic replays.

**Observed failure.** At05:21:23UTC the provider explicitly logged CPU-controller preemption. Its attempted platform restart was denied by the immutable claim, correctly preventing duplicate dispatch. The mapped children received cancellation at05:24:22 and the app reached stopped/zero containers by05:26:58. Repeat17 committed200 updates/409637targets, attempted201/411673; Repeat23 committed79/161780, attempted80/163795. Their last complete states are192 and64, independently downloaded and checked. All703 compact/selected-state artifacts verify. Their240 saved observed-dev outputs remain evidence; no431-question endpoint output exists. The two final intents retain unresolved committed-state status; do not infer unseen weights from an interrupted backward trace. The other six runs, base and audit never claimed.

**Decision before any allocation endpoint.** One explicitly accounted fresh replacement per failed Repeat run is admitted under the owner's overnight discretion and P007's bounded-repair allowance. These are fresh-base replacement attempts, not exact continuation from192/64 or200/79. Original failed runs/claims are retained and excluded from matched-terminal contrasts because of infrastructure failure, never selected by accuracy. The six unattempted runs and base/audit migrate to the replacement campaign mp-grid-20261012-r2 with identical frozen scientific configs. This is one finite eight-slot completion campaign; the original unattempted slots are retired and must never also be dispatched. No automatic second replacement is admitted. See PREEMPTION_RECONCILIATION.json for the immutable parent receipts and explicit attempt accounting.

**Engineering change.** A finite nonpreemptible CPU controller now uses individually spawned calls, saving dispatch intent before submission and call IDs afterward. Read-only result polling never cancels a child or resubmits it. Modal documents a3×CPU/memory premium for this CPU-only setting; GPU preemption remains possible. No training, checkpoint, loss, schedule, evaluation or scoring code was changed. A60-second nvidia-smi sampler records actual compute/memory/power use, stops before manifest construction, and makes no model calls. Parent failure is preserved; an uncertain spawn still fails closed. Source is published before building. [Provider preemption contract](https://modal.com/docs/guide/preemption), [spawn/call retrieval](https://modal.com/docs/guide/job-queue).

**Validation.**37 local tests passed, including lost spawn response, lost local receipt, duplicate dispatch, pending result, worker timeout, parent interruption, changed/live parent, queue expansion, complete checkpoint/optimizer/RNG round-trip, target normalization and analysis checks. SDK1.6.1 accepted function options. Local checkpoints192/64 passed independent manifest/full-state validation. These are engineering checks, not additional scientific evidence or a guarantee against every cloud fault.

**Costs.** New campaign reserves$80:8×$9 training,$4base,$1audit,$3 nonpreemptible controller. Preserve$19 in conservative reservations for old admitted work and$13.50 preparation/engineering: current total$112.50. The old$59 for work that never attempted is retired, not reported as money spent. The latest authenticated provider meter is$2.83059585 with credits and egress allowance offsetting billed cost to0; provider reporting lags, so neither reservations nor this snapshot are a final invoice/credit balance. Failures and build overhead remain counted.

**Reflection and overnight next decision.** Recovery correctness at two diagnostic updates did not establish robust cloud orchestration. A preemptible parent plus a cancellable map created an avoidable common-mode failure. Preserve this operational negative result. Complete and audit all four conditions first; then report both seed contrasts, uncertainty conditional on models/problem draw, and the effect of answer attrition/exposure. If contrasts are coherent, prioritize one confirmation on a fresh procurement draw; if extra solutions add little, first diagnose coverage, length/quality and token-dose sensitivity rather than hunt for a winning ratio. The original capped same-teacher acquisition pilot remains a useful next step because the bank's historical costs are unknown. Choose and freeze one small follow-up only after actual results, reserve its cost/absolute deadline in advance, and avoid another broad grid. Stable-state heartbeat is now30min; meaningful failures remain immediate. The morning note must distinguish verified endpoints, pending work, costs and next scientific decision.


### Replacement admission observed,05:40UTC
Published repair d8c75ae3 was submitted exactly once as mp-grid-20261012-r2. The controller and two independently spawned A10080PCIe jobs are real and progressing:32/31 committed updates at05:40:33UTC; published release and reconciliation binding match the remote intent. Initialupdate receipts andcheckpoint32 manifests were retrieved. REPLACEMENT_STARTED.json records the provider app and meter3.32059585USD (credits offsetbilled0,reportinglag). Earlypointutilization samples0–30% andrough12GiB VRAM do not establish sustained efficiency; retain60-second samples forphaseanalysis. Automation p007 is ACTIVE every30minutes with theowner's overnight follow-up authorization andbudgetreserve. No endpoint431 resultyet.


### First pair completed training,06:02UTC
Both Repeat17/23 committed all256 updates and exactly524288 supervision targets; finalupdate intents/completions agree and bothcheckpoint256 manifests were collected. Training-after evaluation is stilllive; no endpoint resultorallocationconclusion isreported. The fixedqueue/configs remainunchanged. Authenticatedmeter5.42059585USD,credits offset billed0; reportinglag and112.50USD reservation remainexplicit. Passive60-secondGPU samples remainaround24–28% mean acrossmixedstages,not a timeintegrated utilizationmeasure. Finalfullstate/export/localscoring checks will followcompletedresults.


### Repeat endpoints verified; Solutions started, October12 06:33UTC

**Result and verification.** Repeat seed17 scored309/431 (71.69%); seed23 scored307/431 (71.23%) at the fixed terminal256. Both runs committed256 updates and524288 targets, with all671 outputs per run preserved. Each local export independently verified867 compact/full-terminal-state files; the terminal adapter/optimizer/RNG/cursor states and frozen LR/schedule matched their manifests and identities. The local independent prefix oracle re-scored all1342 saved outputs and matched raw returns, per-batch intent/completion hashes, summaries and immutable terminal receipts. No generation was repeated. See REPEAT_RESULTS_VERIFIED.json. The provider has released the two Repeat GPU containers; the same CPU controller automatically launched the two Solutions workers, each at64 committed updates in the06:30:43 snapshot. Breadth/Mixed/base/audit remain unclaimed. No new failure.

**Reflection.** These are the first complete endpoints, not evidence favoring problems or solutions. The observed80 trajectory is63→60→57 for seed17 and65→61→64 for seed23 at64/128/256 updates. Its fluctuation cautions against choosing a best checkpoint; the prespecified terminal256 comparison remains unchanged. Training itself took718/740 seconds out of2709/2816 seconds per run; generation took1666/1763 seconds. Most elapsed time is evaluation rather than gradient work. Sparse GPU samples and low memory occupancy support investigating efficiency after this campaign, without changing its numerical recipe mid-comparison. No allocation, ratio or follow-up is selected from this single condition.

**Cost.** Authenticated provider snapshots around06:30–06:32 reported8.48059603 then8.42059603USD metered (a downward reconciliation), with billed0 after credits/allowance. Preserve the latest raw summary and reporting-time caveat; these are not final invoices or a remaining balance. Conservative reservations remain112.50USD and the350/100/50 budget split is unchanged. Runtime estimates of2.22/2.30USD for the two completed runs are separate from workspace metering and exclude some overhead.
