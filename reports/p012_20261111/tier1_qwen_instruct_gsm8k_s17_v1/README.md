# Tier 1 Qwen instruct × GSM8K, seed 17

| Cell | Correct / 1319 | Accuracy | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 920 | 69.75% | 0.30% | 4 | 69.96% (920/1315) |
| K8 | 882 | 66.87% | 0.83% | 11 | 67.43% (882/1308) |
| R | 770 | 58.38% | 0.08% | 0 | 58.42% (770/1318) |
| K4 | 893 | 67.70% | 1.14% | 11 | 68.48% (893/1304) |
| L | 865 | 65.58% | 0.53% | 4 | 65.93% (865/1312) |

Rawoutputs, labels, checkpoint hashes, traininglogs/config and perresponse terminationflags are in the percell ZIPs. Same reviewed training/evaluation paths as Qwen × MATH, using the frozen GSM8K data. Normal-termination accuracy has differing denominators. Registered two-seed decisions await Tier2.
