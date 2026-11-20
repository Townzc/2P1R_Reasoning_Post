# Claude audit 20261013am pt2 — D2 zero-price T8 pair @ 28ad56c5: **PASS (both)**

I used the same method as pt1:
- The device tar blob ids equal the ones in the commit (30501f87…, 63657e19…).
- The archives were extracted into isolated directories, and each was checked with `g3_endpoint.py` plus `t8_lineage.py`.

| run | frozen primary | caps | event mismatches | parser disagreements | entry→terminal s |
|---|---|---|---|---|---|
| `d2_b8_p0_breadth_t8` | **956** (72.48%) | 51 | 0 | 0 | 6,627 |
| `d2_b8_p0_depth_t8` | **971** (73.62%) | 45 | 0 | 0 | 6,263 |

Every lineage and dose item passes:
- tar = manifest ⊂ artifact manifest;
- 35-source bundle and spec 4ca2c55d;
- original config at 9,560;
- the ledger chain, a deadline of exactly claimed + 9,630, and 1,253¢;
- the 5¢ supplement bound to this run's claim;
- LR equal to `LR_VECTORS["2048"]`, and the schedule equal to the frozen plan;
- 2,048 updates totalling 4,194,296 targets, with 128 blocks;
- the 1,024-step forensic targets match, with `used_for_selection=false`;
- named-wave collection with 0 calls and 0 writes, and the provider stopped with 0 containers.

7 of 8 T8 outcomes are now externally checked. `d2_b8_p4_depth_t8` is still pending.
