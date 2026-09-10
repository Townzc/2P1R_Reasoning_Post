# C018: existing-cache length and selection audit

2026-09-10 UTC. Post-hoc CPU analysis; no model, server or teacher call.
The original C017 decisions and E013/E014 results are unchanged. The analysis
verifies all **15,308 accepted response hashes** against cached source text.
Supervised lengths reuse C017's exact tokenizer counts, including EOS.

## Length is not a sufficient diagnosis

| Existing accepted bank | Original parent denominator | Parents with at least one / four solutions | Median / 90th-percentile supervised length |
|---|---:|---:|---:|
| GSM8K | 1,024 | 1,013 / 963 | 143 / 227 |
| MATH levels 1–3 | 512 | 486 / 481 | 207 / 417 |

The 32 E013 targets have mean 163.31, median 144.5 and maximum 368 supervised
tokens. Eight failed examples range from 82 to 368; 24 passed examples range
from 84 to 322. This overlap does not establish a length–failure causal effect.
The minibatch loss remains variable near the end (last-32-update mean 0.01261,
maximum 0.07332); different batches prevent interpreting this as proof of LR
instability. E014's direct target probes remain the stronger fit evidence.

## Hypothetical shorter-only filtering loses coverage

| Bank / cutoff, including EOS | Retained pairs | Parents with at least one | Parents with at least four |
|---|---:|---:|---:|
| GSM8K, no added cutoff | 7,776 | 1,013 | 963 |
| GSM8K, 128 | 2,973 | 629 | 373 |
| GSM8K, 256 | 7,361 | 1,006 | 915 |
| GSM8K, 512 | 7,773 | 1,013 | 962 |
| MATH, no added cutoff | 7,532 | 486 | 481 |
| MATH, 128 | 1,449 | 288 | 139 |
| MATH, 256 | 4,840 | 448 | 383 |
| MATH, 512 | 7,155 | 486 | 475 |

These are sensitivity analyses, not new acceptance rules. A 128-token rule
would remove all usable answers from 384 previously covered GSM8K parents.
Selecting a shorter answer **within each retained parent** is different from
globally discarding all long responses. Neither establishes better learning.

## A surface-diversity comparator is feasible without dropping more parents

On the original first 256 GSM8K parents, choose min(4, K_i) accepted responses.
Every policy has 996 pairs from 253 parents; the three zero-success parents
remain in the denominator. Exactly 245 parents have four selected responses.

| CPU selection rule | Selected supervised tokens, one traversal | Mean within-parent trigram Jaccard |
|---|---:|---:|
| Original source order | 152,924 | 0.2600 |
| Deterministic hash-random, seed label 17 | 153,083 | 0.2643 |
| Farthest-first surface diversity | 154,668 | 0.2111 |
| Shortest within each parent | 136,805 | 0.2833 |

The diversity rule begins with the same response as hash-random, then minimizes
maximum similarity to selected responses. Similarity averages are unweighted
over the 250 parents with at least two responses. Only eight of 256 parents
have any accepted pair with Jaccard at least 0.8. The diversity rule uses 1.04%
more supervised tokens per traversal than random; shortest uses 10.63% fewer.
These are **not** equal-dose training runs. A later experiment must construct
whole-response schedules with matched total supervised tokens/updates and
report the remaining length/processed-token differences.

Lexical dissimilarity is expected to improve under an algorithm that optimizes
it. This is a manipulation/feasibility check, not evidence of reasoning diversity,
better teaching, or downstream gains. Selection uses no validation/test labels.
Cached accepted K_i is not a measured teacher pass rate.

## Reproduction and records

```sh
python3 -m analyses.c018_selection_audit --out NEW_UNUSED_OUTPUT_DIRECTORY
```

Restore the original ignored C017 raw cache using its source receipts first.
The script refuses existing outputs and checks source response hashes before
writing. [Summary](real_math_c018_selection_audit_r1/summary.json) and
[per-parent selections](real_math_c018_selection_audit_r1/selection_by_parent.jsonl)
contain counts/IDs rather than copying raw third-party text. Independent
reproduction and invariant checks are recorded in
[verification](real_math_c018_selection_audit_r1/verification.json).

Conclusion for planning: reject blanket aggressive shortening as the default
repair. Retain random and repetition controls; keep student-aware selection and
curriculum as hypotheses requiring separate, priced experiments.
