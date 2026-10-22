## CLOSED: fixed f52bba2a report accepted — 2026-10-22T07:06:06.756044+00:00

See `review_f52bba2a_3B_and_forced_relaunch_accepted_v1` for original report, exact scope/flags and limitations. Fresh budget and slots remain required; this is not an actual result audit.

# Actual 3B prefix, dose and numeric A2-lite — PENDING

Prepared 2026-10-22T06:38:17.022111+00:00; fixed `5f1003c5f459ed3f4f1780decae49e2141a37d1a`. Direct owner chose ②+③ and now directly delegates tonight's decisions to Claude. The later prefix review1901fcf7 explicitly retains **9,072 / 3,024**, superseding the earlier delegated2,268 variant. Prefix data CR allfiveflagsPASS; constructor7893 and actualmetadata70843 completed once. No tokenization, census, originalendpoint construction or model repeated.

**Actual common B′=123,808,531 supervised tokens including EOS; U=1,935; 2.9609906792140244× original B.** Large9,072 is one pass. Small3,024 has one-pass41,282,839, q=2 plus41,242,853remainder, token-weightedE=2.9990314135130096;3,020answers appearthree times and4appear twice. Original whole_schedule and learning_rates(1935,'S-F15') used once, same U and rates in bothcells. Savedplans and actualjobmanifest are in NEW_PREFIX_METADATA.tar.gz.

The newpacket contains only10newmetadata members/754,462compressedbytes withone fullreadback. Exact newprefixhash33566a5a32c2caec7086707ad2fef4a255d33e8ac708a8bcbe03e82c28b8d3f2 binds1,301,288,297bytes. It references the already published originalf679fa5c12096tokenarchive; newlargeindices0..9071 andsmall0..3023. **No oldtokenarchive re-publication or Codexre-hash/readback.** Originalnative3300boundinput/context/modelreceipts remainexact; runtime selects originalMATH2500 greedyfirst then4samples. AIME/AMCNOT_RUN, notzero. Private modelbinary access notclaimed.

Claude65eb8c30 alreadyPASSed originalruntimev1. Currentv2 c1a73d32 changes onlythe scorechild import/source snapshot andimmutableSPEC locator; exact86bindings,84unchanged. Its shortdiffCR remainsnecessary; please resolve that existing request together withthisnewactualA2. Original45cell90pair/costwatchdog/checkpoint500/maxoneproveninfraresume/fullstateoracle/complete500endpoint/four-sampleprimaryrequirements areunchanged. Both currentv2CR andactualA2mustbeaccepted beforefreshbudget/upload/twoGPUcalls. No permissionfromold81orv1PASS is inferred.

Please explicitly confirm allfourflags and exactscope; record actualreview/read limitations. No repeat oldscience/tests requested.

```json
{
  "request_id": "p011-ext-3B-actual-input-and-numeric-A2-lite-r1",
  "scope": "p011-ext-3B-actual-input-and-numeric-A2-lite",
  "status": "PENDING",
  "target_commit": "5f1003c5f459ed3f4f1780decae49e2141a37d1a",
  "packet": "reports/p011_20261020/ext3b_actual_inputs_v1",
  "source_target": "c1a73d322e65e1ce5c4545befd366e9f8b6787a2",
  "spec_sha256": "3a824522f32a5236cc65dc712bc8821f5cfeb86885dd39eaeec1d07d1f313f9e",
  "manifest_sha256": "9d568ef4d7ca3ea1add7a1410c33ec9077150e271c5771c0b408dd7ae21aae9b",
  "actual_input_binding_sha256": "fe932aab0c629a5c42c1aa61436736b3ebedf331fd4481b66ac2defb808d169d",
  "input_manifest_sha256": "afd5fe1bd7e13d28353d28fe4e7b6e2e296babcbc7752dc5cec843bdb7d17bfc",
  "actual_job_manifest_sha256": "bf556ba4e18ab52b6613d6e86eec207ec6dedab9937accb2b754f94368453a24",
  "required_flags": [
    "exact9072_first3024_original_answer_bytes_and_new_prefix_manifest_accepted",
    "equal_actual_Bprime_q_remainder_scaled_LR_U_and_effective_presentations_accepted",
    "original_model_context_native3300_bound_inputs_MATH2500_scope_no_gold_upload_accepted",
    "exact_full_source_SPEC_actual_job_manifest90pair45cell_checkpoint_resume_and_partial_scope_bound"
  ],
  "GPU_calls": 0,
  "first_remote_publication_utc": null
}
```
