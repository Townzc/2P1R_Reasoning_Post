# P009 S1 first pair: registered futility stop, actual A4 pending

| Seed17 training set | Correct / 500 | Accuracy | Length caps (counted wrong) |
|---|---:|---:|---:|
| n400 | 273 | 54.6% | 36 |
| n3200 | 276 | 55.2% | 54 |

Both original once-only runs completed all1024 updates/2,097,148 targets and
500 frozen MATH endpoint outputs. Full raw/state/dose/source/forecast oracles
and frozen local scoring passed; both apps are STOPPED with zero owned containers.
The registered n3200-minus-n400 contrast is3 questions/+0.6pp, with91 discordant
questions. It is below the original2pp futility threshold. The original decision
function was run once and returned `stop_registered_futility`. No remaining S1
slot or Stage2 call is admitted; actual independent outcome A4 is still pending.
G1 and its bootstrap were not run. No additional seed, model, dose or label change.

This is a stopping decision for this registered setting, not evidence of
equivalence, a capacity limit, a stable zero effect or a pure mechanism. Training
data exposure and coverage vary at fixed targets; seed17 is a single joint data
permutation/training realization. S2 remains excluded by its original cap failure.
The already accepted NC pair was954/967 of1319 and did not trigger its5pp stop.
HF historical endpoints are excluded from all P009 effects and gates.

The fixed sample rosters contain25 and22 disagreements respectively: all available
disagreements because each is below50. Neither endpoint has a fallback sample or
an outer-timeout pair. Original Boolean labels and null adjudication fields are
preserved until the independent review; no Codex adjudication is fabricated.
The stored boxed denominators are copied evidence, not a fresh extraction.

[Original paired decision](../stage1_s1_first_pair_v1/REGISTERED_FIRST_PAIR_DECISION.json),
[n400 complete evidence](../stage1_s1_results_v1/s1_s17_n400/README.md),
[n3200 complete evidence](../stage1_s1_results_v1/s1_s17_n3200/README.md),
[actual A4 request](../S1_FIRST_PAIR_ACTUAL_A4_REVIEW_REQUEST.md).
All original raw, checkpoint identities, full local scoring journals, failures,
provider projections and source bindings are retained in those immutable packets.
A public checkpoint SHA is not a claim that an external reviewer read the private
binary. Private originals remain; nothing has been deleted or re-generated.

At10:11:06UTC the two completed S1 applications total$4.02358019 in delayed platform
metering. Workspace gross metering is$246.90239056, billed cash$0. These are not a
final invoice or remaining-credit balance. Prior failures, build/setup/storage and
lag are retained;655c per-slot reserves are not actual expense. See
[observed cost and original snapshot hashes](OBSERVED_COST.json).
