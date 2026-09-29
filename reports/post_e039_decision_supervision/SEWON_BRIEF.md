# Discussion draft for Sewon — decision supervision after E039

Prepared for Zhice to review and send. No message has been sent.

We completed the planned four-arm, equal-added-dose continuation. Within each existing single/paired recipe, ordinary CE (U) and first-decision weighting (D, lambda5) started from the same step256 adapter and received128 further updates on unchanged data. Optimizer/scheduler were reset; order, seed17, LR vector, and token budget were matched within recipe. Weight-mass normalization does not equate gradients.

On the frozen fresh48-group pool, the primary H outcome required both targets to be strictly correct under greedy decoding:

| Recipe | U | D | D−U, percentage points [95% group interval] |
|---|---:|---:|---|
| Single | 13/48 | 20/48 | +14.58 [+4.17, +27.08] |
| Paired | 16/48 | 24/48 | +16.67 [+6.25, +27.08] |

The equal-recipe mean was+15.63 pp [+7.29,+25.00]; family-cluster sensitivity intervals were also positive. These are exploratory, jointly paired number-group bootstrap intervals, conditional on one training seed and inherited parents. Two recipes are not two seeds. The previous inconclusive/negative paired-versus-single finding remains unchanged.

Stage A established that low whole-reference CE did not imply reliable training behavior: actual F training prompts yielded38/256 and35/256 successes. Actual H reference NLL was0.0204/0.0248 overall but0.6055/0.8841 at the first decision. Saved same-prefix raw/effective logits passed the fixed64-case greedy alignment audit.

The benefit has important limits. H gains concentrated at root holes; both D arms reached only3/24 both-goal successes on internal holes. F sampled pass@1 D−U was−0.52 pp for single and+2.08 pp for paired, with both intervals crossing zero; the equal mean was+0.78 pp [−1.17,+2.60]. Paired F pass@4 improved9→20/96, but this exploratory secondary signal does not replace the planned F outcome. F greedy and fixed F64 training-fit counts were lower under D in both recipes. Fresh H first-decision reference NLL worsened under single-D despite better behavior, so a single uniform NLL mechanism is not supported.

The next proposed change is a position/count-matched non-decision-token weighting control, using the same dose and weight-mass rule, frozen without selecting positions by model loss. This would test whether the benefit is specific to semantic decision positions. Independent seeds, earlier parent-chain retraining and independent families would be a later confirmation stage. None has been launched; the server is off. We should not yet claim gradient dilution, internal goal binding, free program-search improvement or methodological novelty.

All512 updates,4,736 generations and7,552 diagnostic sequence-equivalent forwards completed. Raw outputs and backups passed independent checks. Whole powered-window proxy cost was CNY16.28, not an invoice. Full evidence: `EXECUTION_SUMMARY_ZH.md`, `RESULTS.md`, `STAGE_A_TRAIN_FIT.md` and the accompanying result archive.
