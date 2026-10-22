# Once-only future commands; inspect fences/CLI/receipts first

The original data constructor32526 is already ACTIVE; never call it again.

After data completion and this exact source commit is published, metadata only (no GPU or re-encoding):
```
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_ext4b_actual_runtime.py --data-review .local/p011_20261020/r1/EXT4B_DATA_CR_ACCEPTED.json
```
Publish actual input/metadata and request exact full-source CR plus actualA2. Only after both genuinely accepted:
```
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/record_p011_ext4b_budget.py --source-review R/EXT4B_FULL_RUNTIME_CR_ACCEPTED.json --actual-review R/EXT4B_ACTUAL_A2_ACCEPTED.json --directory R/ext4b_runs_r1/budget_ACTUAL_UTC
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_ext4b_io.py upload --source-review R/EXT4B_FULL_RUNTIME_CR_ACCEPTED.json --actual-review R/EXT4B_ACTUAL_A2_ACCEPTED.json
```
R is the literal .local/p011_20261020/r1 path; substitute it in commands, not a private environment assumption. Fresh rate <=1h must still hold at first worker admission. If upload consumes that window, do not reuse stale admission; save a new, explicitly dated necessary admission snapshot before any first model call. Old snapshot stays historical.

Start each job once with scripts/run_p011_ext4b_once.py --job exact_JOB --source-review exactCR --actual-review exactA2 --budget-json exact_JOB_BUDGET. Two independent CLI sessions may run concurrently within8sharedslots. Wrapper uses modal run -m experiments.p011.modal_ext4b. Never use a barefilename invocation. No commit/push until BOTH submitted or explicitly preentry terminal. No manual direct worker call.

On first complete result and whole-appSTOPPED0: p011_ext4b_io.py collect/audit/score with --attempt-name JOB_attempt1 (or the only successful attempted2). Collect usesModalenv; auditdata_pipelineenv; scoremath_verify_env. Fullstateaudit concurrency1. Original failed attempts are preserved, not fed to completed collector. Explicit proven infraresume uses prepare_p011_ext4b_infra_resume.py, new fresh remainingbudget and same wrapper --attempt2 --resume-json exactRESUME; not an automatic controller, no thirdattempt.

After both complete scoreproofs, analyze_p011_ext4b.py with analysis_env --small-attempt exact --large-attempt exact --source-review exactCR --actual-review exactA2 once; then newactualA3. No oldoriginalarms or benchmarks rerun.
