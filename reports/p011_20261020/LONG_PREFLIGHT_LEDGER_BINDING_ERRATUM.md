# Dated clarification of the failed-ledger source map

Written 2026-10-21T09:44:02.935517+00:00. Original immutable candidate target38942d3a9380030d3ad885dfe46b6cfb377aad00 is unchanged.

In long_preflight_failed_ledger_runtime_v1/REVIEW_REQUIREMENTS.json, the top-level `source_files` field was inherited from the original33-source request. It is historical and is **not** the new candidate map. The exact candidate has37sources. The following three maps agree exactly and are authoritative for the narrow review:

- `SOURCE_BINDING.json.source_files`
- `SPEC.json.source_files`
- `REVIEW_REQUIREMENTS.json.binding.source_files`

The original33 are unchanged; the four additions are failed_attempt_ledger.py, long_preflight/failed_ledger_path.py, long_preflight/modal_failed_ledger_entry.py, and scripts/p011_long_preflight_failed_ledger_io.py. The runtime reviewed() function compares the actual SPEC source map, not the inherited top-level field. A report accepting only33source cannot admit these new wrappers. Please explicitly accept37source plus the exact SPEC/binding and11flags already requested. No new scientific scope, dose, window, test, model or input is introduced; no immutable packet is rewritten.
