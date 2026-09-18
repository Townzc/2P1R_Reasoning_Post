# Public benchmarks complete; development evaluation remains active

Snapshot: 2026-09-18T10:10:45.557122+00:00. All26,595 public outputs are scored and independently bound to their raw records. The complete finite phase and shutdown remain pending.

QDW-v0 underperforms DFT and TrimSFT on the predeclared primary MATH average@8 outcome. The observed GSM advantage does not support a broad superiority claim. QDW versus SFT remains inconclusive under paired question uncertainty on both benchmarks. All results use one training seed and128 committed updates per arm.

| Method | MATH average@8 | MATH pass@8 | GSM8K greedy |
|---|---:|---:|---:|
| Base | [32.100, 32.350]% | [78.20, 78.60]% | 37.53% |
| SFT | [41.050, 41.250]% | [74.40, 74.60]% | 80.97% |
| DFT | [59.300, 59.575]% | [79.20, 79.60]% | 79.30% |
| TrimSFT | [59.050, 59.300]% | [77.20, 77.40]% | 76.50% |
| QDW_v0 | [42.175, 42.375]% | [74.00, 74.20]% | 81.88% |

Table ranges bound unresolved judgments; they are not confidence intervals. Official500-question and1319-question denominators are retained. Each MATH method has4,000 completions.

| Primary paired MATH comparison | Difference bounds (pp) | Paired97.5% interval (pp) |
|---|---:|---:|
| QDW − DFT | [-17.400, -16.925] | [-20.08, -14.22] |
| QDW − TrimSFT | [-17.125, -16.675] | [-20.15, -13.65] |

The two primary intervals use a nominal Bonferroni family95% target across the predeclared QDW–DFT and QDW–Trim comparisons. QDW–SFT is secondary: difference bounds[+0.925,+1.325]pp, paired95% interval[−0.725,+2.975]pp. Resampling uses whole questions with all eight draws kept together;10,000 replicates, seed2026091814. Training-seed uncertainty is not measured.

GSM results are secondary/descriptive: QDW−DFT+2.58pp,97.5% interval[+0.30,+4.85]; QDW−Trim+5.38pp,[+2.88,+7.88]; QDW−SFT+0.91pp,95% interval[−0.99,+2.81]. They do not override the negative primary MATH result.

## Quality and scope limitations

Allfive methods have eight unresolved MATH outputs from the same official reference that normalizes to empty. Seven additional outputs remain unresolved after the frozen CPU scoring retry: Base2,DFT3,TrimSFT2. Both kinds stay in full-denominator bounds; no extra scoring or generation is requested. The ten method-by-benchmark summaries are not separate training replications.

MATH parse failures are Base296,SFT14,DFT1,TrimSFT0,QDW29 out of4,000. MATH length-cap fractions are11.80%,0.475%,3.825%,1.750%,0.950% respectively. QDW mean output length375.9 tokens versus DFT449.7 and Trim439.9 is descriptive; it does not identify the causal mechanism of the performance gap. The Base GSM result has637 parse failures and50.64% length caps, so Base-to-trained gains include interface adaptation.

The original GSM128 OOM/128 lost attempts and TrimSFT checkpoint-cache failure/32 lost training updates remain in resource records. Replayed TrimSFT GPU training is not bitwise identical. Its numerical limitation does not create another independent seed or justify replacing this arm. No failures, outputs, references or results were removed or selected away.

The observed result is about this fixed one-seed pilot, not state-of-the-art ranking or all implementations of these methods. CFT and other optional comparisons remain unrun. Complete the unchanged dev queue, reconcile all31,203 logical outputs and retained recovery state, shut down normally, then provide the complete Chinese report and long-term decision options.

See [the compact benchmark evidence](BENCHMARK_COMPLETE_DEV_PENDING.json), [the overnight authorization](OVERNIGHT_COMPLETION_AMENDMENT_20260918.md), and [the stage review](LONG_TERM_TRANSITION_20260918_ZH.md).
