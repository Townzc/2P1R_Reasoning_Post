# Audit 20261014br: P009 P0 owner post-result internal-only amendment

- **Request:** `p009-p0-internal-only-owner-amendment-r1`
- **Scope:** `p009-p0-vllm-internal-only-owner-amendment`
- **Target:** `2d3e1dd13277d556b18a3569cd80c252b112d54b`

## Bindings checked

| Item | SHA-256 | Result |
|---|---|---|
| Packet manifest (`reports/p009_20261014/p0_internal_only_amendment_v1/MANIFEST.json`) | `9fb99f9f54c3794c25fdd88fe74dd461cc0e069f6f7e4e39a1246e871c9f2bcd` | All 5 entries match |
| `AMENDMENT.json` | `4f2a56f3e794fd4182e1d9e36c30af0c09c0d6751dea157a3abd34918abf2872` | ✓ |
| `OWNER_AUTHORITY.json` | `ab9eb85a14d61eb296707b6244ae3a7ed2ad97fd38f00ad0a92add402e1ec378` | ✓ |
| `ORIGINAL_P0_RESULTS.json` | `1b065f68ba45f5e82fff8408597727ec7a5d5a42d4ff9e7c3950336dbaa0b0fc` | Byte-identical to `RESULTS.json` at `original_result_target_commit` `26d7cff6fe2b305542c70a3de1713d42ee87f015` ✓ |

## Decision

**PASS.** The owner-resolved engine-scope blocker is **closed**. Every later actual gate remains pending: P1, P2/P3, G0, G1, the negative control, futility, data/dose, runtime/budget and the once-only checks.

Return values:

| Field | Value |
|---|---|
| `comparison_scope` | `P009_within_vllm_only` |
| `post_result_amendment` | `true` |
| Original frozen decisions (retained) | base_638 = `blocked_unspecified_discordance_case`; correct_969 = `pass_internal_only` |
| Owner-authorized dispositions | base_638 = `internal_only`; correct_969 = `internal_only` |

**The A2 at 26d7cff6 is unchanged.** 20261014bq stands as written:
- the raw, lineage and accounting replay is an exact PASS;
- the scientific gate was not passed as comparable.

This amendment is a scope decision. It is not a retrospective pass, and it is not evidence that the engines are equivalent.

## Checked

### Authority

- The exact quote is my bq option (a), word for word, including "我推荐这个". The owner chose it and sent it directly to Codex after the complete outcomes were disclosed.
- This satisfies the direct-owner rule. My recommendation became an instruction only through the owner's own message, not through my relay.

### Nothing else moved

| Target | Change since `26d7cff6` |
|---|---|
| `experiments/`, `analyses/`, `src/`, `scripts/` | Only `PROTOCOL.md` has a diff: an appended section of 21 added lines and 0 deletions. The original four-case P0 rule is intact |
| Complete-result packet | Empty diff |
| Actual-gate packet | Empty diff |
| `gates.py` | `1543f482…`, unchanged |
| `high_throughput_v1.py` | `539d9cf9…`, unchanged |

### Disclosure

- The discordance figures are stated exactly: 126/1319 (9.552691%) and 77/1319 (5.837756%).
- The amendment requires both the original gate decision and the post-result owner resolution to appear in any report.

### Cost and calls

- The amendment adds 0 model calls, 0 generations, 0 training updates and 0¢.
- No paid replay or calibration is authorized.
- The budget is unchanged: $110 total, with Stage 0 / 1 / 2 / unallocated at $20 / $50 / $35 / $5, the $450 project limit and $50 protected.

### HF numbers

- HF 638 and HF 969 are restricted to historical diagnostics. They can never be a treatment-effect, G0 or G1 input.
- Base 650 is reused only for the same Qwen/GSM 0-shot endpoint, and is never regenerated.

## Notes

- **N1: same endpoint on both sides of G0.**
  - The NC/S2 G0 compares teacher 0-shot against student 0-shot.
  - The teacher's evaluation must use the same vLLM configuration and the *same endpoint definition* as base 650 before the two may be subtracted: prompt family, greedy decoding, max 512 new tokens, frozen `first_stop` and parser. Teacher sampling settings (temperature 0.8, max 1024) apply to data procurement only, never to G0.
  - Each G0 admission should bind both endpoint specs.
- **N2: the 950 is not a P009 learning result.**
  - The correct-reference 950 comes from a P008 checkpoint. It may serve as a disclosed vLLM reference point only.
  - It is not a Stage 1 student and not part of any NC gap.
- **N3: reporting.** Any text that cites P0 must say "internal-only by post-result owner amendment", not "parity passed". This includes the midpoint deck notes: slide 12's note already follows it.

## Science-signal check

No new outcome. The amendment removes the engine-scope blocker without spending anything. The next real signals are:
- the P1 first-100 throughput (bp N1);
- P2/P3 outputs: G0 for NC, S1 and S2, the S1 mean answer length (≤ 655 tokens) and fallback rates.
