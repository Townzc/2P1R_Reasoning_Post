# Related-work model and compute audit

2026-09-10 UTC. Primary-source follow-up to the existing
[closest-work notes](../docs/CLOSEST_WORK.md),
[positioning review](ICLR_POSITIONING_20260909.md) and
[model-choice evidence](MODEL_SELECTION_EVIDENCE_20260910.md).
The owner explicitly excludes compute-heavy model plans. This note informs
P004's proposed scope; it does not register or execute an experiment.

## What the previously referenced papers actually use

A trained student, a solution generator and an off-the-shelf evaluation baseline
have different costs. These are paper-reported configurations, not measurements
on our A800. Missing hardware/time entries are not zero-cost claims.

| Paper and inspected sections | Trained students / backbones | Other model roles and compute implications |
| --- | --- | --- |
| [Data Repetition Beats Data Scaling in Long-CoT SFT](https://arxiv.org/html/2602.11149v1), sections 2.2, 3 and appendix A | Qwen3-4B, Qwen3-8B and Olmo3-7B | Teacher sensitivity uses Qwen3-0.6B and Qwen3-8B reasoning checkpoints while retaining Olmo3-7B as student. BF16, Unsloth and 8-bit Adam; each configuration uses one H100 94GB for up to 24 hours. Evaluation permits 30k output tokens. The 0.6B teacher is not a 0.6B main student. |
| [CoScale-RL](https://arxiv.org/html/2601.14695v1), sections 4.1, 5.1–5.3, figure 5 and appendix D.2 | Main pipeline: Qwen2.5-0.5B-Instruct. Solutions-versus-problems SFT ablation: Qwen2.5-1.5B-Instruct. Additional checks: Llama3.2-3B-Instruct and Qwen2.5-7B-Instruct | QwQ-32B generates additional solutions; Qwen2.5-32B-Instruct helps curate problem categories. Appendix D.2 evaluates 16 generations per problem, up to 16k tokens, on seen/trained problems. Small-student precedent does not make the teacher-plus-RL pipeline inexpensive or establish held-out generalization. These students are Instruct, unlike our base checkpoint. |
| [What Do Learning Dynamics Reveal About Generalization in LLM Reasoning?](https://arxiv.org/html/2411.07681v1), section 4.2 and appendix A | Pretrained Llama3-8B and Gemma2-9B on GSM8K/MATH | Learning-rate, epoch and data-size experiments use larger students than our proposed core. Borrow the learning-dynamics measurements; do not budget a reproduction of this model/grid combination. No hardware-hour figure is established by this audit. |
| [Why Do Reasoning Models Lose Coverage? The Role of Data and Forks in the Road](https://arxiv.org/html/2605.17026v2), section 4 and appendices A–B | Graph SFT: Qwen2.5-0.5B and EvoLM-1B. Math SFT also includes EvoLM-4B; appendix B.2 adds Olmo-7B | Math uses GSM8K problems with existing OpenMathInstruct-1/2 responses. R1-distilled models are also examined off the shelf; they are not all newly trained SFT students. Math evaluation samples 64 responses per question. This is a direct small-student precedent, with substantial evaluation cost still possible. Its Olmo-7B is not our proposed OLMo-2-0425-1B. |
| [Learning Diverse Responses with Prefix-Conditioned Supervised Fine-Tuning](https://aclanthology.org/2026.acl-long.9.pdf), section 4.1 and appendix B | Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct and Qwen3-8B | Appendix B reports training on 32 H200 GPUs, without a per-configuration hour estimate there. Claude Sonnet 4.5 is used for diversity judging. Its reported infrastructure is outside our minimum plan. |
| [Training Large Language Models to Reason in Parallel with Global Forking Tokens](https://arxiv.org/html/2510.05132), section 3 and appendix A.9 | Main: Qwen2.5-32B-Instruct. Extensions include Qwen2.5-Math-7B, Qwen3-4B-Base and Llama3.1-8B-Instruct | Appendix A.9.2 reports SSFT-32B training plus logging taking 6.5 hours on eight B200 GPUs. The 93k-example 7B experiment in A.9.4 takes about four days on eight A100s. These are SFT configurations; their separate RL stages are not part of our scope. |
| [Spend Wisely](https://arxiv.org/html/2501.18962v2), section 4.3 and appendix E.4 | Llama-3-8B-Base with full-weight fine-tuning | Iterative self-generated math solutions are filtered and reused for training. The math experiment reports about 400 A800 GPU-hours per configuration, even with a 512-token generation maximum. This is a cost-allocation reference, not a feasible replication target for the present allowance. |

The original three reading-list papers are the first three rows; the rest come
from the later positioning/cost-framing review. None establishes that a small
checkpoint will succeed on our task or yield an ICLR contribution. CoScale's
seen-problem comparison must not be presented as an answer to our proposed
held-out allocation question.

## Proposed compute-constrained selection

1. Retain **Qwen2.5-1.5B base** as the first primary-student calibration candidate.
   Small-model precedents complement our existing measured pipeline; this is
   not an exact reproduction of CoScale's Instruct setup. Keep Qwen0.5B for
   debugging. Exclude a 4B/7B/8B/9B/32B student grid from the minimum plan.
2. Keep **OLMo-2-0425-1B base** conditional, for decisive second-family checks
   after capability and throughput calibration. It comes from our earlier
   protocol, not a claim that these papers used this exact checkpoint. It has
   not run, and is not a prerequisite for the first real-data pilot.
3. Remove **Qwen2.5-Math-7B-Instruct as the default teacher commitment** in P004.
   First audit reusable multi-solution math data on CPU. For new local sampling,
   consider **Qwen2.5-Math-1.5B-Instruct** in a bounded calibration. Its
   [maintainer card](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct)
   confirms math CoT support, not our answer/trace quality or cost. Neither
   teacher has run. The earlier 7B proposal is historical and outside the minimum
   plan; no 32B teacher or paid generation service is planned.

The small teacher is a candidate, not a validated replacement. A smaller model
can lose on cost per usable solution if it produces more failures or duplicates.
Count all attempted tokens, runtime, verification and rejection costs; audit
reasoning rather than only final answers. Preserve failed problems and acquisition
denominators instead of retaining only questions that supply K solutions. Freeze
one teacher/source within a comparison so quality/style does not change with
allocation. TIR model-card scores are not tool-free CoT quality measurements.

Third-party cached solutions can cheaply test training-allocation feasibility.
Without generation-attempt/cost logs, they cannot establish our measured marginal
generation price or acceptance yield. Separate our actual retrieval/curation
spend, unknown historical production cost, and counterfactual price scenarios.
A later bounded local-generation audit is needed for claims about an observed
acquisition process. Public GSM8K subsampling likewise does not measure human
question-writing prices.

## Fit with our results and the next gate

Our 1.5B stack has measured A800 feasibility, but synthetic generalization is
weak and E011 failed full-proof training. E011 peak allocated/reserved CUDA
memory was 27.18/29.13 GiB with FP32 parameters and AdamW. These task-specific
measurements are not GSM8K estimates. See [E011](RELATION_E011_RESULTS.md)
and [the evidence inventory](MODEL_SELECTION_EVIDENCE_20260910.md).

Before a new training proposal, price an entire bounded phase: teacher attempts,
verification, student updates, response lengths, evaluation samples, seeds and
checkpoint storage. The nine P/K cells remain a candidate range, not a promised
full sweep. Choose a small informative subset and decisive replications after
profiling. Do not silently alter precision/adaptation between arms, truncate
correct traces, or select easier questions based on teacher success to fit the
budget. Check real-task learning and floor/ceiling effects before interpreting
allocation differences.

No model download, SSH contact, GPU process, new budget or runtime/configuration
change occurred. E012 remains paused and its release is unchanged. The ledger
is still **5971/7200 process seconds used, 1229 remaining, 16 receipts, zero
reservations**. This allowance is not a cost estimate for the proposed real-data
study. The 50GB disk constraint remains in force.
