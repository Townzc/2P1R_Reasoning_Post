# Literature audit for the next experiment

2026-09-10 UTC. Planning evidence, not experimental results or a novelty claim.
The owner requested broader ICLR/ACL literature and corrected rental accounting.
All work in this review used local CPU and public primary sources; no server,
pretrained inference, training, teacher API or new compute reservation was used.

We inspected relevant methods, ablations and implementation sections of eleven
full papers. Official proceedings establish the venues below; Findings is
identified separately from the main conference. PDF hashes, page counts and
reading locations are in [the source manifest](literature_next_20260910_sources.json).
PDFs and extracted text stay in the private cache. Four key figure/method pages
were rendered and visually checked. This is a targeted review, not an exhaustive
systematic review. Previously audited papers are not presented as new discoveries.

## Evidence and transfer limits

| Paper / verified venue | Relevant design and evidence | Implication for this project |
|---|---|---|
| [OpenMathInstruct-2](https://proceedings.iclr.cc/paper_files/paper/2025/hash/302ce0673c00aee2cf84bb43d0117553-Abstract-Conference.html), **ICLR 2025** | Section 2 uses Llama-3.1-8B base. At 256K training pairs, varying unique MATH questions from 1K to 6.5K strongly favors breadth. Other ablations balance teacher question coverage; shorter OpenMath-style traces outperform a more verbose format. Four epochs and fixed pair counts do not establish equal supervised-token or rental budgets. | Breadth is an established, necessary comparator. Format/length and teacher identity must not be called independent causal factors without controls. Main 8B/70B, 14M-pair results are not a small-student budget prescription. |
| [Symbolic Chain-of-Thought Distillation](https://aclanthology.org/2023.acl-long.150/), **ACL 2023 main** | OPT students span 125M–1.3B. Section 4 downsamples 30 rationales to an average of five, comparing random, diversity, teacher likelihood and variable allocation. Bigram-based openness assigns 1/3/5/7/9 rationales across quintiles. Random selection is strong; no subset matches all 30. Core selection tasks are commonsense reasoning. | Neither multiple rationales nor adaptive K is new by itself. Include random selection and repetition controls. Matching rationale counts does not match token exposure; lexical openness is not a verified mathematical strategy. |
| [DART-Math](https://proceedings.neurips.cc/paper_files/paper/2024/hash/0ef1afa0daa888d695dcd5e9513bafa3-Abstract-Conference.html), **NeurIPS 2024 main** | Rejection filtering under equal raw attempts loses harder questions. Uniform targets accepted counts; Prop2Diff allocates by measured teacher failure rate, with at least one response and an attempt cap. Approximately 590K-example comparisons use 7B/8B/70B students and a DeepSeekMath-7B-RL teacher, while student training is SFT. Appendix B reports substantial synthesis/training resources; creation cost is partly argued through reuse amortization. | Explicitly retain zero-success parents and rejected attempts. Our capped, prefiltered cache cannot recover teacher failure rates or original acquisition cost. Adaptive allocation and cost arguments have direct predecessors; a new cost formula alone is insufficient. No RL student is needed to borrow this insight. |
| [Small Models Struggle to Learn from Strong Reasoners](https://aclanthology.org/2025.findings-acl.1301/), **Findings ACL 2025** | Qwen/Llama **Instruct** students include 0.5B–3B. MATH teacher comparisons and mixtures show that stronger/longer reasoning is not uniformly better for small students. Appendix A uses four A100 80GB GPUs, two epochs and cosine LR 1e-5 for full tuning. Teacher identity, style and length vary together. | Test compatibility with the student, not teacher reputation alone. Our base model, short references and 32 exposures differ materially. The paper does not prove that reducing our LR, shortening every trace or switching to Instruct will fix E013. |
| [Unveiling the Key Factors for Distilling Chain-of-Thought Reasoning](https://aclanthology.org/2025.findings-acl.782/), **Findings ACL 2025** | Six granularity levels, multiple representation formats and several teachers are studied with BLOOM 560M–3B and small Gemma/Llama students, including GSM8K/MATH. Granularity effects are nonmonotonic. Appendix B specifies three epochs, cosine LR 3e-5; Appendix C generates traces conditioned on ground-truth answers. | A student–trace compatibility hypothesis is plausible. Neither shortest-is-best nor answer agreement implies sound intermediate reasoning. Ground-truth-conditioned synthetic text is not an unbiased sample of teacher solving success. No transferable single-A800 wall time is established. |
| [Towards Efficient CoT Distillation: Self-Guided Rationale Selector](https://aclanthology.org/2025.findings-emnlp.413/), **Findings EMNLP 2025** | MoRSD filters for accuracy/diversity, then selects low RD: PPL_student(answer given question and rationale) divided by PPL_student(answer given question). Default Flan-T5 students use GPT-3 rationales on seven small reasoning datasets. Appendix A reports V100s, up to 10K updates and **best test accuracy during training**. | RD is not full-trace NLL or E014's memorized loss. A future student-aware selector needs charged forward passes, a fixed training endpoint, random controls and a test of trivial answer copying. Do not import its test-based checkpoint selection. |
| [Teach Small Models to Reason by Curriculum Distillation](https://aclanthology.org/2025.emnlp-main.376/), **EMNLP 2025 main** | Qwen2.5-3B base/Instruct learn from two 32B teachers on 6,445 MATH questions common to all successful generation modes. A two-stage mixture changes teacher mode with difficulty: concise heuristics first, selected explicit traces later. Table 2 improves over single-stage baselines. Generation/evaluation can reach 16K tokens and multiple samples per problem. | Curriculum is a distinct alternative to static selection. Intersection filtering, teacher style, stage order and total dose can confound it. Compare reordered versus shuffled versions of the **same multiset at the same total dose** before claiming an ordering effect. Not the first experiment under 733 process seconds. |
| [MCC-KD](https://aclanthology.org/2023.findings-emnlp.454/), **Findings EMNLP 2023** | Diverse rationales are selected using trigram Jaccard; training adds bidirectional KL between answer-token distributions under two rationales. GSM8K/SVAMP/ASDiv and OOD arithmetic are included; students are larger Flan-T5/Llama variants. This is an extra consistency objective, not simply more response rows. | Answer consistency is an alternative mechanism to coverage. Two conditioned distributions and their gradients need explicit compute accounting. First compare ordinary multi-response SFT with random/lexical selection; do not silently change the objective across allocation arms. |
| [Learning Diverse Responses with Prefix-Conditioned Supervised Fine-Tuning](https://aclanthology.org/2026.acl-long.9/), **ACL 2026 main** | P-SFT prepends a semantically unrelated random-integer prefix, resampled every training iteration. It also studies inference-only prefixes. Students include Qwen2.5-7B-Instruct, Llama3.1-8B-Instruct and Qwen3-8B; Appendix B reports 32 H200 GPUs. Ordinary sampling and prefix inference use different temperatures. | A lightweight SFT mechanism to consider **after** demonstrating multi-response collapse. Prefixes are not labels for known reasoning strategies. Separate train-prefix and inference-prefix effects, hold sample counts fixed and charge extra prompt tokens. E013 has one target per problem, so its failures do not establish this mechanism. |
| [Training Large Language Models To Reason In Parallel With Global Forking Tokens](https://proceedings.iclr.cc/paper_files/paper/2026/hash/88af3540325dd0b70617a9ab605f294d-Abstract-Conference.html), **ICLR 2026** | SSFT optimizes a set objective using bipartite matching between control tokens and reasoning traces. Appendix A.9 reports 32B SFT on eight B200 GPUs for 6.5 hours, with four traces and six controls. A random-matching baseline is included. GFPO is a separate RL component. | Coverage-sensitive SFT has strong prior art and additional matching/forward cost. Retain only the SFT idea as a distant fallback; do not implement the RL stage or treat the full method as a cheap patch. |
| [RL Squeezes, SFT Expands](https://proceedings.iclr.cc/paper_files/paper/2026/hash/e52554a70e0df57a0bea11d1eca0c9b5-Abstract-Conference.html), **ICLR 2026** | The study includes Qwen2.5-Math-1.5B and released SFT/RL descendants. It separates correct/incorrect output clusters using chrF; main trajectory measurements draw 256 samples/problem. Appendix C.7 adds single-response SFT on s1k-1.1. Different released checkpoints and context limits complicate causal comparisons. | SFT can expand correct-output coverage in these settings; universal collapse is not established. Use correctness and termination alongside diversity. Lexical clusters are proxies, and 256 long generations/problem are inappropriate for our immediate budget. RL remains outside scope. |

## Synthesis that changes the plan

1. **Question breadth, multiple rationales, variable K and diversity selection all
   have close precedents.** A credible contribution needs a sharper empirical
   boundary: under a specified small-student SFT budget, when does another usable
   solution help more than another problem, after selection loss and implementation
   cost? This remains a candidate question, not established novelty.
2. **Compatibility and optimization are different hypotheses.** E014 shows local
   reference argmax misses, not a teacher-capacity diagnosis. Its failed examples
   include short targets. We should first isolate a bounded optimization change;
   thereafter compare data selection at fixed problems and dose. Changing model,
   prompts, teacher, scheduler and K together would make the result uninterpretable.
3. **Filtering can manufacture an apparent efficiency improvement by dropping
   problems.** [C018](REAL_MATH_C018_SELECTION_AUDIT.md) measures this directly on
   the existing cache. Any adaptive rule must retain its original parent denominator
   and compare against random selection; unavailable solutions stay unavailable.
4. **Cost has three separate meanings:** the current scientific process guard,
   actual rental time from power-on to provider-confirmed stop, and data-acquisition
   cost. Cached teacher creation cost is unknown; CPU work on a running rental is
   still billable. No paper's GPU-hour number can substitute for our rental bill.

Previously reviewed repetition, CoScale-RL, coverage and Spend Wisely papers
remain in [the earlier compute audit](RELATED_WORK_MODEL_COMPUTE_20260910.md).
This review broadens the alternatives; it does not erase those comparisons or
turn large-model evidence into an endorsement of a large-model replication.

The concrete staged choice, stopping rules and rental window are in
[P005](../docs/experiments/P005_literature_guided_next_phase.md).
