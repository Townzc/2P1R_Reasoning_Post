# P005: literature-guided next phase with rental-time accounting

2026-09-10 UTC. **Review-only plan; no queued GPU job or request to start a server.**
This supersedes the default priority of D024's 512-update E015 proposal, which
remains unchanged as a historical fallback. The owner requested planning and
broader literature, not an additional runtime allowance or a new scientific grid.

Read [the eleven-paper evidence audit](../../reports/LITERATURE_NEXT_EXPERIMENT_20260910.md),
[C018's completed CPU checks](../../reports/REAL_MATH_C018_SELECTION_AUDIT.md)
and [the rental workflow](../RENTAL_WALL_CLOCK.md).

## Recommended order and alternatives

| Priority / route | Concrete question and comparator | Advance / stop rule |
|---|---|---|
| 1. One optimization calibration | Does reducing the learning rate only at the end of the existing 256-update recipe remove the local fit/termination failures? Compare with immutable E013, same base/data/order/seed/dose/scorer. | Pass the original overfit gate before scientific training. A failed or partial run ends this branch; no automatic LR/seed/step sweep. |
| 2. Minimal allocation study | At a fixed SFT dose, compare Repeat256x1, Solutions256x4 and Breadth1024x1. Keep actual missing-parent counts. Breadth and repetition are necessary prior-work controls. | Only after a usable recipe, a non-floor held-out calibration and a budget for the complete comparison. Do not launch underfunded arms or interpret a common accuracy floor as a null effect. |
| 3. Selection or curriculum | If a multiple-solution effect exists, compare random with surface-diverse selection at the same P/K/dose; then consider student-aware selection or curriculum if evidence motivates it. | Require a change in independently reviewed reasoning features or learning outcomes, not merely the optimized lexical score. Charge scoring passes. Compare curriculum with shuffled order of the same multiset. |
| 4. Model or objective boundary | If calibration fails, review one task-matched small student before more of the same tuning. If ordinary multi-response SFT demonstrably loses useful coverage, review a prefix or consistency objective. | A new model needs a frozen baseline and common recipe within every comparison. No simultaneous architecture/teacher/objective sweep. SSFT/RL replication is outside the minimum plan. |

Routes 2–4 are alternatives or conditional follow-ups, not an automatic queue.
Keep Qwen2.5-1.5B **base** as the incumbent. Qwen2.5-Math-1.5B or an Instruct
variant would be a separately reviewed change, not a silent substitute; no
capability or speed has been measured for them here. OLMo1B remains a later
second-family option. RL and new large teachers remain out of scope.

## The first proposed GPU experiment: terminal LR decay

Identifier reserved for planning: `gsm8k_terminal_decay_e015_r1`; not registered
or launchable. Configuration: [review-only JSON](../../configs/diagnostics/real_math_terminal_decay_proposal.json).

- Fresh original pinned base and fresh optimizer; original 32 E013 references,
  seed 17, update order, full tuning, FP32/BF16/SDPA, batch 4/microbatch 1.
- **256 updates**, 167,232 supervised / 229,056 nonpadding processed tokens,
  32 exposures per reference. No data, prompt, scorer, decoding or batch change.
- The only training factor changed is LR schedule: updates 1–192 use 5e-5;
  updates 193–256 use `5e-5 * (1 + cos(pi * (step-192)/64)) / 2`.
  The final update has zero LR; retain all 256 forward/backward/update records,
  and report 255 nonzero-LR updates and summed LR. Equal token/update counts
  are not equal integrated learning rate; that difference is the intervention.
- Final checkpoint only. Decode the same 32 training prompts at batch 8,
  max_new_tokens 768, context 1024; record all target/EOS top-one margins/NLL.
  No new dev/test decoding or intermediate checkpoint selection in this repair.
- Original gate: at least 31/32 correct and terminated, zero truncations,
  reference NLL < 0.1, complete dose and profile. Training success establishes
  engineering feasibility only, not useful generalization or a data-policy effect.

Rationale is a **testable optimization hypothesis**, not a conclusion of the
papers. E014 demonstrates local argmax misses despite low mean NLL. C018 shows
that failures are not restricted to long references. Related small-student SFT
studies use decaying schedules, but none validates this exact terminal schedule.
Keeping the first 192 updates unchanged localizes the intervention. The older
512-update constant-LR proposal remains possible only after renewed review;
neither proposal runs automatically after the other fails.

Proposed process cap **360 + 15 guard = 375 seconds**, leaving at least 358 of
the existing 733 seconds if reserved at maximum. E013's measured training and
E014's batch8/reference phases suggest feasibility, not a certified upper bound.
A full CPU/Linux release, checkpoint storage/transfer plan and owner review are
still required. The latest observed 6.29 GiB free does not meet the inherited
12 GiB checkpoint-writing gate. No unique data may be deleted to pass it.

## What the scientific minimum would establish

Use the already audited C017 pools; do not acquire a new corpus or teacher now.
Three arms (drop the intermediate Mixed512x2 arm from the minimum) each retain
524,288 supervised tokens and 256 updates. Actual original counts are 253,
996 and 1,013 selected pairs; zero-success parents remain visible. The primary
comparisons are Solutions versus Repeat and Solutions versus Breadth. Report
processed/padded tokens, wall time, failures, training exposures and selection
loss alongside accuracy. Identical integer P×K labels are not identical data.

Before this stage, prepare a separate capability/profile run with a predeclared
nonzero held-out-calibration requirement; the existing 32-example memorization
task cannot meet it. Fix calibration questions, scorer and a floor criterion
before generation; retain all explored recipes in the selection history. Freeze
the eventual scientific evaluation and confidence-interval plan before training.
Use paired seeds and question-level paired uncertainty; 16 development examples
cannot support a strong generalization claim. Never tune on final test.

Existing four-arm training-only projections are 2,096–2,165 seconds. Even an
approximate three-arm equivalent (about 26–27 minutes of training, before
evaluation, setup and backup) exceeds the **733-second process balance**.
The main-study size and extra allowance therefore remain unset. First price the
entire seed-17 comparison and its planned replication, including every startup,
evaluation and transfer; do not use the entire remaining allowance for an
uninterpretable miniature grid. More precise figures require the final recipe.

Cached source creation costs are unobserved. Initially report a conditional
frontier over explicitly labeled problem/solution acquisition-price scenarios,
plus measured local preparation/SFT/rental cost. A true marginal generation-cost
claim needs separate bounded attempt logs and verification timing, including
rejected/duplicate outputs. A different small teacher cannot price this cache.

## Offline completion checklist before requesting startup

The literature review and C018 audit are complete. Next, following review of
the one-factor repair, implement/publish its independent runner and frozen
release, verify LR/update accounting and all reused raw-output checks locally,
prepare a tested Git/input bundle, and establish a safe checkpoint transfer.
Resolve reference-quality flags prospectively for scientific arms; do not
rewrite E013 or drop problematic parents after observing treatment results.

Before requesting startup, present one finite queue, hourly rate, monetary cap,
process cap and a whole power-on window, with shutdown responsibility explicit.
Actual rate and spending limit have been requested and are still unknown.
An illustrative 20-minute repair window costs `hourly_rate / 3` before billing
rounding/storage charges; it is not a quote or an approved expense. It requires
already staged assets and sufficient backup bandwidth. If prerequisites fail,
keep the server off and return to local work.

## Subsequent owner authorization and implementation — 2026-09-10 UTC

The owner supplied CNY8/hour, CNY3000 total ceiling and asked to proceed with the
next plan. The terminal repair is now registered in [E015](E015_terminal_decay.md)
and implemented separately; the proposal JSON and original plan above remain
historical. There is no need for another approval of the same repair. Input
release and local verification precede startup. The measured prior checkpoint
export took16.24minutes, so the conservative whole-rental plan is40minutes target,
45minutes planned ceiling (~CNY5.33/~CNY6), superseding the20-minute illustration.
The existing process ledger is preserved for E015; future finite scientific
phases can be budgeted within the money ceiling after their scientific gates,
without treating733 historical process seconds as the new monetary allowance.
No scientific grid, automatic fallback or model substitution is authorized here.
