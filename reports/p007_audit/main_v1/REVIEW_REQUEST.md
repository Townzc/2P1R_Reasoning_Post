# P007 main: external audit packet v1

Status: **external review pending**. Local/cloud engineering verification passed;
this is not a Claude verdict. Snapshot `p007-main-20261012-v1`.

Manifest SHA-256:
`ca17892ccef7056c7b8057ab6620fa2aff4deea16ace799f08ba65f14ae0df0b`.
Pin the Git commit containing this packet when responding.

- [manifest.json](manifest.json): immutable data-file hashes.
- [question_outcomes.jsonl](question_outcomes.jsonl):3,879 endpoint outcomes for
  eight runs and base, including parse/stop state, token counts, raw-file hashes
  and source run/checkpoint identity. No omitted formal endpoint.
- [runs.json](runs.json): exposures, dose, reference NLL, recorded diagnostic
  curves, original receipts and complete-state hashes.
- [cost_and_scope.json](cost_and_scope.json): cumulative provider meter, preserved
  prior failures, unknown diagnostics and attribution limits. Per-run estimates
  are not provider invoices. Final invoice is unavailable, not zero.
- [main closeout](../../sft_allocation_midpoint_20261011/MAIN_CLOSEOUT_20261012.json)
  and [original primary contrasts](../../sft_allocation_midpoint_20261011/FOUR_ARM_RESULTS_20261012.json).

From the repository root with NumPy installed:

```sh
python -m scripts.verify_p007_audit_packet --packet reports/p007_audit/main_v1
```

Priority checks:
1. Recompute all nine accuracies and the two original paired-question contrasts
   from the per-question file; verify denominator, seed pairing and intervals.
2. Check exact training exposures/dose and distinguish descriptive training NLL
   from a causal explanation for the Solutions−Repeat contrast.
3. Check limits of the cost-allocation claim, unknown handling and the
   [audit-suggestion disposition](../../../docs/audit/P007_REVIEW_DISPOSITION_20261012.md).

Bootstrap:10,000 paired-question draws,NumPy seed20261013,the same draw across
student seeds. It conditions on these models and this single procurement draw.
Eight interrupted middle diagnostics remain unknown; no formal endpoint is
unknown. Do not replace the frozen final endpoint with a curve maximum.

This compact packet does not contain private correspondence, full model weights,
or the complete raw token files. Raw/scored record hashes bind those retained
artifacts. Metric reproduction from Boolean outcomes is not independent
verification of model generation or answer parsing. Request the retained
artifacts if that deeper review is needed, and report unchecked items.

Please return a scoped PASS, PASS-WITH-NOTES, FAIL or INCOMPLETE-EVIDENCE with
finding IDs and exact reproduction evidence. No compute or code changes are
requested by this review. The owner sends external review requests.
