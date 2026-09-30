# First attempt: scoring timeout, not a scientific result

The published d33cbbfa source completed five W_prefix optimizer updates and saved
96 TRAIN outputs. The sixth batch stopped on an extra-suite timeout for one
Mbpp/239 candidate. There were 90 completed dual verdicts, one fail/timeout and
five samples left unscored. All 96 raw outputs and 102 signed records were checked.
No update has uncertain commit status; no heldout model generation or final
checkpoint export occurred. W/C/R comparisons remain unavailable.

The evaluator used fast_check=False, which continues after a known failed test.
The timed-out extra suite recorded 30 failed tests out of104; base recorded three
failures. The saved candidate materializes a Cartesian product of sequences.
Static source inspection establishes the unnecessary continuation; it does not
identify every inner failure as timeout versus allocation/candidate exception.
The existing EvalPlus inner-FAIL attribution limitation remains.

170 compact evidence files were independently copied and verified. The792.8MB
reference cache was rehashed and retained remotely. Provider OFF was verified by
06:01:20UTC; the temporary timer was cleared. A conservative860-second powered
window gives a CNY1.9063 compute proxy, excluding storage, not an invoice.

The owner correctly objected to shutting down after a recoverable scoring fault.
The next operational attempt repairs the scorer and completes the same scientific
comparisons, with all failed-attempt dose/cost preserved. See the repair amendment;
this record and its timeout are not relabelled after post-run rescoring.
