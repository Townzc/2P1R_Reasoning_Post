# CFT reproduction contract — not executed

This pilot does not run CFT annotation or CFT training. CFT is an unmeasured direct comparator; no pilot outcome establishes superiority to CFT. Checked against the fixed [CFT paper v1](https://arxiv.org/html/2510.10974v1), retrieved 2026-09-17.

The paper starts from correctly answered greedy model trajectories. For each position it substitutes alternatives ranked 2 and 3 (`k=3`) and continues greedily. A token is selected only when both substituted continuations fail the final-answer judge. Equation 8 divides masked cross-entropy by the count of selected critical tokens. These are different data and loss contracts from QDW's frozen question-ablation score and full-response training. [Sections 3–4](https://arxiv.org/html/2510.10974v1).

The inspected paper and focused source search did not establish an accessible author-linked annotation implementation or released annotations. This is a bounded retrieval result, not proof that none exist. The paper's general OpenRLHF and Qwen evaluator links do not identify its annotation code. Exact rollout length/stop settings and implementation-level edge cases remain unverified; do not invent them.

Before any later execution, freeze the following unresolved items:

| Item | Required evidence |
|---|---|
| Source and annotations | Author implementation commit, file hashes, license, annotation dataset revision and model identity; otherwise explicitly label a new paper-based implementation. |
| Correct-trajectory subset | Exact prompt, initial greedy decoding, answer extraction/judge, complete counts, failures and selected question IDs. |
| Perturbations | Rank-2/rank-3 candidate token identities, ties, eligible positions, treatment of special/end tokens and all counterfactual prefixes. |
| Rollouts | Frozen greedy continuation limit, model context limit, stop IDs/strings and tool policy; insufficient-budget rollouts remain incomplete. |
| Labels | Per-alternative raw completion and answer judgment; both alternatives required before labeling critical. |
| Loss | Critical-token denominator over the optimizer update, zero-critical-row/update policy, masks and gradient checks. |
| Cost | Initial greedy outputs plus two continuation attempts per eligible position, actual generated tokens/forwards, retries, wall time and storage; runtime on this model/hardware is not yet measured. |

The fair follow-up is a separately authorized and frozen comparison on one common correctly solved trajectory subset: rerun SFT, DFT, TrimSFT, QDW and CFT with matched data and optimization budgets. Do not rank methods trained on different filtered rows. Do not rename QDW masks, or hard CE on those masks, as CFT. The current 4,096-question pilot's budget does not authorize this follow-up.

The source paper HTML was frozen with SHA256 `17c4ae24b7d74245382618282f44b5c5054341ef4a2eb843b2d96a82fa506e27`. No model-specific annotation-cost estimate or reproduced CFT score is asserted.
