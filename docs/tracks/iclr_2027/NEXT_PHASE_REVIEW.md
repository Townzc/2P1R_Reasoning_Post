# Next method and resource review

September 11, 2026. **Review packet, not execution approval or runtime readiness.**
E017 already has authorization. The next decision is conditional P006 Stage B/C;
the scientific comparison below is a separately reviewable later phase. No
allowance, reservation, run, or reserved-data release was created here.

## 1. Immediate decision: one retained-learning recipe

After a complete passing E017, review the following fixed proposal together:

| Item | P006 Stage B: E018 |
| --- | --- |
| Scientific role | Recipe feasibility; not an isolated causal LoRA, breadth, or LR effect versus E015 |
| Base | Fresh original Qwen2.5-1.5B base, revision `8faed761d45a263340a0528343f099c05c9a4323`; never resume E015 |
| Data | Existing C017 Repeat anchors: nominal256 parents,253 available; retain3 unavailable in accounting |
| Dose | Two full epochs,506 presentations,64 positive-LR updates,77,192 supervised tokens including EOS,109,434 processed nonpadding tokens |
| Adaptation | LoRA rank16, alpha32, dropout0, bias none; q/k/v/o/gate/up/down; base weights, embedding, head and norms frozen |
| Numerics | FP32 base/adapters, BF16 autocast, SDPA, TF32 off; no quantization; AdamW on adapters only, betas(0.9,0.999), eps1e-8, weight decay0, clip1.0 |
| Batching | Eight examples/update, microbatch1, each epoch's final update has5 examples; normalize by all unmasked target tokens in that update; no packing or target truncation |
| LR/randomness | Existing exact P006 64-value schedule: four-step warmup to1e-4, cosine to1e-5, summed LR0.003505; seed17, epoch order17/18 |
| Evaluation | Same64 observed dev parents, base and final adapter; fixed32 training decodes; all253 training references before/after for pooled NLL; at most160 free generations |
| Process/rental | 900+15=915 process seconds;30-minute/CNY4 whole-rental cap; require1,215 seconds remaining at admission |
| Preservation | Compact records first; estimated70.44MiB FP32 adapter tensors, actual size still to be measured; bounded120-second copy only with adequate measured throughput |

The exact source of this proposal, including two fixed32-ID samples and every
LR value, is [P006](../../experiments/P006_evaluation_and_capability_preservation.md)
and its [configuration](../../../configs/diagnostics/real_math_p006_proposal.json).
No thresholds are relaxed here. The existing B/C proposal is retained rather
than replaced by an additional hyperparameter search.

Require both base and adapter usability:64 valid records, at least48 parsed,
at least8 task-correct, at most8 true length caps, zero invalid/false-EOS records.
For retention require `10 * both_correct >= 9 * base_correct` and net loss at
most4 questions. Publish both-correct, lost, gained and both-wrong cells; gains
do not cancel losses in the first rule. For learning require complete finite
updates, changed adapter weights, unchanged base weights, and at least10% lower
pooled training-reference NLL. These are operational screens, not powered proof
of noninferiority or broad knowledge retention.

On success only, Stage C proposes base versus this same frozen adapter on64
reserved development parents, ranks81–144, under identical rules. Maximum128
generations;420+15=435 process seconds;20-minute/CNY2.67 rental cap;735 seconds
required at admission. No new tuning after seeing them. Failure blocks scientific
scaling, and these parents never become fresh again. A later alternative recipe
requires a new decision, not an automatic sweep.

### What remains before an execution release

The method and spending request are concrete; E018 is not executable yet.
Before requesting its startup, complete the actual implementation and review:

- Reconstruct all253 prompt/response bytes from the existing cache, verify
  hashes, masks/EOS, full schedules and disjointness without inspecting reserved
  development. Review the already fixed32-row quality sample and retain flags;
  a material error requires an explicit new data decision, not silent repair.
- Pin compatible PEFT/runtime wheels and exact trainable parameter names;
  verify frozen-base equality, zero-adapter identity, correct token-normalized
  gradients, and adapter save/reload. Only new implementation gets new focused
  tests; do not repeat unrelated unchanged suites as a project milestone.
- Implement an explicit phase authorization record and cumulative guard that
  preserve the20 historical receipts and frozen7,200-second configuration.
  P006's1,350 seconds are an additive proposed B/C envelope, not permission to
  reset a ledger or edit a frozen budget dependency. Rebase its starting hash
  to the actual post-E017 ledger after E017 completes.
- Freeze unique run IDs, exact inputs, source hashes, Linux preflight,
  measured-profile reporting, absolute rental deadline, export and shutdown
  behavior; publish the execution release before startup.

A methods/envelope review can be made once for this conditional B/C plan;
actual admission still requires E017 results and a verified release. This
document does not ask for repeated E017 approval or imply that an unimplemented
training launcher has already passed its checks.

## 2. Later scientific minimum: three allocations, one model and one task

This replaces neither C017's archived four-arm proposal nor P006's short
calibration. It proposes dropping Mixed from the sprint and testing one primary
contrast with a breadth reference:

| Condition | Acquired P / target K | Trainable P / unique pairs | Existing one-pass supervised tokens |
| --- | --- | --- | ---: |
| Repeat |256 /1 |253 /253 |38,596 |
| Solutions |256 /4 |253 /996 |152,924 |
| Breadth |1,024 /1 |1,013 /1,013 |155,630 |

Use the existing nested C017 parent ordering and accepted response identities.
Do not restrict to parents with four successful outputs or backfill missing
parents. Verify anchor inclusion in Solutions before the release. Cached
acceptance means final-answer agreement, complete serialization, length and
text uniqueness; it is not a proof of correct intermediate reasoning or distinct
semantic strategies. Inspect declared training-quality samples before outcomes.

For review, retain C017's exact **524,288 supervised tokens and256 updates per
arm**, with its whole-response schedules for seeds17/23. Each update uses its
actual supervised-token denominator. Selected rows all appear; remainder
assignment creates disclosed length-dependent weights. Across the original
four-arm schedules, processed totals span738,263–743,195 and per-update target
totals span1,752–2,327. Reconcile the exact three-arm subset at release; do not
claim per-update, sequence-length, exposure, runtime or FLOP equality.

### The dose transition is a real scientific risk

The scientific token dose is **6.79 times E018's**, and256 updates are four
times64. P006's two epochs cannot even traverse the larger response banks once
at the same77,192-token budget. Passing the small calibration does not validate
the larger comparison. Do not silently transplant that passing label.

A concrete larger-dose candidate for review keeps the same adapter targets,
optimizer/precision and microbatch1, but uses C017's variable accumulation
groups and a256-update LR schedule. For update `t` starting at1:

```text
t <= 16: lr(t) = 1e-4 * t / 16
t >= 17: lr(t) = 1e-5 + (1e-4 - 1e-5)/2 * [1 + cos(pi * (t-16)/240)]
```

All256 rates are positive; their sum is0.014005. This changed duration,
accumulation pattern and integrated LR must be reviewed as part of the
scientific recipe. All arms share it and begin from the same original base
with fresh adapters and paired seed rules.

The predeclared Repeat/seed17 endpoint is also the larger-dose retained-learning
screen on the observed64 parents. Reuse this exact endpoint in the comparison
if it passes; never retrain it to obtain a better score. Its reference-learning
check uses the same253 anchors as E018. Failure stops expansion and preserves
the endpoint. Apply the same integer usability/retention screens to every arm,
and the10% reference-NLL reduction screen to each arm's own selected references
against their original-base NLL. If any later arm fails a screen, report that
arm and stop expansion; do not drop it or tune its recipe separately. A completed
three-arm comparison requires all declared endpoints.

Proposed order: Repeat17, Solutions17, Breadth17; then the fixed seed23
replication of those three. A separately approved finite queue may implement
these gate-dependent transitions; E017 authorization does not. Two seeds are
the planned budgeted replication, not independent training-population draws.
No extra seed is selected after an inconvenient sign. Low learning, mixed
directions or broad uncertainty may justify continued research rather than an
ICLR claim. MATH, OLMo2, RL, semantic-route annotation and teacher generation
are outside this minimum.

## 3. Evaluation and precision plan for review

Primary endpoint: task-completed marked numerical correctness under the frozen
E017-style contract, counting caps and malformed outputs as failures over the
full declared denominator. Native-EOS correctness, parse/cap/boundary rates,
output lengths, gross lost/gained base successes, and training-reference NLL
are separate diagnostics. Do not report accuracy only among completed outputs
as the primary score. An incomplete model run is an incomplete experiment,
not an arm that can be silently excluded.

Primary contrast: Solutions minus Repeat. Breadth minus Solutions and Breadth
minus Repeat are secondary contextual contrasts; if testing their significance,
apply Holm correction to that two-comparison family. No pass@k or semantic
coverage claim is supported by this greedy-only design.

After all scientific endpoint/source/analysis choices freeze, propose one
368-parent development block (ranks145–512), base plus six adapters. The full
official GSM8K test is a later single frozen block of1,319 questions for the
same seven endpoints. Neither block was opened for this plan. Test access and
its resource envelope require explicit separate review. Once authorized and
opened, no recipe, arm, seed, scorer or data selection changes follow its scores.
An incomplete queue remains incomplete; no selective subset substitutes for it.

Report every seed's paired2x2 table and difference; use10,000 paired
question-bootstrap resamples with fixed seed17020 for conditional95% intervals.
For the mean across two training seeds, resample question IDs jointly across
all endpoints and retain the seed vector. Do not treat two predictions on one
question as two independent observations, or describe question intervals as
training-seed uncertainty. Report the two seed estimates and their range;
two seeds do not precisely estimate population variability.

Use a **5-percentage-point** interval margin for any proposed practical-equivalence
claim, fixed before outcomes. Merely failing to reject zero is insufficient.
The following analytic planning scenarios assume25% discordant questions,
near-zero difference, independent question units and normal approximations:

| Questions per paired endpoint | Approximate95% interval half-width | Approximate effect detectable at80% power |
| ---: | ---: | ---: |
|64 |12.25 percentage points |17.50 percentage points |
|368 |5.11 percentage points |7.30 percentage points |
|1,319 |2.70 percentage points |3.85 percentage points |

For paired differences `D in {-1,0,1}`, `Var(D)=q-delta^2`. The table uses
`1.96*sqrt(q/n)` and `(1.96+0.84)*sqrt(q/n)`, with assumed `q=.25`; it is not
power measured from unopened examples. Correlated seed outcomes do not double
sample size. Larger discordance widens uncertainty; at `q=.5`, multiply these
figures by `sqrt(2)`. The64-parent screens are unsuitable for certifying small
scientific effects or noninferiority. A null on368 may remain uninformative.

## 4. Measured anchors and whole-rental estimates

All arithmetic is in [budget_estimate.json](budget_estimate.json). These are
planning scenarios from completed runs, not measurements of a new recipe.

| Retained timing | Measurement | Correct use |
| --- | --- | --- |
| [E013 phases](../../../runs/gsm8k_overfit_e013_r1/phase_timings.json) |167.14s training,256 updates,167,232 supervised /229,056 processed tokens | Full-SFT short-response proxy only |
| [E015 phases](../../../runs/gsm8k_terminal_decay_e015_r1/phase_timings.json) |166.43s training;14.06s checkpoint save/hash | Similar full-SFT proxy; adapter training/export cost is unmeasured |
| [E016 phases](../../../runs/gsm8k_capability_e016_r1/phase_timings.json) |Base64 generation145.36s; E01564 generation80.71s; base load1.97s | Use the slower original-base point scenario,2.271s/question; the shorter failed model's outputs are not a target throughput |
| [E016 closeout](../../../reports/REAL_MATH_E016_RESULTS.md) |235s charged process;721s observed notification-to-provider-off span | AboutCNY1.60 at the stated rate, not an invoice or exact power-on span |

Scaling E015 training by supervision/processed-token ratios gives **76.82–79.51s**
for E018 training alone. This does not measure LoRA throughput; frozen-parameter
backpropagation, accumulation and kernel costs differ. E018's160 generations
have a363.39s point proxy; Stage C's128 have290.71s. Add model loading, NLL
passes, hashes, compact export and shutdown. C017 training alone is about522s
per arm by the same token-ratio proxy, before evaluation and overhead.

E017 may reduce generation tails but has no measured speed yet. Fixed batches
wait for their longest active row. Different evaluation lengths and new stopping
behavior invalidate treating per-question scaling as a guarantee. Stress-test
the planning estimates at twice the observed latency; that multiplier is not a
statistical bound. Update admission calculations from actual E017/E018 profiles
before seeking scientific execution review, and stop if a complete phase cannot
fit its cap rather than spend the unused project ceiling automatically.

| Conditional phase | Free generations | Proposed guarded process ceiling | Whole-rental ceiling | CNY at8/hour |
| --- | ---: | ---: | ---: | ---: |
| Existing E017 |64 |255s |15min |2.00 |
| P006 B / E018 |160 |915s |30min |4.00 |
| P006 C |128 |435s |20min |2.67 |
| Scientific seed17, three arms |192 observed-dev |3 x915s =2,745s |75min |10.00 |
| Scientific seed23, three arms |192 observed-dev |3 x915s =2,745s |75min |10.00 |
|368-parent scientific development, seven endpoints |2,576 |7 x1,815s =12,705s |4h |32.00 |
|1,319-question final test, seven endpoints |9,233 |7 x6,615s =46,305s |14h |112.00 |

Scientific per-arm process ceilings include training, observed-dev evaluation,
adapter save/hash and the15-second guard. The proposed development/test
ceilings respectively allocate1,800/6,600 worker seconds plus15 guard per
endpoint. Their total whole-window caps also include setup, compact/adapter
export and provider shutdown. These are new proposals, not existing registered
jobs. Greedy base results may be reused only for byte-identical model/input/
decoding contracts; the table conservatively counts a base once in each new
evaluation block. Historical E016 outputs cannot substitute for a fresh block.

The development evaluation's point generation estimate is97.51 minutes; the
official test's is349.50 minutes. Twice these estimates leaves finite overhead
within the4h/14h envelopes, subject to actual profiling. Evaluation therefore
dominates this design; training-only estimates substantially underprice it.

Suggested whole-window allocation, in seconds:

| Phase | Startup/preflight | Maximum guarded processes | Export allowance | Shutdown/slack | Total ceiling |
| --- | ---: | ---: | ---: | ---: | ---: |
| E017, already frozen |345 |255 |120 |180 |900 |
| E018, existing proposal |585 |915 |120 |180 |1,800 |
| Stage C, existing proposal |465 |435 |120 |180 |1,200 |
| Each three-arm scientific phase |300 |2,745 |360 |1,095 |4,500 |
| Scientific development block |300 |12,705 |360 |1,035 |14,400 |
| Final-test block |300 |46,305 |720 |3,075 |50,400 |

Unused time is not a target to consume. Recheck the remaining absolute deadline
before each admitted job, and retain adequate export/shutdown time. Do no paper
writing, literature review or open-ended debugging while billed. All windows
require provider-confirmed shutdown; no new machine or paid teacher API is part
of the request. Adapter transfer is bounded; a slow copy leaves uniquely required
state on a retained stopped volume for separate recovery, never a disposable one.

## 5. What would be approved, and what remains unknown

The **next conditional method/resource decision** is P006 B+C only:
1,350 additional guarded process seconds and at most50 rental minutes/CNY6.67,
after a valid E017 result and offline release. E017's15-minute/CNY2 authorization
already stands. Keep the original20 receipts and actual post-E017 receipt;
do not spend the last24-or-more seconds as an automatic continuation.

If every later scientific/test phase were independently reviewed and admitted,
the entire table would total21h35min/CNY172.67 of planned rental, including
E017, before storage, rounding, separate E015 recovery or other fees. The
proposed post-E017 guarded processes total65,850 seconds, with distinct phase
records; none is authorized by this estimate. B/C is a subset of that total,
not an additional charge to add again.

The shared CNY3,000 ceiling is not remaining cash, and279 historical process
seconds are not a permanent restriction on the research project. Actual billed
spend, balance, provider rounding and other fees remain unknown. A paid later
phase must fit both a reviewed process authorization and the remaining shared
financial ceiling after those charges are reconciled. Do not issue parallel
allowances to the two research workstreams or count the same receipt twice.

Submission readiness is a separate decision from affordable compute. The
budget cannot purchase a novelty claim; if the closest-work or evidence gates
fail, preserve the work and continue the research beyond September25.
