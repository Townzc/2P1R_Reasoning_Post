# C7 review packet

Scope: the one C7 review requested in accepted `e10a4bf5` section 5. Code source: `af9344df`. No C7 model calls have run. R1 and the authorized L cost probe run independently.

## Frozen endpoints

For each of four initial models and two tasks:

| Endpoint | Questions / solutions | Conditioning | Decoding / measurement |
|---|---:|---|---|
| Holdout capability | 500 questions | Base: 4 frozen demonstrations; Instruct: 0 | 8 draws, T=0.7, top-p=1; pass@1=c/8, pass@8=1[c>0], averaged over questions |
| Primary pre-SFT test baseline | MATH-500 / GSM8K 1,319 | 4 frozen demonstrations for both base and Instruct | Greedy; OMI prompt, training template and scorer |
| Secondary pre-SFT test baseline | Same test questions | 0-shot for both | Same greedy decoding and scoring |
| Teacher NLL | 1,000 frozen solutions, two per held-out question | Zero-shot OMI training prefix for both initializations | Teacher forcing, response and template terminator only; aggregate total NLL / total target tokens |

Generation uses the reviewed `evaluation.py` and `modal_g0.py`, grading uses `scoring.py`. Output limit 4,096; context 8,192. Every endpoint is submitted as one complete batch. The primary Delta_SFT comparison uses the greedy MATH-500 subset / GSM8K endpoint. No sampled Delta_SFT is computed from greedy-only baseline outputs.

Four-shot demonstrations remain conversation turns; they are not embedded into an extra user message. No new demonstrations, train/test split or teacher solutions are selected. The eight complete conversation files are in `frozen_conversations.zip`; every file hash and all 24 model/task/endpoint configurations are in `MANIFEST.json`. NLL consumes the exact already-audited C6 `nll1000.jsonl` files.

## NLL implementation

`capability_nll.py` imports the pinned LLaMA-Factory processor and verifies its commit and exported template. It compares every actual input/label sequence to `source + target` / `[-100] * len(source) + target`, and checks the accepted C6 full token count. No truncation, packing or padding. One solution per forward pass; `AutoModelForCausalLM` computes its standard causal cross entropy under `eval()` and `torch.inference_mode()`. No training or generation occurs.

The first prompt token is masked, so the model's causal shift retains all response tokens, including the terminator. Each row records target count, mean loss, summed NLL, parent/solution IDs and token/label hashes. The primary average is weighted by target-token counts; an unweighted mean of solution-level losses is a secondary diagnostic. NLL units are nats per model token; the two families have different tokenizers.

The zero-shot NLL prefix follows the training serialization. This is a prospective implementation choice for the previously unspecified NLL conditioning, stated here for review. The pass@1/pass@8 shot rules remain exactly as registered.

`modal_capability.py` validates C1 file hashes, source hashes, immutable run IDs and an admitted forecast before loading the initial model. It uses the existing pinned training image, H100 / 2 CPU / 16 GiB, a persistent output volume and no automatic retries. Launch with `modal run --detach -m experiments.p012.modal_capability`.

## Evidence and execution order

- 36 relevant tests pass, including all four actual tokenizers, masking/causal shift, token-weighted aggregation and rejection of duplicate/missing draws or changed inputs.
- All 24 complete generation endpoints fit. Maximum prompt lengths: Qwen MATH 2,618 / GSM8K 955; Llama MATH 2,545 / GSM8K 861. The full 4,096-token output allowance is preserved.
- All eight actual NLL input sets pass parent membership, two-solutions-per-parent and normalized solution-hash checks. Earlier accepted C6 evidence contains real pinned LLaMA-Factory preprocessing checks. This packet has no GPU NLL result yet.
- Capability budget remains $4. The manifest is a preparation record, not a production budget admission. After review, first measure one Qwen/MATH setting, forecast the remaining endpoints from measured throughput, and admit each finite batch under the existing 80% remaining-budget rule. If the complete scope exceeds the cap, report it before further calls; do not silently reduce draws, questions or endpoints.
- Code fixes requested by this review will be applied together. No extra per-cell review round is proposed.

Only code, manifests, numeric checks and raw data are supplied here; course prose remains the owner's work.
