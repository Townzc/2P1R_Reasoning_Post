# Seed23 paired replication: primary direction repeats, broader transfer does not

**Completed 2026-09-09 UTC.** On the same restricted 64-problem development set,
Paths scores **22/64** and GCM **17/64** on the prespecified primary endpoint,
greedy final-expression correctness. The net difference is five problems, as in
seed17. Complete verified calculation traces are only **18/64 versus 16/64**;
broader development is **1/64 each**, with complete traces **0/64 versus 1/64**.
This supports a limited fixed-pool stability result, not general reasoning
improvement, an identified mechanism, statistical significance or ICLR readiness.

## Why this attempt and how it was fixed

The [registered question](../docs/experiments/E009_seed23_paired_replication.md)
asks whether seed17's primary direction depends on one allocation/order/training
seed. It was fixed after seed17's post-hoc audits, before seed23 outputs. The
research journal was published at `3fb43907c0fb8c951b50adfad6dabcc1bfde6403`
before either new GPU run; this is a repository record, not external registration.
Both arms executed source `6128e4266d62f14f063585d4c8e94dbe3ad8c711`.

Paths presents four distinct legal reference paths per selected problem. GCM
assigns one of those paths to each problem and repeats it, with canonical global
and per-update structure frequencies matched across arms. Both start separately
from the pinned Qwen2.5-1.5B base; no trained checkpoint is resumed.

The experiment preserves the 256 training problems, both 64-problem development
sets, full-model FP32 trainable parameters and AdamW states with BF16 autocast,
learning rate and decoding settings. The joint
assignment/order/training seed changes from 17 to 23; evaluation seed stays 17.
These sources of variation are not separately identified. GCM assignments change
on 196/256 problems; all 1024 update orders change; Paths' aggregate path inventory
is unchanged. There is no new problem pool, holdout evaluation or dose tuning.

Each arm completed **1024 updates, 4096 presentations, 267456 supervised tokens
including EOS, 472832 processed tokens, and zero training padding**. The frozen
data manifest is `0959c217feb4b0c51aebf85c1f08e341e1b6c8034657ee028acb263a2ee18ad4`.
All 96 Linux tests passed before launch, and both final output audits reconcile
the planned and actual exposures and rescore predictions from text. Both jobs
completed on their first attempt; no efficacy stopping, failed-arm exclusion,
extra seed, additional inference or replacement run occurred in this phase.

## Outcomes, retaining primary and secondary endpoints

| Endpoint | Seed17 Paths | Seed17 GCM | Seed23 Paths | Seed23 GCM |
|---|---:|---:|---:|---:|
| **Matched greedy final expression — primary** | **23/64** | **18/64** | **22/64** | **17/64** |
| Matched complete trace | 21/64 | 14/64 | 18/64 | 16/64 |
| Broader greedy final expression | 4/64 | 1/64 | 1/64 | 1/64 |
| Broader complete trace | 1/64 | 1/64 | 0/64 | 1/64 |
| Matched sampled pass@1 | 28.125% | 27.344% | 35.156% | 24.219% |
| Matched sampled pass@2 | 40.104% | 30.729% | 47.135% | 30.469% |
| Matched sampled pass@4 | 51.563% | 34.375% | 54.688% | 37.500% |
| Correct sampled generations | 72/256 | 70/256 | 90/256 | 62/256 |
| Complete sampled traces | 59/256 | 57/256 | 70/256 | 55/256 |
| Sampled problems with any success | 33/64 | 22/64 | 35/64 | 24/64 |
| Training diagnostic greedy | 9/16 | 14/16 | 11/16 | 15/16 |

Each sampled problem has four draws. Pass@1/2/4 use the existing combinatorial
estimator, not additional independent decoding runs. Training diagnostics cover
only the fixed 16-problem sample; their difference does not measure whole-training
performance. Seed23 matched greedy parse failures are 2/64 versus 0/64; both arms
have zero truncations across the saved evaluations. The complete-trace audit is
secondary and does not rewrite the official final-expression score. It requires
exact arithmetic, legal input consumption and a connection to the final ordered
expression tree; unknown syntax and unconnected equivalent expressions remain
unverifiable. It does not measure hidden reasoning faithfulness.

| Paired matched-dev outcome | Seed17 | Seed23 |
|---|---:|---:|
| Both final expressions correct | 11 | 11 |
| Paths only correct | 12 | 11 |
| GCM only correct | 7 | 6 |
| Neither correct | 34 | 36 |

For seed23 complete traces the paired counts are 10 both verified, 8 Paths only,
6 GCM only and 40 neither. Among correct greedy final expressions, four Paths
outputs and one GCM output have inconsistent traces. Thus the repeated primary
gap does not establish an equally stable improvement in complete calculation
reliability. All 800 saved seed23 predictions, including errors, have CPU audits.

## What changed in the explanation

**The primary direction repeats; its apparent location does not.** In seed17,
the 16 matched problems whose four stored references contain no identity
operation contribute the entire greedy net difference (8 versus 3). In seed23
that group is 5 versus 5; the other 48 problems are 17 versus 12. These reference
labels were fixed before seed23 but were post hoc for seed17. They describe the
stored four paths, not all mathematically possible solutions. This movement
weakens an explanation that attributes the primary gain to one identity stratum.

Sampled any-success is more consistently concentrated on the 32 matched problems
containing input 1: Paths/GCM is 22/12 in seed17 and 25/14 in seed23; without input
1 it is 11/10 and 10/10. This remains descriptive. Input 1, legal path support and
difficulty differ jointly; these data do not show that input 1 causes an effect.
Also, the near-equal total sampled successes in seed17 (72/70) do not repeat in
seed23 (90/62). A story of *only* redistributed success with an unchanged average
single-draw success rate is not a cross-seed result.

**Broader development remains the largest performance gap.** Both arms answer
just one of 64 broader problems correctly in seed23, and the Paths calculation
for that answer is inconsistent. This selected complement is neither an IID
population sample nor a demonstrated compositional OOD benchmark. The result
nevertheless provides no evidence of useful broader transfer under this recipe.

**Exact structural matching is narrower than semantic matching.** The independent
[training-exposure audit](PAIRING_SEED_SEMANTIC_AUDIT_20260909.md), completed during
training without reading new evaluation outcomes, finds identity exposures of
2780 versus 2800 out of 4096 presentations in both seeds. It also records zero,
intermediate-one, sign and depth profiles and per-update residuals. None of the
selected training paths has fractional intermediate values, although the solver
allows them. Numerical properties can be part or a consequence of the allocation
intervention; they are not automatically nuisance confounders to adjust away.
The current estimand is a contrast between the specified allocation procedures
on this fixed pool, conditional on the recipe and joint seeds.

## Scientific decision and next falsifiable step

Do not expand the same positive-results table yet. The closest inspected prior
work already studies per-problem versus global diversity and coverage; see the
[positioning audit](ICLR_POSITIONING_20260909.md). Tighter accounting and a second
seed alone do not establish a substantive new ICLR contribution.

The candidate next question is whether the allocation benefit depends on
different numerical calculation structures or also appears for alternative legal
ways of consuming required inputs. In Countdown, multiply/divide by one may be
necessary to use every input once. Such a path is legal and is not merely the
Surface wording control. Simplification is an analysis projection and must not
erase input provenance from the actual examples.

The [small inventory feasibility check](SEMANTIC_CONTROL_FEASIBILITY_20260909.md)
already rules out a naive reuse design: numbers of identity-containing paths
among the four stored paths have distribution 0/1/2/3/4 = 72/0/0/41/143 problems.
Only 41 problems support at least one path of each binary category; **zero**
support two of each. This says nothing about undiscovered paths outside the
stored inventory. It is a failed construction, not a failed neural hypothesis.

Next, define the legal path equivalence/projection and the intended contrast on
CPU, then test shared support in a separately specified development construction.
Record every eligibility loss and residual in operator/depth/numerical exposure,
token dose and update matching. Fix problems and audit difficulty proxies rather
than claiming all difficulty is controlled. If the intervention lacks adequate
shared support, redesign or record that it is not yet identifiable; do not simply
remove input 1, train unrelated pools and attribute the difference to a mechanism.
The [roadmap](../docs/ICLR_EXPERIMENT_ROADMAP.md) retains later independent pools,
uncertainty and task/model boundary gates. No later GPU phase is authorized by
this report, and the 2048 reserved raw holdout groups remain unsolved/unevaluated.

Two joint seeds share one training pool and the same 16 selected matched-dev
blocks. They are not 128 independent new test problems, nor independent dataset
replications. No seed-level significance or power claim is made. Stronger
uncertainty and generalization require a new fixed design, not reinterpreting
these counts as independent observations. The present decision is **keep the
narrow stability finding; investigate a controlled boundary before more GPU work**.

## Runtime, preservation and reproducible evidence

Paths elapsed 499.181 seconds (charged 500), GCM 503.475 (charged 504), together
**1004 process-seconds**. Both peak at 26836.27 MiB allocated on one A80080GB.
The original cumulative allowance is now **4716/7200 used, 2484 remaining**,
with 13 receipts reconciled and no unresolved reservation. Instance idle time,
data transfer and storage billing are separate; no A800 price was supplied.

The 50 GB data disk was sufficient after re-verifying and deleting only four
already backed-up seed17 weight directories (24,763,214,324 bytes). Model cache,
environment, source and compact results were retained; free space became 41.16
GiB before new checkpoints. No disk expansion or altered training precision was
needed. See [cleanup proof](replication_seed23_storage_cleanup_20260909.json).

**Backup status at this results milestone:** raw records and the current private
ledger are local; both new weight downloads are in progress. The instance is not
yet disposable. Completion requires all 24 checkpoint files to pass independent
SHA-256 verification, plus a published recovery milestone and final idle check.

Evidence paths:

- [Registered E009](../docs/experiments/E009_seed23_paired_replication.md),
  [research journal](../docs/RESEARCH_JOURNAL.md), and
  [frozen protocol](../docs/PILOT_REPLICATION_PROPOSAL.md).
- [Official result snapshot](pilot_replication_seed23_after_gpu/results.json),
  [full trace/stratum audit](pilot_replication_seed23_after_gpu_audit/summary.json)
  and its raw per-generation/per-problem files.
- [Paths raw run](../runs/pilot_replication_paths_seed23_r1/) and
  [GCM raw run](../runs/pilot_replication_gcm_seed23_r1/): source/config manifests,
  full training histories, predictions, dose, checkpoint hashes and receipts.
- [Paths output verification](pilot_replication_paths_seed23_r1_output_verification.json),
  [GCM output verification](pilot_replication_gcm_seed23_r1_output_verification.json),
  [ledger verification](replication_seed23_ledger_verification.json),
  [all attempts](run_registry.json), and [resource accounting](compute_accounting.json).

To reproduce the CPU analysis from the retained records, use fresh output paths:

```bash
python -m scripts.report_pilot \
  --queue configs/pilot_replication_seed23/queue.json --out reports/review_seed23
python -m scripts.audit_replication_outputs \
  --queue configs/pilot_replication_seed23/queue.json --out reports/review_seed23_audit
```

The audit requires complete matching-source runs and validates official scores,
data bytes, fixed labels and dose before producing any secondary result. It does
not launch model inference or evaluate the holdout.
