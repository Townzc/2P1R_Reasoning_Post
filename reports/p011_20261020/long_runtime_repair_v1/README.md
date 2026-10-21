# A/D runtime repairs R1–R3 and independent numeric-gold input candidate

PREPARED, NOT EXECUTED. Same shared long-path CR/A1/A2-lite request; original
31-source packet and failed CPU attempt are immutable. Exact37-source closure
adds src/sft_data.py and src/__init__.py, new protocol/checkpoint/gold adapter
and independent input entry. No existing paid worker, model or input output is
modified. C1 and B runtime bytes are unchanged.

R1: shifted_loss_sum's actual src dependency is included in closure and rejected
by runtime SPEC validation if absent. R2: full-parameter arm requests96GiB host
memory (LoRA32GiB); CPU4/H100 and exact per-arm memory cost are SPEC-bound. New
terminal writer verifies serialization with torch.load(mmap=True), deletes the
mapped view before export, and retains full FP32 parameters/AdamW/RNG/schema.
Old shared checkpoint source remains byte-identical. The host reservation and
mmap reduce the identified duplicate-state pressure; this is not an observed
full16k GPU-memory guarantee or peak-host measurement.

R3: shared constants change3300requests from104x32 to7batches (6x512+228), engine
max_num_seqs256 with8192chunked-prefill tokens and capture sizes through256.
Worker/forecast/namedjournal/raw oracle share the geometry. Each request's
original seed/sampling/cap/content remains unchanged. New whole-batch timing is
unmeasured: old32batch durations cannot be relabeled as512batch measurements.
Runtime still requires true complete numeric/memory/window/D1 A2 admission.

The new gold adapter and input entry are separately gated by a real owner
failure exception and exact input-only CR. Existing consume/write_endpoint and
original request_roster/tokenization functions are AST-identical. The new
projection supplies the same numerical answer as canonical text while retaining
original value/type/hash. All600prompt encodings are new; the530ephemeral failed
ones cannot be reused. Training-token dictionaries and plan bytes are reused.

Thirteen NEW checks PASS once0.713s: real tinyCPU torch mmap roundtrip and
corruption fencing, full3300mock dispatch/seeds/three commits/7cycles, per-arm
resource/rate/closure guards, unchanged science/input function ASTs, original
synthetic gold failure and new exact projection, owner/CR and partial/replay
rejections. No prior successful suite, real model, benchmark encoding, score,
statistic or checkpoint was rerun. No tests constitute independent audit.

R4 remains an owner-required bounded GPU-preflight proposal, not permission.
No measurement exception or scientific smoke retry is implemented/admitted.
A concrete preflight path must be separately fixed/reviewed with owner approval,
full resource rate, <=5USD A allocation, original protected/D1 obligations and
complete result window before any paid attempt. Short-output preflight timings
cannot alone bound original16384token endpoint completion. P01019UTC remains.
