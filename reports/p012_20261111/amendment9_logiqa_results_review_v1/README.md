# A9 LogiQA2.0 pilot — full independent audit requested

Three completed endpoints, 5,544 original outputs. New data/scorer path is explicitly exempt from prereview by Amendment 9 section 4; please independently rescore all 1,572 outputs per test model and all 2,400 training samples. No training or full-generation extension has started.

| Endpoint | Correct | Accuracy | Answer-only | Unfinished |
|---|---:|---:|---:|---:|
| 4B test | 1,141 / 1,572 | 72.582697% | 0% | 11.068702% |
| 9B test | 1,191 / 1,572 | 75.763359% | 0% | 9.987277% |

The 300 training rows yield correct-count distribution 0–8 of 35, 11, 9, 10, 8, 12, 11, 22, 182. Thus 235/300 (78.3333%) have at least 4 correct samples, projecting 9,844.15 of 12,567 source rows. All sampling seeds and sequence IDs are distinct; zero questions have eight identical outputs. Correct sampled solutions: median 762 tokens, mean 828.506, p95 1,433. 4B and 9B tokenizer assets are byte-identical, so these are also student-tokenizer counts.

Measured token-cost upper bound for the pilot is USD 4.931279, charging all prefill as uncached. Sample endpoint cost is USD 2.031754 for 300×8; projection to 12,567×8 is USD 85.110187. The existing 1.5 admission margin would give USD 127.665280 for that future batch. These are token/rate calculations, not a settled invoice. All three frozen pilot continuation conditions pass; extension still requires the owner's decision after this audit.

Overlap is reported without filtering: passage-only exact 228 test rows/320 train rows and 13-gram 311 test/459 train; passage-plus-question exact 217 test/225 train and 13-gram 544 test/1,598 train. Source IDs repeat, so immutable record identities use split plus source-line index. Sampling sorts numeric source IDs stably and retains all original rows.

INPUT_MANIFEST.json binds requests, safe input identities, source/template hashes, prescore records and output archives. Each endpoint archive contains complete raw model outputs, labels, request, usage, version, completion and prescore evidence. The source passages, questions/options, full prompts and reversible prompt token IDs remain private. Gold letters and prompt hashes are public as authorized. Original labels are unchanged. All results exploratory, outside H0–H3.

Please verify the frozen scoring (last boxed letter, normal termination required), full raw/label alignment, literal template use from the source hashes, student token lengths, overlap count method and all three continuation conditions. No bootstrap, refit or model training is performed by this packet.
