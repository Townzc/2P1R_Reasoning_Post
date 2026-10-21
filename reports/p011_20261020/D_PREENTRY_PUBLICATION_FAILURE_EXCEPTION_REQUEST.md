# D1 first-entry publication race — explicit delegated exception requested

- request_id: `p011-D-first-preentry-publication-failure-exception-r1`
- scope: `p011-D-first-preentry-publication-failure-exception`
- target_commit: `a3a5da834f7ec726e14370b6c5958cb5537d5558`
- failure packet: `reports/p011_20261020/d_pair_preentry_publication_failure_v1`
- MANIFEST SHA256: `c0f5ec6e7f325caeacbc9d4fd20b2445f6f7dddd7eae531e704373325a4922f4`
- FAILURE_BINDING SHA256: `d38a4c94b4b23738f7944d4a524a657f7e5031a2c5274de8fd9425c274b9a2d7`
- Original exact62 target: `687011075c425de058f35133a44284153a4c6159`.
- Unchanged SPEC: `438a120f242b10f99bddc76a06a80f9412dce766dc014fcf603e23e0e71d9321`.
- Full accepted CR/A1/A2-lite report: `26d7fe9706770bfe1c81872b0603e045605456407115db9d0521d2a8a5c7f2b2`.
- Request prepared: 2026-10-21T19:01:51.606166+00:00.

Codex caused a publication race: original D1 CLI16928 built the exact runtime, then `long_d_pair_path.submit` failed at its first published-HEAD check while new B metadata was being committed/pushed. The rejected remote-head value was not saved. This is before exact source verification, job review/budget loading, dispatch INTENT/ledger/reservation creation and `worker.spawn`. No D function-call ID or model computation exists. The one new app was independently observed STOPPED/owned0 at18:58:25UTC; private full provider evidence is retained. Model-call/reservation zero does not imply no possible image-build or storage expense.

Both original input uploads75810/1974 completed and are bound in the failure packet; they must not repeat. D2 never entered. Original62 source/scientific inputs/frozenLR/timing/limits/17flags remain unchanged. All older failed reservations remain100.22 overall; D0. No automaticretry has occurred.

Please give a reasoned explicit delegated disposition and independent failure/source-scope confirmation: allow one additional D1 **entry invocation before its first model dispatch**, reusing the two completed uploads and original unchanged logical IDs/fences, or close/hold the pair. If allowed, D2 remains its original first entry. Fresh observed rates/accounting, complete pair predicted80%/hard-cap reservations, slots/fences and whole windows still apply. Retain the failed CLI, app closure and unused original budget snapshot; create separately dated budget evidence if freshness expires. No release, increased cap, transfer, new arm, timing change or model retry is requested.

Operational correction is local sequencing, with no runtime change: complete and independently verify ordinary publication before launch, keep HEAD unchanged while each entry runs until SUBMITTED or terminal preentry receipt, and publish subsequent metadata only afterward. Both-or-neither remains; no dispatch until this specific exception is accepted. If another failure occurs, preserve it and do not automatically retry.

Required explicit disposition/scope fields:

- `one_additional_D1_preentry_invocation_explicitly_authorized`
- `original_failure_no_model_dispatch_and_zero_reservation_accepted`
- `unchanged_exact62_SPEC_and_prior17flag_review_accepted`
- `both_completed_uploads_reused_without_repeat_and_D2_first_entry_accepted`
- `publication_fixed_until_submission_fresh_gates_pair_window_accepted`

Original CLI whitespace is retained in its explicitly workspace-redacted public projection; whole-format check is not PASS. Full original log/hash is private. P01019UTC freeze and A owner hold remain separate. The original62 PASS alone does not grant this exception.
