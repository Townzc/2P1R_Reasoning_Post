# Tier 1 Qwen base × GSM8K, seed 17

| Cell | Correct / 1319 | Accuracy | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 909 | 68.92% | 0.68% | 8 | 69.39% (909/1310) |
| K8 | 860 | 65.20% | 0.91% | 8 | 65.80% (860/1307) |
| R | 806 | 61.11% | 0.68% | 7 | 61.53% (806/1310) |
| K4 | 886 | 67.17% | 0.68% | 7 | 67.63% (886/1310) |
| L | 902 | 68.39% | 0.45% | 4 | 68.70% (902/1313) |

Rawoutputs, labels, checkpoint hashes, traininglogs/config and perresponse terminationflags are in the percell ZIPs. Same reviewed training/evaluation paths as Qwen × MATH, using the frozen GSM8K data. Normal-termination accuracy has differing denominators. Registered two-seed decisions await Tier2.
