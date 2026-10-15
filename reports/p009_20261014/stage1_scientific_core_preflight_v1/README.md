# Stage1 NC/S1 scientific core — prepared, not admitted

This packet prepares the exact training/merge and isolated evaluation core while
independent P1/Stage0 result reviews proceed. It is not a Modal entry, student
input release, worker time/cost admission or model call. S2 is explicitly rejected
because its original zero-shot cap gate failed locally; independent A2 remains
pending. NC and S1 still need their own actual scientific and input gates.

Training reuses unchanged P008 forward/loss/AdamW/gradient-clipping/checkpoint and
16-update block-journal functions, with the actual P0091024-update/2097148-target
whole-answer plan and original frozen1024 LR vector. Runtime retokenization must
match the frozen full encoded rows exactly; no answer filtering, truncation,
q0, smaller n or new LR computation. Seed17/29 and the registered NC/S1 n lists
are checked before model load. NC is seed17 n400/3200 only. Save/read back the
complete1024 state (adapter/optimizer/RNG) before FP32 safe merge and BF16 model
storage. There is no intermediate evaluation or checkpoint selection.

The pinned common P009 Linux environment has NumPy2.2.6, while the earlier P008
training environment used2.3.2. This is disclosed and requires review; no claim of
bitwise cross-experiment equivalence. Forward/loss/optimizer functions remain
unchanged, and P009 trains all its students under the same exact admitted stack.
The training process must exit before the future parent starts vLLM, so both
models cannot retain a GPU concurrently. A future exact parent must prove this.

Endpoint inputs must be the original complete raw-prompt token IDs: NC1319/GSM
max512, S1MATH500 max1024. The common high_throughput_v1 engine, greedy sampling,
context2048 and fixed inference seed17 apply also to training-seed29. The isolated
engine consumes original256-row batch boundaries once, rejecting repeats or
skips. Original returned token IDs/text/backend stop metadata and malformed
shapes are forwarded to the future parent for durable preservation before
validation; no GPU scoring. The original CPU stop/scorers, not this engine, will
produce outcomes. MATH P1 must be fully locked before any S1 training is admitted.

The future entry/input/numeric review still must bind actual G0, P1 and roster
reviews, exact model/input/plan bytes, a single-use claim, hard full-worker timer,
all-block/full-batch forecasts, original journal units and source-scoped oracle.
No automatic retry or controller is provided here. The22-file source/data closure
includes old code that is imported but whose old evaluation/dispatch routes are
not invoked. Historical budget constants in those dependencies are not a new
P009 runtime allowance. Existing generation34 and P1window12 bytes were preserved.

Eight new CPU/mocked checks passed once, including a mocked full top-level train
path which verifies final-save/merge order and no replay. They are not a GPU,
checkpoint-binary, real training, vLLM generation or MATH-scoring experiment.
