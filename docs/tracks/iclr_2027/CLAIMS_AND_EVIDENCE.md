# Claims, evidence, and the novelty gap

September 11, 2026. The labels below distinguish completed observations,
post-hoc diagnostics, operational readiness, and hypotheses. No new model
measurement was made for this inventory.

## Current claim-to-evidence map

| ID / status | Supported statement and exact evidence | Interpretation limit | Missing evidence for a stronger statement |
| --- | --- | --- | --- |
| C1 / observed | E015's final configuration passes the unchanged 32-parent overfit gate: 32/32 correct and terminated, zero truncations, NLL 0.001106. [Result](../../../reports/REAL_MATH_E015_RESULTS.md) | It demonstrates memorization. E013/E015 trajectories already diverged before terminal decay; this is not an isolated LR effect | Independent retained learning and held-out outcomes under the chosen scientific recipe |
| C2 / observed | On the 64 E016 development parents, clean correctness is base 26/64 versus E015 0/64; 26 paired losses and zero gains. Base truncation 14/64 exceeds 8/64, so both screens fail. [Result](../../../reports/REAL_MATH_E016_RESULTS.md), [frozen metrics](../../../runs/gsm8k_capability_e016_r1/metrics.json) | Missing answer markers alone cannot explain E015, which parses 62/64. These are observed development outcomes, not a general forgetting theorem or proof of a specific optimizer cause | Prospectively calibrated completion plus one bounded retained-learning recipe; larger scientific dose requires its own check |
| C3 / post-hoc | C020 finds 13 of the base's 14 truncated streams continue after a new-question header; saved first-task prefixes count 39/64 correct versus E015 0/64. [Audit](../../../reports/REAL_MATH_C020_COMPLETION_AUDIT.md) | Text-prefix counts do not revise E016 or establish actual stopping speed. E016's own marked-answer 39/64 is a separate recorded metric | E017's actual batched generation, raw-prefix audit, and measured stop/latency report |
| C4 / ready, not run | E017 has 62 CPU passes, two Linux watchdog checks pending, independent 160-stream replay, exact observed inputs, and a verified transfer release. [Readiness](../../../reports/REAL_MATH_E017_READY.md) | Scripted generation and saved-token replay are not new task accuracy or hardware throughput | One already authorized 64-parent run after owner startup; no additional experiment approval needed for its accepted specification |
| C5 / restricted observation | Synthetic Paths/GCM matched greedy scores are 23/64 vs 18/64 at seed17 and 22/64 vs 17/64 at seed23. [Seed17](../../../reports/PILOT_V1_RESULTS.md), [seed23](../../../reports/PILOT_REPLICATION_SEED23_RESULTS.md) | Same strongly selected training/evaluation pool; broader scores are weak. Neither a real-math allocation finding nor two independent populations | A valid real-data contrast with preserved repetition control and independent evaluation |
| C6 / boundary observation | The separately selected identity-absent pair has greedy 7/64 vs 5/64, complete traces 4/64 each, broader 0/64 vs 2/64. [Result](../../../reports/ABSENT_BOUNDARY_SEED31_RESULTS.md) | Endpoint-dependent and weak. Changing the population prevents a causal identity-removal comparison with the old pair | A new controlled mechanism study, outside the default sprint |
| C7 / CPU data feasibility | C017 nominal Repeat/Solutions/Mixed/Breadth contain 253/996/1,011/1,013 accepted pairs; proposed schedules match 524,288 supervised tokens and 256 updates. [Audit](../../../reports/REAL_MATH_CPU_AUDIT_20260910.md) | Missing parents, variable K, length-dependent remainder weighting and unequal per-update tokens remain. Correct final answers do not certify every reasoning step | Raw-text/mask release and quality review for the selected scientific arms, then actual learning and held-out results |
| C8 / unknown | E018 retention, the real-data allocation ranking, a causal explanation, and measured teacher acquisition costs are all unknown. [P006](../../experiments/P006_evaluation_and_capability_preservation.md), [P004](../../experiments/P004_cost_aware_sft_allocation_proposal.md) | Public released candidates do not reveal all attempted generations, failures, deduplication effort, or original expense | Separately reviewed experiments; real acquisition measurement belongs to continued research |

All original failed experiments and superseded preparations remain part of the
record. None is silently replaced by a new score, model, dataset, or workstream.

## Five direct prior-work challenges

Primary sources were checked on September 11. The distinctions in the last
column are proposed research obligations, not verified novelty.

| Close work and location | What it already studies | Consequence for the sprint |
| --- | --- | --- |
| [Generalization in LLM Problem Solving: The Case of the Shortest Path](https://arxiv.org/html/2604.15306v1), ICLR 2026, Sec. 4.1–4.3 and Appendix E | Directly compares allocating records to more questions or more answers; includes a MathQA study and reports benefits from broader question coverage | Explicitly confront this result. Repeating the question on GSM8K does not establish an increment; a credible boundary needs controlled and replicated evidence |
| [OpenMathInstruct-2](https://proceedings.iclr.cc/paper_files/paper/2025/file/302ce0673c00aee2cf84bb43d0117553-Paper-Conference.pdf), ICLR 2025, Sec. 2.2.4/Fig. 6 | Varies distinct questions at 256K question–solution pairs and observes a substantial question-diversity effect; also analyzes solution format and quality | A fixed-pair breadth/depth plot is already precedent. Equal tokens and updates improve control but are not automatically a new scientific finding |
| [Why Do Reasoning Models Lose Coverage?](https://arxiv.org/html/2605.17026v2), Sec. 4.2.1 and 5 | Compares problem-level and dataset-level NL/code diversity on GSM8K; examines pass@k shrinkage and mitigation | Do not claim to introduce within-problem diversity or coverage analysis. Paired survival of greedy base successes is a different measurement, not a synonym for their sampled coverage or proof of a new mechanism |
| [Data Repetition Beats Data Scaling](https://arxiv.org/html/2602.11149v1), Sec. 2 and 4 | Shows repetition benefits under fixed updates in long-CoT SFT; studies memorization, termination and forgetting | Retain an exact-repeat control. Our 32-parent failure neither refutes its matched-budget results nor establishes an opposite universal rule |
| [Spend Wisely](https://arxiv.org/html/2501.18962v2), abstract and budget-allocation framework | Studies how to distribute generation/training budgets across iterative synthetic-data bootstrapping | Avoid a first-cost-aware-allocation claim. The sprint does not measure an acquisition policy, and a price formula cannot fill that gap |

Small model size, shorter solutions, a different dataset, per-question loss/gain
tables, or cleaner accounting are setting/method differences. Their combination
is still not sufficient evidence of novelty. The September 17 review must state
an actual, nontrivial finding and the prior inference it changes. If it cannot,
the work remains a careful replication or feasibility study and continues later.

## Candidate claim and falsification

**Candidate, not a result:** under a declared small-model, retained-learning SFT
regime, the marginal held-out value of additional natural-language solutions
can be separated from exact repetition and problem breadth, with completion
failures and lost base successes measured rather than hidden by an aggregate
score. The sign of the effect is deliberately unspecified.

The primary contrast is Solutions minus Repeat at fixed P, supervised tokens,
and updates. Breadth is the essential allocation baseline. These comparisons
can establish a local empirical effect, not semantic strategy diversity,
global primitive matching, general preservation of knowledge, or an optimal
acquisition policy. No core scientific contrast has yet run.

Potentially informative outcomes include a reproducible benefit, a reproducible
harm, or a sufficiently precise absence of a practically meaningful difference.
Each still requires a substantive novelty case. A small noisy difference,
failed retention screen, mismatch in training dose, or effect confined to a
post-hoc subgroup falsifies the proposed strong interpretation. New successes
cannot erase gross loss in the retained-learning gate.

## Exposure inventory shared by the project

| Population | Status at this milestone | Proposed use; never an automatic release |
| --- | --- | --- |
| GSM8K development ranks 1–16 | Observed in E013 and saved-output analysis | Historical diagnosis only |
| Development ranks 17–80 | Observed in E016; E017 will reuse exactly these 64 | Stopping and retained-learning calibration |
| Development ranks 81–144 | Reserved, not opened in this milestone | P006 Stage C only after a frozen passing E018 recipe |
| Development ranks 145–512 | Reserved, not opened in this milestone | Proposed 368-parent scientific development block after all endpoints and analysis are frozen |
| Official GSM8K test, 1,319 questions | Unevaluated by this project; not opened in this milestone | One separately authorized frozen final evaluation |
| C017 independent training draw | Reserved for future training-pool validation | Not an independent replication already supplied by seed23 |
| Synthetic final holdout and MATH final tests | Remain unexposed to model evaluation | Outside the default sprint |

There are currently 80 observed and 432 reserved GSM8K development parents.
Stage C would leave 368; the scientific development block would then leave
zero in that original 512-parent reserve. Record each approved exposure once
in the shared history. A later workstream must not call these populations
fresh. Project split hygiene does not certify absence from model pretraining.

## Immediate evidentiary checkpoint

E017 can answer whether the implemented completion contract passes its frozen
operational screen. It cannot answer whether LoRA preserves capability or
whether additional solutions help. At present the best-supported statement is
that engineering memorization and better output formatting were insufficient
for development capability retention in this configuration. That motivates the
next check; it is not by itself the promised ICLR contribution.
