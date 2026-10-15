# Stage1 roster selection — code preparation only

No new student has been called and no actual Stage1 dataset has been selected.
This pure core consumes existing independent raw/P1 fields without decoding,
parsing or scoring again. Future full input binding must prove complete original
corpora, final P1 adjudication, actual G0, source hashes and resource shutdown;
this module alone cannot supply those admissions.

For MATH, choose the earliest original row for each normalized question before
reading correctness. Only that row's attempt01 may qualify, with native EOS and
an existing complete, parseable, correct P1 label. Later attempts and duplicate
rows cannot rescue it. Unsupported gold stays excluded, never scored zero. The
original answer text and generation/P1 row digests are retained.

The implementation freezes a version-independent permutation before new student
outcomes: sort SHA256("p009-stage1-question-order-v1:SEED:PROBLEM_ID"), breaking a
hash tie by full problem ID. The same seed/question gives the same key for NC
and S2; seed17 and29 differ. Seed17 uses100/400/1600/3200, seed29 uses400/3200,
and NC uses only400/3200 at seed17. Every size is a prefix of one full inventory
order. Source-provided input order does not change that order. This specifies a
previously unimplemented permutation detail and requires exact code review.

Only complete encoded rows passing the existing EOS/masking/context checks may
enter. Fewer than3200 distinct eligible questions or an exact selected whole
answer target sum above2097148 blocks the release; no smaller n, q0, shorter
answer substitution or dose increase. The original exact whole-answer schedule
and frozen1024 LR bytes remain unchanged. Actual schedule feasibility still
requires the existing training-plan check on every selected release.

Eight new synthetic scientific-rule and permutation checks passed once. These
are not actual MATH labels, source verification, G0, student input admission or
new generation. Existing scoring and the active34-source runtime did not change.
