# One shared pre-C8 review: remaining G0 addendum

This supplements ../pre_c8_review_v1; it is the same pending review, not a per-cell review round. Review the fixed standard-base prompt/scoring wrapper and consolidated Li MATH judge path together with F4/F5 and the Modal launchers. Actual production use of the new base and combined-judge paths awaits Claude's review under P012 section 12. Existing approved Li Instruct/checkpoint evaluation continues.

Base protocols were frozen prospectively in ../g0_remaining_protocols_v1/BASE_PROTOCOL_FREEZE.json. harness_baselines.py uses the actual pinned lm-evaluation-harness task, sampler, filters and scorer; only dataset transport is replaced by hash-checked C1 rows. MATH uses all5,000 test rows and reports its fixed MATH-500 subset; GSM8K uses all1,319. Both families use exactly the same few-shot strings, with one explicit BOS for Llama. These are G0 standard baselines, separate from the amended main-grid Delta_SFT baseline.

The standard Minerva scorer requires ANTLR4.11; math-verify requires4.13.2. modal_baselines.py isolates Minerva CPU work from the unchanged GPU evaluation/scoring environment. Synthetic integration validation checks the actual reference functions, GSM strict/flexible filters, no heldout-gold dependence, and real tokenizer behavior. The interval example's stock SymPy behavior is recorded, not patched. Full benchmark prompt preparation and model calls through this new path have not run.

modal_g0.py additionally supports locally authorized file-scoped downloads for Llama. The HF token stays on the local machine; remote files must match C1 SHA256 and the receipt excludes temporary URLs. All three cloud caches passed. Local protocol regression tests:31passed (2new cases,29existing). Actual CPU validation passed at source6e168e14: fixed harness1863f15a,ANTLR4.11,SymPy1.14,TF4.56.2; four real-tokenizer cases, three correct numeric references, one incorrect-answer reference, and both GSM filters. The stock interval reference scores0; its metric is unchanged. Evidence: CPU_RUNTIME_VALIDATION.json.

Built with Llama.
