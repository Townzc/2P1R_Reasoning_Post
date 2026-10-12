# Version-specific handoff templates

Copy only the relevant template. The owner sends messages; these are drafts.

## Claude audit request

- Repository / branch / **exact commit**:
- Packet snapshot ID / manifest path / manifest SHA-256:
- Frozen protocol / result / per-question or per-attempt paths:
- Questions to audit (ranked, maximum3):
- Current engineering verification and its scope:
- Metered workspace usage with time; attributed estimates; final invoice status:
- Attempted versus completed dose; failures, unknowns and deviations:
- Proposed claims and explicit nonclaims:
- Reproduction command:
- Please return a scoped verdict, finding IDs, severity, exact evidence and
  reproduction steps. Do not modify code, start compute or approve a budget.

## Claude finding response

- Snapshot and commit actually inspected:
- Checks actually rerun; commands and outputs:
- Verdict: PASS / PASS-WITH-NOTES / FAIL / INCOMPLETE-EVIDENCE:
- Finding ID / severity / affected claim:
- Observed fact, inference and recommendation (separate):
- Supporting artifact paths and hashes:
- Correction or additional evidence required:
- Unchecked items and residual limitations:

## GPT Pro reading request

- Scientific question / rival explanation / design decision:
- Current evidence packet and related-work inventory:
- Closest primary papers, exact versions and sections:
- For each: actual experimental comparison, controlled resources, findings,
  limitations, and the overlap with our proposed contribution:
- Distinguish paper statements, your inference and suggestions needing tests.
- Return a short prioritized reading table and sources. Do not assert that a
  search is exhaustive or that no similar work exists without a defined scope.

## Codex disposition

- Finding ID and source:
- Status: accepted / corrected / deferred / disputed:
- Evidence and reasoning:
- Does it change interpretation, code, data, dose, budget or deadline?
- Proposed bounded action, prior authorization and any unresolved owner decision:
- New source commit and artifact version, when completed:
- Old evidence remains at:
