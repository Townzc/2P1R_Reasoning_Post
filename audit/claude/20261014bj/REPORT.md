# Audit 20261014bj — Plan A P0 result publisher (code only)

- Request: `p009-p0-fast-result-publication-code-r1`
- Target: `fe8a6bcc60b1fee23336f9fb39ae10ed8053f370`
- Manifest: `reports/p009_20261014/p0_fast_publisher_preflight_v1/MANIFEST.json`, SHA-256 `ad44dcb69f76e2c8716c2a425ce335f0ceff5710f4549a3aaef88ddff5f3a1f6` (matches)

## Verdict

**PASS-WITH-NOTES.**

- **Create-only:** the archive is opened with `xb`, and there is no delete or overwrite path.
- **Input checks:** the oracle must report `inherited_outputs == 0` and `old_reference_rescored == False`.
- **Old rows and HF reference:** the 128 eager rows are recorded as retained and unscored, and are not included. HF outputs are not re-scored.
- **Actual-result A2:** marked PENDING.
- **No computation:** the publisher runs no model, scoring or parity computation.

## Note

Archive readback and the evidence guards execute only at real publication. My A2 will replay all 2,638 raw rows independently, whatever the publisher reports.
