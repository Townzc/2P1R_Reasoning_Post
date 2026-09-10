# Decisions and open questions

## D025 — 2026-09-10: plan from literature and total rental time

The owner clarified that rental billing starts at power-on, including idle and
CPU work, and requested broader ICLR/ACL ideas. Keep the existing process guard
unchanged and add separate rental-time/money accounting. E014's 170-second
process charge must not stand in for its observed 34.39-minute orchestration
span; provider start/stop times and actual charges remain unknown.

Inspect eleven full-paper methods/ablations/setups and run C018 on local CPU.
Shorter-only filtering substantially loses parents; surface-diverse selection
is feasible at fixed P/K but establishes no learning gain. Prior work already
covers breadth, multiple rationales, variable K and selection; do not claim
novelty from those labels or a cost equation alone.

Replace default 512-update scaling with a review-only 256-update terminal-LR
repair, preserving all other E013 training factors and the original gate.
Keep the old proposal unchanged as a fallback. A three-arm allocation minimum,
then conditional selection/curriculum/model/objective checks, needs independent
capability and complete-budget gates. No automatic next run or new allowance.
No server contact/model call was made; ledger stays 6,467 used / 733 left.
See [P005](experiments/P005_literature_guided_next_phase.md) and
[rental workflow](RENTAL_WALL_CLOCK.md).

## D024 — 2026-09-10: retain E014 diagnosis and defer scientific scale

E014 completes fromd78aa77 with32/32 exact raw replays and no selected-case
repair at batch1. All27 queried first differences prefer the generated token;
17 reference targets lose top-one across12 rows, despite NLL0.014206. All32
reference EOS targets win, which does not measure EOS on generated loops.
Retain E013's failed gate and the observed batch sensitivity without claiming
a causal software bug. Both raw-record audits and55 Linux tests pass.

Charge170 seconds;18 receipts reconcile to6467 used /733 left,zero reservations.
Original weights remain independently preserved and rehashed. No next job is
queued. Prepare a review-only512-update fresh-base calibration with the same
32 rows and original score/decoder; proposed600+15 cap fits but its12GiB free
checkpoint-preservation gate is unmet at6.29GiB. No promised repair, new budget,
training sweep or scientific comparison follows. See
[results](../reports/REAL_MATH_E014_RESULTS.md) and the separate E015 proposal.

## D023 — 2026-09-10: repair CPU audit overhead before the authorized E014 launch

The owner restored the existing A800 specifically for E014. Published source
5f7a417 passed all54 Linux tests, but CPU-only inspection exceeded45 seconds;
a profiled180-second check also timed out while repeatedly computing tokenizer
length in the unchanged E013 auditor. Sixteen length calls took0.364809 seconds
and all returned151665. No E014 run directory, reservation or model call exists;
the17-receipt ledger remains6297 used /903 left.

Before any model execution, add an audit-only tokenizer view that snapshots
vocabulary size once and delegates decoding/EOS to the original tokenizer.
Keep the E013 auditor, generator and every src/scripts file byte-identical.
Equivalence fixtures check accepted records and invalid token/type/EOS/text/score
rejections.53 local tests pass; two GNU-timeout checks await the amended Linux
suite. Preserve both CPU timeouts and r1 inputs; prepare an immutable r2 source
release. Verify r2 cases and CPU evidence against r1 before launch. The run ID,
model, prompts, selection, reference queries and360+15-second bound stay fixed.
This changes CPU audit cost, not the experiment or its scoring, and is completed
under the owner's execution request. Max remains the recommendation.

## D022 — 2026-09-10: diagnose the saved checkpoint before another training run

The owner requested local inspection of E013 generation anomalies, preparation
of the subsequent experiment, and notice when the existing server is required.
Prepare [E014](experiments/E014_generation_diagnostic.md): original32-parent
batch8 replay, all eight failed cases plus two fixed successful controls at
batch1, and all32 teacher-forced token/EOS records with selected first-divergence
queries. Preserve the original decoder, source, weights, labels and scores.
This is an inference diagnostic with a360-second process cap plus15-second
guard, leaving528 of the existing903 seconds unreserved; no training or new
allowance is approved. A supplied A800 for this phase permits this single
prepared diagnostic, not automatic old-queue or scientific-grid execution.

The implementation lives outside the frozen E013 src/scripts set.52 component
and tiny-random-model CPU tests pass; two GNU-timeout integrations remain
mandatory on Linux. A separately attempted historical E011 input regression
correctly rejects the pre-existing C017 sft_data change; retain that failure
and the old guard. Input materialization and clean-release verification follow
source publication. No pretrained model, GPU, server contact or reservation
occurred at this source milestone. Max is recommended; no setting is changed.

D022 CPU release outcome: published source3dd0034 and releasee79a0e1 pass
independent token/position/source verification and default CPU inspection. All32
parents,5226 reference targets and12 checkpoint files verify. All17 receipts
remain reconciled at6297 used /903 left. The concrete release and decision table
are complete; request the existing owner-started A800 for this single diagnostic.
See [readiness](../reports/REAL_MATH_E014_READY.md).

## D021 — 2026-09-10: retain failed E013; defer scientific scale

The owner restored the existing server. The fixed E013 trajectory completed
and all raw-record/dose checks pass, but its overfit gate fails:24/32 correct
terminated train answers, five truncations, three wrong numeric finals. Low
teacher-forced NLL does not establish reliable free generation. Baseline output
format limits interpretation of its strict0/16 development score.

Retain the frozen metrics and failed checkpoint; do not add updates, relax
the scorer, extend the cap, replace parents or auto-retry. Diagnose generation
and evaluation before setting a launchable scientific scale. The current
four-arm training-only proxy (2096–2165 seconds) also exceeds the903-second
remaining allowance. All17 receipts reconcile, with6297 seconds used and no
reservation. No new GPU stage or allowance is approved by this result.
See [E013 results](../reports/REAL_MATH_E013_RESULTS.md).

## D020 — 2026-09-10: begin finite real-data engineering before scaling

The owner asked to start the next experiment. Prepare and run one E013 GSM8K
engineering trajectory on the existing authorized A800 if available, with the
unchanged cumulative ledger. Freeze C017's 32 selected responses and the first
16 development ranks; 256 fixed updates, numeric/EOS/NLL gate, 900-second process
cap plus 15-second guard. Publish code before preparation and immutable inputs
before launch. Do not restart the paused E012 ladder or infer authorization for
the four-arm grid, new teacher generation, rentals or an extra allowance.
Max is recommended for this bounded implementation task; no setting is changed.
See [E013 registration](experiments/E013_gsm8k_engineering.md).

## D019 — 2026-09-10: execute C017 CPU audit, propose a measured small scale

The owner authorized the next CPU source/split, coverage and attrition audit
following P004. C017 freezes parent draws before capped solution retrieval,
retains mirror/partition/parser failures, and verifies acquired denominators,
complete-response tokens and corrected filtering outcomes. Read
[the results](../reports/REAL_MATH_CPU_AUDIT_20260910.md).

Data support a proposed four-condition GSM8K study with P up to1,024 and K up
to4. Exact CPU schedules use524,288 supervised tokens and256 updates per arm;
actual unique-pair and exposure differences are explicit. This is a concrete
proposal requiring scientific review and a real-data32-example overfit/profile
before pricing/launch. It is not approval to execute eight model jobs or
reopen E012. No GPU, teacher, server, additional budget or external message.
The original ledger remains5971/7200 used,1229 left,16 receipts,zero reservations.

## D001 — 2026-09-05 UTC: public reproducible workspace
The user requested starting the agreed project and updating the provided GitHub repository after code and experiments. Import only code and synthetic fixtures; keep private handoffs and connection information outside the public repository.

## D002 — 2026-09-05 UTC: bounded initial compute
The user approved 2 GPU-hours (7200 process-seconds on one GPU) for first-stage checks and feasible pilots. Instance idle billing is separate. Record and enforce cumulative job time. Do not automatically rent another GPU.

## D003 — engineering recipe, not a scientific result
Use the already selected 0.5B base model for correctness/debugging with FP32 trainable parameters and BF16 autocast. The intended 1.5B base remains the main candidate. No switch to LoRA or lower-precision optimizer state is implied by a memory failure.

## D004 — 2026-09-05 UTC: owner-provided A800 continuation
The owner supplied a new A800 server and requested continuation of the planned experiments. Continue the existing 7200-second cumulative budget, carrying forward 737 seconds already charged. First repeat the unchanged 1.5B memory profile, then run the 32-example engineering gate at the previously debugged LR 5e-5. Capture greedy and four-sample development performance before and after adaptation. This does not settle the still-open scientific arm/domain definitions. The A800 hourly price is not known; do not apply the old 4090 reference price to A800 runtime.

## D005 — 2026-09-08: approved staged pilot preparation

The owner approved the proposed sequence: finish data/control preparation locally,
then A800 calibration, then one paired-seed four-arm pilot if calibration and cost
permit. The owner will supply a replacement A800 when needed. Routine CPU design
choices are specified in PILOT_V1.md: expanded raw number domain, presolver splits,
exact shared-block schedules, sentence-frame Surface control, and a common four-cycle
dose. The existing 7200-second cumulative budget remains unchanged. Main-grid,
additional seeds and holdout evaluation remain later decisions.

The owner also suggested karpathy/autoresearch as a reference. Adapt its compact,
bounded iteration and fixed-evaluation workflow to this causal comparison. Retain
all attempted runs in Git; use token/update matching plus finite runtime ceilings.
No open-ended autonomous optimization or extra spending is implied.

## D006 — 2026-09-09 UTC: ICLR evidence review and fixed next-pair preparation

The owner asked to continue, prepare the next experimental idea, then tell them
when to start or rent a replacement server; the goal is ICLR with efficiency and
quality. Codex prepared seed23 Paths/GCM on CPU, retaining the selected problems,
base model, training recipe, 1024 updates and exact token/structure matching.
Assignment/order/training use seed23 while evaluation keeps seed17. The proposed
pair reserves 2130 of the 3488 remaining seconds under the original budget.
No prior server was contacted and no GPU work or additional rental occurred.

Independent intermediate-step and identity-operation audits are post hoc for
seed17 and fixed secondary diagnostics for seed23. They do not replace greedy
final-expression correctness. Recent prior work directly overlaps the broad
question; the new roadmap requires a substantive controlled boundary study,
independent pools/seeds and broader evaluation before any strong paper claim.
The next pair is a limited stability gate. The owner will supply/start the
instance after reviewing this concrete next phase; the later roadmap remains a
design and budget decision, not an open-ended training authorization.

## D007 — 2026-09-09 UTC: supplied A800, fixed pair and explicit research journal

The owner supplied a replacement A800 for the prepared seed23 pair and requested
separate records of attempted ideas, motivations, experiment designs, results
and interpretation, followed by a current assessment and local/GitHub paths.
The owner also authorized removal of unneeded old server files given a 50 GB
data disk. All 48 old scientific checkpoint files were independently SHA-256
verified locally and remotely before deleting only the redundant remote
checkpoint directories; code, predictions, manifests and local backups remain.
The data filesystem now has about 41.16 GiB free, so no expansion is needed for
this pair. All 96 Linux tests, nine pinned model-file checks, frozen-data checks
and the 3712-second ledger match passed on the supplied instance.

Execute only the published seed23 Paths/GCM comparison under the original
cumulative budget and full-phase guard. The execution code is the verified
`6128e4266d62f14f063585d4c8e94dbe3ad8c711` milestone. The new
RESEARCH_JOURNAL.md and experiments/E009_seed23_paired_replication.md record
the reasoning before any seed23 output; historical entries are explicitly
retrospective reconstructions. No broader grid or additional budget is implied.

### D007 completion update — results verified, weight transfer in progress

Both arms completed from the fixed source with no retries: primary Paths/GCM
22/64 versus 17/64; complete traces 18/64 versus 16/64; broader final expressions
1/64 each and complete traces 0/64 versus 1/64. All 800 predictions were audited.
The phase charged 1004 seconds; the independent ledger matches all 13 receipts,
4716/7200 used, 2484 remaining and no unresolved reservation. Weight downloads
remain pending at this results milestone; do not discard the instance yet.

Keep the primary fixed-pool stability finding; do not claim a mechanism or
broader transfer. CPU exposure and shared-support failures are separate A003/C007
entries. The next decision is a defined legal-path-family construction, not
another seed or a larger-model grid. See reports/PILOT_REPLICATION_SEED23_RESULTS.md
and docs/RESEARCH_JOURNAL.md (repository-relative paths).

### D007 preservation completion

Both new checkpoints are independently SHA-256 verified: 24 files and
12,381,607,162 bytes. The compact results are published at
`a4edae0817c72c11481ce0f7536952500a8e1e02`; the ledger is reconciled and no GPU
job/reservation remains. Final recovery synchronization follows publication of
these completion records. No additional GPU phase is queued.

## D008 — 2026-09-09 UTC: bounded local CPU support census

During checkpoint transfer, the P002/C008 plan and census implementation were
published as `b504cb7b604847b2155bb71dd2bb2c3602d9f371` before enumerating the
256 already public training questions. All 1,966,080 ordered candidates were
checked; 25,846 legal solutions and every stored reference were recovered.
Disjoint-AC 2+2 and 4+4 support is 132/256 and 131/256 respectively. This resolves
part of the selected-inventory uncertainty but cannot supply the full original
256-problem 4+4 experiment. The proposed next gate is fixed CPU token/structure/
block matching, with declared cardinality and retention; not automatic training.
No new problem pool, development/holdout inference or GPU spending occurred.

## RESOLVED FOR PILOT V1 — coverage matching and exposure budget
The updated condition table specifies one path and one exposure on a fixed problem set. At comparable response lengths this has fewer supervised tokens than the multi-path condition. A concrete matched-exposure proposal, structural-frequency residuals and length audit must be reviewed before launching this decisive scientific comparison.

Pilot v1 uses four exposures per problem per cycle in every arm, including GCM,
and demonstrates exact per-example token and per-update Paths/GCM structure matching.
See PILOT_V1.md and the immutable matching audit. The earlier issue is retained
above to explain why the original one-exposure row was not implemented.

## RESOLVED FOR PILOT V1 — main data domain
Four distinct inputs in 1..20 yield at most C(20,4)=4845 groups before eligibility filtering. A 4096-problem breadth pool plus large disjoint holdouts does not fit comfortably. Keep the present data engineering-only; review an expanded domain or task design before creating final splits.

Pilot v1 expands to 1..40 and assigns 4096 train, 2048 development and 2048
reserved holdout raw groups before solving. It is a restricted pilot, with large
selection shifts reported explicitly, not the final broad benchmark.


## D009 — 2026-09-09 UTC: measure matching loss; stop after bounded search

The owner requested the next planned round, review of prior failures and notice
if storage expansion is needed. C009 was frozen and published before its local
CPU execution. Complete question-level support is 131 raw, 67 token-matched and
66 structure-feasible. Global key discovery reached the two-million-pair cap;
681 keys/seven questions/one block are found witnesses, not total capacity.
Preserve that incomplete result without increasing caps in the same attempt.
Next prepare a complete CPU join and selection audit before any reduced-pool
training proposal. No additional model inference, GPU charge or expansion occurred.

The owner also explicitly authorized automatic shutdown of the current project
instance after this round. A task heartbeat was configured as a backstop. Stop
only the verified instance after publication and recovery checks, confirm actual
provider stopped state, and disable the backstop. This does not authorize a
new server, deletion, release, or automatically resuming a later experiment.
The prior seed23 recovery/Git closeout was aligned at `fc96885c`; CPU artifacts
can be restored from newer Git history after shutdown. GPU ledger remains 4716
used and 2484 remaining; no unverified final shutdown state is implied here.


### C009 shutdown completion — 2026-09-09 07:37 UTC

After C009 result publication at `f52d7228fe18bd9667030725348234c790cc7883`
and local/Git tree verification, the owner-authorized normal shutdown was
confirmed in the authenticated provider console as “已关机”. The instance
identity matched the previous run and the confirmation dialog. A fresh remote
check immediately before shutdown found no active GPU/training process, no
reservation and the unchanged 4716-second ledger. No instance was deleted or
started. The task heartbeat backstop was then paused; no further GPU job is
queued. See [closeout receipt](../reports/c009_shutdown_closeout.json).


## D010 —2026-09-09: remove irrelevant family selection; prepare a fixed boundary pair

Before CPU outcome counts, C012 chose identity_absent-only Paths/GCM with
selection/assignment/order/training seed31, evaluation17,32-block then16-block
scale tiers,1024 complete updates, and the original recipe. Requiring present
paths and cross-family equality has no control role for this two-arm contrast.
Keep all within-family/exposure/structure checks. This removes avoidable
screening; it does not restore the original256-question population.

C011 found common-class67/common-structure66 versus separate-family-class129/
separate-family-structure84; high targets vanish again with the two-family
structure requirement. C010 retained a600-second incomplete failure. C013's
new compact exact Hall-bitset algorithm completed all48,429,084 pairs in4.833s,
with1,019,005 keys,63 supported questions and15 optimal blocks. Do not relabel
C010 complete or infer capacity from its search prefix.

C012 independently completes74,764 local combinations,4,182 shared keys,
138 supported questions and33 optimal blocks. Follow the frozen Random31
selection rule to use32 blocks/128 questions. Prepare only Paths/GCM, each with
277760 supervised tokens,482848 nonpadding tokens,3734 padding,1024 updates.
Independent CPU checks pass; retain selection and numerical-exposure residuals.
The new pair estimates allocation on this selected population, not a causal
identity-removal effect or a direct comparison to the old256-question models.

Queue2130 seconds against the retained2484 balance, without raising the7200
allowance. It is prepared, not executed. The user will provide/start tomorrow's
A800; verify current Git, ledger, base model, idle GPU and18GiB free first.
See ABSENT_BOUNDARY_TRAINING.md, NEXT_SESSION.md and the complete research report.

## D011 —2026-09-09: retain the weak boundary result; pause scientific scaling

The owner explicitly authorized E010 on the restarted A800. The frozen pair
completed without GPU failure, retry or recipe changes. Primary matched greedy
is7/64 versus5/64; complete traces4/64 each; broader expressions/traces0/64
versus2/64. All800 outputs passed independent server/local CPU audits with
byte-identical reports. These endpoint-dependent outcomes do not support
expanding a general path-diversity claim or an identity-removal mechanism.
They also do not establish zero effect from this one small selected population.

Retain all results and the pre-outcome registration. Propose CPU task/estimand
construction, support/difficulty/shortcut audits and a small falsifiable design
for owner review before another scientific phase. Do not turn the development
endpoint into a seed or hyperparameter search. The cumulative ledger is5740
used,1460 remaining,15 verified receipts and zero reservations; this cannot
reserve another current2130-second pair. Complete independent preservation
and the already authorized normal shutdown. See
[E010 results](../reports/ABSENT_BOUNDARY_SEED31_RESULTS.md).

## D012 —2026-09-09: separate evidence routes from strategies; audit before training

The owner requested an immediate review of construction and controls. Three
independent reviews and a coordinating consistency check reject adding more
arithmetic seeds as the next step. C009–C013 establish the cost of support
selection; E010 supplies weak, endpoint-dependent allocation evidence rather
than a causal identity-removal result.

Select a single CPU falsification candidate: latent-permutation relation
transport with four equal-length routes. Its mathematically guaranteed support
and uniform population labels avoid two failures of naive constructions.
The routes are automorphic instances of one algorithm, so the claim is
evidence-route allocation, not semantic strategy diversity. Exact route-slot
matching also does not equalize every realized state/table exposure.

The concrete proposal has a multi-route/repeated-route schedule, complete
certificate scoring, useful versus irrelevant evidence deletion, coherent
counterfactuals, world-level splits and CPU rejection gates. Passing these
would establish implementation feasibility, not novelty or ICLR readiness.
No data was generated and no new scientific GPU protocol is approved by this
review. See [P003](experiments/P003_task_and_control_redesign.md) and
[the integrated proposal](CONTROL_REDESIGN_PROPOSAL_20260909.md).

Separately, the authenticated provider console confirmed the exact E010
instance as stopped at approximately20:00 UTC, after previously verified
preservation. The confirmation heartbeat is paused. No instance was started,
deleted or released; cumulative GPU accounting remains5740 used/1460 remaining.

## D013 —2026-09-09: CPU construction passes; prepare engineering, not scaling

The owner authorized the next CPU stage. C014 ran from prepublished clean
source6c24d4c and retained all10,000 intended worlds. Independent exposed-table
solving, gold/negative/counterfactual checks, exact token budgets and conservative
world grouping passed. Eight predefined CPU predictors across five views
triggered no corrected test; this does not prove every shortcut absent.
Independent archive verification reconciled all40,000 clean references,
50,000 view prompts and80,000 predictions.

The new1137-token serialization needs its own32-example overfit/profile gate.
Prepare an executable bounded runner and concrete cost proposal before asking
for a server. No new GPU experiment or allowance is implied. Do not relabel
the CPU sandbox as a final test or the accounting schedule as a training plan.
Retain state/table-exposure residuals and the one-algorithm/one-topology scope.
See [C014 results](../reports/RELATION_TRANSPORT_C014_RESULTS.md). Ledger stays
5740/7200 used,1460 remaining,zero reservations; server was not contacted.

## D014 —2026-09-09: one fixed engineering trajectory before a scientific proposal

The owner asked to prepare the next step and signal when a server is needed.
Prepare C015/E011 locally: fixed C014 seed prefixes,32 training/16 diagnostic
parents, unchanged pinned1.5B full-parameter recipe,256 updates and96 greedy
outputs including the16-output baseline. All four routes are exposed eight
times in training. Strict complete-proof scoring distinguishes a correct final
state from a verified, EOS-terminated derivation. No output-driven selection
or automatic retries. The32/32 plus NLL/profile gate tests engineering only.

Reserve at most735 seconds only when actually launching on the owner's A800,
within the1460 remaining original budget. Source and compact data must be
published first. The budget guard now supports optional exact-ledger and full-
cap checks under its lock, closing the inspection-to-reservation race without
changing historical callers. No GPU spending/reservation is added by this
source milestone. See [E011 registration](experiments/E011_relation_engineering.md).


D014 implementation outcome: C015 extraction and independent re-verification
pass with all48 selected worlds retained; the exact256-update/103424-token
engineering release is ready.40 local tests pass;2 GNU-timeout integrations
await Linux. Request the owner-started A800 after publishing the complete release.
No GPU outcome,new allowance,reservation or scientific comparison is implied.


## D015 —2026-09-09: stop at the failed relation engineering gate

E011's complete dose yields0/32 complete train proofs and0/16 per dev view.
All333 parseable generated step results are2;mean NLL.119 does not indicate
learned table computation. Independent96-output audits agree exactly. Keep
the frozen failure and do not scale a scientific comparison. Prepare CPU
diagnostics separating reference multimodality,provided-route propagation
and basic lookup;these are prospective engineering tests,not established
causal explanations. No new GPU run is authorized automatically. Current
5971/7200 used,1229 left;all checkpoints/receipts preserved for shutdown.


## D016 — 2026-09-09: prepare a diagnostic ladder on CPU, preserve E011

The owner approved CPU preparation of single-step lookup, supplied-route
propagation and fixed-reference diagnostics. Keep all original 32 training and
16 observed dev parents. Recover the training anchor from E011 round zero;
retain all four assigned-route operations, without output-driven filtering.
The full fixed-reference arm keeps original prompts and exactly matched update,
parent and token dose. Given-route keeps all 32 edges and the same target,
adding only an oriented path hint. One-edge lookup changes context/target
length and per-operation repetitions; it is a capability gate, not a matched
treatment effect. Dev groups remain an observed sandbox and tables can repeat.

Prepare strict route-aware scoring, parent denominators, field-wise target
measurements and all-line lookup diagnostics so truncation and low mean NLL
cannot mask semantic failure. The proposed later order is lookup, route given,
full fixed reference, with fresh base weights and no continuation past failure.
Three 360-second caps plus guards fit within 1229 seconds, but this is a
reviewable proposal only: no GPU runner, job, reservation or server contact is
authorized by this CPU request. See the frozen
[construction and interpretation plan](experiments/C016_relation_diagnostics.md).

D016 CPU outcome: all288 rows retained and independently verified;53 focused
tests pass in the published clean checkout. Sourcef073955 preceded generation,
data4a5ad97 preceded fresh-checkout verification. Fixed-reference accounting
matches E011 exactly; supplied route adds86 prompt tokens. State2 is31/128
training step labels, and train/dev share34 tables and13 table/input operations.
Retain these finite imbalances/overlaps, with no new filtering or generalization
claim. The data release is complete; the GPU runner/raw-output auditor remains
a separate CPU implementation before startup review. Ledger unchanged5971 used.
See [C016 CPU results](../reports/RELATION_C016_CPU_READY.md).


## D017 — 2026-09-09: execute the reviewed finite diagnostic ladder

The owner requested the next experiment after C016 and reported switching to
Max. Implement E012 with the frozen lookup / given-route / fixed-reference
sequence, fresh original base for each stage,256 updates each and no automatic
retry or continuation past a failed gate. The prior concrete1125-second maximum
reservation plan fits1229 remaining; this is within existing authorization.
Prepare/publish the runtime release before asking for server startup.

Raw-token scores, exact update indices and per-target CE/top-one records must
be independently reconciled. Separate completed learning failure from incomplete
execution, and preserve both. Unknown padded-vocabulary outputs are retained
as proof failures. Add the E011 result to stale registry/accounting summaries
without altering the actual ledger or treating a failed gate as success.
See [E012 registration](experiments/E012_relation_diagnostic_ladder.md).


D017 implementation outcome — 2026-09-10 UTC: source `1fc27d4` and immutable
release `27a0943` are published. Clean-checkout default inspection and 76 CPU
checks pass; 2 GNU-timeout integrations remain mandatory on Linux. Request an
owner-started A800 now that the reviewable execution release is complete.
No E012 model run, new allowance, server contact or reservation occurred.
The current 16-receipt ledger remains 5971 used / 1229 left; the two previously
stale aggregate summaries now include E011's existing failed-gate result.
The conditional sequence and failure stopping rule are unchanged. See
[ready report](../reports/RELATION_E012_READY.md).


## D018 — 2026-09-10: respond to framing questions before more experiments

The owner asked to resolve the project question and concrete deliverables first.
Pause E012 execution while preparing a reply. P004 proposes treating asymmetric
problem/solution acquisition costs as the primary SFT allocation question;
structural diversity and exact repetition become targeted explanations/controls.
Use P for acquired problems, K for target usable solutions, E for training
exposure; preserve historical labels. Measured generation/verification costs
must remain distinct from hypothetical problem-acquisition prices and sunk
public-dataset creation costs. Count rejected and duplicate outputs, selection
loss and calibration overhead. Do not assume more problems always wins or claim
that a cost equation itself establishes novelty.

Proposed initial assets are Qwen2.5-1.5B base, GSM8K and a fixed math-specialized
7B teacher; OLMo2-1B is the proposed second-family check. This is a reviewable
scientific proposal and unsent private reply, not a change to frozen experimental
sources or permission to execute its grid. No GPU/model/server action or ledger
change occurred. See [P004](experiments/P004_cost_aware_sft_allocation_proposal.md).


D018 evidence clarification: retain Qwen2.5-1.5B as the first real-task calibration
candidate because its synthetic/A800 stack is measured, not because generalization
or cost optimality has been demonstrated. Math7B teacher selection and OLMo1B
replication are conditional on their own unrun capability/cost checks. The
initial reply overstated readiness through omission; the revised private bilingual
version states prior failures and prospective status. Keep the grid tentative
until profiling. See [model rationale](../reports/MODEL_SELECTION_EVIDENCE_20260910.md).

D018 compute constraint: the owner explicitly rules out compute-heavy model
plans. Recheck the original three papers and later related work, distinguishing
small students from large teachers and expensive long-trace evaluation. Keep
Qwen1.5B as the primary calibration candidate and OLMo1B as a conditional
second family. Remove Math7B as the default teacher and from the minimum plan;
audit reusable solutions and consider bounded Math1.5B-Instruct calibration.
Neither route is validated, and public cached outputs without attempt/cost logs
cannot establish measured generation price. Preserve the historical rationale,
paused E012 release and existing allowance. See
[paper/model/compute evidence](../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md).

D018 data-scope clarification: the earlier GSM8K-only draft did not adequately
specify a second real problem distribution. Propose MATH levels 1–3 with
subject/difficulty stratification for decisive validation after feasibility and
original-split verification. Audit OpenMathInstruct-2 as an output source, not
an independent third task; GSM-Symbolic stays evaluation-only because it derives
from GSM8K test parents. Problem pools precede solution-success inspection.
Cached accepted outputs cannot establish generation costs, and a different
small teacher cannot price them. This review changes no frozen protocol or
resource allowance. See the
[dataset evidence review](../reports/DATASET_SELECTION_EVIDENCE_20260910.md).
