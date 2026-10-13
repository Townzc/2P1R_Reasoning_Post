# REVIEW REQUEST: exact outcome-blind T1-first timing rule

Claude4d4fc7b7 acceptedc206f0dc block-journal code. Its scope remains code-only; actual pool G1/joint plans are absent, no student/base job has started, and N2 remainsOPEN. This packet predeclares the suggested timing-only dispatch change: all10 already-plannedT1 students (8main +2 retained bridges) andbase first, thenT8 only if the common timing criterion and actual numeric review pass. No new model job, shortened dose, new budget, livepool modification, or score gate.

## Precise criterion and conservative corrections
`F_i = terminal.finished_epoch - intent.started_epoch - span(first,last completed-update mtime) + 2s`; this includes actual final packaging/commit time, unlike result.wall_seconds, which is captured beforepack. Take max(F_i, actualbasewall).

`c_i = sum(all256 optimizerseconds)/sum(all256 processedtokens)`.

The first→last completion span contains255intervals: subtract **optimizersteps2..256**, not all256. `m_i=max((span-sum(seconds[1:])+2)/255, (blockboundaryseconds+localstepwriteseconds)/256)`. Take the componentwise maximum across all10 predeclaredT1 slots; missing/failed runs cannot be dropped or replaced with favorablehosts. Negative/inconsistent inputs failclosed.

There is no existing pure checkpoint timer. Use `first_eval_intent_mtime - last_update_completion_mtime +2s` as an explicitly named checkpoint-and-setup **proxy**; K=2×max(proxy). It contains final snapshot/save/readback/commit and other setup; F already includes it, so this double-counts deliberately. Do not label it isolatedmeasured checkpointtime.

For every8× plan, use its exact processedtoken sum and2048updates. `T8_hat = Fmax + P*cmax +2048*mmax +K`; require `1.2*max(T8_hat)<=9530` with original9560hard cap. 2048 ratherthan2047 retains another conservative update. Report all component/max/perrun estimates, metadataresolution, and input/checkpointsource hashes. Token scaling remains a proxy for length-dependent compute, and past host latency is not a future guarantee. Numeric PASS still needs actual input/source-bound externalreview, even if the engineering inequalitypasses.

## Code/collection safeguards
EightCPUtests pass: exact255-gap alignment, slow-host max, missingroster, outcomesfieldrejection, changedcaps/steps, nonfinite/inconsistenttime, extraT8. estimate() always returnsN2_closed=false/runtime_admission=false. Preparedextractor writesT8_TIMING_PROPOSAL.json only, neverT8_TIMING_ACCEPTED.json. Allmetadata collection is read-only after real completedreceipts/STOPPED0. Originalmtime metadata is saved separately because compacttar intentionally normalizes timestamps; it cannot be reconstructed from export mtimes.

Please confirm this concrete rule and the T1/base-first dispatchorder, and identify any correction before use. The subsequentactual numericalpacket is separate. Existingmodel/cap/input/G1/no-replay requirements still apply; if the inequalityfails, retainT8pending, no automaticcapincrease or fallbackdose.

## Review accounting corrections
The acceptedblock implementation has256 **training** remotechecks forT8 plus83unchangedformal-evaluation checks =339 total. Original2131 comprised2048training+83eval; do not compare256against2131 as ifboth includeevaluation. This does notchange codePASS orscience.

D2 remains originalactiveworker; predeclaredrepair still blueprint-only withstrict no-unknown-regeneration and no additionalreservation. Newprogress11:52:33 isselectedsavedreceipt evidence, notfullG1: D1 highBzero-price wallets~82.9/81.7%, D2~42.8/42.0%. The currentparent deadlines remain12:23/12:24UTC; no extension.
