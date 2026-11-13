# Corrected Tinker LoRA pass@8 endpoints

Each endpoint uses the original500frozenquestions, eight separatelyseeded draws, T0.7 and4096/8192. Originalv1endpoints are retained butsuperseded.

| Model | pass@1 | pass@8 | Unique seeds | Questions with ≥7 distinct draws |
|---|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B-Base | 65.125% | 93.00% | 4000 | 99.40% |

First-run admission requires4,000unique seeds and>=80%questions with>=7distinctoutputs. Rawoutputs, checks, usage and labels are in the permodel evidence ZIPs. Only completedv2endpoints appear in this table.
