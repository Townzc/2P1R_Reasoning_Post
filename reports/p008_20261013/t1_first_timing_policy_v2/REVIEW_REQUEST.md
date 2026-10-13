# REVIEW REQUEST: C1/C2 corrected outcome-blind timing policy

Source review7265c558 @485e7410: PASS-WITH-NOTES with C1/C2 required before use. This v2 records both corrections; no student/base call, actual joint plans, timing sample, or numerical N2 admission exists.

## C1: review-scoped calibration roster
At the joint-plan admission, before any T1 dispatch, freeze every planned T1 slot belonging to each draw that has actual G1 acceptance, plus base. Include the exact source/spec/common-plan hash, accepted-draw report hashes, and all T1/T8 IDs. An admitted T1 failure or slow host cannot be dropped. A later draw requires a separately frozen monotonic roster extension before that draw's first T1, includes all previously admitted T1, and must join the componentwise maxima before any T8 of that draw. No endpoint scores select membership. Missing/failed samples keep dependent T8 pending.

**Scope correction to the review:** C1 does not by itself make an incomplete D2 pool admissible or remove the existing all-pool/joint-plan requirement. Both complete local pool oracles and the joint complete-answer plan remain necessary. D1 may overlap D2's external G1 review once those common prerequisites exist. If D2 cannot complete, this review alone does not authorize a one-draw student study. Prepared extractor expects an actual immutable roster; roster producer/runtime admission remains NOTRUN and must bind those real prerequisites.

## C2: token and per-update compute
`u_i=sum(optimizer_seconds)/256`; use `compute_j=max(P_j*c_max, 2048*u_max)`. This retains fixed update cost when T8 rows are shorter and token scaling when they are longer. All original F/m/K, exact255-gap alignment, 20% margin, 9530 criterion,9560 hard cap remain. Two new tests cover each branch;10/10 CPU checks pass. Scientific runtime27 and livepool23 bytes unchanged.

The base's observed walltime is an empirical proxy, not a guaranteed upper bound for a trained model on another host. All historical timing maxima remain estimates. The estimator always returns N2_closed=false/runtime_admission=false; actual input-bound numerical external review is still required.

## Current actual state
D1 original terminal completed12:20:18UTC, providerSTOPPED05:20:23PDT/zero ownedcontainers observed12:21:34. Read-only collector is in progress; full G1 raw-token and wallet oracle has not yet run. D2 still originaljob at the last12:21 observation; no new dispatch or deadline extension. The conditional D2 repair remains blueprint only until full parent reconciliation.

Please review C1/C2 implementation and stated scope. No silence-as-approval. Keep the v1 packet immutable.
