# Llama C7 NLL measurements

| Model | Task | NLL/token | NLL/character |
|---|---|---:|---:|
| meta-llama/Llama-3.2-1B | gsm8k | 1.025182 | 0.305282 |
| meta-llama/Llama-3.2-1B | math | 0.873455 | 0.322720 |
| meta-llama/Llama-3.2-1B-Instruct | gsm8k | 0.605728 | 0.180375 |
| meta-llama/Llama-3.2-1B-Instruct | math | 0.542218 | 0.200336 |

Each endpoint uses the same frozen 1000 teacher solutions, with no training. Per-character NLL is provided for comparisons across tokenizer families. Per-solution records and token counts are in the four ZIPs. Built with Llama.
