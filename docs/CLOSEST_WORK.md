# Closest-work audit — 2026-09-05 UTC

**Updated 2026-09-10:** Verified student/teacher identities and compute settings
are in the [primary-source model audit](../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md).
The earlier notes below remain historical framing evidence.

**Updated 2026-09-09:** The expanded [positioning audit](../reports/ICLR_POSITIONING_20260909.md)
identifies a recent direct per-problem/global-diversity comparison, including
its released update-matched full-SFT recipe. It supersedes any impression that
the broad question below is unaddressed. Exact exposure accounting alone is
not an established novelty claim. The original narrower audit follows intact.

Scope: targeted reading of original-paper methods, results, and listed appendices; not an exhaustive literature review or reproduction. [closest_work.csv](closest_work.csv) contains the requested task/model/data/control/budget/seed comparison fields. “Not identified” means absent from the sections inspected, not a proof of absence everywhere.

| Paper and inspected sections | Finding and consequence for this project |
|---|---|
| [Data Repetition Beats Data Scaling in Long-CoT SFT, v1](https://arxiv.org/html/2602.11149v1), §§2–4, Appendices A/B | Repetition is already a strong baseline at fixed optimizer updates. This budget does not establish exact supervised-token equality. Retain memorization and termination diagnostics. The v1 negative-trajectory appendix captions appear inconsistent with the main table/discussion; numerical reuse needs underlying-result verification. Our short synthetic task is a boundary study, not its long-CoT reproduction. |
| [CoScale-RL, v1](https://arxiv.org/html/2601.14695v1), §§3–5.3, Appendices C and D.1–D.2 | The SFT ablation in D.2.2 explicitly aligns sample counts: 90 problems with 20 solutions versus 1,800 with one, using the same batch size and epochs. Evaluation there is on seen training problems. Thus generic solutions-per-problem scaling is already closely covered. Our narrower question requires canonical structural labels, global coverage, surface and repetition controls, exact token accounting, and shared held-out problems. No positive novelty claim is established by this audit. |
| [What Do Learning Dynamics Reveal About Generalization in LLM Reasoning?, v1](https://arxiv.org/html/2411.07681v1), §§3–5, Appendices A–C | Pre-memorization accuracy is a calibrated learning-dynamics metric, not ordinary train correctness or NLL. Preserve checkpoint predictions and likelihoods, but do not label the current implementation as reproducing that metric. Any later calibration uses development runs while the final test remains sealed. A 32-example overfit is a software gate, not generalization evidence. |

Before a scientific pilot, publish candidate eligibility, exact exposures, token and global-structure residuals, plus interpretation limits. Existing engineering fixtures do not meet that gate. No joint global-coverage/surface/repetition control under exact token matching was identified in these inspected sections; broader literature and code audits remain open.
