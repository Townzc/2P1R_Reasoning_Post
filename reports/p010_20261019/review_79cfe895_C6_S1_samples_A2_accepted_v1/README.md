# C6 search and original S1 sample-only A2 accepted

Claude's fixed 79cfe895 report was read in full. C6 search is PASS-WITH-NOTES; the two original S1 four-sample endpoints are PASS. Exact SPEC and source bytes were checked against the report-reviewed context 2a5955c0. This packet contains code/input/numeric acceptance, not actual search selection or new sample outcomes.

C6 retains the disclosed method differences: mean joint probability beam ranking over pooled depth-one/two candidates, a 1024 continuation cap, and the S1 zero-shot template. Its selection never uses gold or test correctness. Existing S1 inference restores original final adapters, requires original merged-byte equality, and adds only the four original sampling passes; old greedy scores remain unchanged.

The report's progress reminder describes its earlier context. Original K1/E1d calls have since started. Dispatch remains within the original four-slot bound. All five original K1/E1d receipts must be recorded before the later inference phase. C6 must be submitted before the S1 sample-only calls, because the frozen C6 admission enumerates original T receipts and cue receipts; the newer sample-only entry additionally enumerates sample-only receipts. No source is hot-edited to change this bookkeeping.

No model, scoring, bootstrap, or old test was executed by this acceptance operation. Z1 actual labels/results remain Claude-owned and unread by Codex.
