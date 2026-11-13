# C7 Qwen completed

| Model | Task | NLL/token | NLL/character | 4-shot greedy | Holdout pass@1 | Holdout pass@8 |
|---|---|---:|---:|---:|---:|---:|
| base | math | 0.545724 | 0.212939 | 26.60% | 19.05% | 56.40% |
| base | gsm8k | 0.586087 | 0.195624 | 65.20% | 58.80% | 92.80% |
| instruct | math | 0.483625 | 0.188709 | 36.20% | 55.20% | 83.80% |
| instruct | gsm8k | 0.510451 | 0.170378 | 59.51% | 65.92% | 95.20% |

NLL: 1,000 frozen solutions per setting; pass@8: 500 frozen held-out questions × 8 draws. Baseline: MATH-500 or all 1,319 GSM8K test questions. All use 4,096 generation / 8,192 context limits. Holdout prefix is 4-shot for base and 0-shot for Instruct, as registered.

The existing base × MATH group is reused from `c7_first_group_results_v1`. New raw output, token IDs, labels and manifests are in the nine ZIPs.

Technical results only. Independent results audit is pending.
