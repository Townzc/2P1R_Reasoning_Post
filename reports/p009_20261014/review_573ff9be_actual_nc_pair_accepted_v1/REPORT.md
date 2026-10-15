# Audit 20261014cg: `p009-stage1-NC-guard-repair-complete-pair-A4-r1` (actual NC pair A4)

- **Target:** `9a266dbe` (queued at `bd896bbc`)
- **Packet:** `reports/p009_20261014/stage1_nc_guard_repair_complete_v1`. Manifest `fc560e602f13bee81f92c86ba6a573fb2eba107ec22b9a649e588e1f35403d3d`. All 19 members match.
- **Replacement state SHA (public; binary not loaded):** `c5cd77d8d2632cfcb25a9d2b4990229ef07f05a1054da3626117d8b5f4530b62`

## Decision: PASS
- replacement_integrity = PASS
- paired_NC_gate = **NC_gate_passed**. The registered NC stop rule did not fire.
- S1 runtime is **not** admitted by this report.

## Independent checks (`nc_pair_rescore.py`)
**Replacement n3200, from the original-byte archive**
- **Prompts.** 6 raw batches give 1319 unique IDs in frozen order. Every prompt equals the frozen `input_ids`. No token is out of vocabulary.
- **Scoring.** My own BPE decoder ran the frozen `first_stop` (EOS 151643, cap 512) and `completion_score` against the gold.
  - Result: **967/1319**; 1261 native EOS and 58 length caps, counted wrong; 0 unknown.
  - Against the published oracle: **0 event mismatches, 0 score mismatches, 0 verdict disagreements**. Every raw SHA matches.
- **Dose.** All 1024 updates equal the update recomputed from `nc17_n3200_plan` and `nc17_n3200_encoded` (indices, LR, per-update supervised and processed tokens, cumulative sums). Total **2,097,148 targets** and 2,552,365 processed.
- **Units.** 1095 units, none missing or extra.
- **Merge and exit.** The merge ran in fp32 and saved in bf16, with 0 post-save updates. The training process exited 0 and joined before the endpoint.

**Pair.** NC400 comes from the cd-verified parent oracle. I paired the two by question ID.

| Measure | Value |
|---|---|
| n400 correct | 954 |
| n3200 correct | 967 |
| Δ (n3200 − n400) | **+13 = +0.99 pp** |
| Registered stop threshold (Δ ≥ 66, 5 pp) | **not reached** |
| Discordant questions | 237 |
| Only the n3200 student correct | 125 |
| Only the n400 student correct | 112 |
| My own bootstrap 95% interval | about [−1.4, +3.3] pp |

- The packet's `REGISTERED_NC_DECISION` gives the same numbers (`delta_count` 13, `discordant_count` 237).
- My bootstrap used Python `random`, not the registered PCG64 generator. It is a sanity check only. The registered NC rule is a point threshold and needs no interval.

**Lineage**
- The failed NC3200 (896 updates, preempted) stays `failed` and is not filled as zero.
- The preclaim zero-work call is kept, with 655¢ still reserved.
- Total Stage 1 reservation is 2620¢.

## 科学信号检查 (science-signal check)
- **The negative control is flat, as expected.** On GSM8K at fixed training compute, 3,200 distinct answers beat 400 by only 0.99 pp. That is consistent with P008's plateau.
- This means the new design (1,024 updates / 2,097,148 targets for every n) does not create a slope by itself. So any S1 slope cannot be blamed on the design.
- **Caveat.** The replacement decision was made after NC400's score (954) was already known. This is disclosed. The recipe was identical and the alternative was stopping, so I judge the risk of bias to be low.
- **Next:** S1 seed 17, n400 vs n3200, on MATH. The registered futility rule stops the remaining runs if S1's Δ is below 2.0 pp.
