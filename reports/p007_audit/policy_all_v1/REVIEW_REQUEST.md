# P007B procurement audit request

Pin this packet to a Git commit. External review is pending.

Check four same-cap cells, accepted/invalid/duplicate counts, zero-usable parents and unused balances. Compare attempts.jsonl with results.json and check every manifest hash. Existing policy_p0_v1 is preserved.

Special focus: breadth_p4 retains 192 known outputs from a watchdog failure and adds only 96 previously unattempted outputs. The last original action lacks its measured settlement; a conservative 50s charge is reconstructed from timestamped provider evidence. The reconstruction and unilateral interruption limit a clean price-interaction interpretation. Check that this is not hidden by a completed continuation receipt, and that no runtime estimate for the continuation is mislabeled total cost. No original claim was reset and no output replayed.

Eight student plans are frozen at 256 updates and 524,288 supervised targets per run. They retain every usable complete answer; all four corpora and both seeds must pass together. Compare P007B_STUDENT_ADMISSION.json and source mappings. There are no student accuracy results yet.

Full raw-token artifacts and timestamped provider logs remain privately retained. If inaccessible, mark those checks unverified. Local oracle results do not constitute Claude PASS. Return findings with severity, evidence location, reproduction steps and scope of each verdict.
