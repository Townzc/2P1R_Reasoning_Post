# September 30 storage cleanup

The owner requested deletion of unused server data after startup. Six closed
step-128 training-state files (AdamW, scheduler and RNG state) and six orphaned
transfer partials were removed after exact identity checks. This released
74,726,768,640 allocated bytes (69.59 GiB): used space fell from 85.04% to 38.64%,
and free space increased from 22.44 GiB to 92.03 GiB on the 150 GiB data volume.

All six final model weights remain (42,650,763,318 bytes). All twelve checkpoint
components were rehashed against the original audits before deletion; retained
model inodes/sizes/mtimes were unchanged afterward. The 246 Q2 input files were
also fully rehashed after cleanup. Scientific outputs, scores, training logs,
negative/failed results and original manifests were not deleted. Seven compact
cleanup evidence files were independently copied locally.

Exact optimizer/scheduler/RNG resumption of these six completed runs is no longer
available. Earlier audits describe the historical pre-cleanup retention state;
they have not been rewritten. Explicit retention markers accompany the model
stores. The newly prepared Q2 environment and complete input bundle are retained.
See [the compact receipt](RECEIPT.json).

The original Q2 >=40 GiB disk admission floor now passes. The previously proposed
lower post-install floor is unnecessary and is not adopted. GPU compatibility
and the finite two-update profile were subsequently verified in the separately
recorded [engineering profile](../q2_feasibility_20260929/RESULTS.md). Its saved new
model brought data usage to40.59%; about89.11GiB remained free. Provider OFF was
verified by05:02:38UTC. Cleanup itself performed no model experiment.
