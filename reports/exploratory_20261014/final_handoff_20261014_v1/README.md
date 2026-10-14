# Final exploratory results — October 14, 2026

Both owner-approved exploratory experiments and all three complete evaluations are finished. Local raw/source/dose checks and the independent **actual-result G3 review PASS** are complete. All three suffix apps are stopped with zero owned containers. No scientific computation remains.

| Evaluation | Correct / 1,319 | Accuracy | Length caps counted incorrect |
|---|---:|---:|---:|
| Qwen2.5-1.5B base, fixed dev-only 4-shot | 823 | 62.40% | 9 |
| Official Qwen2.5-1.5B-Instruct, zero-shot | 904 | 68.54% | 54 |
| Natural-wrong-teacher student | 934 | 70.81% | 43 |

All use the frozen greedy/512-token/context-2048/batch-16 endpoint and marked_answer_v1 parser; technical unknowns are zero. The requested correct-answer breadth control is **969/1,319 (73.46%)**. The wrong-teacher student is **35 questions lower (−2.65 percentage points)**, a descriptive difference. Depth965 and base0-shot638 are previously completed background references, not new runs.

The wrong-teacher student was trained once on 429 eligible answers from 101 questions, with 256 updates, 524,287 targets, seed17, LoRA and the frozen LR/schedule. After the owner-requested stop, the reviewed continuation restored its exact original checkpoint and only finished evaluation. All 496 saved outputs, including48 unacknowledged rows, were reused; 3,461 new suffix rows completed3,957 total. No retraining or duplicate generation occurred; original failed parents and their costs remain in the record.

These are **non-preregistered** results on a previously observed test. Different coverage, answer length, exposure and label ambiguity prevent a pure correctness-effect interpretation. Four-shot exemplars also carry content/context, and the general Instruct model under this local protocol is a reference, not a capability ceiling. No new confidence intervals, winner selection or causal claim is introduced here. Reviewer-only exploratory intervals and interpretation boundaries are documented in [the disposition](DISPOSITION.md).

At 10:23:08–09UTC / 03:23PDT, the six original-plus-suffix apps had **$11.19667285 delayed metering**: $5.43330865 original work plus $5.76336420 suffixes. This is not a final invoice or balance; setup/build/download/storage and lagged fees remain accountable. The approved total cap stayed **$30**; no additional budget was used for this closeout. The conservative project check was $384.23919669 against the $450 spending ceiling with $50 protected.

Materials:

- [Complete results, per-question evidence, source/lineage and manifests](https://github.com/Townzc/2P1R_Reasoning_Post/blob/0debdeba2c9b581c3fdf526d346399721f4cf670/reports/exploratory_20261014/completed_endpoints_v1/README.md)
- [Full result data](https://github.com/Townzc/2P1R_Reasoning_Post/blob/0debdeba2c9b581c3fdf526d346399721f4cf670/reports/exploratory_20261014/completed_endpoints_v1/RESULTS.json) and [saved cost snapshot](https://github.com/Townzc/2P1R_Reasoning_Post/blob/0debdeba2c9b581c3fdf526d346399721f4cf670/reports/exploratory_20261014/completed_endpoints_v1/LATEST_BILLING.json)
- [Original stop, saved prefixes and checkpoint preservation](https://github.com/Townzc/2P1R_Reasoning_Post/blob/bdf2ffd36ffe07ac94b7cd5c03290f0a20092c1d/reports/exploratory_20261014/owner_stop_preservation_v1/README.md)
- [Exact continuation code and numeric review](https://github.com/Townzc/2P1R_Reasoning_Post/blob/ae553bd21b492ee16b5416912bc0f423650181e1/audit/claude/20261014aw/REPORT.md)
- [Final independent full-result G3 report](https://github.com/Townzc/2P1R_Reasoning_Post/blob/8573632e0ac315a8404277b8cdf748799c53dc18/audit/claude/20261014ax/REPORT.md) and [bounded acceptance](ACCEPTED.json)
- [Previously closed P008 final materials](https://github.com/Townzc/2P1R_Reasoning_Post/blob/031462f90c3da1eea4e636fd8f4d10d2a5a83d9b/reports/p008_20261013/final_handoff_20261013_v1/README.md)

The original result packet retains its then-pending review metadata; this dated acceptance supersedes that status without rewriting its bytes. P008 and its21PDT material freeze remain unchanged. Operational monitor closure is recorded separately in [the pause receipt](../AUTOMATION_4_PAUSED_20261014.json); p007 remains paused. Handoff prepared 2026-10-14T10:57:24.933488+00:00 (2026-10-14 03:57:24 PDT).
