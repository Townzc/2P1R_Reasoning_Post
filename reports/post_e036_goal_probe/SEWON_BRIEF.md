# Thursday research brief — draft for the owner

The previous E031–E036 study is complete. Its compute-parent manipulation did not
establish selective readiness, and its interaction remained inconclusive. We
therefore tested four frozen endpoints with no additional training.

We froze24 new number groups, each paired with two targets requiring different
operators in the same one-hole expression. F asks for a free solution, H gives
the skeleton, and C evaluates its completed expression. We retained greedy and
the existing four-sample decoding for F/H:2112 total generations.

| Endpoint | F sampled | H sampled | H both-target pairs | C greedy |
|---|---:|---:|---:|---:|
| C-S |5/192|33/192|2/96|43/48|
| C-P |8/192|41/192|2/96|45/48|
| B-S |6/192|43/192|2/96|44/48|
| B-P |8/192|42/192|1/96|47/48|

Providing a skeleton improves sampled accuracy by14.6–19.3 percentage points,
with positive exploratory group and skeleton-cluster intervals. Yet correct
switching between both targets remains rare. The96 sampled pair outcomes per
model are nested in24 independent number groups, not96 independent problems.

Forced-prefix local scoring shows a small directionally appropriate goal effect:
mean paired log-odds shifts0.35–0.59 nats, with positive intervals in all four
models. This still produces only13–16/48 correct unique operator argmaxes and
0–1/24 groups with both targets ranked correctly. Target sensitivity and correct
choice are different observations.

Failure inspection separates interface and decision errors: of960 H outputs,
257 retain the hole symbol, while368 preserve the template but choose the wrong
operator. C's13 errors include12 traces whose local equations are true but whose
program deviates from the supplied expression. We should not call this only an
arithmetic problem, only an output problem, or a pure internal search mechanism.

The actual main SFT data has one target per number multiset, despite one versus
two ordered programs. An ancestry audit corrected a preparation-report error:
E030 calibration is not ancestral to these endpoints. Correct endpoint support
is768 source rows/512 number multisets, all single-target; the frozen erroneous
superunion is preserved with a separate correction.

**Proposed next step, not executed:** compare G-single and G-paired from the same
prespecified E031 checkpoint on the same256 new number/skeleton groups and512
rows, using a common full-expression completion format. Match operator roles,
renderings and report token residuals; keep128 updates and test new paired goals
plus transfer to new free construction. This is a data-recipe comparison that
changes target/program/repetition support together, not an isolated mechanism
claim. Independent fresh-group confirmation should precede stronger claims or
additional seeds. No novelty claim follows from this diagnostic.

All outputs are verified, the server is off, and work is paused for owner planning.
This file is a draft research brief only; no external message was sent.
