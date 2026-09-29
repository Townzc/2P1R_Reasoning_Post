# Paper references — literature values, not pilot results

The following are published **MATH500 percentages for Qwen2.5-Math-1.5B Base and its fine-tuned variants**, transcribed from each paper's main Table 1. Keep the two paper settings separate. No row is a measurement from this repository's 4,096-question pilot.

| Source setting | Method | Published MATH500 (%) |
|---|---|---:|
| DFT paper v3, average@16 | Base | 31.66 |
| DFT paper v3, average@16 | SFT | 43.76 |
| DFT paper v3, average@16 | DFT | 64.89 |
| TrimSFT paper v1, average@8 | Base | 31.45 |
| TrimSFT paper v1, average@8 | SFT | 40.02 |
| TrimSFT paper v1, average@8 | DFT | 63.17 |
| TrimSFT paper v1, average@8 | TrimSFT | 66.95 |

The DFT source uses 100,000 NuminaMath-CoT examples, batch 256, maximum training input 2,048, temperature 1 and maximum generation 4,096. Its main statistic averages 16 generations. [DFT v3, §4.1 and Table 1](https://arxiv.org/html/2508.05629v3).

The TrimSFT source samples 20,000 NuminaMath-CoT problems and uses one epoch, batch 24, `(m, tau)=(1.5, 0.8)`, temperature 1, top-p 1 and maximum generation 2,048. Its main statistic is average@8; pass@8 and majority-vote best-of-8 are separate metrics. [TrimSFT v1, §4.1, Table 1 and Appendix A](https://arxiv.org/html/2609.09707v1).

Our pilot fixes 4,096 unique training questions, batch 32, 128 updates, one training seed, 0-shot `qwen-boxed`, and maximum generation 2,048. Its MATH500 primary metric is average@8, with pass@8 secondary. Its own jointly paired Base/SFT/DFT/TrimSFT/QDW results belong in a separate results table with exact coverage and question-bootstrap intervals.

Differences in training dose, sampled rows, prompt/source revisions, decoding, and implementation prevent direct cross-table rankings or claims to reproduce a paper's score. A higher or lower pilot value would not by itself establish a methodological improvement or failed reproduction. CFT has not been run; see [its separate contract](CFT_REPRO_CONTRACT.md).

Source retrieval: 2026-09-17. Frozen HTML SHA256: DFT v3 `3505f7cea58d762fba58727c4d9cbabdb0216d5bca00a1908c410bb4ca02ae79`; TrimSFT v1 `0650e450f38f4a5e500f75cccab9851f4fdb97c52d445c89cc7810cf6bbf6b67`. Formula provenance is distinct from reproducing a complete training pipeline: DFT author commit `11e395d49ed1b9da7dc5d957224d942d90af5bf6` was accessible; the TrimSFT author-linked repository was not accessible at retrieval, so this pilot implements its published formula.
