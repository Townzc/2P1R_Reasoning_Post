# Claude audit 20261013u — G1-D1 pool (7973161b) and timing policy r2 (e34f9c18)

Audited 2026-10-13 ~12:50 UTC at 7eead57c.

## 1. p008-g1-d1-pool-r1 @ 7973161b — **PASS-WITH-NOTES (D1 numeric G1; this admits no student)**

**Method.** My own scripts ran on the owner's device. They decode the original raw `token_ids` with a pure-Python byte-level BPE decoder (tokenizer.json from the frozen reconstruction), score each output with my own parser, dedupe, and then **re-implement the wallet** without importing Codex's `procurement.py`/`Policy`.

The D1 packet on the device is hash-identical to the git commit: the sha256 over all 575 file hashes is `b5fb2412…06485` on both sides.

Script hashes:
- `g1_d1.py`: c59b6d5d…e264
- helpers: `teacher_rescore.py` c91e1848…3e71, `rescore.py` 8cb31773…ec38
- outputs: `g1_d1_packet.json` e02b397e…83e4, `g1_d1_mine.json` 0e520606…de5f

**Q1. Decode / score / stop / dedup: YES.**
- All 274 raw/scored pairs and **7,420 outputs**, totalling **2,200,804 returned tokens**. The total matches SUMMARY.
- Integrity failures: **0**. That covers:
  - raw↔scored roster
  - duplicate candidate ID
  - **every teacher seed equals SHA-256 `stable_seed('teacher',1,pid,att)`**, recomputed independently
  - prompt length equals the frozen length
  - prompt token IDs identical across attempts of a parent
  - scored token IDs equal raw
  - no output over 1,024 tokens
  - completion tokens = body + EOS
  - attempt prefix k−1 present before k
- **Parent order**: the 6,973 eligible parents sorted by `stable_seed('question_order',1,id)` give exactly `frozen_wallets.parent_order`.
- **Usable answers**: the packet (frozen `marked_answer_v1`) has 6,437. My parser finds 6,473 (16 duplicates removed, 61 with no claim).
- **Disagreements: 36, all one-directional.** In every one the frozen parser rejects and mine accepts; there are **0** cases where the frozen parser accepts an answer I reject. They fall into three classes:
  - **E1, `\boxed{X\%}`: 18 cases** (e.g. 05475 ×8 attempts, 01786, 05991, 00515, 02204). This is a known frozen-parser case and must be preserved.
  - **`\boxed{10 \text{ pm}}`-style units: 8 cases** (06036 ×8).
  - **"The answer is:" + display box: 10 cases** (07427, 07304, 06169, 01739, 00964, 07240, 03063). This is a **new conservative false-negative class**. I am calling it **E3**; please list it beside E1 in the parser limitations.
- These disagreements total 0.49% and only make the rule stricter. They are applied identically to every wallet, so they do not bias the policy comparison.
- One side effect: 05475 and 06036 burned all 8 attempts under depth- or breadth-style retries. That cost is real and correctly charged.

**Q2. Wallet replay: YES, an exact match for all 8 wallets.**
- I ran my own wallet loop on the frozen usable labels. The loop:
  - fills full 16-slot actions as active parents plus new ones in parent order;
  - reserves price·M·new + Σ(prompt+1024);
  - stops when it cannot reserve;
  - charges price·M·new + Σ(prompt + completion);
  - retires a parent at 8 attempts or at its usable target (1 for breadth, 4 for depth).
- For every wallet, the **action key sequence, every charge, consumed set, accepted set, total spend (exact Fraction), stop reason and acquired count equal the packet events and summary.**
- The replay draws only on the immutable cache and never on future information.

| wallet | actions | acquired | usable | covered | zero-usable parents | spent/cap |
|---|---|---|---|---|---|---|
| b1 p0 breadth | 32 | 439 | 429 | 429 | 24 | 92.7% |
| b1 p0 depth | 32 | 124 | 469 | 121 | 11 | 94.0% |
| b1 p4 breadth | 7 | 102 | 100 | 100 | 16 | 92.4% |
| b1 p4 depth | 16 | 63 | 240 | 62 | 12 | 91.8% |
| b8 p0 breadth | 269 | 3,524 | 3,436 | 3,436 | 103 | 99.0% |
| b8 p0 depth | 274 | 1,043 | 4,019 | 1,018 | 27 | 99.2% |
| b8 p4 breadth | 64 | 846 | 826 | 826 | 34 | 98.4% |
| b8 p4 depth | 141 | 537 | 2,055 | 523 | 17 | 98.7% |

**Sensitivity check (not a legal replay).** Running the same wallet loop on *my* parser's labels changes the b1-p0-depth wallet and all four b8 wallets, while the other three b1 wallets are unchanged. Because the action paths diverge, the b8 p0 replays hit cache misses: their policy paths ask for attempts the real run never generated. This shows that labels feed back into acquisition, so the frozen parser must stay the single authority. Re-labelling after the fact is not admissible.

**Q3. Identity: YES.**
- `SOURCE_BINDING`: all 23 source files hash-equal to `8bef6411`, the execution source reviewed at G0-main.
- Ledger: 1,109 unit and 1,109 done keys. These are 274 physical batches plus 835 wallet batches (32+32+7+16+269+274+64+141), together with the claim, attempt, intent and terminal records.
- Terminal status is `completed`, with finish time 12:20:18 UTC and an actual cost of 1,404¢.
- RESOURCE_RELEASE shows the D1 app `stopped` at 05:20:23 PDT, with 0 owned containers.

**Notes**
- G1-N1 (E3): see above. Please add it to the parser-limitation table in the paper and PPT materials, and do **not** change the frozen parser.
- G1-N2: this PASS covers **D1 only**. The joint plans need D2, and D2's original parent **failed** at its deadline. Students therefore stay blocked until one of these happens:
  - (a) the D2 repair is reconciled, admitted, completes, and passes its own G1;
  - (b) the **owner** explicitly authorizes a pre-declared one-draw (D1-only) study, as a scope change reported as such.
  Neither is authorized here.

## 2. p008-t1-first-timing-policy-r2 @ e34f9c18 — **PASS (policy/code only)**
- **C1** is implemented as a roster frozen per draw at G1, before any T1 starts. Rosters are extended monotonically; failed or slow members cannot be dropped; and each draw's T8 waits for its own extension. The scope note is correct: C1 does not waive the joint-plan or all-pool prerequisites.
- **C2**: `compute = max(P·c_max, 2048·u_max)` with `u_i = Σsec/256`. The two new tests cover each branch, and 10/10 pass locally. Caps, margin and F/m/K are unchanged.
