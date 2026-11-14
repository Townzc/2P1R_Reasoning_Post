# Registered two-seed main-grid analysis

A-1 through A-6 from accepted review169754c4 are implemented. Thirteen synthetic tests passed; the three identity swaps fail as required. The first real-data run completed successfully at3a2984e3. All72 main cells and12 paired baselines are included. Independent numerical audit **passed** at `46694f515ff2c6d1f78931761f3f8e47dd0de2cb`. The auditor independently reproduced all headline values and bootstrap hashes. The original numerical artifact and execution receipt are retained; the current JSON adds audit/reporting metadata only.

| Setting | P-L, pp [95% CI] | L-R, pp [95% CI] | P-K8, pp [95% CI] | P-L noticeable |
|---|---:|---:|---:|---|
| llama_base_gsm8k | +15.13 [+13.23, +17.13] | +1.48 [-0.23, +3.15] | +5.99 [+4.09, +7.85] | True |
| llama_base_math | +2.25 [+1.68, +2.82] | +0.41 [-0.11, +0.92] | +0.10 [-0.51, +0.71] | False |
| llama_instruct_gsm8k | +4.47 [+2.35, +6.56] | +10.50 [+8.49, +12.59] | +6.56 [+4.44, +8.68] | True |
| llama_instruct_math | +1.85 [+0.94, +2.76] | +7.24 [+6.32, +8.14] | +2.49 [+1.58, +3.40] | False |
| qwen_base_gsm8k | +1.02 [-0.87, +2.92] | +8.91 [+6.94, +10.88] | +4.02 [+2.01, +6.10] | False |
| qwen_base_math | -0.98 [-1.96, +0.01] | +9.89 [+8.91, +10.88] | +1.48 [+0.51, +2.44] | False |
| qwen_instruct_gsm8k | +3.68 [+1.82, +5.57] | +7.35 [+5.27, +9.48] | +3.56 [+1.67, +5.50] | True |
| qwen_instruct_math | -0.03 [-1.01, +0.94] | +9.19 [+8.19, +10.20] | +1.10 [+0.15, +2.07] | False |

L-R is derived from the registered PR-data contrasts, not independently preregistered. Noticeable follows the mean/CI/sign rule frozen at169754c4. These intervals describe question sampling conditional on two observed training seeds. All per-seed estimates, intervals, threshold flags, P-R, K8-R, paired SFT comparisons, baseline accuracies and termination diagnostics remain in RESULTS.json.

| H1 capability | Spearman rho vs P-L |
|---|---:|
| pass_at_1 | -0.357143 |
| pass_at_8 | -0.357143 |
| nll_per_token (negative) | -0.571429 |
| nll_per_char (negative) | +0.047619 |

The character-normalized NLL association is the primary cross-family interpretation. Both Llama base settings have conversation nontermination; Llama Instruct GSM8K has answer-only zero-shot prompting. Their pass@k values remain visible with the required failure notes. Four-shot remains the primary SFT baseline; zero-shot is also paired for each Instruct setting. G0 Li measurements are read-only references.

## Reproduction and independent audit

INPUT_MANIFEST.json binds every local input by SHA256, including the training manifest, checkpoint inventory, generation manifest, raw responses, registered labels, termination summary and required first-box diagnostic. SOURCE_LOCATIONS.json maps all580 bound paths to public files or exact members of public ZIPs; restore those relative paths before running the command in RUN_RECEIPT.json. Check archive and member hashes. Install the pinned analysis/requirements-p012.txt. No API key or model call is needed.

The first real analysis, its bindings, and the35+3 additional endpoints below passed audit46694f51. The previously accepted38 endpoints remain covered by169754c4. These are separate accepted batches.

- Instruct bridgeL: ../instruct_bridge_l_results_v1/
- A6-3 9B L64: ../a6_3_tinker_lora_9b_math_l64_s17_v1/
- Original Tinker9B-Base L seed29: ../tinker_lora_qwen3_5_9b_base_math_l_s29_v1/

The Tinker/A6/bridge endpoints remain separate from this full-finetuning analysis. Built with Llama.

## Paired SFT contrasts (two-seed means)

Values below are read from the unchanged registered output. Each interval conditions on the two observed training seeds.

| Setting | Δ_SFT vs 4-shot, pp [95% CI] | Δ_SFT vs 0-shot, pp [95% CI] | Baseline interpretation |
|---|---:|---:|---|
| llama_base_gsm8k — 相对退化基线 | +30.86 [+28.70, +33.06] | — | 相对退化基线（不终止）；不能解释为 SFT 收益大小 |
| llama_base_math — 相对退化基线 | +5.50 [+4.00, +7.10] | — | 相对退化基线（不终止）；不能解释为 SFT 收益大小 |
| llama_instruct_gsm8k | +12.85 [+10.24, +15.50] | +46.89 [+44.35, +49.43] | Paired protocol-specific baseline |
| llama_instruct_math | +15.20 [+11.50, +19.00] | +10.80 [+6.60, +14.80] | Paired protocol-specific baseline |
| qwen_base_gsm8k | +4.51 [+2.01, +6.94] | — | Paired protocol-specific baseline |
| qwen_base_math | +15.10 [+11.20, +19.10] | — | Paired protocol-specific baseline |
| qwen_instruct_gsm8k | +10.96 [+8.45, +13.50] | +11.41 [+8.72, +14.22] | Paired protocol-specific baseline |
| qwen_instruct_math | +5.20 [+1.10, +9.40] | -12.40 [-16.50, -8.30] | Both baselines must be shown together |

`RUN_RECEIPT.json` and `ARTIFACT_MANIFEST_original_313f2dd5.json` describe the original run and publication. `AUDIT_ANNOTATION.json` links the original and annotated artifacts; no statistics or labels were recomputed.
