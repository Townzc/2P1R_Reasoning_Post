# P011 OT3/AM revised shared-path CR request

- Request: `p011-OT3-AM-long-data-construction-CR-r2`
- Scope: `p011-OT3-AM-long-data-construction-CR`
- Exact candidate: `df4d590485a2bb6b8cb2eeb02e8688f64ebd03db`
- Packet: `reports/p011_20261020/long_data_preflight_v2`
- Manifest SHA256: `c8648dde2563e098c753a18a0980882d8264c36ece615bab58d245129b442242`
- Original frozen plan SHA256: `20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22`
- Unchanged source-lock SHA256: `0e78298f49b86ee3de7182443eb052da422d14af14f423bceb3f728a1696fdb0`
- Direct owner amendment SHA256: `e58e8d721f740e438d82ef3f5e6ecea50970e3b507458ad3d77e07eacfe75c72`
- Exact proposal SHA256: `f8d5816e362aa3ddc7108676f118af85cd6ccf3405cad6757c7f973521ea7756`

The direct owner adopted R1/R3 after reading Claude's CHANGES-REQUIRED, before
production selection or outcomes. See original owner text and retained proposal
in the packet. The r1 candidate remains unattempted; no false acceptance exists.
Please review the requested changes against efa4a7a8 and the exact3source mapping
in SOURCE_BINDING.json: maximum once-dose, independent complete passes plus
extras, shuffled candidate-prefix OT3/AM loops without a second shuffle, prefix
statistics, full-common-source metadata counts, disk check and owner binding.
Eight new tests passed once; old successful tests and production were not run.
All120 OT3 source hashes and both original AM files are complete/verified.

A passing fixed report must explicitly bind exact target, scope, source_files,
source_lock_sha256, plan_sha256, owner_amendment_sha256, proposal_sha256 and
operational_details_accepted=true. This is one shared data-only CR, not model
runtime or actual A1. Complete actual inputs receive A1 afterwards. Future
commands are in the packet. No new request to approve the already adopted scope.

Please keep this report entirely non-Z1. The report header22:45UTC in r1 was
later than its actual commit22:20:10/read22:21; original bytes are retained and
actual commit/read times are used rather than treating that header as an event.
