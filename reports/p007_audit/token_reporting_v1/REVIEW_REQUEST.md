# Round4 R1/L1 response: offline reproduction and endpoint reporting

Scope: verify the lazy import in `scripts/plan_real_math_scale.py` and the explicit stop-count checks/report columns in `scripts/audit_token_student.py` and `scripts/summarize_token_students.py`. Frozen runtime code, inputs, plans,512-token generation bound and incorrect-score rule are unchanged; no model calls. The active eight-student queue has no complete corrected outcomes in this packet.

R1: public schedule replay now runs with `python -S` (site packages disabled), no pyarrow or fake module. All eight admitted plan digests remain identical.

L1: the local oracle derives every stop count from saved records, retains all capped answers in the denominator as incorrect, and rejects changed count/denominator or a capped answer scored correct/unknown. The results include counts/fractions per cell and seed plus both-seed totals. Eleven focused CPU tests pass. Count-only reuse of already-verified original-pilot files confirms38/1319 and33/1319 length-capped outputs. No prior immutable audit or packet was rewritten.

See `CHECKS.json`, `PUBLIC_REPRODUCTION.json`, `PILOT_STOP_COUNTS.json` and `manifest.json`. The fixed [Claude round4 report](https://github.com/Townzc/2P1R_Reasoning_Post/blob/730e7d06885bf853fb9fcb1afac2aef83d5fc7d1/audit/claude/20261012d/REPORT.md) covers earlier v2plan reproduction and original-pilot outcomes; its PASS is not inherited by this follow-up. New eight outcomes remain pending.
