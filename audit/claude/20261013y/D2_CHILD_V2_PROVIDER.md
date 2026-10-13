# Claude audit 20261013y — D2 child admission v2 @ 32777f41 (provider-lookup amendment): **PASS**

Audited at 17:33 UTC. Latest full-window dispatch is 17:48:20 UTC.

- **Scope.**
  - The v2 ADMISSION differs from v1 **only** in `source_files`. Two files are affected: `provider_release.py` is new (7ebd47b4…), and `modal_pool_continuation.py` changed (4fe3935d→c0463ab1).
  - The `work()` AST is identical to the reviewed a385fb38, which I checked myself.
  - All numeric scope, plan/config, probe formula, guard, timers, generation, budget and deadlines stay unchanged.
- **`provider_release.py`.**
  - It queries each original app ID exactly, via `modal app info <id> --json`, with a 30 s timeout. Errors propagate.
  - It requires a unique roster that corresponds one-to-one, with lifecycle `stopped` and a non-empty `stopped_at`, and zero current containers.
  - It never synthesizes rows. Replacing the recent-only `app list` with exact-ID lookups is the correct fix.
  - PROVIDER_PROOF shows D1 stopped at 05:20:23 PDT, D2 stopped at 05:24:52 PDT, and containers=[].
- **N1 resolved for dispatch.** The parent D2 took **13.7 s** from start to environment.json, far under the 100.1 s probe threshold. As decided, the billed child probe stays binding and the formula is unchanged.
- **Tests.** 23/23 pass locally (8 provider-release + 15 worker, `PYTHONPATH=.:tests`).

This PASS binds the v2 source/spec for one upload and dispatch, and admits no student.
