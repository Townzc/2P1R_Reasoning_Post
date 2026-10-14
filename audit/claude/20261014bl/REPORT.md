# Audit 20261014bl — Plan A P0 unattempted remainder (EOS-at-cap metadata tie)

- Request: `p009-p0-fast-unattempted-remainder-r1`
- Scope: `p009-p0-fast-unattempted-remainder-runtime-and-numeric`
- Target: `5c5222573dece18fe3fe715ecfa3bdbfec1d2d01`. The 32 sources are byte-identical at HEAD `1593c99a`.
- Manifest: SHA-256 `5e8ded2ae5248015d2d00edeba6e1f32a50d0076d9c39e53c0c12b8d3431d866`
- `spec_sha256`: `7e653032c0eacbe73c920c26de5c82497a11a1152974f0d2fb04d78366e9ccb0` (recomputed)
- `parent_preservation_sha256`: `608c33154abda7178a0413c78e26e4a004c310c7ac4e0edcb1138c46493022eb`
- The original 26 sources are unchanged, and `engine_kwargs` is identical to Plan A (20261014bi).

## Decision

**PASS-WITH-NOTES** for the runtime and numerics.

| Flag | Value |
|---|---|
| `bounded_suffix_only` | **true** |
| `native_eos_cap_metadata_accepted` | **true** |
| `same_frozen_logical_stop` | **true** |

**The budget status in §3 must reach the owner before P2/P3.** It does not block this remainder.

## 1. Failure and the metadata tie, verified independently

I extracted `original_failed_fast_projection.tar.gz` and read `base_638/raw/0000.json` (SHA `142defc1…`, 256 rows):

| Check | Result |
|---|---|
| IDs and order | IDs equal test order 0..255; all prompt IDs equal the frozen parity prompts |
| Stream structure | 189 rows end with a single terminal EOS; 67 rows are exactly 512 tokens with no EOS |
| The tie | **Exactly one tie:** `gsm8k/test/00115`, 512 tokens, the sole EOS at index 511, `finish_reason=length`. No row has a post-EOS token, a duplicate EOS or a short stream without EOS |

This is consistent with the pinned vLLM 0.11 V1 `check_stop`, which tests the length cap before EOS. The configuration itself worked: chunk 1 completed in a ~20 s proxy.

**Scoring stays unchanged.** I confirmed from `analyses/completion_contract.first_stop` (SHA `ea0bc0ec…`, unchanged) that a stream whose first EOS is at index 511 yields `native_eos`, with the answer segment taken before it. That is also what HF `generate` would have produced at P008. The new `p0_stop_metadata.raw_checked` accepts only that exact tie (512 tokens, single terminal EOS, `length`, `stop_reason=None`) and delegates every other row to the original checker. It mutates nothing.

## 2. Remainder

| Item | Detail |
|---|---|
| Rows | 256 saved base rows are inherited from the failed parent, which keeps its missing done-ack; no ack is fabricated. New rows: base 256..1318 (4 × 256 + 39) and correct-969 0..1318 (5 × 256 + 39), 2,382 in total |
| Chunks | Same 256-row boundaries as the original plan |
| Gate | Every new chunk is gated, with no bootstrap exception. The forecast uses max(20.41 s proxy, all new chunks). My projection: setup ~100–200 s + 11 chunks × ≲ 20 s, giving ≈ 400–650 s actual, and a forecast of about 150 + 1.2 × (20.4 × 11 + 300) ≈ 780 s ≤ 1,170 s |
| Lineage | The parent stays failed, with a permanent continuation marker. The eager 128 rows stay excluded and unscored |
| Pooling | Mixing rows from two containers is acceptable and must be disclosed in A2 (as in 20261014bg) |

## 3. Budget signal for the owner (science-schedule risk)

| Item | Reserved |
|---|---|
| Eager P0 | 248¢ |
| Fast P0 | 252¢ |
| This remainder | 252¢ |
| **Total Stage 0 reservations** | **752¢ of 1,000¢** |
| **Left for P1/P2/P3** | **248¢** |

That is not enough for the about 14,450 outputs of P2 + P3 under the current full-window reservation rule, where one worker reserves about 252¢. The ledger permanently counts each failed attempt at its *full reservation*, even though the two failed runs actually used about 100–200 worker-seconds each, plausibly well under $1 combined.

The owner needs to choose one of the following before P2/P3:

- **(a)** Allow reconciling closed failed slots to their **metered** cost plus a lag buffer, once provider metering for those apps is read. This keeps the cap meaningful while not double-charging reservations.
- **(b)** Release part of the $5 unallocated reserve to Stage 0.
- **(c)** Accept that G0 cannot run tonight.

Codex correctly refuses to borrow without approval.

## Science-signal check

No scores. 67 of the first 256 base outputs (26%) hit 512 tokens. That is a property of base 0-shot output, already present in HF; it is not an effect.
