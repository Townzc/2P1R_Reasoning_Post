# A8 T group: four complete MATH endpoints

All four original Qwen3.5-4B LoRA rank 32, seed 17 endpoints completed, with 20,000 raw outputs. Exploratory, outside H0–H3. Source/data accepted b24f787a; A release 204ad0ae; frozen predictions 5e1f9128.

| Cell | P,K,E | Updates | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| T01 | 2048,2,2 | 1024 | 3001/5000 | 60.02% | 59.97% | 5.20% | 167 | 3001/4740 |
| T02 | 1024,2,4 | 1024 | 2774/5000 | 55.48% | 55.36% | 2.54% | 74 | 2774/4873 |
| T03 | 4096,1,1 | 512 | 3066/5000 | 61.32% | 66.94% | 9.18% | 343 | 3066/4541 |
| T04 | 4096,2,2 | 2048 | 2917/5000 | 58.34% | 58.13% | 5.48% | 206 | 2917/4726 |

ENDPOINTS.json binds all training steps, complete epoch permutations, cosine learning rates, model/rank, frozen inputs, sampler/state, generation settings, raw outputs and unchanged labels. Timestamped predictions bind the original raw hashes before scoring. T02 used the exact reviewed patch after C05 completion; e84611a7 already accepted that timing.

Please independently score the four endpoints and apply frozen A8 §5 and SL-8: MATH hit threshold 2.5pp, group hit rate and mean residual, K > 1 comparison with both fixed alternatives, and E = 2 versus E != 2 subsets. A/B/C and reduced GSM results are already audited and are reference-only. No refit, new bootstrap or label change was introduced. Retain all A8 checkpoints. No additional experiment is authorized.

The T controller completed normally at 2026-11-15 07:38:50 PST. All eight original calls (four training, four evaluation) completed with no duplicate launch or stop event. COMPLETION_AND_CHECKS.json records 72 verified evidence/input bindings and 4,608 training updates. Both Modal workspaces have zero active applications.

A8 T accounting is $23.758422 / $40. Combined Tinker accounting plus retained reserves is $398.202617 / $485, including the existing $30 storage reserve once. API readback reports 135 checkpoints, 91928265102 bytes, and $0.1/GB/month. All checkpoints and TTLs remain retained.
