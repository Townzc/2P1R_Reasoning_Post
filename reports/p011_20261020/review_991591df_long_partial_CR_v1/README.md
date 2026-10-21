# Long A/D source review: input permission only; runtime changes required

Observed 2026-10-21T06:13:08.178650+00:00. Original fixed report at claude/audit991591df, Git05:31:17,
self-described around06:10, full read06:01:53 recorded separately. The report
explicitly passed only original input preparation. R1 source closure, R2 full
checkpoint memory and R3 endpoint batching require correction. R4 bounded GPU
preflight and A/D D1 obligations need separate decisions. No full runtime/A2
acceptance exists. Original raw report remains private; the public projection
omits one account-availability paragraph and binds its full original SHA.
The one authorized CPU input invocation subsequently failed; see the sibling
long_input_failed_preservation_v1. The original permission cannot authorize retry.
