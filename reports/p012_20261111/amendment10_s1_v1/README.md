# A10 S1 generation

Authority f42dcd15; owner confirmed an independent USD200 stage cap. S1 cap USD75. Source and all input identities are frozen before the first call; source passages, full prompts and prompt token sequences remain private. Generation is exempt from prereview under A10 section1.4; selected data and the training-path diff require review before training.

Counts:12567 source rows →12106 after removing461 overlapping rows →11169 unique passages →10913 after removing256 pilot rows still present. Order is sorted record identity then Random(20261121).shuffle. Batches600, eight independently seeded samples, max4096, unchanged pilot renderer/prompt/scorer. Only first four whitespace-distinct correct solutions qualify. Stop after a completed batch reaches4300 qualified rows. Any selected overlength training sample stops this path for reporting. No silent truncation or replacement.

The local finite controller needs this Mac awake and online. It starts no training, baselines or other A10 jobs and never automatically replays a failed batch. Budget reservations remain recorded on failure. Accounts, billing and power settings are unchanged. Model output and safe identities are public; original LogiQA text is private. Results are exploratory outside H0–H3.
