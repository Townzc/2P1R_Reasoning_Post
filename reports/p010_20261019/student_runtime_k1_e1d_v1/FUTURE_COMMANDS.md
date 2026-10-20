# Only after actual A1 and this exact A2

Use the original project root and named paths. Never use these as a batch submission script. Verify a free slot and first SUBMITTED receipt before each next original call. Tier3 and disputed K4/K8 are absent.

- Upload once: `PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_student_k1_e1d_io.py --root .local/p010_20261019/r1 --spec reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json`
- Entry only: `.local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p010.modal_students_k1_e1d::main --run RUN --receipt-dir .local/p010_20261019/r1/student_runs/RUN --data-review-json ACTUAL_TEACHER_A1 --runtime-review-json ACTUAL_K1_E1D_A2 --budget-json FRESH_ACTUAL_T_BUDGET`
- Original result+real STOPPED0: one existing `scripts/p010_transfer.py collect --receipt RECEIPT --remote /p010-20261019/students/RUN --out NEW_EXPORT`.
- One `scripts/audit_p010_student_k1_e1d.py records`, then `audit` with originalreceipt/export, student_inputs_r2, exactSPEC/run/records/tokenizer/gold/teacherA1/runtimeA2 and newoutput. Actual argument schema is in the snapshotted source.
- One `scripts/score_p010_student_k1_e1d.py --generation-oracle NEW_ORACLE --receipt RECEIPT --spec SPEC --run RUN --data-review ACTUAL_A1 --runtime-review ACTUAL_A2 --out NEW_SCORES`, in the frozen math_verify_env.25200local seconds+5cleanup/2readers/8secondpair guard; confirmed journal values stay immutable.

Unknown/partial evidence is preserved and reconciled; no whole-helper rerun, model retry, state reload or raw re-decode. Fresh necessary budget snapshot at a real paid stage, no repeated billing just for waiting. Real A3 and actual A4 follow complete results.
