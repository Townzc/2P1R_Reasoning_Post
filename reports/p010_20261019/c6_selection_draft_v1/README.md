# C6 label-free selection draft — no model execution

This is independent preparation for the already approved P010 E2 experiment. It adds no separate code-only approval gate. A complete C6 runtime, frozen inputs, normalization and budget are still required before execution. No generated development or test response has been read or scored here.

The fixed plan uses 30 development questions, width20, depth2, 20 openings plus no cue, 16 continuations per question/candidate, and max1024 continuation tokens. The paper used16384; this is an explicit planned difference. This code accepts no gold or correctness field. Missing answers form one category; the >10 percentage-point exclusion uses the exact48/480 count boundary. The no-cue candidate is eligible as specified in P010; entropy ties prefer no cue, then frozen beam rank.

Reference: [paper Appendix A](https://arxiv.org/html/2610.06851#A1), [author code](https://github.com/sophicle/cues/tree/cd9caabe748307df0565502f630e3a834a9f998d). The inspected source commit is recorded in REFERENCE_BINDING. Author CLI defaults use100 proposal problems, width40, top-first12, top-second4 and a50% presence filter; these differ from the approved plan and are not silently imported. Our draft measures mean joint probability on every one of the30 dev prompts for every surviving prefix, keeps a20-wide beam at each depth, pools the one- and two-token beams, then takes the top20. It does not substitute mean log probability or zero-impute absent per-question beams. The final full C6 review must assess this explicit implementation against P010; it is not a claim of identical paper execution.

Five distinct new offline tests passed once: mass versus log-mass ordering, two-depth openings, exact missing-answer boundary/no-cue ties, complete-roster entropy selection, rejection of partial/duplicate/gold-bearing inputs and invalid probability distributions. No old tests, tokenizer, symbolic scorer, model or output are rerun. Normalization, full source/input binding, inference and once-only durable collection remain unexecuted engineering work.

These are execution records, not prose for the course report.
