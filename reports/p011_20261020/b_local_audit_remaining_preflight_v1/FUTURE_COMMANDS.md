Future-only. Explicit exception, exact101 binding and all7 flags must be accepted before either remaining tail. Check new/original fences and preserve the original absolute windows.

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/continue_p011_b_student_local_audit.py --job B_B1_s17_r1 --review .local/p011_20261020/r1/B_STUDENTS_LOCAL_AUDIT_REMAINING_CR_ACCEPTED.json --original-review .local/p011_20261020/r1/B_STUDENTS_POST_LONG_FAILURE_A1_A2_ACCEPTED.json
```

Only after this continuation's COMPLETED and its full proof, first score once:

```sh
PYTHONPATH=. .local/p009_20261014/r1/math_verify_env/bin/python scripts/p011_b_students_post_long_failure_io.py score --job B_B1_s17_r1 --review .local/p011_20261020/r1/B_STUDENTS_POST_LONG_FAILURE_A1_A2_ACCEPTED.json
```

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/continue_p011_b_student_local_audit.py --job B_B3_s17_r1 --review .local/p011_20261020/r1/B_STUDENTS_LOCAL_AUDIT_REMAINING_CR_ACCEPTED.json --original-review .local/p011_20261020/r1/B_STUDENTS_POST_LONG_FAILURE_A1_A2_ACCEPTED.json
```

Only after this continuation's COMPLETED and its full proof, first score once:

```sh
PYTHONPATH=. .local/p009_20261014/r1/math_verify_env/bin/python scripts/p011_b_students_post_long_failure_io.py score --job B_B3_s17_r1 --review .local/p011_20261020/r1/B_STUDENTS_POST_LONG_FAILURE_A1_A2_ACCEPTED.json
```

After both original scores close, run the first original B contrast once:

```sh
PYTHONPATH=. .local/p009_20261014/r1/analysis_env/bin/python scripts/analyze_p011_b_students_post_long_failure.py --review .local/p011_20261020/r1/B_STUDENTS_POST_LONG_FAILURE_A1_A2_ACCEPTED.json
```

Do not run original audit or collect commands again. No production command in this file has run.
