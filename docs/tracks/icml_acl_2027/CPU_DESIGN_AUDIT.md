# LT001 offline planning audit

2026-09-11. This records documentation, source-inspection and analytic arithmetic checks. It is not a training result, acquisition experiment, independent-agent review or passed GPU release test.

## Checked inputs

- Repository baseline: `73170a459e9fed2c5fdea6a9afb40b4b80837bb2`; read the current protocol, decisions, status/handoff and P004/P006/C017 evidence. Historical artifacts were not edited.
- [Primary source manifest](sources.json): five closest papers; course and venue pages; pinned author source at `838c28e48b8a2cc9278263a730f0aa3c7d765a4e`. The complete GitHub tree was not truncated. No MathQA-named path was found; this is a limited release-inspection finding, not proof that no additional author artifact exists.
- No final-test/reserved-development contents or private resource ledger were read for these checks. Existing compact reports supplied the historical counts. No large data/model download or remote code execution occurred.

## Analytic calculations

The [precision CSV](precision_plan.csv) contains 18 deterministic planning scenarios: n in {64,80,288,368,512,1319}, assumed discordance q in {.1,.2,.3}, three contrasts, family alpha .05 and approximate power .8. Reproduction uses Python's standard library only:

```python
from statistics import NormalDist
from math import sqrt, ceil
z = NormalDist().inv_cdf(1 - .05 / (2 * 3)) + NormalDist().inv_cdf(.8)
mde_percentage_points = 100 * z * sqrt(q / n)
n_for_three_points_at_q_point_two = ceil(z * z * .2 / .03**2)  # 2327
```

The calculation concerns evaluation-question uncertainty near the null, conditional on fixed trained endpoints. It omits pool/training variability and cannot establish actual power without observed or independently justified discordance assumptions. It generated no synthetic model predictions.

Protocol arithmetic: 128×8=1,024 maximum calibration calls; 1,024×768=786,432 maximum emitted tokens; 192×4=384×2=768×1=768 nominal validation pairs; 3 policies×2 training pools×2 optimizer seeds=12 proposed endpoints. The optional capped/nominal control adds at most 2×2×2=8 endpoints. None is an approved phase or a runtime estimate. Development-role arithmetic is 80+64+80+288=512, with 432 still reserved at the current baseline; future roles were not materialized.

## Completed publication checks

The local check passed: 13 package links resolve; the JSON source manifest and all 18 CSV scenarios parse; three inspected author files match their recorded hashes; all protocol/count/precision arithmetic above agrees. `git diff --check` passes. Modified tracked files are documentation only, and `src`, `scripts`, `analyses`, `configs`, `runs` and `tests` have no diff from the branch baseline. A scan of new content/added lines found no private absolute paths, connection addresses, credentials or task identifiers. This scan supplements review; it is not a proof that every possible secret pattern is excluded.

The initial staged whitespace check flagged the CSV writer's CRLF line endings; these were normalized to LF without changing any values before publication. No unchanged project/model tests were rerun; their previous results remain historical. Commit and remote-branch equality are checked separately at publication and reported in the user handoff. Publication is confined to the assigned branch; no merge, main push, resource reservation or server operation is part of these checks.
