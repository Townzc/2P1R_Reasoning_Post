# Verified status

## Engineering implementation — 2026-09-05 UTC
- Public repository initialized and CPU fixture reproduced byte-for-byte.
- 35 tests pass on the training server, including loss normalization, isolation and budget enforcement.
- Debug model: all nine cached files verified against official file identities at the pinned revision.
- Real tokenizer audit completed: 128 presentations per arm yield 7676–8156 supervised response tokens, so these fixtures are not matched-budget comparisons.
- Training/evaluation, raw-output recording and bounded runtime are implemented; GPU execution is next.
- User-approved initial budget is 7200 GPU-process seconds. No scientific comparison has run.

See VALIDATION.md, cpu_reproduction.json, token_audit_debug.json, environment_4090.json and ../docs/CLOSEST_WORK.md. The global-coverage exposure allocation and expanded data domain still need a concrete reviewed proposal before scientific treatment comparisons.
