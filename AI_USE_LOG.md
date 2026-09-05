# AI assistance log

## 2026-09-05 UTC — repository bootstrap
Codex imported user-provided CPU arithmetic code and synthetic fixtures, summarized the updated SFT-only protocol, and established public-repository hygiene and compute accounting. Source fixtures are CPU examples, not model results. Private correspondence and server credentials were excluded. Human decisions: start implementation, use this repository for progress, cap initial GPU jobs at two GPU-hours. Validation and actual outcomes are recorded separately in reports and run directories.

## 2026-09-05 UTC — engineering implementation
Codex implemented exact response-token labels and exposure accounting, bounded subprocess execution with a persistent budget ledger, strict generation scoring, engineering overfit/profile entry points, and targeted correctness tests. It reproduced the CPU fixture byte-for-byte, pinned model revisions against the official API, and read targeted sections of three closest papers. Human review of the causal comparison and global-coverage exposure definition remains pending. No treatment effect has been inferred from fixtures or tests.

## 2026-09-05 UTC — first GPU attempt and overfit diagnostic
A launch during an incomplete server fetch exposed an untracked-source provenance gap. Codex stopped and invalidated that attempt, conservatively charged 120 seconds after confirming no run/GPU processes remained, added an explicit tracked-source guard, and synchronized the published Git history using a bundle. The subsequent committed-code run completed 400 updates: 25/32 train correctness, 0/16 greedy dev correctness, reference train NLL 0.011995. The 95% overfit gate failed. Raw outputs show malformed/incorrect arithmetic expressions, not a reason to relax the verifier. A new engineering run is configured from the same base with a lower learning rate (5e-5) and up to 800 updates to address oscillation; no scientific treatment comparison or dev-based model selection is implied.
