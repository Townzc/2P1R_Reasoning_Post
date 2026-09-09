# Evidence roadmap toward an ICLR-quality study

**The next contribution must explain a controlled boundary, rather than merely
produce a positive second seed.** The current arithmetic pilot is a useful
engineering and design result. It is not sufficient evidence for a general
reasoning claim, and close prior work already addresses the broad per-problem
versus global-diversity question. This roadmap separates the small executable
replication from larger scientific decisions that require a new fixed protocol
and compute review.

## What the present evidence establishes

| Evidence | Supported reading | Remaining gap |
|---|---|---|
| [Four-arm pilot](../reports/PILOT_V1_RESULTS.md) | Exact response-token/update controls are feasible; Paths/GCM greedy is 23/64 versus 18/64 on one selected dev slice | One seed, one selected training pool, only 16 matched-dev blocks; broader dev is 4/64 versus 1/64 |
| [Trace audit](../reports/pilot_v1_trace_audit_20260909/FINDINGS.md) | Final answers and displayed arithmetic can disagree; complete matched traces are 21/64 versus 14/64 | Broader complete traces are 1/64 in both arms; displayed correctness is not hidden-reasoning faithfulness |
| [Structure audit](../reports/pilot_v1_structure_bias_20260909/summary.json) | 695/1024 training reference paths contain an identity operation; input 1 occurs in half of matched dev but only 5/64 broader dev | Syntax diversity may overstate useful computational alternatives; observed strata differ in difficulty and support |
| [Positioning audit](../reports/ICLR_POSITIONING_20260909.md) | Closest prior work directly studies per-problem/global diversity and coverage; repetition and multiple-reference SFT are established topics | A narrower, falsifiable intervention and a meaningful boundary result are needed beyond tighter bookkeeping |

The audits are descriptive analyses performed after observing seed17. They
motivate hypotheses, not confirmed explanations. In particular, the greedy
advantage and the sampled any-success advantage concentrate in different
identity strata. We cannot conclude that neutral operations either cause or
fully explain the observed difference.

## Stage 1 — fixed low-cost stability check

**Completion update:** the pair completed; see
[seed23 results](../reports/PILOT_REPLICATION_SEED23_RESULTS.md). Primary is
22/64 versus 17/64, complete traces 18/64 versus 16/64 and broader greedy 1/64
each. The primary direction repeated; a mechanism and broader benefit did not
become established. The protocol description below retains its pre-run budget.

Execute only the [paired seed23 proposal](PILOT_REPLICATION_PROPOSAL.md) after
CPU artifacts are frozen, reviewed and verified on the supplied instance:
Paths/GCM, the same training/development problems, a jointly regenerated
assignment/order, training seed23, evaluation seed17, and unchanged model,
1024-update dose and 267456 supervised response tokens per arm. The complete
phase reserves 2130 of the remaining 3488 process-seconds on one A800 80GB.

Keep greedy final-expression correctness primary. Preserve all secondary
metrics, arithmetic-trace categories, unfavorable outcomes and failed attempts.
Do not choose more seeds until a positive result appears. Two seeds on the same
pool are a limited check of sensitivity to random assignment/order/training;
they do not establish robustness across datasets or a useful effect size for
publication. A null or reversed replication may be the most informative result.

A positive repeat would allow a more focused design discussion, not authorize
Stage 2 training. A negative repeat should narrow or suspend the positive claim;
CPU investigation of a falsifiable boundary can still be useful if it does not
retrofit the conclusion to the observed outcomes.

## Stage 2 — test a boundary between defined legal path families

**CPU completion update,2026-09-09:** C011 confirms both length and structure
screening. C013 fully searches the old double-family common-length grid:
63 questions and15 optimal blocks/60 questions. It remains severely selected.
The separately preselected C012 absence-only contrast removes requirements
irrelevant to its two model arms and supplies33 blocks. Its frozen preparation
uses32 blocks/128 questions,277760 tokens and1024 updates per arm, within the
original remaining budget. See [complete analysis](../reports/MATCHING_COMPLETION_AND_TRAINING_20260909.md)
and [finite training plan](ABSENT_BOUNDARY_TRAINING.md). Models are not yet run.
This is a limited allocation boundary pilot; it does **not** estimate the
allocation-by-family interaction described as a conceptual goal below. A future
interaction study still needs common-population design and separate review.

The provisional scientific question is: **Does the benefit of within-problem
legal multitrace allocation depend on supplying different numerical calculation
structures, or can alternative legal ways to consume the required inputs yield
a similar benefit on shared problems at a fixed budget?** This is a boundary
test of the existing diversity literature, not an established new mechanism or
a claim that a syntax tree labels a human cognitive strategy. Fix problems and
audit specified difficulty proxies; do not claim to control all task difficulty.

Prepare a controlled construction before training. A candidate factorial design
has two factors: within-problem versus globally matched allocation, and two
prespecified families of legal trajectories with different numerical properties.
Repeat and Surface remain useful controls wherever they isolate a stated
alternative explanation. The exact feasible cells, dose and sample size must be
frozen after a CPU feasibility audit, rather than improvised during GPU runs.

Numerically neutral does not mean invalid, useless or equivalent to Surface.
Countdown requires each input exactly once: for inputs `[1,2,3,4]` and target
24, `(1*2)*(3*4)` and `(2*3)*(4/1)` are legal ways to consume all inputs, as is
`(1+3)*(2+4)`. Removing multiply/divide-by-one is only an analysis projection;
the reduced expression may violate mandatory input use. Retain the complete
legal expression and its input provenance in every construction and analysis.

A scientifically useful construction needs the following properties:

1. **Explicit path taxonomy.** Define the equivalence relation and its limits.
   Record which changes are removed by exact neutral-operation simplification,
   AC canonicalization and any further audited algebraic rewrites. Preserve
   input provenance and legal use. A correct target value alone cannot define
   path equivalence: every valid answer to the same problem shares that value.
   A different tree alone cannot establish a different computational strategy.
2. **Shared support where possible.** Prefer problems that support both candidate
   path families, so changing the paths does not automatically change the
   questions. Match within a fixed pool and report eligibility losses. If shared
   support is too narrow, revise the generator or define a restricted estimand;
   do not silently compare unrelated easy and hard pools.
3. **Matched global exposure.** Reconcile structural frequencies, operator and
   depth distributions, actual presented problems, paths and repetitions. Match
   supervised tokens including EOS and optimizer updates. Check per-update
   matching when feasible; otherwise quantify the residual and its scientific
   consequence before allowing a run. Never use truncation or meaningless
   padding to manufacture a useful-token match.
4. **Difficulty controls fixed before outcomes.** Audit number/target ranges,
   exact solver solution counts, intermediate magnitude/fraction profiles,
   operation depth and solvability. These are partial proxies for difficulty,
   not a guarantee that two domains are equally hard for the model. Any
   model-based calibration must use a separate development protocol and budget.
5. **A contrast that can fail.** Prespecify the allocation-by-path-family
   interaction and the simplest competing prediction. For example, a benefit
   confined to neutral rewrites would weaken the claim that additional
   nontrivial computational alternatives are necessary. Failure to reproduce
   the interaction should remain a reported result, not trigger a favorable
   redefinition of the strata.

Simply deleting input 1 and rerunning changes the task distribution, eligible
structure support and often difficulty together. It would not isolate neutral
operations: zero/one can also arise as intermediate values without a literal 1
in the inputs. Conversely, retaining input 1 does not prove every solution uses
a neutral operation. The intervention must manipulate the defined path property
while preserving or explicitly measuring the other factors.

The existing input-1 and identity-reference counts are useful design diagnostics,
not a ready-made causal intervention. The conceptual interaction design does not itself authorize a configuration,
statistical power claim or new GPU budget. The later C012 finite preparation
has its own narrower estimand and uses the existing remaining allowance.

The [CPU inventory check](../reports/SEMANTIC_CONTROL_FEASIBILITY_20260909.md)
found 41 problems with at least one stored path in each identity category and
zero with two of each. The naive current-inventory 2+2 construction therefore
fails. This does not rule out legal alternatives outside the stored four paths;
it establishes that the next construction needs a separately specified search
and support audit before any training.

The separately fixed [complete census](../reports/LEGAL_SUPPORT_CENSUS_20260909.md)
subsequently recovered disjoint-AC 2+2 support on 132/256 training questions and
4+4 support on 131/256. This diagnoses stored-inventory loss on part of the pool;
it still cannot supply the full original 256-problem 4+4 construction. Freeze a
matching-loss diagnostic was subsequently executed as C009, then C010/C013
completed the old global matching question. C011 diagnoses the restrictions
and C012 prepares the narrower absence-only alternative. The identity
categories remain numerical trajectory properties, not semantic classes.

## Stage 3 — independent pools, broader development and uncertainty

Once the intervention is feasible, select problem counts and the number of
independent training pools/seeds from a stated minimum meaningful contrast and
desired uncertainty. Use CPU simulations or an explicit design calculation with
plausible variance ranges. The present 64 selected dev problems and two seeds
cannot reliably supply all required variance components. Do not invent a power
percentage or declare an arbitrary seed count sufficient.

Sample and split raw number groups before solving or constructing paths, keeping
train, development and final reserved groups disjoint. Use independent training
pools as well as prespecified training/assignment seeds; report their effects
separately. Shared-structure selection blocks induce dependence, so uncertainty
calculations should respect problem pairing, blocks and independent training
replicates rather than treating every generated sample as an independent run.

Expand development coverage beyond the current eligibility-selected slice and
its small complement. Prespecify the population, sampling/selection rules and
any compositional split. Random unseen number groups do not by themselves make
a compositional OOD benchmark. Report target/operator/identity distributions,
selection fractions and matching residuals for each split. Broader development
should test the proposed boundary; it should not be selected to rescue a
particular metric after seeing the results.

Keep greedy correctness as the established pilot primary endpoint. A new study
may choose another estimand, such as an allocation-by-path-family interaction
or problem-level coverage, only in a new protocol frozen before its outputs.
Prespecify decoding counts and caps; additional draws improve within-problem
sampling resolution but do not remove training-seed or dataset-selection
uncertainty. Keep trace validity, syntax parsing and termination as distinct
outcomes, including unverifiable categories.

## Stage 4 — targeted boundary and sealed final evaluation

Choose one second model family or task because it tests a stated boundary, not
because a larger table appears more publishable. The planned OLMo-family check
could test dependence on the Qwen base; a typed graph/relational task could test
whether the intervention generalizes beyond arithmetic identities. Both require
separate feasibility, comparability and cost checks. The closest paper already
contains synthetic graph work, so adding a graph task alone does not establish
novelty. RL and an open-ended search over model/tuning recipes remain outside
this project scope.

Before final evaluation, freeze data construction, model/config hashes,
endpoints, decoding, stopping rules and the analysis code. Establish a genuinely
sealed final holdout with a documented access process. The current 2048 unsolved
reserved raw groups are useful separation, but are not yet a finished final test
benchmark or a technical access-control system. Keep them untouched while
building the new development protocol. Any final holdout construction/evaluation
is a later explicit decision; repeated tuning on it would invalidate its role.

Require reproducible commands, pinned dependencies, all failed/negative runs,
full exposure/resource receipts, raw compact predictions, and independently
verified model/ledger backups. A clone is only a migration convenience: every
replacement instance must recover the same history and outstanding budget.
Prepare an anonymized submission artifact separately from the identified public
GitHub repository. Human authors must review the evidence and interpretation.

## Paper and resource gates

A candidate paper should have a precise estimand, a substantive relation to the
closest prior work, a controlled intervention or informative boundary, credible
uncertainty across pools/seeds, and conclusions that survive the disclosed
limitations. A carefully bounded negative finding may be useful; venue ambition
cannot determine its sign. Exact accounting is necessary for the claim, but
accounting alone is unlikely to be the scientific contribution.

The [verified ICLR 2027 schedule and policy audit](../reports/ICLR_POSITIONING_20260909.md)
records a genuine-abstract deadline of September 18, 2026 at 23:59 AoE and a
full-paper deadline of September 25 at 23:59 AoE. Refer to that audit's official
sources for author, anonymity, profile and AI-disclosure requirements. These dates
are planning constraints, not a promise to meet this cycle. Decide readiness from
completed evidence before the genuine-abstract deadline; do not submit an empty
placeholder or imply that this roadmap is a submission authorization.

Only Stage 1 has a concrete near-term compute envelope. Prepare later stages on
CPU, measure the required model/evaluation workload, then present the exact
jobs, maximum reservation, storage/backup requirements and the decision they
will resolve. A800 80GB remains sufficient for the unchanged current recipe.
The completed pair used 1004 seconds, leaving 2484 of the original allowance.
This balance does not approve a main grid or create a reason to rent a larger GPU.
Once its backups finish, release the instance while the next design is prepared.
