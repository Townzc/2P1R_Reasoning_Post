# Registered two-seed main-grid analysis

A-1 through A-6 from accepted review169754c4 are implemented. Thirteen synthetic tests passed; the three identity swaps fail as required. The first real-data run completed successfully at3a2984e3. All72 main cells and12 paired baselines are included. Results await the independent numerical check promised in review section7.

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

The code review is complete; this request concerns the first real output and its bindings. Independently recompute headline points and paired intervals as promised in169754c4 section7. Also audit the35 endpoints in ../results_and_analysis_review_20261113_v2/addendum_after304_v1/, which were explicitly outside169754c4. Three later endpoints are linked below; previously accepted38 endpoints need no repeat review.

- Instruct bridgeL: ../instruct_bridge_l_results_v1/
- A6-3 9B L64: ../a6_3_tinker_lora_9b_math_l64_s17_v1/
- Original Tinker9B-Base L seed29: ../tinker_lora_qwen3_5_9b_base_math_l_s29_v1/

The Tinker/A6/bridge endpoints remain separate from this full-finetuning analysis. Built with Llama.
