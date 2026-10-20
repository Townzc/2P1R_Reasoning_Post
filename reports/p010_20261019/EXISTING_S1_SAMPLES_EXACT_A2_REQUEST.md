# Original S1 new four-sample evaluations: exact A2

Request `p010-C5-existing-S1-samples-A2-r1`; scope `p010-C5-existing-S1-sample-only-A2`.

Packet [existing_s1_sampling_runtime_v1](existing_s1_sampling_runtime_v1/README.md), exactSPEC SHA `fbb07d3dc9fc1f16975e1eb0701b640598c707d3ec5d1fdd39fad1ceefa5f41c`,32runtime/47verification source maps. Both original final state proofs and actualP009A4 are included; endpoint SHA `8f9a0500f80f0f2178d96e2b909057a5e7ea6803401358d83121d4cf01fbadae`. Original273/276greedy and the old P009 stopping decision remain unchanged. Only the four new sampling passes per model in P010v3§2.5 are proposed.

Please audit inputs, originalterminal/state/model-hash inheritance, all exact code,8batches/2000outputs/model, frozen symbolic scoring and numerical limits together. Actual restore exits beforevLLM; no optimizer/update, greedy regeneration or old full-state oracle. No actual cloud call, state load, scoring or output yet. Separate true A3 will review completed new results. Shared max4counts T/I/pending/unknown/unmatched; this new phase will not overlap untracked pendingI with the older K1entry. Failed/completed reservations are retained. T2.52each/5.04total remains in150, no release or transfer.600s allowance/20percent/max20originalC4timings is an uncalibrated scenario830.870484s<=1170, not futurebound. Local scoring19560scenario<=20400cap+5cleanup preserves original8s pairtimeout/confirmedcache/primarylabels.

Requested real fixed report: exact scope/target/spec_sha256/source_files/verification_source_files; original_parent_proofs_accepted=true, original_merged_bytes_required=true, restore_exit_before_vllm=true, new_training_updates=0, greedy_regeneration=false, exact_new_outputs_per_model=2000, original_4_sample_protocol_unchanged=true, frozen_symbolic_scorer_unchanged=true, new_T_reserved_usd=5.04, first_paid_measurement_exceptions=0 and PASS or PASS-WITH-NOTES. Full fixed report bytes/hash and readtime will be recorded; no comment-only or self-declared approval.

Oldsource/tests/scoring remain complete and were not repeated. Existing7adapter/3worker/4payloadchecks already published; this extension only ran4newdurable sample scoring checks. No extra code-only approval round. Claude ownsZ1; noZ1actual data/report used. This is code/evidence documentation, not course-report prose.

Publication check: two unchanged transitive source copies retain historical EOF blank lines; whole-tree whitespace check is not claimed PASS. Source hashes are preserved. The check excluding exactly these two files passes.

Fixed candidate `8a63b8d74932953c7be34d4d93d520a8095df9f3`; all69manifest members and the manifest itself match original Gitbytes once. No new model call.
