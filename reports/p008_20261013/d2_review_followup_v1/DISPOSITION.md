# D2 prefix/core review: acceptance and bounded follow-up

Claude report82b3d69a gives the failed D2 prefix PASS; report39caf811 gives the continuation core atc16ba8c8 PASS-WITH-NOTES. These scopes remain separate from a completed pool, merged G1, a runtime admission or an owner decision. No new cloud task, input upload, reservation or student plan is created here.

## Independent checks and corrections

- The next depth action contains16 candidates, **four already cached and12 missing**; breadth has16 missing. Both actions are unpublished and there are no unresolved original intents. “No pending action” must not be rewritten as “no partial cache coverage of the next action.” Reusing the four cache rows still requires committing the full original action and charging its full virtual cost. Those four answers must not be generated again.
- The actual feasibility expression is **1.2 × (136 ×41.11433975 +300) =7069.860247 seconds**. The report's displayed “...×1.2 +300” would give7009.860247 seconds. The stored proposal/result is unchanged and remains only an estimate with narrow headroom, not a runtime bound.
- We accept the joint-T coupling issue: the current plan builder cannot start D1 students while D2 remains incomplete. Freezing a D1-only T and later requiring D2 to match it is a different, asymmetric design, not an implementation-only optimization. It requires a direct owner decision, prior disclosure of the estimand and treatment of infeasible D2 cells, and real re-review. It has not been adopted.
- We do not endorse categorical feasibility or probability claims (“definitely times out,” “feasible today,” “probably misses”) as measured facts. The frozen18-student+base worker caps total141982 seconds, or39.44 GPU-hours; an ideal four-lane cap envelope is9.86 hours before dispatch/transfer/review overhead. This is not an expected runtime. Starting all students at17UTC leaves9 hours before02UTC, so a guarantee that every job fits its full cap would fail even before those extras. Actual faster completion remains possible; no new T1 timing exists yet. D1-only has fewer jobs but still needs actual plans, gates and review; its completion is not guaranteed.
- Use actual GitHub event and retrieval times in REVIEWS.json rather than approximate report header times.

The first local follow-up builder stopped before writing the packet because it looked for student configs that intentionally do not yet exist. The builder now reads the already frozen pool admission slot caps; the empty attempt and failure note are retained privately. No student preparation was run.

## Test invocation (Q3 addressed without changing reviewed production code)

From the repository root, using an environment with the project's CPU dependencies:

```sh
PYTHONPATH=.:tests python -m unittest test_p008_pool_prefix test_p008_pool_continuation -v
```

Alternatively, the original Codex continuation-only invocation was:

```sh
PYTHONPATH=. python -m unittest discover -s tests -p 'test_p008_pool_continuation.py' -v
```

The20-test total is Claude's12 continuation +8 prior-prefix tests. Codex previously verified those two groups separately. They are not20 new model calls or a fresh scientific oracle. No existing test or raw-output oracle was rerun for this documentation correction.

## Future worker requirements — accepted in principle, not implemented/admitted here

W1: the future worker must actually wire fresh ParallelActiveCheck into all original journal checks; a code import alone is insufficient. Per-unit atomic writes, limits and deadlines remain unchanged. Parent dependency checks must be included in its measured cost; the future actual key count cannot be assumed to remain26 after adding a child campaign.

W2: separate the local pre-dispatch full-window/source/review check from the worker's **pre-model** measurement. A child host does not exist before dispatch. An admitted worker may measure its complete required read set before loading the teacher, using a predeclared bounded sample count and conservative maximum; aborting there still consumes billed startup/runtime. Do not spin up an extra unadmitted probe GPU or repeat measurements until a favorable host passes. Rebase the existing full round-time proxy on the new read time, retain non-guard I/O and the300-second allowance inside the1.2 margin, and compare with actual remaining worker/deadline time. Generation plus guard time alone drops known other overhead. This remains an estimate, so the hard timer is mandatory. Exact probe parameters and numeric rule still need code and external review before dispatch.

W3: merged G1 must independently decode **parent raw + child raw**, with child batches starting at146 and originals never copied into child-return counts. The child's combined cache is not evidence of new physical generation. Preserve original failed parent status and both physical costs. Existing student/finalCPU bindings must accept the genuine lineage explicitly, never a synthetic completed parent.

W4: the expired original15UTC child cutoff, proposed extension and D1/D2 common-T policy remain owner decisions. No reply has arrived. No option is implemented or silently selected. Global19PDT compute stop and21PDT material freeze remain unchanged. P007B is already a complete audited midpoint evidence set.
