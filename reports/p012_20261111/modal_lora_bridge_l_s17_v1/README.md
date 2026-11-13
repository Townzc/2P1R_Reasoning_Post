# Modal LoRA bridge L: B-3 stop

Full MATH test: 2109/5000 = **42.18%**. Length caps: **4999/5000 = 99.98%**, exceeding the accepted 25% B-3 threshold. 4203 responses contain token loops. Only 1 response terminates normally (1 correct); the normal-only percentage has a denominator of one.

P, K8, R and K4 remain unstarted and stopped under review `8bbf06a7` section 4 B-3. Adapter loading and the 36,929,536-parameter check passed. This failure establishes a termination problem for this bridge configuration; its cause has not been isolated. No learning-rate, output-head, backend or recipe change was made.

All original full-test outputs, labels, termination flags, training logs and checkpoint hashes are in `evidence.zip`. Prediction commit `8bbf06a7` was recorded in the published generation request before scoring. Full evaluation function time: 2924.870642302 seconds. Main full-finetuning and Tinker LoRA experiments continue under their existing authorizations.
