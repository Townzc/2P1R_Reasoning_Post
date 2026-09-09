# ICLR positioning and evidence gate — 2026-09-09 UTC

**The broad idea is already closely covered.** Our next useful contribution would
need to be a demonstrable control, boundary condition or explanatory result beyond
prior work. Another positive seed on the current restricted arithmetic slice would
establish neither novelty nor ICLR readiness. This is a bounded primary-source
audit, not an exhaustive novelty search or a reproduction of the cited papers.

## Verified conference schedule

The official [ICLR 2027 call](https://iclr.cc/Conferences/2027/CallForPapers)
lists these deadlines, checked on 2026-09-09:

| Item | Official deadline | UTC equivalent | Los Angeles equivalent |
|---|---|---|---|
| Genuine abstract | September 18, 2026, 23:59 AoE | September 19, 11:59 UTC | September 19, 04:59 PDT |
| Full paper | September 25, 2026, 23:59 AoE | September 26, 11:59 UTC | September 26, 04:59 PDT |

The [author guide](https://iclr.cc/Conferences/2027/AuthorGuidelines) requires
an anonymous submission, at most nine main-text pages initially, and a genuine
abstract. Authors cannot be added after the abstract deadline. OpenReview profiles
should be prepared now; noninstitutional profile moderation can take two weeks.
Check reciprocal-review eligibility and quotas with the actual author team:
teams without an eligible reciprocal reviewer are exempt from reviewing, but each
such author is limited to one qualifying submission. The identified public GitHub
repository should be accompanied by a separately anonymized submission artifact.

The [AI policy](https://iclr.cc/Conferences/2027/AIPolicyForAuthors) requires
disclosure in both the paper and submission form. Our experimental design,
implementation, synthetic-data work and interpretation involve AI assistance and
must be described accurately; the human authors remain responsible. The existing
AI_USE_LOG is useful provenance, not a substitute for author review.

There are roughly ten days to the abstract deadline and seventeen to the full
paper deadline from this audit. Current evidence does not justify promising this
cycle. Aim for the scientific standard first; decide submission readiness from
completed evidence before the genuine-abstract deadline. No submission is made or
authorized by this document.

## Five closest comparisons

“Not verified” below means that this audit did not establish the control; it does
not allege that the authors omitted it. Paper outcomes are not directly comparable
to our short arithmetic pilot.

| Original source and inspected scope | What it already addresses | What remains to distinguish here |
|---|---|---|
| [Why Do Reasoning Models Lose Coverage? The Role of Data and Forks in the Road, v2](https://arxiv.org/html/2605.17026v2), September 1, 2026; §§4.1–4.2.1, 5, Appendices A/B | Directly contrasts per-problem versus dataset-level NL/code diversity with a 50/50 global mode balance; evaluates GSM8K test pass@k. Also studies synthetic graph forks, decision-rationale controls and multiple base-model families. | This directly overlaps our central question. Exact arithmetic structure/exposure controls and an informative selection boundary could extend it; the generic claim that within-problem diversity matters beyond global diversity is already present. |
| [CoScale-RL, v1](https://arxiv.org/html/2601.14695v1), §5.2 and Appendix D.2.2 | Its SFT ablation compares 90 problems × 20 solutions against 1,800 problems × one solution, with aligned example counts, batch size and epochs. It measures sampled success on seen training problems as RL potential. | Shared unseen problems, explicit structural labels and global-coverage controls address a different estimand. A generic problems-versus-solutions allocation claim is already covered. Exact supervised-token equality was not verified. RL is outside our experiment. |
| [Data Repetition Beats Data Scaling in Long-CoT SFT, v1](https://arxiv.org/html/2602.11149v1), §§2–4 and Appendix A | Repetition versus increasing unique examples at fixed optimizer-update counts; long-CoT math/science evaluation across model families. | Repetition is an essential baseline, not a novel idea. Exact response-token equality and a per-problem/global-structure contrast were not verified. Short synthetic traces provide a boundary study, not a direct reproduction. |
| [Learning Diverse Responses with Prefix-Conditioned SFT](https://aclanthology.org/2026.acl-long.9.pdf), ACL 2026, §§3–4.3 | Uses 16 responses per question and identical optimizer settings to compare ordinary SFT against prefix-conditioned SFT; separates standard and prefix-conditioned inference and measures pass@k. | Changes conditioning/training rather than just allocating fixed structural supervision. It already warns that several references do not automatically create useful output diversity. Our final-expression structure count is a different operational measure and needs semantic validation. |
| [Training LLMs to Reason in Parallel with Global Forking Tokens](https://arxiv.org/html/2510.05132), §§2–3 and Appendix A; [author repository](https://github.com/Sheng-J/SSFT) | Set SFT matches forking tokens to multiple traces through bipartite assignment; compares ordinary multi-trace SFT on the same traces and studies pass@k, voting and cross-domain transfer. | Primarily an objective/conditioning intervention. Our unchanged SFT objective can isolate data allocation, but diverse reasoning, parallel coverage and cross-domain evaluation are established research directions. Canonical structure matching was not verified here. |

## Closest-paper implementation check

The Forks repository was inspected at main commit
`64bf9e3e86231bc6b52f2974ca285ad8aa8fc181`. Its
[launcher](https://github.com/psunlpgroup/reasoning_forks/blob/64bf9e3e86231bc6b52f2974ca285ad8aa8fc181/run_sft.sh)
declares **12,800 examples in each diversity condition**, batch 32 and LR 1e-5;
the [README](https://github.com/psunlpgroup/reasoning_forks/blob/64bf9e3e86231bc6b52f2974ca285ad8aa8fc181/README.md)
gives eight-epoch commands for both. Thus the released recipe intends matched
example/update budgets. We must not claim that update matching distinguishes us.
These are configuration facts, not independently reconciled historical receipts.

Its [trainer](https://github.com/psunlpgroup/reasoning_forks/blob/64bf9e3e86231bc6b52f2974ca285ad8aa8fc181/src/training/sft.py)
uses full fine-tuning, BF16 with FP32 mixed precision, fused AdamW,
response-only supervision and no packing. Full-parameter SFT is therefore also
shared. This inspection did not verify per-example EOS-inclusive token equality,
per-update structural histograms, or shared question identities from the actual
data files. Our code supplies stricter accounting for its own selected slice;
that alone is not a sufficient paper contribution.

The paper's reported distinction concerns increasing pass@1 while large-k
coverage declines under dataset-level diversity, versus more stable coverage
under problem-level diversity. It also probes branch confidence and prompt
perturbations. Our single endpoint cannot establish training-time coverage
collapse, latent routing, or a new explanation for that phenomenon.
[Paper, §§4–5](https://arxiv.org/html/2605.17026v2).

## Pilot evidence and the strongest defensible next question

The [completed pilot](PILOT_V1_RESULTS.md) has Paths/GCM matched greedy 23/64
versus 18/64, sampled pass@1 28.12% versus 27.34%, and pass@4 51.56% versus
34.38%. The observed difference is larger in the spread of successes across
problems than in mean per-draw success. Four draws, one training seed and sixteen
matched selection blocks give very limited resolution. Broader-dev greedy remains
4/64 versus 1/64. These are descriptive results, not a mechanism or transfer claim.

A useful provisional question is: **When global computational structure exposure
and supervision budgets are held fixed, does reallocating paths within problems
reliably redistribute successful outputs, and on which arithmetic subdomains?**
This narrows the estimand. It is not a novelty claim and should not be presented
as a discovered law or an optimal P/T/R allocation rule.

Canonical operator trees can overstate meaningful diversity: multiplication or
division by one, cancellation and algebraically equivalent rebracketings can
create different syntax without different computational content. Before assigning
a “strategy” interpretation, quantify these cases in both training paths and
successful generations. Compare target/operator/neutral-operation distributions
between eligibility-selected and broader slices. A new graph task by itself would
not settle this issue or differentiate us from the closest paper.

## Evidence sequence before scaling

1. **CPU falsification first.** Independently audit intermediate equations, input
   reuse, final-expression agreement and semantic simplifications; retain every
   parse failure. Recompute current paired outcomes by prespecified descriptive
   strata, including input one and neutral operations. Label these analyses
   post hoc, preserve original metrics and leave the reserved holdout untouched.
2. **Small fixed replication only after that audit.** The proposed paired seed 23
   should retain the original greedy primary endpoint, shared selected problems,
   recipe and dose. Jointly regenerate assignment/order and verify exact matching.
   Do not replace the primary endpoint with pass@4 because it looks better. A
   reversal or concentration in a shortcut stratum is a useful stop signal.
3. **Resolve the scientific boundary.** If the descriptive signal survives, freeze
   a broader development evaluation and a nontrivial-operation construction that
   can test an explicit interaction between path allocation and solution structure.
   Hold one factor fixed at a time. Determine sample sizes from desired uncertainty,
   account for shared selection blocks, and distinguish training-seed variation
   from problem-sampling variation. More decoding samples alone cannot resolve
   either dataset selection or seed uncertainty.
4. **Establish a substantive extension.** Require independent training pools and
   several prespecified seeds, a defined generalization split, and a targeted second
   task or model-family boundary. A mechanism claim needs an intervention that
   separates semantic path alternatives from syntax/length/neutral operations,
   with a prediction that could fail. Endpoint pass@k alone does not identify it.
5. **Final evaluation and paper gate.** Freeze estimands, metrics, decoding and
   stopping rules before any final holdout. Publish unfavorable conditions, complete
   provenance and uncertainty. Decide whether the contribution is a useful
   controlled replication, an explanatory boundary study or a sufficiently
   supported new result; venue ambition must not determine the conclusion.

Only CPU work is implied now. Additional GPU phases, broader evaluation and
protocol changes require the concrete proposal to be reviewed under the existing
project rules. The remaining 3,488 process-seconds are a replication budget, not
evidence that a complete ICLR study fits it.
