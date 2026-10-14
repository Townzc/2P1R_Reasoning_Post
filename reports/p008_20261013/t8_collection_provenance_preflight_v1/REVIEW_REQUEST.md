# Public T8 collection provenance — L1 follow-up

Only the prepared per-T8 public publisher changes. The original publisher remains preserved at94eb84e6, the two read-only collection/recovery helpers remain exact4aadc204 (now PASS7034ad9d), and live35/CPU19 sources are unchanged. No actual collection, raw scoring, archive publication, model or cloud call has run. No old tests are repeated; the new source parses and archive creation/readback ASTs match the reviewed original exactly.

Please review the new metadata before MANIFEST is first written:
- Single-run collection is labelled only when no wave intent names this run. The completed envelope, stopped provider, local oracle, ledger and original mtime checks remain in the unchanged original body.
- A wave requires its actual per-run COLLECTION, common ledger SHA, named run list, READ_INTENT original envelope SHA and COMPLETED proof. Partial waves cannot claim a completed public collection.
- If a recovery directory exists, READBACK_VERIFIED must be present and passed, the saved original ConnectionError stays present, all4 original readback file SHA/size values must match the new export, and zero new model/remote writes is required. Only a bounded projection and proof/source hashes are published; original private intent/gates are not copied.
- Both routes produce public COLLECTION.json before the packet's one manifest. No existing immutable public packet is edited; the original archive paths and bytes/size/hash/readback implementation are unchanged.

Requested scope t8-public-collection-provenance. This only blocks using the new per-run publisher; does not block ongoing models, now-accepted collection/recovery, raw/state oracle, all19 analysis or finalCPU. Actual end-to-end source markers still require real complete results and G3.
