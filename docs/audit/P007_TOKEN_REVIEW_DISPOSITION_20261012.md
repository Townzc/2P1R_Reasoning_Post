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
