# Research journal

This index records the question, motivation, competing explanation, design,
outcome and decision for each substantive attempt. It complements the
[machine-readable run registry](../reports/run_registry.json),
[current status](../reports/STATUS.md) and [resource accounting](../reports/compute_accounting.json).
Raw run artifacts remain the authority for numerical claims.

The historical entries below were reconstructed on 2026-09-09 from existing
records. Their explanatory questions are retrospective summaries, not claims
that a formal preregistration existed before those runs. Explicit post-hoc
analyses stay post hoc. A proposal is not an attempted or successful experiment.
Budget figures inside completed entries are historical charges, not the current
balance. Dates are UTC unless specified otherwise.

## Attempted work and completed analyses

| ID | Work date | Question or attempted change | Status | Outcome / decision |
|---|---|---|---|---|
| [C000](experiments/C000_environment_and_cpu_bootstrap.md) | 2026-09-05 | Establish a supported interpreter, verified model bytes and CPU checks | Environment failures corrected | Python 3.12 and official-digest verification retained; no task-semantic relaxation |
| [E001](experiments/E001_debug_provenance_failure.md) | 2026-09-05 | Can the first debug run establish a reproducible software gate? | Invalidated GPU attempt | Untracked execution source; no scientific evidence retained from its outputs |
| [E002](experiments/E002_debug_high_lr.md) | 2026-09-05 | Does the initial 0.5B recipe memorize 32 examples? | Completed; gate failed | 25/32 train, 0/16 dev; test a lower LR |
| [E003](experiments/E003_debug_lower_lr.md) | 2026-09-05 | Can the lower-LR debug recipe pass the same gate? | Completed; gate passed | 31/32 at 300 updates; development remained zero |
| [E004](experiments/E004_main_4090_memory_failure.md) | 2026-09-05 | Does unchanged 1.5B FP32 AdamW fit 24 GB? | Failed GPU attempt | OOM before an optimizer update; preserve recipe on a larger-memory GPU |
| [E005](experiments/E005_main_a800_profile.md) | 2026-09-05 | Does that recipe fit the supplied A800? | Completed profile | 110 updates; optimizer allocation succeeds |
| [E006](experiments/E006_main_a800_overfit.md) | 2026-09-05 | Does the main model pass the engineering gate? | Completed; gate passed | 32/32 train; 0/16 greedy and 0/64 sampled dev |
| [C001](experiments/C001_exact_matching_unconstrained.md) | 2026-09-05 | Are exact shared-structure/token controls feasible? | Completed CPU audit; inadequate operator coverage | 256 problems, but all selected paths additive/subtractive |
| [C002](experiments/C002_muldiv_small_pool.md) | 2026-09-05 | Does requiring multiply/divide preserve adequate support? | Completed CPU sensitivity audit | Only 64/1024 problems selected |
| [C003](experiments/C003_muldiv_larger_pool.md) | 2026-09-05 | Can a larger candidate pool supply 256 matched problems? | Completed CPU sensitivity audit | 256/4096 selected; selection and weak Surface control remain |
| [C004](experiments/C004_tokenizer_preparation_failure.md) | 2026-09-08 | Can the saved tokenizer serialize frozen pilot data? | Failed CPU preparation | Original tokenizer blob check failed; no solving |
| [C005](experiments/C005_development_support_failure.md) | 2026-09-08 | Do 1024 development candidates yield 16 exact blocks? | Failed CPU preparation | Only 14/16 blocks; enlarge the presolver pool |
| [C006](experiments/C006_frozen_pilot_preparation.md) | 2026-09-08 | Can all four conditions share a complete, audited dose? | Completed CPU preparation | Frozen 256/64/64 data and exact controls |
| [E007](experiments/E007_pilot_calibration.md) | 2026-09-08 | Is the common dose feasible and nondegenerate? | Completed; gate passed | 14/64 matched dev at the full 1024-update dose |
| [E008](experiments/E008_seed17_four_arm_pilot.md) | 2026-09-08 | Does Paths outperform globally matched allocation? | Completed single-seed pilot | Paths/GCM 23/64 vs 18/64; restricted development only |
| [A001](experiments/A001_seed17_trace_audit.md) | 2026-09-09 | Do displayed calculations support correct final expressions? | Completed post-hoc CPU analysis | Fully verified matched traces 21/64 vs 14/64; broader 1/64 each |
| [A002](experiments/A002_seed17_identity_and_success_audit.md) | 2026-09-09 | How do identity operations and success concentration qualify the result? | Completed post-hoc CPU analysis | Heavy identity-path selection and endpoint-dependent strata |

## Completed replication and concurrent CPU design checks

| ID | Registered phase or analysis | Status | Outcome / decision |
|---|---|---|---|
| [E009](experiments/E009_seed23_paired_replication.md) | Same-problem Paths/GCM seed23; evaluation seed17 | GPU, CPU output audit and independent weight backups complete | Primary 22/64 vs 17/64; complete traces 18/64 vs 16/64; broader 1/64 each; pause before more GPU |
| [A003](experiments/A003_pairing_seed_semantic_exposure_audit.md) | Are numerical path exposures also matched across allocation procedures/seeds? | Completed CPU audit during training without reading new evaluation outcomes | Identity exposures 2780 vs 2800; structural matching does not imply every numerical property is matched |
| [C007](experiments/C007_identity_family_inventory_failure.md) | Can the stored four paths support two paths of each identity category on the same problem? | Completed CPU check; proposed inventory reuse fails | 41 problems have at least one of each; zero have two of each; redefine construction before training |
| [C008](experiments/C008_complete_ordered_support_census.md) | Does complete ordered enumeration recover support hidden by stored-four selection? | Complete local CPU census, 256/256 questions | 132 support disjoint-AC 2+2; 131 support 4+4; matching remains untested in C008 |
| [C009](experiments/C009_token_structure_block_matching.md) | Exact token/structure/shared-block matching and fixed inventory-policy losses | Per-problem checks complete; key search stopped at prespecified cap | 131 raw → 67 equal-token → 66 structure-feasible; discovered 681 keys/7 questions/one four-question witness; global capacity unknown |

The E009 registration is preserved and results are appended separately. A003 and
C007 are dated CPU analyses, not retroactively registered hypotheses. Independent
weight backup completion is a separate recovery gate from a completed model run.

## Proposed scientific work, not executed

| ID | Idea | Status / decision gate |
|---|---|---|
| [P001](experiments/P001_iclr_positioning_and_semantic_intervention.md) | Test a controlled boundary between defined legal path families | Literature positioning and design critique completed; intervention and larger study remain proposals |
| [P002](experiments/P002_legal_support_enumeration_design.md) | Distinguish selected-inventory loss from legal path support and matching constraints | Census completed in C008; token/structure checks measured in C009; global join incomplete |

## Maintaining the record

Use [the entry template](experiments/_TEMPLATE.md) for a new idea or attempt.
Before a new scientific phase, record its contrast, endpoints, controls, costs
and stopping rule; link the frozen configuration. State whether the hypothesis
was formulated before or after the relevant outcomes. On completion, append
results and analysis from raw evidence, retaining the original prediction and
unfavorable outcomes. Do not rewrite a failed hypothesis into an apparent success.

A retry gets a new run ID and a linked attempt entry; changing a scientific
factor gets a new design entry. Avoid copying large logs into prose: link the
immutable artifact and retain the exact source/config/data identifiers there.
Publish each completed milestone and update this index. Credentials, connection
details, personal filesystem locations and model weights stay outside this journal.
