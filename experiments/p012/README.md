# P012 execution code

The active specification is P012 v1 plus amendment 1. See the [current packet](../../reports/p012_20261111/README.md) and [review request](../../reports/p012_20261111/C2_C4_CODE_REVIEW_REQUEST.md). This is research code, not course prose.

Training uses the pinned LLaMA-Factory release. Evaluation uses a separate vLLM environment. The two `.in` files contain direct pins; their `.lock` files resolve the Linux/Python 3.11 dependency graphs. GPU installation, imports and timing still need validation.

After the first-use review, generation takes a JSON config and JSONL inputs with stable `id` and `problem` fields. Scoring additionally requires `gold`. Optional `messages` holds a frozen few-shot conversation; optional `prompt` is a fully rendered completion prompt and requires `apply_chat_template=false`. Main-grid templates must be exported from the fixed training template and supplied through `chat_template_file`.

```sh
export P012_CODE_COMMIT="<full reviewed source commit>"
python -m experiments.p012.evaluation --config CONFIG.json --inputs INPUTS.jsonl --output NEW_GENERATION_DIR
python -m experiments.p012.scoring --inputs INPUTS.jsonl --generation NEW_GENERATION_DIR --output NEW_SCORE_DIR
```

Generation writes a manifest, raw token IDs, text and stop metadata, then a completion record with the raw SHA256. Scoring rejects missing, duplicate, unexpected or altered responses. Sampled accuracy is the mean over the registered draws; question IDs remain available for paired bootstrap.

Li's released MATH exact-match functions are copied unchanged with their MIT license. Its judge receives only extracted nonmatches; missing-format answers remain wrong. The scorer writes `judge_inputs.jsonl`. Generate those with the pinned `candidate_configs/li_judge.json`, then score the original generation into another new directory using `--judge JUDGE_GENERATION_DIR`. Exact and judged metrics remain separate. Released GSM8K uses the published flexible-extract metric. OMI-2 requires the last balanced `\boxed{}` and uses math-verify or numeric equality.

No module starts a model when imported. No training loop, automatic paid launch, per-cell review mechanism or budget timer is implemented here.
