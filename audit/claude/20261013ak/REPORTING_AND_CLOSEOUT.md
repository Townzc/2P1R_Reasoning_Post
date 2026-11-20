# Claude audit 20261013ak — reporting supplement and T8 read-only closeout helpers

## p008-registered-reporting-A1-A2-r1 @ 4c1ad2d9: **PASS**

### Wallet table: 16/16 match my own replays
I compared every wallet against my own replays: G1-D1 (`g1_d1_packet.json`, using the frozen judgments; 20261013u) and the merged G1-D2 (`g1_d2_packet_merged.json`; 20261013aa). All 16 match on these fields:
- **charged units**, exactly, including the fractional p4 charges. For example, 106,387,753/64 = 1,662,308.640625 and 718,997/4 = 179,749.25;
- **purchased problems** and **usable answers**;
- **paid attempts**, equal to my action count × 16. For example, D1 B8/p0 gives 269 × 16 = 4,304 and 274 × 16 = 4,384, and D2 B8/p4 depth gives 142 × 16 = 2,272.

The **zero-usable** columns equal my *corrected* ac values: D1 10/3/2/1/88/25/20/14 and D2 11/2/0/0/74/21/19/13. Every wallet stops with `cannot_reserve_full16_action`, none hits pool exhaustion, and there are 0 technical unknowns. Unused cap equals cap − charged; I checked the rows I sampled.

### Overlap
- **Usable-problem overlap:** I recomputed all 4 high-B rows independently from the problem ids in the admitted student input rows. Every intersection, union and Jaccard value matches:
  - breadth/0: 1,788 / 5,165;
  - depth/0: 147 / 1,889;
  - breadth/4m: 101 / 1,566;
  - depth/4m: 34 / 1,020.
- **Purchased-problem overlap:** the 4 rows are internally consistent (union = D1 + D2 − ∩). I did not recompute the intersections, because that would need the purchase events.

### Other figures
- **Physical teacher work:** D2 has 3,992 parent outputs + 3,424 child outputs = 7,416. This is consistent with my D2 G1. The packet correctly notes that summing the virtual-wallet tokens would double-count shared physical generation.
- **Billing snapshot (01:24 UTC):**
  - workspace delayed usage $166.55;
  - P008-labelled $78.31;
  - billed $0, labelled as not an invoice;
  - P008 reservation $266.44, kept distinct.
- **Labels from my 20261013aj notes.** A2 (bridge gap) is labelled "conditional, unregistered", and A3 (parser-v2) is still marked pending. A1 is now satisfied: the publisher v2 puts these numbers on the final page.

### Observation for the report (descriptive)
The high-B **depth** pools barely overlap across draws (Jaccard about 0.08 at p0 and about 0.03 at 4m), while breadth/p0 overlaps at about 0.35. So D1 and D2 depth students trained on largely different problems. This is useful context for any draw-to-draw spread.

## p008-t8-readonly-closeout-code-r1 @ 4aadc204: **PASS** (helpers only; none have been run)

### `collect_t8_cap_wave.py`
- **Run set.** It takes 1–8 named, distinct T8 runs. None may already have a closeout, and none may appear in any earlier wave intent (create-only, disjoint fence).
- **Envelopes.** Each run's envelope must be completed, carry its own run id, and have a manifest digest equal to the evidence.
- **Before the ledger scan.** The provider must be read as stopped with 0 containers, and each terminal must equal its envelope receipt.
- **The scan.** It is one shared scan of the claims store, limited to the original and replacement prefixes; the global amendment key lies inside that prefix. The selected terminals and the supplements are verified against the scan, and then again live before and after each closeout.
- **Per-run files.** Each closeout gets a hard link to the one ledger, the original Volume mtimes, `provider.json` and `COLLECTION.json`.
- **What it does not claim.** It makes no atomic-snapshot claim for unrelated active rows.
- **On failure.** It writes `ERROR.json`, keeps the partial pieces and the intent, does not allow a whole-wave retry, and is capped at 1,200 s.
- **Remote state.** It writes nothing remotely.

### `recover_completed_t8_cap_receipt.py`
- **Preconditions.**
  - The canonical result is absent.
  - `return_error.type == 'ConnectionError'`, with a DNS/reset/client message. I checked that today's DNS disconnects were in fact recorded with exactly the type `ConnectionError`, so the precondition matches reality.
  - The real cap binding is valid.
  - The provider is stopped with 0 containers.
  - The terminal is completed, with an exact claim→intent→plan/config/source chain and a deadline of exactly claimed + 9,630.
  - The supplement verifies.
- **The reads.** It reads 4 Volume files, each bounded to 16 MiB, writes each one create-only, and binds them to the terminal evidence and the manifest. It checks 9,600 s, 1,258¢, the supplement, and the cost fields with invoice = None.
- **Before writing.** It re-reads the ledger and the supplement and requires both to be unchanged. Only then does it write the reconstructed envelope.
- **Remote state.** No spawn, no claim change, no remote write, no scoring.

### Mocked tests
The 3 mocked checks were reported to pass. I read the source; I did not execute the tests against the cloud.

### Note
**L1 (LOW).** The recovery helper records its provenance in `receipt_recovery_t8_cap/<run>/READBACK_VERIFIED.json`, not next to the canonical `result.json`. The wave collector writes `COLLECTION.json` into `closeouts/<run>`. For the public per-run packet, please carry a `COLLECTION.json`-style marker, as was done for the T1s, whichever route was used.
