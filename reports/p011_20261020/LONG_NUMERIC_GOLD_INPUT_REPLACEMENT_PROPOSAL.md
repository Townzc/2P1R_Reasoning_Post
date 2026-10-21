# One independent CPU input replacement — owner decision required

Prepared 2026-10-21T06:13:08.178650+00:00. Request `p011-long-numeric-gold-input-replacement-owner-r1`.
Original failure: [preserved bytes](long_input_failed_preservation_v1/README.md),
original CLI37318, permanent LONG_RUNTIME_INPUT_ATTEMPT, no successful input.
The earlier input-only source permission is consumed; P011 §7.1 prohibits
an automatic retry. This proposal grants no GPU call and spends no new budget.

Proposed scope: one new script `prepare_p011_long_numeric_gold_inputs.py`, one
new permanent LONG_NUMERIC_GOLD_INPUT_ATTEMPT and new long_inputs_numeric_gold_r1.
Keep all600original problems and answer values; preserve each original scalar
and hash, map only integer or finite integral float to its exact integer string,
retain strings byte-for-byte. Reject other values before any tokenizer use.
No answer correction, dropping/reselection, truncation, scientific arm, seed,
B/U/LR, benchmark size, decision rule or budget change. All original failed
markers and files remain immutable.

All600 native prompt encodings would be made in this independent attempt. The
first530 computed by the failed constructor were never saved: this is explicitly
new encoding of those prompts, NOT reuse. Existing OT3/AM training rows and all
plans are reused; original consume/write_endpoint functions remain unchanged.
Create-only per-file outputs, one3600second local bound and originalOct22 05UTC
cutoff apply; partial/failure permanently blocks any automatic repeat.

Execution requires both a real explicit owner decision naming this proposal and
a fixed exact CR of the37-source candidate, original failure/input hashes and
owner decision hash. After completion actual input A1 remains mandatory; source
or input permission never implies model/runtime/numeric/paid admission.
No owner decision has been received for this proposal as of preparation.
