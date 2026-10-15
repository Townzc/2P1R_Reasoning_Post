# Future commands, NOT RUN

Only after the exact three-source helper scope passes a real fixed report:
save stage1_s1_r1/READONLY_PUBLICATION_CODE_ACCEPTED.json with scope,decision,
source_files,target_commit,report_commit,report_sha256,local_report_path.
The separate actual runtime and all scientific gates are still required.

```
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p009_s1_observe.py status --run s1_s17_n400 s1_s17_n3200
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p009_s1_observe.py startup --run RUN
PYTHONPATH=. .local/p009_20261014/r1/analysis_env/bin/python scripts/publish_p009_s1_results.py run --root .local/p009_20261014/r1/stage1_s1_r1 --run RUN --out reports/p009_20261014/stage1_s1_results_v1/RUN --code-review .local/p009_20261014/r1/stage1_s1_r1/READONLY_PUBLICATION_CODE_ACCEPTED.json
PYTHONPATH=. .local/p009_20261014/r1/analysis_env/bin/python scripts/publish_p009_s1_results.py first-pair --root .local/p009_20261014/r1/stage1_s1_r1 --out reports/p009_20261014/stage1_s1_first_pair_v1 --code-review .local/p009_20261014/r1/stage1_s1_r1/READONLY_PUBLICATION_CODE_ACCEPTED.json --analysis-review .local/p009_20261014/r1/STAGE1_REGISTERED_ANALYSIS_CODE_ACCEPTED.json
```

Replace RUN with the actual registered slot. Status only names active/nonclosed
original calls and normally runs every30min. Startup is once after its true
first16 ack. Publication requires complete original result/fullraw-state proof,
frozen full scoring and actual STOPPED0, with no prior output directory. Any
partial is preserved; no whole-helper retry. Real independent samples/A4
remain necessary before futility continuation or G1.
