# New results after accepted46694f51 audit

Fourteen new endpoints,70,000 raw outputs. All original raw/label archive members match the recorded hashes. This packet requests numerical verification under P012 section12; no new training, scoring or statistical method is introduced. The accepted main-grid analysis and prior38 endpoints require no repeat review.

| Model / track | Cell | Seed | MATH5000 | Cap rate | Loops | Normal-termination correct / denominator |
|---|---|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-1.5B-Instruct / modal_lora_bridge | P | 17 | 41.84% | 10.84% | 428 | 2092/4458 |
| Qwen/Qwen2.5-1.5B-Instruct / modal_lora_bridge | K8 | 17 | 41.64% | 11.84% | 455 | 2082/4408 |
| Qwen/Qwen2.5-1.5B-Instruct / modal_lora_bridge | R | 17 | 32.68% | 2.10% | 129 | 1634/4895 |
| Qwen/Qwen2.5-1.5B-Instruct / modal_lora_bridge | K4 | 17 | 41.14% | 11.02% | 448 | 2057/4449 |
| Qwen/Qwen3.5-9B / tinker_lora | P | 29 | 68.30% | 4.12% | 135 | 3415/4794 |
| Qwen/Qwen3.5-9B / tinker_lora | K8 | 29 | 65.82% | 4.52% | 119 | 3291/4774 |
| Qwen/Qwen3.5-9B / tinker_lora | R | 29 | 57.02% | 1.72% | 38 | 2851/4914 |
| Qwen/Qwen3.5-9B-Base / tinker_lora | P | 29 | 67.50% | 4.32% | 130 | 3375/4784 |
| Qwen/Qwen3.5-9B-Base / tinker_lora | K8 | 29 | 64.60% | 4.22% | 100 | 3230/4789 |
| Qwen/Qwen3.5-9B-Base / tinker_lora | R | 29 | 58.32% | 3.10% | 64 | 2916/4845 |
| Qwen/Qwen3.5-4B / tinker_lora | P | 17 | 60.06% | 5.80% | 190 | 3003/4710 |
| Qwen/Qwen3.5-4B / tinker_lora | R | 17 | 46.56% | 1.44% | 36 | 2328/4928 |
| Qwen/Qwen3.5-9B / A6-3 | E4 | 17 | 62.38% | 2.48% | 68 | 3119/4876 |
| Qwen/Qwen3.5-9B / A6-3 | E8 | 17 | 59.16% | 1.28% | 29 | 2958/4936 |

The four Instruct bridge cells follow the accepted L gate; L itself was accepted46694f51. Original Tinker training/output predictions remain8bbf06a7, and A6-3 E4/E8 retain18f64e2d. All predictions were recorded before scoring. These separate LoRA tracks do not enter the full-finetuning H0-H3 analysis. No confidence interval was newly computed for this packet.

The newly approved cross-teacher pair is frozen at46694f51 in ../review_46694f51/. Its4B M512 construction and the Base pair are now running under ../a6_2_base_and_4b_admission_v1/. Those future endpoints are outside this review packet. Review does not pause authorized execution.

The registered analysis annotations are metadata only: ../registered_analysis_169754c4_v1/AUDIT_ANNOTATION.json proves unchanged numerical settings and links the original output hash. Every Llama base SFT table is labeled relative to a degenerate baseline; Qwen Instruct MATH shows both4-shot and0-shot deltas.
