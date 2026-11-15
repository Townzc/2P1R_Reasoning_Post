# Reduced Tinker GSM8K: new endpoints after b0d31d3a

The owner-reduced queue is complete. This packet requests independent review of 7 new endpoints / 9233 outputs. The five accepted training endpoints are reference-only. All runs use Tinker LoRA, seed17, unchanged frozen data and scoring; exploratory outsideH0–H3.

| Endpoint | Correct | Accuracy | Capped | Loops | Normal correct/n |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-4B K8 | 1129/1319 | 85.595% | 0.45% | 4 | 1129/1313 |
| Qwen/Qwen3.5-4B P | 1133/1319 | 85.898% | 0.23% | 3 | 1133/1316 |
| Qwen/Qwen3.5-4B R | 955/1319 | 72.403% | 0.23% | 1 | 955/1316 |
| Qwen/Qwen3.5-9B-Base K8 | 1183/1319 | 89.689% | 0.30% | 3 | 1183/1315 |
| Qwen/Qwen3.5-9B-Base R | 1109/1319 | 84.079% | 0.08% | 1 | 1109/1318 |
| Qwen/Qwen3.5-9B K8 | 1190/1319 | 90.220% | 0.00% | 0 | 1190/1319 |
| Qwen/Qwen3.5-9B R | 1104/1319 | 83.700% | 0.00% | 0 | 1104/1319 |

Please verify the new raw outputs, training/input/sampler bindings and frozen G2–G3 predictions from8bbf06a7. G1 is not judged because K4 was cancelled. POLICY preserves the decision time,5/27 exposure and owner reason; K8_GATES records the prospective per-model P−R>=3pp decision before launch. Cancellation and unused reservations are reconciled in COMPLETION and BUDGET_SNAPSHOT.

For4B use4-shot1216/1319 as the training-before reference. The0-shot baseline had543/1319 answer-only outputs; holdout pass1/pass8 are descriptive only and are not capability measures. Labels remain the existing Codex labels under the accepted percentage-normalization rule. No re-score or bootstrap was introduced.

The completion receipt preserves the legacy pre-A8 accounting fields. BUDGET_SNAPSHOT.json uses the canonical review_204ad0ae helper and adds the reserved/actual A8 T arms exactly once; it is the current combined total.
