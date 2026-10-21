# A/D complete long training and evaluation path — first shared CR request

Prepared without running a model, input consumer, original scorer, bootstrap,
upload or cloud job. This request replaces draft-only waiting with one complete
source path: original input consumer → shared admission/Modal dispatch → arbitrary
full U/B training → saved FP32 parameters/AdamW/RNG → FP32 merge then BF16 export →
joined child exit → native vLLM3300 endpoints → full binary/raw archive → actual
STOPPED0 named-record collection → one full-state/raw oracle → unchanged frozen
P1 scoring with final-think-region adapter → original question-level contrast.
No per-cell CR is introduced. Concrete actual spec/timing and new endpoint A1
will be added to this SAME request after source review permits the input consumer.

All three smoke arms, the two nonduplicated baselines, selected A cells and both
D cells use this common path. Original A1..A8 B41813212/U654 and D B4070922/U64,
seed17, original whole answers and masks remain. The consumer copies original
plans and selects original encoded dictionaries without re-tokenizing training
answers, reselection or filtering; first600 native endpoint prompts yield3300
requests. Public raw gold remains local; only gold-free endpoint requests upload.
All three LR vectors are prepared per cell; they are not extra model calls.

Integration corrected the draft's timing: training whole iteration covers both
volume commits plus unit/done store, and endpoint whole iteration covers all
three commits plus unit/done store. Old body durations remain separate. Final
cycle-file/summary writes, final-state export, engine startup and packing are
outside those cycles and must fit an explicitly accepted future allowance.
A/D has NO C1 self-calibration exception. No feasible measured long-duration
proxy, concrete cap or actual SPEC is invented here. Real numeric A2-lite must
resolve long-token/H100/full-parameter memory and startup/export/packing/IO/local
scoring costs. Every job reserves its actual per-function platform/startup cap.
Synthetic test timings/rates are fixtures only. Actual A115/D25/P011180/protect48 and original80percent gate remain.

Each model dispatch is once-only across the common P011 ledger, including local
pre-spawn intents, failed, pending, unknown and unmatched provider containers.
At most four owned/pending/unknown slots: five initial smoke/baseline jobs cannot
all occupy a GPU simultaneously; each still starts at most once when a real slot
is free. One local lock and permanent dispatch/claim/unit markers prevent replay.
Later A/D jobs require Claude's actual original smoke decision and permitted IDs;
A7 identities reuse the original smoke, never train it again. No algorithm here
chooses a student or writes scientific interpretation.

Linux hard stop targets only current worker descendants before exiting; platform
cap remains a second bound. Healthy workers are never cancelled by monitoring.
Normal failure retains remote files and immutable failure terminal. Abrupt hard
termination can leave no terminal; it does not authorize restart. Completed-only
collection is forbidden for failures. A new bounded failed-call recovery proposal
would be needed if actual remote incomplete state cannot be collected safely.

Full-state and merged binary bytes are preserved in an uncompressed archive,
with fixed actual admission byte bound. A public SHA is not reviewer access to
private weights. Collection and oracle/score share one original absolute result
window, not fresh windows per tool. One scorer process group includes33000maximum
seconds plus5cleanup; original8-second comparisons/two workers and fixed samples
remain. The full result window must cover this conservative local scenario and
all transfer/oracle/analysis time beforeOct22 05UTC; no cap extension is implied.

New tests: initial12 had11PASS/1missing-review AttributeError; fixed explicit
missing-review rejection and reran ONLY that failed test (PASS0.000s). Five NEW
consumer/EOS/contrast/source-permission checks PASS0.005s; two NEW owned-descendant
checks PASS0.000s. One new native-asset stop guard PASS0.001s and two new native-prompt NFC checks
also pass;22distinct new checks total. Old successful suites were
not rerun. Original failed log is retained. Mocked full worker is not realGPU,
state, score or numerical acceptance. Original source/published drafts remain
in Git; only new prepared path and the four integration files change.

The final native-prompt integration records original raw prompt SHA, nativeNFC
SHA and a change flag, and verifies exact decoder roundtrip before any model.
It admits only the pinned tokenizer's own NFC, never NFKC/trim/cleanup. Original
benchmark problem bytes/gold remain local and unchanged. This avoids repeating
the known raw-versus-native-NFC assumption in the new endpoint preparation.
No original benchmark was tokenized during these synthetic tests.

CR must inspect every actual remote writer and reader, dict/list structures,
all loops, full-state tensor schema,3B/fullparameter/LoRA settings, exactsource
closure and no retry boundaries. Private manifests are bound by hash; original
full input archives already reviewed remain linked through OT3/AM packets.
P010's Oct21 19UTC metadata-only formal freeze remains separate.
