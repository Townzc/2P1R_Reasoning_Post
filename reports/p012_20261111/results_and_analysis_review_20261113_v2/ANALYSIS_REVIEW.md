# First-use review of the registered numeric analysis

Candidate code: `analysis/p012_registered.py`; seven synthetic tests in `tests/test_p012_registered.py`, all pass. Dependencies pinned in `analysis/requirements-p012.txt`. No real endpoint labels have been analyzed by this candidate.

The runner requires an accepted40-character analysis review commit and all eight main full-finetuning settings. It binds input, raw, generation-manifest and Boolean-label hashes; checks dose, family, task, greedy sampling and seed; rejects missing/duplicate/unresolved labels. It pairs by frozen question ID, not row order. Exploratory/Tinker results cannot enter this main-grid CLI.

Registered contrasts: P-L, P-R, P-K8, K8-R, and P-beforeSFT. Delta-SFT uses the frozen four-shot C7 baseline on the identical MATH500 subset or fullGSM1319. Each training seed is reported separately. MATH allocation contrasts use5000 questions. NumPy2.5.4, PCG64 seed20261111,10000 paired-question bootstrap draws and linear2.5/97.5percentiles are fixed. Seed-mean point estimates are also reported; a supplementary seed-mean interval resamples the same questions jointly across both seeds and does not treat the two seeds as doubled sample size. All3pp/CI/sign components are exposed, with no new automated H0-H3 acceptance rule.

H1 numeric components use all8 settings, Spearman tied ranks, and negativeNLL so larger capability has the same direction as pass@1/pass@8. Constant predictors return null. The baseline termination note is mandatory, including the degenerate LlamaBase conversation baseline. All five contrasts remain visible even where Delta-data is small.

Please review before its first real-data run. The mean interval is supplementary; use the original registered criterion for any headline interpretation. No model call or rescoring occurs in this analysis code. Test command: `PYTHONPATH=. .local/p012_20261111/venv/bin/python -m unittest tests.test_p012_registered -v`.
