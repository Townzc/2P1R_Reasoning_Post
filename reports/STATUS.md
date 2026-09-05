# Verified status — 2026-09-05 UTC

- CPU data reproduced byte-for-byte; 35 server tests pass.
- All nine debug model files match official pinned file digests. Real tokenizer audit and environment inventory are recorded.
- First valid GPU run completed 400 updates: 25/32 train greedy, 0/16 dev greedy, train NLL 0.011995. The 95% overfit gate did not pass; lower-learning-rate diagnostic is next.
- Measured debug throughput: 621 supervised tokens/s over 100 updates after 10 warmups; peak allocated 8781 MiB, peak reserved 10062 MiB.
- Charged GPU budget so far: 462/7200 seconds, including a conservatively accounted aborted provenance attempt. See run_registry.json and raw run receipts.
- Existing fixture cannot provide the requested global-coverage control: necessary TV mismatch is at least 0.2578125. See ../docs/PILOT_PROPOSAL.md for an explicit exposure correction and proposed tolerances; it is awaiting review.

No scientific treatment effect is claimed. Next: pass the overfit gate, profile the main model, then review scientific data/control design.
