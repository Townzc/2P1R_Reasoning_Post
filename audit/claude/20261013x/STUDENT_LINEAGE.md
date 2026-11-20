# Claude audit 20261013x (part 2) — p008-student-parent-child-lineage-code-r1 @ 8f31b0ca: **PASS-WITH-NOTES (code only)**

This verdict admits no student; it only reviews the code.

- **Q1. Lineage.** YES.
  - `validate_pool_lineages` requires exactly three records: draw 1 `completed_original` (pool_d1 completed), draw 2 parent `pool_d2` **failed**, and draw 2 child `pool_d2_remaining` completed under the child campaign.
  - It checks each record's claim SHA and hash format. It also requires a merged proof that shows parent and child raw outputs re-decoded, all wallets replayed, 3,992 parent outputs plus more than 0 child outputs, and parent/child terminals equal to the records.
  - No completed parent is synthesized.
- **Q2. Gates intact.** YES.
  - Diffed against the originals, the only changes are these:
    - `main_binding.validate_binding` swaps the old rule "both pools completed" for the lineage roster;
    - `student_binding.validate_student_binding` drops the same pool-completion check;
    - `modal_students_lineage.py` adds the three source names, renames the app, and drops the runtime `status=='completed'` check, because the status is now enforced by the validated roster tuples.
  - Everything else is unchanged: the joint all-draw plan gate, common targets, per-draw G1 bound to the oracle hash (for D2, the **merged** oracle), the block-journal policy, input readback, caps and reservations.
- **Q3.** The science files (`block_student_runtime`, `block_journal`) are untouched. 13/13 synthetic tests pass locally with `PYTHONPATH=.:tests`. They are correctly described as synthetic.

**Note (schedule, for the owner).** The joint-T rule still applies, so **every** student, D1's included, waits for the child (finishing by 20:00 UTC at the latest), the merged D2 G1, and the joint plan gate. On the frozen caps, 18 students plus the base are 39.4 GPU-hours, about 9.9 h across 4 lanes. Starting around 21:00 UTC leaves about 5 h before the 02:00 UTC hard stop. This is cap arithmetic, not an ETA. Under the owner's choice, an incomplete queue is reported as pending. ADMISSION already records `full_student_queue_completion_not_guaranteed`.
