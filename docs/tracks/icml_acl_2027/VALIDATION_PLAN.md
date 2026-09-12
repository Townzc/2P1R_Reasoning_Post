# Independent validation and statistical plan

LT001, 2026-09-11. Prospective roles only. No reserved identities/content were opened or reassigned in this milestone. Coordinate every future release with the single shared exposure history before execution.

## 1. Separate learning the protocol from testing the recommendation

| Pool | Proposed role | Restriction |
| --- | --- | --- |
| Existing 1,024 C017 audit parents | Four-point pilot and new-source acquisition calibration | Already part of observed engineering/data work; never call it an independent pool |
| C017 development ranks 1–80 | Observed engineering sandbox, including E016/E017 | E017 creates no fresh development sample |
| Development ranks 81–144 | The already proposed P006 recipe confirmation | Separate release still pending; once observed it cannot validate allocation selection independently |
| Development ranks 145–224 (80) | Proposed allocation fitting/selection development | Release only after the recipe is frozen; too small for a final small-effect claim |
| Development ranks 225–512 (288) | Proposed common scientific confirmation | Keep inaccessible until policies, contrasts, dose and analysis are fixed; one common set for every arm |
| Existing C017 fresh draw (1,024) | Validation training pool A: first 768 original frozen ranks | Use the pre-solution order; retain the unused 256; do not choose by available K |
| Other eligible GSM8K reserve (4,910 at C017 freeze) | Validation training pool B: 768 by `lt001-validation-pool-b-v1|group_id` hash order | Must exclude all intervening shared exposure/training allocations before a published release; no choice by solutions |
| Official GSM8K test (1,319 original problems) | One final common evaluation after decisions are frozen | Historical source-provenance/overlap checks are recorded; no final-test predictions or policy fitting here |

The arithmetic 80+64+80+288=512 describes a proposal compatible with P006, not permission to open the remaining 432 questions. If the sprint consumes a proposed role first, record that history and define a new role before outcomes; do not silently rename exposed questions “fresh.” Pool B is not materialized now. Two disjoint training pools test sensitivity to data sampling; both are from the same selected GSM8K training population, not two independent benchmarks or a guarantee against pretraining contamination.

## 2. Frozen interface from the sprint

The current baseline has **no passed real-data scientific recipe**. E017 is a stopping calibration, not SFT validation. Before this design becomes executable, receive a published immutable release containing:

- original base and tokenizer digests, adaptation/precision/optimizer/scheduler versions, exact trainable parameter list and fresh-base initialization;
- exact prompt/response serialization, target masks/EOS, token-based loss normalization and sampler/order rules;
- fixed context/decoding/stop/extraction contract and independently checked raw-prediction scoring;
- actual completion, learning and capability-retention results, including failure cells and the status of recipe confirmation;
- a measured profile and reviewed common scientific (T,U) dose, distinct from an engineering dose;
- input/exposure manifests, artifact recovery status and the canonical resource receipt reference.

Use that release unchanged across PF/SF/FM. The nominal C017 524,288-token/256-update proposal is not automatically safe because a lower-dose P006 recipe later passes. Do not silently promote 77,192 tokens/64 updates to 524,288/256, or select full SFT for one condition and LoRA for another. Every trained arm starts from the same original base, never the calibration adapter.

Before outcome evaluation, audit whole-response schedule feasibility for every arm: all accepted pairs must fit and appear; common T and U, actual processed/padding tokens, per-update target-token counts and repetition distributions must be reported. If exact totals cannot be achieved without excluding parents, truncating targets or hidden length weighting, stop and propose one shared amendment. Do not search for a favorable seed or substitute a condition-specific dose. Retain the C017 subset-sum weighting residual when reusing its schedules.

Learning/retention gates are for establishing a common recipe. Once scientific endpoints are registered, a condition's poor learning, forgetting or truncation is an outcome; it cannot be dropped from the comparison because it loses. An infrastructure-incomplete run remains distinct from a complete bad result and gets no silent retry.

## 3. Smallest informative confirmation block

The [acquisition protocol](ACQUISITION_PROTOCOL.md) fixes PF=(768,1), SF=(192,4), FM=(384,2), all nominally 768 pairs, with incomplete targets allowed. None is one of the initial four pilot allocations. The primary resource ceiling B1=0.75 B0 is frozen from acquisition calibration **before validation outcomes**, along with attempt/response caps and all other ceilings.

Run all three policies on pools A and B, with optimizer/initialization seeds **17 and 23**, paired across policies. Acquisition events are shared within a pool by parent/attempt identity, while training permutations and initialization use the declared seed. This is 3×2×2=12 training endpoints, not 12 independent problem-pool replicates. Each acquired dataset supports two training seeds without reacquiring it. Shared base predictions may be reused if exact inputs and scoring match.

A completed identical dataset/schedule/base/seed/recipe endpoint from the sprint is an alias to existing evidence, not a new run. Same P/K alone is insufficient for equivalence. If no compatible source-matched pilot exists, price up to four exploratory pilot endpoints separately. Do not promise 12 endpoints fit an unmeasured phase budget.

The acquisition question does not require inventing a learned policy. The minimum compares three simple rules and tests a precommitted pilot recommendation. Define the nominal-pair pilot reference as the highest mean greedy accuracy on fitting development among PF/SF/FM, averaged over the available predeclared pilot seeds; exact ties prefer FM, then PF, then SF. Map that rule to its 0.75-scale target without fitting an accuracy curve. Commit its rule ID, reference comparison, uncertainty and selection data before confirmation. If the pilot ranking is uncertain, say so instead of treating its winner as an established law. The highest confirmation accuracy is a **retrospective three-rule oracle**, not a validated deployed recommendation. Any future learned selector needs new confirmation that was not used to build it.

The proposed main contrasts are PF−SF, FM−PF and FM−SF. Report all three, including a fixed mixture that ties or beats an extreme. The three rules do not span every allocation or every online schedule. A result at 768 nominal pairs is a local out-of-pilot-scale test, not a scaling law.

### What a ranking reversal would and would not identify

The 12-endpoint block can establish how fixed policies compare under the declared acquisition constraint, and whether a source-matched pilot recommendation transports. Comparing a new-pool cost-constrained outcome with an old-pool pilot **does not by itself causally isolate acquisition friction**; pool variation and dose/source changes must not be overlooked.

For the stronger statement that the ceiling/attrition *causes* a ranking change, predeclare an additional within-pool comparison before inspecting its outcomes: PF and SF with their nominal targets and the same finite per-parent caps but with the service-time ceiling removed, holding source, pool, seed and T/U fixed. Contrast `(PF−SF)_capped − (PF−SF)_nominal`. This adds at most 2×2×2=8 endpoints if none aliases a completed endpoint. It changes acquisition opportunity, not training dose. Register only if the calibrated process is plausibly binding and the full stage is affordable; otherwise use transport/resource-constrained wording and leave the causal claim unresolved.

This targeted eight-endpoint addition is not part of the automatic minimum. Repricing identical trained data alone cannot identify a learning effect of acquisition cost. A more expensive question-source scenario without observed onboarding costs remains hypothetical even when the accuracy measurements are real.

## 4. Common evaluation and failure reporting

Primary outcome: greedy task-complete numeric correctness under the sprint's frozen reviewed contract, over the same evaluation parents for every endpoint. Call it greedy accuracy; do not conflate it with sampled pass@1. Invalid/abstained/truncated outputs count as primary failures and retain their own diagnostic columns.

Also report native EOS versus boundary completion, parsed/correct marked answers, length, reference NLL, trainable-parent coverage and four paired base-retention cells. None replaces the primary outcome post hoc. If affordable and registered beforehand, add four identically configured stochastic generations per problem to report sampled pass@1 and pass@4; the generation budget, seeds and cap are shared, and samples within one problem are not independent experimental units. Large-k coverage claims need their own powered design.

Use the 288-parent confirmation for the first honest research conclusion. Later final-test evaluation must be jointly frozen across both tracks, scored once for all needed endpoints with raw records retained. A bug after final-test access requires a versioned correction and disclosure of exposure; rerunning a corrected scorer does not restore untouched status. Never choose a decoder, checkpoint, acquisition policy, stop threshold, price region or paper narrative by final-test performance.

## 5. Three distinct uncertainty sources

1. **Evaluation questions:** use paired per-question differences for each trained-model pair. Compute question-cluster bootstrap intervals with 10,000 resamples, seed 20270911; resample each question's full vector across models/seeds/pools together. With a finite benchmark, these are descriptive resampling intervals conditional on trained endpoints, not literal randomness in the published benchmark.
2. **Training stochasticity:** report both paired optimizer-seed effects within each pool. These capture initialization/order/numerical variability conditional on the acquired data. Extra sampled solutions or bootstrap draws do not add training seeds.
3. **Acquisition and problem sampling:** report the effect in each disjoint training pool and its parent-level acquisition uncertainty. Two pools are a minimal stability check, not a precise estimate of between-pool variance. Acquisition RNG and problem sampling are still combined here; a separate repeated acquisition tape would be needed to separate them.

Primary simultaneous intervals use conservative Bonferroni 98.333% marginal intervals for the three contrasts, giving a nominal 95% family level. A hierarchical model/bootstrap over just two training pools can be displayed as a sensitivity analysis but should not be presented as well-calibrated population inference. Report the mean paired effect, every pool/seed result and the conditional question intervals together. Do not treat 12 checkpoints, 10,000 bootstrap resamples or 4×question generations as thousands of independent experiments.

The service-time ratio and incremental acceptance curves use parent-cluster resampling of the complete calibration, including zero-yield parents. Record undefined zero-denominator resamples rather than substituting a value. Later-attempt estimates and verifier-error audits require the declared sampling weights/risk sets.

### Precision before spending

For a paired binary contrast with discordance probability q, the near-null standard error is approximately sqrt(q/n). An optimistic normal-approximation 80%-power detectable difference for a three-contrast family is `(z_(1-.05/6)+z_.8)*sqrt(q/n)`. This ignores training/pool variance; actual uncertainty can be larger.

| Common evaluation size | q=.10 | q=.20 | q=.30 |
| --- | ---: | ---: | ---: |
| 64 | 12.79 pp | 18.09 pp | 22.15 pp |
| 288 | 6.03 pp | 8.53 pp | 10.44 pp |
| 1,319 | 2.82 pp | 3.98 pp | 4.88 pp |

These are planning scenarios, not observed discordances or a retrospective power claim. At q=.20, resolving a 3-point effect at this approximate power requires 2,327 questions, beyond the official GSM8K test size. Therefore neither a 64-question gate nor a wide null result can certify a small allocation advantage or equivalence. Use intervals and meaningful effect bounds; do not compensate by repeatedly opening more test subsets.

## 6. Conditional extension, chosen before new outcomes

If the first block is informative, the next extension answers one unresolved question: a second acquisition ceiling for budget transport, the within-pool capped/nominal contrast for causal attribution, or one decisive MATH/OLMo replication for external scope. Do not run all of them by default. MATH needs its existing original-split/level/format limitations resolved; OLMo needs its own measured capability/profile gate. These cannot be silent substitutions for an unfavorable GSM8K result.
