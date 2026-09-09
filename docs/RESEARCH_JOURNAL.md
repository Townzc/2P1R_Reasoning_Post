# Research journal

This index records the question, motivation, competing explanation, design,
outcome and decision for each substantive attempt. It complements the
[machine-readable run registry](../reports/run_registry.json),
[current status](../reports/STATUS.md) and [resource accounting](../reports/compute_accounting.json).
Raw run artifacts remain the authority for numerical claims.

The historical entries below were reconstructed on 2026-09-09 from existing
records. Their explanatory questions are retrospective summaries, not claims
that a formal preregistration existed before those runs. Explicit post-hoc
analyses stay post hoc. A proposal is not an attempted or successful experiment.
Budget figures inside completed entries are historical charges, not the current
balance. Dates are UTC unless specified otherwise.

## Attempted work and completed analyses

Latest completed experiment: [E010](experiments/E010_absent_boundary_seed31.md),
the frozen C012 Paths/GCM seed31 pair. Matched greedy is7/64 versus5/64,
complete traces4/64 each, broader expressions/traces0/64 versus2/64. All800
outputs and exact full doses passed independent CPU audits. This weak boundary
result does not justify scaling; prepare a CPU task/estimand review. The result
report separates completed execution from checkpoint/shutdown preservation.

| ID | Work date | Question or attempted change | Status | Outcome / decision |
|---|---|---|---|---|
| [C000](experiments/C000_environment_and_cpu_bootstrap.md) | 2026-09-05 | Establish a supported interpreter, verified model bytes and CPU checks | Environment failures corrected | Python 3.12 and official-digest verification retained; no task-semantic relaxation |
| [E001](experiments/E001_debug_provenance_failure.md) | 2026-09-05 | Can the first debug run establish a reproducible software gate? | Invalidated GPU attempt | Untracked execution source; no scientific evidence retained from its outputs |
| [E002](experiments/E002_debug_high_lr.md) | 2026-09-05 | Does the initial 0.5B recipe memorize 32 examples? | Completed; gate failed | 25/32 train, 0/16 dev; test a lower LR |
| [E003](experiments/E003_debug_lower_lr.md) | 2026-09-05 | Can the lower-LR debug recipe pass the same gate? | Completed; gate passed | 31/32 at 300 updates; development remained zero |
| [E004](experiments/E004_main_4090_memory_failure.md) | 2026-09-05 | Does unchanged 1.5B FP32 AdamW fit 24 GB? | Failed GPU attempt | OOM before an optimizer update; preserve recipe on a larger-memory GPU |
| [E005](experiments/E005_main_a800_profile.md) | 2026-09-05 | Does that recipe fit the supplied A800? | Completed profile | 110 updates; optimizer allocation succeeds |
| [E006](experiments/E006_main_a800_overfit.md) | 2026-09-05 | Does the main model pass the engineering gate? | Completed; gate passed | 32/32 train; 0/16 greedy and 0/64 sampled dev |
| [C001](experiments/C001_exact_matching_unconstrained.md) | 2026-09-05 | Are exact shared-structure/token controls feasible? | Completed CPU audit; inadequate operator coverage | 256 problems, but all selected paths additive/subtractive |
| [C002](experiments/C002_muldiv_small_pool.md) | 2026-09-05 | Does requiring multiply/divide preserve adequate support? | Completed CPU sensitivity audit | Only 64/1024 problems selected |
| [C003](experiments/C003_muldiv_larger_pool.md) | 2026-09-05 | Can a larger candidate pool supply 256 matched problems? | Completed CPU sensitivity audit | 256/4096 selected; selection and weak Surface control remain |
| [C004](experiments/C004_tokenizer_preparation_failure.md) | 2026-09-08 | Can the saved tokenizer serialize frozen pilot data? | Failed CPU preparation | Original tokenizer blob check failed; no solving |
| [C005](experiments/C005_development_support_failure.md) | 2026-09-08 | Do 1024 development candidates yield 16 exact blocks? | Failed CPU preparation | Only 14/16 blocks; enlarge the presolver pool |
| [C006](experiments/C006_frozen_pilot_preparation.md) | 2026-09-08 | Can all four conditions share a complete, audited dose? | Completed CPU preparation | Frozen 256/64/64 data and exact controls |
| [E007](experiments/E007_pilot_calibration.md) | 2026-09-08 | Is the common dose feasible and nondegenerate? | Completed; gate passed | 14/64 matched dev at the full 1024-update dose |
| [E008](experiments/E008_seed17_four_arm_pilot.md) | 2026-09-08 | Does Paths outperform globally matched allocation? | Completed single-seed pilot | Paths/GCM 23/64 vs 18/64; restricted development only |
| [A001](experiments/A001_seed17_trace_audit.md) | 2026-09-09 | Do displayed calculations support correct final expressions? | Completed post-hoc CPU analysis | Fully verified matched traces 21/64 vs 14/64; broader 1/64 each |
| [A002](experiments/A002_seed17_identity_and_success_audit.md) | 2026-09-09 | How do identity operations and success concentration qualify the result? | Completed post-hoc CPU analysis | Heavy identity-path selection and endpoint-dependent strata |

## Completed replication and concurrent CPU design checks

| ID | Registered phase or analysis | Status | Outcome / decision |
|---|---|---|---|
| [E009](experiments/E009_seed23_paired_replication.md) | Same-problem Paths/GCM seed23; evaluation seed17 | GPU, CPU output audit and independent weight backups complete | Primary 22/64 vs 17/64; complete traces 18/64 vs 16/64; broader 1/64 each; pause before more GPU |
| [A003](experiments/A003_pairing_seed_semantic_exposure_audit.md) | Are numerical path exposures also matched across allocation procedures/seeds? | Completed CPU audit during training without reading new evaluation outcomes | Identity exposures 2780 vs 2800; structural matching does not imply every numerical property is matched |
| [C007](experiments/C007_identity_family_inventory_failure.md) | Can the stored four paths support two paths of each identity category on the same problem? | Completed CPU check; proposed inventory reuse fails | 41 problems have at least one of each; zero have two of each; redefine construction before training |
| [C008](experiments/C008_complete_ordered_support_census.md) | Does complete ordered enumeration recover support hidden by stored-four selection? | Complete local CPU census, 256/256 questions | 132 support disjoint-AC 2+2; 131 support 4+4; matching remains untested in C008 |
| [C009](experiments/C009_token_structure_block_matching.md) | Exact token/structure/shared-block matching and fixed inventory-policy losses | Per-problem checks complete; key search stopped at prespecified cap | 131 raw → 67 equal-token → 66 structure-feasible; discovered 681 keys/7 questions/one four-question witness; global capacity unknown |

The E009 registration is preserved and results are appended separately. A003 and
C007 are dated CPU analyses, not retroactively registered hypotheses. Independent
weight backup completion is a separate recovery gate from a completed model run.

## Proposed scientific work, not executed

| ID | Idea | Status / decision gate |
|---|---|---|
| [P001](experiments/P001_iclr_positioning_and_semantic_intervention.md) | Test a controlled boundary between defined legal path families | Literature positioning and design critique completed; intervention and larger study remain proposals |
| [P002](experiments/P002_legal_support_enumeration_design.md) | Distinguish selected-inventory loss from legal path support and matching constraints | Census completed in C008; token/structure checks measured in C009; global join incomplete |
| [P003](experiments/P003_task_and_control_redesign.md) | Reassess task construction, causal controls and closest-work overlap after E010 | Review complete; one evidence-route CPU prototype proposed, no new data/model run |
| [C014](experiments/C014_relation_transport_cpu_audit.md) | Can the constructive evidence-route task pass fixed CPU support/token/shortcut/grouping gates? | Complete:10,000/10,000 retained, all fixed gates and independent verification pass; zero new GPU seconds |

## Maintaining the record

Use [the entry template](experiments/_TEMPLATE.md) for a new idea or attempt.
Before a new scientific phase, record its contrast, endpoints, controls, costs
and stopping rule; link the frozen configuration. State whether the hypothesis
was formulated before or after the relevant outcomes. On completion, append
results and analysis from raw evidence, retaining the original prediction and
unfavorable outcomes. Do not rewrite a failed hypothesis into an apparent success.

A retry gets a new run ID and a linked attempt entry; changing a scientific
factor gets a new design entry. Avoid copying large logs into prose: link the
immutable artifact and retain the exact source/config/data identifiers there.
Publish each completed milestone and update this index. Credentials, connection
details, personal filesystem locations and model weights stay outside this journal.


## 2026-09-09 —C010–C013 matching completion and morning training preparation

**Question.** Can the original two-family construction be searched completely,
and which of its restrictions select the data? What control-preserving smaller
question can be executed within the original remaining GPU allowance?

**Prior failures reviewed.** C009's2,000,000-pair prefix did not measure total
capacity. C010 improved safe pruning but stopped after600 seconds with671,108
pairs remaining, repeating7.70GB of witnesses. Preserve both failures. Equal
length alone was not the whole cause: C011 restores high targets with separate
family lengths, then loses them again when both families require four structures.

**Design.** Before new outcomes, C012 fixed an absence-only allocation pair,
removing irrelevant requirements for present alternatives and cross-family
class/length constraints. Keep original questions/targets, exact serialization,
K4, within-question length, structure matching and untouched holdout. Sort and
shuffle an optimal packing with independent Random31; take32 blocks else16.
Use complete cycles for1024updates. After C010's stop, C013 independently froze
a new exact Hall occurrence-bitset algorithm and compact indexed output, with
the same600-second ceiling; it never chooses C012's family or seed.

**CPU results.** C013 completes48,429,084 pairs in4.833s:1,019,005 keys,63 questions,
15 optimal blocks. C012 completes74,764 combinations/4,182 keys,138 supported
questions and33 optimal blocks. Independent support/packing checks corroborate
the latter; its19- and119-question components give a33-block upper certificate.
C011 four cell counts are67/66/129/84 in common-class/common-structure/separate-
class/separate-structure order. All protocols and execution hashes are retained.

**Training preparation.** From published d537c31, immutable128-question data
use32 blocks/eight cycles, each arm1024updates/4096presentations/277760 response
tokens. Independent arithmetic/token/RNG/schedule/exposure checks pass. Both
old development files and split allocation are byte-identical. Only the new
Paths/GCM seed31 pair is queued; eval17. CPU inspection confirms2130 seconds
reserved within2484 remaining; no new charge or server connection occurred.

**Analysis.** Removing unnecessary family screening restores33 high targets,
but55/128 targets still equal inputs and all7 preview templates remain. Matched
batch structures/counts do not make each question's numeric exposure equal:
depth differs for120/128 questions, negatives for52/128, maximum intermediate
magnitude for90/128. Magnitude differs in600/1024updates. These are measured
components/limits of this allocation contrast, not a semantic mechanism or an
ICLR claim. Old models use a different pool and are not a causal identity control.

**Decision and records.** Prepare the preselected finite pair for the owner's
morning A800 launch; do not open a server now, change seed based on descriptors,
train a four-arm grid or evaluate holdout. Full results, paths, exact source
commits, archives, residuals and commands are in
[the integrated report](../reports/MATCHING_COMPLETION_AND_TRAINING_20260909.md)
and [NEXT_SESSION](NEXT_SESSION.md). Negative and failed attempts remain in Git.


## Legacy provenance regression repair

The final full suite enabled the real pinned-tokenizer regression and exposed
an old verifier that compared preparation hashes with today's source files.
Adding the new dataset dispatch legitimately changes pilot_runtime.py, so that
comparison incorrectly invalidated historical artifacts. The two historical
data manifests also explicitly record dirty preparation worktrees; their
recorded commits cannot retroactively be called complete source snapshots.

The repair binds only the two exact historical manifest hashes to the verified
later published GPU snapshot6128e4266d62f14f063585d4c8e94dbe3ad8c711, checks the
manifest bytes in that snapshot and every recorded source SHA, and reports
later_publication=true/prepublication_claimed=false. Unknown dirty provenance,
missing commits, altered hashes and invalid paths are rejected. Current data,
token, split and seeded reconstruction checks are unchanged. The new C012
preparation did use prepublished clean source; these historical exceptions do
not change its source record or frozen data.

## 2026-09-09 —P003 task/control redesign and final E010 shutdown confirmation

**Question and motivation.** Can a constructive task avoid rare support
selection while isolating a scientifically interpretable allocation contrast?
C009/C010 matching failures and completed C013 support, C012 residuals, and
E010's7/64 versus5/64 primary/4-versus4 traces motivate the review. Those
outcomes remain unchanged and do not identify identity removal.

**Methods considered.** Independent reviews assessed causal identification,
arithmetic identities, planted equal expressions, reachability, permutation
transport, mixed proof networks and seven closest primary works. Reject
always-positive reachability and orientation-as-strategy claims. Defer mixed
algorithms whose proof complexity and support guarantees are unresolved.

**Design decision.** Provisionally select S5 relation transport only for an
evidence-route CPU prototype: four paths by construction, independent exposed-
table solver, fixed allocation schedules, strict proof scoring, useful/irrelevant
evidence deletion and coherent counterfactuals. A second review checked the
telescoping/gauge argument and both Latin/factorial schedules. Corrections
make uniform query sampling, undirected disconnection, deranged endpoint edits,
full serialization checks,16-example factorial updates and remaining table/
state-exposure residuals explicit.

**Results and analysis.** This round produced design arguments and rejection
criteria only. No generator audit, shortcut score, data split, training result
or new holdout observation exists. All chains share one algorithm and bare
topology; no semantic-strategy or topology-OOD claim is supported. Closest work
already covers allocation and constructed proofs; evidence deletion supplies
a candidate operational distinction, not established novelty.

**Next step.** Publish one fixed CPU source/configuration before materialization,
then test support, solver agreement, tokens, shortcuts and grouped splits.
Only successful concrete receipts can support a later reviewed GPU/resource
proposal. Read [the integrated review](CONTROL_REDESIGN_PROPOSAL_20260909.md)
and its three independent memos for exact reasoning, controls and kill criteria.

**Operational closeout.** The authenticated provider console showed the exact
E010 instance as **已关机**, recorded20:00:03 UTC. The confirmation heartbeat
was paused. No new shutdown command, instance start, deletion, GPU spending
or storage expansion occurred. The latest ledger remains5740/7200 used with
1460 remaining and no reservations; see the
[closeout receipt](../reports/absent_boundary_seed31_shutdown_closeout.json).

## 2026-09-09 —C014 full-retention construction and fixed shortcut audit

**Motivation.** Implement the P003 decision without the old arithmetic
eligibility filter. Establish actual full support, exact tokenization and a
scoped shortcut challenge before incurring new GPU cost.

**Design.** Published clean source `6c24d4c1379a421be7b44151c653842a6cd9aabf`
froze100 seeds/10,000 worlds, seed-level8000/2000 CPU fit/audit splits,
five views, eight predictors,40-test Bonferroni threshold, direct exposed-
table solving, strict proof checks, conservative world groups and immutable
archives. Development fixtures used distinct seeds;25 focused tests passed.

**Results.** All10,000 worlds retained with four disjoint four-step proofs;
all answers, counterfactuals, negative fixtures, masks and matching gates pass.
All references have101 EOS-inclusive supervised tokens; clean sequences1137.
No probe test flagged; accuracies18.75%–21%. CPU execution138.647s, followed
by105.031s independent verification of40,000 references,50,000 view prompts
and80,000 raw predictions. The complete record is recoverable from ten
lossless hashed shards and the published source, without a running server.

**Analysis.** The construction resolves retention/token matching for its
declared population. It does not establish LLM benefit, complete shortcut
absence or topology/semantic-strategy diversity. The accounting contrast still
changes state/table exposure: neutral transitions25,599 vs25,468, identity
tables1053 vs932, and7,041/8,000 questions differ in neutral exposure. These
are retained treatment/residual descriptors, not reasons to select another seed.

**Next decision.** Prepare a bounded32-example engineering/profile runner,
exact data and resource plan before requesting an A800. Do not execute the
8,000-update CPU accounting schedule. No new GPU charge/reservation, storage
expansion, server operation or arithmetic holdout access. Read
[full results and file index](../reports/RELATION_TRANSPORT_C014_RESULTS.md).

## 2026-09-09 —C015/E011 engineering source preparation

**Why.** C014 resolves declared construction gates, not1.5B learnability or the
1137-token training cost. Additional arithmetic seeds would not repair E010's
interpretation limits. This step therefore measures a small, fixed engineering
trajectory before any new scientific comparison.

**Design.**32 original seed401 worlds,16 seed481 diagnostics, no reselection;
256 full-parameter updates, fixed multi-route dose, unchanged pinned base/recipe.
Profile updates9–72; greedy clean train and clean/deletion dev, strict full-proof
and EOS metrics, raw token streams and final train-reference NLL.720-second cap
plus15-second guard; use original cumulative ledger. Stop and retain failure if
incomplete, invalid, OOM, nonfinite or out of budget. No automatic next phase.

**Verification so far.**37 of40 initial focused tests passed; one prepared-data
regression awaits materialization and two GNU-timeout integrations require Linux.
After adding the under-lock race guard, all8 affected local tests pass; the same
2 Linux-only integrations remain deferred. No real model execution was tested.

**Status.** Source/configuration are ready to publish before input extraction.
No newly materialized engineering input, GPU result, server action, reservation
or holdout use at this milestone. The full prospective design is
[E011](experiments/E011_relation_engineering.md); later preparation and outcomes
will be recorded separately.

## 2026-09-09 —C015 complete; E011 ready, GPU not_run

**Execution.** Published source8eeb0f9883759a69ca42540932b98d71b2c64414 preceded
0.824-second extraction. Independent3.374-second reload verified original-record
identity,192 clean references,240 view prompts,split groups and exact token dose.
No selected world was dropped/replaced. The five-file compact bundle is167834 bytes.

**Results.**32 train worlds/128 references,16 dev parents;256 updates,1024
presentations,103424 supervised tokens,1164288 processed tokens,zero padding.
Each route appears8 times. Maximum prompt plus generation cap is1164 tokens.
42 focused tests:40 pass,2 GNU-timeout integrations remain mandatory on Linux;
real pinned-tokenizer release checks and synthetic output-corruption tests pass.

**Analysis and next action.** CPU feasibility and reproducibility pass. There is
still no real model learnability,memory,throughput or allocation result. Request
one owner-started A80080GB,check12GiB free and current exact ledger,then execute
only the bounded E011 engineering trajectory. Its735-second maximum reservation
fits1460 remaining; no GPU time or reservation was added by this preparation.
Preserve all failures and dev outcomes and use the fixed decision rules; no
scientific pilot follows automatically. See [ready report](../reports/RELATION_E011_READY.md).

C015 migration check: default launcher inspection from a clean tracked-files-only
worktree at published f4aec50 passed in3.143 seconds. The only external inputs
were the original tokenizer and retained private ledger. No run directory,model
process or new ledger reservation was created; ledger bytes stayed identical.
See [clean-checkout receipt](../reports/relation_engineering_c015_clean_checkout.json).

## 2026-09-09 —E011 executed; CPU re-audit performance repair before verification

The owner started the supplied A800 and authorized E011. All42 Linux tests
passed after supplying a canonical private tokenizer-cache symlink; an earlier
41-pass/1-skip preflight remains retained. The unchanged frozen run completed
256 updates and saved its checkpoint. Its initial metrics report a failed
engineering gate (0/32 complete train proofs); independent audit remains pending.
The process charged231 seconds,bringing the original ledger to5971/7200 used.

The initial post-run CPU audit exceeded its60-second orchestration bound and
produced no verification receipt. Inspection found repeated vocabulary-size
queries:100 len(tokenizer) calls took0.648 seconds locally. Prepare a read-only
memoization adapter,leaving the original frozen auditor,scorer,tokenization,
training source and result schema byte-unchanged. Forward all tokenization and
decode methods,and recheck vocabulary size after the audit. A synthetic test
checks forwarding,caching and mutation rejection. Publish this CPU adapter
before using it on the real outputs. This repair adds no model execution and
does not change the failed engineering threshold or authorize a training retry.

## 2026-09-09 —E011 failure independently verified and preserved

**Result.** Fixed256 updates completed;231 seconds charged. Full proofs0/32
train and0/16 for clean/useful-delete/irrelevant-delete dev. Final train
NLL.1193898 passes only the NLL sub-gate. The full engineering gate fails.
Profile771.64 supervised tokens/s,27.18GiB peak allocated memory;no OOM,
nonfinite history,training truncation,early stop or GPU retry.

**Analysis.** All333 parseable generated step results equal2,while512 gold
step results span all five states. Only33/133 grounded training step lines
satisfy their local lookup. State-result tokens are4/101 of supervision;
this does not measure per-field loss or identify the cause. Formatting and
termination improve without complete correctness. Mean NLL and answer-only
counts would give a misleading readiness signal. Do not claim task
impossibility,route benefit or a deletion effect from this one failed arm.

**Verification/preservation.** All96 token streams/dose give byte-identical
server/local audit reports. The immutable-size cache fixes CPU audit overhead
without changing scoring. All16 receipts match the retrieved ledger;prior15
unchanged.12 checkpoint files/6190803414 bytes independently SHA256-backed up.
Current5971 used/1229 remaining,zero reservations. Publish and normally shut
down;provider confirmation is recorded separately.

**Next.** CPU preparation of fixed-reference/full-graph,supplied-route,and
one-edge diagnostic gates;separately review their order,inputs and total caps.
No automatic model calls. Read [E011 results](../reports/RELATION_E011_RESULTS.md).


E011 shutdown closeout: after result publication at1a999ad,verified backups,
latest ledger and synchronization to the instance,the vendor shell helper was
invoked through Bash. Direct exec had failed before execution because the
helper lacks an interpreter header; its cleanup target was verified absent.
SSH ended during shutdown. The authenticated console subsequently displayed
the exact instance as已关机,which is the independent state confirmation.
No instance deletion/release,new GPU phase or storage expansion occurred.
See [shutdown receipt](../reports/relation_e011_shutdown_closeout.json).
