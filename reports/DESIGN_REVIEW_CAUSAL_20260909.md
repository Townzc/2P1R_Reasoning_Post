# Causal design review: define the allocation effect before constructing another task

**Independent reviewer memo, 2026-09-09. Status: proposed scientific design, not an approved protocol or compute request.** This review reads committed documentation and saved aggregate artifacts only. It does not generate model outputs, operate a server, inspect or solve reserved holdout questions, or change any existing experiment. The current scientific budget is 5,740 of 7,200 process-seconds used; the remaining 1,460 seconds do not authorize another phase.

**Decision:** stop extending the present arithmetic series. Preserve its results as a restricted allocation study and a documented warning about selection induced by exact controls. Develop a constructive task on CPU only after stating whether its intervention is *proof-route allocation*, *inference-schema allocation*, or a specified contrast between the two. A two-arm Paths/GCM comparison can identify a precisely defined allocation procedure at a fixed dose. It cannot isolate an abstract benefit of diversity while keeping conditional proof multiplicity, question–proof association, and repetition per proof unchanged: those are parts of the intervention.

This memo follows the project scope in [AGENTS.md](../AGENTS.md), [README.md](../README.md), [PROTOCOL.md](../docs/PROTOCOL.md), [DECISIONS.md](../docs/DECISIONS.md), and [STATUS.md](STATUS.md). Its empirical claims are grounded in the linked local reports; the proposed estimands, controls, and gates below are reviewer recommendations, not new empirical findings or literature-novelty claims.

## 1. What E010 establishes

The [E010 result report](ABSENT_BOUNDARY_SEED31_RESULTS.md) records the following frozen outcomes:

| Endpoint | Paths | GCM | Paths minus GCM |
|---|---:|---:|---:|
| Matched greedy final expression, original primary | 7/64 | 5/64 | +2 questions |
| Matched complete displayed trace | 4/64 | 4/64 | 0 |
| Broader greedy expression | 0/64 | 2/64 | −2 questions |
| Broader complete displayed trace | 0/64 | 2/64 | −2 questions |
| Matched complete sampled traces | 13/256 | 15/256 | −2 generations |

The primary paired cells are 3 both correct, 4 Paths-only, 2 GCM-only, and 55 neither. Only six matched questions disagree. These are evaluation observations from one training pair, not six or 64 independent replications of the training intervention. Four sampled generations from one question do not create four independent training units.

The run is technically interpretable: both arms completed 1,024 updates, 4,096 presentations, and 277,760 supervised tokens from the same frozen source; independent audits agree on all 800 outputs. Its low success and endpoint disagreement are scientific findings, not evidence of a failed execution that warrants a replacement seed.

E010 gives a conditional comparison of two specified path-allocation procedures on the selected 128-question population at seed 31. It does **not** identify:

- An identity-removal effect. Relative to the old pilot, training changed from 256 to 128 questions, from 16 to 32 presentations per question, from 267,456 to 277,760 supervised tokens, and changed selected trajectories and the joint seed. The old checkpoints are not the counterfactual for E010.
- The necessity or causal role of numerical identities. A small uncertain effect in an identity-absent family cannot show that identities caused the earlier result. Identity absence also permits cancellation and computed constants under the declared label.
- A zero allocation effect, a reliable positive effect, broader arithmetic transfer, or hidden-reasoning faithfulness.
- General undertraining of Paths. GCM's lower training NLL and 16/16 versus 11/16 fixed train diagnostic are compatible with different supervised target distributions and other explanations. They do not justify extending only Paths or selecting its best checkpoint.

The old seed 17 and seed 23 primary gaps of five questions remain two observations on one selected training pool and the same small evaluation slices. Pooling their scores with E010 as three exchangeable replications would erase a material change in the estimand.

## 2. State the estimand as an allocation intervention

Let a generator define a population of questions and legal proofs. A training draw D contains questions q_i, each with K selected valid proofs p_i1,…,p_iK. Let S(p) be a *prespecified* proof-schema label. Freeze the selected proof inventory before treatment assignment; an arm cannot obtain easier questions or independently select a preferred proof family.

Define two training datasets with the same questions and N presentations per question, with N divisible by K:

- **Within (W):** present each of the K proofs N/K times for every q_i.
- **Global matched single proof (C):** choose one proof p_i,A_i through a declared balanced randomization, and present that fixed proof N times for q_i.

Both start independently from the same pinned base model and use the same declared optimizer recipe, supervised-token budget T, and number of updates U. A changes proof allocation; O controls presentation order and R controls model-training randomness. Write M_z(D,A,O,R;T,U) for the resulting trained model. For a predeclared evaluation population E and correctness score Y, the population target is

    Δ = E_{D,A,O,R}[ E_{q ~ E}[Y(M_W, q) − Y(M_C, q)] ].

An experiment with fixed D,A,O,R estimates only its corresponding realized contrast. Generalizing over generated datasets or random assignments requires actually sampling those dimensions. A balanced randomized control defines an average over its specified feasible assignment distribution; it is not an average over every possible single-proof training set.

The scientific sentence should be: **At fixed training-question exposure, global schema frequency, supervised tokens, and updates, what changes when supervision is distributed across K legal proofs per question instead of concentrated on one fixed proof?** This is a useful falsifiable question. It describes replacing repeated proof exposures with alternative proof exposures. It is not a factorial effect of K holding repetition per proof fixed: with fixed question count and dose, those quantities cannot all be fixed independently.

If E is the generator's IID distribution, label the result accordingly. A second evaluation distribution must explicitly define the change in composition, depth, graph topology, or proof availability. Merely drawing new entity names or unseen random questions does not establish compositional generalization.

## 3. Separate treatment components from nuisance features

The treatment necessarily changes the number of distinct proof targets per prompt, their conditional distribution, exposure per proof, and the association between questions and proof schemas. These are not accidental confounders to be adjusted away after training.

For example, in a balanced construction with K equally frequent schemas, W can have H(S|Q)=log K while C has H(S|Q)=0, despite identical H(S)=log K. Matching the full joint distribution of question and schema would remove this particular intervention. Likewise, making C choose a new proof each epoch eventually turns it into another within-question condition; it is not a cleaner fixed-single-proof control.

At the same time, choosing more proofs need not require longer proofs, larger arithmetic intermediates, different distractor counts, or a different answer distribution. These are candidate nuisance dimensions **only after** the scientific question states that they should be held fixed. Use a three-column inventory before generating data:

| Category | Examples | Required handling |
|---|---|---|
| Intended treatment components | Proof count per question; proof/schema association; repetition per proof; proof-related target ambiguity | Define and retain; do not match them away or statistically adjust for them as if pretreatment covariates |
| Fixed question properties | Query, answer, graph, candidate answers, distractors, input order policy, available legal proof support | Use exactly the same questions and prompts in both arms; document generator and split rules |
| Prespecified proof nuisance vector C(q,p) | Length, inference count, branch/depth profile when outside the intervention, rule counts, operand magnitudes, intermediate values, rendering | Match by construction at the stated level, or retain a narrower allocation-bundle claim and disclose residuals |

If the desired claim excludes a proof nuisance C, the strongest simple design makes C(q_i,p_ij) equal across all candidate j for each question. That controls the nuisance without requiring equality of the entire proof distribution. Some intended schema contrasts make this impossible: chain-versus-branch may intrinsically change depth or dependency structure. In that case, either treat those differences as part of the specified intervention or choose a different contrast. An impossible match is a reason to revise the claim, not to assert that randomization equalizes difficulty in each realized run.

The [pairing-seed audit](PAIRING_SEED_SEMANTIC_AUDIT_20260909.md) illustrates the distinction. Canonical structures match at every update, but 180/256 questions have at least one audited numerical-feature residual in each old seed. GCM's assigned path changes on 196/256 questions across seeds, and at least one audited feature changes on 99/256. Globally, identity exposures are 2,780 versus 2,800 in both seeds; near equality of a marginal total does not imply the same feature is presented on the same questions.

E010 improves several global/update matches but still has per-question mean-depth residuals on 120/128 questions, negative-intermediate residuals on 52/128, and intermediate-magnitude differences on 600/1,024 updates. These are recorded in the [completed selection analysis](MATCHING_COMPLETION_AND_TRAINING_20260909.md). They do not invalidate the exact checks that actually passed. They do invalidate an unqualified assertion that numerical difficulty or semantic exposure was equal.

Lower training NLL is especially unsuitable as a nuisance-balancing target. Uniform distinct proof strings induce a different empirical target distribution from a repeated fixed target. A surface arm with K uniformly used strings can match string cardinality and empirical sequence entropy, but still differs in where tokens branch and what they mean. Training loss is an outcome of the training distribution and optimizer, not an independent measurement of intrinsic question difficulty.

## 4. Global matching needs a declared representation and level

“Global coverage matched” must name the map S and the actual weighting. Matching a set of observed labels is weaker than matching their exposure-weighted frequencies. Matching schema labels is weaker than matching all joint features of proofs. Matching the full question–proof multiset is incompatible with the intended W/C contrast.

The minimum schedule audit should verify:

1. Identical question identities, order, and presentation counts at corresponding updates.
2. Exact counts of the prespecified schema labels under actual presented exposures, not only unique stored rows.
3. Equal EOS-inclusive supervised-token totals and updates; preferably equal totals at every update under the existing token-normalized loss. Match processed tokens and report padding as well.
4. Histograms of the declared nuisance vector at global, update, and question levels, including specified joint distributions. Do not report only means when a tail or a schema–difficulty association matters.
5. The randomization algorithm, its support, inclusion probabilities where known, and all rejected assignments. No choosing the best-balanced-looking seed after outcomes.

Blocks with K questions and K schemas admit a transparent schedule: C assigns one schema to each question through a fixed permutation; W cycles through K permutations. Every question sees N examples, and each update can contain the same schema histogram. This is sufficient only if every question legally supports all assigned proofs and all claimed token/nuisance checks pass. A block is an allocation device, not necessarily an independent statistical unit: blocks sharing a latent graph or template remain dependent.

Matching in expectation over A is a legitimate *different* design. It does not give exact realized token budgets or the same per-update normalizer. If exact matching requires severe question exclusion, either design token lengths into the representation before sampling questions or explicitly propose a randomized approximate-balance study. Do not silently replace the current fixed-budget estimand with expected-budget equality. Do not add meaningless tokens or truncate valid derivations to manufacture matching.

## 5. Question selection is a separate problem from within-pair balance

Using the same selected questions in both arms protects their conditional contrast. It does not make the selected population representative. Selection becomes especially consequential when the claim concerns all arithmetic problems, or when old and new effect estimates use different populations.

The selection costs are empirical, not hypothetical. The [completed CPU analysis](MATCHING_COMPLETION_AND_TRAINING_20260909.md) finds:

- The old two-family common-length construction supports only 63 questions and 15 disjoint blocks; 56/63 targets equal an input and no target exceeds 40.
- Relaxing cross-family lengths gives 129 locally feasible questions without the distinct-structure constraint, but adding that constraint reduces support to 84 and again eliminates all targets at least 41. Token matching alone is not the entire cause.
- E010's selected 128 questions contain 33 high targets, 18 input-one questions, and 55 targets equal to an input, versus 105, 96, and 59 respectively in the original 256-question pool.

Randomly selecting 32 blocks from one optimal packing does not give a uniform sample of every feasible question population. A complete solver establishes feasibility, not representativeness. Reweighting cannot recover a stratum with zero inclusion probability, and it cannot reconstruct the effect of training a nonlinear model on a training population that was never used.

A constructive generator avoids the *search* for rare multi-proof support by defining a population where that support is guaranteed. It still defines a deliberately restricted world. Sample latent problem structure before labels/renderings; guarantee the advertised K-proof property for every permitted draw; report all subsequent rejection stages. Split latent graphs or semantic instances before generating queries, proof variants, entity renamings, or textual renderings. A held-out renaming of the same graph skeleton is insufficient for a topology-generalization claim. If schemas themselves are held out, say explicitly that this tests a different boundary from interpolation among globally trained schemas.

## 6. Minimum comparison and controls that earn additional claims

| Control/comparison | Role | Decision |
|---|---|---|
| W versus fixed-single-proof GCM | Identifies the declared within-question allocation effect at matched global schema exposure and dose | Necessary core; two arms are sufficient for this narrow claim |
| Arbitrary Repeat anchor | Provides a reference for uncontrolled global schema coverage | Optional; GCM already supplies a repeated-single-proof comparator |
| GCM with K surface renderings of its one proof | Tests whether multiple target strings or rendering variation can account for a claimed advantage | Necessary before claiming benefit beyond the tested surface alternative; not required for the narrow procedural W/C claim |
| Factorial allocation × rendering | Tests whether the allocation effect persists under a common rendering policy and whether they interact | Stronger alternative to a three-arm screen when that interaction is central; must match global renderer exposure and dose |
| Same-question path-family factorial | Estimates allocation effects within each defined family and their interaction | Necessary for a causal family-interaction claim; unsupported families/populations cannot substitute for missing cells |
| Breadth or answer-only SFT | Compares other uses of a budget | Optional separate allocation questions; changes supervision/task variables and does not repair W/C identification |
| Longer training, alternate learning rates, additional models | Tests dose/recipe/model boundaries under a new fixed plan | Optional later; do not use one-arm optimization to rescue the primary pair |

Surface variation must preserve proof facts and inference structure. Renaming entities inside both question and answer creates another prompt instance and can change problem exposure; it is not automatically a response-only Surface control. Even a valid Surface control establishes only the tested rendering alternative. It does not prove that every possible lexical or optimization explanation has been excluded.

An identity-family factorial would require the same questions in all four cells and an explicit account of cross-family dose, rule composition, and computation. A statistically detectable interaction would still be an interaction between those complete defined families, not automatically the pure effect of one identity operator.

## 7. Objections a constructive graph or relational task must answer

**Different routes may be one schema.** K equal-length paths through different intermediate nodes can all be the same repeated-transitivity rule chain. That tests route/evidence diversity. Node names, edge order, proof serialization, or traversal order do not by themselves create a new inference strategy. Count proof paths, premise sets, dependency DAGs, rule sequences, and quotient classes separately. Define which symmetries the study removes, and show the proposed distinction survives them.

**Making schemas more different can reintroduce difficulty differences.** A chain and a conjunctive branch may differ in number of facts, rule applications, depth, branching, intermediate search burden, and answer ambiguity. Matching final text length does not match these properties. Typed relations or different rule names can also create label-frequency cues. Record the intended difference and nuisance vector for each candidate; do not call all such routes equally difficult by inspection.

**Planted proofs can leak the answer.** A graph generator that always plants K positive proofs can yield an always-yes task. In an entity-answer task, a unique planted hub, degree pattern, name position, repeated endpoint, relation suffix, or sorted premise position can reveal the target. For Boolean queries, include controlled false cases with the same superficial statistics; for entity selection, balance candidate roles and prove answer uniqueness. A question that requests a witness between two given endpoints is a valid task, but its copied endpoint is not evidence of answer inference.

**Witness support must be real.** Validate every derivation against explicit rules, including variable binding and directionality. Check for unintended direct shortcuts, shorter proofs, accidental extra answers, contradictions, and interactions among planted routes. Enumerate the complete small-task universe or use an independent solver where feasible. A known planted witness proves existence; it does not prove uniqueness, minimality, or absence of easier alternatives.

**Robustness interventions can change the question.** Removing one route after training can test dependence on that route, but only if the modified instance remains well-defined and its answer is independently verified. If route removal changes the answer or available support, its score cannot be treated as the same original endpoint. Freeze this as a separate evaluation distribution.

**Construction can reduce effective diversity.** Thousands of entity substitutions of a few planted gadgets do not supply thousands of independent reasoning structures. Hold out latent construction families appropriate to the claim, report concentration, and test shortcut-only algorithms on new CPU development examples. A lookup baseline using names, degrees, edge counts, answer frequency, or relation-token statistics should not solve the intended benchmark. Passing these audits narrows known shortcuts; it never proves absence of every shortcut.

The strongest immediate candidate is therefore the one whose path distinction, legality, and nuisance controls can be demonstrated on a small exhaustive example set. A graph domain is not scientifically preferable merely because it has more solutions than Countdown.

### Specific candidate: consistent S5 bijections on four disjoint chains

The parallel construction review proposes hidden vertex potentials in S5, exposed edge bijections, four equal-length vertex-disjoint routes, and the query y=T_s→t(x). This is a proposal reviewed conceptually here, not an implemented or verified generator. If edge maps are derived consistently from hidden potentials, route compositions can agree by construction. That addresses contradictory answers; it does not create four inference schemas. All four chains still apply the same composition procedure and can be exchanged by a graph automorphism. Forward/backward presentation is not independently established as a different reasoning strategy.

For this candidate, **evidence-route allocation** is the defensible immediate label. Global inference-schema matching is largely automatic because the algorithm is shared. Equal counts of arbitrary latent route slots establish assignment balance, not a substantive control for global strategy coverage. The study must distinguish actual premise-set choices from those arbitrary slot names. Randomize route order and entity labels independently of target value, keep hidden potentials hidden, and audit whether the serialization exposes a preferred route or an endpoint shortcut. Per-route intermediate states, permutation properties, and lookup direction still need descriptive exposure checks; equal chain length does not prove equal model difficulty.

A prespecified edge-deletion evaluation could add a meaningful, falsifiable boundary. On every evaluation graph, choose a route and an edge using a model-independent seeded rule, remove that edge, and independently verify that the correct answer is unchanged and legal alternate routes remain. Use the same modified instances for both models. Score all original sampled questions, including those either model failed before deletion. Report the clean contrast Δ_full, the deletion contrast Δ_drop, and the interaction Δ_drop−Δ_full, with uncertainty clustered by original graph and training replication. A paired clean/deleted example is not two independent tasks.

Do not choose the deleted route from a generated proof, from whichever route a model appears to prefer, or from a baseline-success subset for the primary analysis. Those rules make the evaluation intervention or sampled population depend on model behavior. A separate explicitly adaptive attack may be studied later, but it answers a different question and must not replace the model-independent endpoint. For new test graphs, a supposed “trained preferred route” is particularly ill-defined unless the construction exposes a consistent route-selection convention, which itself creates a shortcut to audit.

This boundary can test whether within-question evidence supervision improves robustness to loss of one available proof route. It cannot by itself establish hidden route reliance, semantic strategy diversity, or novelty relative to the closest prior work. Its value depends on an explicit competing prediction and on showing that the gain survives label/order shortcuts and the tested surface alternative. No implementation, dataset materialization, or GPU run follows from this suggestion.

## 8. Evaluation and seed plan

For a new protocol, freeze one primary behavioral endpoint before model outcomes. Greedy answer correctness preserves continuity; if the scientific object is valid proof construction, it is also defensible to preregister a new primary of **correct answer plus a fully valid proof**. That would be a new-study decision, never a retrospective replacement of E010's endpoint. Always report answer and proof correctness separately. Accept every valid proof under the declared verifier, rather than only the planted or canonical reference; otherwise the evaluation mechanically rewards reference imitation and may favor one allocation policy.

Use one IID generator test and one specifically motivated boundary test. Stratify by the predetermined schema/support/complexity factors and retain unfavorable strata. Sampled success and proof diversity are secondary and must share a fixed decoding budget. Report proof diversity conditional on validity as well as unconditional validity; otherwise invalid novel strings can inflate diversity. Reference NLL, parse failures, lengths, termination, and train fit remain diagnostics. Do not replace them with hidden-reasoning or faithfulness claims.

The original reserved arithmetic holdout stays untouched. A new task requires its own frozen development and final-evaluation generation rules. Separate development calibration from the later confirmatory set, including latent templates and all variants. Decide final-set size using desired precision for paired contrasts and realistic cluster dependence; 64 questions or four samples per question is not a power justification.

Separate RNG namespaces for generator/pool, selection, assignment A, order O, training R, and sampled evaluation. Pair arms on the same pool, base model, question order, and training-seed setting. Sharing a seed improves comparability but does not create independent training replications or guarantee identical random-number consumption in data-dependent computation.

The **model-training run** is the treatment unit. Proof-allocation blocks are randomized inside a run, while all their gradients affect one shared model. Evaluation questions are measurement units and must be paired across models; questions from the same latent graph/template are clustered. A problem-level bootstrap alone conditions on trained models and omits training-population/seed uncertainty. Do not label it uncertainty for the full Δ above.

A practical later planning floor is three independently generated training pools and two prespecified paired RNG bundles per pool, giving six W/C pairs. This is a proposed coverage floor, **not** a power calculation or a claim of adequate precision. Jointly sampled assignment/order/training bundles estimate their combined variation; they cannot identify which source caused it. If separating assignment sensitivity from optimizer randomness is a scientific objective, cross at least two assignment maps with at least two training seeds within each pool and keep order separately specified. When W is identical across assignment maps, its checkpoint may be reused for computational efficiency, but all contrasts sharing it are dependent and must be analyzed that way.

Before authorizing such a study, choose a minimum useful effect δ and precision goal, simulate plausible between-pool, between-run, and evaluation-cluster variation on CPU, and price the full finite design. The present sparse arithmetic results cannot reliably supply all these variance components for a new graph task. Additional seeds must be chosen prospectively and retained irrespective of sign. A conditional feasibility pilot can be smaller, but it cannot be promoted into population evidence because it happens to be positive.

## 9. Stop and kill criteria

**Before any new GPU proposal:** stop the candidate if its formal verifier fails; the advertised K-proof guarantee fails on allowed draws; the claimed proof distinction collapses under its declared equivalence relation; train/test semantic instances overlap; the answer is derivable by a prohibited shortcut; or exact budget checks fail. Fix the generator or narrow the question in a versioned CPU design. Do not silently prune failed examples until only a favorable domain remains.

**Before scaling a pilot:** freeze and require an arm-neutral capability gate with nontrivial success on the intended task and prespecified acceptable formatting/truncation rates. Choose thresholds and the calibration sample before outputs, using the task's answer baseline. A floor-level or ceiling-level endpoint cannot efficiently answer the proposed question; changing complexity after observing treatment gaps starts a new design version. Do not require equal training losses or equal convergence endpoints between arms.

**At the end of the fixed scientific batch:** evaluate the predeclared primary effect and interval at the correct replication level. If the upper uncertainty bound is below the chosen useful δ, stop pursuing a practically meaningful positive effect under that design. If the interval is wide, call the result unresolved and use only a preplanned continuation rule, not an open-ended search. If the claimed benefit appears only on answer correctness while valid-proof correctness or the required boundary test is adverse, narrow the claim and do not scale a general reasoning story. Preserve every run and secondary result.

**For the proposed contribution:** abandon or narrow a strategy-diversity claim if the surviving distinction is only lexical renaming, premise ordering, or parallel copies of one rule chain. A well-controlled route-allocation boundary or negative result can still be scientifically useful. Tighter accounting and more positive seeds, without a distinct falsifiable question and population-level evidence, are not by themselves an ICLR-quality contribution; the project's [positioning report](ICLR_POSITIONING_20260909.md) already records direct overlap with the broad question.

The next reviewable milestone should contain a generator specification, formal path equivalence and nuisance vector, a tiny fully verified example gallery, a complete CPU support/shortcut/split audit, one primary contrast with claim-specific controls, and a finite seed/evaluation/cost plan. That milestone can be prepared without another server or any use of the reserved holdout.
