# Audit 20261014be — P009 whole-answer training-plan code

- Request: `p009-training-plan-code-r1`
- Target: `c23ed87558685f152b2c03b4af9a75cef6c18ca7`
- Packet manifest: `reports/p009_20261014/training_plan_preflight_v1/MANIFEST.json`, SHA-256 `8403f2def5936ab7a2cbf7fa526439c33bfd60cb288a60987fb11893f301e156` (matches the request)
- Scope: pure planning and validation code. No selected-data plan, training or runtime is admitted.

## Verdict

**PASS-WITH-NOTES.**

## Checked

| Item | Result |
|---|---|
| LR bytes | `LR_VECTORS.json` file SHA `cb9c2e04…` and canonical `'1024'` vector SHA `14ac59d2…` both match. The file was committed with P008 on 2026-10-13, so it predates P009. The vector equals linear warmup to 1e-4 over 64 updates followed by cosine to 1e-5, within 1.4e-20 of my own formula. No recomputation on the host |
| Dose | Exactly 1,024 nonempty updates and 2,097,148 supervised targets. `budget_report` must show 0 padding. `TARGETS < Σ lengths` is rejected, so there is no q = 0 bridge and no target relaxation |
| Exposure | Every answer is used q or q+1 times with q ≥ 1, as checked against the recorded `row_exposures`. One answer per question; `problem_id` and `path_id` both unique |
| Row contract | Prompt masked; labels equal IDs after the prompt; a single terminal EOS and no embedded EOS; length ≤ 2,048; integer metadata consistent with `encode_row` |
| Seeds | {17, 29} only |
| Tests | 7 + 1 synthetic fixtures pass, with logs retained. They are synthetic only, as the packet says |

## Notes

- **N1 — S1 n = 3,200 feasibility (science risk; check right after P2).** The fixed dose admits n = 3,200 only if the mean supervised length is ≤ 655 tokens (2,097,148 / 3,200).
  - GSM8K is safe: the D1 mean is about 292 Qwen and 275 OLMo tokens, so q ≈ 2 at n = 3,200.
  - MATH answers from Qwen-Math are much longer. If the mean of the frozen first-3,200 attempt01-correct answers exceeds 655, `make_plan` correctly fails closed, and S1 cannot reach its G1 point under the frozen dose.
  - Compute this from P2 outputs before any S1 student is trained. If it is infeasible, stop and ask the owner. Do not change the dose or n silently.
- **N2 — repetition at small n (descriptive arms).** q is about 70 at n = 100 for GSM8K and about 17 at n = 400. The G1 comparison deliberately uses 400 vs 3,200 for this reason, as in 20261014ay §5.2. Report q per run.
- **N3 — duplicate MATH question.** `checked_rows` enforces unique `problem_id`, not unique question text. The data-selection step must enforce the protocol's "earliest of algebra/train/925 and 959" rule before planning.

## Science-signal check

No outcome yet.
