# Working manuscript: solutions, repetition, and retained learning

September 11, 2026. Research draft and outline only. The central comparison has
not run and the novelty claim is unresolved. Do not submit this document or turn
its missing results into promises in an abstract.

Working title: **Additional Solutions or Repeated Supervision? A Controlled
Study of Small-Model Mathematical SFT**. This deliberately names the question
without predicting a positive result. A final title should describe the actual
finding after the quality reviews.

## Abstract preparation

There is no submission-ready abstract today. The September17 version must state
the actual research increment, the completed model/data/control setting,
numerical results with uncertainty, and the resulting bounded conclusion.
Do not claim success from the existing overfit gate, substitute C020's post-hoc
counts for a prospective experiment, or imply that planned comparisons have run.

## Introduction: draft prose grounded in current evidence

Supervised fine-tuning can allocate demonstrations across new problems,
alternative solutions to existing problems, and repeated exposure to the same
solution. These choices change the distribution of supervision even when the
training budget is fixed. Their relative value is an empirical question:
existing work compares question breadth with answer multiplicity, while other
work finds strong benefits from repeating smaller datasets under fixed update
budgets. A useful comparison must make its supervision and optimization units
explicit and establish that the training procedure is usable in the regime
being studied. See [Shortest Path](https://arxiv.org/html/2604.15306v1) and
[Data Repetition Beats Data Scaling](https://arxiv.org/html/2602.11149v1).

Our preliminary engineering record illustrates why these prerequisites matter.
A Qwen2.5-1.5B base configuration fine-tuned on32 GSM8K training problems
produced correct terminated answers on all32 training prompts. On a separate
64-problem development calibration, however, that endpoint produced zero
clean-correct answers, compared with26 for the original base. The base itself
failed a predeclared truncation screen. These observations separate successful
memorization from retained development performance and identify evaluation
completion as an unresolved prerequisite. They do not establish why the loss
occurred or how any allocation of additional solutions would change it.
[E015](../../../reports/REAL_MATH_E015_RESULTS.md),
[E016](../../../reports/REAL_MATH_E016_RESULTS.md).

The study proposed here asks a narrower question: once completion and retained
learning are established, what is the held-out effect of additional cached
natural-language solutions relative to exact repetition at the same problem
count, supervision, and optimizer-update budget? A problem-breadth condition
provides the allocation reference. We distinguish numerical correctness,
termination, and the survival of problems solved by the original base. The
current draft specifies how to test this question; the decisive experiments
and any resulting contribution statement remain incomplete.

**Editorial requirement:** replace the final paragraph with completed-study
language only after evidence exists. Keep a dedicated sentence stating what
the final result adds beyond the five closest works. If that sentence cannot
be supported, this remains a project report rather than an ICLR submission.

## Related work: draft prose

**Question and solution allocation.** The Shortest Path study directly compares
more questions with more answers and extends its investigation to MathQA. This
is a direct predecessor to the allocation question, including a real-math
setting. OpenMathInstruct-2 also varies the number of distinct questions while
holding the number of question–solution pairs fixed. Our proposed controls
therefore address a local experimental regime rather than introducing the
breadth-versus-depth question. A substantive boundary result, if established,
must be distinguished from a simple replication on another model.
[Shortest Path, Sec. 4/Appendix E](https://arxiv.org/html/2604.15306v1),
[OpenMathInstruct-2, Sec. 2.2.4](https://proceedings.iclr.cc/paper_files/paper/2025/file/302ce0673c00aee2cf84bb43d0117553-Paper-Conference.pdf).

**Diversity and coverage.** Why Do Reasoning Models Lose Coverage? compares
alternative reasoning modes placed within each problem or distributed across
problems, and studies their sampled coverage behavior. Our proposed measurement
of which greedy base successes survive SFT is distinct from pass@k coverage;
neither metric establishes the other. Multiple accepted natural-language
solutions also do not certify multiple semantic strategies. The design needs
an explicit empirical increment beyond those existing diversity comparisons.
[Coverage study, Sec. 4.2.1/5](https://arxiv.org/html/2605.17026v2).

**Repetition and acquisition budgets.** Data Repetition Beats Data Scaling
studies fixed-update repetition and connects its findings to memorization,
termination and forgetting in long-CoT SFT. This motivates keeping repetition
as a full-dose baseline, without treating our small engineering failure as a
refutation. Spend Wisely analyzes allocation of generation and training across
iterative bootstrapping. Our use of a public solution cache does not measure
its original attempts or generation costs; the sprint cannot support an
acquisition-optimality claim. [Repetition study](https://arxiv.org/html/2602.11149v1),
[Spend Wisely](https://arxiv.org/html/2501.18962v2).

## Proposed main-text structure

The current [ICLR 2027 author guide](https://iclr.cc/Conferences/2027/AuthorGuidelines)
allows nine main-text pages at submission. The following is an allocation for
a complete paper, not a plan to fill pages before decisive results exist.

| Section | Approximate pages | Content and evidence obligation |
| --- | ---: | --- |
|1. Introduction |1.00 |Question, actual finding, and a specific increment over direct prior work |
|2. Related work |0.75 |Direct comparison with all five close studies; no first-P/K or first-cost claim |
|3. Data and evaluation contract |1.50 |Parent splits before augmentation, source/acceptance provenance, missing P/K, response quality, exposure history and stopping semantics |
|4. Training design and estimands |1.25 |Three arms, exact supervised tokens/updates, common adaptation, repetitions, residuals, independent endpoints and paired analysis |
|5. Results |2.50 |All seeds/arms, prospective independent development and frozen test, uncertainty, retained and newly solved questions, completion failures |
|6. Interpretation and failure analysis |1.00 |What the evidence distinguishes; adversarial explanations and effects of selection/formatting; no inferred semantic mechanism |
|7. Limitations |0.75 |Single model/task, short cached responses, limited seeds, pretraining exposure, selection and adaptation limits |
|8. Conclusion |0.25 |Only the supported local empirical statement and research implications |

References and supplementary material should carry detailed source, recipe,
raw-record, and accounting evidence. The main text must still make the result
assessable without requiring reviewers to reconstruct an appendix.

## Methods outline: explicit draft status

**Data.** State acquired problem count `P`, target solutions `K`, available
per-problem counts `K_i`, unique pairs `sum K_i`, presentations, supervised
tokens including EOS, processed tokens, padding, updates, and actual runtime.
Use the existing C017 draw, not a solution-success-selected replacement. The
three candidate arms have253,996 and1,013 unique pairs respectively. State
that numerical-answer acceptance and text deduplication are proxies, not
step-validity or semantic-strategy labels.

**Model and adaptation.** Pin Qwen2.5-1.5B base and tokenizer revisions. E018's
proposed LoRA recipe is a preliminary feasibility stage, not the scientific
comparison or a causal LoRA-versus-full-SFT ablation. The larger-dose comparison
has its own reviewed recipe and common fresh-base initialization in every arm.
Report actual parameter inventory, precision, library versions, positive-LR
steps, summed LR and the completed dose. Use the exact proposed transition in
[the review packet](NEXT_PHASE_REVIEW.md); no new training method has run yet.

**Completion and scoring.** Preserve both original E016 metrics and the later
prospectively specified task-completion contract. Native EOS and recognized
question-boundary stops are different events; retain trigger tokens and later
padding. Gold answers cannot control stopping. Score every declared question,
including caps and malformed outputs, and retain the full raw token records.
Numerical correctness is not verified reasoning. E017 is still pending.

**Estimands.** Primary: paired held-out numerical-correctness difference of
Solutions versus Repeat at fixed P and declared dose. Secondary: Breadth
comparisons, base-success survival, gross gains/losses, completion and length.
These secondary views are not new mechanism claims. Greedy evaluation does
not measure pass@k. Use question-paired uncertainty and show each training seed;
do not pool repeated predictions as independent questions.

**Selection and independence.** The80 observed development parents are an
engineering sandbox. P006's proposed64-parent recipe confirmation and the
later368-parent scientific block have separate roles. Freeze scientific
endpoints and analysis before releasing the latter; freeze all choices before
the separately authorized official test. Two seeds share a training draw.
Report calibration history and never relabel an observed population as fresh.

## Results: only completed evidence may be stated today

| Completed measurement | Actual result | Role in this draft |
| --- | --- | --- |
| E015 training memorization |32/32 correct/terminated, no truncation, NLL0.001106 | Preliminary configuration endpoint, not generalization |
| E016 development clean correctness |Base26/64, E0150/64;26 losses, no gains | Retained-capability concern; both registered screens failed |
| E016 base completion |14/64 true truncations, exceeding the frozen8 limit | Evaluation prerequisite, not a passed base gate |
| C020 saved-prefix audit |Base39/64, E0150/64 under a candidate stop contract | Post-hoc diagnostic; no revised E016 result or new runtime measurement |

Evidence and limitations for each row are in [the claim inventory](CLAIMS_AND_EVIDENCE.md).

| Required new result | Status on September11 | Required presentation when complete |
| --- | --- | --- |
| E017 actual stop calibration |Not run |Full64 denominator, stop/parse/cap counts, audit and latency |
| E018 retained learning and Stage C |Not run; training release absent |Learning plus paired retention, full failure record, uncertainty |
| Scientific larger-dose retention |Not run |Exact Repeat17 endpoint and same dose/recipe used in comparison |
| Three-arm paired seeds17/23 |Not run; review required |All six endpoints, exact dose, primary and secondary contrasts |
| Independent scientific development |Reserved; not opened here |368 questions, seven endpoints, seed-specific and paired statistics |
| Frozen official GSM8K test |Not authorized or run here |1,319 questions, seven fixed endpoints, full denominator and uncertainty |

The empty scientific rows must not be represented as zero accuracy, synthetic
error bars, extrapolated gains, or inferred results from the older synthetic task.
If the scientific effect is null, show its interval relative to the predeclared
5-point meaningful margin. If imprecise or inconsistent, call it inconclusive.

## Figures and appendices once evidence exists

- Main result figure: all three conditions and both seed estimates on the
  independent evaluation, with paired differences and explicitly defined
  intervals. Do not manufacture a fitted allocation frontier from three cells.
- Diagnostic figure: gross base-success losses and gains for each endpoint,
  alongside native EOS, boundary and length-cap counts. This separates score
  accounting; it does not prove a latent reasoning mechanism.
- Data table: nominal/available P/K, unique pairs, exposures, total/per-update
  tokens, processed tokens and actual runtime. Preserve the matching residuals.
- Appendix: source and data hashes, rejected/missing responses, quality-review
  limits, exact schedules, raw-record auditor, all historical adverse evidence
  relevant to claims, full per-seed tables, and sanitized process/rental records.

A submission would also need an anonymous reproducibility package and an AI-use
statement. Record assistance with source review, code, analysis and drafting
honestly; authors remain responsible for checking the manuscript. Avoid public
repository links that identify authors in an anonymous review package. Essential
unique artifacts, including any historical weights needed for claims, require
verified independent preservation before calling the package complete.
