[21:00 PDT中期冻结材料](reports/p008_20261013/midpoint_freeze_20261013_2100PDT_v1/READINESS.md)：使用截止前原字节；未完审计明确pending，后续单列。

P008 最新：18学生与base全部完成并通过本地核验，8/8 T8结果与完整注册统计/3图已获真实外审G3 PASS。[冻结后解读](reports/p008_20261013/post_freeze_results_review_v1/FACTS_ADDENDUM.md)明确高B带题价的depth优势只在D2出现、D1未复现；不称稳定效果。原21:00材料及原N2 FAIL/9600事后修订记录保持不变。最终CPU核验仍待数值审计与执行。

# Problems, Paths, or Repeats?

Allocating data-acquisition budgets for reasoning SFT. Working branch: [`codex/icml-acl-2027`](https://github.com/Townzc/2P1R_Reasoning_Post/tree/codex/icml-acl-2027); the default `main` is historical. This repository is a research evidence record, not presentation or assignment prose.

**Status, October13 06:24UTC / October12 23:24PDT:** the finite P007B comparison is fully closed. Eight students,10,552 formal outputs,2,048 updates,4,194,296 supervised targets and eight complete terminal states passed local checks. CPU evidence covers14 directories:10 fully checked by the original audit and4 by the bounded continuation. The original timeout remains a failure. All owned GPU/CPU containers exited; no new model jobs are queued.

## Evidence and current result

- [Verified midpoint facts and limitations](reports/sft_allocation_midpoint_20261011/P007B_MIDPOINT_EVIDENCE.md)
- [Primary contrast figure](reports/sft_allocation_midpoint_20261011/figures_token_v2/policy_gaps_and_price_interaction.png), [accuracy context figure](reports/sft_allocation_midpoint_20261011/figures_token_v2/accuracy_by_price_and_seed.png)
- [Final audit packet and recomputation scope](reports/p007_audit/token_final_v1/REVIEW_REQUEST.md)
- [Workboard](docs/WORKBOARD.md), [collaboration handoff](docs/COLLABORATION.md), [reusable workflow](docs/RESEARCH_WORKFLOW_ZH.md)
- [Post-midpoint engineering/research proposals — not executed](docs/P007_NEXT_PHASE_PLAN_20261013.md)
- [Execution log](reports/sft_allocation_midpoint_20261011/RUN_LOG.md), [AI-use log](AI_USE_LOG.md), [historical record](docs/LOG.md)

P007B holds a hypothetical acquisition cap and student training resources separately fixed. Each Qwen2.5-1.5B base/LoRA student uses256 updates and524287 supervised targets, complete answers, prompt/padding masking and one frozen learning-rate vector. All1,319 evaluation questions are generated once at the final checkpoint. Length caps and known parser false negatives remain under the frozen primary rule.

| Problem price | Policy | seed17 /1319 | seed23 /1319 | Mean accuracy |
|---|---|---:|---:|---:|
|0|More problems|963|958|72.82%|
|0|More solutions|950|958|72.33%|
|4m|More problems|927|949|71.11%|
|4m|More solutions|952|949|72.06%|

Mean depth−breadth is **−0.49pp** at price0, conditional95% interval[−2.24,1.25]; **+0.95pp** at price4m,[−0.83,2.73]. The price interaction is **+1.44pp**, interval[−0.95,3.87]. The seed17 point-estimate ordering change is not repeated by seed23, which ties at both prices. There is no established stable winner, equivalence, or general price threshold.

Intervals resample shared questions after averaging the two observed seeds. They condition on these models and inventories; they are not training-seed or procurement confidence intervals. Each cell has one random teacher trace, reused by both training seeds. Common cap211257 hypothetical token units leaves6.14%/6.88%/12.26%/10.90% unused; this is not equal realized spending or actual API dollars. Fixed training targets imply unequal repeat exposure. Neither final-answer correctness nor distinct text establishes reasoning quality or structural diversity. The official benchmark was already observed by this research effort in September.

Claude [round15](https://github.com/Townzc/2P1R_Reasoning_Post/blob/3e3e33d3652e813a7685c2fb5bd6315b5448ccb5/audit/claude/20261013h/REPORT.md) gives the final packet and factual evidence page **PASS**, and the original figures **PASS-WITH-NOTES**, at fixed commit736b3920. A new v2 accuracy plot fixes overlapping markers/legend without changing results; that display revision is now PASS in [Claude v3 response](https://github.com/Townzc/2P1R_Reasoning_Post/blob/4dfd22f6b28c0b99e7bbe0d27c4dbf6ca2a4ce74/audit/claude/20261013j/P008_V3_RESPONSE.md). [Scope and disposition](docs/audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md).

**P008:** Both draws/common inputs passed G1. All18logicalstudents+base now have complete local raw/dose/state verification and stopped providers. T8 totals are D1/p0 breadth967,depth965; D1/p4 breadth945,depth939; D2/p0 breadth956,depth971; D2/p4 breadth935,depth990, each/1319. Caps39/50/56/47/51/45/45/36 remain incorrect. All eight T8 outcomes have independent G3 PASS at their exact packets. [Complete registered primary tables and plots](reports/p008_20261013/registered_primary_results_v1/FACTS_AND_LIMITS.md) retain all19cells/31contrasts and conditional paired-question intervals; the complete analysis and figures have actual G3 PASS; final CPU integrity remains pending. The positive B8/price4m gap appears in D2 only and is not replicated in D1; see the separate post-freeze interpretation addendum. No stable policy winner, equality or full budget-by-training interaction is claimed. Original N2FAIL and owner/independently accepted9600-second post-hoc engineering deviation, all failed physical parents and21PDT material freeze remain explicit.

## Previous stages, kept separate

The earlier OpenMathInstruct-2 inventory experiment uses a different teacher source and431-question development endpoint:

| Arm | seed17 /431 | seed23 /431 | Mean accuracy |
|---|---:|---:|---:|
|Repeat|309|307|71.46%|
|Solutions|354|355|82.25%|
|Breadth|350|352|81.44%|
|Mixed|348|351|81.09%|
|Base|256|—|59.40%|

Solutions−Repeat is+10.79pp; Breadth−Solutions is−0.81pp, interval[−3.71,2.20]. These do not isolate path diversity or repetition harm. Historical bank acquisition cost is unknown. [Main audit packet](reports/p007_audit/main_v1/REVIEW_REQUEST.md) and [scientific plan](docs/experiments/P007_midpoint_allocation_plan.md).

P007A yielded1,024 physical attempts:959 usable,59 invalid and6 rejected valid duplicates. [Pilot](reports/sft_allocation_midpoint_20261011/P007A_RESULTS_20261012.json). All four subsequent procurement cells preserve2,064 physical outputs and failures. Claude identified speed confounding in the original time-based cost interpretation; the owner approved the [uniform-token revision](docs/experiments/P007B_token_tariff_revision.md). Two already-running time-priced students finished953/969 of1319 and remain operational pilots, separate from the new eight. The six untouched original students and their audit are retired. Failed work, old unknown diagnostic attempts, interrupted audits and transport repairs remain recorded.

## Cost and delivery

Workspace delayed meter is **$224.56193173 at October14 03:19:49UTC**, billed$0; P008-labeled monthly rows total$135.30891807. This is not an invoice or credit balance. The owner-approved P008 cap/reservation is **$266.44**, including both independent replacements and the$0.40 T8 cap amendment. Residual metering89.25301366 plus the entire P008 reservation is355.69301366 below the450 project ceiling; residual may include lag or unlabeled P008 costs. Full workspace meter plus full reservation491.00193173 double-counts labeled P008 work and is not the admission calculation. Failures, setup/build and storage remain included. [Saved billing snapshot](reports/p008_20261013/BILLING_UPDATE_2019.json).

Midpoint technical facts, deterministic charts and limitations are ready before the owner's TuesdayOctober13 21:00PDT deadline. Final slide composition, personal interpretation and rehearsal remain the researcher's work under the course policy. Long-term extensions are proposals only and do not change the closed experiment.
