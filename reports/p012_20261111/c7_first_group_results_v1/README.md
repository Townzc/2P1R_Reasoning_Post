# C7 first group complete; remaining C7 stopped at the $4 gate

Accepted review `07b56e49`, with N1 implemented in `e6183b90`. The authorized Qwen2.5-1.5B base × MATH group is complete. The three required classes project to **$5.69 without a margin**, or **$7.54 including the existing 25% time margin and 30-second per-call allowance**. Both exceed $4, so remaining C7 endpoints are stopped as instructed.

## Measured results

| Endpoint | Result | Function seconds |
|---|---|---:|
| Teacher NLL, 1,000 frozen solutions | 0.545724 nats/token; **0.212939 nats/character** | 40.1131 |
| Four-shot MATH-500 greedy baseline | 133 / 500 = **26.60%** | 116.0876 |
| Held-out pass@1, eight draws per question | 762 / 4,000 = **19.05%** | 419.3427 |
| Held-out pass@8 | 282 / 500 = **56.40%** | Same call |

The baseline has 39.40% length caps; the held-out samples have 29.375%. Generation keeps the frozen OMI-2 prompt, four conversation demonstrations, training template, 4,096 output / 8,192 context, and math-verify grading. No questions or draws were reduced. NLL uses the frozen zero-shot training prefix, including prompt masking and response terminator; raw solution characters are Unicode code points, including whitespace.

Measured function-duration cost for this group is approximately **$0.6623**; runtime plus per-call tail reserves is $0.7661, before a $0.10 late-charge reserve. These 22:00 UTC-hour jobs are not yet in a closed provider billing interval.

## Complete cost forecast

| Class | No margin | With time margin / tail allowance |
|---|---:|---:|
| 1. Eight NLL measurements | $0.37 | $0.73 |
| 2. Eight four-shot greedy baselines | $1.46 | $1.94 |
| 3. Eight held-out pass@8 endpoints | $3.86 | $4.86 |
| **Required classes 1–3** | **$5.69** | **$7.54** |
| 4. Four Instruct zero-shot baselines | $1.35 | $1.76 |
| 5. Four base zero-shot baselines | $1.35 | $1.76 |
| All endpoints | $8.40 | $11.05 |

Mandatory forecasts use the measured first-group rates for unmeasured settings, with GSM8K baseline generation scaled from 500 to 1,319 questions. NLL remains 1,000 solutions and pass@8 remains 500 questions for every setting. The specific unknown is the throughput/output length of the other initializations and GSM8K; no unmeasured savings are assumed. Optional zero-shot rows use the full 4,096-token output volume and measured baseline throughput, not an observed zero-shot score.

`C7_FORECAST_AND_STOP.json` records every endpoint's status. Three required endpoints are complete, 21 required endpoints are unrun at the cost gate, and all eight optional zero-shot endpoints are unrun. There are no active model jobs.

`original_c7_first_group.zip` preserves all NLL records, generated tokens/text, per-response grades and question-level pass metrics. The input hashes bind these outputs to the already audited C6 data. The separate main-grid cost stop remains unchanged.
