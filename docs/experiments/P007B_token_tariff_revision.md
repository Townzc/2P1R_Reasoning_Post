# P007B corrected comparison: one fixed token tariff

Owner explicitly approved this revision on October12, after Claude C-B1 was reproduced and before either original student endpoint result was inspected. This is a finite correction to the cost estimand, not a new teacher search. [Retirement binding](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_RETIREMENT.json) and [new admission](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json) supersede the six untouched original student slots and their final audit. The original two students finish and remain separate operational pilots. Their work and all previous costs/failures remain recorded.

## Scientific question and estimand

Under a stated, identical acquisition tariff and a common spending ceiling, does the relative performance of breadth-first versus depth-first procurement differ between free and costly problems? The primary comparisons are depth−breadth at each price and their difference (price interaction), reported separately for both student seeds and averaged. A reversal requires supporting within-price contrasts; an interaction alone is not a winner. No significant difference is not equivalence.

The original wall-clock wallets mix generation, scoring, receipt persistence, length and hardware throughput. These are honest operational expenses, but separate workers have substantially different time per output token. A clean interpretation as a problem-price effect is therefore unavailable. The corrected comparison uses the saved, fully audited teacher traces with a common hypothetical tariff. It does not turn old wall-clock costs into measured API prices.

## Frozen prefix simulation

- Teacher and outputs are unchanged: Qwen2.5-Math-1.5B-Instruct, fixed revision, same prompt, sampling, scorer and within-parent duplicate rule. **Zero new teacher calls.**
- One tariff unit per prompt token and per generated completion token, including EOS. All failed and duplicate attempts are charged. The pilot mean is373.341796875 units/attempt; problem prices are0 and1493.3671875 units (4×pilot mean).
- Common cap211257 units, selected from available trace lengths before student endpoint outcomes. This is a hypothetical tariff, not dollars.
- Same ordered problem pool,16 slots, at most8 attempts/problem. Breadth retires at1 usable answer, depth at4.
- Reserve the price of new problems, known prompt lengths, and **16×1024 maximum completion tokens** before reading a batch's outputs. The actual source/config maximum is1024; an earlier private handoff's768 was a transcription error. The CPU candidate always used the actual1024, so its selected data did not change.
- Stop if the next complete16-slot action cannot be reserved. Charge actual token counts only after admission. No outcome-dependent partial-batch selection, suffix search, or extra generation.
- All original collection costs, unselected trace suffixes, failed/blocked workers, setup and closing time remain in platform costs separately.

| Scenario / policy | Problems purchased | Problems with usable answers | Usable answers | Charged attempts | Tariff spend | Unused cap |
|---|---:|---:|---:|---:|---:|---:|
| p0 breadth |420|408|408|512|198280|6.14%|
| p0 depth |135|128|474|528|196716|6.88%|
| p4 breadth |95|91|91|112|185348.8828|12.26%|
| p4 depth |61|58|230|256|188226.3984|10.90%|

Positive-price breadth uses only the first7 original batches, before the failed batch11; none of its resumed output or reconstructed wall-clock charge enters this tariff prefix. This removes that particular reconstruction from the tariff, not the need for independent procurement replication. Different cells still have different sampled teacher trajectories, one trace per cell; the price interaction remains conditional on these finite pools.

## Students and outcome safeguards

Four cells×seeds17/23, same Qwen2.5-1.5B base, LoRA, frozen LR vector,256 updates, complete answers/EOS, prompt/padding masked, total-target loss normalization, no packing or truncation. All usable prefix answers receive balanced q/q+1 exposure.

The initial524288-target whole-answer schedule was infeasible for depth_p4. Before endpoint scores, choose the largest jointly feasible integer at or below the original budget within1%; all eight plans use **524287 targets**. This uniform one-token change is based on lengths only. The unsuccessful CPU preparation is preserved. A second CPU integration check found missing redundant length metadata; recomputed metadata fixed it without changing texts, selected candidates or plans. No GPU was launched by either failed CPU check.

All students run on H100, with one fixed1319-question GSM8K official-test greedy evaluation at step256 (512 new tokens,2048 context,batch16). No intermediate development evaluation or checkpoint selection. The test had been researcher-observed in September; no claim of pristine or contamination-free testing. Final-answer correctness and distinct text do not verify reasoning quality or structural solution diversity.

Independent local audits verify every update, exact targets, full state hashes, raw tokens, scores and all1319 outcomes. Paired-question bootstrap uses10000 shared resamples,seed20261013, conditional on the eight fixed models. It does not estimate across-seed or procurement-draw uncertainty. A final CPU audit verifies four source procurement packets, eight new students and both retained original pilots.

## Execution and budget

New campaign`mp-policy-token-20261012-r1`; at most2GPU total; no controller or automatic retry. Original pair finishes, independently verifies and releases before new dispatch. Four pairs: p0 seed17, p4 seed17, p0 seed23, p4 seed23. Each slot submitted once, preserved intents/claims/checkpoints; ambiguity is reconciled rather than replayed.

Original unattempted six student reservations$108 plus old audit$3 are retired; new eight$144 plus final audit$3 yield net+$36. Cumulative conservative reservation$366.50 is **not an invoice**. $500 total, maximum$450 spending and at least$50 protected. Original hard deadline **2026-10-14 02:00UTC / Tuesday October13 19:00PDT** is unchanged. H100 each≤10800s, CPU audit≤3300s, or earlier shared deadline. No permanent deployment; completed workers exit; evidence Volume is retained.

Claude rounds2–3 independently reproduced prefix selection (PASS) and reviewed student/summary code (PASS-WITH-NOTES). The findings and limits are recorded in [the disposition](../audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md). Outcome verification and new v2 additions remain externally pending. Local checks are not Claude approval.

## Pre-dispatch interpretation amendment (October12)

All four unused-cap fractions exceed the original5% threshold for an exact-spend claim. Full16 saved-trace action reservation is an explicit constraint of this revision; unlike the earlier time-policy proposal, there is no smaller last batch. Report common caps and actual token-tariff spending together.

Fixing524287 targets produces unequal complete-answer exposure: p0 breadth approximately4.46, p0 depth3.97, p4 breadth20.75, p4 depth8.00. These are part of the fixed-training-budget policy outcome, not controlled away. The summary reports exact per-seed exposure distributions. No isolated diversity/repetition causal claim is supported. See the immutable [interpretation binding](../../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_INTERPRETATION.json). The already-admitted data, seeds, updates, targets and budget remain unchanged.
