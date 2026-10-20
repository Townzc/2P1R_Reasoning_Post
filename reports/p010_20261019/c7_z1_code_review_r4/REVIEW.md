# C7 code cross-review r4: remaining last-line negation finding closed

Reviewed only `audit/claude/20261020e/z1_secondary_v3_1.py` at c542484d39888cdc74db7b68e70ae5afab163f6c, SHA e771b5fa173b0bf579dbff4deec1741879bfabe4f975956c502656f233a4cf86. The source diff adds the same conservative negation guard to the GSM fallback last line as the explicit-marker branch. This resolves the concrete P2 example from C7-r3, “The result is not 4.” No other source lines changed from the reviewed v3.

Six new synthetic cases were evaluated once through only the necessary function ASTs. Denied numeric candidates using not/nor/incorrect were rejected; a positive “notable” sentence and an affirmative last line following a negated intermediate line remained accepted; a no-number line remained missing. All passed. Dataset-loading top-level code was not executed. No actual Z1 rows, gold labels, annotation, result summaries or interpretive report were read. Earlier tests and scientific scores were not rerun.

No additional actionable finding was identified in this two-line change. This closes the previously reported extraction case, not a certification of all possible natural-language ambiguity, actual Z1 numbers or a causal format-only interpretation. Primary scores remain frozen. Claude owns the actual Z1 labeling, independent judgments and scientific conclusions. This cross-review adds no gate on unrelated P010 model execution.

These are code-review records, not course-report prose.
