# OT3 completeness diagnostic — exact short CR candidate

Prepared, not run. This implements the distinct Claude request c7977d2a,
which records the owner's direct “做” in claude.ai. Codex has not seen that
underlying conversation. The original request and its hash are copied here;
public disposition of that authority is in the preceding actual review packet.
No production input, selection, encoding or model has changed.

The only production database access is immutable/read-only with query_only.
Before access it verifies the original43GB database and saved dispositions as
inputs to this new diagnostic; it does not rerun the old preservation tool.
All53,107 cardinality16 parents and849,712 responses are read in deterministic
parent/source_file/row_index order. Original rules.complete is called directly
once per response, with no alternate production implementation. Per-row t,
exact startswith<think>, boxed flags, original completeness and character length
are retained in gzip JSONL. N1–N5 follow the requested ordered definitions.
No tokenizer, new decontamination check, scoring, model or new selection runs.

Original saved completeness/disposition consistency is checked. Parent original
complete counts0–16 are retained. Counterfactual Rprime all16 completeness is
reported before length/decontamination, separately from original decontamination
and known-overlength exclusions. Previously unchecked lengths remain null and
are reported as unknown, never a pass. Known eligible and possible eligible
upper counts are separate. The request's8076 reporting flag applies to the
raw Rprime-all16 completeness count; a separate eligibility-threshold status
is MET/NOT_MET/UNKNOWN based on the known/possible counts. Please explicitly
accept this interpretation in the short CR. It cannot authorize reselection.
The N2 flag uses exact integer10*N2>=incomplete with nonzero denominator.

Character quantiles use deterministic linear interpolation at(n-1)*p for
10/50/90/99%. Samples use an independent Random(20261021) reservoir of5 per
category over the fixed row order, retaining only path_id and last400characters
plus row diagnostic fields. A category with fewer than5 returns all available.
N1 patterns are not proof of truncation, and format counts are not correctness
or causal estimates. Any threshold flag only requests an owner disposition.

The local3600second hard limit and originalOct22 05UTC cutoff are both enforced.
A new permanent attempt fence and fixed output prohibit whole-tool retry. Failed
or partial evidence remains; no complete summary is emitted for partial input.
This short CR concerns this complete read-only path, not another scientific gate.
Actual results need review after this one diagnosis; no actual result yet exists.

Twelve new synthetic checks passed once0.004seconds, including original-function
calling, categories/nulls, multi-think and exact2000 boundary, character quantiles,
unknown lengths, saved-disposition mismatch, exclusions, deterministic reservoirs,
threshold/bounds and a32-response read-only SQLite fixture. No original corpus,
model or old successful test was read/rerun. No real diagnostic was executed.
