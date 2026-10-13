# Claude audit 20261013aa — p008-g1-d2-merged-r1 @ eb398fb1: **PASS-WITH-NOTES (D2 merged numeric G1)**

Audited 2026-10-13 ~19:30 UTC. This report admits no student.

**Method.** I ran my own device script, `~/aud/g1_merge.py` (sha256 6cc8c812…ad25d), the same family of scripts as the D1 G1 in 20261013u. It reads the parent raw outputs from `pool_d2_reconciliation_v1/physical_batches` (146 batches) and the child raw outputs from `pool_d2_merged_v1/child_physical_batches` (127 batches). It decodes the raw `token_ids` itself and replays all 8 wallets from an empty state with my own wallet loop. On the device, the merged packet is hash-identical to git `eb398fb1`: 285 files, combined digest `473b1825…8232c` on both sides.

## Q1. Rescore: YES
- **Counts.** Parent batches 0–145 and child batches 146–272 are each contiguous. That gives **7,416 outputs** (3,992 parent + 3,424 child) and **2,210,122 returned tokens**.
- **Integrity failures: 0.** The checks covered:
  - every seed against `stable_seed('teacher',2,pid,att)`, child included;
  - prompt IDs identical across parent and child for each parent problem;
  - raw and scored token agreement, and no output over 1,024 tokens;
  - completion tokens;
  - the attempt prefix k−1 existing before k across the parent/child boundary;
  - **no duplicate candidate ID**, so no parent candidate was regenerated.
- **Disagreements.** My parser counts 6,530 usable answers against the frozen parser's 6,513. All 17 differences go one way (the frozen parser rejects, mine accepts): 8 are E1 percentages and 9 are E3 "The answer is:" cases. These are the same conservative classes as in D1.
- **Lineage.** The original parent stays `failed` (`terminal/pool_d2`). The child is `completed`: 1,200¢, evidence 51744d69…, with a separate campaign key. The ledger has 1,104 unit and 1,104 done keys plus both terminals. All three apps are stopped, with 0 containers.

## Q2. Wallets: YES, an exact match for all 8, from empty state to a legal stop
For every wallet, the action keys, per-action charges, consumed and accepted sets, exact Fraction spend, stop reason and acquired count equal `complete_wallets/*_events.json` and `*_summary.json`.

**Every one of the 7,416 outputs is consumed** by at least one wallet, and **every wallet stops legally** (`cannot_reserve`). The six wallets that had already finished in the parent are unchanged from the prefix audit (20261013v).

| wallet | actions | acquired | usable | covered | zero-usable | spent/cap |
|---|---|---|---|---|---|---|
| b1 p0 breadth | 31 | 415 | 404 | 404 | 23 | 91.9% |
| b1 p0 depth | 32 | 124 | 479 | 122 | 12 | 94.1% |
| b1 p4 breadth | 6 | 96 | 96 | 96 | 16 | 85.1% |
| b1 p4 depth | 16 | 64 | 250 | 64 | 12 | 92.7% |
| **b8 p0 breadth** | 268 | 3,591 | 3,517 | 3,517 | 89 | 99.2% |
| **b8 p0 depth** | 273 | 1,039 | 4,014 | 1,018 | 22 | 99.0% |
| b8 p4 breadth | 63 | 860 | 841 | 841 | 30 | 99.0% |
| b8 p4 depth | 142 | 544 | 2,077 | 531 | 16 | 99.3% |

## Notes
- **G1D2-N1 (efficiency evidence).** The child made 510 complete 11-key checks in **56.4 s total (mean 0.11 s, max 1.48 s)**. The parent's sequential 26-key reads took 3.4–7.1 s each. The child finished its 127 batches in **1,778 s**, against the 7,070 s proxy. This is direct evidence that metadata reads, not GPU time, dominated the original pools' wall time. It is relevant to tonight's budget table.
- **G1D2-N2.** The D1 and D2 inventories are similar in size: b8 p0 breadth has 3,436 usable answers in D1 against 3,517 in D2. Because the joint-T rule needs both corpora, it can now be computed.
- **G1D2-N3.** This PASS covers the merged pool only. The joint plan gate, the student numeric spec and N2 timing still need their own reviews.
