# One path-level CR: OT3 and paired-AM input construction

**PREPARED, production NOT RUN.** This packet requests the new construction
code path's line-by-line CR; actual input A1 will use its completed outputs.
It does not request per-cell reviews or admit training. Fixed scientific plan:
`e0dee182972f9910b707fac68800dcb5a3aff2d3`, SHA256
`20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22`.

The [source lock](SOURCE_LOCK.json) pins all 120 OT3 parquet objects, the two AM
math JSONL objects, model/tokenizer revisions, and the exact 600 benchmark
problems. The D partner is the authors' `a-m-team/AM-Qwen3-Distilled` repository,
whose card identifies Qwen3-235B-A22B and links the AM-Thinking counterpart.
Only math files are downloaded for D. Raw transfer uses the stock Hub client;
it does not execute this new construction path.

Both pinned Qwen2.5 Instruct tokenizer sets match the already cached tokenizer
Git blobs. No tokenizer or old model weights were downloaded again. The
MATH500 materialization is reused unchanged from P009. New AIME24/25 and AMC23
sources contain 30/30/40 rows. AIME24's `solution` field is its boxed gold answer;
AMC23's question field is `question`.

## Operational details requiring explicit CR disposition

1. **Length:** follow §1.1's stronger total serialized sequence limit 16,384 for
   parent filtering and training encoding. §1.3's wording “16,384 + prompt” is
   not used to admit a longer training sequence. Future generation still has
   the separate 16,384-new-token limit and needs its own context configuration.
2. **Native chat supervision:** native Qwen rendering, including its default
   system and exact whitespace, is retained. The prefix, literal assistant
   response plus `<|im_end|>`, and final ignored newline are tokenized separately.
   Concatenated tokens must decode to the exact native rendered text. Both
   length filtering and training use this identical policy. Only the assistant
   span and its final `<|im_end|>` are supervised. This can differ from
   whole-string BPE at the supervision boundary; it is not claimed bit-identical
   to whole-string tokenization. A real cached-tokenizer synthetic fixture
   exposed a merged prompt/assistant newline in the initial whole-string
   implementation; original source and failure are retained privately.
3. **13-grams:** NFKC, strip outer whitespace, split on whitespace, retain case;
   compare contiguous 13-word tuples. Exact normalized problem equality is also
   excluded, including prompts shorter than 13 words. No semantic matching or
   outcome-based filtering is used. Parent identity itself retains internal
   whitespace exactly, as the plan states.
4. **Source order:** OT3 source filenames sort lexically, then original row
   index. All matching normalized parents across sources are combined before
   cardinality checks. Parent ordering uses `Random(20261020)`; response ordering
   uses the literal hex-string `sha256(parent_key+'p011')[:16]` as the seed.
5. **D duplicates:** choose one original row per teacher before length or
   completeness filtering, using the literal first16 hex characters of
   `sha256(parent_key+':p011-D:'+teacher+':20261021')`. Both chosen answers must
   pass. Common parents sort before `Random(20261021).shuffle`. No fallback to
   another answer after a chosen row fails; no cherry-picking.
6. **Exact dose:** A7's once-pass supervised count defines B; U=ceil(B/64000).
   D uses max of its two once-pass counts. A checkpointed exact subset-sum
   implementation preserves q/q+1 whole-answer exposures. Length buckets have
   width512 with seeded ordering. A once-pass sum above B, nonrepresentable
   residual, or insufficient presentations is recorded as infeasible; B is
   never raised, no answer dropped, and no sequence truncated to force a pass.
   Such a real conflict requires disposition, not a fabricated runnable plan.

OT3 is not correctness-verified. AM author verification metadata is retained;
missing or <0.9 scores are counted without silently adding a new selection rule.
Actual A1 must examine those counts and the common support size. Neither path
imports a scorer or model runtime. Partial construction directories are retained
and block a second invocation. No production data has been filtered or selected.

## Verification and limits

Eleven initial offline rule/scheduler tests passed; one real-tokenizer synthetic
boundary test failed as described above. After the boundary repair, only that
failed test was run again and passed. Four new IO/schema/create-only fixtures
passed. Thus 16 distinct checks are covered, with the initial failure disclosed;
this is not a claim that the original whole run passed. The successful earlier
checks and all old P010 checks were not rerun. No GPU or real corpus construction
was tested. Exact source/test hashes and raw log hashes are in the binding packet.

The constructor stops at the P011 cutoff, preserves raw row locations and parent
dispositions, and creates one completed manifest only after all intended local
work. Real runtime and end-to-end result validation remain future work.

See [future commands](FUTURE_COMMANDS.md). They are NOT RUN and require the real
fixed report, exact source/lock hashes, plan binding and explicit acceptance of
the operational details above. No fake ACCEPTED record has been created.
