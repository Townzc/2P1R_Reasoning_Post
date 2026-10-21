# Shared path stages — none executed

First source CR only must have scope `p011-C1-complete-path-CR`, exact12 source map,
original_group_binding_sha256, true input_preparation_authorized, real fixed
report bytes/SHA/target and PASS/PASS-WITH-NOTES. Record the real source CR as
private C1_FULL_PATH_SOURCE_CR_ACCEPTED.json, without claiming actual A1/numeric.
Then the single original-byte copy is:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_c1_inputs.py --original-binding reports/p011_20261020/c1_evidence_draft_v1/ORIGINAL_GROUP_BINDING_DRAFT.json --code-binding reports/p011_20261020/c1_full_path_preflight_v1/SOURCE_BINDING.json --review .local/p011_20261020/r1/C1_FULL_PATH_SOURCE_CR_ACCEPTED.json
```

After that real inventory, publish its full input evidence and an actual timing
proposal under the SAME request. A complete spec must pass c1_execution.validate_spec;
no synthetic900s/1.95USD fixture becomes a candidate. Same-request independent
scope `p011-C1-complete-path-CR-A1-A2-lite` must bind actual full source/input,
spec-file SHA, original binding, task-inventory and timing canonical SHA, all6
flags in c1_admission.reviewed_path and measurement_exceptions0. Source-only
approval cannot create C1_FULL_PATH_ACCEPTED.json or admit upload/worker.

Only after that, necessary fresh accounting and once-only upload/readback, actual
published acceptance and ordinary remote verification, use modal_c1::main once.
Its fixed spec path is reports/p011_20261020/c1_runtime_v1/SPEC.json (ABSENT now).
Future IO CLI is scripts/p011_c1_io.py upload|collect|audit --review ACTUAL_REVIEW.
All three outputs are canonical create-only c1_io_r1 directories. collect requires
original completion + actual STOPPED0; audit only follows complete collect. No
pending/failed/unknown return may use collect, and no whole helper retry exists.
These commands are not permission to supply placeholder acceptance or timing.
