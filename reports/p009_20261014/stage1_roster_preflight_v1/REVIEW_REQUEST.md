# Exact Stage1 selection code review

Request p009-stage1-roster-selection-code-r1.
Scope p009-stage1-roster-selection-code.
Review the exact source/data map in SOURCE_BINDING, including unchanged schedule,
serialization and frozen LR dependencies. Verify earliest-original duplicate
choice precedes label filtering, attempt01-only eligibility, native-EOS complete
answers, unsupported-gold accounting, no rescoring, fixed nested seed orders,
NC roster, and strict count/dose checks. The eight synthetic checks are not an
actual input audit. Review the new deterministic hash permutation as an explicit
pre-student implementation detail; no new data, model, seed or treatment arm.

Return fixed target, scope, decision and exact source_files. A code PASS alone
must not admit a student: full original corpus and P1/G0/source/input/numeric
runtime evidence must still be independently bound before any paid training.
This request does not block the three active Stage0 generators or local P1.
