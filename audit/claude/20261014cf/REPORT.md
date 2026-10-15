# Audit 20261014cf: NC guard-intent repair (runtime) + its closeout code

This one report covers two scopes. The owner-proxy decision is a separate comment: #13 comment 6186240160 (event 2026-10-15T06:47:28Z), which approves exactly one new entry call. This audit is independent of that decision and is not waived by it.

## Erratum to cd (my miss)
In cd Part B I checked the replacement binding's `intent()` against the binding and the AST-level tests. I did not run the unchanged `RunGuard.admit` on that intent.
- The guard accepts exactly `{run_id, config_sha256, source_sha256, data_sha256}`, optionally plus the recovery pair. The 49-source binding added `failed_parent_terminal_sha256` and `owner_exception_sha256`, so the real call failed before the claim.
- One real paid entry was used up with no scientific work: about $6.55 is reserved, and the actual cost is the setup/build time.
- From now on, whenever a binding change touches the guard, I will run the real guard on the exact intent.

---

## Part A: `p009-stage1-NC-guard-intent-repair-r1`
- **Scope:** `p009-stage1-NC-preclaim-guard-intent-repair-runtime-and-numeric`
- **Target:** `e8f57a1973cacf7efd508b59df9a94fda1539a1a`. Manifest `34d6e73adda168346e8135ccd7143cf6594f4818909ffcfdc5e66e92a2407b1a`.
- **source_files:** the exact 53-entry map in INDEX `source_binding.source_files`. All 53 hashes were recomputed at the target. They are the 49 entries accepted in cd, byte-identical, plus 4 new files:
  - `modal_stage1_nc_guard_repair.py` `d41aae40…`
  - `stage1_nc_guard_repair_binding.py` `0a14df43…`
  - `scripts/audit_p009_stage1_nc_guard_repair.py` `ddcc529b…`
  - `scripts/p009_stage1_nc_guard_repair_io.py` `b6c05f51…`
- **Bindings:**
  - spec_sha256 `ab01c527ea82d1dd72ad78960bc00709063e3ad22d4e9793ae1d4305540f18b5` (recomputed)
  - timing_sha256 `e3dc389f7cd5f1a6c180d948504870248b0b0d717ee309a43a73a484ad4fa817` (unchanged from cd)
  - preclaim_proof_file_sha256 `4fe19c8e7138a98163a1601bf4cc679920770cf746a494c19ad91a324af27e07`
  - preclaim_manifest_file_sha256 `5c996371ebbaf6233630d12cd47012b8df49fde0a177546574a433667cfae5d1`
  - failure packet manifest `1e7d53c4b4bb93fcfeb9fa5ec81b174c88e125a4ad56ba6ef143920fb27e249e`
  - owner_authority_file_sha256 `c5b2308c5cace6f199b498c4554bc8cf4845de898a3873bcf00e6989364235f3`
- **owner_proxy_comment_sha256:** `d66bec7bb2f5a46782ccf3650cc00e6e005ddd033e52b195f4653611e1b9b947`
  - This is `common.digest()` of the GitHub API object for comment 6186240160, as returned by GET right after posting. The POST and GET objects were identical.
  - The raw GET bytes are saved here as `owner_proxy_comment_GET.json` (file SHA `3c8310ca…`).
  - The comment author is `Townzc`, with association `OWNER`.

### Decision: PASS
- original_guard_four_field_schema = true
- original_fences_and_failed_parents_retained = true
- no_prior_replacement_training_or_endpoint = true
- one_new_entry_call_only = true
- prior_stage1_reserved_cents = 1965
- new_reserved_cents = 655
- first_paid_measurement_exceptions = 0

### Checks
- **The real guard accepts the new intent.** I ran the unchanged `experiments/sft_allocation_midpoint/guard.py` on an in-memory store seeded with the exact `preclaim_records` (campaign plan + the two consumed fences), using the real `PLAN.json`. It is identical to cd's plan.
  - The old 6-field intent gives **`invalid intent fields`**, the same as the real failure.
  - The new 4-field `intent()` is **admitted**.
  - A second admit gives `run already claimed`.
- **Argument flow.** The new entry imports `intent` from the repair binding and passes `intent(spec,run)` straight into `guard.admit`. Before the claim it validates the full spec, every source SHA, the new repair fences = `marker()`, and every `required_records` entry. It also checks the raw proxy-comment bytes against the release.
- **Science unchanged.**
  - `validate()` requires `digest(original_replacement_spec)=35b17552…` and runs cd's `validate` on it.
  - Every spec key except scope, sources, records, apps and reservation must equal the original.
  - `configs[RUN]` equals the original n3200 config: same plan, dose, LR, endpoint and 4500/4560/600/5200 s windows.
  - `stage1_nc_replacement_runtime.py` and `_training_process.py` are unchanged from cd.
  - The oracle script differs only in its import and schema name.
- **Zero work in the failed preclaim call** (`stage1_nc_replacement_preclaim_failure_v1`):
  - `return_error` is `GuardError: invalid intent fields`, and the CLI log projection shows the same at guard.py:207.
  - The ledger has only 3 keys: the campaign plan, the dispatch fence and the logical fence.
  - `ZERO_WORK_VERIFIED` shows no claim, intent, attempt, terminal or checkpoint, 0 updates and 0 endpoint outputs.
  - The remote output directory is `NotFound`.
  - The app `ap-iCt0KOKWNfNojiIzZv1LoM` is `stopped`.
  - No failed terminal was fabricated, and the 655¢ stays reserved.
- **Fences.** Both consumed fences stay in `required_records`. The new keys are `…/guard_intent_repair_dispatch/<run>` and `…/independent_replacement_r1/guard_intent_repair_r1`. `require_unused` blocks dispatch if anything beyond the preclaim records exists.
- **Budget.** Reserved 1965 + 655 = 2620 of 5000¢ for Stage 1, leaving 3035 before this slot and 2380 after. The forecast (4,193 s, 618¢) is admitted. The overnight extra amount is not used.
- **Tests.** I set up the fixture per `TEST_FIXTURE_README`, and 13/13 pass.

---

## Part B: `p009-stage1-NC-guard-repair-closeout-code-r1`
- **Scope:** `p009-stage1-NC-guard-repair-observation-and-pair-publication-code`
- **Target:** `8154c25b3c2300e9d95d70576e95081b11426f3c`. Manifest `9a4f0f216af16552213f9d369edf8a29f68f5e826f9067db68e884fde00d32d7`.
- **source_files** (exact):
  - `scripts/p009_nc_guard_repair_observe.py` `a39fb1c79627f09dd29caf3618ce3f56827d6f99a6007f72696244f57aa00ed5`
  - `scripts/publish_p009_nc_guard_repair_pair.py` `5ea01d95110fee8efd286343041c4778615a0b0919e0bf0d5f35d40539e92e2f`
  - `scripts/publish_p009_stage0_result.py` `708d426fc1097e00e5f8a56b5daa6441c87c25c7eb62b3cf1477fb8d6f94ab26`

### Decision: PASS-WITH-NOTES
- **What changed.** The diff against the ce-accepted helpers adds:
  - the 53-source binding and scope;
  - a SHA check of the preclaim packet manifest and proof;
  - a raw proxy-comment check;
  - `raw_comment_local_path` among the projected keys;
  - a preclaim reference file;
  - 2620¢ in the SUMMARY.
- **ce N1 is partly fixed.** The provider projection is now computed **before** `mkdir`.
- **Unchanged.** The NC400 sibling, the decision call `nc_result(ids, NC400, replacement)` and the archive logic are identical to ce.
- **Tests.** 8/8 new helper tests pass.
- **Note.** `archive_original` and `nc_result` still run after `mkdir`, the same low risk as before. Pair A4 will re-score the replacement's 1319 outputs independently.

## 科学信号检查 (science-signal check)
No new outcome.
