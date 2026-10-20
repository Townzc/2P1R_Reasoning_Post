# Actual E3/C6 A3 and early Z2 A5 dispositions

Recorded 2026-10-20T14:28:40.078124+00:00. All three fixed Claude reports give PASS-WITH-NOTES. Their targets,
manifest hashes, original report hashes, actual commit events and read-confirmation
times are bound in REVIEWS.json. Approximate times printed in the reports are not
used as observation times.

- E3: 3,200 new rows, 1,600 reused rows and the saved descriptive metrics accepted.
- C6: all 21,371 rows, retained failed-parent lineage and all eight paired results accepted.
- Z2: early Codex-owned assembly accepted with 73/77 trace sources independently
  verified. Four local-only sources remain unverified by the reviewer. Final freeze A5 is outstanding.

The [dated technical notes](../post_audit_technical_notes_20261020_v1/README.md) provide required field
definitions and parser-sensitivity disclosure without altering original data.
Original reports are linked in REVIEWS.json; original bytes remain preserved.

The A5 file unexpectedly contained a Claude-owned Z1 section. Its initial display
exposed that material; BOUNDARY_EXPOSURE.json records this failure of separation.
No original Z1 artifact was opened. The public projection excludes that entire
section, and no Codex acceptance of Z1 or of the author's checks is asserted.
Completed C7 is not repeated. No model, scorer, statistic or renderer ran here.
