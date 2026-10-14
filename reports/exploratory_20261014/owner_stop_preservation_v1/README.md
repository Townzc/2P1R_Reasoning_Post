# Exploratory experiments stopped and preserved

Recorded 2026-10-14T08:14:11.523297+00:00. Owner explicitly chose “停止并保全，准备修复送审”. The three original apps were stopped once at08:05:16–18UTC (01:05PDT); independent provider reads through08:05:47UTC confirmed all three STOPPED and zero containers. Each original terminal remains **failed** due to the requested interruption, with its original claim, callback error, failure manifest and costs retained. No model, training, evaluation, upload or scoring was repeated.

| Run | Saved raw outputs | Original acknowledged | Saved without final batch ack | Never attempted |
|---|---:|---:|---:|---:|
| base_4shot | 272 | 256 | 16 | 1047 |
| instruct_0shot | 144 | 128 | 16 | 1175 |
| wrong_teacher_t1 | 80 | 64 | 16 | 1239 |

The three attempted prefixes have no missing raw rows in the saved inventory. Each last16-output batch lacks its original completion acknowledgment. Those48 rows remain unacknowledged; this inventory did not independently decode/score any endpoint output. No full1319-question result or partial accuracy is reported, and no missing acknowledgment was fabricated. All three endpoints remain incomplete.

The wrong-teacher student completed **256 updates and524,287 targets**. Its original222,109,365-byte full checkpoint was copied, hash checked, loaded locally once, and matched to all256 exact frozen schedule/LR records and16 remote training-block acknowledgments. Adapter/optimizer tensors are finite, optimizer steps are256 and RNG fields are retained. State SHA256: `45d3871207d9a9b42c2dcc7f72ef71c289d943b3d9e4fedfafd016a8c502ef57`. This is state preservation, not a tested cross-host restore or permission to resume. The full binary stays private and on the original Volume; the public packet contains its original manifest and verification proof.

All690 committed original files (231,420,287bytes) were preserved once. Before/after stopped Volume listings match. The archive includes original raw/scored files, local journals, failure records and checkpoint manifest. It excludes the full `.pt` and the original intent embedding private gate metadata; their hashes remain in the full original manifests. `ledger.json` is the single original campaign snapshot. Public provider data is explicitly projected to omit actor identities; original private bytes remain preserved.

## Performance repair submitted for review

All three interruption tracebacks stop inside `len(tokenizer)` in the per-token reference-validation comprehension. This supports the repeated vocabulary lookup as a material overhead source. Original cloud batch intervals and the one local timing diagnostic remain evidence, not a calibrated future-host speed guarantee or proof that no other overhead exists.

The [unapplied cache proposal](https://github.com/Townzc/2P1R_Reasoning_Post/blob/1a3c910ecb438bd16f0cff860973168c98edc56d/reports/exploratory_20261014/vocab_cache_proposal_v1/REVIEW_REQUEST.md) moves the same vocabulary-size lookup outside the token comprehension. Its4 new edge fixtures and32 saved-event comparisons were already completed before stopping and were not repeated here. Original37 scientific source bytes remain unchanged. Exact proposal code review is requested through INDEX; this packet does not declare it PASS or admit an executable replacement/continuation.

Owner stop approval authorizes preservation and repair preparation only: **no retries, new scientific calls or extra budget**. Any possible future continuation must preserve these failed parents, every already-attempted ID and the completed student state; it is not authorized by this record. p007 remains paused and original P008 materials remain closed and immutable.

## Accounting

The08:08:43–44UTC delayed billing snapshot attributes $5.43330865 to these three original app IDs. It is not a final invoice, complete current cost or balance. The original$30 ceiling remains; no reservation is recycled and setup/download/storage/failure costs are retained. Conservative residual plus the full priorP008 reservation and full$30 envelope is$384.84256089 against the unchanged$450 project spending ceiling and$50 protection. See `BILLING.json` for exact scope and read times.
