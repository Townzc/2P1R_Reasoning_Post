# Frozen forward metadata erratum

Source commit: `2bb39fbdf5bf83bb471e436804e1b968262ff530`. This correction is descriptive only; the running source, scientific queue, raw manifests and budgets remain unchanged.

The frozen `launch_manifest.json` label `identity.planned_candidate_scores=2304` counts only the six fresh eval_H views. Stage A also runs two train_H candidate views: 2 × 64 contexts × 4 scores = 512 scores. The full registered plan is **704 candidate contexts and 2,816 candidate scores**.

The frozen `identity.planned_forward_contexts=16384` is mislabeled. Its value is the **hard cap on sequence-forward equivalents**, not a planned context count. The actual planned work is **7,552 sequence equivalents across 28 views**, already stated correctly in the frozen queue, prepared plan and protocol.

| Scope | Views | Sequence equivalents | Candidate contexts | Candidate scores |
|---|---:|---:|---:|---:|
| Stage A parent original H/F reference decomposition | 4 | 2048 | 0 | 0 |
| Stage A parent fixed train_H reference decomposition | 2 | 128 | 0 | 0 |
| Stage A parent fixed train_H first-decision candidates | 2 | 128 | 128 | 512 |
| Four endpoint original H/F reference decomposition | 8 | 4096 | 0 | 0 |
| Six-state fresh eval_H reference decomposition | 6 | 576 | 0 | 0 |
| Six-state fresh eval_H first-decision candidates | 6 | 576 | 576 | 2304 |
| **Total** | **28** | **7,552** | **704** | **2,816** |

A reference decomposition is one sequence forward. All frozen operator candidates are single-token, so four candidate scores share one sequence forward. The 6,848 reference decompositions plus 704 candidate-context forwards give 7,552. Teacher-forced scores are separate from the 4,736 planned autoregressive generations and the 512 training updates.

The two erroneous constants are used only to populate launch identity metadata. ForwardBudget continues to charge actual calls against 16,384; no execution or budget mismatch is implied, and no run stop is required.

The original review preceded final export; observed completion is now recorded below. The final report must count immutable candidate records/scores and all 28 views, and report charged forward reservations separately from completed scientific work. Any ambiguous or fault reservations remain charged. Preserve the frozen fields and attach this correction transparently.

## Final saved-output count supplement

Final execution status: `completed`. Durable records contain 704 candidate contexts, 2816 candidate scores, 6848 reference decompositions and 7552 sequence-equivalent outputs. The ledger charges 7552; 0 charged equivalents lack saved outputs. These are direct saved-record counts, not model-logit recomputation. Original frozen launch fields remain unchanged.
