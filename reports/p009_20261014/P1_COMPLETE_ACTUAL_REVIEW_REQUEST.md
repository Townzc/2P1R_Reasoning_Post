# Actual complete P1 scoring, fixed independent adjudication and S1 G0

Request p009-math-p1-complete-scoring-A2-r1.
Scope p009-math-p1-complete-scoring-and-independent-adjudication-A2.
Prepared 2026-10-15T02:33:53.352989+00:00; use the exact fixed target in INDEX.

[Complete immutable scoring evidence](p1_complete_scoring_v1/REVIEW_REQUEST.md),
[summary](p1_complete_scoring_v1/SUMMARY.json),
[original-file and projected-intent accounting](p1_complete_scoring_v1/COLLECTION.json),
[source binding](p1_complete_scoring_v1/SOURCE_BINDING.json).
The accepted readonly publisher was executed once (CLI43474 exit0). No raw
re-decoding, symbolic rerun, original first100 retry, model or new training.
Original timing approval bx and publisher approval by are copied in the packet.

All10489 scorable rows across105 committed chunks and4048 distinct cached pairs
are present. Of8993 procurement generations,4 structurally unsupported gold rows
are excluded explicitly;8989 are scored. All1500 endpoint golds are supported.
Seven original context exclusions were never generated. All original failures
remain, including one saved procurement tool_error and all parse/cap failures;
there are0 outer timeouts, not a claim that every symbolic attempt succeeded.
Technical_unknown0 concerns committed evidence, not perfect answer correctness.

Independently adjudicate every fixed sample, with row-specific explicit findings:
50 procurement disagreements,34 teacher endpoint,16 Qwen zero-shot and17 Qwen
four-shot (117 total). Fewer than50 uses every available disagreement. No pool
exceeds the registered2% fallback fraction or0.5% unique-pair outer-timeout
flag. Also inspect the saved one tool_error and4 unsupported gold exclusions
without silently rescoring, replacing a label or claiming unsupported gold zero.
Original adjudication fields deliberately remain null until actual independent
review. If uncertain, record uncertainty and keep the gate unresolved.

The original complete question/solution/reference files are in
[the frozen Stage0 input archive](https://github.com/Townzc/2P1R_Reasoning_Post/blob/e6350f0bf1f987d7c8a5acd76bbf924b6ed33f4e/reports/p009_20261014/design_and_inputs_v1/stage0_inputs.tar.gz):
math_train7500.jsonl SHA73d37f56faabe743a203a966c84250d31d7d7bd53c97d4543963b14e9907e99a,
math500.jsonl SHA132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d.
Match original_gold row digests and problem IDs. Use the full original question,
reference and generated segment, not an answer-string-only plausibility check.
The already-audited raw generation target is192f9156c9235d1bcc3433ac5eade608ef5bbec9.
The original source12/window/proposal bindings are unchanged.

Saved frozen Boolean summaries (not yet admitted outcomes): teacher359/500,
Qwen0-shot136/500, Qwen4-shot147/500; caps36/68/39. Qwen4-shot has the previously
reviewed386/500 new-problem boundaries; report them with its descriptive score.
Only the zero-shot Qwen endpoint defines S1 G0. Independently recompute the
registered teacher gap>=20pp, student caps<=15%, technicalunknown0 and verify
all adjudication/exclusion requirements before explicitly deciding S1 G0.
Procurement6905 correct rows include multiple attempts; do not call this6905
eligible questions or assume3200 eligibility without the separate frozen roster.
S2's original cap failure remains. NC G0 already passed bw. HF638/969 are historical
P008 references and cannot enter any P009 effect or gate.

Return the fixed target, decision, source12 map, summary/collection/manifest file
hashes, explicit independent adjudication evidence, exclusion/fallback/timeout
dispositions, and separate eligibility-use and S1 G0 decisions. A raw-integrity
PASS alone must not be represented as all scientific gates passed. No student
runtime, input or numerical admission is implied by this outcome review.
