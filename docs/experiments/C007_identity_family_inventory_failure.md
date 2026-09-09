# C007 — The frozen four-path inventory cannot supply a same-problem 2+2 control

**Work date:** 2026-09-09 UTC. **Status:** completed CPU feasibility check;
candidate construction rejected for the current inventory.
**Hypothesis timing:** follow-up to A002/A003 and the semantic-control proposal,
after seed17 outcomes and after seed23 configuration freeze. This check was
conducted during the active seed23 training/collection phase without reading any
seed23 outcomes. The journal records completed CPU work, not an earlier
preregistration or a new GPU experiment.

## Question and motivation

[A003](A003_pairing_seed_semantic_exposure_audit.md) shows why global structural
matching is not a complete semantic-exposure control. A candidate 2×2 mechanism
study might cross allocation with identity-containing versus identity-free path
families. Can each family supply at least two distinct selected paths for the
same training problem, using only the already frozen four-path inventory?

## Competing explanations and design

The existing four paths might provide balanced family support even though their
aggregate identity rate is high. Alternatively, most inventories might be
uniform or have only one identity-free path, preventing within-family path
diversity in both families. The necessary gate is elementary: count 0/1/2/3/4
identity-containing paths per problem, then count problems with at least one of
each family and with at least two of each.

Read only the frozen `train_blocks.json` and saved per-problem identity labels.
Check block/problem identities, inputs, targets, prompts and all four unique
path IDs before counting. Use the established identity convention, including
numerically evaluated zero/one intermediates. Do not enumerate more solutions,
solve another pool, inspect holdout groups, infer labels from new model outputs,
or modify existing data. This attempt uses no additional GPU process time.

## Evidence and result

The [small feasibility report](../../reports/SEMANTIC_CONTROL_FEASIBILITY_20260909.md)
contains the exact dependency-free reproduction code and expected output.

| Identity-containing paths out of four | Training problems |
|---|---:|
| 0 | 72 |
| 1 | 0 |
| 2 | 0 |
| 3 | 41 |
| 4 | 143 |

There are **41/256 problems with at least one path in each family**, but
**0/256 with at least two in each**. Every mixed inventory is three identity-
containing paths and one identity-free path. Counts reconcile with the previous
695/1024 identity-containing selected paths: 41 × 3 + 143 × 4 = 695. The embedded
read-only reproduction was executed and matched its expected output exactly.

### Exact source provenance

| Source | SHA-256 |
|---|---|
| `runs/pilot_v1_20260908_r3/train_blocks.json` | `e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea` |
| `reports/pilot_v1_structure_bias_20260909/per_problem.jsonl` | `7ea6f0cb0b39a2df41440c49534b036ef4440953965943c6cb91cd67fe8dbdd0` |

The accompanying context is the
[training-exposure report](../../reports/PAIRING_SEED_SEMANTIC_AUDIT_20260909.md)
and its [source-hashed numerical records](../../reports/pairing_seed_semantic_audit_20260909.json).
No seed23 model score is evidence for this inventory result.

## Interpretation, limitations and next decision

Reject **this specific reuse of the existing four selected paths, divided by
identity presence**, for an at-least-two-paths-per-family same-problem control.
Repeating the sole identity-free path does not create another distinct path;
rewriting its sentence frame adds surface variation. The weaker 41-problem
one-per-family support does not prove token, structure, difficulty or sample-size
feasibility either.

CountDown requires each supplied number to be used exactly once. An identity
operation can legitimately incorporate a supplied one or a zero/one computed
from other inputs. Identity-containing paths are valid solutions under the
frozen rules, not invalid examples; their family is not the Surface control,
which changes wording while preserving equations and order. These binary labels
also do not by themselves establish distinct semantic strategies.

Zero support in this inventory does not prove that these problems lack other
solutions, that a larger path inventory cannot work, or that semantic strategy
diversity is ineffective. It rules out one cheap candidate construction before
spending on it. A further design would need an explicitly reviewed path-family
construction or richer inventory and new shared-support/matching checks. No
such solver expansion, training phase, budget extension or generator change is
authorized or implemented by this entry. E009's data and primary endpoint stay
as frozen.
