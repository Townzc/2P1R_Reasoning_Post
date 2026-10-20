# C6 probability adapter, answer keys and original dev inputs

Prepared only. This package introduces no separate code-only approval gate. The complete C6 runtime, process isolation, once-only dispatch, resource limits, measured-cost forecast and exact A2 are still required. No actual search, development generation or test evaluation has run.

The thirty original development IDs and their order are copied without reselection. Only `problem_id` and tokenized `input_ids` enter the worker file. The original dev source also contains solutions; those fields are excluded. Original S1 zero-shot serialization and the pinned base tokenizer are used, without truncation. BASIS records exact token lengths and ID disjointness from S1 n3200, every E1d candidate and MATH-500. This is an ID check, not a claim that all questions are semantically distinct.

The new proposal adapter obtains full-vocabulary probabilities from the final prompt position, with explicit left-padding masks and position IDs. Every prefix intent and complete FP32 probability matrix is saved once; a partial prefix cannot be replayed. It follows the cited implementation's HF probability stage. Later continuation generation uses the frozen vLLM configuration only after the proposal process exits. The outer runtime and that exit check are not implemented in this draft. Existing width20/depth2 selection code remains unchanged.

The answer-key adapter uses the author's last2000 completion characters, first80 extracted-answer characters and six-decimal numeric grouping. These keys group answers for entropy; they do not assert mathematical correctness or replace primary scoring. Missing extraction/empty parse is one missing category. Parser exceptions remain technical failures rather than being silently mapped to missing. The future bounded local parser process, timeout handling and exact source binding remain to be integrated.

Seven new checks passed once in1.626 seconds, including a real tiny randomly initialized Qwen CPU forward, padding equivalence, full-matrix preservation, replay rejection, gold-field rejection and exception preservation. This is neither a full-model nor GPU throughput measurement. No previous test, score, output or checkpoint was rerun.

Reference source is pinned in REFERENCE_BINDING. The earlier [selection draft](../c6_selection_draft_v1/README.md) records the explicit differences from the paper and author CLI. The approved continuation cap is1024 rather than the paper's16384. Original results and primary parsers remain unchanged.

These files are execution and audit records, not report or presentation prose.
