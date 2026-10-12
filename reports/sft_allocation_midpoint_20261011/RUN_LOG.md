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
