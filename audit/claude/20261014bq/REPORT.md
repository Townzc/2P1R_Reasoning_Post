# Audit 20261014bq: P009 P0 complete engine-parity A2 (actual result)

- **Request:** `p009-p0-entry-repair-complete-A2-r1`
- **Scope:** `p009-p0-complete-engine-parity-A2`
- **Target:** `26d7cff6fe2b305542c70a3de1713d42ee87f015`. The request was recorded at `0715a38f`.
- **Packets:**

| Packet | Manifest SHA-256 | Matches request |
|---|---|---|
| `reports/p009_20261014/p0_entry_repair_complete_v1` | `76695a90eb05bb481905254098dd78e8e3cde04d633d96d503d1732b9c732ce7` | ✓ |
| `reports/p009_20261014/p0_entry_repair_actual_gate_v1` | `9dfd3559bd89c1404226d9b2a5d9d36a06e2ab058c6482b2d4c77a9b11780fc0` | ✓ |

## Decisions

The raw-data and lineage check passed. The scientific gate did not, and needs an owner decision. I report the two separately, as the request asks.

1. **Raw, lineage and accounting: PASS.**
   - My independent replay reproduces every count and both frozen gate decisions exactly.
   - All lineage, fence and budget bindings check out.
2. **Scientific gate: NOT PASSED. P0 does not establish engine comparability.**

   | Endpoint | vLLM / HF correct | Δ (pp) | Discordance | Frozen decision |
   |---|---|---|---|---|
   | base_638 | 650 / 638 | +0.910 | 126 / 1319 = 9.55% | **`blocked_unspecified_discordance_case`** (protocol case 4) |
   | correct_969 | 950 / 969 | −1.440 | 77 / 1319 = 5.84% | **`pass_internal_only`** (case 2) |

   Under the frozen protocol, case 4 "fails closed for review". **All later science (P1–P3, G0, Stage 1) therefore stays blocked until the owner explicitly resolves case 4.** Neither endpoint is `pass_comparable`.

## Independent replay

### Inputs

- I extracted `original_fast_projection.tar.gz` (`542253b5…`).
  - All 63 members match `PROJECTION.json`.
  - The omitted items are `intent.json` and the bundle wrappers, as disclosed.
  - All 18 manifest entries match.
- The 2,382 new rows (`base_638` offsets 256–1280; `correct_969` offsets 0–1280) were merged with the immutable inherited 256 rows, `base_638/raw/0000.json` SHA `142defc1…`. This equals `parent_raw_sha256` in the envelope and in `result.json`.
- The HF reference maps are byte-identical to the frozen `HF_REFERENCE_OUTCOMES.json` that I independently verified earlier (CPU G3).

### Method

I ran my own decoder `p0_a2.py`, built on my own BPE byte map. It applies the target's frozen `first_stop` (EOS 151643, cap 512) and `completion_score`, then `gates.parity`.

### Results

| Endpoint | Checks | Logical stops | Backend stops |
|---|---|---|---|
| base_638 | coverage 1319/1319; 0 duplicates; 0 prompt mismatches; 0 EOS anomalies; 0 incomplete | 985 native_eos / 291 new_problem_boundary / 43 length_cap | 1021 stop / 298 length |
| correct_969 | same: all clean | 1272 native_eos / 47 length_cap | 1272 / 47 |

- The single inherited EOS-at-cap metadata tie is classified `native_eos`, as frozen.
- Correct counts are 650 and 950. Delta counts are +12 and −19; discordant counts are 126 and 77.
- **Every number equals the local oracle and `RESULTS.json`.** Technical unknowns are 0 and there were 0 training updates.

## Lineage, fences and budget (bo N3 closed)

- **Ledger.** The original eager and fast parents remain `failed` with 248¢ and 252¢ terminals. The fast parent's continuation marker points to child claim `52e21ac1…`.
- **Dispatch.** `entry_schema_repair_dispatch/p0_fast_remaining` exists, with provider `ap-qifF5xCCz1p7jnLZPqLgnL`, 2,382 permitted outputs, 256 inherited and 0 retries.
- **Child run.** Exactly one claim and one attempt, 11 unit/done pairs, and a completed 252¢ terminal.
- **Intent data hash.** `data_sha256` `81f06c34…` is the same nested input manifest digest as the parents' intents, so the repair bound the correct inputs.
- **Gate projection.**
  - The release flags equal my bo decision exactly:
    - spec `996f6603…` and target `c12f7b3c`;
    - report SHA `7b06550b…`;
    - all four boolean flags true;
    - preclaim proof `87c88241…`;
    - caps 2000 / 11000;
    - owner amendment `cc668683…`.
  - Budget: 752¢ prior + 252¢ slot; the settlement release was not used. Project upper estimate: 26,070¢ + 11,000¢ ≤ 45,000¢, which is a disclosed engineering estimate.
  - The report commit `1708a34f` contains the bo report with the same bytes as `6a6f3e60`.
- **Providers.** All four apps are STOPPED with 0 owned containers. The new app ran 15:37:15–15:48:21 PDT.
- **Timing.** The worker ran 293.6 s before packing. New batches took 10.8–13.8 s, setup took 72.7 s and 69.2 s, and every forecast was admitted (maximum predicted 725.6 s against the 1,170 s line).

## Science-signal check (what the outcome means)

- **base_638: churn, not bias.**
  - The discordance splits 69 vLLM-only-correct vs 57 HF-only-correct (two-sided sign test p ≈ 0.33).
  - The marginal gap is within 1 pp, but about 1 in 10 questions flips under greedy decoding. This fits bf16 kernel-level divergence on a low-margin base model. It is not a systematic accuracy shift.
  - Discordance is 12.1% on the inherited rows 0–255 and 8.9% on rows 256+. No inherited-row artifact is evident beyond normal question variation.
- **correct_969: a modest one-sided shift.**
  - The split is 29 vLLM-only vs 48 HF-only (unadjusted p ≈ 0.04), so vLLM scores this merged checkpoint about 1.4 pp lower.
  - This is a disclosed descriptive pattern. I am **not** inferring a bug, and I offer no cause.
  - One possible contributor (unverified) is the bf16 LoRA merge path versus HF's evaluation path.
- **Practical reading.**
  - vLLM and HF numbers **must not be mixed** in any comparison. In particular, P009 vLLM results must not be placed directly against P008 HF accuracies.
  - What P009 itself needs (G0, Stage 1 and Stage 2 contrasts) is all measured within one engine and one frozen configuration. The protocol's internal-only rule (case 2) already covers that use.
- **Owner decision required for case 4.** The protocol leaves this case open on purpose, so I am not resolving it myself. The options are:
  - **(a)** Treat base as internal-only, like case 2. All P009 endpoints are then vLLM-only under `high_throughput_v1`, with no cross-engine contrasts, and the discordance is disclosed. *This is my recommendation*: it matches how P009's gates are actually computed, and it costs nothing.
  - **(b)** Investigate the engine difference before continuing, for example by re-running HF on a sample of discordant items. This costs extra budget and time.
  - **(c)** Stop P009 here.
- **Not affected:** the 4% threshold was an ex-ante draft value. This outcome is not a reason to relax it retroactively under any other label.
