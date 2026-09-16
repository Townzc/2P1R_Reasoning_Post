# Post-E030 arithmetic continuation: offline analysis

Status: **all_registered_outputs_verified**. All reported primary metrics use the original strict scorer.

Completed views: 30/30. Unique completed results: 4768/4768; charged attempts: 4784/4864 (includes the original16 fault attempts).

The original576 completed outputs are reused once. Missing cells and incomplete views remain unmeasured.

| Discovery measure | C-S | C-P | B-S | B-P | Interaction |
|---|---:|---:|---:|---:|---:|
| discovery_sampled/pass_at_1 | 0.0755 | 0.0677 | 0.0938 | 0.0417 | -0.0443 |
| discovery_sampled/pass_at_4 | 0.1562 | 0.2083 | 0.1458 | 0.1562 | -0.0417 |
| discovery_greedy/pass_at_1 | 0.0833 | 0.1354 | 0.1042 | 0.1771 | 0.0208 |

Question-paired and reference-template bootstrap intervals are in `core_2x2.json`; they do not include training-seed uncertainty. Nonsignificance does not establish equivalence.

Parent probe pass@1 and pass@4, the descriptive target-minus-control contrast, matched sentinel changes, midpoint trajectories, and the fixed16 training diagnostic are reported separately. Compute probes are not construction accuracy.

The training diagnostic selects four questions from each anchor-family x target-label stratum (population supports 25, 103, 29, 99). Target-degenerate questions are 8/16 of the diagnostic versus 54/256 of the training population. Scores are unweighted diagnostic summaries, not whole-training accuracy estimates.

Construction errors distinguish exact number resources, exact target satisfaction, and explicit intermediate equations. NA remains unknown. An expression reaching the wrong target may still have correct intermediate arithmetic. Parsing alone is not verified task correctness.

A/B reference NLL is teacher-forced and response-token weighted; A/B names the reference program family, not the prep state. Each Surface reference-family aggregate mixes eight anchor and eight non-anchor questions. Paths sees both program families, but its trained rendering can differ from reference rendering 0. These aggregates cannot identify literal memorization or unseen-path performance. Missing measurements remain NA. Recorded forward runtime appears in `reference_nll.json`; absent timing remains NA. Forward runtime is already included in process/rental charges and adds no autoregressive generations.

Batch counts, generated records, retained tokens, padded generated tokens, generation time (including prefill), CPU scoring, and persistence timing remain distinct in `timing_profiles.json`. No separate prefill/decode timing was measured.
