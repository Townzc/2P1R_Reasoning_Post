# E038–E039: paired-goal training did not improve the primary outcomes

Draft for the owner to review and send. Execution is complete; the next experiment below is a proposal and has not been run.

Both arms continued from the same E031 adapter for 256 updates (four epochs), with identical F replay and equal H-example counts. G-single trained one target per number group in two styles; G-paired trained both targets, one style each. The comparison therefore changes target/program support and repetition together. Evaluation used 48 new number groups, two targets each, with 36 skeleton families. All 3,344 registered generations were verified. [Execution and scope](SUMMARY.json), [training records](TRAINING_AND_REFERENCE_NLL.json).

| Outcome | E031 | G-single (E038) | G-paired (E039) |
|---|---:|---:|---:|
| H greedy: both targets correct, primary | 0/48 | 12/48 | 10/48 |
| H greedy: individual targets correct | 4/96 | 40/96 | 45/96 |
| F sampled: correct outputs, primary pass@1 | 1/384 | 14/384 | 13/384 |
| F sampled: targets with ≥1/4 successes | 1/96 | 13/96 | 10/96 |
| F greedy: correct outputs | 0/96 | 3/96 | 3/96 |
| C greedy: supplied expression calculated correctly | 89/96 | 92/96 | 94/96 |

G-paired minus G-single is **−4.17 percentage points** for H both-target correctness (95% paired group interval **[−16.67, +8.33]**) and **−0.26 points** for F sampled pass@1 (**[−2.60, +2.34]**). Skeleton-family intervals also span zero. These estimates show no observed paired-goal advantage, while remaining compatible with benefits or harms; they do not establish equivalence. F remains near the floor. Intervals use 10,000 paired resamples, seed 2026091708, retaining targets and samples within groups. This is one training seed, with no training-seed uncertainty or multiplicity correction. [Primary results](GOAL_SWITCH_RESULTS.json), [F results](FREE_CONSTRUCTION_TRANSFER.json).

Both arms largely learned the H scaffold: 95/96 and 96/96 greedy outputs follow it, but 55/96 and 51/96 choose the wrong hole operator. Improvements over E031 include shared H training, F replay, and extra optimization, so they cannot be attributed to paired targets. Prefix-conditioned operator diagnostics also disagree: G-paired improves the correct-versus-best-wrong margin by 0.492 nats [0.293, 0.707], but its target-conditioned preference shift, D_goal, is lower by 0.120 nats [−0.201, −0.039]. Unique correct argmax is only 30/96 versus 31/96. A favorable margin does not establish reliable target switching or free construction. [Operator diagnostics](OPERATOR_CHOICE_RESULTS.json).

Low reference loss has not become reliable generation. H response-token NLL is 0.0204/0.0248 on each arm’s own references; these are different reference sets, and aggregate loss does not isolate the decisive operator. On 16 stratified H-training groups, G-single solves 11/16 anchor and 6/16 countergoals; G-paired solves 8/16 each. Their F scores, 2/32 and 1/32, measure transfer on those H-training number groups—not free generation on the common F-replay training examples. This deliberately stratified diagnostic is not held-out accuracy. [Training diagnostic](TRAIN_SEEN_COUNTERGOAL_DIAGNOSTIC.json).

The complete C-error review adds a separate caution: all six post-training failures have locally correct equalities but alter the supplied program through reversal, substitution, or an extra operation. Local arithmetic consistency alone is insufficient. [All 13 failures and evidence](C_INTERFACE_ERROR_AUDIT.md).

**Most informative next step, proposal only:** a bounded, symmetric prefix-ablation diagnostic on exact supervised training prompts, comparing unprefilled generation with the reference prefix stopped immediately before the decisive operator, and measuring that operator’s loss separately. Include the common F-replay examples to fill the missing training-generation readout. This holds weights and data fixed while testing whether the failure already exists at the supervised decision or emerges with generated context. Any subsequent matched dose intervention should follow that diagnosis; these results do not yet motivate breadth or multi-seed expansion as the immediate next experiment. The present comparison establishes neither structural OOD nor an internal mechanism.
