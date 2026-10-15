# Independent synthetic fixture setup

Codex ran the16 tests once using the private candidate and original dispatch.
All synthetic new verdicts are made inside the test, never saved as acceptances.
For an isolated review checkout, copy ADMISSION.json to
.local/p009_20261014/r1/stage1_nc_replacement_candidate_r1/ADMISSION_DRAFT.json,
PLAN.json to that directory/PLAN.json, and TEST_ORIGINAL_DISPATCH_PROJECTION.json
to .local/p009_20261014/r1/stage1_nc_r1/runs/nc_s17_n3200/dispatch_intent.json.
The latter retains all historical validation fields and omits only host locators
as already declared in the original public parent projection. No test inspects
those locator fields or calls a provider, model, tokenizer, state loader or scorer.
Run tests.test_p009_nc_replacement_admission in that isolated checkout. Codex did
not rerun the16 passed tests merely to reconstruct this public fixture layout.
