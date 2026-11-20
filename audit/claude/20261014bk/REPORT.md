# Audit 20261014bk — Plan A P0 read-only status and failed-preservation helper (code only)

- Request: `p009-p0-fast-readonly-code-r1`
- Scope: `p009-p0-fast-readonly-observation-and-failed-preservation-code`
- Target: `52972cfa9c73d1ea2ea3261bb1ffe505c826d70b`
- Manifest: SHA-256 `48de0ee25d3a1901fb37ccc35ecba011753f5bbcd2a34f2de7cae3912e5d5003` (matches the request)
- Script SHA claimed by the request: `009874616e16e47fbfab1a5c481257f1e2d5cb503dba299f3d505dca014c5b8e`

## Verdict

**PASS-WITH-NOTES.**

Both actions are read-only toward the provider and create-only locally.

- **`status`** reads 29 known Dict keys with at most 2 readers, `modal app info`, `modal container list` and local callback hashes.
- **`preserve-failed`** first requires a failed terminal, plus claim and marker binding, plus a STOPPED / zero-owned-container proof. It then copies the failure evidence into a create-only directory (`xb` / `x`), journaling and fsyncing each file. Bounds are 512 files, 32 MiB per file and 256 MiB total. It refuses an unclassified hard-killed worker instead of guessing.

**What the code does not do.** It has no delete, overwrite, remote write, model replay or scoring path. It does not enumerate or score raw outputs. A partial preservation directory blocks a whole-helper retry.

## Notes

- **Status timing.** Status is explicitly non-atomic; treat it as observation only. The helper never replaces the completed-only collector or my independent 2,638-row A2 replay.
- **Testing.** The 4 pure tests do not exercise real Modal RPC, so the first real use is also its first integration test. If any read errors, record it as unknown; never convert it into a classification.
