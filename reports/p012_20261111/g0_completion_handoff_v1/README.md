# Current G0 completion handoff

Shared source to review:fae6656d, ../pre_c8_review_addendum_v1/README.md together with the original pre_c8_review_v1. Source review is still pending. This package adds results and queue metadata without changing that source.

All four Li MATH500 generation sets are complete: Qwen Instruct, UWNSL short, UWNSL long, and Llama Instruct. Their742 pending rows total151,855 prompt tokens (max909) using the actual fixed judge tokenizer. Each queue hash matches its initial-score manifest. Production merge and judge have not run. One32B H200 load is planned after the shared-source review and final budget admission.

Latest results: ../g0_uw_long_gsm_v1 and ../g0_llama_instruct_math_v1. LongGSM825/1319 passes the paper-comparison numeric gate. All independent10% raw-output audits remain pending. Llama GSM1319 is currently running under its prospective$1.22276forecast. BaseMATH5000/GSM1319 inputs and cache assets are ready for the reviewed wrapper; new base prompt construction/inference have not run. NoG0-T,C8 or main-grid baseline call.

Current G0-E cap8, emergency8,total85/protected4. Reported through11UTC snapshot3.21473239 includes partial activeLlamaMATH usage; the ledger retains remaining forecast reserves rather than treating partial billing as complete. Built with Llama.
