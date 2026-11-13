# T4 first pass@8 diversity check

9B-Base has251/500questions (50.2percent) with all8token sequences identical, crossing the review8bbf06a7T4 majority-identical guard. Original4000outputs are retained. All8sequence IDs differ within eachquestion, so the client did not simply repeat one response object. The cause is not established by this observation. Formal9BBase training is held; ModalA5/bridgecontinue.

`CHECK.json` records exacttoken diversity for allcompletedgroups. TinkerSDK0.39 `SamplingClient.sample` documents num_samples as independent; it forwards oneSamplingParams seed unchanged to the server. Serverseed-offsetsemantics are not exposed by the client. The inspected local SDK source is bound by `SDK_SOURCE.json`; public type documentation: https://github.com/thinking-machines-lab/tinker/blob/main/docs/api/types.md

Concrete proposed diagnostic: first8frozenheldoutquestions,8single-sample calls each withdistinctrecordedseeds, T0.7,4096tokens, unchangedmessages/renderer/stops. Compare token diversity against the originaln8outputs, withoutscoring answers or replacingtheprimary500questionendpoint. Maximum64newresponses plusfullprefill and25percentmargin fit$0.40. No diagnostic hasrun. OwnerdecisionisneededbecauseT4explicitlyrequiresstoppingandreportingattheobservedcondition.
