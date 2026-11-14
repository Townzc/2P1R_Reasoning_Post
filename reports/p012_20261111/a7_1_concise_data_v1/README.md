# A7-1 concise data: pre-training report

Both512-row datasets are frozen. All attempted generations, prompt tokens, eligibility records, literal template, first-eligible selections, fallbacks and pre-score UTC/hash records are preserved. Training has not started.

| Teacher | Concise SHA256 | Fallback rows | Attempts |
|---|---|---:|---:|
| Qwen/Qwen3.5-9B | 090ef4576c05498e2a35bfd7ccd2e621bbee418cba2156d55d06a074b60819f9 | 0 | 513 |
| Qwen/Qwen3.5-4B | d60568ff56b7a8d486b6a24da05453d2e2f22b1432037813064d9f244e5f8a22 | 0 | 513 |

| Student tokenizer | Mean supervised OMI | Mean supervised concise | Mean supervised long | Concise / OMI | Concise / long |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B | 295.600 | 278.822 | 748.764 | 0.9432 | 0.3724 |
| Qwen/Qwen3.5-4B | 299.164 | 249.689 | 675.656 | 0.8346 | 0.3696 |
| Qwen/Qwen3.5-9B-Base | 295.600 | 278.822 | 748.764 | 0.9432 | 0.3724 |

The frozen SC-3a data check is reported without adjusting prompts or filtering by response length. Full distributions and4608 actual row/mask checks are in DATA_REPORT.json and CPU_ROW_CHECKS.jsonl. Every training arm retains512rows,2epochs,128updates,batch8,rank32 and its original model learning rate. Seed17 arms precede seed29. All pending training requests remain unadmitted until this report is delivered.

Source provenance: the original construction requests retain preparation base67c155e5. Constructor and template were published at213ee3e5 before either model call; their exact hashes bind the original requests and data archives. This preserves the original request bytes while locating the new source unambiguously.

Posthoc full review passed at8a8fac5c: all1024rows and1026attempts checked.

4B M512 long.jsonl contains40 of512 rows with only a boxed answer and no reasoning;9B contains none. Interpret SC-1/SC-2 primarily using9B;4B is a repetition with this limitation. Frozen data,labels and predictions remain unchanged.
