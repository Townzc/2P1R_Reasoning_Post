# Prepared S1 local scoring process limit

This new supervisor prepares the missing outer process limit around the existing
durable S1 endpoint scorer. The parent starts exactly one child in a new POSIX
process group, counts input writes and child startup within its supplied local
window, and kills only that owned group on timeout or failure. A bounded cleanup
wait of at most five seconds can follow the scoring cutoff; it is not additional
scoring time. Parent record writing after the child lifetime is explicitly
excluded from the reported child-lifetime measurement. Abrupt host or parent
loss remains an unknown partial operation; this helper cannot promise cleanup
after such a loss and never authorizes replay.

The original scorer, pair timeout, parser, cache and decision rules are unchanged.
An existing control directory blocks every second attempt, including after
spawn failure, timeout or partial evidence. Completed payload and source/input
hashes must agree. This is process supervision only: full runtime verification,
sample adjudication and scientific G1 admission remain false. The future complete
driver still needs exact NC A4, S1 source/input/runtime and local numerical
admission. Its two-file parent/child check is not a full transitive source audit.
There is no new separate code-only blocking request or actual S1 execution.

Eight new checks passed once in 1.117 seconds using synthetic records and tiny
local processes. They covered successful closure and replay refusal; an actual
timeout signaling the owned child/grandchild group; nonzero and missing-proof
exits; altered payload hashes; failed spawn; invalid inputs/window; and changed
child source binding. No symbolic comparison, model, prior raw decode, state
load, prior test suite or old scientific tool was rerun. These tests are not
evidence of S1 scoring speed or a successful scientific endpoint.
