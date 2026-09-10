# C017: real-math CPU audit and proposed training scale

2026-09-10 UTC. **CPU audit complete; no model inference or training.**
The data support a bounded first GSM8K study with acquired P up to 1,024 and
target K up to four. A four-condition schedule is concrete and CPU-verified.
MATH remains a useful second task, with unresolved answer formats and selected
population limits to review before training. This is data feasibility, not an
allocation-performance result or a launch approval.

## Audited population and source evidence

The [fixed audit specification](../docs/experiments/C017_real_math_cpu_audit.md)
and [configuration](../configs/diagnostics/real_math_c017.json) record revisions,
seeds and limits. Original problems were grouped and sampled before any released
solution shard was retrieved. The corrected parent freeze was published at
`bc1992b5bac772936b9a2202f4314ee405205929` before retrieval.

| Dataset | Original train | Original test | Eligible training groups | Development | Audit draw | Fresh draw reserved | Other eligible reserve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GSM8K | 7,473 | 1,319 | 7,470 | 512 | 1,024 | 1,024 | 4,910 |
| MATH | 7,500 | 5,000 | 2,908 | 256 | 512 | 512 | 1,628 |

MATH is limited to original levels 1–3 without explicit question-side diagram
markup. Proportional subject/level sampling preserves all 21 strata in dev,
the complete audit draw and the fresh draw; smaller nested prefixes need not
contain all 21 strata. Fresh and development solutions were not scored or
selected. Official tests were read only for provenance/overlap checks; no test
model predictions, benchmark scores or final-test tuning occurred.

The MATH split check found real mirror errors:

- The [author-linked merged mirror](https://huggingface.co/datasets/qwedsacf/competition_math/tree/e839825f9ec5c6cfa585c654a59610969ec13993)
  labels all 12,500 rows `train`. Its four-field row multiset exactly matches
  the [split-preserving EleutherAI mirror](https://huggingface.co/datasets/EleutherAI/hendrycks_math/tree/21a5633873b6a120296cce3e2df9d5550074f4a3).
- The [original-ID mirror](https://huggingface.co/datasets/nlile/hendrycks-MATH-benchmark/tree/465bcdb36f5962aa3512891498966df785fc3c18)
  uses a 12,000/500 benchmark partition that mixes original splits. Its original
  IDs claim 7,499 train and 5,001 test records, with one duplicated test ID.
  Normalize whitespace in question/reference and require matching original
  split and subject: **12,499 file IDs verify; one training row is quarantined**.
  Its raw metadata also differ in 488 question-whitespace cases, three level
  fields and one subject field. Original unknown levels are preserved.
- The historical [EleutherAI loader](https://huggingface.co/datasets/EleutherAI/hendrycks_math/blob/3730e0d9543219af79a2ddf93da274bb55d7fc27/hendrycks_math.py)
  explicitly reads original `MATH/train` and `MATH/test` directories. The
  author's raw archive returned HTTP 403 and the old HF loading script returned
  HTTP 401. The raw HF ZIP was not downloaded. This clarifies the compact
  source receipt's shorthand “archive/loader” wording; archive-byte provenance
  is not claimed.

All 250 [GSM-Symbolic templates](https://github.com/apple/ml-gsm-symbolic/tree/b6a1625025fc857300203bac9f617e5d8ec99f65/templates)
map to 100 valid [official GSM8K test](https://github.com/openai/grade-school-math/tree/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/data)
parent indices. They remain evaluation-only. Public source availability says
nothing about unknown student pretraining exposure.

## Problem-side filtering losses

Losses below are sequential, counted once in the stated order. Number-masked
five-token-shingle Jaccard >=0.8 groups are deliberately conservative template
candidates, not proven duplicate mathematical problems.

| First exclusion reason | GSM8K lost | MATH lost | MATH remaining |
| --- | ---: | ---: | ---: |
| Unresolved original file ID | 0 | 1 | 7,499 |
| Component touches an official test: exact, near or number-template candidate | 2 | 393 | 7,106 |
| Outside levels 1–3, including unknown level | 0 | 3,852 | 3,254 |
| Explicit question diagram markup | 0 | 271 | 2,983 |
| Another eligible representative already kept in the group | 1 | 75 | 2,908 |

MATH originally has 3,504 level-1–3 rows; the final 2,908 retain 82.99% of that
scope and 38.77% of all original training rows. Because exclusions overlap,
the 3,852 sequential scope loss differs from the 3,996 rows outside levels 1–3
in the raw inventory. Report this selected text-only population, not all MATH.
There are zero cross-dataset edges under the specified similarity rule and zero
cross-partition group collisions after exclusions. These are operational checks,
not a claim that every semantic overlap has been found.

## Released-solution coverage and filtering

The fixed four [OpenMathInstruct-2](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2/tree/469216e3f46f4dacf476b382e192485ea51a143e)
shards contain 1,746,600 rows: 57,236 original GSM8K, 307,572 original MATH and
1,381,792 augmented rows. Augmented questions are excluded. Two `math` rows
match an official-test problem and were excluded before draw linkage. Every
original-source row links to a normalized original question; no fuzzy source
linkage or synthetic-parent inference is used.

| Measure | GSM8K | MATH |
| --- | ---: | ---: |
| Acquired audit parents | 1,024 | 512 |
| Released rows found for those parents | 7,793 | 24,294 |
| Inspected after first-16 cap per parent | 7,792 | 8,045 |
| Accepted by the corrected conservative checks | 7,776 | 7,532 |
| Source/reference numeric disagreement | 9 | 0 |
| Source/reference equivalence unresolved | 0 | 371 |
| Final/reference equivalence unresolved | 7 | 142 |
| Empty, missing final answer, numeric final disagreement, exact duplicate, serialization error, over 2,048 tokens | 0 | 0 |
| Parents with at least one accepted solution | 1,013 (98.93%) | 486 (94.92%) |
| Parents with at least two | 1,005 (98.14%) | 482 (94.14%) |
| Parents with at least four | 963 (94.04%) | 481 (93.95%) |
| Zero solutions: no source row in the four shards | 10 | 1 |
| Zero solutions: source rows exist but checks reject/unresolve all | 1 | 25 |

GSM8K has 964 parents with at least four source rows and 963 with four accepted
rows: most K=4 shortfall is retrieval-slice coverage. MATH has 508 parents with
four source rows and 481 with four accepted rows: its dominant loss is answer
normalization/verification. **Do not label unresolved equivalence as wrong
reasoning or count unobserved released rows as failed teacher generations.**

The original conservative pass is retained as `solutions_r1`: it accepted
7,175 MATH responses on 463 parents. A matrix-separator bug and unambiguous
LaTeX presentation cases were repaired; the same 15,837 candidates, in the same
order and with the same raw-file hash, were replayed. The corrected `solutions_r2`
accepts 357 additional MATH responses and restores 23 parents. No new shard,
parent, candidate, prompt or model call was added. Units, percent signs, base
subscripts, assignments, mixed numbers and general algebra stay unresolved.
One source expected-answer string is visibly malformed. These are documented
follow-up issues, not silently repaired labels.

No normalized exact-text duplicates were found among checked eligible rows.
At the prespecified >=0.9 shingle-Jaccard sensitivity, two MATH responses are
redundant; no parent's K=1/2/4 coverage changes. This does not establish distinct
reasoning strategies. Per-parent and per-stratum denominators are retained in
[the corrected summary](real_math_c017_solutions_r2/summary.json) and
[per-problem records](real_math_c017_solutions_r2/per_problem.jsonl).
Prealgebra level 2, for example, loses all accepted solutions on 8/47 parents;
any second-task claim must acknowledge this selection shift.

## Reference quality and sampled reasoning review

GSM8K training row 03529 has a defective native reference: the question says
40% and 34% of 50 attendees support the two teams, while the reference calculates
60% for the first team and answers 3. The literal arithmetic gives
50*(1-.40-.34)=13, agreeing with all nine retrieved source rows. The audit keeps
this parent in acquired P, marks the mismatch and excludes its responses; it
does not silently change the official reference or label these as model errors.

Eight parent-distinct accepted responses per dataset were selected by the frozen
hash rule for AI-assisted step review. The review found no arithmetic error in
the displayed computations, but identified an unstated independence assumption
in a MATH weather-probability problem, ambiguous “two times heavier” wording in
a GSM8K question, and an inconsistent introductory sentence in a MATH complex-
arithmetic solution whose displayed equations are correct. See
[the row-level review](real_math_c017_solutions_r2/qualitative_review.json).
These flags were not used to replace sampled parents or tune model outcomes.
Sixteen AI-reviewed examples are not human gold or a corpus-wide proof audit.

## Training scale supported by the data

Recommend starting with the following **four conditions**, using the frozen
GSM8K draw. The shared first 256 parents make Repeat/Solutions directly useful;
Mixed and Breadth preserve the proposed acquisition-allocation question.

| Condition | Acquired P | Target K | Trainable P | Actual unique pairs | One-pass supervision tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Repeat | 256 | 1 | 253 | 253 | 38,596 |
| Solutions | 256 | 4 | 253 | 996 | 152,924 |
| Mixed | 512 | 2 | 508 | 1,011 | 154,623 |
| Breadth | 1,024 | 1 | 1,013 | 1,013 | 155,630 |

All missing parents and unmet K targets remain in acquisition accounting. No
condition is restricted to the 963 parents known to have four accepted outputs.
The larger P=1,024/K=4 cell is feasible as 3,970 pairs, but is not needed in the
first proposed four-condition comparison. This smaller design cannot by itself
fit and validate a general price-dependent allocation rule; fresh draws and
off-grid policy checks remain subsequent work.

The [CPU schedule proposal](real_math_c017_scale_proposal_r1/proposal.json)
contains row identities and all updates for seeds 17 and 23. **Each arm has
exactly 524,288 response tokens including EOS and 256 optimizer updates.** Every
selected pair appears; no trace is truncated and no artificial padding is used
to match supervision. Repeat rows receive 13–14 exposures, other rows 3–4.
A seeded subset-sum chooses the one-extra-exposure remainder, which introduces
a disclosed length-dependent weighting residual. With microbatch one there is
no padding and no packing; normalize by actual response tokens per update.

Per-update supervision is not identical: ranges across proposed arms/seeds span
1,752–2,327 tokens. Total processed tokens span 738,263–743,195 (about 0.67% range),
and presentations/parent exposure also differ. Exact totals plus equal update
count do not establish equal runtime or identify every allocation mechanism.
Review these residuals as part of the scientific protocol before launch.

All accepted GSM8K sequences are <=687 tokens (response p95=260, max=641).
The proposed GSM8K context limit is 1,024, with 768 maximum generated tokens.
MATH sequences reach 1,143 tokens (response p95=513); keep 2,048 for it.
At 1,024, 16 MATH responses would be lost, without changing K=4 parent coverage.
The 2,048 filter loses none; this is not a length-matching-selected pool.

**Next model step:** a new 32-parent GSM8K overfit/profile using the existing
pinned Qwen2.5-1.5B base recipe. Its available reference rows are listed in the
proposal as an engineering-only selection. After successful learning and measured
training/evaluation cost, price one complete four-arm seed17 phase; seed23 is
conditional replication, not automatically authorized. One four-arm seed is
2,097,152 supervised tokens; two seeds are 4,194,304. CPU token counts cannot
price GPU runtime. The existing **1,229 remaining GPU process-seconds** do not
constitute a verified full-phase budget.

Keep the MATH 512-parent draw for decisive second-task contrasts, provisionally
(P,K)=(128,4),(256,2),(512,1), after resolving answer-format and quality limits.
Do not expand to a second full grid or a larger teacher to fix a CPU audit issue.

## Verification, costs and recovery

[Independent reconciliation](real_math_c017_solutions_r2/independent_verification.json)
re-enumerated all 1,746,600 source rows, recovered the exact first-16 candidate
selection, checked all 21,292 parents and independently retokenized all 15,308
accepted responses. All P/K totals agree; cross-partition group collisions and
original-test training rows are zero. Twenty-four targeted tests pass, including
JSONL Unicode separators, source exclusion, conservative answer formats, rare
stratum preservation, zero-parent denominators and exact whole-trace budgets.

Source files occupy 968,697,196 bytes in total, including the 947,333,768-byte
solution slice. Recorded file transfers take 62.69 seconds; two discovery-file
transfer times are unknown. These are transfer measurements, not total human
research/curation time. Both filtering runs and the independent verification
are retained, including repairs. Neither failed historical teacher attempts
nor teacher generation cost can be inferred from this released cache. Shared
retrieval/curation overhead must be charged or amortized explicitly in any
future offline policy replay; problem-writing prices remain stated scenarios.

Code and compact records are public; raw third-party questions/responses stay
in the ignored source cache. The full parent manifests are preserved byte-exact
as adjacent gzip/base64 archives. Run IDs r1/r2 are immutable. The r2 parent
freeze's commit field names its base checkout; the actual proportional patch
is identified by `executed_source.json` and was reproduced byte-for-byte from
published source before response inspection. Source/publication mapping and
reproduction receipts make this distinction explicit.

No model weights were loaded, no teacher/API generation was requested, no
server was contacted and no GPU ledger changed: **5,971/7,200 seconds used,
1,229 left, 16 receipts, zero reservations**. E012 remains paused. No external
message, course submission or private correspondence was published.
