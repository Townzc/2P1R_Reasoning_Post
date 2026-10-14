# Claude audit 20261013am — five T8 outcomes @ 57a61a53 / 9a34c532: **PASS (all five)**

The five requests reviewed here are `p008-t8-outcome-{d1_b8_p0_breadth, d1_b8_p4_breadth, d1_b8_p4_depth}_t8-r1` @ 57a61a53 and `{d1_b8_p0_depth, d2_b8_p4_breadth}_t8-r1` @ 9a34c532.

## Method
- **Device copies.** The `original_evidence.tar.gz` on the device has the same git blob id as at 9a34c532 for all 5 runs. I extracted each archive into an isolated directory, after checking that there were no absolute paths and no `..` members, and copied in the packet's `gsm8k_test1319.jsonl`.
- **G3.** I used the same `g3_endpoint.py` as before: my own byte-level BPE decode, my own line-scan boundary and minimal-prefix stop logic, and my own marked-answer parser.
- **Lineage and dose.** I ran `t8_lineage.py` on git objects only. It extracts the tar from the commit itself.

## Results

| run | frozen primary | acc. | caps | event mismatches | parser disagreements | entry→terminal s |
|---|---|---|---|---|---|---|
| `d1_b8_p0_breadth_t8` | **967** | 73.31% | 39 | 0 | 0 | 6,301 |
| `d1_b8_p0_depth_t8` | **965** | 73.16% | 50 | 0 | 0 | 7,119 |
| `d1_b8_p4_breadth_t8` | **945** | 71.65% | 56 | 0 | 1 (mine wrong: `\boxed{L - 8}`) | 5,934 |
| `d1_b8_p4_depth_t8` | **939** | 71.19% | 47 | 0 | 0 | 5,777 |
| `d2_b8_p4_breadth_t8` | **935** | 70.89% | 45 | 0 | 0 | 5,666 |

**G3 (all 5).**
- 1,319 rows across 83 files, in eval-set order.
- Every prompt decodes to the frozen template.
- Generated-token totals and `padded_tokens` match exactly.
- `summary.question_correct` agrees row by row.
- Every non-cap row ends with native EOS.

The single disagreement is another false positive from my own parser: `\boxed{L - 8}` is an answer containing a variable. The frozen parser correctly rejects it, and this is the same lesson as in 20261013ag.

**Lineage and dose (all 5 pass every item).**
- The tar members equal `ORIGINAL_EVIDENCE_MANIFEST` and form a sha-exact subset of `artifact_manifest`.
- **Source and spec.** `SOURCE_BINDING` equals the 35-source cap bundle I reviewed at 4fef52a3, under spec 4ca2c55d.
- **Config.** It equals the original spec config, with `max_seconds` 9,560.
- **Ledger chain.** `config_sha256`, `source_sha256`, `intent_sha256`, `claim_sha256` and `evidence_sha256` all chain correctly.
  - Terminal status is `completed`, with an actual cost of 1,253¢.
  - The claim deadline is exactly claimed + 9,630.
  - The claim plan is the original plan.
- **Supplement.** It binds this run's claim digest and the global amendment record, which in turn binds the cap spec: 5¢.
- **LR, schedule and identity.** `recipe.lrs` equals `LR_VECTORS["2048"]` and the schedule equals the frozen T8 plan. Every one of the 2,048 updates has the plan's indices and LR, and cumulative targets reach **4,194,296**, equal to the plan's `supervised_targets`. There are 128 training blocks.
- **Checkpoints.** Both `checkpoint_1024` and `checkpoint_2048` manifests are present. The oracle's 1,024-step forensic targets equal my cumulative count at step 1,024, and that checkpoint is marked `used_for_selection=false`.
- **Result.** 12.58 reserved, invoice null.
- **Collection.** The route is a named-wave single read-only scan, the callback route needs no recovery, and there are 0 model calls and 0 remote writes. The provider is stopped with 0 containers.
- **State.** The state SHAs are recorded checksums. I did not inspect the binaries.

## Timing observation
The actual T8 times, entry→terminal, were 5,666–7,119 s, which is **inside the original 9,560 s cap** and well under 9,600. In hindsight the original N2 failure (forecast 9,551 s, 21 s over its line) came from the conservative max-component proxy. It does not change the recorded deviation. The write-up should still state that the original gate failed and that the cap was raised before any outcome was known.

## Scope
3 T8 cells are still pending: `d2_b8_p0_breadth`, `d2_b8_p0_depth` and `d2_b8_p4_depth`. No contrast is computed here.
