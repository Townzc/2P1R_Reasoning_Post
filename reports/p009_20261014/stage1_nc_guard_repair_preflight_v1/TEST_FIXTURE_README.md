For an isolated checkout copy ADMISSION.json and PLAN.json into
.local/p009_20261014/r1/stage1_nc_guard_repair_candidate_r1 as
ADMISSION_DRAFT.json and PLAN.json. Copy TEST_ORIGINAL_DISPATCH_PROJECTION.json
to .local/p009_20261014/r1/stage1_nc_replacement_r1/runs/
nc_s17_n3200_replacement_r1/dispatch_intent.json. Run only the new
 tests.test_p009_nc_guard_repair suite. New proxy/review values are synthetic
in-memory fixtures and are never persisted as approval. Real RunGuard is used;
no actual model, tokenizer, raw score, state load or remote write occurs.
