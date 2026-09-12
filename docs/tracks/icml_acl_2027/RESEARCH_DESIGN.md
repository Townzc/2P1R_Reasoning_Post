# Research design: acquisition friction and allocation

LT001, 2026-09-11. Review proposal; no new experiment, data release or compute allowance.

## Main question and claim boundary

For a fixed student, SFT recipe and training dose, **does measuring problem-dependent acquisition yield change a useful breadth/depth recommendation under a finite acquisition ceiling, and does that conclusion hold on new training pools at a previously untested allocation scale?**

The working mechanism is specific: obtaining the first usable response for a new problem and obtaining the next nonduplicate usable response need not have the same yield or cost. Difficult/ambiguous questions, repeated answers, verifier abstentions and finite retry limits can change both the number and composition of trainable problems. This can favor breadth, depth, a fixed mixture, or none of them. It is a hypothesis, not a result.

The [closest-work audit](CLOSEST_WORK.md) rules out a generic P/K novelty claim. Our strongest possible contribution is an empirical boundary with a validated decision implication. A null or negative result is useful if it tightly limits the practical role of acquisition friction; an underpowered ranking table does not establish invariance.

## Quantities that must remain separate

| Quantity | Operational definition |
| --- | --- |
| P_selected / P_acquired | Distinct parent IDs the policy attempts to onboard / successfully onboards; include onboarding failures in the former |
| P_trainable | Acquired parents with at least one accepted response; never replace P_acquired in a coverage denominator |
| M_i | All dispatched generation attempts on parent i, including errors, invalid answers and duplicates |
| K_target / K_i | Intended accepted-response cap / realized accepted, exactly deduplicated responses; K_i can be zero |
| N_unique | Sum of K_i; nominal P times K is only a target |
| T / U | EOS-inclusive supervised target-token exposures / optimizer updates |
| E_i,j | Number of training presentations of each retained response; repetitions are not newly acquired solutions |
| C_acq | Observed acquisition service costs or explicitly priced scenarios, with provenance for each term |
| C_research | Actual shared expenditure: calibration, all queried events, training, evaluation, idle/transfer/storage and failed work |

“Usable” means the frozen acceptance checks pass, not that the entire reasoning is proved. “Coverage” initially means parent retention and predeclared problem strata. Text/operation signatures are proxies; this project does not infer distinct cognitive strategies from multiple strings.

For policy p, define A(p; B,T,U) as common-evaluation greedy task-complete accuracy after acquisition capped by B and SFT at (T,U). The primary pairwise contrast is A(problem-first) minus A(solution-first); fixed-mix comparisons prevent presenting either extreme as the only alternative. All three pairwise effects are reported with simultaneous uncertainty. Base-to-trained retention is a separate diagnostic.

The acquisition policy's total effect includes its induced parent distribution and training repetition. Adjusting away realized P_trainable, response length or difficulty in the primary comparison would remove part of that effect. Conditional/matched analyses are secondary and cannot replace the intention-to-acquire result.

## Evidence needed for each conclusion

| Conclusion | Required observations | Observation that rejects or limits it |
| --- | --- | --- |
| The constant-cost approximation is misleading | Frozen mean-cost predictions miss realized useful-pair/parent counts on new pools, with systematic position/stratum dependence and correctly charged failures | Prediction errors are small within prespecified operational tolerances, or only attributable to a change of teacher, verifier, batching or price assumption |
| Acquisition friction changes the preferred allocation | A source-matched record-budget pilot establishes the reference recommendation; real-budget comparisons reverse the relevant contrast on independent pools, with a practical effect and no unreported strategy selection | The same recommendation persists; mixed is as good; a reversal appears only in one seed/pool or only after hypothetical repricing; uncertainty spans both useful directions |
| The measured recommendation transfers | The selected rule, budget conversion, directions and contrasts are committed before validation; it succeeds at an unfit allocation scale with the same information and constraints as the baselines | A rule is chosen after seeing validation, needs hidden solution capacities, or only fits its calibration points |
| No practically material change in this regime | Simultaneous intervals for the prespecified changes/effects lie inside the chosen equivalence band and cost predictions remain adequate | Merely failing a significance test; wide intervals; no source-matched record-budget baseline |

Use an initial practical accuracy band of **±3 percentage points**, declared for review rather than estimated from outcomes. A positive policy-advantage claim needs an effect at least 3 points with an interval excluding zero. Claiming the gain is reliably at least 3 points requires its lower confidence bound above 3. A robust sign requires the same direction in both validation pools and disclosure of all seed results. These rules may result in “inconclusive”; the [precision plan](VALIDATION_PLAN.md) shows why that is plausible.

An important failure branch: if common evaluation or capability retention remains unusable, stop the allocation interpretation. That is a feasibility failure, not evidence that acquisition friction is unimportant. Likewise, zero accepted calibration responses makes a cost-per-usable-response estimate undefined, not zero or infinite with a precise confidence interval.

## What is measurable now and what is only a scenario

| Evidence route | Can support | Cannot support |
| --- | --- | --- |
| Existing C017/C018 cache records | Released-slice availability, verifier attrition, exact retained counts, token/exposure feasibility, selection sensitivity | Original teacher failure probability, number of missing attempts, real generation cost, online acquisition latency |
| Hypothetical problem price and cached SFT outcomes | Conditional cost frontiers and break-even calculations for that source and dose | An observed change in market prices, human authoring cost or deployment policy effectiveness |
| Complete bounded sampling from one frozen teacher | Capped attempt yields, incremental duplicate rate, measured generation/verifier effort for that exact pipeline | A different teacher's costs, uncapped eventual success, semantic diversity, whole-instance invoices from token counts |
| Independent policy replay over complete recorded attempts | Counterfactual datasets and event-based cost estimates with no future-outcome access | Literal cash spent independently by each replayed policy or measured policy-specific online latency |
| Prospective online execution and invoice reconciliation | Actual pipeline behavior and attributed spending in the tested deployment | A universal acquisition price or general optimal allocation law |

The public GSM8K license/access price is not a measured problem-writing cost. The primary empirical route uses an already available problem bank and measures marginal onboarding/solution processing. A positive per-question human-authoring price is a sensitivity parameter unless separately measured. Zero/low marginal problem price must remain in every scenario report.

## Three high-value validations

1. **Attempt-yield measurement.** Collect the fixed first-through-eighth-attempt calibration, with each original parent retained in accounting. Examine new accepted responses per attempt and time, cumulative first-solution coverage, exact duplicates, abstentions and the cost of verification. Fit predictions only on calibration. All-eight sampling avoids inferring later-attempt yield solely from parents that failed earlier.
2. **Independent policy comparison.** Evaluate problem-first, solution-first and fixed-mix at the proposed 768-pair nominal scale, on two new pools and paired training seeds, under a shared acquisition ceiling and the same SFT contract. Score the prospective pilot recommendation as such; the best validation arm is only a retrospective menu oracle. Reuse matching sprint conditions instead of repeating them.
3. **Selection and validity challenge.** Recompute acquisition summaries with all selected parents versus the diagnostic K-complete subset; then audit a frozen blinded sample for verifier errors and reasoning quality. Keep original outcomes. If a proposed explanation depends on pruning incomplete parents or accepting invalid reasoning, register one targeted contrast before any extra training. A second model or task comes after this internal-validity check.

## Minimal progression from the four-point pilot

The proposed C017 points are (256,1), (256,4), (512,2), (1024,1). They contain one shared-parent repetition contrast and three approximate equal-pair allocations. They are not a full factorial, a fitted optimum or an authorized queue. Their actual retained counts differ from nominal P×K.

First consume the sprint's frozen usable recipe and any compatible four-point outcomes. Keep the same adaptation, scoring and dose within a comparison. If those points use the released 405B-generated cache, their effects stay cache-specific. **A new small teacher's measured price must not be attached to those outcomes.** A real-acquisition claim requires source-matched pilot training, either shared from the sprint or separately budgeted on the measured source. That is a new source condition, not a reproduction of an existing result.

The smallest planned confirmation is the three policies on two new pools at one held-out scale, with two paired optimizer seeds: **12 training endpoints**, plus shared base evaluation. No broad P×K×model×task×price grid is proposed. If compatible pilot outcomes do not exist, up to four exploratory source-matched endpoints are additionally needed before confirmation; this dependency must be priced explicitly, not hidden inside “reuse.” A single exploratory seed does not establish a stable record-budget winner.

Only after this block may a separate proposal add a second budget, one informative K between tested values, a second student, or MATH. Choose the extension by the unresolved scientific question before opening its outcomes. Do not search extra seeds or prices until one gives the preferred sign. If budget cannot support independent validation, narrow the paper to a feasibility/measurement study and say that allocation recommendations remain unvalidated.
