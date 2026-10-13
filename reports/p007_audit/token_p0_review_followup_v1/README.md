# Token price0 seed17: external review and E2 follow-up

Claude report pinned at2d811a49 gives PASS-WITH-NOTES to the first corrected
pair, and PASS to the earlier R1/L1 offline fixes. This packet records that
version-specific review without overwriting the original outcome packet.

Codex independently decoded the saved E2 row, reproduced the empty marked
answer claim, and recomputed the paired-question bootstrap using10,000 draws,
seed20261013: depth−breadth−0.9856pp, conditional interval[−3.1842,1.2130].
This is uncertainty across questions conditional on two fixed models/traces,
not across training seeds or acquisitions. No stable advantage is established.

The original report has a count-wording slip in one sentence: each model has
1,319 outputs,2,638 combined. Use the complete artifact roster as denominator.

The frozen primary score remains963/950. No alternate scorer was applied to
training or live evaluation. A possible eventual supplementary format sensitivity
must use the same rule over every completed model, separately from the primary.
The high-price and seed23 outcomes are not covered by this external verdict.
