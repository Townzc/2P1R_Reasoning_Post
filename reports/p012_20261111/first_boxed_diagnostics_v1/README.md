# A6 first-boxed diagnostic for cap rates above20percent

Registered last-boxed scores remain unchanged. The additional column uses the first balanced box and the same math/numeric scorer. No model was called. Raw output hashes bind each diagnostic to its original endpoint.

| Endpoint | Registered last box | First box (diagnostic) | Cap rate |
|---|---:|---:|---:|
| a5_qwen_base_math_l128_s17_greedy_20261113_v1 | 42.28% | 45.80% | 90.82% |
| a5_qwen_base_math_l256_s17_greedy_20261113_v1 | 34.68% | 43.42% | 99.38% |
| a5_qwen_base_math_l64_s17_greedy_20261113_v1 | 38.34% | 45.08% | 81.94% |
| modal_lora_bridge_qwen_base_math_l_s17_greedy_20261113_v1 | 42.18% | 43.56% | 99.98% |
| llama_base_math_k4_s17_greedy_20261113_v1 | 6.16% | 6.16% | 23.20% |
| llama_base_math_k8_s17_greedy_20261113_v1 | 6.72% | 6.72% | 23.28% |
| llama_base_math_l_s17_greedy_20261113_v1 | 4.46% | 4.48% | 32.12% |
| llama_base_math_p_s17_greedy_20261113_v1 | 6.40% | 6.40% | 25.20% |
| c7_llama_base_gsm8k_baseline4_20261113_v1 | 0.30% | 4.47% | 100.00% |
| c7_llama_base_math_baseline4_20261113_v1 | 0.00% | 1.60% | 99.80% |

The four heavily capped Qwen endpoints differ from the independent audit by at most0.04pp under this existing scorer; the registered scores are not replaced. Llama baselines remain visibly degenerate even where the first-box diagnostic is higher.
