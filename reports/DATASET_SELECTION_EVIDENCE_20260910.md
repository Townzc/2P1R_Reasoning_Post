# Dataset selection: evidence, roles and proposed scope

**Subsequent work:** [C017 completed the CPU source/split, solution and attrition
audit](REAL_MATH_CPU_AUDIT_20260910.md). Statements below that no ingestion/audit
had occurred describe this earlier literature-review milestone.

2026-09-10 UTC. Read-only literature and dataset-metadata review supporting
[P004](../docs/experiments/P004_cost_aware_sft_allocation_proposal.md).
This is a proposed data-scope extension, not an approved training grid, a data
release or a completed acquisition experiment. E012 remains paused.

## Conclusion and connection to existing progress

GSM8K is a defensible first calibration task, but the previous proposal did not
adequately justify its selection or specify a second real problem distribution.
For a claim about allocation across problem coverage, difficulty and solution
quality, propose GSM8K as the primary study and a stratified MATH subset for
decisive second-task comparisons. Public solution corpora and robustness tests
serve different roles; counting their names does not establish task breadth.

The existing Qwen1.5B/A800 stack provides engineering evidence, not GSM8K or
MATH performance. Earlier arithmetic transfer was weak, matching changed the
supported problem population, and E011 failed complete-proof training. Preserve
those outcomes. Do not infer that real tasks or a larger benchmark automatically
fix the failure. See the [progress inventory](MODEL_SELECTION_EVIDENCE_20260910.md).

## What the referenced papers use

The first three rows are the original reading-list papers; the remaining four
come from the later positioning review. These are selected experiments relevant
to our question, not a claim to list every baseline dataset in each paper.

| Paper and inspected location | Training problems and solution source | Evaluation and scope distinction |
| --- | --- | --- |
| [Data Repetition Beats Data Scaling in Long-CoT SFT](https://arxiv.org/html/2602.11149v1), sections 2.2–3 | Dolci-Think-SFT-7B, filtered for first-turn reasoning traces and length; new teacher-distillation comparisons use NuminaMath-TIR as the question pool | AIME 2024/2025 and GPQA. NuminaMath-TIR supplies questions for newly generated solutions in that comparison. |
| [CoScale-RL](https://arxiv.org/html/2601.14695v1), section 4.1 and appendix D.2 | Filtered OpenMathReasoning combinatorics/probability questions, existing responses and additional QwQ-32B solutions | Selected MATH-500, AMC, OlymMATH subsets; held-out OpenMathReasoning and ReasoningGym. The separate SFT problems-versus-solutions ablation evaluates seen training questions, not held-out allocation generalization. |
| [What Do Learning Dynamics Reveal About Generalization in LLM Reasoning?](https://arxiv.org/html/2411.07681v1), sections 4.2–5 | GSM8K and MATH training data with reference solutions | Corresponding test data and prompt-perturbation analyses. This directly motivates comparing learning dynamics on both problem families. |
| [Why Do Reasoning Models Lose Coverage?](https://arxiv.org/html/2605.17026v2), section 4 and appendix B.1 | Synthetic path-star graphs; GSM8K questions with natural-language responses from OpenMathInstruct-2 and code responses from OpenMathInstruct-1 | Synthetic graph evaluation and original GSM8K test. Two solution corpora still share one underlying math question family. |
| [Learning Diverse Responses with Prefix-Conditioned Supervised Fine-Tuning](https://aclanthology.org/2026.acl-long.9.pdf), sections 4.1 and 4.3 | Section 4.3 names “OpenThought3-1.2M” and describes 16 responses per question in its training setup | AIME 2024/2025, HMMT, GPQA-Diamond and LiveCodeBench, among other evaluations. The paper's construction is not evidence that every public corpus question has 16 unique strategies. |
| [Training Large Language Models to Reason in Parallel with Global Forking Tokens](https://arxiv.org/html/2510.05132), section 3 and appendix A.9 | s1k with four selected teacher traces per question; additional Open-R1-Math220k and Open-Thoughts coding experiments | AIME, MATH-500, GPQA-Diamond and LiveCodeBench. DAPO-Math-17k is used for additional RL, not the main SFT question pool. |
| [Spend Wisely](https://arxiv.org/html/2501.18962v2), section 4.3 | Regenerated GSM-Symbolic/GSM-P1/GSM-P2 template instances, mixed 7:2:1, with self-generated solutions filtered by final answers | Held-out data from the three difficulty families. This is not simply SFT on the original GSM8K training split. It already studies generation/training cost allocation. |

The model and hardware implications are recorded separately in the
[compute audit](RELATED_WORK_MODEL_COMPUTE_20260910.md). Reusing a dataset idea
does not require reproducing a paper's large teacher, student or RL pipeline.

## Proposed assets and why they belong

**GSM8K: primary calibration and allocation study.** The
[official repository](https://github.com/openai/grade-school-math) describes
human-written arithmetic word problems with reference solutions, separate
training/test data and short multistep calculations. These properties make
problem identity, final-answer scoring and small-model learning checks practical.
The native references do not provide the controlled multi-solution inventory
our study needs. Its narrow domain also limits any universal allocation claim.
Public availability does not measure a human problem-writing price or establish
absence from a student's pretraining data.

**MATH: proposed second real problem distribution.** The
[original paper](https://arxiv.org/html/2103.03874v2) specifies 7,500 training and
5,000 test questions, seven subjects, difficulty levels 1–5 and worked solutions.
Propose levels 1–3 as the initial bounded population, stratified by available
subject and difficulty labels before inspecting teacher success. Human difficulty
labels are covariates, not measured student difficulty. Verify parsing, any
diagram requirements and learning feasibility before training. Disclose any
exclusions and restrict claims to the resulting population. Replicate decisive
contrasts rather than promise a second complete grid. MATH-500 would be an
evaluation subset, not another training corpus.

There is a concrete split-provenance issue: the download mirror linked from the
[author repository](https://github.com/hendrycks/math),
[qwedsacf/competition_math](https://huggingface.co/datasets/qwedsacf/competition_math),
currently presents all 12.5k rows under one `train` split. That label cannot
establish membership in the original 7.5k training set. Reconstruct and verify
original split membership using source identifiers/file lists before use;
unresolved rows are ineligible for training. No corpus has been ingested here.

**OpenMathInstruct-2: candidate output bank.** The
[NVIDIA dataset card](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2)
describes approximately 14M problem-solution pairs generated using
Llama-3.1-405B-Instruct, including original GSM8K/MATH training questions and
synthetically augmented questions. Original-question expected answers come from
the source data; augmented-question answers use majority voting. These are
different provenance/quality groups. Initially audit only responses that can be
linked to original, eligible training questions. Reusing released responses does
not require running the 405B teacher. This is an output source spanning two
question families, not a third independent reasoning task.

**GSM-Symbolic: evaluation-only robustness check.** The
[Apple repository](https://github.com/apple/ml-gsm-symbolic) provides templates
and generated variations for GSM-Symbolic, P1 and P2. Its `original_id` refers
to a GSM8K test question. Keep these parents and all their variants out of
training and allocation selection; group uncertainty by parent/template. Fifty
variants of one template are not fifty independent problem families. The
repository currently says generation/parsing code is not released, so do not
assume a ready-to-run official generator. This evaluates specified variations,
not arbitrary compositional generalization or pretraining decontamination.

**Existing synthetic tasks: diagnostic role.** Preserve exact verifiers and
program labels for targeted repetition, surface and structural-path controls.
Their low marginal generation cost represents a different acquisition scenario
from newly curated human problems. Do not restart a large graph curriculum as
a prerequisite for the revised real-data question.

## Data work that makes the allocation study interpretable

1. **Provenance and splits.** Record source revision, original parent ID, split,
   subject/difficulty where available, answer provenance and content hashes.
   Split parent problems before solution augmentation. Check cross-corpus and
   near-duplicate overlap; no resulting claim of unknown pretraining cleanliness.
2. **Selection before outcomes.** Draw nested, seeded problem pools before
   inspecting how many usable solutions they yield. Record acquired P,
   trainable P, attempted generations and accepted K_i, including zero. Never
   restrict all conditions to questions already known to have four good traces.
   Report coverage and difficulty shifts through every filter. Earlier matching
   failures make this a necessary design constraint.
3. **Quality and diversity.** Check answer equivalence, formatting, duplicates
   and a prespecified sample of reasoning steps. Final-answer agreement alone
   does not verify the full argument. Distinguish duplicate text, paraphrases
   and evidence of different solution structure. Keep one teacher/source fixed
   within each primary contrast; NL/code source differences are not a free
   causal manipulation of diversity.
4. **Training exposure.** Audit response tokens, processed tokens, lengths,
   updates, repetitions and actual runtime. Match the declared primary budget;
   disclose residual differences rather than silently dropping long solutions
   or repeating the previous selection-by-exact-matching failure.
5. **Acquisition economics.** Public caches support retrieval/curation cost
   measurements and explicitly modeled price scenarios. Accepted outputs alone
   do not identify historical failed attempts or generation costs. A local
   Math1.5B pilot cannot price the production of 405B-generated cache contents:
   their quality and yield may differ. An observed generation-cost claim needs
   aligned source-specific acquisition and training comparisons. Keep public
   retrieval, local generation and hypothetical problem prices distinct.
6. **Decision validation.** Develop the allocation rule using development data;
   test it on fresh training-pool draws and allocations not used to fit it.
   Compare problem-first, solution-first and a fixed mix under the same stated
   constraints. Freeze the final benchmark evaluation once; MATH test and
   GSM-Symbolic cannot select teachers, difficulty cutoffs or stopping rules.

Two datasets alone would not establish a contribution. The proposed evidence
is how acquisition yield, problem coverage and solution quality change the
measured value of another problem versus another solution, and whether that
decision transfers to new draws and a second task. Negative or task-dependent
results remain valid outcomes; broad novelty and optimality are unestablished.

## Next bounded step and resource status

Prepare a CPU data manifest and acquisition-audit specification for review,
starting with original training problems and capped solution retrieval. Check
source licensing, split reconstruction, storage and per-problem coverage before
any download of a large output corpus. With the existing 50GB disk limit, stream
selected data or retrieve required shards only; avoid downloading all corpus
subsets or large teacher weights. Price the complete proposed GPU phase after
this audit. No new server is needed for this documentation step.

The primary student remains Qwen2.5-1.5B base; OLMo-2-0425-1B stays conditional.
The choice between a public solution bank and bounded Math1.5B generation is
unresolved. No dataset/model download, teacher call, server contact or experiment
occurred in this review. Frozen E012 files and the resource ledger remain
unchanged: 5971/7200 process seconds used, 1229 left, 16 receipts, zero reservations.
