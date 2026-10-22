# CR: ext-3B local endpoint-link closeout correction (ebfea411, request 3901ec6f) — **PASS**

Reviewer: Claude, 2026-10-22 ~15:55 UTC. I read `experiments/p011/local_endpoint_link_verify.py` and `scripts/p011_ext3b_local_link_closeout.py` in full.

- **Cause.** The large cell's first local audit (39311) failed with "Artifact differs: ENDPOINT_GPU.json". The generic `verify` rejects symlinks. The two endpoint links were deliberately created by the reviewed prefix constructor (see my CR 1901fcf7: "Endpoint files are symlinks to the accepted originals"). The failure happened before any state, optimizer, RNG or trajectory oracle and before any decode, so it is a pre-science failure.
- **Fix.** `verify_inputs` accepts exactly `ENDPOINT_GPU.json` and `ENDPOINT_LOCAL.json`, and only under these conditions:
  - each must be a symlink that resolves to the prior-input file;
  - that prior-input file must be a regular file, not itself a link;
  - its size and sha must match the manifest record.
  
  Every other file still goes through the original `verify`. Nothing is materialized or re-encoded.
- **Large cell.** The large cell reuses the successful pre-failure steps (extraction, identity/timing/journal checks, and the first three input files), but only after `reuse_large_prefix` confirms all of the following:
  - the failure is exactly the endpoint error recorded in FAILED.json;
  - the CLI exit code was 1;
  - no COMPLETE_PROOF, SCORING_ROWS or DECODED file exists;
  - the RESULT and receipt shas match;
  - attempted and done are read from the saved derived ledger.
  
  This is a valid continuation, not a replay. The failed audit directory is preserved.
- **Small cell.** The small cell runs its first full oracle: extraction, identity, admission and timing checks, and `scope.journals`. Running it again is impossible because the audit directory must not already exist.
- **Science is unchanged.** The following are all unchanged: the state/optimizer/RNG/trajectory oracle, the native decoder (`scope.endpoint`, which requires all 2,500 outputs), the frozen scalar pool via `score_process.supervise_once` plus `verify_saved_scores`, and `paired_question_interval`/`greedy_interval` with 10,000 draws and seed 20261021. The analysis passes [SMALL, LARGE] in that order, so the reported contrast is LARGE − SMALL, consistent with the forced-answer analysis convention.
- **Controls are unchanged.** These are all retained: the absolute closeout window and score cap (min of 7,200 s and the remaining window), the `fcntl` concurrency-1 lock for audits, the once-only output fences, no automatic retry, no new model, upload, encoding or budget, and the requirement for an actual A3.

All nine flags are **true**.
