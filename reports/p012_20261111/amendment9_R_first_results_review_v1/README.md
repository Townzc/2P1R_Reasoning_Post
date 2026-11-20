# A9 R01, R02, R03, R05 — endpoint result audit requested

4 new endpoints, 5,276 original full-GSM8K greedy outputs. Please independently verify original labels and frozen A9 predictions. Training, generation and scoring sources are unchanged from b95c631e (manifest includes exact hashes). All train/eval runs completed once.

| Cell | Seed | Training examples | Updates | Accuracy | Truncated | Loops | Normal termination correct/n |
|---|---:|---:|---:|---:|---:|---:|---:|
| R01 | 29 | 4096 | 512 | 27.672479% | 15 | 12 | 365/1304 |
| R02 | 29 | 4096 | 512 | 51.933283% | 17 | 14 | 685/1302 |
| R03 | 29 | 4096 | 512 | 68.764215% | 19 | 16 | 907/1300 |
| R05 | 29 | 8192 | 2048 | 36.012130% | 5 | 4 | 475/1314 |

INPUT_MANIFEST.json binds 71 source, request, checkpoint, training, generation, raw-output, label, termination and prescore files. Training manifest, model revision, seed, frozen data, Num examples and global_step agree for every endpoint. Timestamped predictions were published before scoring. All original archives remain in the endpoint directories listed in RESULTS.json. Checkpoints retained pending audit.

Point residuals use the authoritative A9 rounded predictions and strict outside-band test. The accepted staged adapter has completed the first formal analysis for these four units; see ../amendment9_analysis_runs_v1/r_first/README.md and ANALYSIS_BINDINGS.json. Please independently recompute all point estimates, paired intervals and bootstrap draw hashes. R-1/R-2 source diff and all eight input endpoints are bound. Aggregate verdicts remain null until their required units are available. No refit has run. Earlier A8 seed17 labels are unchanged and need no repeat audit. All new endpoints exploratory, outside H0–H3. Existing authorized queues continue.
