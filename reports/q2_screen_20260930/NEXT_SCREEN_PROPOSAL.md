# One final control-completion screen — proposal only

September 30, 2026. No startup, model work, dose amendment or new spending is
authorized by this document. The old queue is closed. The earlier C-repeat
question remained unanswered; the old four-hour window must not be extended.

## Scientific decision

Keep the original question: after a supervision-data upgrade, retain the weakly
supervised weights or return to the original model, under equal future training?
Use a stronger-supervision history to separate this from simply training more.
The current 46.48 → 49.22 → 49.02% trajectory does not answer that question.

## Repair before admission

1. Diagnose the saved initialization and suite-timeout cases, retaining every
   original result. Separate candidate test-limit violations from outer worker
   timeouts; unresolved outcomes must stay unknown. Do not change the tests or
   labels merely to permit training to finish.
2. Pass authored CPU tests, then a bounded Linux regression on the exact saved
   cases and previously known verdicts before GPU work. The failed suite-watchdog
   opt-in remains prohibited. A Linux check may require the next owner-started
   session; all such time counts against that session's cap.
3. Reuse the completed W weights only if the scoring intervention remains
   comparable. A change to effective reward semantics requires a new reviewed
   protocol; do not mix new C/R rewards with old W and call the contrast matched.
4. Preserve per-update commit evidence, safe checkpoints and all raw rollouts,
   including backend sampling log-probabilities. Checkpoint presence is not exact
   sampler recovery. An ambiguous failure must not trigger blind replay.

These are preparation gates, not a claim that the repair is already solved.
If they cannot be passed promptly, spend no additional GPU time on this screen.

## Conditional finite queue

Reuse the already completed W_prefix/W_future states and evaluations. Keep the
same pinned model, 250/128 task split, schedules, seeds, optimizer settings and
128-update phase length. Do not extend training to search for a negative effect.

| New phase | Reward | Updates | Training outputs |
| --- | --- | ---: | ---: |
| Fresh C_prefix from original R | Base AND extra | 128 | 2,048 |
| C_future from C_prefix | Base AND extra | 128 | 2,048 |
| Fresh R_future from original R | Base AND extra | 128 | 2,048 |
| **Total** | | **384** | **6,144** |

Evaluate C_prefix, C_future and R_future on the original 128 tasks × eight samples:
**3,072 additional evaluation outputs**, for **9,216 total new outputs**. The
failed C100 and R25 attempts remain separate overhead; do not relabel the proposed
fresh starts as exact continuation. This is one paired replicate completed across
sessions, not another independent seed. No old evaluation is regenerated.

Measured successful training phases took about 23–24 minutes each, and evaluation
phases 11.5–16.6 minutes each. A nominal roughly two-hour workload suggests a
**2–3-hour powered window, hard cap three A800 hours** including admission,
diagnostics, repairs, collection and shutdown. At the previously observed
CNY7.98/hour this would cap compute at **CNY23.94**, excluding storage; verify
the live price and resources before admission. This is not an A100-equivalent
estimate or an extension of the closed run. Any necessary recovery reserve must
fit inside the cap. No automatic rental, restart, extra arm or seed is proposed.

## Decide once the controls are available

Report W_future−R_future, W_future−C_future and C_future−R_future together.
Retain the original pilot priority pattern: W_future at least 3 pp below both
alternatives, while C_future is no more than 1 pp below R_future. A matching
pattern warrants an independently trained replication proposal, not a confirmed
mechanism or an automatic new run.

If W<C but W≥R, weak-history weights still have positive future value: this is
not a case for restarting from R. If W and C both trail R, general additional
training is an alternative explanation. If differences are small or imprecise,
deprioritize for the current project rather than extend doses, hunt seeds or
claim that all supervision-history effects are absent. Preserve other outcomes
without rewriting the original hypothesis after seeing them.

## Office Hour discussion, still provisional

Bring the three-state table and explicitly missing comparisons. Ask whether the
checkpoint-retention decision adds a worthwhile data-centric question beyond the
nearest verifier-quality and reward-switch studies, and whether the C history
is an adequate control. Industrial relevance is the cost of retaining versus
discarding training after acceptance criteria change; applicability beyond this
small model and benchmark is unproven. If that contribution is too narrow or the
remaining control is uninformative, ask which adjacent question deserves a new
novelty/asset audit. Do not present an unaudited backup as a ready replacement.
