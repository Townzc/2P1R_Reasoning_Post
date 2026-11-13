# A5-1 restored Qwen-Instruct zero-shot baselines

Frozen C7 baseline0 conversations, greedy4096/8192, seed17. Original generation and scorer unchanged.

| Task | 0-shot | 4-shot | Higher baseline |
|---|---:|---:|---|
| math | 53.80% | 36.20% | 0shot |
| gsm8k | 59.06% | 59.51% | 4shot |

| MATH cell | MATH-500 | Δ versus0-shot | Δ versus4-shot |
|---|---:|---:|---:|
| P | 42.40% | -11.40pp | +6.20pp |
| K8 | 41.40% | -12.40pp | +5.20pp |
| R | 34.40% | -19.40pp | -1.80pp |
| K4 | 41.60% | -12.20pp | +5.40pp |
| L | 43.20% | -10.60pp | +7.00pp |

P is11.4pp below the restored zero-shot baseline; using only4-shot reverses the sign of the SFT comparison. Both registered baseline contrasts are retained. The newly restored baselines await independent result audit.
