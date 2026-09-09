# A003 — Canonical matching leaves numerical exposure differences

**Work date:** 2026-09-09 UTC. **Status:** completed CPU training-exposure audit.
**Hypothesis timing:** prompted by A002 after seed17 outcomes and after seed23
configuration freeze; conducted during the seed23 training phase. This is not an
earlier preregistration. The report records 2026-09-09T06:01:53+00:00 and the
coordinator's statement that training logs existed while seed23 development
outcomes had not yet been generated. This auditor read neither those logs nor
any seed23 model outcomes.

## Question and motivation

[A002](A002_seed17_identity_and_success_audit.md) established that many selected
arithmetic paths contain numerical identity operations. Does the exact
per-update canonical-structure matching also match these numerical properties,
and which properties change when GCM's assignment seed changes from 17 to 23?
The purpose was to clarify the scope of the fixed
[E009 replication](E009_seed23_paired_replication.md) before interpreting its new
evaluation outcomes, without modifying its data or training plan.

## Competing explanations and design

Canonical operator trees do not encode evaluated operand values. Their matching
could coexist with differences in identity operations, fractional/negative
intermediates or assignment of deeper paths to individual problems. Conversely,
these data could happen to match some such properties exactly. An observed
residual would refute only that attribute's complete matching, not the separate
canonical matching claim or the validity of the allocation comparison.

Read only each seed's frozen Paths/GCM rows and common schedule. Use the existing
identity definition, a separate AST-whitelisted exact-rational walker, and an
independent check of the displayed training equations. Count actual scheduled
presentations at global, update and problem levels. Define intermediate values
as the two nonroot binary-operation results; use ordered-tree depth before AC
canonicalization. The common 1024 updates present each of 1024 rows four times,
for 4096 exposures per arm and 16 per problem. All reported residuals are GCM
minus Paths. No generation, solver expansion, development-result analysis,
holdout reading, training edit or additional GPU process time was involved.

## Evidence and result

The [full report](../../reports/PAIRING_SEED_SEMANTIC_AUDIT_20260909.md) embeds the
bounded computation. Its [companion JSON](../../reports/pairing_seed_semantic_audit_20260909.json)
retains global and residual histograms, 256 per-problem records and source
hashes. Every corresponding update has the same ordered problem IDs and
canonical-structure histogram between arms in both seeds.

- Identity-operation exposures are **2780 Paths versus 2800 GCM** out of 4096
  in each seed. The global +20 residual is unchanged; updates with a nonzero
  identity residual change from **44/1024 to 28/1024**.
- GCM's intermediate-one occurrences change from **960 to 928**; Paths stays
  at 956. The GCM-minus-Paths residual therefore changes from +4 to -28.
- Every selected training trace has **zero fractional intermediates**. Global
  and per-update negative-intermediate exposure and depth sums match, but
  per-problem negative-intermediate and depth exposure differ on **64/256** and
  **124/256** problems respectively in each seed.
- GCM changes its assigned path on **196/256** problems. At least one audited
  attribute changes for **99/256**, including identity status on **12/256**.
  Paths' per-problem path support and global audited histograms remain unchanged.

All 4096 stored training rows across the two seeds and two arms passed the
independent displayed-equation/depth check. A fresh-workspace run reproduced the
JSON byte for byte; its embedded computation SHA-256 is
`b1bc6b925333ab789bb447b8a94f4e27931a255a7e1a7a27dcbfd104265f1ca3`.
These are CPU checks, not new GPU measurements or seed23 evaluation results.

### Exact source provenance

| Source | SHA-256 |
|---|---|
| `runs/pilot_v1_20260908_r3/train_paths.jsonl` | `882934ff99b28f835d29bb6e4357126bcd746475519890bb25b142a9c70cbe30` |
| `runs/pilot_v1_20260908_r3/train_gcm.jsonl` | `8f10816657485b8bd33299bcc0d0a4b218c7c7f3f48efa7a33f0000ecb2a69b8` |
| `runs/pilot_v1_20260908_r3/schedule_seed17.json` | `7eb9816e0d7508e439ca31e3473740831c3f7e3a40afd894312a52365c996a0f` |
| `runs/pilot_replication_seed23_20260909_r1/train_paths.jsonl` | `0d2cb55bf4d7d6daad37b3438d323503074a4c6b512d88be0af69395dc5c98d7` |
| `runs/pilot_replication_seed23_20260909_r1/train_gcm.jsonl` | `df7c98783b3dc42e0dfdef2b80206dd2fd165ed1fe8a48932bf2e9a7fd3aea3f` |
| `runs/pilot_replication_seed23_20260909_r1/schedule_seed23.json` | `0b23fde1ee5e2739c30d3a40191cc315fab4d2b54ebd4d2e12eb277b3c6f24b7` |
| `src/countdown_smoke.py` | `2249e313c60090958d5ddfe474dc44f2dff6337dbccc79a6ee48498254531058` |
| `scripts/audit_pilot_structure_bias.py` | `f868213c4cbc20833356291051b3c31a9ea742ce744c70755abca509c9fee8f8` |

## Interpretation, limitations and next decision

The pair estimates a conditional contrast between the specified allocation
procedures on this frozen pool and pairing seed. It does not isolate abstract
semantic strategy diversity while fixing every numerical feature. Changing
assignment, order and training RNG jointly is part of the declared replication;
this analysis does not separate their effects.

Numerical exposure changes may be consequences or components of the allocation
treatment itself. Labeling all of them confounders would assume an unsupported
causal model; correlating them with a later outcome would not prove a mechanism.
Post-outcome adjustment could change the estimand or condition on treatment-
induced quantities. This audit makes no such adjustment. Attribute counts are
not a full equivalence relation, a complete joint-distribution match, or a model
of task difficulty. The absence of fractional intermediates applies only to the
selected training inventory, not all solutions to its problems.

Retain the fixed E009 configuration and original primary endpoint. For a later
mechanism comparison, specify which path property changes and which numerical
properties should be controlled before creating data. Report common support,
selection/difficulty changes and residuals at the needed levels. Requiring each
problem's entire property distribution to match may remove part of the intended
allocation treatment, which calls for an explicit new estimand. The subsequent
[C007 inventory check](C007_identity_family_inventory_failure.md) tests one small
candidate reuse of the current paths rather than launching a new search.
