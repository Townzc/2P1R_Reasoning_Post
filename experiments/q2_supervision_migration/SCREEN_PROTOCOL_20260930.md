# One exploratory supervision-history screen

September 30 UTC, before any new model work. The owner requested continuation,
rapid feasibility evidence and a concrete direction before Thursday's Office Hour.
The completed two-update engineering profile established execution on one A800;
it did not test supervision-history effects. This finite screen starts from the
original pinned model, **not** the engineering profile's trained weights.

## Question and course relevance

After upgrading the data used to verify code-RL outputs, is keeping the previously
trained policy more useful than returning to its earlier weights, under the same
future training procedure? Is any negative future value specific to the earlier
supervision rule, beyond the general effect of additional training?

The intervention is the supervision data: original MBPP tests versus the union of
original and existing MBPP+ extra tests. It connects to the course's critique of
RLVR training signals and to an industrial checkpoint-retention decision when
acceptance tests change. The union is a stricter public acceptance rule, not a
semantic oracle. No benchmark, tests, annotations or synthetic errors are invented.

The [closest natural-test study](https://arxiv.org/abs/2607.11022v1) already contrasts
base and extra-test training and reports bounded average effects. Its baseline
contrast is not our contribution. [PRIME](https://arxiv.org/abs/2606.09711v1) already
studies residual proxy-related behavior after reward changes. Our proposed
contribution would have to concern the **future value of retaining earlier weights
with a matched stronger-supervision history control**. This is a hypothesis worth
screening, not an established effect or a guarantee of novelty. See the existing
[reading audit](../../docs/tracks/icml_acl_2027/Q2_READING_LIST_20260929.md).

## Frozen comparisons and dose

Use Qwen2.5-Coder-1.5B-Instruct at the already hashed revision, official MBPP+
v0.2.0 and the nearest study's existing 250 TRAIN / 128 evaluation split. This
is an established benchmark with a published study split, not a new official
full-benchmark score or evidence of pretraining decontamination. All inspected
evaluation results become exploratory development evidence.

| Phase | Starting weights | Training reward | Updates |
| --- | --- | --- | ---: |
| W_prefix | Original R | Base tests | 128 |
| C_prefix | Original R | Base AND extra tests | 128 |
| W_future | W_prefix | Base AND extra tests | 128 |
| C_future | C_prefix | Base AND extra tests | 128 |
| R_future | Original R | Base AND extra tests | 128 |

Every phase uses a fresh empty Adafactor and a fresh phase-local constant learning
rate of 1e-6. Other training settings retain the working profile: full-model bf16,
GRPO/DAPO implementation, beta=0, microbatch4, accumulation4, eight completions per
prompt, temperature1 and a640-token output limit. Sixteen completions correspond
to two prompt groups per update. Exact settings and schedules are in
[the frozen machine-readable plan](assets/screen_t128_k128.json).

An outcome-independent hash permutation fixes prompt order. Each128-step phase
covers all250 TRAIN tasks once and repeats six at the next permutation's start.
W/C share their prefix schedule and trainer seed0; all three future phases share
the future schedule and trainer seed1. This is one paired training replicate,
not five independent seeds. The pinned TRL colocated vLLM engine uses seed0 for
all phases; paired schedules do not guarantee identical random trajectories
once policies and output lengths differ. This explicit sampler replaces the
profile's eight-task random sampler without changing batch/reward semantics.

Total: **640 update opportunities, 10,240 training completions, five final weight
exports**. Actual token counts, zero-signal groups and runtimes are reported;
equal scheduled updates do not imply equal FLOPs or generated tokens. A fresh
weight/tokenizer probe must pass before each W/C continuation; optimizer/RNG
resume is not attempted.

All six states R, W_prefix, C_prefix, W_future, C_future and R_future are evaluated
once on every128 evaluation task with eight samples: **6,144 evaluation completions**.
Use fixed task-specific sampling seeds shared across states, temperature1, top-p1,
no top-k filtering, max640 tokens, batch four tasks × eight samples. All generated
text, token IDs, finish reasons when exposed, extracted code and both verdicts
are retained. The primary score is task-macro sampled pass@1 under the union;
observed pass@8 and base/extra scores are secondary. This is not greedy accuracy.

The queue is exactly **16,384 new completions**. There are no intermediate model
evaluations, extra seed, hyperparameter sweep, alternate model or optional arm.
No result-based early stopping selects the best checkpoint. One canonical
reference cache covers378 tasks and is reused with a hash check. The official
empty extra suite for TRAIN task Mbpp/793 passes vacuously, so its union equals
base; the task is neither removed nor silently assigned zero.

## Interpretation and stopping the project

Report W_future−R_future, W_future−C_future and C_future−R_future together. Also
report the two immediate prefix-minus-R contrasts; these cannot replace future
comparisons. Question-bootstrap intervals are descriptive and conditional on
these specific trained policies; they do not quantify training-seed uncertainty.

A predeclared **pilot priority pattern** is W_future at least3 percentage points
below both R_future and C_future, with C_future no more than1 point below R_future.
These are practical screening thresholds, not a power calculation, confirmed
noninferiority or a joint significance test. Such a pattern warrants discussion
and independently trained replication; it does not establish irreversible harm
or a unique mechanism. W<C while W>=R means weak history still retains value.
If W and C both trail R, the general additional-training explanation remains;
a further W−C gap may still matter. Other patterns remain in the result table.

A weak or imprecise signal is **unresolved**. Because Thursday is close, it can
justify deprioritizing the project without declaring the hypothesis false. Do
not extend dose, hunt seeds or manufacture stronger errors until a result appears.
A deployment/scoring failure is an engineering failure, not a scientific null.
A genuine replacement must pass a separate closest-work, asset and budget audit;
current backup review has not admitted one. Negative evidence remains a legitimate
basis for a concrete Office Hour discussion.

## Time, spend and shutdown

One owner-started A80080GB; no new rental, GPU configuration change or installation.
Reuse the resident inputs and locked runtime. The two-step profile's second step
took8.80s and its batch generation/scoring intervals were7.88–10.38s. Extrapolating
640 updates plus384 training-sized evaluation batches and process/export overhead
suggests roughly **2–3 powered hours**. This is a rough planning estimate: four
profile tasks do not establish throughput for the full task distribution, and
standalone evaluation throughput has not been measured.

**Hard whole-powered cap: four hours**, including staging, idle time, collection
and shutdown. At the last verified7.98 CNY/hour, the cap is **31.92 CNY compute**,
excluding storage and not a quote or invoice. Verify the live price before work;
if above that rate, do not silently enlarge the spend cap. A800 hours are not
asserted to be A100 equivalents; all failed and successful work remains within
the shared project accounting and<=1,000 A100-hour overall ceiling.

Set and visibly verify the provider's normal shutdown timer at or before
conservative power-on+4h. The parent shares **13,200 seconds** across all phases;
admit it only with that allowance plus at least600 seconds left before provider
shutdown. Reference preparation additionally has600s, each training phase2700s,
and each evaluation phase1800s; the earlier shared deadline always wins. Each
worker has a recorded owned process group. No restart or replay after failure,
missing receipt or ambiguous generation is automatic.

Require>=40GiB free data disk at admission, and retain>=10GiB data /3GiB system
before every generation and update. The last stopped host had about89GiB free;
the five new weight exports need about15.4GB plus records/caches. Those are
planning quantities, not measured peak requirements. No old model, result or
failed record is deleted to make this screen fit.

On completion or failure: inspect real GPU/CPU workers, reconcile updates and
reserved/returned/scored completions, independently rehash final checkpoint
manifests, collect and verify compact outputs, then promptly perform normal
provider shutdown and verify OFF. Never use the Trash-clearing helper or wait
for the timer after finishing early. Analyze locally after shutdown. The old
LT002 experiment and heartbeat remain closed.

## Readiness and limits

The new plan/runtime/scoring/analysis are CPU-tested with authored fixtures;
the source must be published and verified before any server execution. Tests
cover fixed paired dose, leakage rejection, empty extra suites, unresolved score
handling, corruption, incomplete output, owned process limits and no automatic
replay. These tests do not qualify the full128-step GPU run or new standalone
evaluation path. The latter receives no unbounded repair allowance.

The EvalPlus0.3.1 inner FAIL category can conflate candidate exceptions with some
inner subprocess failures. This limitation is retained; outer errors/timeouts
abort rather than become zero rewards. This screen uses the same frozen public
evaluator across arms, but must not claim perfectly attributed semantic errors.
Scorer isolation is not an adversarial-code security sandbox; execute only on the
isolated research instance. No external correspondence is sent by the agent.
