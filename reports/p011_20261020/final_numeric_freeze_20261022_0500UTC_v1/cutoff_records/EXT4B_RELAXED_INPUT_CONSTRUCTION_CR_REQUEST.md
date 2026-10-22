# P011-ext-4B relaxed-pool input construction — exact CR requested

Request: p011-ext-4B-relaxed-pool-input-construction-CR-r1
Scope: p011-ext-4B-relaxed-pool-input-construction-CR
Status: PENDING; zero production data/model executions
Fixed target: 583a035a9cd3353f0d71f9ad6d8432d57ef9f4ea
Packet: reports/p011_20261020/ext4b_relaxed_input_preflight_v2
SPEC: acc18dc4a8267b6cf06c0ac34b62829aa537b42b9e180c9d7db0e83954ab143c
MANIFEST: f0ba47c553baebb9c3a04a838417b4dccc4217779ef3311ed1a2ec3f23d4181b

Latest direct human amendment: use12096 large questions once and the first3024 small questions matched to the same exact Bprime using the original q/q+1 schedule. Approximately165Mtokens and80USD are estimates;90USD pair/45percell hard caps remain. DIRECT_OWNER_CARDINALITY_AMENDMENT.json is exact authority. V1 target2d1d0254 remains immutable, superseded, UNEXECUTED. Raw DIFF_AGAINST_V1.patch preserves context whitespace; whole git style check is not PASS; all nonpatch new files passed.

The human directly instructed this chat to execute6304b2a2 with two cells totaling<=90USD. Exact owner record is included; its relaxed-pool rule data section replaces the earlier4096/16384 section and lifts the pool hold. Finished census has30428parents with>=1eligible answer. First source review is separated so this CPU constructor can proceed while the full training/checkpoint/resume/closeout path is completed and reviewed. This request does not authorize a GPU, and is not a substitute for the full runtime CR or actual A2-lite.

Review all10exact sources. Two production source files are new. V1 four boundary methods passed once; only one new v2 cardinality method ran and passed0.006s after the direct amendment. Original successful methods were not rerun. The completed census's parent hashes and answer lengths are reused; raw-key projection reconstructs sorted actual parent keys, fixed seed shuffles once, and selected groups are checked against their census eligibility count and first-eligible answer token mass. No whole-pool answer re-tokenization, old data-builder invocation or model call. Original eligible/mask/NFC/EOS rules and exact whole_schedule/exact_subset are retained. Previously encoded selected identities are copied; only new selected identities receive first encoding. Native3300endpoint bytes reused. No result-based selection or automatic data retry.

Please explicitly confirm all five contract flags in a fixed report:
- `exact_6304b2a2_plus_direct_amendment_nested_12096_3024_order_accepted`: true
- `completed_census_lengths_reused_with_selected_original_eligibility_agreement`: true
- `original_NFC_masks_EOS_and_existing_encoded_identity_byte_reuse_accepted`: true
- `equal_exact_Bprime_q_qplus1_whole_schedule_and_scaled_original_LR_accepted`: true
- `input_construction_only_no_GPU_before_separate_full_runtime_CR_and_actual_A2`: true

Disclose independent checks and private raw/cache access limits; a saved census parent summary alone is not independent full raw verification. Original05UTC P011 freeze remains; this new scope is separately pending. No4xB production has run. Full runtime will enforce45USD percell/90pair including any one infrastructure resume, retain14h ceilings, checkpoints around500updates, original F15 science and full endpoints; it must not assume14h fits45USD or reset failed-attempt costs.
