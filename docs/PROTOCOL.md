# Protocol v0.2 — implementation draft

## Question and tasks

Does within-problem structural path diversity provide benefits beyond global strategy coverage, exact repetition and surface rendering at matched SFT supervision and update budgets? Arithmetic expression construction is Task A. Typed graph/relational derivations are planned Task B. Real-math external validation is conditional on the controlled core. RL is excluded.

## Conditions

Repeat, Surface, Within-Problem Paths, Global-Coverage Matched; Breadth and Balanced are secondary. Shared anchors and paired seeds are required. Single-path coverage matching must report structural-frequency, length and operator-distribution residuals. The draft's fixed-set single-path R=1 row cannot by itself match the token budget of multiple paths; actual exposure allocation must be specified before any causal comparison. This remains a scientific decision, not a silent sampler default.

## Budgets and labels

Primary: supervised response tokens including terminal EOS and optimizer updates. Also record prompt+response processed tokens, padding, actual sample/path exposure, runtime and memory. Do not truncate valid answers or pad useful-token budgets. Do not pack examples initially. Each update's summed shifted target loss is divided by that update's total nonignored response targets, across accumulation microbatches.

## Models

Engineering: Qwen/Qwen2.5-0.5B base. Main: Qwen/Qwen2.5-1.5B base. Second: allenai/OLMo-2-0425-1B base, decisive comparisons only. Freeze exact model/tokenizer revisions. Use the same adaptation method within scientific comparisons. Full-parameter FP32 parameters with BF16 autocast and AdamW is the initial engineering baseline. A larger GPU is preferred to a hidden optimization change if the main model cannot fit.

## Evaluation

Fixed development-only subsets first. Greedy correctness, parse failures, EOS/termination, truncation, output lengths and reference NLL. Sampled pass@k on a common problem set, with independent samples per problem and problem-level aggregation. No final-test tuning; compositional OOD is not implemented by random IID splits.

## Gates

CPU correctness -> token/loss audit -> 32-example overfit and measured profile -> base capability calibration -> reviewed coverage/budget design -> single paired-seed scientific pilot -> human review before more seeds. Engineering smoke tests are not scientific treatment comparisons.
