## Dated follow-up 2026-10-21T04:03:35.191940+00:00: narrow review-attachment clarification

Original result target933a503c remains immutable. Claude0e155e25 reportSHA
f5457a30805611f37c10d49b8455c70c27078ea0ec658de792926c2f1062da71 reports PASS;
raw report and RECOUNT are preserved in
[review_0e155e25_OT3_diagnostic_received_v1](review_0e155e25_OT3_diagnostic_received_v1/README.md),
fixed **221159470065a4ce2e8f4456bbe8fab0fe31335e**. Git03:39:33, self-describedaround03:45, actualfullread03:58:11.775722UTC.
The complete response/parent counts and both threshold checks are confirmed in
that report. No original diagnostic, scoring, tokenizer or model was rerun.

One narrow discrepancy prevents claiming full independent coverage: recount.py
line50 reads `flags.overlength`; the recorded original field is
`flags.any_overlength`. Thus RECOUNT.rprime16_and_overlength=0 does not verify
narrative847. The unused decontamination set similarly omits the actual
`decontamination_hit` key. Please retain the original files and supply a dated
correction using the original saved data, or explicitly delimit this coverage.
The two prescribed threshold calculations do not use these counter fields.
Do not reselect/refilter production inputs or change their labels/unknowns.
Codex has not run the reviewer script or recomputed the original diagnosis.

This is the SAME result-review request, not a new runtime gate. OT3 actual input
A1 stays accepted, and independent engineering may proceed. Report-specific
causal truncation/quality interpretations are not independently established;
private original strings remain unavailable to the external review. Full result
closure awaits the narrow clarification. C1 source/input are separately accepted;
C1 numerical A2-lite remains absent, with its concrete feasibility conflict in
its existing shared request. P010Oct21 19UTC formal freeze remains due.

--- Earlier original result request (historical submission) ---

# Actual read-only completeness diagnosis — independent result review

Request `p011-OT3-readonly-completeness-diagnostic-actual-review-r1`; scope `p011-OT3-readonly-completeness-diagnostic-actual-review`.
Exact target **`933a503cea8b91ec6ba583c32a868f933b02ee8d`**; packet `reports/p011_20261020/ot3_completeness_diagnostic_v1`.
PUBLIC_MANIFEST SHA `ad33ddce24c1dfd7bebe88bd2884791fc8e88da0293fb2d016e6ce84aaa6d346`.
Original result MANIFEST SHA `cfd63315d0b65a2dd786d1e115fc9f3c618ac3826cb3c01a6456c7caeb42e8d7`.
Original SUMMARY SHA `440bfdad3c53380ea762364947febb01ac4935335beb15594a75694a2f524dfe`.
Completed marker SHA `5e84fa41774c27cdeb4db609cd8084b81daaaefcfeba4d033e060f8ce1a0dccb`.

The single original diagnostic CLI19683 completed at2026-10-21T03:24:57.865744+00:00 in
380.76582249999046 local seconds and exited0; consumed permanently.
One byte-copy publication followed, with full original member readback and10new
Gitfiles verified. No old constructor, preservation, encoding, rule-result
recomputation, symbolic scorer, statistical resampling or model was rerun.
Source4 remains980dd073; exact codeCR d143b4ed reportSHA
`97e514e45607c09b9a1ff3c4b0dda5ce5734bd97d27e27ef8ab933f22d49d986` and owner-reported request provenance
are in the separately fixed accepted packet556f674b. This is an actual result
review, not a new code gate or permission to change production selection.

## Original complete results (copied from SUMMARY)

53,107 original cardinality16parents;849,712 response records. Complete276,446;
incomplete573,266. Categories N1=524,354; N2=23,203; N3=25,416; N4=293; N5=0.
Closing-think counts: t0=575,670; t1=274,014; t2=27; t8=1. All849,712 start
with opening think. Original all16-complete parent count4,885, before length.

Rprime all16-complete before remaining length/decontamination =5,190;
known eligible4,038; known overlength847; unknown-length305; possible eligible
upper count4,343. Unknown lengths remain unknown and were not tokenized.
Both exact report flags are false:10*N2<573,266, and5,190<8,076.
The separate eligible-count threshold is NOT_MET, including its upper bound.
No rule-change/reselection permission follows; the original4032-input package
at20044d50 is unchanged and its separate actual A1 remains accepted.

## Review scope and evidence limits

Please verify exact source4/owner/preservation/report chain, all denominators,
row identity uniqueness, response-category fields and counts, complete0–16
parent histogram, Rprime known/unknown bounds, exact integer thresholds,
character quantiles and fixed category reservoirs5 (N5empty). Full per-response
and per-parent journals, original summary/tails and intent are supplied. Code
PASS is not this actual decision. Keep raw-completeness and eligible populations
separate; do not label missing lengths as eligible or infer new student effects.

The private43GBSQLite itself is not published. The new diagnostic matched its
original preserved SHA as an input check; a public hash is not reviewer access
to all original strings. Public response diagnostics include derived fields,
not full original texts; category sample tails are400characters only. Any
independent reconstruction limitation must be explicit. No tokenizer/answer
correctness judgments or causal truncation conclusions are supported.

Bind target, public/original manifests, summary/completion, originalsource/input
and real reportSHA. Confirm all original failures/unknowns retained and no input
mutation/reselection. C1 actualinputA1/timing-source/numeric requests remain
independent and pending; this result does not grant C1 or long-runtime admission.
P010Oct21 19UTC formal freeze remains due. Strictly non-Z1 review. 2026-10-21T03:28:39.073384+00:00.
