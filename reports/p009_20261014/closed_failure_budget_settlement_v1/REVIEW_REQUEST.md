# Exact closed-failure budget settlement review

Scope: `p009-closed-failure-metered-settlement-code-and-numeric`.

Please review the two exact source files, new direct owner authorization, projected original gross app reports and immutable failed/STOPPED lineage. Independently recompute126c closed charge,374c released historical reserve,378c including full252c remainder reserve and622c Stage0 headroom. Check freshness/15min stop age, upward rounding,50c-or20% per-app lag allowance, unique app/interval handling, missing data refusal, monotone historical floors and refusal to cap a later overrun. The allowance is uncalibrated and later metering increases must reduce future headroom.

This review is required before future-stage budget gates use the released amount. It is separate from, and does not block, the existing32-source remainder runtime/numeric review at5c522257, whose500c accounting remains conservatively unchanged. Please return fixed target, exact source_files, settlement_proposal_sha256 and actual decision; do not infer scientific A2 or admit P2/P3/Stage1. No message is sent externally by this publication.
