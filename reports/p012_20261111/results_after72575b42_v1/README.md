# Four new endpoints after72575b42

The accepted14 endpoints are excluded. This packet contains two matched9B-Base M512 arms and the remaining4B seed17 K8/K4 cells:20,000 raw outputs. All archived raw/label hashes and output counts are verified. Existing scoring and termination definitions are unchanged. Independent numerical review **passed** at `53a565dadcd648c50ac1ac2a3c08f5c69da123d0` under P012 section12.

| Model | Cell / arm | MATH5000 | MATH500 | Cap rate | Loops | Normal-termination correct / denominator |
|---|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B-Base | short | 70.14% | 70.60% | 4.44% | 122 | 3507/4778 |
| Qwen/Qwen3.5-9B-Base | long | 87.66% | 87.40% | 9.04% | 7 | 4378/4548 |
| Qwen/Qwen3.5-4B | K8 | 58.64% | 61.00% | 6.82% | 205 | 2932/4659 |
| Qwen/Qwen3.5-4B | K4 | 60.30% | 59.60% | 6.06% | 213 | 3015/4697 |

The Base pair reuses the exact9B M512 questions,128 updates,seed17 and unchanged rank/learning rate; see ../a6_2_tinker_lora_9b_base_pair_v1/. Long minus short is+17.52pp. Solution length and source/content differ together. Prediction18f64e2d preceded scoring.

Original4B seed17 is now complete: P60.06%,K858.64%,K460.30%,R46.56%,L65.60%. P/R/L were previously audited; K8/K4 are now accepted at `53a565dadcd648c50ac1ac2a3c08f5c69da123d0`. The original T prediction remains8bbf06a7. All four new endpoints are separate LoRA/Tinker results and do not enter main-grid H0-H3. No new bootstrap calculation is introduced.

The4B M512 construction and four subsequent4B/cross-teacher arms remain outside this packet. Their finite queue continues. Seed29 may proceed under accepted A4 without waiting for this numerical review.

Accepted audit: [53a565da](https://github.com/Townzc/2P1R_Reasoning_Post/blob/53a565dadcd648c50ac1ac2a3c08f5c69da123d0/audit/claude/20261113i/AUDIT_fce5e186_4_endpoints.md). The original20,000 outputs and registered labels remain unchanged. The current manifest updates result-annotation hashes; the original review manifest is retained.
