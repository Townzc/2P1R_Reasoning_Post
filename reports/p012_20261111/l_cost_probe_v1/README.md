# T1 cost probe: remaining Tier 1 stopped

Accepted review `e10a4bf5` requires the complete Tier 1 training-plus-evaluation forecast to be at most $30. The measured H100 projection is **$49.56 without a margin**, or **$63.99 with the existing 25% compute margin and 30-second per-call tail allowance**. Remaining Tier 1 calls are stopped. R1/R2 use the separate approved G0-T budget and continue.

These are forecasts for all eight settings / 40 cells, not expenditure. The completed probe's function-duration estimate is $0.8269; accounting with tail and $0.10 storage reserves is $1.0670. Provider billing will replace these estimates when available.

## Original measured cell

Qwen2.5-1.5B base, MATH, L, seed 17; 512 distinct rows, two epochs, 128 updates; per-device 8, accumulation 1. Training source `0c09271a`; admissions `fe187aff`, `1b90d12a`, `a9ef372f`.

| Measurement | Result |
|---|---:|
| Training runtime | 44.9309 seconds |
| Seconds per update | 0.3510 |
| Full training function, including setup/save/hash | 88.4440 seconds |
| Peak GPU memory sampled every 30 seconds | 66,149 MiB = 64.60 GiB |
| Greedy first 20 engineering check | 74.0127 seconds; zero caps |
| Greedy complete MATH 5,000 | 219.1087 seconds; 3,515,732 output tokens |
| MATH-500, four sampled draws | 331.9184 seconds; 4,533,876 output tokens |

| Endpoint | Accuracy | Cap rate | Mean output tokens |
|---|---:|---:|---:|
| Full MATH test, greedy | 2,144 / 5,000 = 42.88% | 10.06% | 703.15 |
| MATH-500 subset of greedy | 209 / 500 = 41.80% | See original per-response data | — |
| MATH-500, mean of four draws | 642 / 2,000 = 32.10% | 49.20% | 2,266.94 |

All endpoints use OMI-2 / exported training template / 4,096 output / 8,192 context / math-verify. These are outputs of the L cell; a matched pre-SFT baseline is still pending C7. The first 20 probe checked checkpoint hashes, exact prompt-token identity, termination flags and special-token tails before full evaluation.

## Forecast calculation

`PROBE_AND_TIER1_FORECAST.json` contains the arithmetic and its inputs. Tier 1 comprises 33,792 updates: 32 full-dose cells and eight L cells. The forecast uses measured L seconds/update for all model/task settings, measured initialization/save overhead per training call, and two inference loads per cell. It scales generation by the required response counts: MATH 5,000 greedy plus 2,000 sampled; GSM8K 1,319 greedy plus 5,276 sampled. Completed L calls use their measured durations. The one engineering probe is included once.

The estimate uses MATH throughput/output behavior as a proxy for the unmeasured GSM8K and other checkpoints. The specific unknown is how much shorter/faster those runs will be. Savings from smaller Llama models, shorter GSM answers or better termination after more training have not been assumed. Even the projection without a margin exceeds the cap. Storage beyond the explicit probe reserve is additional.

The larger evaluation component is driven by the four-draw endpoint: 984 / 2,000 responses reach the output limit. Raw outputs and exact label files are preserved for the planned independent review.

## Resource alternative for an owner decision

The measured training allocation exceeds L40S's 48 GiB. A100 80 GB is the direct memory-compatible alternative. At the current [Modal prices](https://modal.com/pricing), its training allocation with the same CPU/RAM costs about $2.94/hour versus $4.40/hour for H100. It would need roughly 67% of H100's training throughput to save money. Its actual throughput is unmeasured; no alternative-GPU job has been launched.

The next main-grid action needs an owner decision following this registered stop. All current L artifacts remain reusable as the actual seed-17 L cell.
