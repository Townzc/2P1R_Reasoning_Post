# Audit 20261014cb: two NC students, exact runtime and timing numeric review

- **Request:** `p009-stage1-NC-runtime-and-numeric-r1`
- **Scope:** `p009-stage1-NC-exact-runtime-and-timing-numeric`
- **Target:** `22b02e313ef38581fb715a8273131f0be3b98c35`
- **Manifest:** `a773e4f956e1d625bf0088efd8c65ac8684372e230ab1b1246763237bed96ba5`. All 137 entries match.

## Decision: PASS-WITH-NOTES

| Field | Value |
|---|---|
| `source_files` | The exact 42-entry map in `ADMISSION.json`. Every repository file at the target hashes to it. All 22 files of the accepted scientific core (by) are unchanged. The new files are the Modal entry, binding, contract, runtime, training process, guards, I/O and audit scripts. |
| `spec_sha256` | `748a7ab00a4fa9cd0b7efd126750f96e323837e672532c89bf42c65bc88f9db4` (canonical digest of ADMISSION, recomputed; the file SHA is `610b73af…`) |
| `timing_sha256` | `d7fab8a49f8ea717375bcb1066d71050754d82757c5cc8d18f10abb1ddb1e376` (recomputed) |
| `input_basis_file_sha256` | `af7149bd26f0a46762f1a108e9ff6c9e6f1c3dadb9d9b4532aec6319f7b4be6a` (equals by) |
| `input_archive_file_sha256` | `266fde7c700a5360594163162f24b662d04c51a306ec645445223c479c6ce92e` (equals by). All 9 `inputs` SHAs equal the files I verified in by. Both configs (plan `fcc25268…` / `84d8d19f…`, rows `58e83308…` / `7e58f9ce…`) match. |
| `all_18_training_hosts_included` | `true` |
| `uncalibrated_timing_proxy_scope_accepted` | `true` |
| `training_process_exit_before_vllm` | `true` |
| `new_reserved_cents` | `1310` |
| `first_paid_measurement_exceptions` | `0` |

## Timing proxy: independent recomputation

**Training blocks.** From each of the 18 hosts' original `TIMING_READ_METADATA` I took, for every `training_block_*`, the completed − intent mtime. To that I added the pad 2 + 2 × that host's `maximum_block_boundary_seconds` + its guard `max_seconds`.
- This gives 1,184 blocks: 8 T8 hosts × 128 plus 10 T1 hosts × 16.
- The sorted vector equals ADMISSION `timing.training_block_seconds` exactly.
- The maximum is **43.307481 s** (`d1_b8_p0_breadth_t1`).
- Per-host maxima range from 26.3 to 43.3 s, and every slow host is retained.

**Endpoint.** The 11 P0 batch intervals are 10.81–13.79 s. The failed-prefix proxy of 20.4121 s is included and is the maximum. It is labelled as a proxy, not a completed batch.

**Scenario.** 1.2 × (43.3075 × 64 + 20.4121 × 6 + 600) = **4192.9820 s**. That is within the 4470 s soft limit and the 4500 s hard limit. The full window is 5200 s.

**Forecast and cost**
- Rate: 0.00122044 USD/s, the same constant as the accepted Stage 0 and P0 contracts (H100 + 4 CPU + 32 GiB).
- Reserve: ceil(5200 × 0.122044) + 20 = **655 ¢** per slot, as stated.
- Forecast: ceil((4192.98 + 700) × 0.122044) + 20 = **618 ¢**. It passes the 80% stage condition for both slots: 5 × 618 ≤ 4 × 5000 and 5 × 618 ≤ 4 × 4345.
- 2 × 655 = 1310 ¢ out of the Stage 1 cap of 5000, leaving 3690. The $5 unallocated reserve is not borrowed.

**Does the proxy transfer?** I judge it adequate and probably conservative:
- The P008 T8 hosts reached 2,097,0xx targets at update 1024. That is the same 2048-targets-per-update density and the same D1 GSM8K corpus as NC.
- The P008 block intervals include extra checkpoint and evaluation work, so they overstate.
- The P0 endpoint intervals were eager-mode runs of the base model. Base outputs often run long, while SFT students usually stop at EOS. The Stage 1 engine also uses CUDA graphs.

**My cost estimate (in-worker).**
- Typical case: 64 × ~35 s + 6 × ~12 s + about 250 s setup/merge/engine ≈ 2,600 s per student, or ≈ $3.2 each and ≈ $6.4 for both.
- Worst case: the 655 ¢ reservation each.

## Code review (runtime)

**Entry (`modal_stage1_nc.work`)**
- The image binds `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `VLLM_USE_V1=1` and offline HF. This closes by N1.
- Container: `H100!`, cpu 4, 32 GiB, timeout 4560, retries 0, single-use.
- The 4500 s hard timer starts at entry and kills child processes.
- It checks source bytes against the spec, the permanent dispatch and logical fences, and the required records. It then claims a slot and writes failure and manifest records on any exception.

**Local entrypoint**
- Refuses to dispatch unless HEAD equals the published remote and the bytes are published.
- Requires all five review reports, a budget snapshot no older than 1 h, and the canonical receipt directory.
- Under the dispatch lock it checks: no prior remote directory, no logical fence, the 7 predecessor apps stopped with 0 containers, pending/unknown containers counted against 4, and that the full 5200 s window fits before the deadline.
- The fences are written skip-if-exists before `spawn`. `call.get()` runs outside the lock.

**Training (`stage1_nc_training_process.child`)**
- It asserts the CUBLAS setting before importing torch, and requires `set_num_threads(4)` and exactly one H100 ≥ 75 GB.
- Base and tokenizer must be the same verified directory, and the inputs are hash-verified. This closes by N3.
- The config must equal the saved config and the recipe.
- It calls the accepted `train_and_merge` once.
- A per-block forecast runs at every 16-update boundary, using prior plus new full blocks and keeping the maximum.
- It requires exactly 64 measured full blocks.

**Process order (`training_once`)**
- Receiving `trained` is not enough: the process must also `join` with exitcode 0 before `TRAINING_PROCESS_EXITED.json`.
- Only then is the endpoint child spawned on the merged directory, which serves as both model and tokenizer. Its manifest is verified, and it includes the saved tokenizer.

**Endpoint**
- Each batch runs a forecast and guard check.
- The unit intent is written skip-if-exists before send.
- Raw output is dumped and committed **before** `transport_checked`.
- Transport rules: EOS only at the end; a short output with no EOS is rejected; only an exact-512 length boundary is allowed.
- There is no scoring and no resend.

**Tests.** I ran 24 of the checks here and all pass: contract 6/6, runtime 8/8, entry body 10/10. The single state-oracle test module imports torch, which this sandbox lacks (no PyPI), so its 3 fixtures were not run here.

## Notes
- **N1 (setup headroom before block 0).**
  - With the constant 1.2 × 600 allowance still counted at block 0, the first block is admitted only if elapsed ≤ 4470 − 4193 ≈ **277 s**.
  - Before that point the worker hashes the 3.09 GB base twice (parent `verify` and child `verify`), loads the FP32 model and re-tokenizes the corpus.
  - Accepted Stage 0 workers spent 74–89 s outside their measured batches. I therefore expect about 100–200 s here, so this likely passes.
  - If a slow volume read pushes it past 277 s, the slot fails closed before any update (cost under $0.5), but the slot is permanently consumed and would need an owner disposition. I accept the design as registered and only flag it. I do **not** propose loosening any cap.
- **N2.** The merged BF16 model lives only in container tmp. The complete 1024 adapter, optimizer and RNG state is persisted. That is sufficient for NC, which feeds no Stage 2.
- **N3.** The new full oracle (`scripts/audit_p009_stage1_nc.py`) is code-reviewed here at the request level only. Its correctness on real outputs belongs to the later outcome A2.

## 科学信号检查 (science-signal check)

No outcomes yet. These two NC students are the preregistered negative control.
- If Δ(3200−400) ≥ 5 pp, the design itself creates a slope and the study stops (§5.3).
- A flat NC result is what P008 predicts, and it is required before S1 is interpreted.
