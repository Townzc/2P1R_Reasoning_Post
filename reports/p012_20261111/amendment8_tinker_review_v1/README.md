# A8 conditional T-group source and MATH data review

Authority: 5e1f9128180f1dcd222fc1e33fe691ec01030f38. This package prepares four exploratory Qwen3.5-4B × MATH LoRA arms. Formal execution requires both accepted source review and Claude’s A-group verdict of at least “partially holds”, followed by a current budget check.

The sole runtime-source diff adds CELLS["A8_P1024_K2_E4"] = (1024,2,4) to training_config.py. The other three tuples already passed ff567d06. The candidate is not applied: the live file remains61163c22 while A runs. No training, sampling, scoring, bootstrap, transport or checkpoint code changes.

| Arm | P | K | E | Updates | Buffered training + greedy USD |
|---|---:|---:|---:|---:|---:|
| T01 | 2048 | 2 | 2 | 1024 | 8.0984 |
| T02 | 1024 | 2 | 4 | 1024 | 8.0492 |
| T03 | 4096 | 1 | 1 | 512 | 6.4890 |
| T04 | 4096 | 2 | 2 | 2048 | 11.3535 |

Total forecast: $33.9901, within the A8 sublimit $40. No A8 T funds have been admitted. Combined cap remains $485; the existing $30 storage reserve is counted once. A fresh combined ledger and API storage check precede execution.

All four datasets use exact frozen C6 rows: training4096 prefix P, then first K solutions. Existing L/K4/K8/P/R files reconstruct byte-for-byte. The complete source rows, parent order, candidate files and frozen5000-question greedy evaluation input are in candidate_datasets.zip. CPU_CHECKS and CANDIDATE_MANIFEST bind every file hash, dose and request.

CPU verification rendered all8192 distinct training rows with the pinned4B tokenizer and unchanged renderer, checking masking, EOS, generation parity and full lengths <=4096. All5000 evaluation prompts have identical frozen-tokenizer prefixes and fit4096 output +8192 context. Every old configuration case is unchanged. All four unadmitted requests are rejected before a model client is constructed. Training rank32, seed17, LR0.0004905250962784578, batch8, own-step cosine and epoch shuffle are inherited unchanged.

Training forecasts use exact rendered input tokens × frozen training rate, plus25% and$0.10. Each greedy forecast uses the largest measured4B main-grid MATH token cost ×1.5. The measured usage receipts are included. Request templates remain admitted=false and accepted_review_commit=null. Evaluation sampler paths and final training evidence are filled only after approved training; no model calls were made.

Review requested: accept the one-tuple diff and four MATH input bindings. This review alone does not release T; A-group outcome remains a separate gate. Before each result is scored, record UTC, raw SHA256 and authority5e1f9128. Results remain exploratory outside H0–H3.
