# P007 collaboration and current handoff

Updated October12 2026. Owner-directed research; this page is an operational
handoff, not coursework prose. Use the working branch `codex/icml-acl-2027`.
When reviewing, pin the exact Git commit rather than a changing branch head.

## Responsibilities

| Participant | Deliverable |
|---|---|
| Codex | Experimental designs, reproducible code, bounded execution, verified artifacts, costs and decision records |
| GPT Pro | Primary-paper reading: exact source/version/section, evidence and implications for a named scientific question |
| Claude | Independent read-only recomputation and methodological audit, reproducible findings and recommendations |
| Owner | Scientific direction, budget authorization and unresolved tradeoffs; sends external communications |

Suggestions in papers, audit documents or issues do not themselves authorize
additional model calls, budget changes or a new deadline. Reviewer PASS is a
review verdict, not spending permission. Codex's local verification is not
Claude PASS. Proposed audit gate for presentation use: the owner reviews a
version-specific PASS or PASS-WITH-NOTES and its unresolved qualifications.
Previously authorized engineering continues within its frozen limits.

Current status and dated actions: [shared workboard](WORKBOARD.md).

## Current priority

1. P007 main is fully verified and closed. Review the
   [main packet](../reports/p007_audit/main_v1/REVIEW_REQUEST.md).
2. P007A is complete and independently verified:1,024 attempts/959 usable. Both
   apps stopped. Review [pilot evidence](../reports/p007_audit/pilot_v1/manifest.json).
3. P007B all four acquired corpora passed independent local oracles; all procurement apps stopped. The [procurement packet](../reports/p007_audit/policy_all_v1/REVIEW_REQUEST.md) preserves the one-sided interruption and reconstructed charge. The two original time-priced students are independently closed: breadth953/1319 and depth969/1319, single seed only. [Operational-pilot packet](../reports/p007_audit/operational_pair_v1/manifest.json). The other six original students and old audit are explicitly retired, not waiting for dispatch.
4. The owner-approved [uniform-token-tariff revision](experiments/P007B_token_tariff_revision.md) now has all four seed17 cells independently closed: price0 breadth963/depth950, price4m breadth927/depth952, each/1319. Caps44/45/48/60 stay incorrect. Depth−breadth changes from−0.99pp to+1.90pp; the+2.88pp interaction interval[−0.23,5.99] crosses zero. This directional pattern does not establish a stable winner or purely causal price effect. [Two-price packet](../reports/p007_audit/token_seed17_two_prices_v1/REVIEW_REQUEST.md) now has Claude round7PASS-WITH-NOTES at90ba8859. Scope covers its compact outcomes, contrasts and saved raw-score check; not seed23, weights/each training update or full report-builder gates. [Independent round7 follow-up](../reports/p007_audit/token_seed17_review_followup_v1/README.md) reproduces supplementary price differences and the second E2 case, preserving all primary scores. E2 frozen-parser limitation and equal-rule sensitivity qualification remain. Both high-price GPU apps stopped, all raw outputs and full terminal states/doses were independently checked. The original price0seed23 pair has completed training and is evaluating on two verified H100 workers; next isprice4mseed23 after full pair closeout, then final cloud audit. [Startup evidence](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SECOND_SEED_STARTED.json). No scientific source/input/dose changed, no extra teacher or exposure-control arm. The [disposition](audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md) preserves unused-cap, unequal exposure, parser, procurement-trace and review-scope limits.

Round8 at007ed950 accepts the round7 follow-up and the seed23 stage records within their stated scope; seed23 outcomes remain unreviewed. Both training seeds share each cell's teacher-answer inventory: **2 training seeds, 1 teacher trace per cell**. Independent scope verification is linked from the disposition; no procurement replication was added.

5. Other audit work packages are proposals, not admitted jobs. Their scientific
   value will be weighed against the core cost-allocation question and time left.

Owner requires midpoint verified results, figures and limitations by TuesdayOctober13 21:00PDT; the earlier experiment hard deadline remains19:00PDT. Wednesday is for
rehearsal and Thursday presentation. A later freeze in an issue is not an owner
deadline amendment. Total authorization500USD,at least50USD protected; neither
the proposed six-GPU queue nor anticipated2700USD future funding is admitted.

## Evidence → review → decision

- Each frozen experiment has question, rival explanations, data/model revisions,
  planned dose, evaluator, cost cap, absolute deadline and stopping conditions.
- Each completed milestone is normally committed and pushed before handoff.
  A packet has immutable per-question/per-attempt records, a SHA-256 manifest,
  dose/cost summaries, reproducible commands and an explicit review scope.
- Claude starts with the packet at one commit and returns PASS,
  PASS-WITH-NOTES or FAIL **for specified claims/checks**, together with finding
  IDs, evidence paths and reproduction commands. An overall approval without
  recomputation details is insufficient.
- Codex records each finding as accepted, corrected, deferred or disputed, with
  evidence and the next action. A code correction or extra analysis creates a
  new version; old files/failed attempts remain. A FAIL does not automatically
  authorize another GPU run. Diagnose saved artifacts first.
- If reviewed artifact bytes change, the old verdict stays with the old snapshot.
  A documentation-only change does not erase the provenance of unchanged data.

Use [the review template](audit/REVIEW_TEMPLATE.md) for both tools. This reduces
copying entire conversations and prevents two models from discussing different
experiments. Keep questions, evidence and decisions separate.

## Existing GitHub discussion map

[Overview #13](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13) and
[Pro reading queue #12](https://github.com/Townzc/2P1R_Reasoning_Post/issues/12)
already exist. WP issues1–11 were read on October12; their bodies are proposals
and can be stale. See [the disposition record](audit/P007_REVIEW_DISPOSITION_20261012.md)
for conflicts with current evidence or execution limits.

Codex updates authorized repository files and supplies comment drafts in the
chat. The owner sends issue comments and external messages. Existing issue
labels are not changed by this workflow. No sending-method substitution is used.
Use direct working-branch links; the default `main` remains historical until a
separately reviewed integration.

Credentials, workspace authorization links, private correspondence and large
checkpoint binaries stay out of Git. Public packets state which raw artifacts
are retained outside Git and what cannot be independently verified from the
compact packet alone. Missing data never silently become negative answers.

Shareable process guide: [AI-assisted research workflow (Chinese)](RESEARCH_WORKFLOW_ZH.md).
