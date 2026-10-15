# Audit 20261014bw: Stage 0 complete generation A2 (raw integrity + GSM G0)

- **Request:** `p009-stage0-generation-complete-A2-r1`
- **Scope:** `p009-stage0-generation-complete-raw-and-GSM-G0-A2`
- **Target:** `192f9156` (packets `stage0_generation_results_v1/{teacher_p2_p3,qwen_p3,olmo_p3}` + `stage0_complete_a2_v1`)
- **Packet MANIFEST SHAs:** teacher `cb844ffa…795`, qwen `657c671e…a7a`, olmo `090c796e…4d3`. Every manifest entry recomputed; 0 mismatches.
- **Source spec:** `e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24`

## Decision

- **Raw integrity: PASS.** 14,450 / 14,450 records.
- **GSM G0, NC: PASS (local, now externally replayed).**
- **GSM G0, S2: FAIL** under the frozen cap rule. This is the correct outcome of the frozen gate, not a defect.
- **S1: PENDING P1.** Nothing about S1 eligibility is inferred here.

## Method (independent)

I wrote my own replay (`replay_stage0.py`, output in `replay_out.json`). It does not import Codex's oracle or the HF tokenizer:

- **Decoding:** my own byte-level BPE decoders, built from the pinned tokenizer.json files. Qwen vocab for teacher/Qwen, OLMo-2 for OLMo.
- **Frozen code:** `first_stop` and `completion_score`, imported from `analyses/completion_contract.py` at the target.
- **Native stop id:** the first EOS present, else the model's primary EOS.
- **Special ids:** taken from the tokenizer.json `added_tokens` with `special: true`.
- **Inputs:** `design_and_inputs_v1/stage0_inputs.tar.gz`. All 7 input SHAs match `input_readback` in `ACTUAL_GATE_PROJECTIONS.json`.

For every one of the 14,450 records I check:

1. **Count and identity.** The record count is exact, there are no duplicates, and `candidate_id` / `problem_id` follow the frozen order.
2. **Prompts.** `prompt_token_ids` equals the frozen `input_ids`, or the request roster `prompt_token_ids` for procurement.
3. **Sampling dict.** The full dict equals the expected one:
   - procurement: T 0.8, top_p 0.95, per-request seed;
   - endpoints: greedy (T 0, top_p 1), seed 17;
   - all: top_k −1, max_tokens = cap, `stop_token_ids` = model EOS set, `ignore_eos` false, `skip_special_tokens` false.
4. **Token ids.** Non-empty, ≤ cap, all inside the vocab, and prompt + cap ≤ 2048.
5. **EOS rules.** EOS may appear only as the last token. Any output without EOS must be exactly cap length with backend `length`.

## Results (all identical to Codex's `RESULTS.json` summaries)

| Dataset | n | Logical stops (mine = Codex) | Correct | Problems |
|---|---|---|---|---|
| math_procurement | 8993 | native 8253, cap 740 | — | 0 |
| teacher_gsm_zero | 1319 | native 1271, cap 48 | **1106** | 0 |
| teacher_math_zero | 500 | native 464, cap 36 | (P1) | 0 |
| qwen_math_zero | 500 | native 420, boundary 12, cap 68 | (P1) | 0 |
| qwen_math_four | 500 | boundary 386, native 75, cap 39 | (P1) | 0 |
| olmo_gsm_zero | 1319 | native 608, boundary 165, **cap 546** | **166** | 0 |
| olmo_gsm_four | 1319 | native 1053, boundary 223, cap 43 | 487 | 0 |

Backend vs logical differences are explained by native-EOS-at-cap ties: procurement has 4 and teacher_math has 1, plus new-problem boundaries inside length-finished outputs. Technical unknown = 0 everywhere.

## Operational lineage

There are 60 batches across the 3 runs (44 / 4 / 12):

- Every `intents/*` and `completed/*` candidate list equals the raw batch's ids exactly.
- Every batch has a timing record.
- There are 57 forecasts. All are admitted, and every one satisfies `remaining = 1.2 × (max_batch × R + 300)` to 1e-6.
- `remaining_batches` falls monotonically to 1.
- Maximum predicted cents per run is under the reservation: teacher 287 / 985, qwen 168 / 326, olmo 185 / 326.
- Worker batch maxima were 20.4 s, 17.7 s and 13.5 s.

Each `GENERATION_COMPLETE.json` reports the full frozen roster, no score on GPU, and 0 training updates.

## G0 (frozen integer rule)

| Setting | Teacher | Student 0-shot | Gap | Relevant caps | Result |
|---|---|---|---|---|---|
| NC | 1106 | 650 (P0 vLLM, accepted internal-only; replayed in bq) | 456 = 34.57 pp | 48 / 43 (both ≤ 197) | **PASS** |
| S2 | 1106 | 166 | 940 = 71.27 pp | 48 / **546** / 43 | **FAIL: 546 > 197 (15% of 1319)** |

The NC student cap count 43 comes from P0 `RESULTS.json` (`1b065f68…`, base_638 `length_cap` 43). It matches Codex's `[48, 43]`. The equality with OLMo-four's 43 is a coincidence.

## Notes

- **N1 (science).** S2 is eliminated by the frozen cap rule. OLMo-2-1B in 0-shot runs to the 512-token cap on 41.4% of GSM8K. Its 4-shot endpoint behaves (cap 3.3%, 487 correct), but using 4-shot as the S2 student baseline would be a post-result amendment. **My recommendation is to keep the frozen gate.** If the owner wants a weaker-student arm, it should be a new, separately preregistered setting, not a relaxation of S2.
- **N2 (science, S1 watch).** The S1 caps are under 15% but not by much: teacher MATH 7.2%, Qwen 0-shot 13.6%, Qwen 4-shot 7.8%. Qwen 4-shot MATH ends by new-problem boundary in 386/500 = 77% of outputs, so its score depends heavily on `first_stop` truncation. This is allowed by the frozen contract, but it should be stated beside any 4-shot number.
- **N3 (data).** In procurement, 3 of the 500 four-attempt problems have two byte-identical attempts despite distinct seeds. The dedup / duplicate charging rules already cover this. Not a defect.
- **N4 (scope).** This A2 does not cover MATH symbolic scoring (P1), student training, or any future dose / budget gate. That matches the review request.

## 科学信号检查 (science-signal check)

- **Is the signal real?** Yes. NC shows a 34.6 pp teacher–student gap. That gap is the headroom Stage 1 needs, but P008 showed headroom alone did not give a learning curve.
- **S2 is gone.** Only S1 (Qwen on MATH) is left as a candidate learning regime. If S1 also fails G0 or Stage 1, the preregistered outcome is "no qualifying learning regime".
- **Spending more budget on S2 would not help.** The failure is a stopping-behaviour property of the 0-shot endpoint, not a sample-size issue.
