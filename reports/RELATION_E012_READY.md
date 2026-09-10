# E012 ready for an owner-started A800 — 2026-09-10 UTC

The finite diagnostic execution release is published and independently checked
from a clean checkout. **No E012 model run has occurred.** The next requirement
is an available owner-started A800 80GB, followed by server verification and
the first bounded lookup run. Max is appropriate for this implementation,
execution and evidence-audit task; the owner reported switching to Max.

## Why this experiment follows E011

[E011](RELATION_E011_RESULTS.md) completed all 256 updates but produced **0/32
complete train proofs** despite mean target NLL 0.11939. Every one of its 333
parseable generated after-states was 2. There was no OOM, nonfinite gradient
or shortened dose. These observations show a failed engineering gate; they
do not establish a unique cause or justify an ICLR-level learning claim.

[C016](RELATION_C016_CPU_READY.md) retained the same 32 train and 16 observed
development parents and froze three diagnostic views, their exact targets,
orders, token masks and dose. This avoids selecting new examples after seeing
the failure. The stages progressively add work, and stop at the first failed
complete training gate:

| Stage | Question | Train / dev rows | Continuation requirement |
| --- | --- | ---: | --- |
| Single-step lookup | Can the fixed recipe learn an individual exposed permutation-table operation? | 128 / 64 | All 128 train proofs correct, covering all four operations of every parent |
| Given-route propagation | Can it retrieve edges and propagate states along a supplied route in the original graph? | 32 / 16 | All 32 train proofs correct and following the supplied route |
| Fixed-reference full task | Can it learn the original question when one consistent reference is repeated? | 32 / 16 | All 32 train proofs correct; any legal route accepted |

Each stage starts from the fresh pinned Qwen2.5-1.5B base and trains for 256
updates. Every gate also requires EOS, no train-output truncation, reference
NLL below .2, complete finite measurements/profile and an independent raw-output
audit. A small mean loss or correct final answer alone cannot pass. Prior compact
outputs and a verified independent checkpoint backup must be published before
the next stage. The frozen [registration](../docs/experiments/E012_relation_diagnostic_ladder.md)
contains exact controls, run IDs, commands, stop rules and interpretation limits.

This is a diagnostic ladder, not a causal comparison across the three tasks:
prompt/target length and per-operation exposure differ. Only the full fixed-
reference condition matches E011's exact prompt, parent/update order and total
token dose. Its assigned-reference NLL also differs from E011's four-reference
average. Development has already been observed and shares 34 tables and 13
table/input operations with lookup training. No unseen-table generalization,
independent final-test result or route-diversity treatment effect is established.

## What is implemented and verified

- A default-inspect launcher, one-stage bounded training worker, exact dose and
  source binding, current-ledger checks, and ordered continuation gates.
- Raw output IDs and strict proof/answer/EOS checks. Valid model-vocabulary IDs
  with no tokenizer entry remain explicit failures even if text decoding omits them.
- Per-token teacher-forced CE and top-one predictions, partitioned by semantic
  field, with after-state positions recorded separately from free generation.
  The auditor rechecks alignment and scalar consistency; it cannot reconstruct
  original model logits from scalar measurements.
- Complete and incomplete runs have distinct records. A completed learned
  failure stops continuation; infrastructure failure keeps partial artifacts
  and its receipt. No automatic retry, shortened fallback or seed search.

**76 checks pass; 2 GNU-timeout integration checks require Linux.** The complete
78-test suite was rerun in a clean published checkout (6.579 seconds), with
zero failures and only those two explicit skips. The default inspection also
passed there. No pretrained weights were loaded, server contacted or budget
reserved. Original and copied private ledgers stayed byte-identical.
See [verification receipt](relation_e012_fresh_checkout_verification.json),
[test log](relation_e012_fresh_checkout_tests.txt) and
[inspection output](relation_e012_fresh_inspection.json).

The registry and aggregate compute summary were found stale at 15 receipts /
5740 seconds. They have now been reconciled from all 16 immutable public
receipts, including E011's 231 seconds and explicit failed learning gate. The
private ledger was already correct and was not changed. This corrects record
maintenance; it is not new computation or a newly successful experiment.

## Published identities and resource plan

- Execution source publication: `1fc27d459c8445417e3db73d944a7d2c7c064ffd`.
- Immutable release publication and clean verification checkout:
  `27a0943fef352e67072e8b2d7db36a3259524246`.
- [Release](../configs/relation_diagnostics_e012/release.json) SHA256:
  `beb536bbea21354c37a2336fc6d6b99f2fbf7f92ad9102109cc2bf393df38749`.
- Unchanged C016 data manifest SHA256:
  `cb923a3e11817682f77b4116d7524e615bdffee29e04e5848b3815352aa8133e`.
- Current ledger: **5971 / 7200 process seconds used, 1229 remaining,
  16 receipts, zero reservations**. Private backup SHA256:
  `664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.

Each stage has a 360-second process cap plus 15-second guard. The entire
conditional ladder reserves at most 1125 seconds, leaving 104. These are caps,
not promised runtimes; idle rental, setup and backup transfers are separately
billable. No new allowance, paid API, extra machine or storage expansion is
included. The last provider-confirmed server state was stopped after E011;
availability has not been rechecked in this CPU phase.

On the supplied server, synchronize the independently verified current GitHub
commit, restore the current ledger, check the pinned original model/environment,
one idle A800 80GB and at least 12 GiB free after setup, and pass the two Linux
watchdog checks before `single_step`. Measure actual disk availability; if
space is insufficient, assess only independently backed-up redundant artifacts
and tell the owner if expansion is needed. See [current handoff](../docs/NEXT_SESSION.md).

## Record locations and next decision

The repository keeps the [research journal](../docs/RESEARCH_JOURNAL.md) for
questions, motivation, design, outcomes and analysis; [decisions](../docs/DECISIONS.md)
for changes in direction; [status](STATUS.md) and [handoff](../docs/NEXT_SESSION.md)
for the current next action; and [artifact inventory](ARTIFACTS.md),
[registry](run_registry.json) and [accounting](compute_accounting.json) for
durability and cumulative execution. Immutable raw outputs will be saved under
the registered `runs/relation_*_e012_r1` directories only when a stage actually
runs. Checkpoints and the live ledger remain outside Git.

If lookup fails, analyze its raw lines and semantic fields before proposing a
redesign. If it passes, preserve and publish before the given-route stage.
Even if every stage passes, a new scientific control design and independent
groups still require review before claiming progress toward an ICLR result.
