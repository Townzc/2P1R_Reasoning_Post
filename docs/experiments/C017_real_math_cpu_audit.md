# C017 — original-problem and bounded released-solution CPU audit

2026-09-10 UTC. The owner requested the next CPU audit following P004: verify
problem splits, solution coverage and filtering losses, then propose training
scale. This authorizes this finite CPU data task; no GPU execution follows.

## Acceptance checks fixed before generated solutions

1. Reconstruct the 7,500/5,000 MATH inventory. Require exact multiset equality
   of problem, solution, subject and level between the author-linked merged
   mirror and EleutherAI's split-preserving conversion. Crosscheck original IDs
   from another mirror using whitespace-normalized question plus reference,
   requiring original split/subject agreement. Quarantine unresolved source IDs.
   Preserve original unknown difficulty labels and report altered mirror metadata.
   The raw author archive is inaccessible; do not infer original membership from
   current mirror split names. Preserve historical loader lineage.
2. Use official GSM8K 7,473 train / 1,319 test rows. GSM-Symbolic template
   original IDs must refer to official-test parents. Only identity metadata are
   audited; no final-test model evaluation, hyperparameter or solution selection.
3. Before solutions, group exact/near/number-template candidate questions using
   deterministic five-token-shingle Jaccard >=0.8. Retain one eligible training
   representative per component; exclude any component touching an official
   test. Conservative grouping can discard genuinely different questions, so
   report losses and do not call it semantic or pretraining decontamination.
4. GSM8K: 512 development parents, 1,024 audit parents, 1,024 disjoint fresh
   parents reserved. MATH: levels 1–3 without explicit diagram markup; 256 dev,
   512 audit, 512 fresh reserved, with proportional subject/level quotas. These
   pools precede output availability and preserve zero-success denominators.
5. Use pinned OpenMathInstruct-2 full-train shards 4, 7, 10, 16, selected by
   Random(20260910).sample(range(32), 4), in ascending order. Approximately
   0.95 GB of solution files, with a 1.1 GB total source cap; no full 14M-row bank.
   Only exact whitespace-normalized matches to eligible original audit parents
   can enter. Ignore augmented questions. Inspect the first 16 released
   candidates per drawn parent, regardless of successes; no adaptive extra shards.
6. Sequential first-rejection accounting: empty text; expected/reference answer
   disagreement or unresolved equivalence; missing final answer; final/reference
   disagreement or unresolved equivalence; normalized duplicate text;
   serialization failure; complete sequence >2,048 tokens. Scalar equality uses
   exact rationals; other answers require conservative normalized LaTeX equality.
   Unresolved equivalence is not a proven wrong answer. No eval, truncation,
   padding-to-match or silent rescue. Show 1,024/4,096 length sensitivities and
   >=.9 solution-text similarity as a secondary sensitivity, not a strategy label.
7. Tokenize exact existing `Problem: ...\nSolution:\n` serialization with the
   pinned Qwen2.5-1.5B base tokenizer. Check prompt boundary and EOS supervision.
   Report one-pass response/processed tokens for nested P/K possibilities, K=0,
   all subject/level denominators and target shortfalls. Select eight accepted
   parent-distinct responses per dataset for explicitly AI-assisted qualitative
   step review; no claim of exhaustive or human-gold reasoning verification.

## Interpretation and resource boundary

Source-discovery finding before generated outputs: the original-ID mirror has
7,499/5,001 claimed train/test entries, one duplicate file ID, whitespace changes
and several altered metadata fields. The initial all-fields/ID equality probe
failed as intended. The split-preserving and author-linked merged mirrors agree
on all 12,500 four-field records. The revised conservative rule above resolves
12,499 original file IDs and quarantines the remaining training row; it does not
repair its ID by guessing. This change precedes all parent draws and solution
retrieval. Original source bytes and the failed discovery log remain retained.

The first parent-only preparation (`real_math_c017_parents_r1`) exposed another
selection issue: balanced round-robin development/draw allocation exhausted the
rare geometry-level-1 stratum before the fresh draw. Retain that preparation as
superseded, not training input. Before any solution retrieval, switch to separate
seeded proportional largest-remainder quotas per partition, with at least one
parent per available stratum. The corrected freeze is `real_math_c017_parents_r2`.

This measures accessible released-slice coverage and our filtering yield. It
does not recover unpublished attempts, full-bank coverage, teacher production
cost, full proof correctness or distinct reasoning strategies. Fresh draw and
development solutions are not checked. Retrieval timing covers the documented
file transfers, not the preceding literature/discovery work or human labor.

Data scale may be proposed from this audit. A new real-data 32-example
overfit/profile must precede a priced training phase. Existing 1,229 remaining
GPU process-seconds are unchanged; no assumption that a complete grid fits.

## Commands and immutable outputs

Use the existing private CPU environment; add `pyarrow==23.0.1` for Parquet.
All source revisions and constants are in `configs/diagnostics/real_math_c017.json`.
Commands use new output directories; source files are cached outside Git.

```bash
python -m scripts.fetch_real_math_sources --cache .local/real_math_c017_sources
python -m unittest tests.test_real_math_audit tests.test_sft_data -v
python -m scripts.prepare_real_math_audit --cache .local/real_math_c017_sources \
  --out reports/real_math_c017_parents_r2 --private-out .local/real_math_c017_parents_r2
# Commit the frozen public parent manifest before the next two commands.
python -m scripts.fetch_real_math_sources --cache .local/real_math_c017_sources \
  --solutions --frozen-manifest reports/real_math_c017_parents_r2/problem_manifest.jsonl
python -m scripts.audit_real_math_solutions --cache .local/real_math_c017_sources \
  --parents .local/real_math_c017_parents_r2/problem_records.jsonl \
  --frozen reports/real_math_c017_parents_r2 --tokenizer-dir "$TOKENIZER_DIR" \
  --out reports/real_math_c017_solutions_r1 --private-out .local/real_math_c017_solutions_r1
```

Publish scripts, configuration, hashes and compact measurements. Keep third-party
problem/response texts in the ignored cache and retain attributable, pinned
retrieval URLs for reconstruction. Record failures without overwriting outputs.
