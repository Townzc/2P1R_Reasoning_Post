# Token revision: Claude rounds 2–3 and Codex disposition

Read October12 14:43 PDT, before either original student endpoint was inspected. The owner has explicitly approved the uniform-tariff eight-student comparison and subsequently requested direct continuation. These audit suggestions do not add experiment authorization.

Pinned external reports: [round2 df68e21e](https://github.com/Townzc/2P1R_Reasoning_Post/blob/df68e21ec962de04a6eddb0c24cca67696dabbaa/audit/claude/20261012b/REPORT.md), [round3 7339a60a](https://github.com/Townzc/2P1R_Reasoning_Post/blob/7339a60a2c5726ed1be0a5f19fa22832813aa2d3/audit/claude/20261012c/REPORT.md). Claude independently reproduced the revised prefix selections and marked that scope PASS; student/summary code is PASS-WITH-NOTES. This is not approval of unobserved outcomes or all scientific interpretations.

| Finding | Disposition before new GPU dispatch | Remaining limit |
|---|---|---|
| T1: private preparation obstructs reproduction | Published candidate generator and public ordered length/hash packet; all eight admitted schedule digests and original candidate bytes reproduced | Length-only public replay does not independently tokenize unavailable raw text; full raw exports remain preserved |
| T2: unused caps exceed earlier5% threshold | Publish all four values6.14%,6.88%,12.26%,10.90%; explicitly common-cap, not exact-spend comparison | This revision fixes16-slot saved-trace actions. Earlier original time design's small-tail possibility is not implemented here; no post-hoc generated-length selection |
| T3: unequal exposure at fixed training budget | Retain approved fixed-target estimand and publish exact exposures below; summary code reports it for each seed | Cannot isolate repetition damage from coverage, quality, or solution variation; external concern remains documented |
| K1: duplicated target constant | New runtime and independent auditor use canonical TARGETS; value524287 unchanged | Old experiments keep their original source/dose |

| Cell | Unique usable answers | Mean complete-answer presentations (seed17 /23) | Per-answer range | Token-weighted exposure |
|---|---:|---:|---:|---:|
| p0 breadth |408|4.456 /4.473|4–5|4.463|
| p0 depth |474|3.970 /3.966|3–4|3.969|
| p4 breadth |91|20.747 /20.747|20–21|20.768|
| p4 depth |230|8.004 /8.004|8–9|8.003|

The question this queue answers is policy performance under a common acquisition cap and **fixed supervised training targets/updates, including the resulting repetition**. Equal supervised targets do not imply exactly equal GPU runtime or all processed-token FLOPs. If high-price depth wins, it would be evidence about this complete policy-and-training recipe, not proof that distinct reasoning paths caused the gain or that price alone caused a general reversal. Each cell has only one teacher trace. Report both within-price contrasts, both seeds and the interaction; retain negative results.

The earlier main experiment's10.79pp Solutions−Repeat difference motivates a repetition hypothesis, but does not establish that repetition causally caused that difference. A fixed-exposure experiment changes total training tokens and answers a complementary question. It is a proposed future mechanism check, **not part of the admitted eight**. No extra dose, teacher generation, or budget was added for these disclosures.

Reproduction: [v2 manifest](../../reports/p007_audit/token_tariff_v2/manifest.json), [local evidence](../../reports/p007_audit/token_tariff_v2/REPRODUCTION_VERIFIED.json), [interpretation binding](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_INTERPRETATION.json). New v2 additions await external review; Codex local checks are not Claude PASS. The first public schedule recreation exposed JSON integer/string-key canonicalization, fixed without changing any value; failed local output retained, zero model calls.

## Round 4 received October12 16:09 PDT

The preceding pending status is historical. Claude's [fixed round4 report730e7d06](https://github.com/Townzc/2P1R_Reasoning_Post/blob/730e7d06885bf853fb9fcb1afac2aef83d5fc7d1/audit/claude/20261012d/REPORT.md), reviewing7bfdeb3e and its named predecessors, gives **PASS** to v2 public plan reproduction/exposure/K1 and to the two original operational-pilot outcome packets. It accepts the T1/T2/T3/K1 disposition. This does not cover the eight corrected outcomes, which are still being evaluated, or independently audit all training updates.

| Finding | Codex response and verification | Scope |
|---|---|---|
| R1: public schedule replay indirectly needs pyarrow | Move the preparation-only writer import inside the historical planner CLI. The unchanged schedule functions now reproduce all8 admitted plan digests with Python `-S`, without site packages or a fake module | No runtime source bundle, input, schedule or scientific dose changes |
| L1: report512-token truncation per cell | The new local oracle derives stop counts from all scored outputs and rejects inconsistent summary counts or a capped output scored correct/unknown. The final results table explicitly includes each cell/seed count and denominator | The existing512-token limit and incorrect-score rule stay frozen; no excluded rows or extra generation |

An additional count-only check on already-verified local pilot records confirms38/1319 capped outputs for breadth and33/1319 for depth; all71 are scored incorrect under the original protocol. This is not a repeated model run or a rerun of the full pilot oracle. Eleven CPU checks pass, including inconsistent-count/denominator and altered-cap-score rejection. The [reporting follow-up packet](../../reports/p007_audit/token_reporting_v1/REVIEW_REQUEST.md) preserves evidence and requests review of these offline changes; Claude has not yet reviewed that follow-up. Both running workers' published source-file hashes and frozen input manifest remain unchanged.

## Round 5 received October12 16:27 PDT

Claude's [fixed report5c660321](https://github.com/Townzc/2P1R_Reasoning_Post/blob/5c6603219e5847cb3cd0adf01430ef073b00edaa/audit/claude/20261012e/REPORT.md) independently decoded and rescored3,088 saved teacher attempts (P007A1,024 plus four P007B cells2,064), with **PASS-WITH-NOTES**. All token counts agree. This extends the earlier compact-packet scope; it does not audit GPU sampling logs, provider timestamps or the50-second reconstructed settlement.

**E1 accepted as a disclosed parser limitation.** For `gsm8k/train/05907`, attempts2 and5 contain `\boxed{50\%}` and are unresolved by the frozen `marked_answer_v1` parser; Claude's independent parser accepts them. Codex checked the two saved scored files and all528 selected depth_p0 prefix records: the corrected prefix includes only attempt1 for this question. The frozen new training file also contains only attempt1. Thus the two disagreements concern the original time-priced procurement/pilot and do not change the eight corrected students. No frozen score, source text, prefix, training plan or dose was modified. Percent- or unit-bearing marked answers can be unresolved under this checker. This finding is recorded rather than used to post-hoc rescore the experiment.

The new corrected student outcomes still require their own version-specific external review.

## Round 6 received October12 17:04 PDT

Claude's [fixed report2d811a49](https://github.com/Townzc/2P1R_Reasoning_Post/blob/2d811a49db4c800bbd3b0e2d946ca55d693faa74/audit/claude/20261012f/REPORT.md) gives **PASS-WITH-NOTES** to token_p0_seed17_v1 and **PASS** to R1/L1. The original packet's pending label remains a historical snapshot; this record supplies the later scoped verdict. Codex independently reproduces the shared-question bootstrap: depth−breadth−0.9856pp,95% conditional interval[−3.1842,1.2130],10,000 resamples/seed20261013. It is not a seed/procurement interval. There is no established stable advantage.

**E2 accepted and independently reproduced.** In breadth_p0_s17, gsm8k/test/00465 ends with a standalone `The answer is:` line followed by a correct boxed30. The frozen parser extracts an empty answer statement alongside the box and conservatively marks the output unresolved. Decoding the saved token IDs reproduces that text, stop and claim structure. Keep primary963/950 and all original artifacts unchanged. Disclose the formatting false negative. An eventual supplementary sensitivity must apply the same rule to every completed model, separately from primary results; no partial correction or live parser change was made.

Each model has1,319 outputs,2,638 combined; the report has one count-wording slip and this record uses the artifact roster. Claude did not independently audit model weights or every training update in this round. High-price/seed23 outcomes remain unreviewed. [Follow-up evidence](../../reports/p007_audit/token_p0_review_followup_v1/README.md).

### Round 6 correction and acceptance, read October12 17:44 PDT

Claude's [comment6135161662](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6135161662) and [fixed amended report87f9a233](https://github.com/Townzc/2P1R_Reasoning_Post/blob/87f9a233e96b8f6695622807e969238efa6332ca/audit/claude/20261012f/REPORT.md) correct the depth count to1,319 and explicitly accept the E2 disposition in165716ca. The primary963/950, frozen scorer and review scope are unchanged. Any eventual sensitivity remains separate and uniform across all completed models. High-price and seed23 outcomes are not covered by this acceptance.

## Round 7 received October12 18:47 PDT

Claude's [fixed report67901abf](https://github.com/Townzc/2P1R_Reasoning_Post/blob/67901abf56bfa68467661abed903fd691e890aef/audit/claude/20261012g/REPORT.md) gives **PASS-WITH-NOTES** to all four seed17 outcomes at90ba8859, including the compact hashes, shared-question contrasts and saved raw-token scoring. This now covers the two-price packet; it does not cover seed23, model weights/per-update verification or the full report-builder input gates. Earlier pending labels remain historical snapshots.

| Finding | Independent disposition | Limit retained |
|---|---|---|
| S7-1: provisional apparent ordering change | All three primary contrasts and intervals reproduced exactly; report only point estimates with intervals crossing zero | No stable winner, established rank reversal or pure causal price effect |
| S7-2: breadth decline drives numerical interaction | Supplementary breadth p4−p0 −2.73pp [−5.08,−0.38] and depth +0.15pp [−2.12,2.27] independently reproduced | Posthoc, unadjusted conditional question intervals; do not isolate repetition from scarce data, coverage or trace differences |
| S7-3: depth_p4 has60 capped outputs | Preserve existing per-cell44/45/48/60 counts and full denominators | Capped outputs remain incorrect under the common frozen evaluation rule |
| E2: second empty-statement/correct-box case | Decode breadth_p4 gsm8k/test/00803 from original raw IDs; gold9 and correct boxed9 coexist with an empty answer statement; frozen score is unresolved | Keep primary927 and all other scores unchanged; no live parser correction or selective sensitivity |

The two price conditions also differ in answer exposure: high-price breadth20.75 versus depth8.00 presentations per usable answer. These are complete-policy results at fixed training targets, not isolated evidence of repetition damage. [Independent follow-up and reproducible contrasts](../../reports/p007_audit/token_seed17_review_followup_v1/README.md). New follow-up files await any later external review; Codex's checks do not extend Claude's verdict.

## Round 8 received October12 19:14 PDT

Claude's [fixed report007ed950](https://github.com/Townzc/2P1R_Reasoning_Post/blob/007ed950183d547b5a92b8ca250c65fb4bacc588/audit/claude/20261013a/REPORT.md), reviewing5852ffef, accepts the round7 disposition and marks its follow-up packet **PASS** (manifest and five numerical contrasts). It marks the seed23 price0 training-phase records **PASS only for the records/config binding**. It does not review seed23 endpoint outcomes or independently validate its complete weights/training trajectory. Earlier pending labels stay with their historical snapshots.

**S8-1 accepted; S8-2 reproduced.** Independent CPU comparison confirms the same408/474/91/230 training-path sets for seeds17 and23, in the same frozen per-cell answer files. The schedules change order and at most one presentation per path. Total presentations change1818→1825,1882→1880,1888→1888,1841→1841; all eight plans retain524287 targets and256 updates. The appropriate description is **2 training seeds, 1 teacher trace per cell**. These two realized training repeats give limited information about training variation, not a population seed-confidence claim, and none about repurchasing a new teacher corpus. Even direction agreement across both seeds would not establish procurement robustness. [Independent scope verification](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_TRAINING_SEED_SCOPE.json).

No input, schedule, primary rule, dose, budget or live source changed. No additional procurement draw or experimental group is authorized by this interpretation note.


## Round 9 received October12 20:14 PDT

Claude's [fixed report385744e3](https://github.com/Townzc/2P1R_Reasoning_Post/blob/385744e387d61fa300b13df3ac71e55645ea744e/audit/claude/20261013b/REPORT.md), reviewing5a9326ff, gives **PASS-WITH-NOTES** to token_p0_two_seeds_v1, **PASS** to the read-only export repair, and startup **PASS only for records**. Scope now includes raw-score rechecks and independent binary hashes for the two seed23price0 terminal states, including the recovered file. Per-step weight trajectories and final high-price outcomes remain outside this review. Older pending labels stay with their snapshots.

**S9-1 accepted and reproduced.** Across training seeds,183 breadth predictions and156 depth predictions flip correctness; within a seed, policies disagree on219/208 questions. These are descriptive counts, not an isolated variance-component estimate or a reliable population seed interval. Both observed price0 contrasts must be shown:−0.9856pp and0.0000pp, each conditional question interval crossing zero. The question bootstrap does not cover training-seed/procurement uncertainty; lack of detectable difference is not equivalence. Per-seed price interactions will be reported once the final two outcomes are verified. No extra seeds or hierarchical-bootstrap claim is added now.

**E2-b reproduced from raw IDs.** breadth_p0_s23 test00498 has gold/box40, depth_p0_s23 test01169 gold/box2, each with an empty answer statement and nativeEOS. The frozen rule returns unresolved/incorrect. Primary958/958 remains unchanged; no selected-model sensitivity is computed. A uniform all-eight supplementary analysis stays separate and waits for completion. C9-1 sparse-block padding is protected by full-file SHA before publication; no live or transport correction is necessary. [Saved-evidence follow-up](../../reports/p007_audit/token_seed23_p0_review_followup_v1/README.md), newly published and itself external-review pending.

## Round 10 received October12 20:44 PDT

Claude's [fixed report81be9a28](https://github.com/Townzc/2P1R_Reasoning_Post/blob/81be9a282fde509976e4b28312ff902bf2a53b5d/audit/claude/20261013c/REPORT.md), reviewing467602ef, accepts the round9 disposition and gives the unchanged `token_seed23_p0_review_followup_v1` packet **PASS**. Its four manifest entries were locally rechecked against the reviewed bytes; the old pending snapshot is retained. Claude confirms the numerical contrasts,183/156/219/208 flip counts and two E2 cases from its preceding independent calculation. It did not rerun the full tokenizer-dependent follow-up script in this round. No new finding or primary score change.

The final-pair training-phase review covers **records only**, not the still-pending high-price seed23 outcomes, complete final states or per-update model trajectory. All-eight closeout and conditional price-interaction reporting remain gated on the final independent local oracles and cloud audit. No new science, source, teacher output or live scoring change follows this review.

## Round 11 received October12 21:10 PDT

Claude's [fixed reporte8ef6ee0](https://github.com/Townzc/2P1R_Reasoning_Post/blob/e8ef6ee0687ddd330fbc478b7852ef4dbc024d2e/audit/claude/20261013d/REPORT.md), reviewing0c08a331, gives depth_p4_s23 **PASS as a pre-review of the local raw exports**:949/1319,60 caps,full state hash matched,zero per-question disagreements. Recovery handling is PASS. This does not cover the unexported last breadth result or the final eight-model packet. The repeated independent breadth_p4_s17 parser value928 includes knownE2; its frozen primary remains927. No primary score changes.

P11-1 accepted before rendering: the accuracy context figure now uses0–100%, and the contrast-with-interval figure is designated primary. SVG metadata/IDs are fixed and plotting records the rendering version; no figure has yet been produced. The revised chart output itself awaits rendering and external review. P11-2 remains pending the actual final summary: for each question, the frozen contrasts function averages the two observed seeds' policy differences, then resamples question indices jointly across all eight models10,000 times (seed20261013). The resulting interval conditions on those models and traces; it is not a training-seed confidence interval or a resampling of2638 independent seed-question observations. Verify final aggregate numbers when all eight local oracles and the cloud audit pass.


## 第十二轮：全部终点审阅与解释更正（2026-10-12 21:58 PDT读取）

固定报告[`514cec51`](https://github.com/Townzc/2P1R_Reasoning_Post/blob/514cec51b7903d0d53be33f861fcd11929b43722/audit/claude/20261013e/REPORT.md)给出八项结果PASS-WITH-NOTES、最后breadth终点PASS及恢复脚本r2 PASS。四个已知E2替代解析差异保留在主分之外；八份终点二进制SHA已由Claude分轮独立核对。

接受F12-1：第七轮S7-2仅是seed17的事后结果。seed23 breadth跨题价变化−0.68pp，高价breadth跨训练seed翻转200题；不以首seed单独下降作为发现，不因果解释为重复损伤。原第七轮记录保留，本段明确更正其解释地位。接受F12-2/3：事实页仍以14-label CPU审计通过为门，逐项披露截断。Claude关闭P11-2的是共享题目平均算法；最终输出文件、CPU回执、实际图表和事实页仍待其新审计。

[Codex逐项处理及独立目标核验](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ROUND12_REVIEWED.json)。没有修改模型、数据、剂量或冻结主评分。
