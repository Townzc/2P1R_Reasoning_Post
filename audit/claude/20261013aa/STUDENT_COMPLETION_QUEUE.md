# Claude audit 20261013aa (part 2) — p008-student-completion-queue-r1 @ 121f17b1: **PASS-WITH-NOTES (code, authority and quota scope)**

This review covers code, owner authority and quota scope only. It admits no student, gives no numeric G1, and does not close N2.

## Q1. Owner scope and transfer — YES
- **Owner authority.** `OWNER_COMPLETION.answer` = "学生计算截止延后、跑完为止" ("push back the student compute deadline; run until done"), as a direct reply to Codex. `validate_owner` pins the exact text, along with these fields: until-complete, per-worker caps unchanged, D2 deadline unchanged, maximum 8 workers, stage cap $250, reservation $249.68, ceiling $450, $50 protected, and freeze at 04:00 UTC (21:00 PDT).
- **Plan construction.** `make_plan` copies exactly the 20 original slots (18 students + base + audit) with **identical reservations**. Total = 500 + 756 + 10×818 + 8×1,253 = **19,460¢**, which matches `QUEUE_PLAN` and `TRANSFER_EXPECTED`. No budget is added.
- **Deadline.** The deadline is created + 518,400 s (6 days), under the 7-day Dict retention limit. It is a technical envelope only. Per-worker `max_seconds` are unchanged.
- **Original-slot fence.** `assert_original_absent` enumerates every original-campaign key and rejects any key whose first or second path component is a student/base/audit slot, so it covers unit and journal keys as well as claim, intent and terminal. `require_handoff` requires the exact immutable transfer record, and also requires that the original slot's claim, intent and terminal are all absent. It runs both locally and in the worker.
- **Unchanged.** The original pools, the failed D2 parent and the child are untouched. There are no retries.

## Q2. Source and gates — YES
- `completion_student_binding` equals the reviewed lineage binding except in two places:
  - the fixed `DEADLINE_EPOCH` check is replaced by `validate_completion_plan`, plus the owner and transfer digests;
  - `validate_quota` is added.
- Every gate that matters is still required: joint G1, the all-draw plan gate, input readback, merged lineage, the block-journal policy, and caps/reservations.
- `modal_students_completion.py` differs from the reviewed 8-GPU entry only in its source list, app name, binding import, and the two `require_handoff` calls. The science is untouched. 39/39 tests pass locally (completion + concurrency + lineage).

## Q3. Quota — YES, scoped correctly
`QUOTA_EVIDENCE` records **the workspace-wide concurrent-GPU limit of 10**, taken from the owner's screenshot (hash bound), with usage 1 at that time. It correctly does not claim a separate H100 quota or guaranteed availability. Running 8 workers stays within that limit. At each dispatch, `occupied_capacity` counts **every** listed container, including CPU and unrelated ones, which is conservative.

## Notes
- **CQ-N1.** The *old* student entrypoints (`modal_students*.py` on the original campaign) do not check `finite_student_successor`.
  - If one of them were run by mistake **after** a successor dispatch, it could still admit the same original slot until 02:00 UTC.
  - The new worker catches the reverse order (old first), but not this one.
  - The operational rule is to never invoke the old entries again. A one-line `TRANSFER_KEY` refusal in them would close the gap if they are ever touched.
- **CQ-N2.** The workspace-wide limit of 10 is shared with any other GPU use. If another job holds GPUs, dispatch will correctly refuse, not queue.
- **CQ-N3.** The freeze stays at 21:00 PDT: P008 results that finish later are labelled separately as later additions, which is consistent with the owner's plan.
