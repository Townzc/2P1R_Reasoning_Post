# Modal next-batch hard stop and proposed accounting correction

Current observed balance: **$48.21**; protected balance: **$4**. Completed-cost accounting plus existing inflight reservations: **$46.1770**. The next four frozen Llama pass@8 endpoints (500 questions x8, unchanged) forecast **$2.7450**, including measured slowdown and margin.

Under the literal approved A4 rule, **$46.1770 + $2.7450 = $48.9220 > $44.21**. The next batch is therefore STOPPED and unsubmitted. Already-admitted original calls continue; Tinker is independent.

The formula subtracts prior paid costs again by comparing cumulative cost to a remaining balance. Proposed correction, requiring owner approval:

1. Cumulative accounted costs + inflight reservations + the next buffered batch must remain <= **$85**.
2. Unsettled/inflight reservations + the next buffered batch must remain <= **actual balance - $4**.

This changes neither the $85 spending cap nor the $4 protected balance and adds no credits. Using a deliberately conservative unsettled upper bound of **$30.3802**, the corrected checks are **$48.9220 <= $85** and **$33.1252 <= $44.21**. The upper bound even retains the entire earlier $20.634 reserve as potentially unsettled; only attributable closed-period per-app charges are deducted from later reservations.

`RECONCILIATION_AND_PROPOSAL.json` contains every later run, known closed billing, runtime/reserved cost, the four unchanged pending endpoints and both calculations. The November13 21-22UTC billing window was read once and is not treated as a final invoice. No rule change or new call is executed before the owner decides.
