# Matching selection, completed CPU diagnostics and next training design

This round responds to the owner's request to resolve avoidable matching
selection, complete CPU searches and prepare tomorrow's training. It adds no
GPU seconds, server connection, rental, model inference or holdout evaluation.
The A800 remains in its previously verified stopped state. The original budget
remains4716/7200 charged,2484 seconds available.

## Why the previous design was inadequate

C008 exhausted the ordered grammar on the original256 fixed training questions:
25,846 legal solutions. C009 found131 questions with disjoint four-plus-four
numerical AC classes,67 with common EOS-inclusive response length, and66 with
four operator structures per family. All large targets (at least41) disappeared
at common-length matching. Its capped discovery was not a capacity estimate.

The candidate must not be built from the seven questions seen early in a search
or from whichever family has favorable later model results. Three CPU protocols
were published at `21090e3511243d45b4ad605e924c730ff4b480eb` before execution:
C010 finishes the old finite join; C011 separates length/structure restrictions;
C012 selects an absence-only allocation contrast with predetermined scale tiers.
Inputs, targets, grammar, labels, rendering, tokenizer and evaluation sets remain
fixed. C012's family and seed31 were chosen before its support counts.

## C010: retain the computational failure, do not call it complete

The600-second support-mask join represented47,757,976 of48,429,084 candidate
pairs:37,104,680 safely pruned and10,653,296 exactly decided.671,108 remained.
It found528,669 valid keys over53 questions and a12-block packing optimal only
over discovered groups. It wrote a7,697,969,832-byte repetitive witness stream
(614,821,423 bytes gzip). The search is incomplete; its12-block bound is not a
global bound. The stop cursor, counters, source hashes, partial stream hashes
and packing are retained in [its receipt](complete_join_20260909_r1/summary.json).

This failure motivates C013's exact compressed representation: first verify
that each numerical AC class maps to one operator structure, then solve the
one/two-slot Hall components with occurrence bitsets. Store tuple and length
signature indices once, and full witnesses only for representative support
groups. This changes computation and storage, not eligibility or training
selection. The original600-second ceiling stays unchanged.

## C013: the original finite search is now complete

From prepublished source `f2d7fea9c4c619bb90669fd9db5ee30a76f35e02`, C013
completed the entire pipeline in4.833 seconds. It represented all48,429,084
pairs:37,104,680 pruned plus11,324,404 exact decisions, with zero unrepresented.
There are1,019,005 valid keys,202 exact-support sets and63 supported questions.
The maximum packing is15 blocks/60 questions. Its explicit packing attains
the simple independent upper bound floor(63/4)=15.

The full compact stream is15,960,826 bytes (2,571,804 bytes gzip). Public
catalogs, all keys and representative witnesses are losslessly archived with
SHA-256 verification; see [receipt](compact_join_20260909_r1/summary.json) and
[storage/reconstruction](compact_join_20260909_r1/storage.json). Safe pruning
and exact occurrence compatibility produce a finite answer rather than a
larger incomplete prefix. C010's unsuccessful outputs remain immutable.

The [independent full-grid audit](compact_join_20260909_r1/independent_verification.json)
passed in15.34 seconds using the public archives alone. It independently
enumerates all positive and negative pairs using per-occurrence AC sets,
checks1,019,005 keys and3,698 representative witnesses/29,584 slots, and verifies
lowest lengths, counts, unique references and lexicographic representatives.
Support components of56 and7 questions give the tighter explicit certificate
floor(56/4)+floor(7/4)=15, attained by the validated integer packing. No private
key gzip or uncompressed catalog/support JSON was needed for this audit.

Completeness strengthens the selection concern:56/63 supported questions have
a target equal to an input, no target exceeds40, and12/63 contain input1.
The packed60 retain all56 target-equals-input questions. It is inaccurate to
generalize C009's first seven discoveries to all feasible questions. The old
double-family construction cannot even reach the64-question operational
minimum of the new plan. C012 remains the independently preselected alternative;
its family, seed and scale rule were not selected from C013's new result.

## C011: length and structure both select the population

All four cells were evaluated independently on every original question using
the same tokenized inventory and disjoint eight-class assignment. These are
CPU constraint diagnostics, not four model conditions.

| Per-question constraint | Feasible questions | Target at least41 |
|---|---:|---:|
| Common length, four classes per family | 67 | 0 |
| Common length, also four structures per family | 66 | 0 |
| Separate family lengths, four classes per family | 129 | 41 |
| Separate family lengths, also four structures per family | 84 | 0 |

Relaxing cross-family length alone restores many questions, but distinct
structures in both families again exclude all large targets. It is therefore
incorrect to attribute all loss to token matching. A per-family-length global
join was not run or silently substituted into the next training design.
Independent NetworkX checks reproduced all cells; original JSON can be restored
byte-for-byte from the [public compressed archive](family_lengths_20260909_r1/length_diagnostic_storage.json).

## C012: remove restrictions irrelevant to the selected pair

Both next models train only on identity-absent trajectories. Requiring a question
also to have four present trajectories, eight cross-family classes or equal
length across families contributes no control to this pair. Those conditions
were explicitly removed before C012 outcomes. Within-question length, four
distinct classes/structures and exact shared structure matching remain.

The single-family search completed all74,764 local structure combinations and
8,774 local keys, finding4,182 shared keys. There are139 individually feasible
questions,138 with shared support, and33 disjoint four-question blocks. The
integer solver's optimum is independently certified: the full support graph
has components of19 and119 questions, so at most floor(19/4)+floor(119/4)=33
blocks exist. The returned packing attains33. All62,865 key/question witnesses
were independently checked, including omitted/added supports and lowest lengths.
See [receipt](absent_support_20260909_r1/summary.json) and
[independent audit](absent_support_20260909_r1/independent_verification.json).

The declared selection rule sorts that packing, shuffles with a separate
Random(31), and takes32 blocks. No model or development prediction determines
this choice. It samples from one feasible packing, not uniformly from all
possible feasible populations. No data, targets or omitted strata are repaired
by inventing new examples or extrapolating weights.

| Fixed population/stage | Questions | Target≥41 | Input1 | Target is an input | Strict preview template |
|---|---:|---:|---:|---:|---:|
| Original training pool | 256 | 105 | 96 | 59 | 7 |
| Individually feasible absent family | 139 | 36 | 23 | 59 | 7 |
| Shared absent support | 138 | 36 | 22 | 59 | 7 |
| Optimal packing | 132 | 33 | 18 | 59 | 7 |
| Frozen training selection | 128 | 33 | 18 | 55 | 7 |

The new selection restores large-target coverage relative to the old common-L
design (33/128 rather than0), while it still underrepresents those targets
relative to105/256. Input1 is also underrepresented, and target-equals-input
is overrepresented (55/128 versus59/256). All seven strict preview-template
questions remain. The avoidable cross-family screening is removed; selection
bias is not fully eliminated. All original, selected and excluded IDs and
stage-specific retention denominators are saved, including negative strata.

## Materialized training and provenance

Data were generated after preparation-code publication at
`d537c31cf6c5498e6ca7d8e8045b976b0fadb1f9` into the immutable directory
`runs/absent_boundary_seed31_20260909_r1`. Its manifest SHA-256 is
`cd9a72d187dbb18f2b75b743ccc0cf85c94951ee574c07e55ed8ddf1f4a1ab97`.
Each arm uses128 questions,1024 updates and4096 presentations. Each question
appears32 times; Paths visits each of four paths eight times, GCM repeats one
assigned path32 times. Training/assignment/order seed31, evaluation seed17.

| Accounting, per planned arm | Paths | GCM |
|---|---:|---:|
| EOS-inclusive supervised tokens | 277760 | 277760 |
| Processed nonpadding tokens | 482848 | 482848 |
| Padding tokens | 3734 | 3734 |
| Optimizer updates | 1024 | 1024 |
| Presentations | 4096 | 4096 |

Maximum sequence length is126 within the frozen384 limit. Ordered questions,
per-example lengths and per-update operator structures agree across arms.
The original64 matched and64 broader development files and split allocation
are byte-identical; reserved groups are used only for disjointness checks.
Repeat/Surface compatibility files are audited but their models are not queued.
The [independent CPU audit](absent_boundary_cpu_verification_20260909.json)
passed in2.475 seconds, checking all512 references with independent AST/Fraction
arithmetic, the pinned tokenizer, source selection, RNG/schedule reconstruction,
exposure counts and every update's token/padding/structure/operator histograms.
Its receipt SHA-256 is
`30cf7b1b096a7b9f4229350263d2ae39e375bcc131521dea9ee75e0f0df95af1`.

Six numerical-feature totals (identity, zero, one, fractional and negative
intermediates, and depth) agree globally and on every update. This does not mean
per-question exposure equality: mean depth differs on120/128 questions and
negative-node count on52/128, with batch-level cancellation. The maximum
absolute nonroot intermediate averages36.488542 for Paths and35.927083 for GCM
(GCM−Paths=−539/960). It differs on90/128 questions and600/1024 updates.
These numerical residuals can be components of the allocation intervention;
they are neither automatically an external confound nor proof of a learning
mechanism. Do not claim equal numerical difficulty or semantic exposure.

The queue is `configs/absent_boundary_seed31/queue.json`, containing only
`absent_boundary_paths_seed31_r1` and `absent_boundary_gcm_seed31_r1`.
Inspection validates the original ledger and the unchanged historical
calibration:2130 seconds reserved for the whole pair,2484 available. These are
ceilings, not actual new charges. Both new runs are still not_run.

## Scientific scope and morning handoff

This pair asks whether within-question structural allocation helps in this
selected absence-family population. Identity absence still permits cancellation
and computed constants. It does not isolate semantic strategies or causally
identify the effect of removing identity operations. Old models were trained
on a different population/dose distribution and cannot serve as that control.

Report the signed greedy contrast, all paired cells, both development sets,
complete-trace results and sampled pass@1/2/4 separately. A favorable single
pair is exploratory boundary evidence; an unfavorable pair must be retained.
Neither outcome establishes general arithmetic gains, training-seed certainty
or ICLR readiness. The holdout remains unevaluated. The full frozen
[training plan](../docs/ABSENT_BOUNDARY_TRAINING.md) gives the interpretation
and stop rules; the [next-session handoff](../docs/NEXT_SESSION.md) gives exact
launch commands, migration prerequisites and output-audit paths.

Only start training after the owner supplies/starts an A800 and its fetched
commit, base model, environment, ledger and disk gates pass. Require18GiB free
after setup; restore neither historical checkpoints nor CPU witness streams to
the50GB training disk. No expansion is needed for today's local CPU work.


## Legacy provenance regression repair

The final full suite enabled the real pinned-tokenizer regression and exposed
an old verifier that compared preparation hashes with today's source files.
Adding the new dataset dispatch legitimately changes pilot_runtime.py, so that
comparison incorrectly invalidated historical artifacts. The two historical
data manifests also explicitly record dirty preparation worktrees; their
recorded commits cannot retroactively be called complete source snapshots.

The repair binds only the two exact historical manifest hashes to the verified
later published GPU snapshot6128e4266d62f14f063585d4c8e94dbe3ad8c711, checks the
manifest bytes in that snapshot and every recorded source SHA, and reports
later_publication=true/prepublication_claimed=false. Unknown dirty provenance,
missing commits, altered hashes and invalid paths are rejected. Current data,
token, split and seeded reconstruction checks are unchanged. The new C012
preparation did use prepublished clean source; these historical exceptions do
not change its source record or frozen data.

Final verification:294 tests ran with the real pinned-tokenizer regression
enabled;292 passed and two GNU-timeout integration checks must run on Linux.
From a clean Git checkout of `0a57fb1d1af22fc9569799e1e3c12779616cbf88`, both
new arms passed independent data/token checks, queue/config gates, calibration
inspection and the unchanged ledger check. No private matching inventory or
expanded search JSON was required. See the
[release receipt](matching_completion_release_verification_20260909.json).
