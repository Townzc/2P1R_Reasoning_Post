# Llama C7 holdout8

| Initialization | Task | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---|---:|---:|---:|---:|
| base | math | 0.38% (15/4000) | 73.80% | 2653 | 0.67% (7/1048) |
| instruct | math | 25.55% (1022/4000) | 3.30% | 21 | 26.42% (1022/3868) |
| base | gsm8k | 0.85% (34/4000) | 69.05% | 2556 | 1.29% (16/1238) |
| instruct | gsm8k | 4.65% (186/4000) | 0.00% | 0 | 4.65% (186/4000) |

Original frozen C7 conversations, reviewed family template and unchanged 4096/8192 generation limits. Raw outputs, labels and termination flags are retained in each ZIP. Built with Llama.
