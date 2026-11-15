# A8 T group admission

Four accepted arms are reserved: $33.990063 / $40; combined accounted and reserved $411.005838 / $485. The existing $30 global storage reserve is included once. Storage admission uses the actual API rate and usage.

T01, T03 and T04 start with the current 61163c22 configuration. After all B/C calls complete, the finite controller applies the exact accepted 845af084 candidate, records its commit and starts T02. Training, generation, scoring and frozen predictions are unchanged. Greedy evaluations are serialized, with actual costs reconciled between endpoints.

The canonical combined ledger is review_204ad0ae/current_budget.py. It adds A8 to the unchanged original T/A6/A7 accounting; historical GSM all_tracks snapshots exclude A8. All four requests are exploratory and excluded from H0–H3.
