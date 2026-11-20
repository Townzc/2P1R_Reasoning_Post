# CR: ext-4B full training / resume / evaluation runtime (target 10b74e99, request 23ec1bc5)

Reviewer: Claude, 2026-10-22 ~05:55 UTC.
**Verdict: code PASS-WITH-NOTES. Owner decision required before A2/launch: as specified, the run is projected NOT to fit the $45/cell envelope.**

## Code (what I read)
I read in full ext4b_training.py, ext4b_encoded.py, the cost-window part of ext4b_runtime_contract.py, and the reused validate_plan, checkpoint.snapshot/restore and rng_state. I skimmed ext4b_execution, ext4b_path, p011_ext4b_io and analyze_p011_ext4b for structure only; their reused evaluation, decoder and scorer paths were accepted in earlier CRs.

- **Update math unchanged.** The per-step loop is the original one: `accumulate`, clip 1.0, lr from the frozen vector, AdamW step, with the same journal begin/end/commit and a non-finite stop. `validate_plan` enforces q/q+1 whole passes, U = ceil(B/64,000) and the LR vector.
- **Checkpoint and resume are sound.**
  - Every 500 steps the run saves a full snapshot: all trainable parameters, the AdamW state, Python/NumPy/Torch/CUDA RNG, the LR vector, the schedule and the cycle prefix.
  - Resume validates identity, cursor (a multiple of 500), schedule, LR, every AdamW slot, the moment shapes and finiteness, the step count, and the exact checkpoint bytes.
  - The prefix trajectory is copied and checked against the frozen schedule, and the tail after the checkpoint is replayed.
  - Only one infrastructure resume is allowed; scientific failures, hard-timer failures and OOMs are excluded.
- **EncodedRows (lazy view) is acceptable.** Each step it seeks to the needed lines and parses them. `json` encodes dict subclasses through the overridden `items()`, so `digest(encoded)` covers the full rows. Hashing materializes about 1 GB of JSON for 12,096 rows, which is fine on the 96 GiB host.
- **Launcher fix is accepted.** The module-qualified launch plus the local wall-clock watchdog address the forced-answer `ModuleNotFoundError` crash loop.
- Flags: all source flags true **for code correctness**. The numeric-fit flag belongs to A2 and is addressed below.

## Blocking for A2: projected runtime exceeds the money-derived worker time
These are measured A7 (F15) actuals from the owner150 archive:
- Training: 654 updates in 6,462 s of worker time, about 9.9 s per update including cycle overhead.
- Evaluation: 7 endpoint batches totalling about 7,958 s, roughly 2.2 h, for 3,300 rows. A7 rarely stops, which is the slow case.

Projection for each 4×B cell:
- U ≈ 165M / 64k ≈ 2,580 updates, so training takes about 25,500 s (7.1 h).
- Relaxed-pool sequences are about 33% longer, which adds roughly 5–15% to attention cost. Five 500-step full-state checkpoints add more.
- Training therefore comes to **7.4–8.2 h**. Evaluation adds **1.0–2.2 h**, depending on how often the student stops.
- **Total: about 8.4–10.4 h.** The affordable worker time at $45 (with $5 noncompute) and $4.9072/h is **7.97 h**.

**Consequence:** each cell is likely to hit its money timer during evaluation, or even at the end of training. Under the current rule ("only full successful results score"), that would waste most of the roughly $80–90.

**Options for the owner (any one of them):**
1. **Raise the cap** to about $55/cell ($110/pair), which buys about 9.97 h of worker time. That still risks an overrun if evaluation is A7-like.
2. **Cut the evaluation down to what matters.** Run MATH-500 sampled×4 + greedy first, and pre-authorize D2-style scoring of complete MATH-500 endpoints even if AIME/AMC are cut. AIME/AMC are near zero for every fine-tuned cell and are descriptive only. Together with option 1, this makes success likely.
3. **Reduce the dose to 3×B** (9,072×1 versus 3,024×E3). Training takes about 5.6–6.2 h, and with the MATH-first evaluation of option 2 the run fits within $45. Repetition versus new data becomes 3:1 instead of 4:1.

My recommendation is option 2 in every case. Then choose between option 1, which keeps 4×B but needs about $20 more, and option 3, which stays within the $90 pair cap.

**Until the owner chooses, do not launch.** Data construction and the actual-input metadata can proceed. The forced-answer relaunch, after the import fix, also needs the owner's go-ahead, since its first attempt ended without inference and its retry was explicitly not adopted.
