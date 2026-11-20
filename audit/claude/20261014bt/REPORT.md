# Audit 20261014bt — P009 funded Stage 0 generation runtime v2 (runtime + numeric)

- **Request:** `p009-stage0-generation-funded-v2-r1`
- **Scope:** `p009-stage0-generation-funded-v2-runtime-and-numeric`
- **Target:** `974efcbf3c6eae6034828ef11c78831cb97dea46`
- **Manifest:** `reports/p009_20261014/stage0_generation_runtime_preflight_v2/MANIFEST.json`, SHA-256 `8e1d95a666119836d47553a0349319303381add9bb9bb5a2a1c7ec0a64e7dfab`. All 57 entries match.

## Decision: **PASS-WITH-NOTES**

Bound fields:

| Field | Value |
|---|---|
| `spec_sha256` | `e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24`. I recomputed `digest(ADMISSION)`. |
| `source_files` | The 34 entries of `SOURCE_BUNDLE.json`, all recomputed from the target. The 23 core files accepted in 20261014bs are byte-identical. There are 11 new v1/v2 entry, binding, contract, engine, runtime, audit and io files. |
| `first_paid_batch_exceptions_accepted` | **3**: one first 256-row batch per model lifetime, inside the original rosters, never repeated. |
| `total_new_reserved_cents` | **1637** |
| `owner_budget_amendment_sha256` | `4e705c0024e34516a6b71ddf574cb285a1973b4570d466168665199461cf440a`. This is the file SHA of `OWNER_AUTHORITY.json`. |
| `sampling_constructor_proof_sha256` | `3398a05652dbc7f5ce8ea333cb9a054e04c9bd1b31c2fb9b2d7f5a086a903900`. This is the file SHA of `ENDPOINT_CONSTRUCTOR_PROOF.json`. |
| `isolated_wheel_constructor_evidence_accepted` | **true** (see N2) |
| `internal_only_amendment_sha256` | `4f2a56f3e794fd4182e1d9e36c30af0c09c0d6751dea157a3abd34918abf2872` |

This review admits the exact v2 runtime for upload, readback, gates and the three once-only dispatches, subject to their own fresh checks. It does **not** admit P1, G0 or any scientific result.

## Checked

### Owner budget

The owner directly added $20 to Stage 0, specifically for Stage 0. This answers 20261014bs N1.

- New caps: Stage 0 $40, P009 $130. Stage 1 ($50), Stage 2 ($35), unallocated ($5), the project limit ($450) and the protected amount ($50) are unchanged.
- The binding checks `project_prior_upper ≤ 32,000¢`, so 32,000 + 13,000 ≤ 45,000.

### Science unchanged

`stage0_generation_contract_v2.py` differs from the core contract only in `SLOTS` and the caps. These are unchanged:
- datasets, hashes, sampling, transport checks and the forecast formula;
- the engine kwargs: the reviewed `high_throughput_v1`, including `generation_config="vllm"`;
- the 14,450 requests.

### Numbers (recomputed)

Reserve per slot is `cost(worker + 700) + 20`:

| Slot | Window | Reserve |
|---|---|---|
| teacher | 7,900 s | 985¢ |
| qwen | 2,500 s | 326¢ |
| olmo | 2,500 s | 326¢ |
| **Total** | | **1,637¢** |

- Prior reservations 1,004¢ + 1,637¢ = 2,641¢, which is ≤ 4,000¢, leaving **1,359¢** unreserved.
- The 80% rule's bases are 2,996¢, 2,011¢ and 1,685¢. The cost test never binds before the time test does: teacher worst case is `cost(7,870) + 20 = 981¢`, which is ≤ 985¢ and ≤ 0.8 × 2,996¢.
- Under the frozen forecast, the largest first batch each worker can admit is about **128 / 127 s** for the teacher (70 / 120 s setup). Under the old caps it was about 37 s. It is about **291 s** for Qwen and **94 s** for OLMo.

### G0 pairing (closes 20261014bs N3)

`G0_endpoint_bindings` records three pairings:
- NC: teacher_gsm_zero vs P0 base 650;
- S1: teacher_math_zero vs qwen_math_zero;
- S2: teacher_gsm_zero vs olmo_gsm_zero.

All three use the same task, greedy decoding and the same cap. The prompt formats are disclosed: native teacher chat vs native student raw. The S1 parser requires the real P1 scorer and its adjudication before G0 can be computed.

### Static key check (the defect class I missed in bl)

I parsed every constant `spec[...]` and `spec.get(...)` key path in the v2 entry, binding, runtime and engine files against the actual ADMISSION. **No path is missing.**

Model `remote_path` and file manifests exist for all three models (7, 9 and 10 files). The inputs list exactly the seven frozen files. `required_P0_records` has 18 entries, and `P0_app_ids` has 4.

### Fences

**Local entry checks, in order:**
1. The published HEAD equals the remote branch, and no runtime bytes are unpublished.
2. The full set of reviewed reports is bound.
3. The budget snapshot is no more than an hour old.
4. The canonical receipt directory is used, under a dispatch lock.
5. `require_unused`, which rules out:
   - unknown campaign records;
   - any prior claim, intent, terminal, dispatch, attempt or unit for this run;
   - an earlier slot without its dispatch marker;
   - an earlier terminal that did not complete;
   - out-of-order dispatch.
6. Cross-campaign dataset fences must be absent, which also blocks the retired 27-source candidate.
7. The remote run directory must be absent.
8. The four P0 apps must be stopped with 0 owned containers.
9. No more than three workers may be occupied.
10. The full window must still fit.

After these checks, it writes the permanent `skip_if_exists` dispatch and dataset fences, then calls `spawn` exactly once.

**Worker checks:**
1. Re-validates the release and the source bytes.
2. Requires both fences to equal the marker.
3. Re-checks the P0 lineage.
4. Registers and admits under a hard timer that covers imports.
5. Writes create-only evidence.
6. Settles with a failed terminal at the full reservation.

### bs N2: SamplingParams constructor

- `wheel_sampling_params.py` has SHA `8219442773ae…`, the same as the claimed module from the pinned wheel (`3861c75f…`, 438,217,982 bytes).
- In that module, `top_k < -1` raises, so −1 is accepted. Greedy decoding normalizes `top_k` to 0 and `top_p` to 1. Seeds are accepted.
- Run r1 failed only on its own fixture's assumption that greedy keeps −1. That failure is preserved and disclosed. Run r2 built all 5,457 endpoint objects successfully. Together with r1's 8,993 procurement objects, every original parameter set was constructed.
- **In addition, v2's engine constructs every SamplingParams with the real installed Linux package *before* `LLM(...)` loads the model.** A rejection would therefore cost only the container start, not a model run.
- Together these close N2. This is not a Linux, V1-sampler, CUDA or throughput test, as the packet states. I also have not verified that V1 treats `top_k=-1` as "disabled" for the sampled procurement. The constructor accepts it, and the docstring says 0 disables, so a reviewer should confirm from the first-batch environment record that the procurement objects keep `top_k=-1` and that the outputs are diverse.

## Notes

- **N1 — not all fixtures could be reproduced here.** Four of the 10 funded fixtures read private `.local/p009_20261014/r1/*ACCEPTED.json` files, so I could re-run only the other six (all pass). The retained log shows 10/10. This is not a blocker, because I checked the logic they cover directly.
- **N2 — module authenticity.** I could not re-download the wheel (package indexes are blocked here). I accept the packet's PyPI SHA readback together with the "GitHub tag module identical" claim.
- **N3 — worst-case spend.** The teacher can now run for up to 2 h. At about $4.4/h of metered H100 time, the actual charge stays below the 985¢ reservation. With 1,359¢ still unreserved, one failed slot could in principle be replaced, but only by a new owner-approved, reviewed plan. There is no automatic retry.
- **N4 — concurrency.** Up to three workers may run at once, in the fixed reservation order. Every reservation is committed in full up front, so concurrency does not change the budget arithmetic.

## Science-signal check

There is no outcome yet. Key early checks once the teacher's first batches land:

1. **Batch time** against the about-127 s break-even.
2. **S1 answer length** (be N1): the mean must be ≤ 655 tokens over the first 3,200 attempt01-correct answers. This needs P1 scoring, but the raw token lengths give an immediate early read.
3. **Procurement diversity**: per-request seeds should give distinct samples for repeated attempts of the same problem.
