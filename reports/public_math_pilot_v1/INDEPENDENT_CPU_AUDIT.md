# Independent CPU closeout audit — public math pilot v1

The final CPU preparation artifacts are internally consistent within the checks below. **No Qwen model process, GPU preflight, formal training, annotation forward, or generation ran.** This audit does not establish GPU correctness, throughput, memory fit, complete-pilot feasibility, or any method performance.

The authoritative data freeze is [release_v1/manifest.json](../../experiments/public_math_pilot_v1/release_v1/manifest.json), SHA256 `f7c67a1c523c3ec5dfbd1ae63506a9ce91dd03683643dcf3b7a72c70b16fa370`. The earlier `795a7bb4…` candidate is superseded and is not the final release.

## Checks actually performed

- Verified all **16** manifest-listed file SHA256 values and byte counts, all three source bindings recorded by the data manifest, and all **12** byte-preserved Qwen vendor files against their provenance manifest. The upstream evaluator commit is `a45202bd16f1ec06f433442dc1152d0074773465`. No evaluator driver or PythonExecutor is vendored.
- Independently reconstructed connected components from all **989,909** declared candidate pairs: **62,060** accepted edges and **927,849** rejected candidates. Every reconstructed root matched the **820,892** published question-node components. Verified all **859,494** source-row memberships. There are **775,342** Numina components; **503** source rows in **85** source components touch a benchmark. The structural files were first checked in a preserved candidate and then verified byte-identical in the final manifest.
- Checked the actual **4,096** pilot rows, **512** dev rows and **20,000** future-pool IDs. Pilot IDs equal the first 4,096 pool IDs; dev/pool contain **20,512 distinct groups**, with no overlap. Recomputed each selected group ID from its complete original-row membership and checked that no selected component touches any of the four benchmark identity sets. Both saved split-key orders are sorted.
- Re-encoded every pilot question/reference with the pinned real tokenizer and compared every serialized encoding field and encoded digest. Full and blank prompts share exactly the same response IDs; response supervision includes one terminal **151645**, no added **151643**, and no truncated references. The longest pilot input is **1,969** tokens, below the 2,048 training cap. Rechecked common text eligibility on all **4,608** pilot/dev records. Verified tokenizer/config asset hashes; the model config's context limit is **4,096**, irrespective of the tokenizer's advertised 131,072.
- Recomputed the original-question context census: MATH500 **500**, full MATH test **5,000**, Minerva **272**, GSM8K **1,319**, plus dev **512**. All fit prompt plus 2,048 output tokens within 4,096. Maximum prompt lengths are respectively **825 / 1,370 / 426 / 222**. Full MATH and Minerva were read through question-only projection; no Minerva answers were inspected.
- Re-normalized all **500 MATH500** and **1,319 GSM8K** original official references and compared every saved reference/status field. Exactly one MATH500 reference is unresolved; all other references are nonempty.
- Ran the final **39 CPU tests**, all passing in **1.965 seconds**: tokenization 5, scoring 8, data 12, preflight helpers 7, source guard 7. These include real-tokenizer/parser tests, synthetic/fake-output stop and ledger tests, transitive grouping and deterministic-selection tests. They do not load Qwen weights or execute the GPU worker. Separate checkpoint/loss test results reported by their implementing agents are not represented here as independently rerun tests.

The additional preflight input document lives outside the data release at [preflight_inputs.json](../../experiments/public_math_pilot_v1/preflight_inputs.json), SHA256 `06660ef5f0a12dde2118b3f7d436a7c0f3f34f492632ec13e438523b33d50c8c`; it is not an undeclared seventeenth data-manifest member. Its hash was independently checked.

## MATH500 boundary

Zero-based item **97**, `math500-test-0097`, retains original answer `\text{east}`. Upstream normalization removes the direction word as a unit and returns an empty string. The complete 500-item dataset remains present, with `reference_status=unresolved_reference` and `normalization_empty=true`.

Actual CPU scorer calls confirmed that empty, direction-containing and unrelated completions on this empty reference return **unresolved / correct=null**, never empty-equals-empty correctness. An empty prediction against a valid nonempty reference is a resolved incorrect answer. Vendor bytes and unit rules remain unchanged. The manifest correctly says `blocked_by_known_unresolved_reference`; this is not a model failure and cannot be silently converted into either 499-question reporting or an incorrect score. See [SCORER_BOUNDARY.md](../../experiments/public_math_pilot_v1/SCORER_BOUNDARY.md).

## Zero-execution and shutdown evidence

[PHYSICAL_LEDGER.json](PHYSICAL_LEDGER.json), [COST_AND_CLOSEOUT.json](COST_AND_CLOSEOUT.json), the execution contract and resource report agree on **0 formal updates, 0 nonformal updates, 0 model processes, 0 generation reservations/attempts and 0 annotation forwards**. No new scientific checkpoint or model-process receipt is claimed.

Independently read the locally preserved pre-shutdown observation: at **19:40:09 UTC**, the recorded GPU compute-process list was empty, the intended execution directory was empty, and the process list contained service infrastructure rather than a training worker. Verified all four private evidence SHA256 bindings listed in the public closeout record. This is a saved point-in-time observation plus the operator's cumulative ledger, not independent continuous surveillance of the server; this auditor made no remote request.

The saved provider observation and public closeout agree on OFF confirmation at **2026-09-17 19:40:40.554989 UTC**; timer clearing is recorded at **19:42:29.001539 UTC**. The window from 19:05:53 is **2,087.554989 seconds**; multiplying by CNY7.98/hour gives **CNY4.62741355895**. This is a powered-window proxy, not an invoice. Zero model work does not imply zero rental cost.

## Scope and remaining limits

Source inspection and CPU tests support question-first grouping, transitive benchmark exclusion, hash-ordered group selection, first eligible reference selection and no model/mask-success filtering. The final release records an eligibility prefix of **20,949 groups** and explicitly leaves the suffix's reference eligibility and total qualified pool unknown. This audit did not independently redo every raw-source MinHash sketch, every candidate Jaccard value, or every reference-qualification decision. It checked the published candidate-edge closure and final selected artifacts.

The final visual rules and three identity-bound question-only adjudications are recorded transparently. Rechecking those rules on selected rows is not an exhaustive semantic or visual-dependency audit. Near-duplicate candidate retrieval remains approximate, and no claim of complete semantic decontamination is justified. No benchmark outcome or generated model answer informed this freeze.

The GPU preflight remains **not run**. The formal four-arm training/full-evaluation orchestrator is explicitly **not implemented or admitted**. The observed raw terminal-backup projection and the unresolved MATH500 boundary remain open; CPU tests cannot waive either. E044–E047 are registrations, not completed models or results.

The closeout review flagged earlier prospective language implying an active preflight or a verified full-model roundtrip. The phase README and resource report were corrected to say the GPU paths are unexecuted; the Chinese summary likewise states zero model work and no formal runtime. No method score, comparative effect, confidence interval or successful GPU preflight should be inferred from these preparation artifacts.

## Source byte identities at this audit

These are local source SHA256 bindings, not a claim that this source was deployed or exercised on a GPU.

| Source in `experiments/public_math_pilot_v1` | SHA256 |
|---|---|
| `checkpoints.py` | `7d9f3c52b84d200317b44aa0c6d538eb7a766e3c4f85dfa3fac923e6fa3c9ca1` |
| `data.py` | `69af4e0916fd1657b70287a761635a3582c988714b01eb40a7c5f02f5b4f425b` |
| `losses.py` | `fbb489e9a7c6dfa724738abc89934b523af54f67ad1132b5d02456435400ef37` |
| `preflight.py` | `d05ec850d71e7bdd4411cba0c8348363a2ce0799726bc3ee11cd27e36094de5f` |
| `scoring.py` | `12f27f9e7f2e82d27b99a3f447a26c3b18c3bbaf78077fa88307deb36fa40f5c` |
| `source_guard.py` | `3730d100f2bbe9c3cc6b5470c9ce6178552b7322a06cc336df07d20be4081fd6` |
| `tokenization.py` | `61132ca09562d4c964d1d4ab9ea5e72448fb920aa73fc74cec8cb52399971eef` |

Reproduction of the CPU suite uses the repository root with the pinned CPU dependencies and:

```text
python -m unittest tests.test_public_math_tokenization tests.test_public_math_scoring tests.test_public_math_data tests.test_public_math_preflight tests.test_public_math_source_guard
```

No historical output, frozen release, runtime source, score or ledger was changed by this audit.

