# Conditional future commands — NOT RUN

Working directory is the `research_tracks/icml_acl_2027` root. Actual acceptance
must be created only after reading the full fixed non-Z1 Claude report and
checking its scope `p011-OT3-AM-long-data-construction-CR`, decision PASS or
PASS-WITH-NOTES, exact three-source map, source-lock SHA, plan SHA, report SHA,
and `operational_details_accepted=true`. Preserve report commit/event/read time.
The private acceptance must contain `local_report_path` pointing to its saved
original report. No placeholder approval file is supplied.

After all OT3 raw downloads complete, the one OT3 production construction is:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_inputs.py --mode ot3 --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model --out .local/p011_20261020/r1/ot3_inputs_r1
```

The independent, one paired-AM production construction, after both raw math
files complete and the same path-level CR is accepted:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_inputs.py --mode am --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model --out .local/p011_20261020/r1/am_inputs_r1
```

Save original CLI IDs and separate logs before any subsequent invocation. If a
directory or partial evidence exists, do not rerun or clear it. Any true deficit
in parents or exact whole-answer budget is reported; no alternate sample,
answer replacement, budget change, training or automatic retry follows.

Actual data outputs require the plan's A1 review. The CR is shared by both data
modes and all cells; this does not add a per-cell gate or admit any model call.
