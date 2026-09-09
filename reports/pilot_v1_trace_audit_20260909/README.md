# Pilot v1 post-hoc arithmetic trace audit

The official final-expression metrics are unchanged. This independent CPU
diagnostic checks stored generations against exact arithmetic and input-use
constraints, then requires a direct ordered-tree connection to the Answer.

| Evaluation | Arm | Generations | Final correct | All local equations consistent | Resource derivation verified | Complete trace verified | Final correct but trace inconsistent | Final correct but trace unverifiable |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| final_dev_greedy | repeat | 64 | 14 | 23 | 17 | 13 | 1 | 0 |
| final_dev_greedy | surface | 64 | 12 | 12 | 11 | 8 | 2 | 2 |
| final_dev_greedy | paths | 64 | 23 | 21 | 21 | 21 | 2 | 0 |
| final_dev_greedy | gcm | 64 | 18 | 15 | 15 | 14 | 4 | 0 |
| final_dev_broad_greedy | repeat | 64 | 2 | 14 | 6 | 1 | 1 | 0 |
| final_dev_broad_greedy | surface | 64 | 0 | 4 | 0 | 0 | 0 | 0 |
| final_dev_broad_greedy | paths | 64 | 4 | 3 | 1 | 1 | 3 | 0 |
| final_dev_broad_greedy | gcm | 64 | 1 | 2 | 1 | 1 | 0 | 0 |
| final_train_sample16_greedy | repeat | 16 | 12 | 12 | 12 | 12 | 0 | 0 |
| final_train_sample16_greedy | surface | 16 | 10 | 11 | 11 | 9 | 0 | 1 |
| final_train_sample16_greedy | paths | 16 | 9 | 11 | 9 | 9 | 0 | 0 |
| final_train_sample16_greedy | gcm | 16 | 14 | 14 | 14 | 14 | 0 | 0 |
| final_dev_sampled | repeat | 256 | 48 | 100 | 70 | 38 | 10 | 0 |
| final_dev_sampled | surface | 256 | 35 | 40 | 37 | 27 | 6 | 2 |
| final_dev_sampled | paths | 256 | 72 | 63 | 60 | 59 | 13 | 0 |
| final_dev_sampled | gcm | 256 | 70 | 59 | 59 | 57 | 13 | 0 |

All frozen training/development reference traces pass the complete checker
(4224 reference rows across six files). All 1600 re-parsed final-expression
scores agree with the saved official scores. No holdout file was opened.

Matched Paths/GCM pairs under the stricter complete-trace diagnostic:

```json
{
  "final_dev_greedy": {
    "both_verified": 8,
    "gcm_only_verified": 6,
    "neither_verified": 37,
    "paths_only_verified": 13
  },
  "final_dev_broad_greedy": {
    "gcm_only_verified": 1,
    "neither_verified": 62,
    "paths_only_verified": 1
  }
}
```

## Interpretation and limitations

- Post-hoc descriptive diagnostic after observing seed17; not a preregistered primary endpoint.
- The complete-trace checker supports only the four frozen pilot sentence frames and one binary operation on displayed integer/rational values per step.
- Unknown syntax is unverifiable, never counted as correct. Inconsistent means an explicit arithmetic/resource/answer contradiction was established.
- Full verification requires legal consumption of every input exactly once and an exact ordered-tree connection to the final Answer. AC-only or other equivalent forms are separately reported as unverifiable under this strict connection rule.
- Equal-valued inputs and intermediate results are handled by enumerating provenance alternatives. Verification proves a consistent interpretation exists, not that the model internally followed it.
- Locally true equations need not form a legal derivation or reach the target; final-expression accuracy and complete-trace verification are reported separately.
- This audits displayed arithmetic, not hidden reasoning, causal faithfulness, cognitive strategies, or natural-language reasoning quality.
- One paired seed on restricted development sets. Sampled generations from the same problem are dependent; generation counts are descriptive, not independent trial counts.
- Only stored pilot development/train predictions and frozen development/train references were read; no generation, GPU work, or holdout evaluation.

Each generated output has a line-level audit in `predictions.audit.jsonl`.
The original text is retained in its immutable run file and linked by source
path, line number, problem/sample identity, and SHA-256. `summary.json`
records full source-file and audit-code hashes for exact reproduction.

Reproduce into a fresh output directory:

```bash
python -m scripts.audit_pilot_traces --out reports/new_trace_audit
```
