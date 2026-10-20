# C1 original-input and confirmed-forward evidence adapter — draft

Prepared only. This continues the C1 path toward one shared full CR/A1/A2-lite;
it does not create a separate code-only blocking gate. There is no model loader,
production CLI, cloud invocation, budget/timing admission or real forward run.

ORIGINAL_GROUP_BINDING_DRAFT copies metadata from the two original input manifests:
P009 S1 seed17 n400/n3200 for T1.5 and P010 student_inputs_r2 seed17 K1 n400/n3200
for T7/T72. The six groups keep exact original config/rows/encoded byte hashes and
producer paths. No original encoded array was loaded by these new functions;
no tokenization, input rebuild, teacher generation or outcome rescoring occurred.
The future loader validates these exact paths and files before unchanged C1
inventory checks token/mask identities and literal-sequence deduplication.

The new evidence adapter groups up to32 unique forwards per durable chunk; each
model call still receives one original unpadded sequence. It saves a per-sequence
attempt before the forward and the full original-span NLL vector after it,
including EOS; chunk confirmation binds every result file hash. An exception,
nonfinite vector, missing confirmation, wrong basis or changed mask blocks the
whole summary. The failed/partial directory remains; there is no retry/resume.
A complete directory receives one descriptive summary only, no bootstrap/test.
Final marker writes are explicitly excluded from elapsed timing. Read-only
closure checks inspect raw saved vectors and hashes without executing a model
or recomputing statistics. The final full entry still needs its permanent global
claim, exact untouched base weight/load/device/dtype binding, complete runtime
window and budget evidence, and independent review before real use.

Seven new synthetic IO/journal tests passed once (0.052s), including an interrupted
chunk and an attempted replay. Old13 C1/B/C2 tests were not rerun. No real data
forward, model load, tokenizer, scoring or GPU use. P011 is exploratory.
