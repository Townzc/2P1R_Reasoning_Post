# Problems, Paths, or Repeats?

**Current research:** allocating data-acquisition budgets for reasoning SFT.
**Working branch:** [`codex/icml-acl-2027`](https://github.com/Townzc/2P1R_Reasoning_Post/tree/codex/icml-acl-2027). The repository default `main` is historical.
This is a living research record, not presentation or assignment prose.

## Start here

- [Shared workboard / 工作总表](docs/WORKBOARD.md)
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
preserved. All main apps stopped and their containers exited. Claude reviewed the fixed main packet with **PASS-WITH-NOTES**: primary trained-model scores agree; base is sensitive to parsing. Scope and unresolved findings are in the [audit disposition](docs/audit/P007_COST_METRIC_REVIEW_20261012.md).

## Current next step and limits

P007A is complete:1,024 physical attempts,959 usable answers,59 invalid answers
and6 rejected valid duplicates; all costs retained. At least1/2/4 usable answers
were available for125/123/122 of128 parents. All1,024 outputs were independently
rescored and both apps stopped with zero containers.
[Verified pilot](reports/sft_allocation_midpoint_20261011/P007A_RESULTS_20261012.json).

P007B numerical admission is frozen: breadth/depth×problem-price0/4m,
equal1.091289088USD scenario caps, actual active-time wallets, same teacher.
All four procurement cells are now verified and released: low-price breadth437 usable answers over437 problems versus depth650 over171; high-price breadth215 over215 versus depth449 over117. All2,064 outputs were rescored. The high-price breadth cell retains an interrupted192-output prefix and a conservatively reconstructed charge; the continuation generated only96 new outputs. This asymmetric interruption limits a clean price-effect claim. These are supply results, not student accuracy.

The original time-priced students are independently verified and closed: breadth953/1319 (72.25%), depth969/1319 (73.46%), one training seed. They remain operational pilots; six untouched original students and their audit are retired. These two scores do not identify a problem-price interaction. [Pilot closeout](reports/sft_allocation_midpoint_20261011/P007B_OPERATIONAL_PILOTS_CLOSED.json).

After Claude C-B1, the owner approved a [fixed-token-tariff revision](docs/experiments/P007B_token_tariff_revision.md). Eight new finite students use saved teacher prefixes, one hypothetical tariff and524287 common targets over256 updates. All eight CPU plans passed; no new teacher output. At23:09UTC October12, the first two remain in final evaluation; six remain unstarted. [Stage evidence](reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FIRST_PAIR_TRAINED.json) and [new student admission](reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json). Claude round4 independently reproduced v2plans/exposure and original-pilot outcomes (PASS within stated scope); the eight new outcomes and subsequent reporting-only changes remain externally pending. Unequal unused caps and repeated exposure prevent claims of equal actual spending or an isolated diversity mechanism.

Latest workspace meter: **51.83084103USD at October12 23:09UTC**, including engineering and failed work. Delayed usage is not a final invoice or credit balance. Conservative reservations366.50USD are distinct from spend;500USD total, maximum450USD spend, with at least50USD protected.

The old bank cannot be priced with the new teacher's pilot. Development accuracy
does not establish uncontaminated generalization. The official GSM8K test was
already observed by this research effort in September. Distinct answer text does
not certify distinct reasoning strategies. See [audit qualifications](docs/audit/P007_REVIEW_DISPOSITION_20261012.md).
