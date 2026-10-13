P008 最新：base 已完成独立核验 **638/1319**（41条长度上限计错），GPU退出；LR 修订真实审计通过，8项尚未尝试 T1 已各派发一次，首项16更新已核验。两项原失败保持 failed，替代方案待直接预算确认；T8 仍待实际计时N2。材料21PDT冻结、有限学生按授权继续。

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

**P008:** both full teacher draws and exact18 student plans passed external G1. Inputs were uploaded once and all37 files including the manifest passed independent readback after preserving one temporary read failure. The original base is actually evaluating. Two D1 B1/p0 students stopped before any update because host `cos` recomputation differs from the frozen LR vector by up to1.36e−20; [both failed calls are fully preserved](reports/p008_20261013/student_lr_failures_closed_v1/DISPOSITION.md), with zero updates/endpoint outputs/unknown work. The [separate exact frozen-LR amendment](reports/p008_20261013/student_frozen_lr_amendment_v1/REVIEW_REQUEST.md) passes7 new CPU checks and awaits scoped review before any of the remaining16 unattempted students start. Existing base/failed slots are excluded; no automatic retry or N2 waiver. Maximum8 within evidenced totalGPU10, per-worker limits and$249.68 reservation/$250 cap are unchanged. Direct owner authority lets the finite student queue run to completion;21PDT materials freeze remains and unfinished outcomes staypending. Latest20:28UTC workspace delayedmeter$117.88183740 is not an invoice/balance. P007B facts, figures and limitations remain ready.

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

Workspace delayed meter was **$116.26183740 at the October13 19:12–19:13UTC read**, billed$0; final worker costs can lag. This is not a final invoice or credit balance. P008 hard reservations are **$249.68 within$250**, including the authorized$12 continuation. Project spending ceiling$450/protected≥$50 remain unchanged.

Midpoint technical facts, deterministic charts and limitations are ready before the owner's TuesdayOctober13 21:00PDT deadline. Final slide composition, personal interpretation and rehearsal remain the researcher's work under the course policy. Long-term extensions are proposals only and do not change the closed experiment.
