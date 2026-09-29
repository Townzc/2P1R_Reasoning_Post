# Thursday decision experiment — prospective execution protocol

The owner requested execution of the September 15 plan on September 16, 2026.
This approves the bounded research implementation described here, superseding
older review-only status for this specific phase. It does not authorize RL,
reserved-confirmation access, an automatic dose extension, or extra machines.
The historical 21 receipts / 7,001 charged seconds remain immutable. A separate
phase ledger will account for new model processes; rental admission additionally
requires current provider price, an explicit finite whole-window ceiling within
the standing CNY3,000 overall ceiling, and an available owner-started A800.

## Estimand and limits

Primary: mean per-problem sampled pass@1 interaction
`(B_paths-B_surface) - (C_paths-C_surface)` on 96 shared discovery instances.
Positive supports the complementarity prediction; negative supports the
substitution prediction; imprecision supports neither. Report four means,
both parent scores and paired changes. This is an intervention-by-recipe effect,
not individual solution value or a proved internal-capability mediator.
One training/preparation seed and one assignment seed are exploratory.

## Finite CPU construction C021

First audit the complete original C008 training-only solution inventory, before
C009 length matching. Rank unequal adjacent child-operator -> parent-operator
interfaces by the number of questions supporting an interface-present and an
interface-absent path with different numeric AC classes AND structure classes.
Tie-break lexicographically. At most the top three are calibration candidates;
candidate choice cannot depend on downstream treatment scores.

Generate a new K=2 pool, rather than expanding the old 66-question subset.
Preallocate distinct four-number multisets from 1..40 to main train (768 candidate
groups), calibration (144), and discovery (288), using data seed20260916.
Disjointness is established before solving/target/path selection. Main target
range remains10..100. Exclude historical arithmetic number groups by ID hashes
where available without opening reserved question contents. Select the first
eligible target by seeded hash, not by model outcome. Select one absent A and
one present B with different AC structure; use minimum pair length difference
only inside a question, without dropping a question for a common-length rule.
Break ties by hash. Preserve every attempted group's eligibility/exclusion.
Primary N=256; uniformly use128 only if the finite pool cannot support256.

Do not iterate candidate pools, targets, dose or learning rate based on final
results. If a construction/runtime assumption fails, retain the failed artifact
and document a separately named implementation repair before any model outcome.
All new instances are development data, not composition-OOD or contamination-free.

## Pretraining intervention and data isolation

Each parent:128 identical atomic exercises +128 distinct two-operation exercises,
two epochs, batch16,32 updates. Opposite operator order defines the control
interface. Arithmetic is verified with Fraction and AST whitelists. Prep and
probe inputs have disjoint complete number multisets; atoms/operators intentionally
overlap. Main/discovery have disjoint four-number multisets. Shared answers alone
are not leakage; prompts must not reveal probe answers or include complete probe
instances. Report prep token/operator/input/length residuals, not merely counts.

C0 is the original pinned Qwen2.5-1.5B Base plus fresh zero-output LoRA.
E018's trained checkpoint is not C0. Parents share adapter initialization and seed.
Children copy the same parent's adapter capacity and reset optimizer/scheduler;
no rank addition, adapter merging or carry-over optimizer state.

## Main treatment and dose

Stratify anchor assignment by target bins, A/B structures and supervision length;
balance A/B globally exactly. Surface supplies two renderings of the assigned
path; Paths supplies A/B with crossed renderings; optional Repeat duplicates the
anchor with renderings balanced across questions. Both parents use identical
files and schedules. Eight macro epochs, batch16:256 updates for N256,128 for N128.
Save0/quarter/half/final; evaluate the fixed midpoint on24 discovery instances and
the predetermined final endpoint. No best-checkpoint selection.

P006 LoRA r16/alpha32/dropout0, q/k/v/o/gate/up/down, frozen FP32 base and trainable FP32 adapters,
BF16 autocast, SDPA, TF32 off; AdamW betas(.9,.999),eps1e-8,weight_decay0,clip1.
Use P006-style6.25% warmup to1e-4, cosine to1e-5, matched within phase.
No packing or target truncation. Divide summed response/EOS loss by the total
supervised token count of each update, including across accumulation microbatches.
Residual<=2%: close token match;2–5%: approximate;>5%: feasibility only.
Never fill responses with meaningless tokens or remove a whole difficult range.

## E018

Run at most once if its release and quality check pass: original253 C017 anchors,
two epochs,64 updates,77,192 supervised tokens,160 free generations; original
fixed P006 LR vector, unchanged observed64 dev questions,32 training decodes.
Require finite training/changed adapter/unchanged base, >=10% pooled reference
NLL decrease, both usability screens and paired retention>=90%, net loss<=4.
No Stage C or reserved GSM8K release. Failure stops scaling and preserves evidence.

## Evaluation and branch decision

Probe C0/C/B on32 atoms +32 target +32 control,4 samples each.
Use original P006 settings only for E018; arithmetic uses temperature.7,top_p.95,
top_k disabled,max_new_tokens512 and the fixed task-boundary/native-EOS stopper.
At most48 calibration problems per candidate, at most3 candidates, within640
total calibration/debug generations. Do not change sampler after outcome ranking.

Freeze manipulation labels before descendants: target-specific improvement must
be visible in paired target probe means and not explained solely by parse/stop
rates or a ceiling/floor. Report raw differences and paired uncertainty; no
p-value is an automatic gate. A conservative operational rule uses >=10 percentage
points B-minus-C target gain, >=5 points above its atom/control mean difference,
no >5-point parse/termination advantage, target parent scores strictly between
.05 and.95. These are pilot decision rules, not scientific significance claims.
Failure selects the prespecified single-C0 Repeat/Surface/Paths fallback and
forbids interpreting a familiarity interaction. Never prolong prep to force a pass.

Core endpoint evaluation: both parents +four children,96 discovery x8 samples
and96 greedy each; midpoint24 greedy per child. Conditional diagnostic: up to32
preselected discovery questions x2 validated prefixes x2 samples x6 endpoints.
Prefix leaves an unfinished target interface, meaningful work and no final
answer; otherwise reduce its actual denominator. Valid unforeseen programs are
accepted; unknown strategy/trace syntax stays unknown. Invalid/capped outputs
remain primary failures. Trace consistency is separate from task correctness.

Core maximum7,360 generations including E018;640 reserve;optional Repeat2,032;
total absolute bound10,032. Optional runs are deferred by default. Sampling is
grouped by question for pass@k and paired question/template bootstrap; interval
uncertainty excludes unreplicated training/prep seeds. No final test is accessed.

## Registration and preservation

IDs checked at parent commit6a7de83: E018 calibration; E019/E020 prep;
E021–E024 four cells; E025/E026 optional repeat; E027–E029 fallback.
C021 is this data/release audit. Preserve hashes, exact commands, revisions,
parent hashes, seeds, token counts, optimizer reset, timing and memory.
Publish source on codex/iclr-2027-sprint before GPU execution. Bound processes and
whole rental separately; export raw tokens, compact records and adapters with
independent checksums, then obtain provider-confirmed shutdown. Preserve E015.
