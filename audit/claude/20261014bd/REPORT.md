# Audit 20261014bd — P009 A0 required clarifications (R1/R2) and scoped Stage 0 verdict

- Request: `p009-a0-required-clarifications-r1`
- Supplement target: `f1e6abd9de4d26150a33c285989236c663ed1acc`; original A0 target: `e6350f0bf1f987d7c8a5acd76bbf924b6ed33f4e`
- Supplement manifest: `reports/p009_20261014/a0_required_clarifications_v1/MANIFEST.json`, SHA-256 `1547f168ee3874712e3450ce229e3037b43101e610cd82dd42985030459f5f01` (matches the request)
- The original design/input packet and `gates.py` are unchanged between the two targets (empty diff)

## Verdicts

1. **R1: CLOSED.**
   - The protocol now freezes S1 Stage 1 eligibility to attempt01 only. That output must itself be format-eligible and correct, and that exact output is the training answer. Attempts 2–4 cannot rescue eligibility.
   - The NC/S2 difference (D1 answers correct within up to 8 attempts) is disclosed.
2. **R2: CLOSED.** The protocol now states, frozen before any P2 output, that:
   - B's ceiling includes every attempt on every question traversed in the raw seed-17 order, including skipped questions;
   - D starts at the first question of that same raw order and pays for every first attempt, including format-ineligible ones;
   - D keeps format-eligible first attempts regardless of correctness;
   - A and B share P_nat (format-eligible attempt01 and a correct answer within 4 attempts);
   - physical charges stay in the ledger even when a virtual ceiling excludes an output.

   This is exactly what 20261014ba asked for.
3. **Scoped Stage 0 design/input decision (original target + this supplement): PASS-WITH-NOTES.**
   - It supersedes the broader PASS-WITH-REQUIRED-CLARIFICATIONS of 20261014ba for every purpose, since its required items are now closed.
   - The remaining notes are N1 (short-demo 4-shot, now labelled as such) and the limitation below. Neither blocks anything.

## New independent verification

The supplement made two checks possible:

| Check | Result |
|---|---|
| OLMo tokenizer | `tokenizer.json` SHA `73fd5254…` equals the hash recorded in the Stage 0 summary. No normalizer, no post-processor, `add_bos_token` unset; config, generation-config and tokenizer EOS all 100257 |
| OLMo prompts, re-encoded with my own BPE encoder (no NFC, as this tokenizer specifies) | `olmo_gsm_zero` and `olmo_gsm_four`: **0 / 1,319 construction mismatches each**; 0 round-trip mismatches; max 189 / 853. This confirms the no-BOS convention. Training must use the same convention with one terminal EOS 100257, as stated |
| MATH dev-order reconstruction from the 7 original test shards | **Not done.** I have no Parquet reader here (pyarrow and fastparquet are absent and the package indexes are blocked). Remains a limitation: the four selected demos are verified as test-split, disjoint and ≤ 57 tokens, but their hash-order selection is not |

## Science-signal check

No outcome exists yet.
