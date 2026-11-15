# A8 final audit acceptance

Accepted `2121b7cb789e31a46e00692d5d5f88907850b75f` for the complete T packet `1767fedb89fcec96ef504b97774f40215ca0712c`, confirming the same four endpoints independently reviewed in `4f3bb1e1e0d4ab81b6f2ca5aa794a5da922ed065`. All 20,000 outputs and all 72 public bindings match the frozen packet. Six reviewer disagreements are confined to `math/test/1714` and `math/test/4127`; the accepted existing labels are retained.

| Group | Audited endpoints | Prediction hits | Frozen-rule verdict |
|---|---:|---:|---|
| A | 10 | 7/10 | partially_holds |
| B | 7 | 6/7 | holds |
| C | 5 | 4/5 | holds |
| T | 4 | 3/4 | partially_holds |

All 26 Amendment 8 endpoints are complete and independently audited; 20 predictions hit their frozen tolerance. The T verdict is **partially holds** (3/4); SL-8 **does not hold**. SL-5 and SL-7 hold. T's mean residual is −1.31 pp. For K > 1, RMSE is 0.14 pp for the registered rule, 0.41 for beta = 1 and 4.20 for beta = 0. The two E = 2 cells both hit; the E = 4 cell hits and the E = 1 cell misses. These values are copied from the accepted reviews, with no new fit or bootstrap. All A8 cells remain exploratory and excluded from H0–H3.

T03's length-cap rate is 9.18%; its accuracy among normally terminated outputs is 67.5%, compared with 61.32% over all 5,000 questions. The primary denominator and frozen labels are unchanged.

The T, B/C and reduced GSM controllers have completed and exited. All 12 retained Tinker GSM endpoints were already accepted; G2 fails, G3 holds and G1 is not assessed. All A8 checkpoints and existing Tinker TTLs remain retained. No additional experiment is authorized or queued, and this completed scope no longer requires keeping the local host awake.

Existing accounting plus retained reserves: A8 T **$23.758422 / $40**; Tinker combined **$398.202617 / $485**, including the $30 storage reserve once. This is budget accounting, not a provider invoice or remaining credit balance. Before any separately authorized future Modal admission, check the first full post-cleanup UTC storage day (11/16), available after 11/17 00:00 UTC, under `84404ebe`; report if volumes approach 900 GiB.

See [acceptance and immutable-file hashes](ACCEPTANCE.json), [current status](CURRENT_STATUS.json), [full packet review](AUDIT_1767fedb_A8_group_T_packet.md), [original endpoint review](AUDIT_A8_group_T_four_endpoints.md), and the [T packet audit sidecar](../amendment8_T_results_review_v1/AUDIT_STATUS.json). Additive audit sidecars supersede historical pending fields in frozen result files; no frozen result, prediction, archive or label was edited.
