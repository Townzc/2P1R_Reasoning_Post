# Audit 20261014ba — P009 A0 design and Stage 0 inputs

- Request: `p009-design-and-stage0-inputs-r1` (INDEX, pending, blocking)
- Target commit: `e6350f0bf1f987d7c8a5acd76bbf924b6ed33f4e`; request commit `630cc77cac20b0f9c0316a59be4df911c3d109b4`
- Packet manifest: `reports/p009_20261014/design_and_inputs_v1/MANIFEST.json`, SHA-256 `8ad23ec5f042bc66894949e9bc906f890308c54309b5debde688ac8c441b882a`. All 18 entries match byte-for-byte (`stage0_inputs.tar.gz` `1c5785b6…6440`; inner files match `INPUT_MANIFEST.json`)
- Scope: A0 design review and the Stage 0 inputs only. **This is not a runtime admission.** A1 stays mandatory.

## Verdict

**PASS-WITH-REQUIRED-CLARIFICATIONS.**

- The Stage 0 inputs **PASS**: every Qwen-side claim was reproduced independently (§2).
- The protocol faithfully implements the owner-approved draft, and in several places it tightens it correctly.
- Two definitions must be frozen **before any P2 teacher output is read** (R1, R2), because both choose data based on teacher correctness:
  - R1 governs Stage 1 for MATH.
  - R2 governs the primary Stage 2 contrast, B − D.
- Neither changes scope, budget or dose. Both block their own stage, not Stage 0.

## 1. Owner amendments and accounting

| Item | Finding |
|---|---|
| $100 total; stage caps $10 / $50 / $35; $5 unallocated, not borrowable | Matches `OWNER_AUTHORIZATION.json`, `BUDGET_PREPARATION.json` and `gates.STAGE_CENTS`. PASS |
| Five Stage 2 conditions × 2 seeds; automatic progression only after gates | Matches. PASS |
| Teacher context 2,048; 7 rows unsupported and not generated | Matches; independently verified in §2. PASS |
| Llama gated (HTTP 401) → OLMo-2-0425-1B fallback | Permitted by the draft; revision and weight hashes are recorded. PASS |
| **Project headroom** | **The draft's "$15.76 remaining" was my error.** The $450 ceiling already protects $50 of the $500 envelope, so I subtracted it twice. I also counted the full reservations of closed stages (P008 $266.44, exploratory $30) as spending, where metering shows ~$136.70 and ~$11.20. Codex's envelope of meter $235.69 + $25 lag buffer + $100 new = $360.69 ≤ $450, leaving $89.31, is the correct structure. The $25 lag buffer is an estimate, not a bound; keep re-reading the meter before every stage. ACCEPTED |

## 2. Independent input verification

Method: I wrote a pure-Python Qwen2 byte-level BPE encoder/decoder, because the container has no `transformers`, `tokenizers` or `regex`.
- **Encoder self-test**: decoding and re-encoding all 4,138 stored Qwen-family endpoint prompts reproduces their token IDs exactly (0 mismatches).
- **Tokenizer identity**: the `tokenizer.json` SHA `c0382117…` equals the packet's recorded Qwen/teacher tokenizer hash.

| Claim | My result |
|---|---|
| MATH train 7,500 rows, 7,499 unique; duplicate algebra/train/925 = 959 | Reproduced |
| Exact normalized train ∩ MATH-500 = ∅; MATH-500 has 500 unique questions | Reproduced (0 overlap) |
| Teacher prompt + 1,024 > 2,048 for exactly 7 rows | Reproduced, same IDs and same lengths: 1,063 / 1,682 / 1,536 / 1,198 / 1,320 / 1,055 / 1,072 |
| 8,993 requests = 7,493 first attempts + attempts 2–4 on 500 rows | Reproduced. All first attempts come first; the 500 are reproduced from `sha256('p009-extra-500-seed17:'+id)`; candidate IDs and seeds are all unique |
| Teacher request prompt IDs | All 8,993 equal my own encoding of the P008 system + user chat template. Sampling 0.8 / 0.95 / top-k off / 1,024 matches `sft_allocation_acquisition.contract.SAMPLING` |
| Endpoint construction (Qwen MATH 0/4-shot, teacher MATH/GSM 0-shot) | All prompts equal my own construction. Max prompt + cap ≤ 2,048 everywhere (795 / 978 / 819 / 216 with caps 1,024 / 1,024 / 1,024 / 512) |
| P0 GSM prompts | 0 / 1,319 differ from the frozen P008-format base prompts; order equals the test order |
| MATH dev 4-shot examples | All four are from the original test split and disjoint from train and MATH-500; 45 / 52 / 44 / 42 tokens ≤ 57 = ⌊(1,024 − 795) / 4⌋ |
| GSM dev examples | The original four; 0 test overlap |
| OLMo prompts | **Structural checks only** (Hugging Face is blocked for me): n = 1,319; EOS 100257 absent from prompts; max 189 / 853; each 4-shot prompt ends with its 0-shot prompt |

Limitations:
- I could not re-derive the hash-ordered dev selection: the 4,500 original-test candidates are not in the tarball.
- I could not encode OLMo text. The A1 packet should include the OLMo tokenizer files, whose hashes are already recorded.

## 3. Gate code (`gates.py`, 8 tests)

- **Thresholds**: integer comparisons match the draft exactly (parity 1 / 3 pp and 4%; G0 20 pp and 15% caps; G1 5 pp / CI > 0 / 2.5 pp; NC ≥ 5 pp; futility < 2 pp; n\* rule).
- **Fail-closed parity hole**: correct, and accepted as a tightening of the draft.
- **Note**: `g0()` takes a single `caps` count. A1 must apply the 15% cap check to the teacher endpoint and the student 0-shot endpoint separately, as the protocol says.

## 4. Required clarifications (freeze before P2 outputs are read)

**R1 — Stage 1 MATH eligibility must be uniform.**
- Problem: P2 gives most questions one attempt, but the 500 hash-selected rows four. "Questions with a correct answer" would therefore admit those 500 on four chances and everyone else on one.
- Required: for S1 Stage 1, a question is eligible iff its **attempt01** output is format-eligible and correct; its training answer is that attempt01 output. Attempts 2–4 are used only for the descriptive retry hazard and for Stage 2.
- Disclosure: S1 then draws from questions the teacher solves on the first try, while the GSM8K settings draw from D1 rows correct within up to 8 attempts. That cross-setting difference must be stated in the report.

**R2 — the D arm must not skip questions it cannot know are bad.**
- Problem: as written, "D uses first attempts on P_nat and then subsequent new questions" builds D's sequence from P_nat. P_nat is defined by *eventual* correctness within 4 attempts, so D would silently skip unsolvable or mislabeled questions free of charge. That is exactly the information an unverified buyer does not have, and it biases the primary B − D contrast toward D.
- Required:
  - **B's spending ceiling** = the teacher tokens of **every** attempt on **every** question B traverses in the seed-17 order until n\* questions have an eligible correct answer within 4 attempts. This includes the up-to-4 failed attempts on questions B skips.
  - **D** traverses the **same raw seed-17 order from the first question**, buys one first attempt per question (charged even when not format-eligible), and keeps every format-eligible first attempt regardless of correctness. It stops before the next first attempt would exceed B's ceiling.
  - **A** may stay on P_nat, matched with B, for the secondary B − A contrast.
  - **P_nat** = questions whose attempt01 is format-eligible and that have an eligible correct answer within 4 attempts. Both exclusion counts and their costs are reported.

## 5. Notes (non-blocking)

- **N1 — short-demo 4-shot.** Because the longest MATH-500 prompt is 795 tokens, all four MATH demos must fit in 229 tokens. The ≤ 57-token demos (e.g. "Simplify √192") are unrepresentative, so the MATH 4-shot baseline is likely a weak lower bound. It is descriptive only, so no gate changes. Label it "short-demo 4-shot".
  - Optional, only with owner approval: one extra descriptive MATH-500 run with the first hash-ordered full-length demos at evaluation context 3,072 (max prompt 1,665 + 1,024). This would not affect the teacher or any training contract.
- **N2 — OLMo BOS convention.** OLMo prompts carry no BOS. A1 should confirm from the model card and config whether OLMo-2 expects a leading `<|endoftext|>`, and use one convention in both training and evaluation.
- **N3 — P0 calibration.** Agree: no paid call until a bounded calibration admission is reviewed. Suggest one pinned complete batch per parity model, with a hard cap of ≤ $2 inside Stage 0's $10 and outputs reused for the full run.
- **N4 — inference statements.** The interpretation language (conditional or adaptive inference, no equivalence claims, label agreement ≠ reasoning validity) is correct and matches the draft's intent.

## 6. Science-signal check

No P009 outcome exists yet, so there is no signal to report. The early-report hooks are in place: A4 after the first 400 / 3,200 pairs, and the futility cancellation rule.

## Reproduction

`audit/claude/20261014ba/qtok.py` (encoder) and `check_p009.py`. Output: `check_out.json`.
