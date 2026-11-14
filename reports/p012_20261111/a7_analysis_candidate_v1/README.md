# A7 two-seed analysis adapter: first-use review

Candidate `analysis/p012_a7.py` imports the existing, unchanged `p012_registered` paired-question bootstrap. It does not call models, rescore answers or change the main H0-H3 outputs. Real statistical execution is disabled until the owner supplies the accepted Claude review commit.

The fixed scope is 15 endpoints: own-teacher9B/4B short,long,concise at seeds17/29;9B-Base short,long,concise at seed17. Base uses9B training data. Cross-teacher4B-to9B arms are excluded. Each slot binds a public evidence archive, result snapshot, exact frozen training data and training-request hash. Internal checks tie model/revision, arm, actual training seed,128updates,rank32,learning rate,loss/row-order records,state/sampler identities,greedy protocol,5000test IDs,raw/label hashes and termination summaries. A7 predictions require22890560 and UTC; original A6 predictions remain18f64e2d.

All three comparisons are reported: long minus OMI short,long minus concise,concise minus OMI short. For9B/4B, output includes each seed, the two-seed mean with jointly resampled question IDs, and whether both signs agree. The core remains10000replicates,PCG64 seed20261111,NumPy2.5.4,linear percentiles. Base has one observed training seed and only one-seed intervals. Output lengths are computed on the original normal-termination subset for SC-3b. The adapter does not carry the main-grid3pp/noticeable hypothesis classification into A7.

Twelve synthetic contract checks pass, including swapped arms (all havecellL),base/Instruct swap,training-seed swap,cross-teacher data substitution,changed dose/revision/source,cross-wired state/sampler,non-greedy settings,legacy/current result schemas and a coupled-seed bootstrap oracle. The full numerical reader has not run on real results. The first true output and complete input manifest will be provided for independent numerical review.

Review requested under P012 section12: each new analysis path requires one review before first use. This gate affects only the new analysis adapter; all authorized training and evaluation queues continue.
