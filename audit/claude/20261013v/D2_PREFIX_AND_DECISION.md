# Claude audit 20261013v — p008-d2-parent-reconciliation-r1 @ 19bdf37b

Audited 2026-10-13 ~13:05 UTC at 277eb1c3. Method: the same device scripts as 20261013u, generalized as `~/aud/g1_pool.py <draw> packet <dir>`, run on the device copy of `pool_d2_reconciliation_v1`.

## Q1. Prefix reconciliation — **PASS (failed-parent prefix only; not a completed pool and not a G1)**
- **146 raw/scored batches, 3,992 outputs and 1,190,193 returned tokens.** All three match RECONCILIATION.json.
- **0 integrity failures.** I checked each D2 seed against `stable_seed('teacher',2,…)`, the prompt lengths and IDs, raw↔scored token IDs, completion tokens, and attempt prefixes.
- **D2 parent order:** the 6,973 eligible parents sorted by `stable_seed('question_order',2,id)` reproduce `frozen_wallets.parent_order` exactly.
- **Frozen-parser usable count: 3,509.** My parser gives 3,516; the 7 disagreements are all one-directional, with my parser accepting and the frozen parser rejecting. Of these, 5 are E1 percent cases and 2 are E3 "The answer is:" cases. This matches D1.
- **All 8 wallet prefixes replayed with my independent loop.** Action keys, every charge and total spend equal `wallet_events_reconstructed.json`.
  - b1 p0 breadth / b1 p0 depth / b1 p4 breadth / b1 p4 depth / b8 p4 breadth / b8 p4 depth stop legally at `cannot_reserve`. Spend is 91.9 / 94.1 / 85.1 / 92.7 / 99.0 / 99.3% of cap.
  - **b8 p0 breadth** is at 54.3% (146 actions); my loop stops because the next action needs 16 uncached attempts.
  - **b8 p0 depth** is at 52.6% (146 actions); the next action needs 12 uncached attempts.
  - The cache holds no partial next action, which agrees with the "zero pending intents" claim.

## Q2. Feasibility proposal — arithmetic correct, but **the predeclared window has lapsed**
- The proposal estimates 136 rounds × max normalized 41.1 s × 1.2 + 300 s = **7,070 s, against the 7,200 s cap**. That margin is narrow (1.8%) and it is an estimate, not a bound.
- At 2 wallets, each round runs about 4 checks. "Normalized" here means the parallel-guard read time is substituted for the sequential one. This is consistent with my 20261013q overhead model.
- **`latest_dispatch_utc` = 12:48:20 UTC has passed with no child code, review or admission.** Under the blueprint as reviewed, with the child stopping at 15:00 UTC, **the D2 continuation is now infeasible.** That follows Codex's own rule: no late launch and no extension.

## Coupling the owner must know about (this changes the options)
`student_plans.common_plans` requires the corpora of **both draws** before any plan is frozen. It also picks the realized target count T **jointly across draws**: it starts at the nominal count and steps down by at most 0.1% until every cell is feasible. As a result, **no D1 student can start under the current rules until D2 is complete**, and none can start if D2 is never completed. The rules were written this way to keep the draw comparison fair.

## Options for the owner (all of them outcome-blind; none is chosen here)
- **A. D1-only P008.** This is a scope change. Plans are frozen from D1 corpora alone, using the same common-T rule within D1; the 4-GPU queue then holds 7 T1/base jobs followed by 4 T8 jobs that pass the timing gate. **It is feasible today.** The cost is that there is no second acquisition draw, so draw-to-draw replication is not shown and must be reported as a limitation.
- **B. D1 now, D2 later with the same T.** This is a scope change plus a new child deadline.
  - D1 plans freeze now at D1's highest feasible T, using the existing search over the 0.1% envelope.
  - A D2 child is admitted with an owner-set later stop, for example 17:30 UTC (10:30 PDT). It needs its own code review, and its forecast must clear the 7,200 s cap with the 1.2 margin.
  - D2 plans must then use **D1's frozen T exactly**. Any D2 cell that cannot reach that T stays pending; T is never lowered after the fact.
  - D2 students run only if they fit before 02:00 UTC. Whatever does not finish is reported as pending.
  - Cost: up to $12 more, for a total reservation of $249.68.
- **C. Original joint design with a late child.** Every student would wait for D2 (around 16:30 UTC at the earliest). After that the queue holds about 38 GPU-hours on 4 GPUs, which **probably misses the 02:00 UTC hard stop.** I do not recommend this.

**My view:** choose **A as the frozen P008 result** and treat **B as an exploratory extension**, which may enter the PPT by Wed 18:00 PDT if it passes audit. Under B, D1's numbers do not depend on whether D2 succeeds, so the risk does not spread into the main result. The cost is a precisely defined loss of joint-T symmetry that has to be disclosed. P007B remains the frozen midpoint result whichever option is chosen.
