# Claude audit 20261013ah — N2 numerical review and T8 cap amendment @ 8e1b3463

## p008-t8-actual-n2-r1: **criterion FAIL confirmed (independently reproduced)**

**Inputs, rebuilt without using MEASUREMENTS.** I rebuilt every timing input from the published packets:
- 8 original T1 runs from `student_t1_eight_v1`;
- 2 replacement runs from `student_t1_replacements_v1`;
- base from `base_v1`.

The fields and their sources:
- update mtimes from `TIMING_READ_METADATA.json`;
- optimizer seconds and processed tokens from each `completed/update_XXXX.json`;
- the first eval intent mtime;
- block_journal_metrics;
- claim and terminal from each LEDGER.

All 10 T1 hosts agree exactly with `MEASUREMENTS.json`.

**Worker seconds.** `worker_seconds_through_terminal` is claim→finished for the 8 originals and for base (1,624.14). For the 2 replacements it is about 1 s longer (+1.018 and +0.923 s). That is min(saved start, claim)→finish, because the replacement timer now starts at entry. This is exactly the N1 rule I asked for.

**The frozen formula.** I re-implemented the frozen v2 formula in my own code (the unchanged `timing_gate.py` from e34f9c18, which I reviewed in 20261013t/u). Componentwise maxima, which match the proposal exactly:
- F = **3,787.53** (from `d1_b1_p0_breadth` replacement)
- u = **1.82442 s/update** (same host)
- c = 7.300e-4
- m = **0.19582** (`d2_b1_p0_depth`)
- K = 2 × 17 = **34**

**Result.**
- Point forecasts: 7,958.98–7,959.74 s.
- With the 20% margin: **9,550.78–9,551.68 s, which is above 9,530 for all 8.**
- **N2 stays closed=false. There is no subset and no T8 admission.**
- Proposal digest: 0fb18e74….

**Lineage checks.**
- The 11 logical members map to physical ids, with the replacements under their replacement names.
- Both failed attempts are retained, under proof 5e5667a0.
- spec ab49b0a6 and roster 3c22d003 are the bound spec and roster.
- No outcome fields are read.

The binding maxima, F and u, both come from the replacement breadth host. It was the slowest per update: 1.82 s/update, against 1.10–1.48 s for the originals. This is host variability, which is what the conservative max rule is designed to absorb.

## p008-t8-cap-amendment-proposal-r1: **arithmetic PASS; needs a direct owner decision**

**What it proposes.** Raise the cap from 9,560 to **9,600 s** for all eight T8 slots, keeping the 30 s soft margin, which gives a threshold of 9,570. The data, the 20% margin, the formula, the dose and the endpoint are unchanged.

**Arithmetic.**
- Per slot: ceil((9,600 + 700) × 4.393584 / 3600 × 100) = **1,258¢**, against 1,253¢ before.
- Total change: 8 × 5¢ = **40¢**.
- New stage total: 26,604 + 40 = **26,644¢ ($266.44)**.
- Headroom: 9,570 − 9,551.68 = 18.32 s.

**My assessment.**
- The amendment is **outcome-blind**: it rests on timing data only, applies uniformly to all 8 slots, and leaves the original failed criterion recorded. It is still a post-hoc change to a pre-registered *engineering* gate. Write it up as a deviation, not as a pass.
- The forecast is very conservative: componentwise maxima taken from different hosts, plus the 20% margin. A typical T8 is more like 2,500–4,000 s of fixed time plus about 2,048 × 1.5 s, roughly 6,000–7,000 s. The +40 s therefore covers the gap from the rule, not a realistic risk of timeout.
- The real risk is time, not money. Adding admission, review and a run of about 2 h means T8 is **very unlikely to finish before the 21:00 PDT freeze**. It fits the Wednesday 18:00 PDT exploratory window.

**What is still required.** Direct owner approval of the 9,600 s cap and the $266.44 stage total. Then a new exact source/spec/slot admission and a new numerical review with threshold 9,570. That admission must:
- bind the original unattempted logical slots;
- block both the old (9,560) and the amended dispatch paths from running twice;
- account for the 40¢.
