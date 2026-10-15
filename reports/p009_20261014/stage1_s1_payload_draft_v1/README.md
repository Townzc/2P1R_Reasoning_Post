# Prepared S1 payload verification helpers

This independent preparation does not change the two active NC workers. The new
helpers verify a complete S1 trajectory, original 1024 state, target dose,
terminal merge, training-process exit, all-block forecasts and both endpoint
batch acknowledgements. They decode all500 original outputs once and bind every
row to the frozen gold IDs. Vocabulary is collected once per full endpoint;
original raw-file hashes are reused after one batch check. Genuine caps stay
caps, and the1024-token native-EOS/backend-length tie preserves backend metadata.

There is no Modal entry or callable CLI, actual cap, generation, real state
loading, actual decoding or symbolic scoring in this preparation. The future
full oracle must first validate exact source/input/runtime/admission, original
claim/terminal/envelope/manifest and provider STOPPED0, then invoke these helpers.
Their output explicitly says payload_only and full_runtime_lineage_admission_checked=false;
it is not a full runtime oracle or permission to train. Frozen MATH scoring and
actual A4/A5 remain separate necessary steps, with no label-rule change.

Seven new synthetic checks passed once. They exercise complete endpoint binding,
raw-byte mutation, process-exit chronology, finite timings, unknown-token refusal,
complete ordered gold identity and preserved EOS/cap metadata. They do not test
real checkpoint loading, GPU execution or math-verify, and do not rerun the old
NC/P1 tests. The4000-second fixture is synthetic, not a proposed S1 cap. Existing
accepted sources, original outputs and closed studies remain unchanged.

No separate code-only blocking audit request is created. The future complete
S1 source/runtime/numeric packet must include these exact bytes and all transitive
imports, actual NC A4/timing, actual S1 inputs and the original stop/budget gates.
