# Future construction — only after exact revised CR

These are not executed. `LONG_DATA_CR_ACCEPTED.json` must quote a real fixed
PASS / PASS-WITH-NOTES report and bind every field in SOURCE_BINDING, including
owner_amendment_sha256 and proposal_sha256, plus operational_details_accepted=true.
Original r1 CHANGES-REQUIRED is not acceptance. Both output directories remain
absent; create-only failure/partial retention prohibits whole-tool retry.

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_inputs.py --mode ot3 --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --owner-amendment .local/p011_20261020/r1/OWNER_LONG_DATA_AMENDMENT.json --amendment-proposal reports/p011_20261020/LONG_DATA_REVIEW_AMENDMENT_PROPOSAL.md --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model --out .local/p011_20261020/r1/ot3_inputs_r1
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_inputs.py --mode am --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --owner-amendment .local/p011_20261020/r1/OWNER_LONG_DATA_AMENDMENT.json --amendment-proposal reports/p011_20261020/LONG_DATA_REVIEW_AMENDMENT_PROPOSAL.md --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model --out .local/p011_20261020/r1/am_inputs_r1
```

Actual construction outputs need A1; no cloud/model/training runtime is admitted
by this data-only CR. P010 deadline19UTC Oct21 remains separate from P01105UTC Oct22.
