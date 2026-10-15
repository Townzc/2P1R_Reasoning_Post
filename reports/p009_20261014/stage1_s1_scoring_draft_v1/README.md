# Prepared S1 durable endpoint scoring helper

This new helper connects the prepared500-row S1 payload to the unchanged frozen
MATH scalar and two-process pool. It journals each returned symbolic pair before
later work, including timeout/tool failures, and reuses that exact pair within
the new endpoint session. Five create-only chunks preserve original row order,
full Boolean outcomes, source identities, pair intentions, completed proofs and
timings. An existing root, even a failed or partial one, blocks the whole helper.
Known returned pairs remain saved; unconfirmed work cannot be retried here.

There is no CLI, actual S1 numerical cap, full runtime admission or actual
math-verify/model invocation in this preparation. The outer future driver must
first check the exact runtime/input/scorer/P1A2/NC A4 and complete-payload binding,
review a finite numerical local window, and enforce its hard process timer.
The helper's per-pair/chunk deadline checks do not replace that outer hard timer;
a worker startup or original in-flight pair can cross the soft check before
control returns.129600 is only the maximum accepted argument, not a proposed
S1 duration, expected runtime or permission to run. No old P1 first100 review is
passed off as a review of a different roster. Original P1 jobs are not reopened.

Outputs explicitly remain payload_only, full_runtime_lineage_admission_checked
false and scientific_G1_admitted false. Fixed audit samples retain null independent
adjudications; no string/symbolic disagreement or fallback changes the frozen
labels. The future complete result still needs its actual external review.
There is no new independent code-only blocking request: the exact future full
S1 runtime packet must include these bytes, complete transitive imports, real
NC A4/timing, actual S1 input review and unchanged scientific/budget gates.

Seven new synthetic checks passed once in0.056s: full500 completeness/order,
unique-pair reuse, whole-job reentry rejection, crash preservation, cached outer
timeout/fallback without label repair, malformed lineage/window refusal, and the
actual persistence hook saving its returned pair before deadline failure. All
symbolic verdicts were synthetic; no math-verify call or old test suite ran.
The mock pool is imported from an existing test module without running its tests.
The accepted NC42 and P1 scalar/pool/journal source files remain unchanged.
