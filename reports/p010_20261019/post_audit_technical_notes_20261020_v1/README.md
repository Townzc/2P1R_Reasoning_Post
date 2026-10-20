# Dated technical footnotes after actual audit

Recorded 2026-10-20T14:28:40.078124+00:00; based on the [actual review disposition](../review_f04922a_actual_E3_C6_Z2_accepted_v1/README.md).
This is audit metadata and table documentation, not interpretive course prose.
Original tables, images, labels and interval files remain unchanged.

## T1 field definition

In [T1_COMPOSITION.csv](../z2_number_trace_v1/T1_COMPOSITION.csv),
`retried_questions` means **K1 selected from attempts 2–4**, excluding fallback
questions. It is not the count of all unavailable first attempts. Display it as
`K1_selected_from_attempt_2to4` or carry this footnote beside the original heading.
All four cancelled K4/K8 cells remain cancelled and unattempted.

## T3 / C6 GSM parser sensitivity

The frozen sampled cue-minus-no-cue result is +10.31 pp. Claude's additional
permissive-parser diagnostic reports approximately +5.31 pp on the same sampled
conditions (2,661 versus 2,381 correct, each out of 5,276). These are reviewer
diagnostic values, not a replacement primary score or a causal formatting share.
The original counts, all eight intervals and all frozen labels remain unchanged.
A symmetric permissive greedy contrast was not established. No Z1 values are used.
See GSM_PARSER_SENSITIVITY_DISCLOSURE.json and the fixed C6 report.

## Other retained audit limits

- E3: capped UTF-8 boundary differences and the reported numeral-base boundary
  case retain original stop decisions and labels; old T0.8 rows were not rescored.
- C6: the reported single sampled numerical-tolerance false positive, numeral-base
  and percent cases, and explicit parse failures remain disclosed without relabeling.
- Intervals are pointwise conditional results, not familywise coverage, equivalence,
  a seed-population bound or a mechanism.
- Use every original T4 contrast. The reviewer corrected its earlier O1 summary;
  no contrast is selected or recomputed in this handoff.
- Early Z2 A5 verified 73 trace sources; four local-only sources were not independently
  verified. Images were byte-compared, not rerendered by the reviewer.
- Z1 remains Claude-owned. Unexpected embedded content exposure is recorded in
  the acceptance packet; Codex does not adopt its labels or claim the owner's checks.

## Scheduled freeze

This addendum does not perform the scheduled 2026-10-21 12:00 PDT (19:00 UTC)
freeze. The actual frozen version and this footnote linkage must be submitted for
final A5, as requested by the reviewer.
