# Prepared S1 scoring journal verification

The new read-only helper verifies a complete 500-row stored scoring journal:
exact original row/source/window binding, five committed chunks, every pair
observation and its attempt order, cached-pair history, all final Boolean rows,
file hashes and fixed audit samples. Unknown, partial or failed evidence is
rejected. No model state is loaded, raw tokens decoded, boxes re-extracted or
symbolic comparisons repeated. The original boxed denominator is copied from
the preserved audit-sample record; it is not independently re-extracted here.

This is a payload verifier, not a full runtime oracle or scientific admission.
The future outer oracle still must bind the exact source/runtime/input reviews,
actual NC paired A4, original completed model proof and an admitted local scoring
window with an enforced hard process cap. Independent sample adjudication and
actual outcome review remain separate. No accepted NC49, NC42, P1 or Stage0
source was modified. There is no new independent blocking code-only request;
these exact bytes must be included in the future complete S1 runtime review.

Eight new synthetic stored-proof checks passed once in 0.103 seconds. They cover
read-only successful verification without granting admission; changed chunk
hashes; missing/duplicate symbolic-attempt order; a resealed but false cache
history; failed/unknown artifacts; substituted source/window; fabricated sample
adjudication; and standard-library-only imports. All evidence was synthetic,
and no prior test suite, raw output or scorer was rerun.
