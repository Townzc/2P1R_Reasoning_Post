# LT002 — complete supervision controls and decoding diagnostic

QDW's advantage over random weighting remains inconclusive on the primary greedy
comparison. Its greedy gap over the position/difficulty-matched control is positive
in this single trained-state comparison. On the same questions, QDW/SFT and both
normalized weighting controls lose accuracy under T=1 sampling, while DFT and
TrimSFT have higher sampled point scores. This supports a development-set decoding
sensitivity observation, not a general improvement or a causal token-selection claim.

## Complete results

All methods use the same 512 **previously observed Numina dev questions**. Greedy
outputs for the four original methods are verified reuse; all other outputs are
new. Sampled means one draw per question at T=1, top-p=1, top-k=0, seed 2026092902,
with the same 2,048-token cap and batch size 16. There are no unresolved judgments;
parse failures remain in the full denominator.

| Method | Greedy | Sampled | Sampled − greedy, pp |
|---|---:|---:|---:|
| SFT | 227/512 (44.34%) | 156/512 (30.47%) | -13.87 |
| DFT | 210/512 (41.02%) | 216/512 (42.19%) | +1.17 |
| TrimSFT | 201/512 (39.26%) | 218/512 (42.58%) | +3.32 |
| QDW-v0 | 239/512 (46.68%) | 169/512 (33.01%) | -13.67 |
| Random weighting | 225/512 (43.95%) | 162/512 (31.64%) | -12.30 |
| Position/difficulty matched | 215/512 (41.99%) | 145/512 (28.32%) | -13.67 |

QDW ranks above DFT/TrimSFT under greedy and below both under sampling on this
fixed question set. A ranking reversal can therefore occur without changing the question set. This
does **not** explain the whole MATH/GSM difference, estimate eight-draw consistency,
or establish transfer.

## Prespecified paired contrasts

Differences and intervals are percentage points. Primary comparisons are QDW minus
each control under greedy, using 97.5% question-bootstrap intervals. The sampled
counterparts retain the frozen implementation's 97.5% intervals; decoding
interactions and matched-minus-random comparisons use 95% descriptive intervals.
All intervals use 10,000 replicates and seed 2026092903, resampling whole questions.

| Contrast | Difference, pp | Interval level | Paired interval, pp |
|---|---:|---:|---:|
| QDW-minus-position_difficulty-greedy | +4.69 | 97.5% | [+0.98, +8.40] |
| QDW-minus-position_difficulty-sampled | +4.69 | 97.5% | [+0.00, +9.38] |
| QDW-minus-position_difficulty-sampled-minus-greedy | +0.00 | 95.0% | [-5.27, +5.27] |
| QDW-minus-random-greedy | +2.73 | 97.5% | [-0.98, +6.45] |
| QDW-minus-random-sampled | +1.37 | 97.5% | [-3.52, +6.25] |
| QDW-minus-random-sampled-minus-greedy | -1.37 | 95.0% | [-6.64, +4.10] |
| matched-minus-random-greedy | -1.95 | 95.0% | [-5.08, +1.37] |
| matched-minus-random-sampled | -3.32 | 95.0% | [-7.62, +0.78] |

QDW minus random greedy is +2.73 pp with an interval spanning zero; this is neither
a demonstrated advantage nor equivalence. QDW minus matched greedy is +4.69 pp
[+0.98, +8.40], conditional on these trained states. Matching did not attenuate the
point gap in this draw; matched-minus-random is itself uncertain. The controls do
not establish that token semantics caused the gap. The QDW-control decoding
interactions also span zero.

One training seed (17), one mask draw and one sampled answer per question were used.
The intervals exclude training-seed and mask-seed uncertainty. Development data
were already observed; these are exploratory results, not fresh confirmation.
Prior negative QDW MATH results remain unchanged.

## Output diagnostics

Entries are greedy / sampled. Every diagnostic retains all 512 questions.

| Method | Mean output tokens | Parse failures | Length caps |
|---|---:|---:|---:|
| SFT | 487.2 / 451.5 | 11 / 14 | 16 / 5 |
| DFT | 539.1 / 521.9 | 11 / 7 | 44 / 37 |
| TrimSFT | 493.2 / 499.1 | 21 / 17 | 23 / 23 |
| QDW-v0 | 499.5 / 458.6 | 12 / 10 | 20 / 6 |
| Random weighting | 489.0 / 469.2 | 11 / 10 | 16 / 9 |
| Position/difficulty matched | 483.1 / 493.2 | 6 / 9 | 15 / 14 |

## Control balance and descriptive training traces

Both controls preserve 147,934 selected tokens, each answer's K, multiplier 5 and
normalized total weight; 156 zero-K examples remain. Random and matched masks
change 3,938 and 3,932 of 4,096 masks, with QDW overlaps of 15,064 and 38,497 tokens.
Matched forced-overlap lower bound is 853 tokens. Mean selected-token NLL and
relative-position residuals are −0.10654/+0.02311 for matched versus
−0.74481/+0.17933 for random. Matching is coarse and leaves residual imbalance.
Original selected positions were eligible by design. See [mask audit](MASK_AUDIT.json).

The following is a **post-hoc summary of existing training logs**, with no new
model calls or new inferential tests. It motivates checking the loss definitions
before attributing the decoding pattern to a mechanism.

| Method | Median weight mass / supervised token | Median preclip gradient norm | Clipped updates |
|---|---:|---:|---:|
| SFT | 1.00000 | 0.4817 | 4/128 |
| DFT | 0.85262 | 0.2197 | 0/128 |
| TrimSFT | 0.01159 | 0.1831 | 0/128 |
| QDW-v0 | 1.00000 | 0.8376 | 15/128 |
| Random weighting | 1.00000 | 0.6071 | 4/128 |
| Position/difficulty matched | 1.00000 | 0.7784 | 11/128 |

Gradient norms are not AdamW parameter-update magnitudes. Loss-weight normalization
was not randomized in this phase. Different-batch raw CE endpoints in the linked
[diagnostic JSON](POSTHOC_TRAINING_DIAGNOSTIC.json) are not a fixed-evaluation learning
curve. These traces do not identify why the methods respond differently to sampling.

## Execution and preservation

- Published execution source: `c11097671c7767114f1f3a23bcaeb9426abced5b`.
- Qwen2.5-Math-1.5B base revision `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2`;
  original 4,096 Numina training examples, full FP32 AdamW / BF16 autocast.
- Two fresh-base controls each committed 128 updates and 1,800,417 supervised
  tokens. All 256 updates and 4,096 new generation reservations reconcile exactly.
  No new annotations, public-test calls, model retries or uncommitted work.
- All 4,096 new scores and 2,048 reused scores bind raw outputs, references and
  frozen scorer identity. New scoring needed no infrastructure retry. One original
  reused score retains its historical CPU retry; it was not rerun in LT002.
- GPU/CPU workers exited successfully at 07:58:33 / 07:58:35 UTC on September 29.
  Final checkpoint model and optimizer/RNG component hashes were reverified.
- 15,724 compact files plus the manifest were independently downloaded and verified.
  Full recovery binaries remain on the stopped server; a full independent binary
  export is **not** claimed. Preserve that volume and the older unique checkpoints.
- Normal provider OFF was verified no later than 08:10:38 UTC; the temporary timer
  was cleared. Conservative whole powered window: 3h55m38s, approximately CNY31.34
  at CNY7.98/hour, excluding storage. This is a time-based proxy, not an invoice.

The local recomputation from all 6,144 per-question score records exactly matches
the frozen report, including every bootstrap interval. A local Python compatibility
issue in the first archive verifier was fixed using the retained download; no
scientific work or transfer was repeated. The scientific source stayed unchanged.

## Evidence and next use

[Exact results](RESULTS.json), [final independent audit](FINAL_INDEPENDENT_AUDIT.json),
[local analysis verification](LOCAL_ANALYSIS_VERIFICATION.json),
[cost and closeout](COST_AND_CLOSEOUT.json), and
[scientific record manifest](SCIENTIFIC_RECORDS_MANIFEST.json) accompany
`SCIENTIFIC_RECORDS.tar.gz`. The archive preserves 15,698 byte-exact scientific
records including raw outputs, saved batches, training histories, masks and scores.
Machine/operator records remain private. Check hashes before extracting or analyzing.

This is an intermediate research result. The next useful preparation is to inspect
the saved loss-weight and clipping traces, then specify a small controlled follow-up
that separates normalization, token selection and decoding. Freeze that follow-up's
design and runtime/cost/stop estimates before execution. No extra arm, seed, test,
server restart or rental follows automatically from this closeout. Discussion
questions remain provisional while subsequent evidence is collected.
