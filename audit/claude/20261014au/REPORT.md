# Claude audit 20261014au — exploratory-owner-stop-preservation-r1 @ bdf2ffd3: **PASS** (preservation) + reviewer-side partial-prefix scoring (exploratory)

## 1. Preservation: PASS
- **Packet.** MANIFEST covers 33 files, all sha and byte counts exact. The archive `saved_evidence.tar.gz` has sha `4e628d12…`, 686 members, all safe regular files.
- **Archive vs. local manifests.** For each run, the archive equals its LOCAL_MANIFEST byte for byte (0 hash mismatches). The only exclusions are the disclosed `intent.json` ×3 and the private `checkpoint_0256/state.pt`.
- **Totals.** LOCAL_MANIFEST totals **690 files / 231,420,287 B**. LOCAL equals REMOTE_LISTING_BEFORE (names and bytes), and BEFORE equals AFTER for all three runs.
- **Ledger.** Each run has exactly one claim (826¢) and one attempt. Each terminal is `failed` (826¢), with `claim_sha256 = digest(claim)`. 104 keys in total.
- **Provider.** All three apps are STOPPED at 01:05:25–31 PDT, with 0 containers.
- **Owner stop.** The owner's stop answer is recorded verbatim. No retry, no new call, no extra budget.
- **Student state.** 256 updates, 524,287 targets, sha `45d38712…`. This is a **public proof only**; I did not read the binary.

## 2. Independent decode and scoring of every saved raw row (reviewer-side, exploratory)
Method:
- My own byte-level BPE decoder (frozen tokenizer.json), applied to every saved raw batch.
- The frozen `first_stop` re-derivation: EOS normalized as in the runtime, the special-token set computed with **one** vocabulary-size read.
- `completion_score` with the frozen `marked_answer_v1`.

Results:
- **0 stop-event mismatches and 0 score mismatches** against the saved events and scored records, across 272 + 144 + 80 rows, including the 3 × 16 unacknowledged rows.
- The saved rows are exactly the **first n questions in official test order**. That is a fixed prefix, not a selected subset.
- The same scorer also removes any parser/decoder doubt about the earlier timing story: all saved outputs are well-formed (base: 265 EOS / 4 boundary / 3 caps; Instruct: 135 / 0 / 9; student: 76 / 0 / 4).

| run | rows (acked) | correct | acc. | base 0-shot, same prefix | P008 969 / 965 students, same prefix | paired Δ vs 969 student [95% boot] |
|---|---:|---:|---:|---:|---:|---:|
| base_4shot | 272 (256) | 168 (157/256) | **61.8%** | 51.1% | 76.1% / 75.0% | −14.3 pp [−20.2, −8.5] |
| instruct_0shot | 144 (128) | 97 (84/128) | **67.4%** | 50.0% | 74.3% / 75.0% | −6.9 pp [−14.6, +0.7] |
| wrong_teacher_t1 | 80 (64) | 59 (45/64) | **73.8%** | 48.7% | 75.0% / 73.8% | −1.3 pp [−10.0, +6.2] |

- Base 4-shot vs base 0-shot on the same 272: **+10.7 pp [+4.0, +17.6]**.
- Bootstrap: paired over questions, 10k resamples, seed 20261014. These are **prefix-conditional** intervals, not full-test estimates.

## Science-signal check
1. **"SFT mostly teaches format" needs revision.** Four exemplars move the base from 51% to 62% on this prefix. That is roughly **45% of the 0-shot → SFT gap** (51 → 76). SFT adds a further ~12–14 pp beyond 4-shot prompting.
   - So the gain is not *only* prompt format. Whatever SFT teaches, it is learned from about 100 answers and saturates.
   - The exemplars are terse GSM8K references (`<<…>>`, `####`). A CoT-style few-shot could close more of the gap. Untested.
2. **The official Instruct model does not beat our 100-answer students** on this prefix (67.4% vs 74–75%; 9/144 length caps).
   - Caveat: this is the Math-style system prompt on the general Instruct model, with a 512-token cap.
3. **A student trained on 429 wrong-answer teacher outputs (101 questions) matches the right-answer students** on 80 questions (73.8% vs 75.0% / 73.8%).
   - Very small n. ~40% of the "wrong" set sits on label-error or ambiguous questions (see 20261014as N1).
   - Direction is consistent with "structure/style, not answer correctness, drives the SFT gain here". Not a causal claim.
4. **Combined reading for the midpoint.** In this setting the SFT gain is about *how to answer* (style and structure beyond a 4-shot prompt), is insensitive to answer correctness, and saturates with ~100 examples. That is why allocation cannot matter here.
   - Next: a setting where content is the bottleneck.
   - Full-test numbers need the repaired continuation the owner is considering. The preserved prefixes must be kept, not regenerated.

Notes: this partial scoring is a reviewer analysis of preserved evidence, **not** an admitted endpoint result. The packet's "no partial accuracy reported" stance is unchanged.
