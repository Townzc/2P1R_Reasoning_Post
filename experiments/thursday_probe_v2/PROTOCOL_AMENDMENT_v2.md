# Thursday arithmetic factorial, protocol v2 — authorized September 16, 2026

The owner explicitly requested execution of the post-E018 revision. This amendment
applies only to new arithmetic runs. E018 remains `completed_failed_retention`:
34/39 retained, below90%, with its original data, scores and implementation kept.
Neither that adapter nor its253 noisy text examples enters this phase. The previous
stop was correct under its protocol; its retention threshold no longer governs
the distinct arithmetic research task. No literature review is repeated.

## Frozen scope and estimand

Use only the existing `thursday_probe/data_r1` primary interface, subtraction
feeding multiplication (`-->*`). Keep256 main questions,96 discovery questions,
the shared Surface/Paths records, anchors, seeds and two prep recipes unchanged.
The other candidate interfaces, Repeat/Breadth/Balanced, RL, additional models,
reserved arithmetic confirmation set and official GSM8K test are excluded.

The exploratory contrast is prep recipe × main recipe:
delta_C=Y(C-P)-Y(C-S), delta_B=Y(B-P)-Y(B-S), I=delta_B-delta_C.
It is not an identified pure within-question-diversity or internal-skill effect.
Fine-structure TV0.08984375 and2.752% prep token imbalance remain. The common
fine-structure residual can interact with parent state and need not cancel in I.
There is one prep/training/assignment seed combination, not a seed replication.

## Data audit and selections, frozen before any new model output

`release_r2/manifest.json` binds all selections, schedules, token counts and
registered IDs. The first CPU preparation is retained in `release_r1`: its ID
allocator mistakenly treated hash substrings as IDs. It was never run or
registered. The repaired allocator reads run identity fields only and reserves
E030–E036, leaving old unused E019–E029 aliases unchanged. Arithmetic examples
and all numerical selections are identical between those CPU preparations.

The256 main and96 discovery questions are retained in full. Identity-anywhere
uses the existing local +0, -0, *1, /1 definition. Target degeneracy examines
actual adjacent child-parent edges: subtraction result0/1, other multiply factor
0/1, or subtraction's right operand0. A program with multiple target edges is
nondegenerate only when every such edge avoids these rules. No target edge means
`target_nondegenerate=false`; this is not a claim of degeneracy for target-absent A.
Local rules do not rule out all algebraic cancellations or measure cognition.

Reference B defines the prospective question subgroups. Train:202 nondegenerate,
54 degenerate; discovery:79 and17. Every B has the target edge and every A lacks
it. Identity-anywhere counts are59/57 for train A/B and18/19 for discovery.
Full intersections and per-reference labels are saved, not inferred from counts.

Calibration reuses all48 existing questions. Hash-order separately within each
existing category; fit8 construction+12 target-compute+12 control-compute,
check8+4+4. Assign construction A/B alternately and the two existing frames in
crossed pairs. Compute target=B/control=A, alternating the same two frames over
one/two calculation lines. Fit has16/16 coarse types and16/16 styles; check8/8.
Each question has one exact executable reference. Calibration is a small-data
learning/format check; its adapter is never a scientific parent.

Sentinel: hash-select16 of each32 probe category,48 total. Parents reuse samples
0/1 from n=4; each child produces n=2. Midpoint: hash-select24 of the96 discovery
questions before outputs. Subgroups, sentinel and midpoint lists never depend
on a model score. Whole-instance/number-group intersections are zero across
roles, except the intentionally shared128 atomic prep instances.

## Uniform model, optimization and branching

Qwen/Qwen2.5-1.5B Base revision `8faed761d45a263340a0528343f099c05c9a4323`;
same pinned tokenizer, PEFT0.17.1, LoRA r16/alpha32, q/k/v/o/gate/up/down,
dropout0, bias none. FP32 frozen base and trainable adapters, BF16 autocast,
SDPA, TF32 off. AdamW betas(.9,.999), eps1e-8, weight_decay0, clip1,
effective batch16, microbatch1. Training seed17; other frozen seeds in the release.
Peak LR5e-5; original linear warmup round(steps/16) and cosine floor1e-5.
No condition-specific parameter, seed, dose, length or learning-rate changes.

| ID | State | Start | Rows / presentations / updates |
|---|---|---|---|
| E030 | Independent calibration | Original C0 |32 /512 /32|
| E031 | C control prep | Original identical C0 |256 /512 /32|
| E032 | B bridge prep | Original identical C0 |256 /512 /32|
| E033 | C-S | Independent copy of C |512 /4096 /256|
| E034 | C-P | Independent copy of C |512 /4096 /256|
| E035 | B-S | Independent copy of B |512 /4096 /256|
| E036 | B-P | Independent copy of B |512 /4096 /256|

All seven runs total1120 updates. Preserve23 complete adapter directories:
one C0, calibration/prep0/32, and main0/64/128/256. Every stage creates a fresh
optimizer and scheduler. Copy parent tensors into the same fixed adapter capacity;
never merge adapters, add rank or train Surface then Paths sequentially.
Save recoverable adapter+AdamW moments+RNG+exact schedule/fingerprint every16
updates and at completion. Atomically commit each latest pointer before pruning
its previous rolling recovery file; scientific adapter checkpoints remain immutable.
Recovery is possible into a separately identified attempt; no automatic replay.

All training labels include native EOS; prompt and padding are ignored; no packing
or response truncation. Divide each update's summed shifted CE by its entire
supervised token count across microbatches. Cumulative supervised tokens already
include all epochs: calibration23856; prep C16278/B15842; each Surface265744,
each Paths265664. Main maximum75 response tokens and calibration maximum69 fit
the common512 decode limit without trimming any reference.

## Evaluation and outcome-independent continuation

The fixed first pass is4704 new generations: the4608 core plus96 C0 discovery
greedy from the256 reserve;160 reserve remain unused. Cap4864, no E018 recharge.
All six scientific states get the same96 questions, n=4 sampled plus greedy.
Three probe states C0/C/B get96×4; all four children get24 midpoint greedy and
48×2 sentinel. Calibration is48 before/after greedy. Optional768 prefixes and
uniform +2304 for n=8 remain disabled in this first-pass execution. The proposal's
7936 absolute optional ceiling does not authorize an automatic extension.

Use temperature0.7/top_p0.95/top_k0, sample seed2026091603, batch8,512 tokens,
native EOS/task-boundary stopping. Save raw prompt/generated/batch IDs, stop
events and invalid/capped failures in the denominator. Accept every mathematically
valid final expression, including nonreference programs; unknown reference
program classes stay unknown. Final correctness, trace verification and output
format/stop behavior are separate. Compute-task numeric answers are not required
to repeat their input expression; displayed-step audits are supplementary.

Sequence: C0 measurements and independent calibration; two prep states/probes;
all four main trainings; all six common free evaluations; child sentinels.
Midpoint measurements are collected during each main run. Probe accuracy,
statistical significance, NLL improvement, retention and Paths benefit never
select whether a cell runs. NLL failure is a learning warning plus implementation
inspection, not permission for a sweep. No score-driven candidate fallback.

Stop for incorrect/nonexecutable references, identity/full-instance leakage,
mask/EOS/token bugs, zero labels, no parameter change, nonfinite state, unequal
undeclared recipes, invalid scoring/length contracts or exhausted resources.
Caps alone are failures in a common metric, not a score threshold. A systematic
length/scoring hard error means that the agreed contract cannot fairly score the
task (including references not fitting or false/mismatched stop records); retain
the failure and repair/version the contract uniformly before another attempt.

## Statistics and interpretation

Primary: mean of per-question sampled pass@1. With n=4, pass@4 is any success
among four, not pass@8. Greedy is separate. Report all six raw state means,
paired delta_C/delta_B/I, per-question gain/loss, full and reference-defined
nondegenerate/degenerate subsets, parsing/stops/lengths and trace correctness.
Use10000 paired question bootstraps and reference-B canonical-structure cluster
bootstraps, seed2026091604. Freeze this cluster rule before outputs; report the
number of clusters and no cluster interval for a single-cluster stratum.
Intervals exclude training, prep and assignment seed uncertainty. Multiple
descriptive subgroups are not independent confirmatory hypotheses.

Prep: report raw atomic/target/control means for C0/C/B, changes from C0,
delta_target, delta_control and D=delta_target-delta_control. Sentinel compares
the same48 questions at n=2; parent batch grouping differs from new child n=2,
so do not claim identical random streams. Weak/no prep separation limits the
student-familiarity interpretation, not the completeness of the factorial result.

## Resource and exit plan

This finite phase uses the existing single owner-started A800 and previously
authorized CNY3000 overall ceiling. No recharge, paid teacher or second instance.
Historical billed spend/remaining money ceiling are unknown. Verify current
price/balance before launch; old7.98/h is not a current quote.

New phase process cap8400 seconds plus15-second kill grace, separate from the
immutable21-receipt/7001-second original ledger and371-second E018 phase.
Whole powered-on cap10800 seconds, maximum verified rate10CNY/hour, compute
cost cap30CNY before unverified storage/rounding. These are bounds, not time or
cost predictions. Require1500 seconds for export/shutdown and enough remaining
time for the entire process cap after setup. After the calibration, use measured
training-token and sampling throughput with1.5 safety factor plus420 seconds
for checkpoint work to admit the complete remaining factorial. Insufficient
budget stops for resource reasons, with all actual observations preserved.

CPU preparation/tests and source publication precede owner startup. Set provider
automatic shutdown before model load. Require4.5GiB free for this adapter-only
queue; no old weights are reclaimed. Export outputs incrementally, then verify
all final file sizes/hashes, adapters and seven recovery states independently.
Confirm provider shutdown, then perform full local analysis/publication. SSH or
Python ending is not shutdown evidence. E015 remains protected; its independent
full-weight backup is still an unrelated open item. No next experiment follows
this finite queue without the owner's next plan.
