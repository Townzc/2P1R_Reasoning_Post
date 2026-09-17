# Frozen scoring boundary: one official MATH500 answer normalizes to empty

Before model evaluation, the full official MATH500 reference audit found one affected row: zero-based index 97 (`math500-test-0097`). Its published raw answer is `\text{east}`. The pinned Qwen parser lists `east` among removable units, so its `math-oai` ground-truth normalization returns an empty string. All other 499 MATH500 references and all 1,319 GSM8K references normalize to nonempty strings under the same wrapper.

The 500-question benchmark is preserved in full. The release stores the raw answer, empty normalized answer, `normalization_empty=true`, and `reference_status=unresolved_reference`. The original vendor bytes and unit-removal rules remain unchanged. No question is deleted, replaced, or used to alter training selection.

Every completion on this row is retained, but its score is `status=unresolved`, `reason=unresolved_reference`, `correct=null`. This is a known reference-contract boundary, not a model error or an infrastructure exception. It does not authorize more model samples. Until an explicitly documented common scoring amendment resolves the reference, a complete resolved 500-question score is unavailable: report unresolved coverage and do not silently reduce the denominator to 499 or count the row as wrong.

For a nonempty reference, an empty or unparsed completion receives zero as required by the owner protocol. The wrapper prevents upstream's early exact-string branch from ever making empty prediction equal empty reference count as correct. Parse failures and known unresolved references are separate states.

This boundary does not prevent an engineering preflight or CPU data freezing; a frozen data manifest must state that full benchmark scoring readiness is blocked by the known reference. It prevents calling partial resolved MATH500 results a complete pilot result.

Source: [Qwen parser](https://github.com/QwenLM/Qwen2.5-Math/blob/a45202bd16f1ec06f433442dc1152d0074773465/evaluation/parser.py) and [grader](https://github.com/QwenLM/Qwen2.5-Math/blob/a45202bd16f1ec06f433442dc1152d0074773465/evaluation/grader.py), commit `a45202bd16f1ec06f433442dc1152d0074773465`. The upstream source and licenses remain byte-preserved under `vendor/qwen_math`.
