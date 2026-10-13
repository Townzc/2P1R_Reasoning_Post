# Blocking local provider lookup amendment only

The exact child G0 at a385fb38 received Claude PASS-WITH-NOTES at a32454b5. Before upload, the actual provider CLI `app list --json` returned [] because its documented scope is running/deployed/recently stopped apps. The old preflight therefore refused before UPLOAD_INTENT, any upload, cloud image or model call. Original failure log is preserved.

Exact `modal app info <original-ID> --json` now confirms D1 stopped05:20:23PDT and D2 stopped05:24:52PDT. Current container list is empty. This amendment replaces the local recent-list lookup with exact-ID lifecycle queries. Missing/foreign/unknown/active records, missing stop time, any container or API error reject. No synthesized stopped rows and no claim bypass. Eight new adversarial CPU checks passed; old tests/oracles were not repeated.

Please review ONLY the new provider_release.py plus local main() change and the31-file binding. Worker work() AST is byte-structurally identical; all numerical scope, plan/config, probe formula (including double-counting), guard, timer, generation, oracle, budget and owner deadlines remain unchanged. N1 parent13.72s metadata check is retained; real billed child probe stays binding. v1 is immutable; this new v2 ADMISSION changes only source_files. New scoped PASS must bind v2 source/spec before upload/dispatch. Latest full dispatch17:48:20UTC remains; no extension or shortened cap.

The amended upload helper is local-only and follows the same exact-ID check; its initial attempt did no remote writes. Student/finalCPU gates are independent and do not block this lookup amendment. No students admitted.
