# Claude audit 20261014aw — exploratory-exact-suffix-continuation-r1 @ 68c8bad5: **PASS-WITH-NOTES**

Scope: `exploratory-exact-suffix-continuation-runtime-and-numeric`.

**Bound identities (as checked):**
- target `68c8bad5459f752c1d42ba198f3ea68cfef624d2`
- ADMISSION canonical digest `154a7f8307bf06ca16b90acca381a6e98e6a8048415ff1cf0348311e1d8a1f6d`
- `digest(prefix_proofs)` `bfc786cae27577e2d31b6244e5f71a2ca03b101c3f056ffc718b60fae90593bd`
- `digest(budget)` `36b7ea56ec69a6ab353eafb82b466a8c7615854a97216775140738f3735b13cf`
- `source_files`: 47 entries, all bytes equal at target. The 37 original entries are identical to the original admission.

## 1. Prefix reuse: YES
- **Prefix proofs match the preserved archive.** All three PREFIX proofs equal `spec.prefix_proofs[*].binding`. Every raw and scored file sha in them equals the bytes I extracted from the preserved archive (bdf2ffd3) and reviewed in 20261014au: 17 / 9 / 5 batches, offsets 272 / 144 / 80, and exactly one unacknowledged last batch per run.
- **My independent rescoring.** In au, my own decoder + `first_stop` + `completion_score` had already re-derived all 496 saved events and scores with 0 mismatches. That includes the 48 unacknowledged rows. Those rows never passed the in-worker audit, because the interruption landed inside it.
- **`inspect_prefix` rejects at runtime:**
  - a parent that is not `failed`, or whose claim/terminal/intent/source/plan/admission binding differs;
  - a hole or extra attempt, or any start other than `range(0, offset, 16)`;
  - remote units ≠ local intents;
  - ack ambiguity, or an ack ≠ {count, raw sha, scored sha};
  - any uninventoried endpoint file;
  - an unacknowledged set other than exactly the last batch.
- **Suffix batching.** The suffix resumes at the **same 16-row batch boundaries** (272 = 17 × 16, 144 = 9 × 16, 80 = 5 × 16). Left-padding and bf16 batch composition therefore match what an uninterrupted run would have produced.

## 2. Runtime equivalence: YES
- **Audit body.** `cached_audit.audit_batch` is **text-identical** to `runtime.audit_batch` (diff of the function bodies). The only change is that `reference_event` comes from the reviewed proposal script, which is unchanged since 1a3c910e.
- **Evaluate loop.** Same `GenerationConfig` (greedy, 512, repetition_penalty 1.0, EOS list), same `NativeStop`, `prediction`, journal begin/commit/end and per-batch audit. The additions are a timing file and one extra `journal.commit()`.
- **Lookups.** No `len(tok)` remains inside any comprehension or loop in the new files.
- **Prompts.** Prompts are re-serialized and compared to the frozen ids for all 1,319 rows before generation, as before.
- **Student state.**
  - `ck.load` of the original `checkpoint_0256`, with the manifest equal to the verified one and step / targets / cursor = 256 / 524,287 / 256.
  - `ck.restore`, then an exact `torch.equal` check of every trainable adapter tensor.
  - No optimizer step and no checkpoint write. The training dose is inherited, and the new dose is 0.
- **Instruct weights.** The weights already on the Volume are re-hashed against the pinned size and sha. There is no download path.

## 3. Guards and caps: YES
- **New identities.** Three new physical ids `*_remaining_r1` in campaign `exploratory-continuation-20261014-r1`.
- **Parent linkage.** The failed parent's claim and terminal must equal the bound records. A permanent `suffix_continuation/<logical>` marker is written with `skip_if_exists`, so it can be consumed once only and an identical retry is refused. The 10-key active check re-reads child guard, parent and marker on every journal check, with a 15 s timeout.
- **Entry checks.** The entry requires a published exact HEAD and bytes, all review gates, a stopped parent app, the parent records, no marker, no prior child claim/unit/attempt/directory, capacity < 3 including pending and unmatched containers, and `time + 5500 ≤ deadline`, checked twice.
- **Worker.** stop = min(entry + 4800, deadline − 30), with a hard `os._exit`; platform 4860, startup 600, `retries=0`, single-use, `max_containers=3`. Failure records `failed` with the full reservation.
- **Tests.** `tests.test_exploratory_continuation` passes 14/15 locally. The one error is the torch-dependent checkpoint-restore fixture, which needs torch I cannot install here. Codex's log shows 15/15.

## 4. Budget: YES
- **Per slot.** 5500 s × $4.39520/h = $6.7149 → **672¢**. The rate decomposes as H100 3.95 + 4 × 0.0473 CPU + 32 × 0.008 memory, which reproduces 4.3952.
- **Total.** 3 × 672 = 2,016¢. Adding the original stopped-cost allowance of 700¢ (which is ≥ the lifetime bound 640 and ≥ the delayed meter 544) and other costs of 284¢ gives **3,000¢**.
- **Old claims.** The original 2,478¢ claims stay immutable and are not recycled. Within the project ceiling. Not an invoice.

## 5. Timing (my independent estimate) — note N1
From the parent's per-batch intervals:
- **Instruct:** (174 − 15.7) s / 8,192 lookups ≈ **19.3 ms** per `len(tok)`.
- **Base:** (86 − 10) s / 3,520 ≈ **21.6 ms**.

So the repeated lookup explains almost all of the parent's overhead, consistent with all three stop tracebacks landing in `len(tokenizer)`. The non-lookup residual is about **4–9 s per batch**, not the 2 s the scenario assumes, and the extra commit adds a little.

With a 10 s/batch residual and 400 s setup:

| run | estimate | soft line 4,770 s |
|---|---:|---|
| wrong_teacher_t1 (78 batches × (40.3 max gen + 10)) | ≈ **4,320 s** worst case | ~9% margin |
| wrong_teacher_t1 (mean gen) | ≈ 3,900 s | — |
| base | ≈ 1,700 s | — |
| instruct | ≈ 2,300 s | — |

This is uncalibrated. **Dispatch the student first.** The latest admissible dispatch is 14:00 UTC − 5,500 s = **12:28 UTC (05:28 PDT)**.

## Notes
- **N1 (MEDIUM, timing).** See §5. The student slot has a single-digit worst-case margin. If its generation runs slower than in the parent, it can still fail at 4,800 s with saved batches and no retry. Acceptable under the owner's no-retry rule, but launch now rather than near the window edge.
- **N2 (INFO, disclosure).** After the owner approved the continuation (08:24 UTC), I scored the preserved prefixes (au, ~08:40 UTC). The continuation design, inputs and arms were fixed before that, so no decision used partial scores. The final merged report should still state that prefix results had been viewed before the suffix completed.
- **N3 (INFO).** Final merged results = parent prefix (including the 48 originally unacknowledged rows) + child suffix. Report them as one exploratory endpoint per run with the split recorded. Keep the parents `failed`.

Verdict: **PASS-WITH-NOTES** for the exact runtime, numeric, prefix and budget binding above.
