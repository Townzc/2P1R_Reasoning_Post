# Claude audit 20261013z — p008-d2-deadline14pdt-r3 @ 4ae602a9: **PASS (exact v3 child spec; one dispatch)**

Audited at 18:15 UTC. The latest full-window dispatch is 18:48:20 UTC.

- **Owner authority:** `owner_authorization.answer` = "同意 D2 截止改为 14:00 PDT" ("agree to move the D2 cutoff to 14:00 PDT"), recorded 18:07 UTC as a direct reply in Codex's chat. Every other owner field is unchanged.
- **Scope (my own diffs against the v2 PASS @32777f41):**
  - **ADMISSION:** only `plan_sha256`, `owner_authorization` and `source_files` differ.
  - **PLAN:** only `deadline_epoch` changes, 1791921600 → **1791925200**, which equals 2026-10-13 21:00:00 UTC.
  - **CONFIG:** identical.
  - **Source:** of the 31 source files, only two change:
    - `continuation_binding.py` changes `CHILD_DEADLINE` and the owner deadline string;
    - `modal_pool_continuation.py` changes the SPEC path from v2 to v3.
  - **`work()`:** its AST is identical to v2.
  - **Unchanged:** the 7,200 s worker, the 1,200¢ / $249.68 budget, the probe formula, the guard, and generation.
- **Prior refusal:** `PRIOR_PRESPAWN_REFUSAL.json` shows the v2 local entrypoint refused with "Complete startup/runtime window expired" **before spawn**.
  - Nothing ran: 0 function invocations, 0 claims, all four child-campaign keys null, the remote run directory absent, and the build-only app stopped at 10:48:32 PDT.
  - This is therefore not a retry of scientific work. Because no campaign record was ever registered, the new plan's `register` cannot conflict.
- **Input reuse:** the 7 prefix inputs (43,709,997 bytes) uploaded and read back under v2 are reused. They are bound by the unchanged `prefix_manifest_sha256` in CONFIG. The entrypoint still re-enumerates child records and the remote directory, and still requires a fresh 7,900 s window.
- **Tests:** 29/29 pass locally (`test_p008_child_deadline_v3` + `test_p008_continuation_worker` + `test_p008_provider_release`).
- **Note:** the global field `global_compute_stop_utc` 02:00 UTC is unchanged in this spec, which is correct for the child: it ends by 21:00 UTC. The owner's 10:43 PDT relaxation of the **student** stop (#13 comment 6151713942) needs its own student-campaign amendment. This review does not cover it.
