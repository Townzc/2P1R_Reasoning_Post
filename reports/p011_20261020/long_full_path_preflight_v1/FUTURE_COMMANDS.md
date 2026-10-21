# Future commands — each once, only after its real prerequisite

1. Full source CR must explicitly authorize the original training-input consumer
and first600 endpoint prompt encodings; source review is not paid admission:

```
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_runtime_inputs.py --review .local/p011_20261020/r1/LONG_FULL_PATH_SOURCE_CR_ACCEPTED.json
```

2. Append actual input inventory/A1, model assets, complete timing evidence,
resource limits, current rate, local score/transfer window and exact SPEC to the
SAME shared request. Only its genuine full A2-lite acceptance authorizes upload.
SPEC.json is deliberately absent; CLI/image cannot be imported successfully now.

3. For each real admitted JOB, with fresh full shared ledger budget and original
raw report bound, call upload once. It reuses already-present identical input/model
bytes, writes only missing files and checks every exact readback; no force upload.

```
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_io.py upload --job JOB --review .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p011.modal_long::main --job-id JOB --review-json .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json --budget-json FRESH_JOB_BUDGET_JSON
```

Later A/D also supplies --selection-json with genuine Claude original smoke
selection report; first three A7/baseline jobs require no selection. Use exact
logical IDs from future SPEC, never an invented retry/suffix. All original claim,
partial or unknown calls are permanent; disconnection does not imply failure.

4. Only original completed result + actual provider STOPPED/owned0 permits:

```
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_io.py collect --job JOB --review .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/p011_long_io.py audit --job JOB --review .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/p009_20261014/r1/math_verify_env/bin/python scripts/p011_long_io.py score --job JOB --review .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json
```

Both existing score/analysis Python paths were found locally without execution.
The actual scorer still verifies pinned versions; no installation or version change
is authorized to fit the new path.
After two complete scores, once per allowed original contrast:

```
PYTHONPATH=. .local/p009_20261014/r1/analysis_env/bin/python scripts/analyze_p011_long_pair.py --left LEFT_JOB --right RIGHT_JOB --review .local/p011_20261020/r1/LONG_PATH_A1_A2_ACCEPTED.json
```

Inspect fixed directories/processes before each tool. Partial transfers preserve
valid bytes and require bounded reconciliation, never whole-tool/model retry.
Actual A3 and Claude smoke selection remain subsequent independent reviews.
