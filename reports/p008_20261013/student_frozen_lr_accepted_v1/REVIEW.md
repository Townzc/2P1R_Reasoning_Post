# Claude audit 20261013ad — p008-student-frozen-lr-unattempted-r1 @ c5053814: **PASS (code; 8 unattempted T1 may proceed)**

## My miss, stated first
In 20261013ab my own recomputed LRs differed from the plans by up to 1.36e-20, in 6 entries (T1) and 38 entries (T8). I accepted the plans because they equal the frozen `LR_VECTORS.json`. **I did not connect this to the fact that `student_runtime.validate_plan` recomputes `lrs(u)` on the worker host and requires exact equality.** Had I flagged it, the two D1 B1/p0 students would not have failed at the LR guard. Both failed after about 25 s with **zero updates and zero endpoint outputs**, so no science or outcome was observed. Setup time was still billed. Per-host libm sensitivity is now on my checklist.

## Review
- **Q1. Exact frozen bytes: YES.**
  - `validate_frozen_lrs` requires a list of finite positive floats of length `u ∈ {256, 1024, 2048}` whose canonical digest equals the pinned hash.
  - I checked independently that each `FROZEN_LR_SHA256[k]` equals `digest(LR_VECTORS[k])`, and that the `LR_VECTORS.json` file sha starts `cb9c2e04…`, matching the constant.
  - All 18 published plans validate.
  - **A one-ULP change (`nextafter`) is rejected.**
  - No tolerance is used, and nothing is recomputed on the host.
- **Q2. Nothing else changed: YES.**
  - Compared with `student_runtime.validate_plan`, the only difference is that `plan['lrs']!=lrs(u)` is replaced by `validate_frozen_lrs`. Seed, update count, inventory order, exposure balance, budget report and the pre-outcome target binding are identical.
  - `frozen_lr_block_student_runtime.py` differs from `block_student_runtime.py` only in its import line.
  - Training already used `plan['lrs']`, so the science is unchanged.
  - The entry differs from `modal_students_completion.py` only in its source list (+2 files), app name, worker import and the exclusion guards.
  - The inputs, spec and plans are the same reviewed bytes (0be9e6e0).
  - Tests pass locally.
- **Q3. Exclusions: YES.** `base`, `d1_b1_p0_breadth_t1` and `d1_b1_p0_depth_t1` are refused in both `main()` and `work()`. The failed evidence is preserved and is not relabelled.
- **Q4. Scope: YES.**
  - The 8 never-attempted T1 slots may proceed under this 32-source bundle, once the runtime-review gate binds it.
  - The 8 T8 slots stay blocked on N2.
  - The T1 timing roster still contains the 2 failed entries, so **N2 cannot close unless the owner approves two replacement runs or a separately reviewed roster rule.**

## Owner decision needed
Replacing the two failed slots is **outcome-blind**: both failed before any training, so their scores are unknown and replacing them cannot select on results. Replacement needs new reservations of 2 × 818¢ = $16.36, which takes P008 from $249.68 to about $266, over the $250 stage cap. Without the replacements:
- the D1 B1/p0 breadth-vs-depth cells are missing;
- the frozen T1 roster cannot complete, so the T8 gate stays shut.
