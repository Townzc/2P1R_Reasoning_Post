# Conditional create-only commands — all NOTRUN

Repository root; R=.local/p010_20261019/r1. Original full generation/scoring/metrics workflow remains in the immutable E3 and C6 runtime packets. Do not execute these adapters before those real prerequisites. No model, old oracle, scorer or analysis may be repeated.

- E3 after original complete raw/scoring/metrics and STOPPED0: `PYTHONPATH=. .local/midpoint_20261011/venv/bin/python R/publish_e3_completed_once.py` → new `reports/p010_20261019/e3_complete_results_v1`.
- C6 after combined21,371-row oracle, all four completed new-score jobs and both STOPPED0: same Python `R/publish_c6_remaining_completed_once.py` → new `reports/p010_20261019/c6_complete_results_v1`.
- Only after the complete C6 packet: `PYTHONPATH=. .local/p009_20261014/r1/analysis_env/bin/python R/analyze_c6_complete_once.py` → new `R/cue_benchmark_analysis_r1`; eight original contrasts once, no old statistics.
- Only after that completed analysis: ordinary Python `R/publish_c6_analysis_once.py` → new `reports/p010_20261019/c6_analysis_v1`.

R is a documented path abbreviation, not a shell variable. Use the full actual path. Check output absence and original source binding before invoking. Every partial output stays preserved; no whole-helper retry. Future actual A3 request must cite the original failed/new lineage, complete journals and fixed sample adjudication. E3 must dispatch before C6 under the frozen accounting-entry order; no change here.
