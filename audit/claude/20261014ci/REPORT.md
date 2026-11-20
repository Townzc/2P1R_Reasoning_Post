# Audit 20261014ci: `p009-stage1-S1-readonly-closeout-code-r1`

- **Scope:** `p009-stage1-S1-observation-and-complete-publication-code`
- **Target:** `adfc66cbdb233f764c8861859fde7e5958571ad8`. Manifest `844b8ad084e9f6cac7faf37f4cf2b235ba4c45273713b32c2ca2e5bdd834d355`.
- **source_files** (exact; all three hashes recomputed):
  - `scripts/p009_s1_observe.py`: `228a0642155ded7948171db7cf7f47df573028c290e24730680a69b8b9fdcb78`
  - `scripts/publish_p009_s1_results.py`: `0b3169485103d44eecd6c065e24a5fd28f350f04097dad3b5b8537c7117b9754`
  - `scripts/publish_p009_stage0_result.py`: `708d426fc1097e00e5f8a56b5daa6441c87c25c7eb62b3cf1477fb8d6f94ab26`
- **runtime 81:** pinned. The hashes match ch.

## Decision: PASS-WITH-NOTES

## Checks
**`publish_run`**
- All checks below run in `check_complete` **before** `mkdir`:
  - full `validate` of the sent release;
  - claim, terminal, attempt and intent equality, with the intent exactly the 4-field form;
  - the permanent markers, and every `required_records` entry;
  - all apps stopped with zero containers, including the first-pair apps for later slots;
  - the worker cap of 4500 s;
  - all six reports, plus the futility report for later slots;
  - the raw bytes of the proxy comment;
  - the raw oracle bound to the spec, sources, artifact digest, state, intent, receipt, ledger, provider and rows;
  - the 500-ID Boolean table in frozen order;
  - the scoring binding and window (6000 s, plus 5 s cleanup);
  - `verify_score_payload` agreeing with the oracle;
  - `independent_adjudication_complete=False`.
- The provider projection and file rosters are also computed before `mkdir`.
- **Omitted from publication:** state binaries, the private intent, packaging and the scoring worker log. Each is recorded with its hash.

**`publish_first_pair`**
- It requires the original registered-analysis review (target `2c7d6b5c`) and those source bytes.
- It re-runs `check_complete` for both runs, and requires each run's already-published packet to verify against its manifest, with an identical oracle.
- It also requires 2 distinct apps and the same NC A4 report for both runs. NC metadata is pinned through the NC packet manifest (`fc560e60…`) and the NC400 parent oracle gz. The NC values must be 954 and 967.
- It then calls `first_pair_decision(...)` once.
  - The registered futility rule is `gates.futility`: **stop if 100·Δ < 2·500, i.e. if the n3200 student gets fewer than 10 more of the 500 questions right than the n400 student**.
  - `FIRST_PAIR = (s1_s17_n400, s1_s17_n3200)`, so the direction is n3200 − n400.

**Observer.** It only reads from Modal (`Dict.from_name`, `Volume.read_file`, `container list`, `app info`). It does no remote writes, no spawn and no scoring.

**Tests.** 10/10 new tests pass here.

## Notes
- **N1.** `archive_original` still runs after `mkdir`. This is the same low risk as before.
- **N2.** The local scorer's verdicts are "unadjudicated" by design. In first-pair A4 I will independently decode all 2 × 500 raw outputs and check the fixed 50 disagreements, all fallbacks and all timeouts before agreeing with the futility outcome.

## 科学信号检查 (science-signal check)
No S1 outcome yet.
