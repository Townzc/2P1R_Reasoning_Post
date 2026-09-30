# Prioritized reading for the supervision migration question

September 29, 2026. This is the decision bibliography for Q2: the future value of
code-RL weights after moving from base tests to stricter public test supervision.
The order reflects relevance to this question, not a ranking of paper quality.
Start with 1–6. Entries 7–12 constrain the history/reset interpretation; the rest
cover adjacent mechanisms and exclusions. Papers are not all equally deeply read.
Version-specific section reads and metadata-only checks are recorded in the
[source record](Q2_READINESS_SOURCES_20260929.json). A literature search is not a
novelty guarantee; author claims are not independently reproduced results.

1. **[When the Reward Suite Is Leaky: A Preregistered Causal Contrast of Natural Verifier False Positives in RLVR](https://arxiv.org/abs/2607.11022v1).**
   Closest natural code-test setting and candidate public implementation. Read
   sections 3–4 and 7, especially the bounded negative findings and imperfect
   suite semantics. Its extra-only treatment is not our proposed union treatment.
   Read the [author erratum](https://github.com/toffee-desuwa/rlvr-leaky-suite/blob/9b6c86abeb4b837418b009d5354f81b43a28f84b/ERRATUM_20260711_suite_operationalization.md)
   alongside it. Prior relevant method/result sections read; arXiv v1.

2. **[Proxy Reward Internalization and Mechanistic Exploitation: A Learned Precursor to Reward Hacking and Its Generalization](https://arxiv.org/abs/2606.09711v1) (PRIME).**
   Direct overlap with correcting rewards and residual history. Read section 4.3
   first, then the experimental construction. Its engineered exploit setting
   differs from natural missing tests. Prior relevant sections read; arXiv v1.

3. **[Delay, Plateau, or Collapse: Evaluating the Impact of Systematic Verification Error on RLVR](https://arxiv.org/abs/2605.02909v2).**
   Explains why verifier errors cannot be summarized by one error rate. Read
   sections 3–4 and v2 section 4.6 on oracle/noisy alternation. Author metadata
   identifies COLM 2026; a proceedings record was not independently verified in
   this review. Relevant methods/results read in v1 and v2.

4. **[Spurious Rewards: Rethinking Training Signals in RLVR](https://arxiv.org/abs/2506.10947v2).**
   Course origin: apparent gains need not establish useful reward information.
   Read the model-dependent findings and clipping-bias explanation. Relevant
   course-review sections were read; not evidence for our rollback policy.

5. **[Reasoning or Memorization? Unreliable Results of Reinforcement Learning Due to Data Contamination](https://arxiv.org/abs/2507.10532v3).**
   Course origin and evaluation guardrail. Read the contaminated-versus-clean
   comparisons and conclusions. It does not establish that every coding model
   is contaminated or that our proposed external evaluation is already clean.
   Relevant sections read in the earlier course review;
   [AAAI 2026 proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/40687)
   independently located this turn.

6. **[Gradient Starvation in Binary-Reward GRPO: Why Group-Mean Centering Fails and Why the Simplest Fix Works](https://arxiv.org/abs/2605.07689v1).**
   Required alternative explanation for weak subsequent learning. Read sections
   3.1–3.3 and 4.3. All-fail/all-pass groups and group-size remedies are already
   studied; recording them alone is not a new mechanism. Relevant sections read.

7. **[Overtrained Language Models Are Harder to Fine-Tune](https://arxiv.org/abs/2503.19206).**
   Current performance and future adaptability can already disagree. Read
   sections 3.1–3.4 of the inspected v1; metadata now lists v2. Previously read
   for Q1, explicitly applied to the Q2 extra-training confound in this review.
   A generic current-to-future reversal is not our novelty.

8. **[When RL Fails after SFT: Rejuvenating Model Plasticity for Robust SFT-to-RL Handoff](https://arxiv.org/abs/2606.09932v1).**
   Closely related LLM trainability and reset/fusion explanation. Read sections
   3.1–3.4 and 4.1. Its over-SFT history is different from natural code-test RL.
   Prior relevant sections read; arXiv v1.

9. **[Resetting the Optimizer in Deep RL: An Empirical Study](https://arxiv.org/abs/2306.17833v2).**
   Explains why inherited optimizer state is a known confound and reset is not a
   novel algorithm. Read sections 2–3. NeurIPS 2023; prior relevant sections read.

10. **[The Primacy Bias in Deep Reinforcement Learning](https://proceedings.mlr.press/v162/nikishin22a.html).**
    Early data can impede later learning; adequate collected data and the ability
    to learn from it differ. Read sections 3–4. ICML 2022 official proceedings;
    prior relevant sections read. Different RL setting, not direct LLM evidence.

11. **[Deep Reinforcement Learning with Plasticity Injection](https://proceedings.neurips.cc/paper_files/paper/2023/hash/75101364dc3aa7772d27528ea504472b-Abstract-Conference.html).**
    Helps distinguish plasticity interventions from changed exploration. Read
    sections 3–5. NeurIPS 2023, not ICML; prior relevant sections read. Adapting
    it to this LLM experiment is not a free or already-implemented control.

12. **[Near-Future Policy Optimization](https://arxiv.org/abs/2604.20733v1) (NPO and AutoNPO).**
    Genuine training rollback with later successful trajectories already exists.
    Read sections 3.1–3.3 and Algorithm 1. The verifier stays unchanged, unlike
    the proposed migration. Relevant sections read; arXiv explicitly marks work
    in progress. Do not mistake the abstract's base-model comparison for GRPO.

13. **[Reinforcement Learning with Verifiable yet Noisy Rewards under Imperfect Verifiers](https://arxiv.org/abs/2510.00915).**
    Asymmetric reward-channel corrections are established. Prior methods/results
    review covered v1 sections 3 and 4.2–4.4; current metadata lists v4. This turn
    additionally inspected v4 section 3.1's assumptions and revision structure,
    not the entire revision. Its channel abstraction is not automatically a
    model of deterministic, program-dependent test omissions.

14. **[RL Fine-Tuning Heals OOD Forgetting in SFT](https://arxiv.org/abs/2509.12235v3).**
    Recovery can depend on the source checkpoint. Read section 3.2 and appendices
    B.2–B.3. Prior relevant sections read. An observed boundary or correlated
    advantage distribution does not identify our supervision-history mechanism.

15. **[Measuring Reward Hacking and Reasoning-Answer Decoupling Under Position-Confounded Optimization](https://arxiv.org/abs/2608.15445v1).**
    Relevant biased-to-unbiased continuation study. Read section 4.5 and setup.
    Constructed multiple-choice supervision differs from natural wrong-positive
    code rewards. Prior relevant sections read; workshop claims are not main-
    conference acceptance.

16. **[An Empirical Study of Reward Specification and Benchmark Reliability in GRPO-based LLM Unlearning](https://arxiv.org/abs/2608.17804v1).**
    Reward semantics, warm-start support and active groups must be separated.
    Read sections 4.1 and 5.4–5.5. Prior relevant sections read; unlearning is a
    different task, not a ready code-recovery implementation.

17. **[Anchored Policy Optimization: Mitigating Exploration Collapse via Support-Constrained Rectification](https://arxiv.org/abs/2602.05717v1).**
    Exploration/support collapse and rectification are existing concepts. Prior
    reading covered section 3 and appendices B.2–B.3. Do not transfer theoretical
    zero-support irreversibility to a finite-sample failure to find correct code.

18. **[Off-Context GRPO: Learning to Reason on Hard Problems using Privileged Information](https://arxiv.org/abs/2607.19313).**
    Supplying guided successes changes sampling and the objective; correction
    matters. Prior reading covered v1 sections 2–3 and appendix E.1. Current v2
    metadata and limited evaluation/setup passages were checked this turn, not
    the whole revision. Guided-data rescue is not an unclaimed method space.

19. **[Towards Robust Reinforcement Learning for Small-Scale Language Model Agents](https://arxiv.org/abs/2607.25091v1).**
    Weight rollback and optimizer reset already occur in small-LM training.
    Read section III-D and Algorithm 1. Its trigger is numerical failure, not
    a corrected verifier. Prior relevant sections read; stated venue acceptance
    was not independently established here.

20. **[ReViSQL: Achieving Human-Level Text-to-SQL](https://arxiv.org/abs/2603.20004v1).**
    Adjacent data-verification and RL work with industrial relevance. Our prior
    reading covered v1 sections 4.1 and 6.5. The current v4 title is
    [Human-Level Text-to-SQL via Reinforcement Learning on Verified Data, Without Pipeline Engineering](https://arxiv.org/abs/2603.20004).
    The old reading should not be represented as a full review of v4. Data repair
    also changes corpus composition; it is not a matched delayed-rollback study.

## Evaluation and algorithm background

These are supplementary original sources. This turn checks their identity and
metadata, rather than claiming a fresh full-paper read. Earlier asset inspection
primarily used official code, dataset cards and errata. They are not extra evidence
that the proposed history effect exists.

- [Is Your Code Generated by ChatGPT Really Correct? Rigorous Evaluation of Large Language Models for Code Generation](https://arxiv.org/abs/2305.01210) (EvalPlus).
- [Program Synthesis with Large Language Models](https://arxiv.org/abs/2108.07732) (MBPP).
- [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374) (Codex and HumanEval).
- [LiveCodeBench: Holistic and Contamination Free Evaluation of Large Language Models for Code](https://arxiv.org/abs/2403.07974).
- [DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models](https://arxiv.org/abs/2402.03300) (GRPO background).

The course syllabus, author errata, source code and an industrial rollback report
are separate non-paper sources. Q1-only papers and abstract-only rejected search
hits are not mixed into this Q2 decision bibliography. Later versions still need
method-level comparison wherever a new claim would rely on them.
