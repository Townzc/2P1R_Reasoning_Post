# Audit 20261014bs: P009 Stage 0 generation core (code and provisional numbers)

| Item | Value |
|---|---|
| Request | `p009-stage0-generation-core-r1` |
| Scope | `p009-stage0-generation-core-code-and-provisional-numeric` |
| Target | `6f0633f5ef6b6c505b6b37c9465981ae5d5ce007` |
| Manifest | `5d4e4a7a0f2e3b70ac3dafeaa7f866a6368cd4b6f151c9f2aa0330f85d17039f`: all 32 entries match |
| `candidate_sha256` | `740da1507b5d6186a39f7a6439abb780d602ff323990a01cb63a916990c62055` (canonical digest of `CANDIDATE.json`, recomputed) |
| `source_files` | the 23 entries of `SOURCE_BUNDLE.json`; all recomputed from the target |

## Decision

**PASS-WITH-NOTES (code only).**

This decision does not admit P1, P2, P3, G0, model uploads or dispatch. It also does not stand in for the final A1 release, which still has to cover the runtime, model inputs and numbers.

I re-ran the 16 CPU fixtures on the target tree and all pass. The `.local/p009_20261014/r1` directory has to exist for them to run. They do not exercise CUDA or real output generation.

**N1 (schedule risk) should be read before the teacher worker is dispatched.**

## What I checked

### Datasets and sampling

- The files and hashes match the frozen Stage 0 inputs: 8,993 teacher requests plus six endpoint files, 5,457 outputs in total.
- Endpoint metadata is checked: `n`, context 2048, the cap, and the model's first EOS.
- The prompt length is capped at 2048 minus the generation cap, so a prompt can never be truncated.
- Procurement keeps each request's own seed, temperature 0.8, top-p 0.95 and a 1,024-token cap.
- Endpoints use greedy decoding with seed 17, a 512-token cap for GSM and a 1,024-token cap for MATH.
- Each request is identified by `candidate_id = pid::attemptNN` with attempts 1 to 4. Duplicates are rejected.
- P0 base 650 is reused only for its own endpoint; nothing is regenerated.

### Engine

- One model lifetime runs per slot, all on the shared, reviewed `high_throughput_v1` configuration.
- The model's vocabulary and architecture are checked against the pinned revision.
- Any automatic EOS the model emits must be in the registered set:
  - teacher: 151645 and 151643;
  - Qwen: 151643;
  - OLMo: 100257.

### Transport

- Raw output is saved before it is validated, so a malformed or extra response is kept.
- Every output must match its request's identity, prompt and sampling.
- EOS may appear only as the last token.
- A native EOS that lands exactly on the cap may carry `length` metadata. This is the same tie that was accepted for P0.
- A non-EOS output is accepted only if it is exactly cap-length. Any shorter or unknown ending is refused.
- Units and acknowledgements are written once with `skip_if_exists`. Nothing is replayed.
- There is exactly one first-batch measurement per model lifetime. Every later batch must pass the forecast built from all observed intervals and the actual elapsed time.

### Budget arithmetic (recomputed)

| Slot | Window | Reserve |
|---|---|---|
| Teacher | 3,100 s | 399¢ |
| Qwen | 1,600 s | 216¢ |
| OLMo | 1,900 s | 252¢ |

- Each reserve equals `cost_cents(window) + 20`.
- 1,004¢ already reserved plus 867¢ new comes to 1,871¢, within the 2,000¢ cap and leaving **129¢**.
- The bases for the 80% rule are 996, 597 and 381¢.
- The forecast's cost check (at most `cost(total + 700) + 20`) never binds before the time limit (at most `worker − 30` s) does.
- No settlement release, no borrowing, and no change to the dose or the science.

## Notes

### N1: the teacher worker's timing margin is thin (schedule risk)

I solved the frozen forecast for the first-batch duration *t* that still passes:

| Worker | Batches | Largest admissible first batch (setup 70 s / 120 s) |
|---|---|---|
| Teacher | 44 | **36.9 s / 35.9 s** |
| Qwen | 4 | 95.7 s / 84.8 s |
| OLMo | 12 | 52.1 s / 48.6 s |

- The only measured batch so far is a P0 GSM batch: greedy, 512 tokens, about 11–12 s.
- A teacher procurement batch runs 256 sequences at temperature 0.8 to 1,024 tokens, with **per-request seeds**. In vLLM, per-request seeded sampling takes a slower sampling path, so I cannot rule out a batch longer than about 37 s.
- If the forecast fails, the teacher worker stops after its first batch, keeps its 399¢ reservation, and leaves only 129¢. That is not enough to retry the teacher.
- One option that fits the current $20 cap: give the teacher slot all of the 129¢ headroom (reserve 528¢, window 4,162 s, worker 3,462 s). The break-even then rises to **about 57 s**, but no headroom remains for any other failure.
- This is a budget and schedule decision for the owner and Codex, not a code defect.

### N2: check SamplingParams on the pinned wheel

- `top_k=-1` plus per-request `seed` under the V1 engine must be accepted by the pinned vLLM 0.11 `SamplingParams`.
- The A1 runtime release should construct the exact parameter objects on the pinned wheel (no GPU needed). That way a validation error cannot first surface inside a paid worker.

### N3: G0 endpoint pairing (follows from br N1)

- The teacher endpoints use the teacher's chat-format prompts (EOS 151645). The student endpoints use raw prompts.
- Decoding (greedy), caps, engine and frozen parser are all the same. The prompt family is each model's native 0-shot format.
- The G0 report should state this pairing explicitly for:
  - NC: `teacher_gsm_zero` vs base 650;
  - S1: `teacher_math_zero` vs `qwen_math_zero`;
  - S2: `teacher_gsm_zero` vs `olmo_gsm_zero`.

### N4: no retry room

After all three reserves, Stage 0 has 129¢ left, so any failed slot is final unless the owner adds budget. The planned dispatch order is teacher, then Qwen, then OLMo, so a teacher failure would also stop S1's G0.

## Science-signal check

There is no outcome yet. Two signals matter:
- **Schedule risk on the teacher worker (N1).** Every Stage 0 G0 depends on it.
- **The S1 n = 3,200 length check (be N1: mean ≤ 655 tokens).** Procurement at a 1,024-token cap produces exactly the outputs that check needs, so measure it from the first batch.
