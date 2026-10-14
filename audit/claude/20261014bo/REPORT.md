# Audit 20261014bo: P009 P0 pre-claim entry-schema repair, read-only adapter, and result publisher

**Target:** `c12f7b3cd9ceaa5b9120ffc0280328df568a14b6`

## Requests covered

| Request | Scope | Manifest SHA-256 |
|---|---|---|
| `p009-p0-entry-schema-repair-r1` | `p009-p0-fast-unattempted-remainder-runtime-and-numeric` | `0563be9d858befe1d656c493342c548d0bf7c73d8ec05aa13752ca017ddc53e7` ✓ |
| `p009-p0-entry-repair-readonly-r1` | `p009-p0-fast-remainder-readonly-observation-and-failed-preservation-code` | source `scripts/p009_p0_entry_repair_readonly.py` `7af71fe8a196c7a4fb6c7fe19a715ee8fac98a31a467b8d89a30d64d118694cd` ✓ |
| `p009-p0-entry-repair-result-publication-r1` | `p009-p0-fast-remainder-result-publication-code` | manifest `0b65f4cccf81486d3f10539c9b5588ad5a3e81f95676b30a5128e33e9b8fab2e` ✓; source `d5d08c20c3ee10585cd7360559af0f4ea45c3142928a1c9d62d8dfe01a80ecb3` ✓ |

## Decisions

**1. Entry-schema repair (runtime and numeric): PASS-WITH-NOTES.**

Return values:

| Field | Value |
|---|---|
| `decision` | `PASS-WITH-NOTES` |
| `target_commit` | `c12f7b3cd9ceaa5b9120ffc0280328df568a14b6` |
| `source_files` | the 38 entries of `SOURCE_BUNDLE.json`; all 38 recomputed from the target ✓ |
| `spec_sha256` | `996f66034e889b0ac22cf2e1ae5173712b94b8187f1a3939f300201af4ed6df1`; `digest(ADMISSION)` recomputed ✓ |
| `parent_preservation_sha256` | `608c33154abda7178a0413c78e26e4a004c310c7ac4e0edcb1138c46493022eb` |
| `bounded_suffix_only` | `true` |
| `native_eos_cap_metadata_accepted` | `true` |
| `same_frozen_logical_stop` | `true` |
| `preclaim_entry_schema_repair_accepted` | `true` |
| `preclaim_proof_sha256` | `87c882413b1e8c14367658a6f72a6c00ef5e228e43f744398d938d7fbbd30e02`; file SHA of `ZERO_WORK_VERIFIED.json` recomputed ✓ |
| `stage0_cap_cents` | `2000` |
| `experiment_cap_cents` | `11000` |
| `owner_budget_amendment_sha256` | `cc668683e84e29e321a842b8884f68aa6d59fcd4a411e29ec38df0cb53aea963`; file SHA recomputed ✓ |

**2. Read-only adapter: PASS.** The diff against the accepted `f9ffa532` changes only four things:
- the root and spec paths;
- `validate_repair_release`;
- `DISPATCH_KEY` added to the observed keys;
- the pre-claim failed app added to the provider roster.

**3. Result publisher: PASS.** The diff against the accepted `299c662b` changes only five things:
- the new root, spec and PUB paths;
- `validate_repair_release`;
- a required STOPPED-0 proof for the pre-claim failed app (`PRECLAIM_PROVIDER.json`);
- a new `ENTRY_REPAIR_PROVENANCE.json`;
- caps of 2000/11000 and the README text.

Oracle, parity and full-endpoint checks are unchanged. The publisher still copies every parity outcome, including stop and blocked.

## What I verified

### The original failure was a real, deterministic defect

`ORIGINAL_ENTRY.py` (SHA `75eea6ba…`) is byte-identical to the `modal_p0_fast_remaining.py` that I accepted in 20261014bl.

- Its admission call reads `data_sha256=digest(spec['inputs'])`.
- The remainder spec (`7e653032…`) has **no top-level `inputs`**; the manifest lives at `spec['parent_spec']['inputs']`.
- The KeyError was therefore certain on the first call.

**This is a defect I missed in bl.** I reviewed the suffix execution core and its numerics but did not trace every key the worker entry reads. That is a reviewer miss, and I own it. To make sure nothing similar remains, this time I parsed (AST) all four entry-path files: the worker/local entry, binding, runtime and remaining contract. I resolved every constant `spec[...]` and `original[...]` key path against the actual ADMISSION. **The only path that does not resolve is the guarded `'inputs' in spec and spec['inputs'] != …` alias check, which is intended.** No other entry-schema KeyError remains in these files.

### Zero-work reconciliation

- The original ledger holds only the identical campaign registration; plan digest `076bee2c…` equals `spec.plan_sha256`.
- There are 0 claims, terminals and units, no model load, and an absent Volume.
- Three apps are STOPPED with 0 owned containers. The pre-claim app `ap-AWwBuFC9C1MSINlMCioi5O` ran 14:37:29–14:43:15 PDT.
- No terminal was fabricated.
- `guard.register` is idempotent (`_same_or_new`), so re-registering the identical plan is safe.

### Scope of the change

- **Spec diff (remainder `7e653032` → repair `996f6603`):** only budget and lineage fields changed:
  - `stage0_cap` 1000 → 2000;
  - `experiment_cap` 10000 → 11000;
  - `parent_reserved` 500 → 752;
  - `original_two_failed_reserved_cents` = 500;
  - `owner_budget_amendment_sha256`, `preclaim_failure`, `reserve`, `schema`, `source_files` and `stage0_remaining`.

  Offsets, the engine kwargs, the 2,382 suffix / 256 inherited rows, 11 batches, 0 bootstrap batches, the 1200/1260/600/1900 s limits, the plan, the parent spec (`1238d0cb…`) and the parent preservation hash are all identical.
- **Sources:** 32 of the 32 original sources are byte-identical. There are 6 new files: the entry, binding, runtime, audit, io and readonly scripts.
- **Runtime:** `p0_entry_repair_runtime.execute` is identical to the accepted `p0_fast_remaining_runtime`, except that `remaining_forecast` is imported from the binding module. Inputs are read from `original['inputs']`, which was already correct.

### Forecast

The formula is unchanged: `elapsed + 1.2 × (max interval × remaining + 300)` must be ≤ 1170.

- The cost limit moved from `0.8 × (1000 − 500)` to `0.8 × (2000 − 752)`, i.e. from 400¢ to 998.4¢.
- In both versions the cost term is non-binding: at most `cost_cents(1870) + 20` ≈ 250¢. **The time gate binds, exactly as before.**
- The budget increase does not relax any timing or science gate.

### Fences

- **Local entry**
  - The ledger must be exactly `{campaign: plan}`.
  - Both failed ancestors and their markers are unchanged.
  - Both Volume directories must be absent.
  - Zero containers must be running.
  - The 4-app roster must be STOPPED.
  - A complete window is required.
  - `DISPATCH_KEY` is written with `skip_if_exists` before `spawn`. Because this key sits under the campaign prefix, any second local attempt fails `registration_only` permanently.
- **Worker**
  - The marker must equal `dispatch_marker(spec, release)`.
  - The nested input manifest must equal the readback before register/admit.
  - The hard timer covers imports and admission, and `finally` cancels it.

### Tests

I ran the 11 new tests here on the target tree (after creating `.local/p009_20261014/r1` for their tempdir): **11 / 11 OK**.

## Notes

- **N1: owner budget amount.**
  - The owner's direct text, "可以提高预算上限，别因为多了一点钱就暂停工作影响进度", authorizes an increase but does not name an amount.
  - The bounded figures ($110 P009, $20 Stage 0; Stage 1/2/unallocated unchanged; project $450 / protected $50 unchanged) are Codex's own allocation, which Codex stated in chat.
  - This is within the owner's words and is conservative. I am flagging it so the owner can see the exact figures.
- **N2: interaction with 20261014bn.**
  - This admission does not use the bn release: 1004¢ is conservatively committed, leaving 996¢ of the 2000¢ cap. That remaining 996¢ already covers the recorded 496¢ P2/P3 plan without any settlement.
  - `closed_budget_settlement.build_settlement` hard-codes `stage_cap_cents == 1000` and the two-app roster. Using settlement under the new 2000¢ cap, or for the third (pre-claim) app, needs a new reviewed version. The bn N1 rule (pass `previous`) still applies.
- **N3: the release gate file is not yet visible.** `budget.*`, `runtime_review.*` with the flags above, and `input_readback` are generated at dispatch and validated by the local entry. The A2 for the actual result must check them in `intent.json`.
- **N4: fail-closed after the marker.** If `spawn` itself fails after `DISPATCH_KEY` is written, the slot is permanently blocked and a new review is needed. I accept this as the intended trade-off.
- **N5: inherited note.** `out.mkdir(exist_ok=False)` followed by `if out.exists()` would write `failure.json` into a pre-existing directory. This cannot happen here because the local entry proves the directory is absent. The pattern is unchanged from the accepted code.

## Science-signal check

There is no scientific outcome yet: the pre-claim failure produced zero outputs. This repair changes no EOS rule, parser, prompt, weight, sampling or merge setting. The next science checkpoint is A2 on the merged 256 + 2,382 rows, using my prepared independent replay (`p0_a2.py`).
