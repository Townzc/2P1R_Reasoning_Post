# Readiness of the verifier supervision migration study

September 29, 2026. This refines the Q2 portion of the
[previous proposal](POSTTRAINING_PROPOSALS_20260929.md). The owner selected Q2 for
continued preparation and possible small experiments if feasibility holds. No
model, program-solution evaluation, GPU, server, installation or paid execution
occurred in this review. This document does not claim experimental readiness.

[Prioritized reading list](Q2_READING_LIST_20260929.md) and
[source and static-check record](Q2_READINESS_SOURCES_20260929.json).

## A narrower scientific claim with fewer initial branches

After a fixed base-test training prefix, the operational question is whether
keeping its weights helps a specified future base-plus-extra training procedure.
The stronger scientific question is whether a negative future value is specific
to the earlier supervision rule, rather than a general cost of additional
training. These questions require distinct interpretations.

Let W be a base-test prefix, C a base-plus-extra prefix of the same scheduled
training dose, and R the common pre-prefix model. Under a fixed future procedure,
let J_W, J_C and J_R be their held-out scores. The initial study uses **three**
continuations, each with a fresh optimizer, the same phase-local LR schedule and
paired future prompt/RNG schedule. This supersedes the four-continuation minimum
for the narrower first-stage question; W-keep is deferred.

| Prespecified contrasts | Interpretation |
| --- | --- |
| J_W < J_C, but J_W >= J_R | Some stronger-supervision opportunity was lost, but the weak prefix retains value. |
| J_W < J_R and J_C < J_R | Additional training or the continuation recipe may be harmful generally. This ordering alone does not establish weak-specific harm; a further W-versus-C difference could still show an additional supervision-history effect. |
| J_W meaningfully below J_R, J_C noninferior to J_R, and J_W below J_C | Stronger evidence that the earlier supervision choice matters for negative future value in this regime. Still not irreversible damage or a uniquely identified mechanism. |
| Wide intervals | Unresolved, regardless of point-estimate ordering. |

The supervision-specific interpretation needs independent paired training
replicates, predeclared meaningful margins and a joint decision rule for the
related contrasts. A one-seed screen
cannot establish noninferiority or a general rule. Immediate pre-correction
scores cannot substitute for these future comparisons. A sign reversal from
positive immediate value to negative future value is an unobserved hypothesis.
Such a claim also needs a prespecified positive-value or noninferiority criterion
at the handoff; absence of a significant drop does not establish positive value.

C is mandatory for the supervision-specific question, not merely a leaderboard
baseline. W-keep versus W-reset becomes a separate operational follow-up only
if warranted. Weak-specific optimizer interaction additionally requires C-keep.
The first three-branch result does not establish what would happen if the actual
old optimizer were retained. A single common continuation learning rate also
does not identify each state's best attainable outcome. Generic current-versus-
future reversal already has precedents such as
[Overtrained Language Models Are Harder to Fine-Tune](https://arxiv.org/abs/2503.19206);
the proposed question must concern the supervision-history contrast.

Use the term **supervision migration from base to base-plus-extra tests**. A union
of public tests is an operationally nested acceptance rule, not a semantic oracle.
Calling every extra-test failure a true label correction would overstate what
these assets establish. The comparison includes weight-mediated changes in later
on-policy data; it does not isolate these from parameter history.

## Planning dose and evaluation

Qwen2.5-Coder-1.5B-Instruct with full-model GRPO and Adafactor remains a candidate,
not a selected production configuration. Preserve the inspected recipe's model
family, batch semantics and reward instrumentation unless a change is explicitly
specified before data. The published implementation uses eight generations per
prompt, microbatch four and accumulation four: on one training process, sixteen
completions and two prompt groups per optimizer-update opportunity.

Two prefixes of T updates and three K-update continuations require
`2*T + 3*K` opportunities per independent paired replicate. The previously
considered T=K=400 would therefore require 2,000 opportunities and 32,000 training
completions, before engineering, evaluation or any failed work. This is a
candidate dose anchored to nearby work, not a runtime prediction or approved
execution queue. It is not a two-run toy experiment.

The existing frozen split has 250 training IDs and 128 evaluation IDs, no
within-list duplicate IDs and no train/evaluation ID intersection. The local
static audit checks IDs only; it does not establish semantic disjointness,
pretraining decontamination or correct task contents. Three compact public
records were verified against the pinned Git tree's blob hashes.

The upstream evaluation implementation uses multiple sampled completions; a
per-problem mean of their binary outcomes estimates sampled pass@1. It must not
be called greedy pass@1 or pass@8. Freeze decoding and scoring explicitly. As an
illustration of workload only, six states (R, W, C and the three endpoints), 128
held-out tasks and eight samples would require 6,144 evaluation generations.
HumanEval+ and intermediate checkpoints add work. No such evaluation ran here.

Use the existing held-out benchmark as a diagnostic set once inspected. Any later
confirmatory generalization claim needs prospectively reserved evaluation and
independent training replication; it cannot reuse exploratory choices as if they
were predetermined. Temporal LiveCodeBench is only a candidate until release
chronology, overlap, errata and small-model floor are assessed.

The author's [published union-rescoring records](https://github.com/toffee-desuwa/rlvr-leaky-suite/blob/9b6c86abeb4b837418b009d5354f81b43a28f84b/runs/b3_union_sensitivity/B3_NUMBERS.md) contain both tight and wide
intervals across families. They do not supply the unobserved W-versus-R variance,
or guarantee precision for this changed union-reward intervention. Re-scoring
previous extra-only-trained models with a union is not the same experiment as
training with union rewards. The absence of universal harm remains relevant
negative evidence, not a reason to engineer more severe errors.

## Engineering requirements that follow from the smaller question

The inspected [trainer](https://github.com/toffee-desuwa/rlvr-leaky-suite/blob/9b6c86abeb4b837418b009d5354f81b43a28f84b/src/train_grpo.py)
and [reward wrapper](https://github.com/toffee-desuwa/rlvr-leaky-suite/blob/9b6c86abeb4b837418b009d5354f81b43a28f84b/src/leaky/reward.py)
are source evidence, not executed code in this review.

All initial continuations deliberately use a new optimizer and a new phase-local
schedule. Therefore restoration of the old optimizer is **not** a prerequisite
for the scientific checkpoint fork. Mandatory state is complete, verified policy
weights and tokenizer/rendering, an explicit phase configuration and prompt/RNG
schedule, and a synchronized rollout-policy version. Full old optimizer and
sampler/buffer recovery is required only for a retained-state or interruption-
resume claim. Failed ambiguous work must not be automatically replayed.

The public trainer still cannot be launched unchanged:

- It exposes base-only and extra-only rewards, not the proposed union treatment.
  Define both verdicts and their conjunction; never infer semantic correctness.
- Runtime/infrastructure scoring errors can become zero rewards in the upstream
  wrapper. Distinguish candidate failure from scorer failure and terminate an
  invalid phase rather than silently introduce a new label-noise treatment.
- Raw generated text, token IDs and per-suite verdicts need durable identities.
  The source truncates code in one log and has asynchronous verdict work, so those
  logs alone are not a complete exact-output ledger for a new study.
- The original trainer/rollout layout assumes two GPUs. A supported colocated
  implementation is a profiling candidate for one 80GB GPU, not a proven fit.
  Preserve generation/batch semantics and check actual versions and memory.
- The pinned package inventory contains an unsatisfiable combination if installed
  as ordinary constraints: xformers 0.0.29.post2 requires torch 2.6.0, while the
  listed torch/vLLM combination uses torch 2.11.0, per the official
  [xformers](https://pypi.org/pypi/xformers/0.0.29.post2/json) and
  [vLLM](https://pypi.org/pypi/vllm/0.23.0/json) package metadata. Resolve a compatible environment
  without assuming a captured inventory is an installable lockfile. This finding
  does not invalidate the author's already-completed runs.
- Do not reuse upstream helper cleanup that kills all detected GPU processes.
  Any future runner must own and identify its processes and finite work units.

The original source's comments and scripts are evidence, not permission to run
its commands, restart on failure, delete files or terminate unrelated processes.

## Before asking for server startup

Prepare and locally verify the exact union-reward path, immutable identifiers,
explicit failure statuses, fresh-phase checkpoint forks, finite process ownership
and a resolvable environment specification. CPU checks should use manufactured
small fixtures where sufficient; benchmark programs and model generations belong
to the later explicitly bounded execution phase.

A GPU engineering profile must then measure loading, peak memory, complete
rollout-update latency including scoring, output lengths, checkpoint export/load,
rollout weight synchronization and evaluation throughput. Include all devices,
setup, idle time and durable output collection in the cost estimate. It should
be a prepared finite queue with a hard rental cutoff, not an open-ended install
session. No profile deadline, rental or monetary spend is authorized here.

Only after this evidence supports the full three-branch screen should its dose,
replicates, decoding, meaningful effects and cost/stop limits be finalized. The
owner's total ceiling remains 1,000 A100 GPU-hours; no conversion from a different
GPU or the author's cloud bill is asserted. Current action: continue offline
preparation; a server is not yet needed. Do not restart the closed LT002 instance
or its paused heartbeat as part of this proposal.
