# Identity-absent boundary: a small primary gap without trace or broader support

**Completed2026-09-09 UTC.** Paths scores **7/64** and GCM **5/64** on the
prespecified matched-development greedy final-expression endpoint: a net two
questions, or3.125 percentage points. Complete verified traces are **4/64 each**.
On broader development, Paths is **0/64** and GCM **2/64**, for both final
expressions and complete traces. These outcomes do not justify scaling a claim
that within-question path diversity consistently improves reasoning. They also
do not establish a zero effect or identify identity operations as the cause.

## Why this experiment, and what previous failures changed

The original selected256-question pilot gave Paths-minus-GCM primary gaps of
five questions at both seed17 and seed23, but little broader success. CPU audits
found substantial identity-operation exposure and selection from exact matching.
C009's capped search did not measure total shared support; C010 timed out;
C013 finally enumerated the complete old-design grid and found only15 feasible
four-question blocks. C011 shows both length and structure constraints change
the eligible population. These failed/incomplete attempts remain in the journal.

C012 fixed an identity-absent boundary *before* learning its support counts or
new model outcomes. It removed requirements for an unused identity-present
alternative family while retaining exact within-question token matching and
four shared structures per update. An optimal33-block packing supplied32 blocks
chosen by a separately seeded Random31:128 training questions. This is a
feasible narrower allocation question, not a repair that makes the original
question population representative. See the [CPU reasoning and selection analysis](MATCHING_COMPLETION_AND_TRAINING_20260909.md).

The [E010 execution entry](../docs/experiments/E010_absent_boundary_seed31.md),
full [training protocol](../docs/ABSENT_BOUNDARY_TRAINING.md) and all294 passing
[Linux tests](a800_absent_preflight_20260909_r1/tests.log) were published before
launch at `9217685f6bdb4d0c67a0d76513c12f89898593cb`. Both arms ran that same
clean commit. The later running-status commit changed documentation only and
was not synchronized onto the server between arms. No outcome-dependent recipe,
endpoint, stratum, checkpoint, dose or decoding selection occurred.

## Exact design and execution

Both arms independently start from pinned Qwen/Qwen2.5-1.5B **base**, revision
`8faed761d45a263340a0528343f099c05c9a4323`. Full FP32 AdamW parameters/states,
BF16 autocast,LR5e-5,WD0.01,clip1,batch4/microbatch2 and length limits384 remain
the measured recipe. Assignment/order/training seed31; evaluation seed17.
No previous fine-tuned checkpoint is resumed. Repeat/Surface compatibility
files are audited data, not additional trained models in this phase.

Each arm completed1024 updates and4096 presentations:128 questions32 times
each, with Paths presenting four different trajectories eight times each and
GCM repeating one seeded trajectory32 times. Both have277760 supervised
response tokens including EOS,482848 nonpadding processed tokens and3734
padding tokens. Ordered questions, token counts, structures and operator
histograms match at every update. The frozen data manifest SHA256 is
`cd9a72d187dbb18f2b75b743ccc0cf85c94951ee574c07e55ed8ddf1f4a1ab97`.

Both runs completed on their first model attempt within1050-second per-run
limits, each charging512 seconds. One earlier noninteractive shell lacked a
bare `python3`; it exited before any job or reservation, and the verified
absolute interpreter resolved it. No GPU retry, OOM, nonfinite history,
truncated generation or incomplete-dose exclusion occurred. Both measured
26857.17MiB peak allocated memory; profile supervision throughput was702.38
versus706.21 tokens/second. The server did not require disk expansion or cleanup.

The full queue ran18:24:48–18:41:53 UTC. Runtime receipts count model loading,
training, evaluation and checkpoint saving; cloud idle/transfer/storage charges
are separate. No A800 monetary cost is inferred from the old4090 price.

## Primary and secondary outcomes

| Endpoint | Paths | GCM |
|---|---:|---:|
| **Matched greedy final expression, primary** | **7/64 (10.9375%)** | **5/64 (7.8125%)** |
| Matched complete displayed trace |4/64 |4/64 |
| Broader greedy final expression |0/64 |2/64 |
| Broader complete displayed trace |0/64 |2/64 |
| Matched sampled pass@1 |9.375% |7.03125% |
| Matched sampled pass@2 |13.02083% |8.85417% |
| Matched sampled pass@4 |17.1875% |10.9375% |
| Correct sampled generations |24/256 |18/256 |
| Complete sampled traces |13/256 |15/256 |
| Fixed training16-question greedy diagnostic |11/16 |16/16 |
| Final100 updates' mean response NLL |0.0402921 |0.00600517 |
| Final matched-reference NLL |0.674792 |0.870193 |
| Matched greedy parse failures |5/64 |3/64 |
| Broader greedy parse failures |2/64 |2/64 |
| Truncations across all400 outputs per arm |0 |0 |
| Charged process-seconds |512 |512 |

The primary paired cells are **3 both correct,4 Paths only,2 GCM only,55 neither**.
Complete-trace paired cells are1 both verified,3 Paths only,3 GCM only,57 neither.
Broader expression and trace cells are0 both,0 Paths only,2 GCM only,62 neither.
Thus the net two-question primary advantage is supported by only six discordant
matched questions, not64 independent treatment replications. Four sampled draws
per question share the same problem; pass@k and draw counts are secondary, not
extra independent experimental units. No significance claim is made.

The full trace audit requires exact calculations, legal input consumption and
connection to the final ordered expression. Three correct Paths greedy answers
and one correct GCM greedy answer lack a fully verified displayed trace. This
does not overwrite final-expression correctness or measure hidden faithfulness.

Prespecified descriptive strata remain in the [complete audit](absent_boundary_seed31_after_gpu_audit_r1/summary.json):

| Frozen matched-dev label | Questions | Paths/GCM final expression | Paths/GCM complete trace |
|---|---:|---:|---:|
| No input1 |32 |5/4 |2/3 |
| Has input1 |32 |2/1 |2/1 |
| None of four stored references uses an identity operation |16 |5/4 |2/3 |
| At least one stored reference uses an identity operation |48 |2/1 |2/1 |

These labels were fixed before seed31 but were post hoc for seed17. They refer
to the stored references, not all possible solutions. The16 block-level strata
and every prediction are retained in the same audit; no favorable block is
selected for the headline. The especially weak48-question reference-identity
slice is compatible with changed train/development support, but does not identify
that explanation as causal.

## What the results support and what they do not

**The favorable primary direction alone is insufficient.** It shrinks to two
questions on this boundary; complete greedy traces tie, sampled trace counts
favor GCM, and broader expression/trace outcomes favor GCM. Endpoint dependence
and low absolute success argue against buying a large grid on the strength of
this result. This is a scientifically retained weak boundary result, not a
technical failure to be rerun until positive, and not proof of no benefit.

**The comparison with earlier scores is descriptive only.** The old matched
scores were23/18 and22/17. The new pair changes from256 to128 training questions,
16 to32 exposures per question and267456 to277760 supervised tokens, as well as
the selected legal paths and joint seed. Therefore neither the absolute decline
nor the changed Paths–GCM gap estimates the effect of removing identities.

**Matching does not remove all numerical or population differences.** The
selected128 questions include33 high targets,55 targets equal to an input and
18 questions containing1, while matched development has32/64 containing1.
Per-update structure equality coexists with per-question depth/negative exposure
differences and intermediate-magnitude differences on600/1024 updates. Absence
of explicit neutral operations still permits cancellation and computed constants.
These were recorded before GPU outcomes and were not tuned away afterward.

**Training diagnostics do not settle the mechanism.** GCM memorizes its fixed
16-question diagnostic better and has lower supervised training loss; Paths
has lower final development reference loss. GCM's one-target repetition and
Paths' multiple targets have different conditional target uncertainty, so their
training NLLs are not an independent measure of reasoning ability. The16-question
diagnostic is not a census of whole-training accuracy. There is no evidence here
that extending only one arm's training would preserve the intended comparison.

## Decision and concrete next work

Stop after the finite pair. Retain the narrow seed17/23 observation and E010's
limitations; do not claim ICLR readiness or run a seed/learning-rate search.
The next scientific task is a CPU-only design review with a written decision:

1. Define a population-level allocation estimand and a task generator with
   multiple valid paths by construction. Assess a graph/relational or controlled
   symbolic task without conditioning most questions on a rare matching event.
   A constructive task is a candidate, not a claimed solution to all confounding.
2. Before any model run, audit train/development support, shortcuts, gold-solver
   correctness, split separation and exact exposure accounting. Distinguish the
   treatment's intended target multiplicity from nuisance numerical difficulty.
   A new development set requires a new design record; do not rewrite E010's
   evaluation to make its scores look better or access the reserved holdout.
3. Prepare a small falsifiable comparison and independent-seed plan with cost
   and stopping gates for owner review. No new scientific factor, main grid or
   GPU launch is authorized by this report. The remaining1460 seconds cannot
   reserve another2130-second pair at the current caps.

Task-mode recommendation: Max remains appropriate for frozen execution,
verification and recovery. A later broad scientific redesign with separable
critical reviews is a candidate for Ultra. This is a recommendation, not a claim
that any setting was changed or that delegation is authorized.

## Evidence and recovery

All800 saved outputs and complete per-update budgets passed the server audit
and an independent local rerun. Their10 audit files are byte-identical; see the
[independent verification receipt](absent_boundary_seed31_independent_verification.json),
[raw Paths run](../runs/absent_boundary_paths_seed31_r1/),
[raw GCM run](../runs/absent_boundary_gcm_seed31_r1/) and
[machine-readable comparison](absent_boundary_seed31_after_gpu_r1/results.json).
No new model inference or holdout evaluation was used for the CPU audit.

Both new512-second receipts and all13 prior receipts exactly match the separately
downloaded cumulative ledger: **5740/7200 seconds used,1460 remaining,15 receipts,
zero reservations**. [Ledger verification](absent_boundary_seed31_ledger_verification.json)
records SHA256 `1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
The original13 jobs are unchanged. The registry and accounting retain all earlier
failed attempts. The2048 raw holdout groups remain unsolved/unevaluated.

Independent preservation is complete: both checkpoints,24 files and
12,381,607,162 bytes passed SHA256 verification. See the [backup summary](absent_boundary_seed31_checkpoint_backup_summary.json)
and [fresh idle/ledger check](absent_boundary_seed31_final_server_check.json).
All weights remain outside Git and are not optimizer/RNG resume state. The
result milestone was published at `3585ad2d2f6424180b4b3ec345904dc0fc21fea6`
and synchronized cleanly onto the server; all compact records and the final
ledger are independently retained. No required unique artifact remains there.

Normal shutdown is authorized. At this preservation milestone the Mac is locked,
so authenticated console verification is unavailable. The vendor documents
`/usr/bin/shutdown` for automatic shutdown; the installed helper was inspected,
and its trash-removal path is absent. Use the vendor helper only after the
published preservation gate and a fresh idle/ledger/instance check. Record a
shutdown request separately from verified provider stopped state. A disconnect
alone does not prove that billing stopped; retain a follow-up for console
confirmation after unlock. See [AutoDL's shutdown instructions](https://api.autodl.com/docs/save_money/).
