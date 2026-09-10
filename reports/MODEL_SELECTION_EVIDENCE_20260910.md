# Model-selection rationale grounded in completed work

2026-09-10 UTC. This is an evidence clarification for P004, not a new
experimental protocol or model-selection result. E012 remains paused.

The first concise P004 reply drew on the existing engineering infrastructure,
but did not sufficiently distinguish completed results from new candidates.
In particular, the teacher and second student have not been tested, and the
nine-cell GSM8K grid has not been profiled. A revised privately retained
bilingual reply makes those distinctions explicit. No correspondence was sent.

## What has actually run

| Work | Observed evidence | What it does not establish |
| --- | --- | --- |
| [0.5B debugging](../docs/experiments/E003_debug_lower_lr.md) | Existing debugging runs; lower-LR gate passed at 31/32 train | A validated main model for the proposed acquisition study |
| [1.5B arithmetic overfit](../docs/experiments/E006_main_a800_overfit.md) | A800 full-parameter recipe reached 32/32 train at 500 updates; dev 0/16 greedy | Broad generalization or GSM8K readiness |
| [Arithmetic allocation replication](PILOT_REPLICATION_SEED23_RESULTS.md) | Seed17/23 matched greedy Paths/GCM: 23/64 vs 18/64 and 22/64 vs 17/64; seed23 broader 1/64 each | An established general allocation law, significant effect, or benefit from more unique problems |
| [Changed-population boundary pair](ABSENT_BOUNDARY_SEED31_RESULTS.md) | Matched greedy 7/64 vs 5/64; complete traces 4/64 each; broader 0/64 vs 2/64 | A causal identity-removal effect or robust broad transfer |
| [Relation engineering E011](RELATION_E011_RESULTS.md) | Completed 256 updates, complete train proofs 0/32 despite NLL .11939 | Learned relation computation or evidence that a larger model is necessarily the fix |
| [C016/E012 preparation](RELATION_E012_READY.md) | Frozen CPU diagnostic inputs and verified execution release | An executed E012 model experiment |

The main model failed on 4090 at optimizer-state allocation under the particular
full-FP32 recipe, then ran on A800. This is a measured hardware/recipe fit
result, not a universal statement about 4090 training or model capacity.

No project run has yet generated a GSM8K solution pool with Math-7B, trained
the new GSM8K acquisition comparisons, evaluated OLMo2-1B, or measured the
relative price of acquiring a new problem and an additional usable solution.

## Why these assets are candidates

### Qwen/Qwen2.5-1.5B base — first student to calibrate

The current pinned revision, exact loss/token audits, full-parameter training,
raw-output evaluation and resource accounting are already built and tested
around this model. It has measured A800 feasibility on earlier tasks, reducing
implementation changes and supplying a useful continuity baseline. The
[maintainer card](https://huggingface.co/Qwen/Qwen2.5-1.5B) identifies it as a
pretrained base, suitable for studying the project's additional SFT stage.

This supports retaining it as the **first feasibility candidate**, not declaring
it the best or already validated student for GSM8K. Recheck capability, loss,
free generation, length and throughput on the new task before freezing the
allocation comparison. Base status does not establish absence of mathematical
training data or benchmark contamination. Do not switch to Instruct merely to
obtain better starting numbers inside a comparison.

### Qwen/Qwen2.5-Math-7B-Instruct — proposed solution teacher

The [maintainer card](https://huggingface.co/Qwen/Qwen2.5-Math-7B-Instruct)
explicitly targets mathematical CoT and tool-integrated reasoning. Its proposed
role is generating candidate mathematical explanations. An instruction-tuned
teacher and a base student have different roles; this does not mean using the
teacher as another student condition. Open weights and a moderate candidate
size would allow controlled local version/sampling and cost measurement.

This teacher was newly proposed in P004. It has not been downloaded, run or
profiled by this project. Larger size and math specialization do not prove
better valid-solution yield, semantic diversity, lower cost or superiority to
an R1-based teacher. Published tool-assisted scores cannot be borrowed as this
project's tool-free CoT quality. A fixed CoT/tool policy, limited acquisition
pilot and proof/answer audit must precede selection.

Measure valid nonduplicate solutions per attempted token, per wall-clock cost
and per verification cost, together with reasoning quality and trace length.
Count failures and duplicate outputs. Confirm actual A800 memory and 50GB-disk
fit before any download or large cache accumulation. Keep the teacher fixed
within an allocation comparison. Sharing the Qwen family with the student may
introduce a style/compatibility preference; it is a limitation to investigate,
not evidence of teacher superiority.

### allenai/OLMo-2-0425-1B base — conditional second-family replication

This asset was already specified in the project's earlier protocol; it was not
introduced for the first time in P004. The
[maintainer card](https://huggingface.co/allenai/OLMo-2-0425-1B) provides an
explicit base checkpoint and training-data/code/checkpoint documentation.
It offers a prospective second-family check at a small model scale.

It has not been run. Perform capability and environment checks before committing
to key-comparison replication. Qwen1.5B and OLMo1B differ in size, tokenizer,
pretraining and architecture; any difference is a cross-configuration result,
not an isolated architecture effect. The official card's post-trained/Instruct
benchmark numbers must not be attributed to the planned base checkpoint.
Second-family replication can challenge a Qwen-specific result, but does not
by itself eliminate all teacher or dataset biases.

## Concrete corrections to the proposed reply and deliverables

- State the actual synthetic pilots and unfavorable generalization/learning
  results before describing prospective real-data work.
- Retain Qwen1.5B as the first student to calibrate; mark Math-7B as a proposed
  teacher and OLMo1B as a conditional replication asset.
- The P in {256,512,1024}, target K in {1,2,4} grid is a tentative scope,
  not a profiled or funded commitment. Start with one student/teacher feasibility
  pilot, then freeze a useful bounded subset before a larger grid.
- Keep P for acquired distinct problems and K_i for retained solutions for
  problem i. Record per-trajectory exposure counts separately; do not assume
  all trajectories receive one common E on variable-length data. Sum K_i, not
  P K, is the actual pair count when targets are not all reached.
- Cost scenarios and measured generation/verification expenditure remain
  separate; no model-selection rationale supplies missing acquisition evidence.

The original remaining 1229 process seconds are not evidence that the proposed
teacher generation, GSM8K grid, multiple seeds and second family all fit.
There was no new spending or ledger change in this review. Historical sources,
data, failed outcomes and the immutable E012 release remain unchanged.

The root agent reconciled the saved experiments while an independent read-only
agent checked model-choice rationale and maintainer cards. Their conclusions
agree on the candidate/validated distinction and the need to avoid borrowing
Instruct or tool-assisted scores for untested configurations. This review is
not an additional experiment or independent model replication.
