# Stage A: actual training fit and first-decision evidence

Actual F replay prompts are deduplicated by exact training prompt tokens. This is separate from H-to-F transfer and fresh-instance evaluation. H anchors/countergoals retain their supervision labels. No metric is a training or checkpoint-selection gate.

| State | Pool | Strict correct / all outputs | Anchor | Countergoal |
|---|---|---:|---:|---:|
| E038 | train_F | 38/256 | NA | NA |
| E038 | train_H | 36/64 | 23/32 | 13/32 |
| E039 | train_F | 35/256 | NA | NA |
| E039 | train_H | 37/64 | 18/32 | 19/32 |

Stored Stage A outputs analyzed: 640. First literal token differences: 544. Outputs with certified error evidence: 491.

A different valid F expression is accepted. Literal mismatch does not locate a semantic mistake. False displayed equalities and strict final violations are recorded as certified evidence; unsupported earlier reasoning leaves the first true semantic error unknown. No F prefix is called a dead end without an exhaustive completion certificate. PER_PROBLEM.jsonl retains these distinctions.

Reference span diagnostics use unweighted likelihood, regardless of training objective. Whole-response NLL does not identify the decisive token loss; H source reference sets differ across recipes. Missing or unavailable span/alignment evidence is NA, never fabricated from generation accuracy.

Forward diagnostic views registered: 28. Details and raw source bindings are in DECISION_DIAGNOSTICS.json.

| State | Reference pool | Records | Full NLL | First decision NLL | Other response NLL |
|---|---|---:|---:|---:|---:|
| E038 | reference_H | 512 | 0.020388 | 0.605515 | 0.011188 |
| E038 | reference_F | 512 | 0.079131 | NA | 0.079131 |
| E038 | train_H | 64 | 0.026831 | 1.149003 | 0.009206 |
| E039 | reference_H | 512 | 0.024811 | 0.884073 | 0.011306 |
| E039 | reference_F | 512 | 0.079596 | NA | 0.079596 |
| E039 | train_H | 64 | 0.023214 | 0.914885 | 0.009210 |

reference_H/F are each arm’s actual training references. train_H is the separate fixed style0 diagnostic reference; its single countergoals are unsupervised and are not included in training NLL. F has no decision weighting mask. Prefix-matched emitted H decisions: 89; all other H trajectory decision alignments remain unknown.
