# R2 reproduction: PASS

Llama-3.2-1B-Instruct, public UWNSL short-chain data, seed 42, two epochs, global batch 16 (2 × accumulation 8), 666 optimizer updates. Accepted T2 recipe; detached launch.

| Benchmark | Measured | Paper | Difference | Gate |
|---|---:|---:|---:|---|
| MATH-500, exact OR math-verify | 167 / 500 = **33.40%** | 33.4% | 0.00 pp | PASS |
| GSM8K, Li flexible extraction | 679 / 1,319 = **51.48%** | 49.2% | +2.28 pp | PASS |

MATH exact matching alone is 158 / 500 = 31.60%; math-verify adds nine correct. No judge model was loaded. Output cap rates are 7.20% for MATH and 0.758% for GSM8K. Li's 16,384 output / 32,768 context protocol is unchanged.

Training completed in 651.8776 function seconds. The original output archive contains training metadata/logs, complete inference tokens/text and labels. All 15 final checkpoint files (4,960,885,314 bytes) have an independent local copy with matching SHA256 values; the original remote checkpoint remains intact. The earlier batch-8 run was stopped when T2 superseded it and remains separate.

Both R1 and R2 now pass the registered reproduction thresholds. G0-T accounting including the failed/superseded attempts, completed new runs and reserves is in `G0T_BUDGET.json`; it remains within $10. R3 is held. The main-grid $30 cost gate remains stopped, while the separately approved C7 first group proceeds.

Built with Llama.
