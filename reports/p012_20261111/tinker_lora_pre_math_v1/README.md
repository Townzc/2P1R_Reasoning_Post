# Tinker LoRA: original MATH pretraining measurements

| Model | 4-shot MATH-500 | 0-shot MATH-500 | Teacher NLL/token | Teacher NLL/character |
|---|---:|---:|---:|---:|
| 4B | 88.40% | 81.80% | 0.647223 | 0.258334 |
| 9B | 91.80% | 91.20% | 0.625836 | 0.249797 |
| 9B-Base | 71.40% | Not scheduled | 0.452764 | 0.180717 |

These original greedy baselines and NLL measurements remain valid. All three original pass@8 endpoints are superseded after the correlated-sampling diagnosis; their metrics are excluded from current tables, while their raw outputs and original score files are preserved in the ZIPs.

The accepted repair is complete: [all three v2 endpoints](../tinker_lora_pass8_v2/README.md) passed the unique-seed and diversity checks before scoring. The 9B-Base training pause is lifted. Formal Tinker training continues under the accepted measured-token budgets. This track is reported separately from Modal full finetuning.
