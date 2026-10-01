# October 1 control completion: scoring admission still fails

No new training, generation, evaluation or checkpoint was admitted. The requested
R_future/C_future completion remains missing. This is an operational failure,
not a negative result for the retention hypothesis.

The owner started the existing single A800 and authorized the same bounded
384-update/9,216-output completion, with a three-hour ceiling. All setup and
CPU diagnostics counted toward that powered window. Old evidence was preserved.

## Saved-program diagnostic

One exact saved R_future sample (Mbpp/599, batch25, sample8) had historically
passed34 tests before the outer watchdog stopped it. We did not change the
candidate, inputs, oracle, memory limit, or per-test limits. Fixed paired runs
produced the following; these are CPU re-executions of saved text, not model outputs.

| Repeat | Original scorer | Observed tests | Guarded diagnosis | Observed tests |
|---|---|---:|---|---:|
| 1 | fail (20.04s) | 14 | pass (79.31s) | 88 |
| 2 | timeout (62.19s) | 34 | pass (78.66s) | 88 |
| 3 | timeout (62.19s) | 34 | pass (79.09s) | 88 |

A separate fresh-process admission gate then failed at test10 (index9), input
`n=100000001`: the candidate hit its frozen5.012398719787598s per-test limit.
Only the first9 tests passed, conflicting with the historical34-test prefix.
The raw evaluator returned FAIL; admission correctly retained UNKNOWN and did
not create a training reward from this replay.

We investigated one operational adjustment: pinning the isolated scorer to
CPU0, selected in advance without a performance search. All116 Linux unit tests
passed, but this gate reproduced the same test10 timeout and prefix conflict.
A fixed CPU is not a dedicated CPU or a guarantee of clock stability. CPU
migration is therefore not an established explanation, and the precise reason
for the timing difference remains unresolved. The three passing diagnostics
cannot be selected while ignoring the two failed admission gates. Neither
full96-output regression nor32 known-W sentinels was reached after this conflict.
No timing relaxation, alternative reward, further CPU search, or model retry ran.

The initial staging attempt also preserved one failed unit-test fixture: it
mutated a model fixture before that fixture was hashed, and repeated writes
relied on filesystem timestamp granularity. The corrected test mutates once
while the model fixture itself is read; it does not change experiment scoring.

## Scientific status and closeout

All prior386 committed updates,6,224 training outputs and3,072 evaluations are
unchanged, including the failed C100/R25/initial5-update costs. Existing union
sampled pass@1 values remain R46.48%, W_prefix49.22%, W_future49.02%.
The matched-future W/R, W/C and C/R comparisons are all unavailable. No
retention-versus-restart or cross-seed conclusion is supported.

All60 compact artifacts from this session were retrieved and hash-verified.
All37 files across the three preserved W_prefix/W_future/R25 checkpoint sets
were independently rehashed before normal provider shutdown. No GPU or owned
Q2 worker remained at collection. The exact single-A800 instance was verified
OFF; no Trash-clearing helper, deletion, rental, new seed or new arm was used.
The compute window stayed below its3h/CNY23.94 ceiling; storage is separate.

This attempt is closed. Further work requires a redesigned and explicitly
reviewed measurement plan; it must not silently reuse the old W outcomes under
a different test timeout policy. First discuss whether the scientific question
warrants that effort relative to the nearby literature and course scope.

Structured evidence: [RESULTS.json](RESULTS.json). Earlier science remains in
[the September30 pilot](../q2_screen_20260930/RESULTS.md).
