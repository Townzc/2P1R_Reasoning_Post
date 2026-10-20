# P011 data-path changes requested by Claude — owner decision pending

Original frozen plan: `claude/audit` commit
`e0dee182972f9910b707fac68800dcb5a3aff2d3`, SHA256
`20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22`.
Review: `efa4a7a8f50c283cf4e160c92077f9128fb146f5`,
`audit/claude/20261020s/REPORT.md`, SHA256
`69f2ee65c67689ae94458a3d6698a928b6f7c1d107b34fab255ec5aa73c3db0d`.
Decision is **CHANGES-REQUIRED**, not execution approval. The original data
construction has never run; no parent selection, production encoding, model,
or P011 scientific outcome has been observed.

## Concrete proposed amendment

| Item | Frozen plan / original implementation | Proposed replacement |
| --- | --- | --- |
| R1: A dose | B is A7's one-pass supervised-token count | B is the maximum one-pass supervised-token count across the original eight A cells; all cells still use exactly B and U=ceil(B/64000), complete answers and q/q+1 exposure. A7 need not be exactly one pass. |
| R3: deterministic sampling | Filter the full population, sort eligible parents, shuffle, take the requested count | Sort cardinality-16 OT3 candidate parents / common AM parents, shuffle with the same original parent seeds, check in that order and stop at 4096 / 1024 eligible parents. Report exclusions and difficulty on the examined prefix, not the full eligible population. |

R1 can increase the common training-token dose relative to the literal A7 rule.
R3 preserves uniform sampling from eligible parents under a random permutation
but changes the exact deterministic selected IDs. These are disclosed changes
before any production selection or student outcome, not retrospective claims
that the original frozen wording was followed. Claude calls them clarifications;
Codex records the literal differences and requests direct owner adoption.

No new arm, model, seed, question count, evaluation or budget is proposed.
The $180 cap and category caps remain unchanged. If the increased dose fails the
existing cost/window admission, it does not authorize higher spending or a timing
exception. Exact q/q+1 remainders can still be infeasible; no truncation or silent
answer removal is permitted. D's dose was already max(D1,D2) and is unchanged.

R2 is a code repair: each full pass independently shuffles every answer exactly
once with `Random('17:pass:<e>')`, then a separately shuffled exact extra subset
is appended. Global length bucketing is removed. Padding optimization, if any,
is confined to micro-batches within an already fixed update and requires the
runtime's CR. This repair proceeds independently of the owner decision.

## Required before production

1. Direct owner adoption of R1 and R3, bound to this proposal's exact bytes.
2. Claude's real fixed re-review of the revised source and tests.
3. Complete pinned raw downloads; the existing create-only / partial-evidence
   rules remain in force. The previous candidate stays unattempted.

This file is a proposal. It is not an ACCEPTED record or authorization to execute.
