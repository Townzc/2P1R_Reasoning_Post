# Owner-adopted changes before any production data construction

The direct owner reply adopts R1/R3 and requires real re-review before execution.
The original plan file and old candidate packet are preserved unchanged. This is
an explicit amendment, not a claim that the original A7 dose was followed.

- R1: every A cell uses the maximum once-pass supervised-token sum across all eight
  original cells; U=ceil(B/64000). D already used its two-cell maximum. A7 need not
  be exactly one pass. Budgets, counts and arms do not increase. Exact remainders
  still fail visibly; no truncation/answer removal/automatic B adjustment.
- R2: each complete epoch is a separate permutation with literal seed
  `17:pass:<e>`; separately shuffled `17:extras` subset comes last. Global length
  buckets are removed; `length_bucket_width=null`. Same update partition logic.
- R3: sorted cardinality-16 OT3 candidates / common AM parents are shuffled with
  original parent seeds, then checked until4096 /1024 pass. No second shuffle.
  Prefix denominators and unexamined counts are explicit; no estimated full-pool
  eligible count. Wrong-cardinality OT3 counts still cover the full pool. D fixes
  each original duplicate choice before checking; it never swaps to a good row.
- AM human info.source set agreement is counted across the entire common pool
  using metadata only; original author verify-score exception counts remain.
- Entry checks free disk >=1.5 times pinned input bytes. Direct owner evidence and
  proposal SHA must match the real revised CR before any output directory exists.

Eight new synthetic checks passed once. Previous16 checks were not repeated.
The test uses fabricated fixtures only; it is not a production call or actual A1.
All120 OT3 parquet hashes verified once after original download55016 exited0.
Both AM raw mathematical datasets were already fully verified; no repeat download.
