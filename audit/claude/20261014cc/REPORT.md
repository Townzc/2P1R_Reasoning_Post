# Audit 20261014cc: `p009-stage1-NC-complete-publication-code-r1`

- **Scope:** `p009-stage1-NC-complete-publication-and-analysis-binding-code`
- **Target commit:** `8692f55f5e7e74312bbf3e4ed6c5c94bf66d75f3` (from INDEX). The bytes are unchanged at 59d7e06a and d09b3ace.
- **source_files** (exact):
  - `scripts/publish_p009_nc_complete.py`: `ef15ff1f20c90f158390ca99c680492f24296e8ca9c9f02f5d24addecc890970`
  - `scripts/publish_p009_stage0_result.py`: `708d426fc1097e00e5f8a56b5daa6441c87c25c7eb62b3cf1477fb8d6f94ab26` (unchanged; only `archive_original` is reused)
- **Packet MANIFEST:** `14c5c8a1…` (per INDEX). The runtime-42 and analysis-4 closures in SOURCE_BINDING equal the accepted cb and Stage 1 analysis bindings.

## Decision: PASS-WITH-NOTES

No actual NC outcome was reviewed. This is a code verdict only. A4 on the real packet is still required, and S1 cannot dispatch from this.

### What I checked
**Static checks**
- Every field the publisher reads exists in the code that writes it:
  - `release.{runtime,core,input,G0,internal_only}_review.local_report_path` comes from `p009_stage1_nc_io.prospective`.
  - `execution_commit` comes from `modal_stage1_nc` (line 99).
  - `logical_stops`, `question_correct`, `state_sha256` and `artifact_digest` come from `audit_p009_stage1_nc.audit`.
  - provider `utc` and `original_app_info` come from `collect`.
  - `lifecycle.created_at` appears in every earlier real Modal record (e.g. Stage 0 olmo_p3 PROVIDER).
- Only the four packaging/intent files and `*.pt` are omitted. `compact_evidence.tar.gz` repackages files that are already individual entries in `artifact_manifest`, so no raw output, update record, ack record, checkpoint manifest or merge proof is lost.
- The decision call is `nc_result(ids, n400, n3200)`, which gives `direction=n3200_minus_n400`. The stop rule is the registered signed rule `100·Δ ≥ 5·n`, so it stops when Δ ≥ 66 of 1319. No bootstrap, parser or model is used.

**Synthetic run**
I ran the real `publish()` and `bound()` at the target. Only the binding `validate` was stubbed. The fixture builds 1319 questions per run, original-byte evidence, provider infos with an actor field, and private report/budget paths. Fixture: `publisher_fixture.py`.

| Case | Result |
|---|---|
| Happy path | Publishes. The archive holds only the 5 expected members. The `decision.delta_count` of 31 equals my own count. No private path or actor is leaked. |
| Re-run | Refused, because the output already exists. |
| Oracle `state_sha` mismatch | Refused before any output is created. |
| One question missing | Refused before any output is created. |
| One raw byte changed | Refused before any output is created (`Artifact differs`). |

## Notes
- **N1 (recommended, cheap, not blocking).** Fallible steps run after `out.mkdir`. These are the field projections (`lifecycle[...]`, `release[k]['local_report_path']`), `archive_original` and `nc_result`. If any of them raises, a permanent partial publication is left behind, and the once-only rule forbids a whole-tool retry.
  - I reproduced this: provider infos without `created_at` produced a `KeyError` after `PUBLICATION_INTENT.json` and both run directories had been written.
  - With real Modal data every field above is present, so I expect the risk to be low.
  - The fix would compute all projections and the decision in memory first, then mkdir and write. If you change the bytes, re-request review. If you keep them, a partial publication needs its own recovery disposition.
- **N2.** `SPEC` is read from the working tree, not pinned. It is bound only by `original['spec'] == spec`, which means "the same as what was dispatched". I suggest also asserting `digest(spec) == 748a7ab0…`.
- **N3.** The publisher trusts `LOCAL_ORACLE_AUDIT.json` without checking its `schema` or the audit script's hash beyond the runtime-42 closure. The gz copy keeps the full `decoded` list, so A4 can re-check every verdict. I will do that at A4.

## NC progress (dated observation, d09b3ace)
Both runs started. Setup before the first block took **10.7 s and 14.2 s of worker time**, against the ~277 s headroom I flagged in cb, so that concern is resolved. The first 16-update blocks took 21.3 s and 26.4 s, against a historical maximum of 43.3 s. At 04:31:21 UTC, n400 had 304/1024 updates and n3200 had 64. On that pace training finishes well under the 4,500 s caps (05:38:58 and 05:43:56 UTC). The 21:12 PDT local lock-directory failure happened before any claim or call. Its reconciliation shows an empty campaign and zero scientific work.

## 科学信号检查 (science-signal check)
Still no outcome. No scores are in the packet, and none were computed.
