# Saved-evidence reproduction

Run commands from the repository root (`repository/` after extracting the handoff). Use an isolated Python environment with the recorded dependencies, CPU torch, NumPy, Transformers and PEFT; plotting additionally requires Matplotlib. Supply the separately retained pinned tokenizer snapshot through `TOKENIZER_DIR`. No model weights are needed for core token/scorer replay.

Frozen execution source: `2bb39fbdf5bf83bb471e436804e1b968262ff530`.
Frozen release manifest SHA256: `ecd1e12dc792f36c9969354fde9764fce8811b2f39e39e0878238d6e2f7b5a5c`.
Model/tokenizer: Qwen2.5-1.5B Base, revision `8faed761d45a263340a0528343f099c05c9a4323`.
`execution_source/` preserves the executed Python bytes separately from result artifacts.

## Core replay

The output directory must not exist. This replays saved token, stopping, scorer, request/RNG bindings, and diagnostic arithmetic; it does not run the scientific model or recompute logits.

```sh
TOKENIZER_DIR="<PINNED_TOKENIZER_SNAPSHOT>"
PYTHONPATH=. python -m experiments.post_e039_decision_supervision.analyze \
  --run-dir runs/post_e039_decision_supervision_v1 \
  --release experiments/post_e039_decision_supervision/release_v1 \
  --output reports/replay_decision_core \
  --tokenizer-dir "$TOKENIZER_DIR"
```

The core `manifest.json` binds nine core outputs. Supplements below are outside that immutable manifest and are included in `DELIVERY_MANIFEST.json`. A replay manifest reflects its actual input inventory: compact raw omits the explicitly listed private binary and PEFT metadata files, while the original analysis used the complete private export. Compare verified scientific results and coverage without claiming these two inventory maps are identical.

## Derived supplements

These packaged scripts use existing reports and make no new model calls or bootstrap draws. Use fresh output paths; they refuse overwrites.

```sh
PYTHONPATH=. python reports/post_e039_decision_supervision/analysis_code/secondary_strata.py \
  --reports reports/post_e039_decision_supervision \
  --release experiments/post_e039_decision_supervision/release_v1 \
  --output reports/replay_decision_supplements

PYTHONPATH=. python reports/post_e039_decision_supervision/analysis_code/plot_results.py \
  --reports reports/post_e039_decision_supervision \
  --output reports/replay_decision_supplements/DECISION_SUPERVISION_RESULTS.png
```

`COST_SHUTDOWN.json` and `COST_AND_CLOSEOUT.json` are byte-identical aliases. They derive provider-confirmed closeout and cost proxies from preserved evidence; the proxy is not an invoice. The disk observation timestamp is sourced from the private provider evidence key `final_disk_measured_at_utc`. The derived phase ledger preserves the earlier raw rental snapshot and explicitly distinguishes its final whole-window proxy fields. `FORWARD_METADATA_ERRATUM.json` preserves and explains the original launch labels: the complete result is 704 candidate contexts, 2,816 scores, 6,848 reference records and 7,552 sequence equivalents; 16,384 is the independent cap.

Operator-only closeout regeneration requires the separately retained helper and factual private evidence; these are not credentials or evidence invented by the public replay:

```sh
PYTHONPATH=. python "<OPERATOR_HELPERS>/closeout_evidence.py" \
  --backup "<PRIVATE_VERIFIED_EXPORT_DIRECTORY>" \
  --provider "<PRIVATE_PROVIDER_EVIDENCE_JSON>" \
  --reports "<FRESH_CLOSEOUT_OUTPUT_DIRECTORY>"
```

## Validation and private recovery boundary

The frozen preflight passed **38 CPU tests with zero skips**, locally and on the execution host, before scientific model calls. Tests cover real serialization/causal masks, F and EOS weights, ordinary-CE parity, weighted recovery, budget/resume faults, passive PEFT greedy/logit observation, paired statistics and partial-output handling. Tiny random CPU fixtures are not pretrained scientific inference. To repeat the suite with the pinned tokenizer:

```sh
DECISION_TEST_TOKENIZER="$TOKENIZER_DIR" PYTHONPATH=. python -m unittest \
  tests.test_decision_spans tests.test_decision_supervision_data \
  tests.test_decision_supervision_runtime tests.test_decision_supervision_diagnostics \
  tests.test_decision_supervision_queue tests.test_post_e039_analysis
```

No additional model calls were made by final analysis, independent saved-record audits, supplementary statistics or packaging. `SAFE_DIAGNOSTIC_AUDIT.json` records the separate read-only audit, including lossless FP32 vector reconstruction; it does not claim CUDA replay or gradient recomputation.

Full weights and optimizer/RNG binaries remain in `<PRIVATE_VERIFIED_EXPORT_DIRECTORY>/raw/`, including `decision_e040_r1` through `decision_e043_r1`, scientific `checkpoint_64`/`checkpoint_128` adapters, and the files referenced by `recovery/latest.json`. Exact private filenames, sizes and hashes are retained in the full export inventory and backup-scope report. The compact handoff is sufficient for saved-output analysis, not for starting training. Restoring or launching further model work requires the separately preserved parent/base assets and a new authorized research plan.

The package includes the frozen `WEIGHTED_LOSS_CONTRACT.json`, `CONTINUATION_MANIFEST.json`, `release_v1/CONTINUATION_MANIFEST.json`, and `release_v1/DECISION_SPAN_AUDIT.jsonl` (1,024 original H records), with the F/evaluation span audits and all 21 manifest-bound release members. No reserved question bodies are required for replay. Do not rewrite frozen source, release rows, raw tensors, scoring or the core manifest to regenerate supplements.
