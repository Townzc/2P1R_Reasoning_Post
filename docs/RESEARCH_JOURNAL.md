# Research journal

## 2026-09-10 — E013 completed, engineering gate failed

**Executed.** After server startup and40 Linux tests, run the fixed32-parent
GSM8K trajectory from4fa838a. All256 updates,167232 response tokens and229056
processed tokens complete. Full32-response memorization is not achieved:24/32
correct terminated generations, five truncations and three wrong numeric
finals.20 responses exactly match references; final NLL is0.014206. The profile
is complete. Preserve the failed gate despite a normal process exit.

**Interpretation.** Base dev strict0/16 is format-limited; final dev0/16 has11
parsed wrong answers and five truncations. This small descriptive set is not
a scientific treatment result. Post-hoc raw-output inspection finds repeated
derivations and one repeated-digit loop; all eight failed train generations
initially reproduce46–355 reference tokens. Record consistency passes for all
64 token streams and256 doses. No NLL rerun or proof-validity claim is made.

**Budget and next decision.**326 seconds are charged;17 receipts reconcile to
6297 used /903 remaining with no reservations. Four-arm training-only proxies
are2096–2165 seconds before evaluation/overhead, and the failed gate separately
blocks scale-up. A review-only E014 proposal would inspect saved-checkpoint
batch8 replay,10 selected single-problem decodes and first-divergence logits;
no model job is queued. All12 checkpoint files (6,190,803,414 bytes) now have
independent verified backups. No additional GPU job was run during analysis
or preservation.

[Result](../reports/REAL_MATH_E013_RESULTS.md),
[post-hoc analysis](../reports/real_math_e013_execution_r1/failure_analysis.json),
[proposal](../configs/diagnostics/real_math_e014_proposal.json).

## 2026-09-10 — E013 engineering preparation

The owner requested the next experiment after C017. Freeze its 32 selected
GSM8K responses and first 16 development ranks; implement one overfit/profile
before any treatment comparison. Preserve the base-model recipe and ledger.
Published source precedes immutable inputs. Each row is exposed 32 times in
256 updates, totaling 167232 response / 229056 processed tokens. Original
source hashes, independent tokenizer labels and every update agree. Eight
input-tampering cases fail closed. 38 tests pass, two GNU-timeout integrations
await Linux. Numeric answer agreement is separate from proof validity and EOS.

The existing SSH endpoint refused a read-only connection. No model was loaded,
job reserved or GPU cost measured. The owner was asked for server availability
or updated access. Balance: 5971 used / 1229 left. The next step is Linux
preflight and this single run; E012 stays paused.

## 2026-09-10 — C017 real-math data audit and scale proposal

**Question and motivation.** Following the cost-allocation discussion, the
owner asked to establish original problem splits, usable-solution coverage and
selection losses before choosing training size. Preserve source failures and
zero-solution parents; do not make support conditional on knowing four solutions.

**Design.** Pinned original GSM8K, three MATH mirrors plus loader lineage, and
GSM-Symbolic parent metadata. Group before partition; draw1,024 GSM8K and512
stratified MATH parents, with separate dev and fresh reserves. Four seeded
OpenMathInstruct-2 shards, first16 released candidates per parent, conservative
answer checks, exact tokenizer serialization, no models or paid generation.

**Failures and repairs.** One original-ID mirror incorrectly maps a train row
to a duplicated test ID; quarantine it. A first balanced partition depleted
rare strata; preserve it and freeze proportional partitions before responses.
Real JSON strings exposed Unicode line-separator handling; fix physical JSONL
reading. Preserve the initial answer audit, then replay exactly the same raw
candidates after repairing matrix separators and unambiguous LaTeX formatting.
The published parent/code tree and exact-reproduction receipts record provenance.

**Results.** Eligible groups7,470 GSM8K/2,908 MATH. Four-shard K>=4 coverage is
963/1,024 and481/512; accepted solutions7,776 and7,532. A native GSM8K reference
has incorrect arithmetic; MATH still loses answers to unresolved units/formats.
Sixteen AI-reviewed traces show prompt/assumption/wording limitations, not a
human-gold quality rate. Twenty-four focused tests and independent source,
identity, cap, token, denominator and schedule checks pass.

**Decision proposal.** Start with (P,K)=(256,1),(256,4),(512,2),(1024,1). Eight
CPU schedules covering seeds17/23 each match524,288 response tokens/256 updates,
with actual pairs253/996/1,011/1,013 and disclosed processed-token/exposure
residuals. First measure a32-parent GSM8K engineering profile before a priced,
reviewed phase. MATH stays a decisive second-task check; no full second grid.
This audit gives no allocation-performance finding or teacher production cost.
Zero new GPU seconds; original5971 used/1229 left. E012 stays paused.

Evidence: [C017](experiments/C017_real_math_cpu_audit.md),
[complete findings](../reports/REAL_MATH_CPU_AUDIT_20260910.md),
[scale proposal](../reports/real_math_c017_scale_proposal_r1/proposal.json).

## 2026-09-10 — revised proposal abstract

Produced a [standalone abstract and deliverables](PROJECT_ABSTRACT_20260910.md)
from P004 and the model/compute audit. The central question is allocating
acquisition expenditure between problems and additional solutions, with measured
local costs separate from assumed public-data prices. The text names the small
student, candidate generator, dataset and conditional second-family check;
synthetic tasks remain diagnostics. It makes no claim of completed acquisition
results. No new scientific protocol, GPU execution or ledger change occurred.

## 2026-09-10 — P004 literature/model/compute follow-up

Question: do the proposed assets reflect the earlier papers and a small-compute
research plan? Rechecked the original three references and four later related
works against primary experimental sections. Small-student precedents exist,
but large teachers, long generations and many evaluations can dominate cost.
Outcome: preserve the measured Qwen1.5B student candidate; keep OLMo1B conditional;
remove the default Math7B teacher commitment. Propose auditing reusable solutions
and bounded Math1.5B generation before selection, with cache-cost limitations
explicit. No model outcome, new protocol, GPU process or ledger change follows.
The [full comparison](../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md) records
paper models, costs, rationale and next feasibility requirements. E012 is paused.

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

Latest completed model experiment: [E011](experiments/E011_relation_engineering.md),
with 0/32 complete train proofs despite target NLL .11939; all 333 parseable
predicted after-states were 2. The failure is preserved. C016 CPU diagnostics
and the E012 execution release are verified; no E012 model run has occurred.
The current owner-requested framing discussion is P004; E012 is paused.
[Current readiness and interpretation](../reports/RELATION_E012_READY.md).

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
| [P004](experiments/P004_cost_aware_sft_allocation_proposal.md) | Asymmetric acquisition costs for new problems versus additional usable solutions under a fixed SFT budget | Proposed for review; E012 paused; no cost or model experiment executed |
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


## 2026-09-09 — C016 diagnostic construction/source milestone

**Question.** E011 learned some formatting but no complete proof, with all
parseable after-states equal to 2. Is a short lookup learnable under the same
recipe, does a supplied route permit propagation, and does a fixed target
trajectory permit full-graph learning? These are prospective questions.

**Design.** Use the same parents, original assignment and update order.
Separate shorter one-edge lookup from original full graph plus route hint and
original full graph with one fixed reference. Record what each change also
alters. Add exposed-text route enforcement and independently reconstruct
queries from C015, without importing the new builder. Preserve all labels,
steps and parent groups; report table-operation overlap and frequencies.

**Implementation checks.** Twelve new synthetic tests initially pass, including
all 1200 permutation/input/direction combinations and planted semantic loss
dilution. Broader regression exposed an old unit fixture that reused the now
retained E011 run ID; its overwrite guard correctly refused it. Give the unit
fixture a distinct temporary identity, without changing the frozen experiment
runtime or deleting real outputs. An old release test also requires its
explicit tokenizer environment variable; supply the verified local cache.
Retain the initial log and rerun focused regressions before source publication.

**Resource boundary.** CPU/tokenizer work only. A800 stays stopped; no model
weights loaded, no ledger mutation, no GPU reservation. Materialization and
its independent audit will follow publication of this registered source.

C016 source check result: all 53 focused tests pass, no skips, including the
real pinned-tokenizer field spans and the retained C015 release regression.
The initial fixture collision and final passing logs are preserved in
`reports/relation_c016_initial_regression.txt` and
`reports/relation_c016_source_tests.txt`. No historical runtime source changed.


## 2026-09-09 — C016 frozen CPU release and independent reproduction

**Result.** Sourcef073955 was published first. The single registered attempt
retained all288 rows/48 parents and completed in2.03 CPU seconds. Independent
reconstruction takes3.56s; after data publication4a5ad97, a clean checkout
reproduces the same audit in3.23s. All53 focused tests pass, no skips. Exact
full-reference budget matches E011; given route adds86 prompt tokens; one-step
serialization is166 tokens. Seven frozen input files total203769 bytes.

**Analysis.** Gold training step states are28/16/31/31/22 for states0..4;
constant2 is a24.22% hypothetical operation predictor, not a model result.
The32/16 parent groups do not overlap, but lookup sets share34 tables and13
table/input operations. Development remains observed engineering data. The
after-state token fraction is3.45% in one-step versus3.96% in full proofs;
shortening the task does not itself fix loss dilution. Per-operation exposure
and final-answer duplication also differ and remain explicit limitations.

**Decision.** Keep the finite diagnostic ladder and source-frozen inputs.
Collect strict proof/EOS, parent success, field-wise gold-prefix measurements
and all-line local lookup diagnostics prospectively. No causal verdict follows
from CPU checks. Next implement/review the bounded runner and raw-output
auditor locally before asking for startup. No pretrained model, GPU, server
contact, checkpoint mutation or ledger change occurred;5971 used/1229 left.

**Records.** `reports/RELATION_C016_CPU_READY.md`, exact examples, immutable
`runs/relation_diagnostics_c016_r1`, release hashes, source and fresh-checkout
verification/test logs, and resource closeout are all published.


## 2026-09-09 — E012 implementation and source milestone

**Why.** E011's0/32 complete proofs and constant2 after-states make another
scientific comparison premature. C016 supplies frozen diagnostic questions
with documented confounds. The owner now requests the finite next experiment.
Max is appropriate for this implementation/verification stage; no delegation
or additional compute allowance was inferred.

**Design implemented.** One explicit bounded stage at a time, fresh pinned
base, unchanged loss/optimizer and C016 schedules. Save every generated token,
actual update index, target-position CE/top-one ID and partial failure history.
Enforce prior full-proof gates, current receipt prefix, complete remaining caps,
published compact outputs and independent checkpoint backup before continuation.
Default inspection has no model/server side effect.

**Checks and refinement.** The first18 new tests passed. Additional tests cover
published-commit binding, backup/publication gates and mutable registry/accounting
repair; the focused suite now has76 passes and2 GNU-timeout tests reserved for
Linux. Pinned Qwen output vocabulary151936 exceeds tokenizer entries; unknown
output IDs are kept and fail strict proof checks, while token CE consistency
uses the real model vocabulary. This is a stream-validation boundary, not a
change to old scores. No pretrained model was called.

**Record maintenance.** Registry/accounting summaries were stale at5740 even
though the16 verified receipts total5971. Implemented a tested registry that
recognizes source_commit and failed engineering gates, plus a public-receipt
accounting reconciler that preserves the old prefix and never mutates the live
ledger. Publish the code before applying it to current aggregate snapshots.

**Next.** Freeze the runtime release, independently inspect it from a clean
checkout, then request owner-started A800. No new model result, GPU charge,
server contact, storage expansion or checkpoint cleanup at this milestone.


## 2026-09-10 — E012 execution release and clean-checkout verification complete

**Question and motivation.** E011's low mean target loss coexisted with zero
complete training proofs and constant generated after-states. Before scaling,
can the same fixed recipe learn a single exposed operation, supplied-route
propagation and a full question with one repeated reference? The original
failed run remains evidence; the new task views do not identify a unique cause.

**Design.** E012 implements C016's already frozen ladder on the same original
32 train / 16 observed dev parents. Fresh pinned base for each stage; exact
256 updates; no outcome-selected examples, loss reweighting or changed stop
threshold. Continue only after complete train proofs/EOS, assigned-reference
NLL < .2, full finite dose/profile, independent output audit, published compact
records and verified independent checkpoint backup. The three maximum caps and
guards total 1125 seconds inside the original 1229 remaining.

**Preparation result.** Execution source was published at `1fc27d4`, then the
immutable release at `27a0943`. In a clean detached checkout, default inspection
passed and 78 focused tests collected: 76 passed, 2 explicitly skipped pending
GNU timeout on Linux. Both private ledger copies stayed byte-identical. No
pretrained model was loaded, server contacted or process reserved. E012 stages
remain not run; readiness is not a learning outcome.

**Additional maintenance finding.** The central registry and compute summary
still showed 15 receipts / 5740 seconds although the preserved private ledger
and detailed E011 receipt already showed 16 / 5971. A tested reconciler repaired
both summaries from immutable receipts without modifying the ledger. E011 is
recorded as completed with its learning gate failed, not as successful training.

**Analysis and next decision.** The execution path now makes proof correctness,
semantic-field loss and gold-prefix/free-generation behavior separately
reviewable. The auditor retains unmapped model-vocabulary IDs as explicit proof
failures and checks necessary CE/top-one consistency; scalar records do not
independently reconstruct original logits. The three task views differ in
length, exposure and hints, and dev is neither fresh nor unseen-table. Request
owner-started A800 availability, pass mandatory Linux checks, and run only the
first bounded stage. Stop on any failed gate; even all passing gates would
require a separately reviewed scientific design before scaling.

See [ready report](../reports/RELATION_E012_READY.md),
[clean-checkout evidence](../reports/relation_e012_fresh_checkout_verification.json)
and [frozen registration](experiments/E012_relation_diagnostic_ladder.md).

Readiness follow-up: after publishing the CPU results, a single read-only SSH
probe at 02:11 UTC returned connection refused. No authenticated remote action,
model job, startup or new reservation occurred. The owner was asked to provide
an available A800 or updated connection information. Power state is unconfirmed.


## 2026-09-10 — P004 cost-aware SFT framing proposal and reply preparation

**Question.** Under a fixed SFT budget, when is the marginal benefit of a new
problem worth its acquisition price compared with another usable solution to
an owned problem? The owner asked to answer framing and concrete-deliverable
questions before continuing experiments.

**Motivation and earlier evidence.** Earlier same-problem arithmetic comparisons
and E011's failed full-proof gate do not measure acquisition costs or determine
an optimal problem/solution allocation. Further E012 engineering is paused while
its relevance to the revised question is discussed. No earlier failure was
removed or retroactively reclassified.

**Proposed design.** Stage a Qwen1.5B/GSM8K P/K surface with fixed SFT budgets,
one fixed math teacher and transparent acquisition/failure accounting; vary
problem-price scenarios separately from measured generation costs. Use synthetic
verification for targeted structural/repetition diagnostics. Validate any
recommended allocation on fresh problem draws and unfit allocations before
second-family replication. Full cost/difficulty/quality/diversity/model factorial
coverage is outside the minimum scope. Refer to P004 for proposed counts/seeds
and course deliverables, none of which is a registered or funded training grid.

**Work completed.** Checked official student/teacher model cards and GSM8K's
source repository, reread prior positioning/evidence, and performed a bounded
primary-paper check including Spend Wisely, CoScale-RL, repetition and coverage
work. Existing work already covers broad multi-solution and budget-allocation
ideas; the candidate distinction still needs evidence and novelty review.
Prepared a privately addressed English reply and a public scientific proposal.
No reply was sent. No new data generated, student/teacher model called, server
contacted, training run reserved or resource ledger changed.

**Analysis and decision.** Explicitly distinguish attempted/accepted solutions,
nonduplicate text/semantic strategies, marginal/sunk problem costs, actual whole-
study spending/counterfactual policy costs and same-example/same-token budgets.
Do not eliminate hard questions by requiring K successful traces. A correct
final answer alone cannot certify a reasoning trace. Discuss the reply first;
then revise the abstract and prepare a bounded feasibility plan. Current
5971/7200 used, 1229 remaining, 16 receipts, zero reservations.


## 2026-09-10 — P004 reply grounded in progress and model-choice evidence

**Question.** Did the proposed reply use actual progress, and why were the three
models proposed? The owner requested those distinctions and aligned English /
Chinese text before continuing experiments.

**Evidence.** Reconciled the 1.5B arithmetic overfit (32/32 train, 0/16 greedy dev),
restricted arithmetic allocation comparisons with weak broader transfer, and
E011's complete-proof training failure. Only the Qwen0.5B debugging model and
Qwen1.5B main model have project run records. Math7B is a new P004 teacher
candidate; OLMo1B was already in the original plan but has never run. No GSM8K
acquisition/model result exists. Maintainer cards establish identities and
intended uses, not this project's performance or teacher-cost advantage.

**Analysis and correction.** The first reply drew on the existing stack but
understated the distinction between measured assets and prospective candidates.
An independent read-only review agreed. Prepared an evidence note and a revised
privately addressed bilingual reply, retaining the first draft as history.
Qwen1.5B is the first candidate for real-task calibration, Math7B needs yield,
reasoning/duplicate/length/cost checks, and OLMo is conditional replication.
Base checkpoints do not establish absence of benchmark exposure; Instruct/TIR
scores do not apply to untested base/tool-free configurations. The nine-cell
allocation grid is tentative pending profiling, not an executed or funded plan.

**Outcome.** Documentation and aligned reply completed; no new teacher/student
call, GPU job, server contact, reservation or ledger change. E012 remains paused
for the owner's framing discussion. The personally addressed draft was not sent
or included in the public repository. See the
[model evidence note](../reports/MODEL_SELECTION_EVIDENCE_20260910.md).


## 2026-09-10 — P004 dataset rationale and proposed second real task

**Question.** Which datasets do the referenced papers actually use, why begin
with GSM8K, and what data evidence is needed beyond a single arithmetic benchmark?

**Work and evidence.** Read the seven primary papers and maintainer dataset
metadata, distinguishing training question pools, generated solution corpora
and evaluation sets. GSM8K supports bounded calibration; MATH adds subject and
difficulty labels. Found that the author-linked MATH mirror combines 12.5k rows
under one train label, requiring original split reconstruction before use.
OpenMathInstruct-2 separates original and augmented questions with different
answer provenance. GSM-Symbolic links variants to GSM8K test parents.

**Analysis.** Propose GSM8K primary plus stratified MATH levels 1–3 for decisive
second-task checks, after feasibility. Audit reusable outputs and keep symbolic
variants evaluation-only. Prior matching-induced selection makes drawing pools
before solution-success inspection essential. Cached outputs cannot reveal
historical rejection costs; local small-teacher costs cannot price another
teacher's cache. Data manifests, coverage/quality attrition, budget accounting
and independent validation are the contribution to develop, not dataset count.

**Outcome.** Saved the [dataset evidence review](../reports/DATASET_SELECTION_EVIDENCE_20260910.md)
and linked the proposal/status/handoff. No source was ingested, model called,
server contacted or experiment launched. E012 and all earlier outcomes remain
unchanged; ledger 5971/7200 used, 1229 left, 16 receipts, zero reservations.
