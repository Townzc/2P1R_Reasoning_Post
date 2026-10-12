# Problems, Paths, or Repeats?

**Current research:** allocating data-acquisition budgets for reasoning SFT.
**Working branch:** [`codex/icml-acl-2027`](https://github.com/Townzc/2P1R_Reasoning_Post/tree/codex/icml-acl-2027). The repository default `main` is historical.
This is a living research record, not presentation or assignment prose.

## Start here

- [Current execution and audit handoff](docs/COLLABORATION.md)
- [Recomputable main audit packet](reports/p007_audit/main_v1/REVIEW_REQUEST.md)
- [Verified results and closeout](reports/sft_allocation_midpoint_20261011/MAIN_CLOSEOUT_20261012.json)
- [Scientific plan](docs/experiments/P007_midpoint_allocation_plan.md), [teacher cost pilot](docs/experiments/P007A_teacher_cost_pilot.md), [cost-matched comparison design](docs/experiments/P007B_cost_matched_policy_design.md)
- [Execution log](reports/sft_allocation_midpoint_20261011/RUN_LOG.md), [AI assistance log](AI_USE_LOG.md), [historical status archive](docs/LOG.md)

## Question

With a fixed data-acquisition budget, when should we acquire another problem
rather than another usable solution to an existing problem? Student training
resources are a separate constraint. Failed and duplicate acquisition attempts
consume resources; historical public-corpus acquisition prices are unknown.

## Verified P007 development experiment

Qwen2.5-1.5B base; one locked OpenMathInstruct-2 inventory, four allocation arms,
two student training seeds (17,23), one procurement draw. Each run uses256 optimizer
updates and524,288 supervised targets, complete answers, masked prompts/padding
and a common frozen learning-rate vector. Endpoint: one greedy evaluation on431
GSM8K training-split development questions at the fixed final checkpoint.

| Arm | Correct, seed17 | Correct, seed23 | Mean accuracy |
|---|---:|---:|---:|
| Repeat |309/431|307/431|71.46%|
| Solutions |354/431|355/431|82.25%|
| Breadth |350/431|352/431|81.44%|
| Mixed |348/431|351/431|81.09%|
| Base, zero-shot |256/431|—|59.40%|

Solutions−Repeat: **+10.79pp**, conditional paired-question95% interval
[7.19,14.39]. Breadth−Solutions: **−0.81pp**, interval[−3.71,2.20].
The second interval does not establish equivalence or exclude every3pp difference.
The first contrast does not isolate reasoning-path diversity from repeat exposure
or other data differences. Two seeds do not establish population seed robustness.

All eight terminal states,5,791 saved main/base outputs and final independent CPU
checks passed; eight interrupted middle diagnostic attempts remain unknown.
Formal endpoints are complete. Failed attempts and engineering work are separately
preserved. All main apps stopped and their containers exited. External Claude
review of the new evidence packet is **pending**, distinct from these local and
cloud verification results.

## Current next step and limits

P007A measures first/second/fourth usable-answer supply from one pinned teacher:
128 frozen problems, at most8 attempts each, at most1,024 outputs, zero student
training. It has its own finite15USD reservation and October13 01UTC cutoff.
P007B is a prepared breadth/depth×problem-price comparison using the same newly
metered source, with student targets/updates separately matched. Its numerical
wallets and execution admission await the verified pilot.

Latest complete-main workspace meter: **27.76043680USD at October12 19:06UTC**,
including engineering and failed work. This is delayed usage, not a final invoice,
per-arm acquisition cost or remaining-credit balance. Owner budget500USD with
at least50USD protected; unissued future credits are not part of admission.

The old bank cannot be priced with the new teacher's pilot. Development accuracy
does not establish uncontaminated generalization. The official GSM8K test was
already observed by this research effort in September. Distinct answer text does
not certify distinct reasoning strategies. See [audit qualifications](docs/audit/P007_REVIEW_DISPOSITION_20261012.md).
