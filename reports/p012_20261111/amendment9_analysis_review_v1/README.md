# A9 R/M analysis adapter — prereview required

Authority ecda0914 section5. Training, greedy evaluation and scoring reuse unchanged reviewed sources. A9 requires new seed29-minus-seed17 and PK2/K4 comparisons, which the old main-grid/A7 CLI does not accept. This candidate adds only an evidence adapter and frozen decisions. It imports bootstrap_delta/two_seed_contrast unchanged from analysis/p012_registered.py (SHA b6973ad6…). No new fitting, rescoring or model calls.

Please review a9_analysis.py, the frozen44-entry CATALOG, INPUT_TEMPLATE and14passing synthetic tests. The three required rejection cases (cell swap, base/Instruct swap, seed swap) pass, along with dataset/revision/update/sample-count failures and strict band-boundary checks. ACCEPTED_REVIEW=None blocks every real statistical run. Upon acceptance, fill the review commit, freeze complete input hashes, then run once and send complete numerical output and inputs for independent recomputation.

All44 endpoint identities bind training run/model/revision/seed/cell/data/dose; Modal adds checkpoint-manifest verification, Num examples and trainer global_step; Tinker adds saved sampler/state, complete row order and optimizer log links. Raw/label/termination/input hashes must agree with the full frozen GSM8K1319 or MATH5000 input. Missing or swapped endpoints fail before statistics. Late inputs currently have null hashes and cannot run.

R residuals use the authoritative rounded A8 predictions in A9_PREDICTIONS.json; same-sign follows the frozen seed17 sign and outside-band is strict. Mean residuals and per-question seed29−17 intervals use full-precision accuracy. M calls the accepted paired two-seed bootstrap unchanged and reports all3noticeable criteria. No significance claim is made from seed dispersion. M1 is not an equivalence test. Every result is exploratory outsideH0–H3.

Pending result packages remain independently auditable while this analysis waits. Existing R/M/R04 and T0 queues continue; this review does not gate training.
