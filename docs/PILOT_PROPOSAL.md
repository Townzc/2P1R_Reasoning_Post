# Scientific pilot proposal — awaiting review, no comparison launched

## Estimand and exposure correction

Estimate the effect of multiple canonical verified structures paired with each problem, relative to one structure per problem when the *exposure-weighted global* structural distribution is approximately matched. This is a narrow operational estimand; algebraic syntax is not a measure of human cognitive strategy.

Proposed first scientific pool: 256 shared eligible arithmetic problem groups, four distinct canonical structures per group, disjoint development and sealed holdout groups. Choose groups and path assignments jointly from an expanded candidate domain before any model outcomes are observed. Numeric range and target distribution must be frozen after the CPU eligibility audit; the existing 1..20 smoke fixture is not the final domain.

| Condition | Same 256 problems | Structures per problem | Renderings per structure | Presentations per problem per cycle |
|---|---|---|---|---|
| Repeat | Yes | One fixed anchor | One | Four identical copies |
| Surface | Yes | The same anchor as Repeat | Four | Each rendering once |
| Within-Problem Paths | Yes | Four | One each | Each structure once |
| Global-Coverage Matched (GCM) | Yes | One assigned structure | One | Four identical copies |

The proposed GCM repeats its assigned path four times. This explicitly replaces the draft's incompatible one-exposure row. It does not provide multiple paths to any individual problem. Common additional cycles repeat every arm's fixed dataset; surface renderings would then repeat too, and must be counted honestly. Breadth and Balanced are secondary and should not enlarge the first decisive comparison.

## Preflight matching proposal

Primary controls: identical optimizer updates and supervised response-token totals within **0.5%** pairwise; proposed global canonical-structure total variation residual **at most 0.02** between Within-Paths and GCM. These are proposed tolerances, not measured achievements. Prefer exact equality when feasible. Count EOS; do not truncate responses or pad useful-token budgets. Keep presentations per problem equal; jointly select eligible paths/renderings/anchor groups to meet the constraints rather than hiding changes in the sampler. Report per-update token distributions, operator counts, response lengths and processed-token/padding differences. A failure to meet tolerances stops the scientific pilot and returns a new design proposal.

The existing 32-problem fixture cannot serve as this GCM experiment. Its 128 Within-Paths presentations cover 53 canonical structures, while a single-path-per-problem arm can cover at most 32. Four identical exposures also force each GCM structural count to be divisible by four. The resulting **necessary TV lower bound is 0.2578125**, even before enforcing which structures each problem supports. See `reports/coverage_feasibility_fixture.json`; this is a mathematical bound computed from data, not a fitted experiment. Supervised totals are also unequal (7,676–8,156 tokens across existing arms).

## Pilot size and interpretation

After the overfit/profile gates and approval of the data/control definitions, run one paired engineering-calibrated seed on the intended 1.5B base model, using the same adaptation method and learning-rate schedule in every condition. Freeze update count and evaluation using only development data and measured throughput; record a new cost estimate before any grid. Three or more paired seeds, a second task, a second model family, and compositional holdouts are later evidence gates, not results available now. Do not infer a generalization effect or a universal ordering from the 32-example software check.

Review items: the explicit four-exposure GCM correction, approximate-matching tolerances, and candidate-domain/data-split design. No new server rental or extra compute authorization is implied.

## Candidate route to exact matching (not yet empirically validated)

Before accepting approximation, search for blocks of four different problems supporting the same four canonical structures, with the same response-token length for each corresponding structure across the block. In Within-Paths, use a four-by-four Latin-square assignment: every update presents each problem once and each structure once; across four updates each problem sees all four structures. In GCM, keep one different structure assigned to each problem and repeat that assignment for all four updates. Each update then has identical problem exposure, structural histogram and response-token total. This construction makes exact matching possible *if eligible blocks exist*. Matching all four structures to the same response length would also simplify the Repeat control. Surface renderings still need independent exact-token matching and a meaningful lexical-diversity audit.

This is a proposed construction, not an implemented data result. Report how many candidates it excludes; restricting problems to shared structure inventories may alter the task distribution. Do not silently replace full canonical structures with a coarse operator label to increase feasibility. A broader-pool sensitivity comparison would remain necessary before general claims.
