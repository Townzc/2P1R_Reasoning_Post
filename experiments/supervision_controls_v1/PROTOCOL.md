# LT002 — supervision controls and development decoding diagnostic

Date: 2026-09-28 America/Los_Angeles. Owner resumed long-term research and requested
concrete experiments before October 1. This is a bounded exploratory phase, not
the full three-seed confirmation plan or a new claim that QDW improves reasoning.
The complete E044–E047 results at `cb9b6b40a6904d5d7ea2c75e63b73db7141a27ec`
supersede the old LT001 execution baseline. LT001's acquisition question remains
a separate, unexecuted proposal. Historical results and resource ledgers are immutable.

## Questions

1. Does QDW differ from controls with the same amount of reweighting, especially
   after matching the coarse position and frozen-base difficulty of selected tokens?
2. Does method ranking change between greedy and T=1 sampling on the **same**
   development questions? Prior GSM-greedy versus MATH-sampled results confound
   question distribution with decoding and do not answer this question.

## Fixed scientific design

- Reuse the original Qwen2.5-Math-1.5B base revision, frozen 4,096 Numina training
  questions, answer/EOS serialization, full-parameter FP32 AdamW with BF16
  autocast, seed17 order, 32 examples/update, 128 updates, original LR schedule,
  clipping and raw-token denominator. Each new arm starts from the public base.
- Keep original QDW masks, existing endpoint weights, and the four original
  step128 greedy-dev outputs. Verify every identity and raw output before reuse.
- Train only two new arms: **random** and **position_difficulty**. Both preserve
  each answer's exact QDW selected count K, eligible region, multiplier5 and
  normalized total weight L. No answer, EOS, whitespace or prompt position is
  newly eligible. Zero-K examples remain in the training denominator.
- Random samples K positions uniformly from the eligible positions of that answer.
- Matched samples preserve QDW counts within a 4×4 cross of relative-response-position
  bins and within-answer frozen-base NLL quantile bins. Equal-NLL ties stay together.
  All original eligible positions remain available; excluding original selections
  would change the null and force infeasible cells. Report overlap, forced-overlap
  lower bounds, changed-mask fractions and continuous-feature residuals. Coarse
  matching does not establish exact difficulty balance or causal semantic keyness.
- Selection seed2026092901 is derived separately by immutable problem ID/condition.
  No mask selection uses development/test predictions. One fixed mask draw is
  exploratory; it is not an independent training seed or mask-seed replication.
- Evaluate all six trained states on the original **512 observed Numina dev**
  questions under greedy and T=1/top-p1/top-k0 sampling, one sampled draw with
  seed2026092902 and the existing 2,048 output-token cap. Same batch16 and
  generation/scoring implementation across conditions. Existing four greedy runs
  are reused only if their full contracts and hashes match.
- Planned new dose: **256 optimizer updates; 0 new annotation forwards; 4,096
  generated answers** (two new greedy runs plus six sampled runs). Missing original
  annotations/checkpoints/outputs is a preparation blocker, not permission to replay.

## Analysis fixed before new outputs

Primary exploratory contrasts are QDW minus each control in greedy dev accuracy.
Report paired differences and 97.5% whole-question bootstrap intervals for the two
contrasts, retaining all512 questions and unresolved bounds. Compare the same
contrasts under sampling and report the paired difference of decoding effects.
Also report all SFT/DFT/TrimSFT scores, sample lengths, parsing failures and caps.
No result-based exclusion, early stop, checkpoint selection, parameter sweep or
public-test re-evaluation. Intervals condition on one training seed and one mask
draw; an interval containing zero is not evidence of equivalence.
Bootstrap uses 10,000 replicates with fixed seed 2026092903.

Prespecified interpretation: attenuation of the point gap after matching is
descriptive. Report matched-minus-random as a secondary paired contrast; a
non-significant QDW-minus-matched contrast alone does not establish an explanation,
equivalence or sufficient power. A gap surviving matching motivates independent
confirmation, not a causal-key-token or novelty claim.
A decoding interaction on Numina dev shows sensitivity there; it cannot explain
the complete GSM/MATH difference or establish out-of-distribution transfer.

## Finite resource plan before startup

Planning reference: previous same-recipe four-arm training processes took61.9min;
dev generation batches totalled3.97 worker-hours for4,576 non-reused outputs.
Sampling latency is unmeasured for this new development contract. On one A80080GB:

| Stage | Planning wall time | Basis |
|---|---:|---|
| Artifact/CPU mask checks and setup | 20–40min | estimate; no new model annotation |
| Two 128-update runs, with saves | 30–50min | prior four-arm measured time, plus margin |
| 4,096 dev generations | 3.5–5h | greedy timing extrapolation with sampling margin |
| CPU scoring | 15–45min, overlapping generation | estimate, prior scorer and same references |
| Verification and normal shutdown | 15–25min | explicit rental reserve |
| Complete powered window | about4.5–7h | sequential one-GPU planning range |

Proposed **hard ceiling8h / CNY64 at CNY8 per GPU-hour**, excluding storage;
this is a phase cap, not a reset of the shared CNY3,000 historical ceiling.
Account funds/rate, current instance state, disk and runtime require fresh checking.
Request one A80080GB; two-card rental would need a revised cost/duration plan.
Training previously allocated33.41GiB at engineering peak; generation uses batch16.
Require at least50GiB GPU free for the inherited training admission and enough
host headroom for full optimizer saves, plus measured disk admission before loading.
Do not automatically start/rent/reconfigure a server or promise a measured A100 speed.

Use a finite detached queue with a registered absolute deadline, per-batch
reservations, immutable outputs, bounded completion/closeout and provider-confirmed
normal shutdown. Stop on missing/mismatched artifacts, OOM, source drift, budget
admission failure or ambiguous outstanding work; preserve failures. No automatic
failed-generation retry or training replay. Finish early and shut down immediately.
The old stopped volume reportedly faced automatic release around October3;
recheck actual retention before dependent work, without deleting or moving it.

## After this exploratory phase

Prepare the factual result, negative/uncertain findings and two or three scientific
questions for the research discussion. Freeze a distinct confirmation protocol
before three independent training seeds or fresh confirmation data. Those runs,
CFT, a larger model, additional benchmarks and expanded acquisition work are
outside this finite queue. Keep personal correspondence and meeting notes private.
