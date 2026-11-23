# Existing-output diagnostics, 2026-11-22

[TABLE.md](TABLE.md) contains the requested 113 training cells: main grid72, A8 26, A9 R/M15. Columns include length-cap fraction, mean and median output tokens, uncapped correct/n and accuracy, and final optimizer-step training loss. All299,968 existing greedy responses are joined to their immutable labels.

INPUT_MANIFEST.json binds each row to public raw output, labels, generation configuration, training identity and complete per-step loss logs. RESULTS.json retains full numeric precision and denominators. CHECKS.json records complete joins, expected final steps, model/seed bindings and agreement with all previously published termination counts. The seven cells above20% cap also quote their existing first-boxed diagnostics, bound in FIRST_BOXED_APPENDIX.json.

Reproduction is CPU-only: build_table.py, then append_existing_first_boxed.py in a fresh output directory. These extractors do not call models, scoring functions, bootstrap, training or account APIs. No original labels, losses or results change. The last-step loss is distinct from the trainer whole-run mean, which is retained only as a reference field in JSON. Numeric table only; the author writes the paper text.
