# A800 engineering continuation — 2026-09-05 UTC

The intended Qwen2.5-1.5B base model now trains with the unchanged FP32-parameter, BF16-autocast, standard AdamW recipe and passes the 32-example software gate. There is still no positive development generalization result and no scientific treatment comparison.

## Environment and provenance

A800-SXM4-80GB; driver 580.126.09; Python 3.12.3; PyTorch 2.8.0+cu128; Transformers 4.56.2. Main model/tokenizer revision: `8faed761d45a263340a0528343f099c05c9a4323`. All nine snapshot files match the expected digests pinned from the official Hugging Face API; a mirror supplied bytes. A slow direct PyPI installation was stopped, then the same pinned packages were installed using an alternate package index. `pip check` and all 40 tests passed.

Both GPU runs used published commit `58e44b3e801472fd2f31e6ef7d488c03405b2e3d`. The existing 737-second ledger was carried to this server, not reset.

## Measured GPU runs

| Run | Updates | Batch / microbatch | Supervised tokens/s | Peak allocated MiB | Peak reserved MiB | Charged seconds |
|---|---:|---|---:|---:|---:|---:|
| `profile_main_a800_20260905_r1` | 110 | 1 / 1 | 280.60 | 25396.92 | 27886 | 32 |
| `overfit_main_a800_20260905_r1` | 500 | 4 / 2 | 642.51 | 26837.74 | 28996 | 404 |

Throughput uses 100 updates after 10 warmups. Different batch sizes prevent interpreting the rows as a GPU-to-GPU speed comparison. The CPU candidate audit started after the measured throughput window; subsequent wall time may include CPU contention. Memory peaks include later training/evaluation. The profile completed the optimizer-state allocation that failed on the 4090.

The overfit run used constant LR 5e-5, seed 17, 32 fixed training examples and development-only evaluation. It processed 127448 supervised response tokens over 2000 presentations. Training correctness fluctuated before update 500 met the prespecified >=95% correctness and <0.2 NLL gate. No final test was evaluated.

## Before and after the engineering overfit

| Measure | Pinned base | After 500 updates |
|---|---:|---:|
| Train greedy correct | 0/32 | 32/32 |
| Train reference NLL | 0.649409 | 0.000263 |
| Dev greedy correct | 0/16 | 0/16 |
| Dev sampled correct, four per problem | 0/64 | 0/64 |
| Dev greedy parse failure | 81.25% | 6.25% |
| Dev greedy truncation at 192 generated tokens | 100% | 0% |
| Dev reference NLL | 0.630177 | 0.741163 |

All 32 final training outputs exactly reproduce the reference trace. Formatting and termination improved, but held-out correctness did not and development NLL increased. This memorization check is not evidence that path diversity improves reasoning. The base score is specific to this strict serialization and decoding cap; heavy truncation limits claims about its underlying arithmetic ability.

Raw predictions, every update, interim evaluation, data hashes and settings remain in the run directories. `main_a800_output_integrity.json` recomputes raw scores and checks budget, throughput and committed configuration consistency.

## CPU exact-matching feasibility

The committed search examined 1024 unique number groups from 1..40, each with one seeded eligible target in 10..100. It found 64 disjoint blocks: 256 candidate problems and 1024 verified reference paths. In each block four problems support the same four complete canonical structures at equal supervised response length, 66 or 68 tokens including EOS.

One proposed cycle gives every arm 256 updates, 1024 presentations and exactly **68608 supervised tokens**. Token totals match per update across Repeat, Surface, Within-Paths and GCM. A Latin-square schedule gives Within-Paths and single-path repeated GCM equal structural histograms at every update (TV = 0), while each GCM problem keeps one fixed path.

This is candidate feasibility, not a frozen benchmark. Only 25% of candidates are selected; selected-vs-candidate target-distribution TV is 0.25098. Search considers the first 12 sorted full structures per length. Surface variants only replace Step with Stage, Part or Line, a weak rendering control. Selection restrictions and rendering scope need review. Group-disjoint development/holdout construction remains to be frozen before augmentation and scientific training. No model outcomes entered the candidate search.

See `runs/exact_matching_candidates_20260905/`, `exact_matching_candidate_integrity.json` and `../docs/PILOT_PROPOSAL.md`.

## Runtime and artifacts

A800 added 436 charged process-seconds. Shared total: **1173/7200 seconds (19.55 minutes)**; remaining: **6027 seconds (100.45 minutes)**. A800 hourly price was not provided, so the old 4090 price is not applied. Instance idle billing is separate.

The checkpoint contains weights and tokenizer, with 12 files verified on the server. See `ARTIFACTS.md` for local backup status. It omits optimizer/RNG/sampler state and cannot provide exact optimizer resume. GPU processes were absent after completion.
