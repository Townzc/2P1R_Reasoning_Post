# New full-pool OT3 math census

Source is the original read-only43.1GB raw SQLite index of all120 pinned local parquet shards, with the original source-lock and ingestion receipts. It scans all850000 math rows; it does not repeat parquet download/ingestion or old training encodings. Full-pool answer-length tokenization is a newly authorized CPU analysis, once only.

A grouping remains NFKC(question).strip(). Raw exact and whitespace-removed casefold counts are separately reported. Eligibility uses original boxed-completeness, exact/13-gram contamination and native prompt+response+EOS+newline<=16384; completeness does not establish correctness. Report≥1 and≥16 eligible responses, and the original stricter exactly16/all16 eligible pool separately.

Length mean/median/p90 excludes EOS; population CV/max:min are per original A group. Zero-length exclusions are explicit. P8192/16384/32768 K1 totals use a new deterministic diagnostic prefix: sorted eligible parent keys shuffled20261020, original per-parent shuffled rows, first eligible response, one-pass supervised tokens including EOS. This is neither a retraining dataset nor a fixed training-token dose. Insufficient pools yield null totals, never zero. Benchmark exact/normalized overlap is reported separately from original13-gram exclusion.

No production run before this exact quick Claude CR. New tests are synthetic; all prior science stays DONE.
