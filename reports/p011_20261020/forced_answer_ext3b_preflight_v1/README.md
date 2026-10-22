# Two extension cells: identical forced-answer diagnostic, separate $20 cap

The human directly requested this new probe at 15:00 PT and then amended its total cap from $12 to $20. No training or other arm is authorized. All previous scientific work remains closed.

This is a route/metadata extension of the accepted seven-cell relaunch. The actual cap selector, fixed 10 IDs, generator, engine settings, first-balanced-box/native-stop adapter, frozen P1 scorer and paired-question bootstrap functions are unchanged. See DIFF_FROM_ACCEPTED_PATHS.patch and SOURCE_BINDING.json. Six new routing/budget/contrast-direction checks passed; no old tests or science rerun.

Only saved MATH500 outputs of 3024xE3 and 9072x1 are selected. Natural scores are reused. The original natural LARGE-minus-SMALL interval is sign-reversed algebraically; only two new forced extension contrasts and the two newly requested A6-minus-A7 contrasts are bootstrapped. Greedy retains one observation per question.

Budget: one H100, 4 CPU, 32 GiB, fresh shared-slot check including unknown/pending. New independent store and local/remote paths, one attempt, no automatic retry. Retain $1.50 for noncompute and 600 startup +60 platform grace. Estimate from all-seven 2680.32549s /9716 rows /160339564 prefill tokens, maximum of row/prefill scaling plus120s; affordable worker window must provide >=2x headroom, minimum3600, maximum10800s. The owner's latest cap is $20. Old $12 run costs remain historical and are neither erased nor relaunched.

Actual input construction is source-CR gated. Exact new manifest/roster/context/model export hashes require actual A2 before any upload or GPU. Final collection after CLI terminal and whole-app STOPPED0, decode only new64 tokens, score complete cells only. Independent actual A3 requested after results; report is posthoc/diagnostic with single-seed and symbolic/binary-access limits.

The model-file inventories are copied from saved evaluated-export receipts. No multi-GB model/state binary was rehashed locally or copied; actual existing remote checkpoint files are checked by the unchanged generation worker.
