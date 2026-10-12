# P007 — SFT data allocation for the October 15 midpoint

**Work date:** October 11, 2026, America/Los_Angeles. **Status:** reviewable proposal and CPU preparation; no new scientific result or GPU queue admitted. **Hypothesis timing:** before new outcomes.

## Question and motivation

Under a fixed acquisition budget, when is another problem worth more than another answer to an existing problem, with student training resources controlled independently? The immediate diagnostic asks whether additional distinct answer texts help beyond repeated exposure to one answer, and how that gain compares with broader problem support. It does not presume that breadth, depth, or an interior allocation wins.

The practical decision arises when a team can commission or curate another task, request more demonstrations for known tasks, or reuse demonstrations it already owns. Problem acquisition includes its usable reference/verification setup when that is part of the purchased unit. Public benchmark problems do not establish a universal market price for this action.

Two evidence tracks remain separate:

1. **Released-bank allocation:** compare retained data and training exposure using a fixed public multi-answer source. Historical generation cost is unknown. This can reveal a learning-value contrast, not a measured dollar-optimal policy.
2. **Metered acquisition pilot:** record all candidate attempts, duplicates, verification, and accepted answers for one fixed teacher. Its own costs cannot be assigned retrospectively to another teacher's released bank. A later cost-performance experiment must train on data produced by the same metered process.

The longer-term contribution candidate is a validated decision about near-optimal allocations and the conditions that change them. Neither a P/R sweep, a price equation, difficulty weighting, nor small-pilot extrapolation is individually a novelty claim.

## Closest prior work and the remaining test

| Primary source | Established precedent relevant here | Consequence for this project |
|---|---|---|
| [Shortest Path](https://arxiv.org/abs/2604.15306) | Problem/response allocation and coverage are direct prior work. | Do not sell more problems versus more solutions as a new task. |
| [When Does Generating More Help?](https://arxiv.org/abs/2607.01727) | Resampling an existing pool versus expanding it, q×r allocation, and extrapolation along the response-count axis. | A small-pilot performance fit alone is insufficient; match the actual resource question and validate decisions on new procurement draws. |
| [OpenMathInstruct-2](https://arxiv.org/abs/2410.01560) | Fixed 256K-pair comparisons with different numbers of problems; a reusable multi-answer source. | It is an inventory comparison, not evidence that R=1 always wins or a history of every rejected generation. |
| [AceReason-Nemotron 1.1](https://arxiv.org/abs/2506.13284) | Seven-point analysis of problem count and average answer count; training to a performance plateau. | Its coefficients are not dollar returns under our fixed supervision budget. |
| [DART-Math](https://arxiv.org/abs/2407.13690) | Difficulty-aware allocation of solution generation. | Compare a budget-capped difficulty baseline later; difficulty weighting itself is established. |
| [X-Coder](https://arxiv.org/abs/2601.06953) | Low-R fixed-pair allocation comparisons in code. | Our R=1/2/4 range is a practical diagnostic, not an unexplored axis. |
| [Reasoning Path Divergence](https://arxiv.org/abs/2510.26122) | Small-data random single-answer versus multi-answer comparisons with a small base student and QLoRA. | Small model/data/multiple answers alone is also prior work; the repeat control and acquisition contract matter. |
| [Data Repetition Beats Data Scaling](https://arxiv.org/abs/2602.11149) | Repetition and training exposure can change the value of nominal data scale. | An exact-answer repeat control and learning curves are necessary. |
| [Smaller, Weaker, Yet Better](https://arxiv.org/abs/2408.16737) | Generator quality and resource efficiency need not rank identically. | Fix one generator first, measure usable output per resource, and separate acquisition from student cost. |

The reading audit also covers label acquisition/relabeling, RPD, OpenThoughts, coverage loss, and strategically diverse sampling. No exhaustive absence-of-prior-work claim is made. In particular, coverage-mode experiments should not be rewritten as halving problem count, and GROOT's auxiliary planning costs have supplementary accounting that must not be omitted from criticism.

## Competing explanations and falsifiable expectations

1. **Useful multi-answer allocation:** Solutions outperforms Repeat on the same acquired parents under matched target tokens and updates. This supports the multi-answer retrieval/training policy over anchor repetition, but does not isolate new content from parent/answer weighting, structural diversity, wording, length or residual quality.
2. **Coverage dominates locally:** Breadth outperforms Solutions at approximately equal retained pair counts. This supports breadth for this bank/student/dose, not for all price ratios or tasks.
3. **Exposure explains most benefit:** Solutions and Repeat have a small, uncertain difference, or Repeat wins. Preserve the result; it weakens the immediate case for paying for more answers in this setting.
4. **Training or supply is the bottleneck:** all arms deteriorate, fail to learn, or usable multiple answers are too scarce. Use reference NLL, generated-answer diagnostics, supply attrition and dose curves to distinguish this from a scientific null.

A non-significant contrast does not establish equivalence. This small study will not certify a 1-percentage-point near-optimal region.

## Design and controls

### Bank, student and split

Use the existing C017 original GSM8K parent draw and four locked OpenMathInstruct-2 shards. Restore raw bytes from the pinned public sources; verify candidate identities and re-tokenize before admission. Do not silently replace missing questions or condition the main cohort on having four successful released answers.

- Student: fresh `Qwen/Qwen2.5-1.5B` **base**, revision `8faed761d45a263340a0528343f099c05c9a4323`; tokenizer same locked revision.
- Bank: OpenMathInstruct-2 revision `469216e3f46f4dacf476b382e192485ea51a143e`, shards 4, 7, 10, 16; GSM8K revision `3101c7d5072418e28b9008a6636bde82a006892c`.
- First adaptation candidate: fixed LoRA r16, alpha32, dropout0, q/k/v/o/gate/up/down projections, one optimizer recipe for all arms. This is still SFT; conclusions are conditional on this adaptation method. A full-parameter replication is later, not a mixed-method comparator.
- Serialization: `Problem: {problem}\nSolution:\n{answer}` plus supervised EOS; prompts/padding masked; no packing or truncation. Normalize summed response-token loss by all supervised targets in each update.
- Keep original question groups together across sources and train/dev/test. Numerical/near-duplicate audits do not prove semantic independence or absence from model pretraining.
- Do not initialize from prior overfit or Q2 checkpoints. The old 32-example full-SFT memorization experiment degraded development accuracy, so its training recipe is not imported as a default.

### Four-arm proposal

These are capped-bank retrieval policies over a parent order frozen before bank availability was inspected. They are **approximately**, not exactly, equal-inventory comparisons.

| Condition | Acquired problems | Requested retained answers/problem | Trainable problems | Actual unique retained pairs | Purpose |
|---|---:|---:|---:|---:|---|
| Repeat | 256 | 1 | 253 | 253 | Repeat the same anchor answers; same parent support as Solutions. |
| Solutions | 256 | up to 4 | 253 | 996 | Extra answer content within the same problem support. |
| Mixed | 512 | up to 2 | 508 | 1,011 | Intermediate breadth/depth. |
| Breadth | 1,024 | 1 | 1,013 | 1,013 | Broader acquired problem support. |

The three missing Repeat/Solutions parents and eleven missing Breadth parents stay in the acquisition denominator. Sampled-shard absence is not a failed teacher attempt. Different answer text is not a certified different strategy. Repeat's answer is an anchor retained in Solutions.

**Proposed common endpoint:** 524,288 supervised targets including EOS and 256 optimizer updates. Existing complete-answer schedules achieve both exactly with all retained pairs exposed; rows receive q or q+1 exposures. The final extra-exposure selection is length-dependent and is disclosed. Nonpadding processed tokens differ by about 0.67% across the eight schedules and are audited, not called identical compute.

**Replication:** training/order seeds 17 and 23, all four arms at each seed, one frozen procurement draw. Fresh base evaluation is an additional reference, not a trained allocation arm. Complete the three discriminating arms before optional analyses; prioritize the full two-seed four-arm study over a larger one-seed grid. Any resource-driven reduction is recorded before inspecting comparative scores.

**Recipe admission:** a bounded engineering profile uses already-observed development questions and 32 training examples. Initial candidate AdamW lr1e-4, betas(0.9,0.999), eps1e-8, no weight decay, norm clip1,16 warmup updates then cosine to1e-5 over the proposed256-update grid; the exact common LR vector and dependency versions must be frozen after profile and before the grid. Failure triggers diagnosis, not endless hyperparameter search. If the proposed dose is not operationally feasible, amend all arms before outcomes, not just the slowest arm.

### Evaluation

Primary endpoint: fixed greedy single-attempt exact numeric accuracy, with raw completions and parse/stop statuses retained. Use one fixed question roster and completion contract for base and every terminal checkpoint. Do not choose each arm's best checkpoint retrospectively.

C017 has 512 development parents. Original-ID inspection finds80 previously mentioned parents; normalized-question inspection additionally finds `gsm8k/train/05016` (development rank203) in a September Numina training input under another ID. The current candidate endpoint therefore has431 parents, not432. Prefer the previously observed80 for engineering and freeze the431-parent candidate endpoint after the documented exposure audit. These are development results, not guaranteed untouched confirmation: paraphrases and remote/private-only outputs remain unaudited. The new models start from the base checkpoint, so old experiment exposure is not asserted to be training exposure of the new student. Official GSM8K test is not used to choose the recipe or allocation.

Primary contrasts: Solutions minus Repeat, and Breadth minus Solutions at the terminal endpoint. Mixed and base comparisons are secondary. Learning diagnostics use training NLL and the same already-observed80-question set at updates64,128,256 in all arms; the main endpoint roster is evaluated only at the terminal state. These nodes describe progress, not checkpoint selection. Retain gained/lost question counts, generation length, termination, parsing failures and truncation. Sampled pass@k is secondary and runs only after a correct bounded sampled-stop implementation is tested. Equal k is not equal actual inference cost.

Report both seed values and their paired differences. Question bootstrap intervals condition on the trained runs and procurement draw; they are not confidence across training seeds or future problem pools. With two seeds, avoid strong population-level robustness claims. Reference NLL is diagnostic, not a scientific-success gate that selects arm-specific endpoints. Before a larger study, freeze a meaningful equivalence margin and calculate what sample size could support it.

### Metered teacher feasibility pilot

Candidate teacher: `Qwen/Qwen2.5-Math-1.5B-Instruct`, revision and dependency checks still to be locked. This is a separate source from the inventory bank. Do not silently substitute another model if its supply is poor.

Proposed bound: first128 acquired audit parents in the frozen order, at most8 candidates per parent (1,024 total), one fixed prompt/temperature/top-p/seed policy and a1,024-output-token ceiling per candidate. Check final-answer extraction on saved fixtures before new generation. Retain all attempts, including wrong, duplicate, parse-failed, length-capped and technical-failure records. No resampling to fill a quota beyond the cap. A 16-parent startup batch may diagnose engineering and throughput, then counts inside the same128-parent pilot; it is not a separate free pilot.

Measure attempts needed for first/second/fourth distinct accepted answers, failure/duplicate curves, length, output tokens, verification time, GPU and host time. Right-censored parents stay in the denominator. Teacher final-answer success does not certify the reasoning chain. Process-quality review, if used, has a separate time/cost record and cannot be called human gold when AI-assisted.

Use a request-level ledger with request and candidate IDs, source/model revisions, raw input/output hashes, sampling settings, stop reason, checker version, duplicate relation, selected status and resource measurements. Store historical bank prices as null/unknown. New-problem prices remain declared scenarios until a credible measured acquisition process is available. Do not call this pilot a dollar-optimal allocation result.

## Resource and execution plan

The authorized planning envelope is **$500 total**, not the additional displayed balance or unawarded future credits. At the checked Modal Functions list rate, A10080 plus4 physical CPU cores and32GiB RAM is approximately$2.9428/hour, so$500 is about170 container-hours before other costs. This is arithmetic, not measured throughput or an invoice. Request/actual resource billing and startup/idle overhead must be included. [Pricing](https://modal.com/pricing), [resource accounting](https://modal.com/docs/guide/resources).

| Stage | Spending ceiling, including failed attempts | Output and admission condition |
|---|---:|---|
| Environment, data, scoring, checkpoint profile | $20 | Fixed-source data audit, baseline parsing,32-example overfit, actual throughput and recovery verification. |
| Metered acquisition pilot | $40 | Complete attempt/acceptance/cost table; no hidden quota refill. |
| Main SFT | $160 | Source-published, reviewed and frozen four-arm queue. |
| Evaluation and independent result audit | $70 | Common endpoint, raw outputs, denominators, hashes and paired contrasts. |
| Key confirmation or bounded repair | $60 | Complete planned key replication; no silent extra grid or lost-dose reset. |
| Report-stage follow-up after midpoint | $100 | Address the most material feedback before October22. |
| Unallocated reserve | $50 | Not a target to spend. |
| **Total** | **$500** | **At most$350 for the initial presentation work.** |

The old A800 projection suggested roughly70–72 minutes of training for eight524k-token runs, excluding evaluation and all overhead. It is neither a Modal measurement nor a promise. The envelope is deliberately larger than that estimate. Replace the estimate with one measured pilot before admitting the entire queue. At most two independent single-GPU runs concurrently; start with one. Do not use distributed multi-GPU training for this small student.

Use CPU tasks for downloads and persistent storage for public weights. GitHub contains code/manifests, not ignored model/data binaries. Approximately969MB of locked source data plus a3.09GB base model can be acquired from public sources; this study does not require an AutoDL restart. Preserve old unique checkpoints on the stopped server.

### Reliability is an admission criterion, not another research variable

- Use finite ephemeral batch apps, no continuously deployed GPU endpoint; zero minimum containers and short bounded scaledown. At completion verify app/container exit and collect outputs. Modal scale-to-zero replaces AutoDL's provider power-off operation.
- Pin source/config/data hashes and issue one immutable run intent before compute. Each physical attempt and failed admission is separately accounted for. An ambiguous prior attempt is not safe to replay.
- `retries=0` does not prevent provider crash/preemption rescheduling. Use atomic put-if-absent run admission, not a Volume lockfile, and an absolute deadline. A claim is never silently released or reused. [Retries](https://modal.com/docs/guide/retries), [preemption](https://modal.com/docs/guide/preemption).
- Distributed claim entries expire after inactivity; the finite campaign deadline must precede expiry. A planned child run after failure needs reconciled dose, a separate reserved budget and an immutable parent reference. Do not reset the monetary window.
- Save model/adapter, optimizer, LR schedule, row cursor, update count, Python/NumPy/Torch/CUDA RNG and cumulative dose. Checkpoint manifests must bind all components and their hashes.
- Verify local save/load numerics, an actual mounted-volume commit/read round trip, and one real-model uninterrupted-versus-resumed short sequence before claiming recovery. Deterministic agreement has a stated scope and tolerance; it is not proof for every future kernel/platform.
- Immutable raw outputs, saved batches, update intents and completion receipts distinguish committed, attempted and ambiguous work. Preserve partial and negative results. Independent verification occurs before deleting or replacing any required copy; this plan authorizes no deletion.
- Record resource estimates separately from provider billing. Workspace usage cap and net-spend cap are separate platform controls to verify; no setting has yet been claimed applied. No paid upgrade is needed.

## Short and long horizon

All planning times below are America/Los_Angeles, not UTC.

| Date | Work and concrete deliverable |
|---|---|
| Sun Oct11 evening–Mon Oct12 | Notes/rubric audit, data reconstruction, local correctness checks, Modal authentication and CPU/GPU platform profile. Freeze recipe after the finite profile. |
| Mon Oct12–Tue Oct13 | Complete the four conditions and paired seeds, plus the bounded teacher-cost pilot. Target first interpretable result table Tuesday evening. |
| Wed Oct14 | Reconcile ledgers/checkpoints and raw scoring; finalize tables/plots, rehearse10-minute talk; only bounded repairs or a predeclared decisive check. No new broad search. |
| Thu Oct15 afternoon | Present verified results and limits, with5-minute Q&A. Freeze scientific slides by noon unless the actual slot requires earlier. |
| Oct16–22 | Address feedback; same-source cost-performance test or fresh procurement draw as the most important missing evidence; submit4-page COLM report byOct22,17:59PT. |
| Late Oct–Nov | Budget-size sensitivity, fixed-ratio and difficulty-aware baselines under the same cap, frozen decision on fresh procurement draws; expand only the decisive conditions. |
| Before Dec14 | Key three-seed replication if affordable, second-model/task boundary check if justified, publish honest scope and reproducibility records. Do not rely on future credit awards. |

If the first results are flat, first distinguish inadequate learning dose, saturation, data supply, and true limited allocation sensitivity. Low teacher yield is reported from the fixed pilot; do not silently replace parents or attempts to improve it. It informs later scope and does not invalidate a different-source bank comparison. An inconclusive but well-controlled bank result plus a complete cost/supply audit is useful feasibility evidence. It is not an incentive to manufacture a winning ratio through selective prices or checkpoints.

## Midpoint presentation and report

The presentation is10 minutes plus5 minutes Q&A. Allocate the first5 minutes to the real purchasing decision, closest precedents, and the scientific comparison; the last5 to actual supply/learning/cost evidence, its limitations, and the next decision. Target8–9 main slides and backup details. Minimum result artifacts: a four-arm accuracy table, an exposure/token/update audit, a multi-answer-versus-repeat contrast, and an attempts/usable-answer/cost figure. Never fill a plot with expected outcomes.

The rubric weights motivation/context, feasibility evidence and clarity equally at4% each, and next steps at3%. Negative results are acceptable when sufficient evidence explains the bottleneck. A successful smoke test alone does not establish scientific feasibility. [Official rubric](https://docs.google.com/document/d/e/2PACX-1vTCIeWZj4vxhtk9SVzGEtYl6F7ygdVkoJpL2VT8PEFgJYclQDC5giexg8s3WGitIrOIp9CHrB19ua5M/pub).

The report uses the unmodified [COLM2026 template](https://github.com/COLM-org/Template/releases/tag/2026), maximum4 main pages excluding references. Include Abstract, Introduction, Related work, Proposed approach, Preliminary results, Plans for the rest of the semester, Contribution statement and References. The course4-page limit overrides the conference's length allowance. Contributions distinguish the solo student's scientific decisions and verification from AI-assisted preparation and implementation; do not imply external collaborators or human annotations that did not occur. [Course project requirements](https://www.sewonmin.com/courses/cs294_288/project/).

## Evidence, reflection and next decision

Completed preparation:28 supplied reading-note files were retrieved, hash-verified and read in full at one pinned Git commit; separate primary-paper spot checks are recorded in the private review. This is not28 newly completed original-paper replications or full-paper reads. Official rubric/template/pricing were checked. CPU reconstruction recovered21,292 original parents and15,837 candidate records byte-exactly; an independent verifier re-enumerated1,746,600 released rows and re-tokenized15,308 accepted responses. Eight complete-answer schedules match their archived hashes and budgets. See the [readiness record](../../reports/sft_allocation_midpoint_20261011/READINESS.md). No new model effect, optimal allocation, acquisition price or GPU runtime has been measured in this plan.

For every run, use the repository experiment record format: motivation; competing explanations; frozen plan and estimate; immutable actual dose/output/cost; failures; interpretation; next decision. Preserve oldQ2/LT002 closeouts. The initial main-grid review concerns the four-arm proposal, fixed adaptation method, endpoint and paired seeds; engineering/data preparation can proceed independently. Later policy/price/teacher changes require an explicit scientific amendment rather than being hidden inside a repair.
