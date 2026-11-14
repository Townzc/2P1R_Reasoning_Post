# Six completed A6-2 follow-up arms

Exploratory LoRA/Tinker endpoints, excluded from H0-H3. Same ordered4B M512 questions in the4B and new9B pairs; the Base pair reuses the original9B M512. Predictions18f64e2d and46694f51 were recorded before their respective output scoring. Two Base endpoints were accepted by 53a565da. The four4B/cross-teacher endpoints and4B M512 construction are now accepted by6af18b72. All six arms are independently accepted.

| Model | Arm | MATH5000 | Cap rate | Loops | Normal-termination correct / denominator |
|---|---|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B-Base | short | 70.14% | 4.44% | 122 | 3507/4778 |
| Qwen/Qwen3.5-9B-Base | long | 87.66% | 9.04% | 7 | 4378/4548 |
| Qwen/Qwen3.5-4B | short | 65.40% | 7.64% | 223 | 3270/4618 |
| Qwen/Qwen3.5-4B | long | 87.56% | 6.78% | 10 | 4378/4661 |
| Qwen/Qwen3.5-9B | short_4b_m512 | 70.06% | 5.20% | 137 | 3503/4740 |
| Qwen/Qwen3.5-9B | cross_long_4b_m512 | 90.14% | 5.32% | 4 | 4506/4734 |

Current review scope: [five-endpoint packet](../results_after53a565da_v1/README.md) includes these four new arms plus original4B L seed29. The two Base endpoints are excluded from repeat review. The original aggregate manifest is preserved as ENDPOINTS_original_69a273b8.json.

Review6af18b72 completed the current five-endpoint packet, including the four new arms in this aggregate. No endpoint in this aggregate remains pending.
