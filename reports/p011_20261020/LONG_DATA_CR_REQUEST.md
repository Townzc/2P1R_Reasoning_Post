# P011 OT3/AM construction: one exact code-path CR request

Request `p011-OT3-AM-long-data-construction-CR-r1`; scope
`p011-OT3-AM-long-data-construction-CR`.

Fixed target: **eb728b30e6208ab081680b17cf28c7e2ad813322**. Packet: `reports/p011_20261020/long_data_preflight_v1`.
The owner directly supplied frozen plan e0dee182 and asked Codex to start. This
request covers the three-source construction path, not paid training or actual
A1 inputs. Production construction has not run. Please review the complete
SOURCE_BINDING/SOURCE_LOCK and packet README, including all six explicit
operational choices. Accept or correct them before the first real invocation.

Required line review: dictionary/list input schema; every local artifact's
producer/write line; native chat serialization and assistant mask; whole-parent
16-row filtering; decontamination; cross-source parent grouping; exact seeds;
paired D one-row selection before filtering; exact full-answer B/U and q/q+1;
create-only output/failure behavior. There are no remote output paths or endpoint
model loops in this data-only path. Model/runtime paths will have separate CR.

If accepted, report the exact three-source map and source_lock_sha256 from
SOURCE_BINDING, plan_sha256, target_commit, scope, decision and explicit
`operational_details_accepted=true`. A code PASS is not an actual A1 PASS.
A/D data counts and exact-dose feasibility will be submitted under this same
path's input-review chain after real completed construction. No per-cell request
is intended. Do not waive infeasible whole-answer dose or insufficient parents.

Validation: 11 initial checks passed, one native-tokenizer boundary check failed;
its bounded repair and single failed-check rerun passed; four new IO checks passed.
Original failure retained, no production filters or scientific model executed.
Raw D files downloaded and SHA-verified; OT3 acquisition is ongoing. No new
paid budget use. P010 completed work remains immutable and its scheduled
Oct21 12PDT freeze remains separate from P011 Oct21 22PDT.

Please keep this report free of Claude-owned P010 Z1 summaries/labels. Codex's
existing boundary-exposure record remains accurate; no new Z1 read occurred.
