# P012 Amendment 4: one combined Tinker / Modal LoRA bridge review

Authority: owner-approved `claude/audit` **77a2520e**, §§2–3 and §5. All three authorized T-smokes are complete. Formal Tinker training, pre-training measurements and the Modal bridge have not run; they await this review. Smoke outputs remain unscored.

## Review scope

| Path | Implementation | Evidence |
|---|---|---|
| Tinker training, forward-only NLL, generation | `experiments/p012/tinker_lora.py` | Three real 20-step / 20-question smokes; full raw tokens, losses, masks, stop reasons and usage |
| Modal bridge configuration / training | `bridge_config.py`, `modal_bridge.py` | Five actual frozen configs accepted; 15 changed-config cases rejected; CPU import / compilation passed |
| Unmerged bridge evaluation | `bridge_evaluation.py`, `modal_bridge_evaluation.py` | Existing generation logic with vLLM `LoRARequest`; adapter inventory/hash validation; CPU import / compilation passed |
| Descriptive termination metrics | `termination_summary.py` | Same frozen token repetition rule and normal-termination definition already used for both full-parameter settings |

The bridge has not had a GPU execution. The Tinker `smoke` path has exercised training, optimizer updates, checkpoint-to-sampler conversion and generation. Formal forward-only NLL and full-size endpoints have not been called. `SOURCE_INVENTORY.json` binds the candidate files; the smoke request binds the exact executed Tinker source at `4b55fa44`.

## Actual smoke evidence

| Model | Learning rate | Training input tokens | Generated tokens | Stop / length | Token-cost upper estimate |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-4B | 0.0004905250962784578 | 65,528 | 5,010 | 20 / 0 | $0.053905 |
| Qwen3.5-9B | 0.00047297908091376354 | 65,528 | 4,488 | 20 / 0 | $0.100012 |
| Qwen3.5-9B-Base | 0.00047297908091376354 | 65,528 | 8,678 | 19 / 1 | $0.103394 |

Total **$0.257311** from recorded tokens and frozen unit rates. This includes full prefill pricing without cache discounts, excludes storage, and is not a provider invoice. The prospective buffered maximum was **$0.870249**, including 20 × 4,096 generated tokens per model and storage reserves, below the authorized $5 smoke cap.

Each `*_smoke_evidence.zip` contains the request, package versions, server model information, actual rendered samples and token-level loss masks, row order, every step's loss/LR, sampler handle, 20 original generations, stop flags, usage and completion hashes. `SMOKE_ARTIFACT_MANIFEST.json` gives archive hashes. `SMOKE_RESULTS.json` records consistency checks and totals. No answer labels or accuracy were computed.

## Tinker recipe and rendering

- Official cookbook pinned to **8486b8df2fc32e9713cf96dd5f75d43c7ef70a17**; installed packages are in `requirements-tinker.lock`. Learning rates are the actual `get_lr(model, is_lora=True)` returns, shared by all cells of each model.
- Rank 32; `train_mlp`, `train_attn`, `train_unembed` all true. Batch 8, Adam (0.9, 0.999, 1e-8), weight decay 0, gradient clipping 1, no warmup, full-grid cosine schedule. Smoke uses the first 20 updates of L's 128-update schedule.
- Frozen C6 bytes are checked before reading. P/K8/K4/R use 1,024 updates; L uses 128. The data order uses the pinned Accelerate seed-plus-epoch rule. `SAMPLER_PARITY.json` records **48 identical epoch permutations**, across both seeds and all five cells, against the actual Accelerate 1.2.1 sampler class.
- `qwen3_5_disable_thinking` is used for every model, including Base. All 512 L rows per model passed token-level generation parity with HF `apply_chat_template(enable_thinking=False)`, supervised rendering parity through `<|im_end|>`, prompt-mask checks and the 4,096-token limit. HF's trailing newline after the final EOS is excluded. The empty thinking prefill is prompt-masked; assistant response and EOS are supervised.
- Loss weights are divided by the total assistant/EOS token count across the whole batch of eight, matching the full-parameter batch token mean. NLL retains per-solution sums, target token counts and character counts and uses the existing C7 aggregator.
- Generation keeps OMI-2 prompts, greedy temperature 0, 4,096 generated / 8,192 context limits and renderer stop IDs. Held-out pass@8 uses 500 questions × 8 draws at temperature 0.7. All original prompt/output token IDs and server stop reasons are retained. Existing `scoring.py` is invoked separately.
- `TOKENIZER_ASSETS.json` contains frozen HF revisions and every downloaded tokenizer/config file hash. The server reports model name, tokenizer ID and rank, but no immutable server weight revision; no equivalence between server weights and a particular HF weight SHA is asserted.

## Modal LoRA bridge

Qwen2.5-1.5B base × MATH, seed 17, five C6 cells. Every full-parameter field is retained except the declared LoRA changes: rank 32, LR **0.0005103340076039325**, alpha 64 (the pinned LLaMA-Factory default `2 × rank`), dropout 0.

The explicit target list is `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj,lm_head`. LLaMA-Factory's `all` shorthand excludes the output head, so the list includes it explicitly to implement all linear layers. Alpha is a Modal configuration default; Tinker does not expose an alpha parameter, so its value is not assumed identical.

Adapters are **not merged**: Qwen ties the input embedding and output weights, and merging an adapted head could alter the embedding. Evaluation loads the pinned base plus the unmerged adapter with vLLM 0.11 `LoRARequest`, then uses the same prompt, decoding and scoring paths. Adapter configuration, every checkpoint file, and its inventory are hash-checked before loading. The pinned vLLM source handles output-head LoRA via the logits processor; actual GPU validation follows acceptance.

`BRIDGE_CONFIG_CHECKS.json` contains the five full configurations and checks. All jobs use H100!, preserving the actual GPU type instead of allowing Modal's automatic H200 upgrade. Production will use detached calls, immutable run directories and the current actual-balance admission rule.

## Prediction freeze and execution after acceptance

The two full-parameter MATH settings and all Qwen C7 endpoints were pushed at **7c34f3d6**:

- [Base × MATH](../tier1_qwen_base_math_s17_v1/README.md)
- [Instruct × MATH](../tier1_qwen_instruct_math_s17_v1/README.md)
- [Qwen C7](../c7_qwen_complete_v1/README.md)

Please review both new paths together and include the §5 prediction file in the same review handoff. Tinker pre-training measurements have not run because they use the new formal path. Predictions can be frozen from the available main-grid results; if they depend on T pre-training measurements, freeze the conditional rule and thresholds now, before those measurements are available. Do not use the unscored smoke as an accuracy input.

After acceptance: run the registered T pre-training measurements, then T-MATH; record the prediction commit before scoring any trained T output. Training and generation may precede that freeze, but their outputs remain unscored until it exists. The bridge follows the now-complete two Qwen MATH settings. Tinker and bridge results stay in separate tracks; no pooling with the full-parameter grid. T-MATH $230, T-GSM $105, smoke $5; at least $400 of the initial Tinker credit is reserved.

Official implementation references: [Tinker cookbook at the pinned commit](https://github.com/thinking-machines-lab/tinker-cookbook/tree/8486b8df2fc32e9713cf96dd5f75d43c7ef70a17), [Tinker model pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/), [Modal GPU type pinning](https://modal.com/docs/guide/gpu).
