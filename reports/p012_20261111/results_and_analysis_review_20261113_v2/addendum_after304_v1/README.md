# Result addendum to the 304cc5ee review packet

This addendum freezes 35 endpoints completed after the original review request: all 32 Tier 2 main cells (seed 29), the two A6-2 9B M512 arms, and the original Tinker 9B L cell at seed 29. The original review manifest and analysis source are unchanged.

- Independently rescore 10% of each endpoint under the accepted registered rule. ENDPOINTS.json locates the raw and label members inside each evidence ZIP; MANIFEST.json binds every file. Archive member hashes were checked against the published results.
- All eight main settings now have seed 17 and seed 29. K4 was only prescribed for seed 17. Qwen seed 29 ran in townzc; Llama seed 29 ran in tangzhice, each on H100. Three Llama base MATH seed 29 cells exceeded 20% caps; their result tables include the first-box diagnostic.
- Qwen Instruct GSM K8 seed 29 uses the unchanged v2 infrastructure recovery after preemption at step 915. The original attempt and costs are preserved in qwen_tier2_k8_preemption_v1. No v1 checkpoint or evaluation was available.
- A6-2 9B short and long use the same 512 ordered questions, 1,024 presentations and 128 updates. Registered full-MATH accuracy is 3,610/5,000 (72.20%) and 4,557/5,000 (91.14%). Supervised tokens are 302,694 and 766,734. Solution source and content change along with length; both arms remain exploratory and excluded from H0–H3. Audit the frozen M512 data and all selected long answers as requested in the original packet.
- The new registered analysis script still awaits its first-use review. These published endpoint scores use the accepted scoring path. No bootstrap or new registered analysis has run on the real results.

No new execution permission is requested. Independent authorized model jobs continue. Built with Llama.
