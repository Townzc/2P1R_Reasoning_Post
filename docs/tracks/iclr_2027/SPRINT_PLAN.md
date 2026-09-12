# September 11–25: a conditional, quality-first sprint

September 11, 2026. Dates in the work plan are America/Los_Angeles. The internal
decision cutoffs are **September 17 at 17:00 PDT** and **September 22 at 17:00 PDT**.
They are research decisions, not scheduled automations or submission permission.

The official abstract and paper deadlines are September 18 and September 25,
respectively, at 23:59 AoE. These correspond to September 19 and September 26
at 04:59 PDT. Work to the earlier local-day targets below. Dates were checked
against the [ICLR 2027 call](https://iclr.cc/Conferences/2027/CallForPapers)
on September 11.

## One question and a finite scope

After evaluation completion and retained learning are demonstrated, do extra
cached solutions to the same GSM8K problems change held-out numerical correctness
relative to repeating one solution, and how does that compare with acquiring
more problems at the same supervised-token and update budgets?

The proposed minimum is Qwen2.5-1.5B base, GSM8K, SFT, and three conditions:
Repeat (256,1), Solutions (256,4), and Breadth (1024,1). These are nominal
acquisition counts; actual trainable counts and exposures differ. Mixed (512,2)
is deferred. The design in [the review packet](NEXT_PHASE_REVIEW.md) is conditional
and not a launchable grid. P006's short LoRA calibration cannot validate the
larger C017 dose by itself.

The prospective contribution must be a reproducible, informative boundary or
explanation of allocation behavior that changes what can be inferred from the
closest studies. The question alone is already studied. A familiar ranking in
one smaller model, a cost equation, or an improved evaluator is insufficient.
There is currently no evidence that this novelty condition will be met.

## Daily deliverables and dependencies

| Local date | Concrete deliverable | Dependency and exit |
| --- | --- | --- |
| Sep 11 | Publish this plan, evidence inventory, writing outline, E017 routing supplement, and priced review packet | Documentation only; preserve all source/data/results |
| Sep 12 | If the owner starts the existing A800, complete the one E017 calibration, compact export, shutdown confirmation, and local result report | Use existing authorization and unchanged 255-second/15-minute bounds. If unavailable, continue writing; do not probe repeatedly or compress later verification |
| Sep 13 | After E017 passes and method/resource review, finish the frozen E018 implementation/data-quality checks, publish its release, then attempt one bounded recipe if ready | No startup for unfinished preparation. Failure or incomplete execution ends the paid window and blocks scientific scaling |
| Sep 14 | Conditional P006 Stage C confirmation; finalize all-arm data, dose, learning-rate and analysis registration for review | Requires passing E018 and exact frozen recipe. A failed fresh confirmation ends this sprint's experimental path pending a new research decision |
| Sep 15 | Conditional seed17 three-arm phase; its Repeat arm is also the explicit larger-dose retention check | Same predeclared endpoint is reused, never retrained to create a favorable gate. If it fails, preserve it and stop expansion |
| Sep 16 | Conditional seed23 three-arm replication; freeze all six endpoints and complete the 368-parent development evaluation if the release and rental budget permit | No seed/arm replacement, checkpoint selection, or unplanned third seed. The development block is opened only after its separate approved release |
| Sep 17, by 17:00 | Abstract-quality decision with completed claim table, paired uncertainty, closest-work comparison, and a real draft abstract | Apply every abstract criterion below. If any core item is absent, do not submit a speculative placeholder |
| Sep 18 | If the gate passes, prepare the final genuine abstract and author-review package for the user | The user handles submission. Final-test design and every endpoint must be frozen before any approved test execution |
| Sep 19 | Conditional start of the finite official GSM8K test queue, with bounded per-endpoint execution and independent compact preservation | Separate test access/resource authorization; all scientific choices frozen. No interim score-driven changes |
| Sep 20 | Finish that same finite queue, confirm shutdown, and reconcile all endpoint records and costs | Timeouts/failures remain visible; do not silently substitute a smaller test or drop an endpoint |
| Sep 21 | Complete tables, paired intervals, failure analysis, and existing-record sensitivity analyses; finish the manuscript | No new model/task, cost-acquisition experiment, or causal story added from observed test errors |
| Sep 22, by 17:00 | Full-paper quality review against every criterion below | Unresolved validity, novelty, replication, or decisive missing result means continue research instead of lowering standards |
| Sep 23 | Resolve writing/citation issues and check every numerical claim against immutable records | Scientific corrections that require new data trigger reassessment; they are not presumed quick fixes |
| Sep 24 | Produce a readable anonymous paper, complete figures/appendix, and user-review package | All main claims supported in main text; preserve reproducibility and AI-use disclosure |
| Sep 25 | User's final decision on the complete paper | No autonomous submission. If not ready, retain the draft and evidence for continued research |

These dates assume prompt owner availability and passing gates; they do not
promise execution. If startup or release work slips, remove the deadline from
the experimental objective rather than skip confirmation or run overnight
without a funded, bounded queue. At each dependency failure, useful work remains:
publish the adverse evidence, refine the design, and maintain the course draft.

## September 17: genuine-abstract decision

All five criteria must pass. An engineering calibration alone does not qualify.

| Dimension | Required evidence by the decision | Continue research if absent |
| --- | --- | --- |
| Research increment | A concrete finding and explicit contrast with all five close works in [the evidence table](CLAIMS_AND_EVIDENCE.md); explain why it matters beyond another P/K comparison | Keep a research question in the draft, not an unsupported contribution claim |
| Reliable experiments | Completed E017 and E018/C gates; larger-dose check; all three scientific arms with audited data, common adaptation/decoding, exact declared dose, and all failures retained | Diagnose the failing stage offline and review one bounded next step |
| Repeated verification | Both paired seeds on the declared pool plus independent 368-parent development measurements; distinguish training-seed variability from question uncertainty | Two seeds share training data and do not prove population robustness; missing or inconsistent evidence blocks the abstract's scientific claim |
| Unresolved risks | No core reference-quality, stop-record, selection, source-identity, or accounting defect; limitations and residual length/exposure differences explicit | Do not use a new scorer, favorable subset, or different model to rescue the abstract |
| Feasible completion | Final endpoints, test release, finite evaluation/export/shutdown budget, and a nearly complete paper structure; actual author arrangements reviewed by the user | Do not make a promise of results or use a placeholder to preserve a submission slot |

The [author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)
require genuine informative abstracts reflecting the full submission and do not
permit adding authors after the abstract deadline. The plan's stricter empirical
gate is our quality choice, not a claim that ICLR prescribes these exact tests.
No abstract is submission-ready on September 11.

## September 22: complete-paper decision

| Dimension | Required evidence by the decision | Continue research if absent |
| --- | --- | --- |
| Research increment | The final statement remains substantively distinct after reading the closest methods and results; a null result excludes a predeclared meaningful range, rather than merely lacking significance | A clean reproduction or uninformative null remains useful project work but is not automatically an ICLR contribution |
| Reliable experiments | Complete frozen GSM8K test for base and all six endpoints, or a separately reviewed alternative established before test exposure; no missing decisive arm, unreported truncations, or altered denominator | Keep results incomplete and postpone the submission; do not relabel observed dev as test |
| Repeated verification | Both paired seeds, full question-paired intervals, and independently reproduced score/dose tables from saved raw outputs | More samples from one question do not create additional training replications; mixed seed directions must be explained or claims narrowed |
| Unresolved risks | Bounded claim survives native-EOS/task-completion reporting, matched-dose residuals, reference-quality caveats, and source/adaptation checks; all essential artifacts independently preserved | Stop paper claims requiring unrecovered unique artifacts or unresolved integrity defects |
| Complete manuscript | Readable full draft with concrete methods, all main results, limitations, closest-work comparison, reproducibility evidence, and AI-use statement | No result placeholders, unsupported causal claims, or last-minute expanded scope |

Even a statistical result does not settle novelty. Even a novel idea does not
excuse invalid evaluation. If the submitted abstract later becomes unsupported,
the user should consider withdrawal; do not replace it with a substantially
different unsupported paper at the deadline.

## Continued research and course continuity

If either quality gate fails, retain the complete research record and continue
the same project toward ICML or ACL 2027. Do not restart allowances or treat
shared results as independent replication. Real acquisition-attempt costs,
independent training-pool validation, MATH levels 1–3 and OLMo2-1B are longer-term
conditional work, not simultaneous prerequisites to force into this fortnight.

The shared course deliverables remain midpoint presentation October 15 or 20,
midpoint report October 20, final presentations November 12–24, and final report
December 14; November 8 is the internal core-experiment target. See the
[course project page](https://www.sewonmin.com/courses/cs294_288/project/).
January 10, 2027 is only a proposed internal manuscript target; official ICML/ACL
submission dates are not established by this plan. An accepted ICLR paper would
require a distinct later contribution consistent with venue rules; overlapping
manuscripts are not to be submitted concurrently.
