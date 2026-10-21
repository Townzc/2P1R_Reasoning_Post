# D pair: narrow predicted-cost budget correction

Claude's complete fixed report 87d2eba3 at b61b88f8 is CHANGES-REQUIRED, with an explicit reasoned clarification of plan section 7.1: the 80% threshold applies to predicted cost; full reservations must fit the hard remaining category cap. It does not authorize this changed implementation before exact review.

Only long_d_pair_path.py changes: pair_budget enforces reserve <= remaining D cap, then calls the unchanged forecast function which enforces projected cost <= 80% of the remaining cap. The SPEC locator points here to preserve the immutable original packet. No other production source changes; all62 source hashes are bound. Original job objects, frozen tokens/LRs, input A1, limits, rates, timing proxies, all failed reservations and the absolute window remain identical.

D1 forecast10.33/reserve11.40, then D2 forecast10.27 <=10.88/reserve11.40 <=13.60. All22.80 stays reserved against25. This is a numerical candidate using original observations, not a fresh quote, measured guarantee or paid permission. Five NEW targeted checks passed once; original ten successful checks were not repeated. Full binding plus original16 flags and explicit clarification flag are required in the genuine final report. Fresh per-entry rates, D1 availability, complete shared ledger/slots, fences and window are still necessary.

F15 lacks successful A smoke selection; 600-second endpoint proxy is uncalibrated, original963-second future margin unchanged. Both D cells or neither. A remains explicitly held for owner; no reduction of reserves, cap increase, transfer, input preparation, upload, model, score or production call occurs here.
