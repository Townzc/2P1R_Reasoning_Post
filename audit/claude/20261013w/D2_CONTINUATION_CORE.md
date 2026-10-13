# Claude audit 20261013w — p008-d2-continuation-core-preflight-r1 @ c16ba8c8: **PASS-WITH-NOTES (code only; nothing admitted)**

Audited 2026-10-13 ~13:25 UTC at 99e43b64. The decision on the owner's scope/time is still open (A/B/C, see 20261013v). This verdict cannot stand in for it.

## Answers
- **Q1. Prefix binding.** YES.
  - `load_prefix` checks the configured manifest SHA and the exact six-file roster, re-verifies every file, and fixes draw=2, B8 and 16,384 attempts, along with the input SHA.
  - It requires the failed terminal, claim SHA, plan SHA, intent SHA, source commit and evidence digest to agree. It also checks the original order, prompt lengths and wallet roster, the teacher revision, and the SHAs of the reconstructed cache, events and states.
  - `pool_prefix.restore` additionally requires each of the following:
    - zero unknown or pending entries;
    - per-parent attempts contiguous from 1 to k;
    - each seed equal to `stable_seed('teacher',2,…)`;
    - integer token counts;
    - every original action re-proposed exactly and re-settled with an identical charge;
    - the original end states equal;
    - consumed set == cache;
    - the unfinished set equal to the reconciliation's.
  - Lineage keeps `original_parent_status='failed'`.
- **Q2. The loop is unchanged and nothing is replayed.** YES.
  - My own AST comparison of `run()`: from the `while True` loop through the wallet, cache and summary serialization, every statement is identical to `pool_runtime.run`. The only difference is that the final `return dict(...)` became `result=dict(...)` plus a lineage `update`.
  - The only pre-loop change is that the initial state is restored instead of starting empty.
  - `pending_union` asks only for keys missing from the cache, and `Cache entry already exists` stays a hard error, so no parent candidate can be regenerated.
  - The cumulative attempt and token bounds start from the parent's totals.
  - Wallets keep their full original charges, and every reservation is still committed before the cache is read.
- **Q3. Scoping.** Accurately stated.
  - There is no Modal entrypoint, binding or admission yet.
  - The 20 CPU tests pass locally (12 continuation + 8 prefix). Note that they need `PYTHONPATH=.:tests`: running them as `tests.X` fails with `ModuleNotFoundError: test_p008_pool_prefix`. Please fix the import or document how to run them.

## Notes for the future worker review (blocking at that stage, not now)
- **W1.** The 7,070 s feasibility forecast assumes **ParallelActiveCheck** for every `journal.begin` check. The worker must actually wire it in and keep the original per-unit fresh-check semantics. If it falls back to sequential reads (≈7.1 s × ~4 checks per round), the child will certainly exceed 7,200 s.
- **W2.** The forecast margin is 1.8%. Fix a feasibility check right before dispatch: re-measure the 26-key parallel read on the child host before the model loads, and abort before the model load if `136 × (gen + checks × measured) × 1.2 + 300 > 7,200`. This happens before any teacher call, so it is outcome-blind.
- **W3.** A merged G1 must be computed over **parent raw + child raw**, with child physical batches numbered from 146 onward. My `g1_pool.py` can be pointed at both directories. The child's `candidate_cache.json` contains parent rows, so the oracle must not count parent rows as child returns.
- **W4.** A new child deadline and the D1/D2 common-T coupling (20261013v) are owner decisions. This code review authorizes neither.
