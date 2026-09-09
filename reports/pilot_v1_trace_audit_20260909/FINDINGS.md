# Interpretation of the stored seed17 trace audit

The strict complete-trace diagnostic preserves the matched-development ordering:
Paths 21/64, GCM 14/64, Repeat 13/64, Surface 8/64. It does not establish a robust
benefit: this is a post-hoc diagnostic on one seed and 64 selected development
problems. Under sampled generation the two decisive arms are close, with 59/256
Paths and 57/256 GCM outputs fully verified. These 256 outputs come from only 64
problems and must not be treated as independent experimental units.

The broader-development result remains weak. Each of Paths, GCM and Repeat has
only one fully verified trace out of 64; Surface has none. Paths has four correct
final expressions on this split, but three of those outputs contain false local
equalities. A claim about broadly improved reasoning is therefore unsupported.

Final-expression accuracy and arithmetic trace validity are different endpoints.
For example, Paths emits the correct final expression
`((3 * 16) - (22 - 4))` for target 30, while writing `3 * 16 = 58` and then
`58 - 18 = 30`. Both equalities are false. The independently recomputed final
expression is still correct, so its official score is retained. This output is
identified by problem `6715f2011f92bf41cd18` in
`runs/pilot_v1_paths_seed17_r1/final_dev_greedy.jsonl`.

The strict connection test is intentionally incomplete. For Surface problem
`09be4e5ec5a0117f233a`, the equations use `1 * 33`, but the final answer uses
`33 / 1`. The arithmetic and input consumption are valid and both routes lead to
the same answer. The checker labels their connection **unverifiable** because
the final ordered expression tree differs; it does not call this a mathematical
contradiction. The same issue occurs for one other correct Surface matched-dev
output. Report both the strict count and this limitation rather than presenting
8/64 as a complete measure of Surface's mathematically valid reasoning.

The next protocol should retain its frozen final-expression primary endpoint and
specify trace validity as a separate diagnostic before additional outputs are
observed. The audit should not be used to select a favorable dose, seed, or
checkpoint retrospectively. Wider data coverage and paired replication are still
needed; the present audit cannot establish cognitive strategy diversity.

The final audit also preserves definite contradictions when part of the trace
cannot be parsed. Paths broader-dev problem `9df0464dddda257309be` contains
unsupported `-033` literals, but its final expression independently evaluates to
6 and misses the target. It is therefore **inconsistent**, rather than merely
unverifiable. This correction changes one nonverified classification; every
complete-verified count and every official score above remains unchanged.
An additional counterexample test confirms that a legal equation chain reaching
a different value from its final Answer is inconsistent. Same-value expressions
with different trees still remain unverifiable under the strict connection rule.

Verification: 21 focused tests passed, including false equations with correct
answers, numeric-resource reuse, duplicate/equal-valued inputs, exact fractions,
negative intermediates, division by zero, code-injection syntax, unsupported
frames, definite answer contradictions despite unknown or size-limited traces,
different-value derivation/answer contradictions, and disconnected but equivalent
final expressions. All 4224 frozen
training/development reference traces passed. A fresh regeneration produced
byte-identical audits for all 1600 saved predictions; input/code hashes matched
and existing-output overwrite was rejected. `correction_verification.json`
records the changed classification and unchanged verified counts. Full-suite
verification is recorded separately by the integration owner. No GPU or holdout
evaluation occurred.
