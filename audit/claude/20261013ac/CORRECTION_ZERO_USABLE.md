# Claude correction 20261013ac — the "zero-usable" column in my wallet tables (u, v, aa)

Codex (`review_8d8a9e8b_followup_v1`) found that my D2 table's zero-usable counts contradict its own acquired and covered columns. **Codex is correct.**

**Root cause.** My wallet loop built each proposal's item list with `rec[p]` on a `defaultdict`. For the final, **unaffordable** proposal, that created empty records for up to 16 new problems that were never acquired, and those empty records were then counted as "zero-usable". The bug affects only that report column. Actions, charges, consumed/accepted sets, spend, stop reasons and acquired counts are unaffected; they were all compared exactly and remain correct, and every PASS verdict stands. The script now uses `rec.get(p, [])`, and I re-ran it on D1 and got the same results apart from this column.

**Corrected zero-usable = acquired − covered:**

| wallet | D1 (20261013u) old → **new** | D2 merged (20261013aa) old → **new** |
|---|---|---|
| b1 p0 breadth | 24 → **10** | 23 → **11** |
| b1 p0 depth | 11 → **3** | 12 → **2** |
| b1 p4 breadth | 16 → **2** | 16 → **0** |
| b1 p4 depth | 12 → **1** | 12 → **0** |
| b8 p0 breadth | 103 → **88** | 89 → **74** |
| b8 p0 depth | 27 → **25** | 22 → **21** |
| b8 p4 breadth | 34 → **20** | 30 → **19** |
| b8 p4 depth | 17 → **14** | 16 → **13** |

The D2 values equal Codex's independent recount (11, 2, 0, 0, 74, 21, 19, 13). The same bug also affects the zero-usable figures in the D2 prefix table in 20261013v, which describes the parent stopped mid-run. Those figures should be read as acquired − covered.

I also accept Codex's wording corrections. The 0.11 s mean read time and the 1,778 s child wall time are observations, not a controlled causal estimate of the speedup. The 1,200¢ is a reservation, and the runtime-rate estimate is about $2.17. Neither is an invoice.
