# T4 first pass@8 diversity check

9B-Base has251/500questions (50.2percent) with all8token sequences identical, crossing the review8bbf06a7T4 majority-identical guard. Original4000outputs are retained. All8sequence IDs differ within eachquestion, so the client did not simply repeat one response object. The cause is not established by this observation. Formal9BBase training is held; ModalA5/bridgecontinue.

`CHECK.json` records exacttoken diversity for allcompletedgroups. TinkerSDK0.39 `SamplingClient.sample` documents num_samples as independent; it forwards oneSamplingParams seed unchanged to the server. Serverseed-offsetsemantics are not exposed by the client. The inspected local SDK source is bound by `SDK_SOURCE.json`; public type documentation: https://github.com/thinking-machines-lab/tinker/blob/main/docs/api/types.md

Concrete proposed diagnostic: first8frozenheldoutquestions,8single-sample calls each withdistinctrecordedseeds, T0.7,4096tokens, unchangedmessages/renderer/stops. Compare token diversity against the originaln8outputs, withoutscoring answers or replacingtheprimary500questionendpoint. Maximum64newresponses plusfullprefill and25percentmargin fit$0.40. No diagnostic hasrun. OwnerdecisionisneededbecauseT4explicitlyrequiresstoppingandreportingattheobservedcondition.

## Approved diagnostic completed

Owner authorized the64-response diagnostic. Originalunique counts1/3/1/4/3/1/1/2 became8/8/8/8/8/8/8/8 under distinctseed single-sample calls. All generation prefixes matched. Token-price upper cost was$0.053869506. No answers were scored. See `DIAGNOSTIC_RESULT.json` and `distinct_seed_diagnostic_evidence.zip`. The original n8 sampling path does not supply the intended independent draws in this experiment; allthree original T pass8 endpoints are retained and marked invalid for that interpretation. Repair is prepared in `../tinker_t4_repair_review_v1/`.
