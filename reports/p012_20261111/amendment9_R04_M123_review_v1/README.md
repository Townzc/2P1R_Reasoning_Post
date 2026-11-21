# A9 R04 and M01–M03: independent audit requested

Four new endpoints,8,957 original greedy outputs: R04 fullMATH5,000 and M01–M03 each fullGSM8K1,319. All scientific sources remain unchanged; existing accepted bootstrap adapter and core were used once for the new complete R04 unit.

| Endpoint | Correct / questions | Accuracy | Truncated | Loops |
|---|---:|---:|---:|---:|
| R04 | 3090/5000 | 61.80% | 470 | 335 |
| M01 | 394/1319 | 29.871114% | 8 | 7 |
| M02 | 657/1319 | 49.810462% | 2 | 1 |
| M03 | 926/1319 | 70.204701% | 8 | 6 |

INPUT_MANIFEST binds 88 public files/archive members, including all raw outputs, labels, training state, complete order, checkpoint/sampler identities, Num examples and global_step where applicable. Normal-termination metrics are in RESULTS.json. The R04 formal INPUT_MANIFEST binds both seed17 and29 and the previously accepted firstR result; earlier outputs remain immutable.

R04 seed29 minus17 is +0.48pp, paired95%CI[−0.6805,+1.68]. Both seeds miss the frozen A8 prediction on the negative side; average residual−5.38pp. The four single-epoch settings now all have same-sign residuals across seeds, but the requirement that at leastthree misses repeat does not hold. R06 interaction remains null; M statistical units wait for their complete eight-endpoint sets.

Please independently rescore these four new endpoints and reproduce the R04 point estimates, interval and bootstrap draw hash. Prior audit7a135e42 and accepted seed17 endpoints need no repeat scoring. One provenance detail: the original analysis template captured R04 train_loss at step121 while training was active. Its bytes are an exact prefix of the completed512-step log; the new input manifest records both hashes and this proof, while preserving the original template. The completed log is also bound by the sampling request and public archive.

R06 was cancelled in the remote service and is separately documented in amendment9_R06_cancellation_v1; it has no successful endpoint and is not included. A10 S1 generation continues independently. All new scientific results are exploratory outside H0–H3.
