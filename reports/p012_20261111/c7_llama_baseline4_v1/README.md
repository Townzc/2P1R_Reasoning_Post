# Llama C7 baseline4

| Initialization | Task | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---|---:|---:|---:|---:|
| base | math | 0.00% (0/500) | 99.80% | 243 | 0.00% (0/1) |
| instruct | math | 13.40% (67/500) | 16.00% | 59 | 15.95% (67/420) |
| base | gsm8k | 0.30% (4/1319) | 100.00% | 1231 | undefined |
| instruct | gsm8k | 38.82% (512/1319) | 0.45% | 5 | 38.99% (512/1313) |

Original frozen C7 conversations, reviewed family template and unchanged 4096/8192 generation limits. Raw outputs, labels and termination flags are retained in each ZIP. Built with Llama.

The Llama base MATH endpoint has0/500 correct and499/500 length caps. Inspection of the first three original responses shows loops and continuation into invented examples. This is a degenerate response baseline under the frozen conversation protocol; zero score does not isolate mathematical competence. Its cause is not established. Keep the endpoint unchanged and flag the issue when interpreting delta-SFT.
