# P012 completed-result audit, 2026-11-13

This packet freezes the completed results at `f26862b2`. File identities are in `MANIFEST.json`; raw outputs, tokens, labels and training evidence are in the linked ZIPs. It requests the independent result audit in P012 section12, not another approval for unchanged execution paths. Active Llama and Tinker work continues.

Review priorities:

1. **T4 closure:** independently verify all three v2 seed/diversity checks, then audit the corrected pass@1/pass@8 calculations against the original raw outputs. All three v1 metrics are superseded; their raw evidence remains available in the historical packet. New v2 pass@1/pass@8: Base65.125/93.0%, 4B79.325/95.2%, 9B89.725/95.4%.
2. **Bridge B-3 disposition:** L has4999/5000 length caps,4203 loops and one normal termination; accuracy42.18%. Parameter count and adapter loading passed. P/K8/R/K4 remain unstarted and stopped. Please audit the complete result and specify the next protocol, if any; no LR/output-head/backend change is assumed authorized.
3. **A5 and GSM:** select10% of the raw outputs independently and rescore under the accepted exact OR math-verify rule. Check termination/loop counts and their denominators. A5 remains exploratory and excluded from H0-H3. Four Qwen main settings are complete at seed17; registered conclusions await seed29.
4. **T LoRA L cells:** audit original outputs, baseline comparisons on the same MATH-500 subset, prediction commit8bbf06a7, and separate-track labels. Full MATH5000:4B65.60%,9B70.92%,Base70.40%.
5. **Llama NLL:** recompute the four per-token and per-character aggregates from the stored1000 per-solution records. No GPU remeasurement is requested.

The original Qwen MATH main-grid results were independently reviewed at8bbf06a7 and are reference evidence, not a request to repeat that completed audit. C7 Qwen result evidence is available at `../c7_qwen_complete_v1/`; please identify any existing result-audit coverage when returning the review.

| Completed block | Evidence |
|---|---|
| a5_baseline0_results_v1 | [README](../a5_baseline0_results_v1/README.md) |
| a5_2_qwen_base_math_s17_v1 | [README](../a5_2_qwen_base_math_s17_v1/README.md) |
| a5_2_qwen_instruct_math_s17_v1 | [README](../a5_2_qwen_instruct_math_s17_v1/README.md) |
| a5_3_qwen_base_math_s17_v1 | [README](../a5_3_qwen_base_math_s17_v1/README.md) |
| a5_3_qwen_instruct_math_s17_v1 | [README](../a5_3_qwen_instruct_math_s17_v1/README.md) |
| tier1_qwen_base_gsm8k_s17_v1 | [README](../tier1_qwen_base_gsm8k_s17_v1/README.md) |
| tier1_qwen_instruct_gsm8k_s17_v1 | [README](../tier1_qwen_instruct_gsm8k_s17_v1/README.md) |
| tinker_lora_pass8_v2 | [README](../tinker_lora_pass8_v2/README.md) |
| tinker_lora_qwen3_5_4b_math_l_s17_v1 | [README](../tinker_lora_qwen3_5_4b_math_l_s17_v1/README.md) |
| tinker_lora_qwen3_5_9b_math_l_s17_v1 | [README](../tinker_lora_qwen3_5_9b_math_l_s17_v1/README.md) |
| tinker_lora_qwen3_5_9b_base_math_l_s17_v1 | [README](../tinker_lora_qwen3_5_9b_base_math_l_s17_v1/README.md) |
| modal_lora_bridge_l_s17_v1 | [README](../modal_lora_bridge_l_s17_v1/README.md) |
| c7_llama_nll_v1 | [README](../c7_llama_nll_v1/README.md) |

Implementation references: accepted sampling review `a56115d6`, track/bridge review and frozen prediction `8bbf06a7`; owner-approved A4 at77a2520e and A5 in8bbf06a7. New calls not represented by this immutable manifest belong in a later result packet. Built with Llama.

Later completed batches: [result addendum](ADDENDUM.md), separately frozen by `ADDENDUM_MANIFEST.json`. The original manifest remains unchanged.
