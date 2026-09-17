# Next-session handoff — public math pilot remains unrun

Read `EXECUTION_SUMMARY_ZH.md`, `RESOURCE_FEASIBILITY.json`, `COST_AND_CLOSEOUT.json`, `PHYSICAL_LEDGER.json`, the final data/CPU audit, and `../../experiments/public_math_pilot_v1/EXECUTION_CONTRACT.json` before any paid work. Current state is provider-off, zero model execution. Do not resume any E040–E043 or earlier phase. Their ledgers and results remain immutable.

## What is present

The independent public Math-1.5B base and official data are locally hash-verified; a matching base copy is already on the stopped instance. The public release contains immutable identities, grouping/exclusion decisions, 4096 training rows, 512 development rows, future20k IDs, selected token IDs and full public benchmark question/reference identities. Actual files and release identities are authoritative; do not reconstruct from an invalidated candidate.

CPU modules implement tokenization, four losses, QDW selection, data qualification, official non-executing Qwen scoring wrapper, checkpoint persistence and a bounded engineering preflight. Source guard verifies a published code closure and exact input manifest before execution. Full-model GPU memory/throughput/save-reload equivalence remain untested; a working tiny CPU test is not evidence of a full-scale successful run. The formal four-arm training/full-evaluation orchestrator is not implemented yet.

## Blocks before a main grid

1. The full MATH500 benchmark has one retained upstream reference-normalization boundary. Read `SCORER_BOUNDARY.md`. A common, documented grading amendment needs to be frozen before results; do not drop the question, score it wrong, or claim empty-equals-empty correctness.
2. Measured uncompressed complete recovery transfer already fails the current effective whole-phase resource gate. Compression, parallel transfer or another route require actual measurement. No assumed improvement, automatic recharge or extra machine is permitted.
3. The new formal orchestration must be implemented/published and checked offline before startup. Preserve one-step-per-unique-batch accounting, all128 updates per arm, exact LR vector, reference/mask identity, shared seed/batch order, immutable64/128 outputs, journal-backed logical output identity, no tool rounds, no test checkpoint selection, and complete denominators.

## Budget state must survive restart

The initial one-hour powered preflight allowance consumed 2087.554989 seconds of startup/preparation/transfer time through the conservative provider-off observation. At most1512.445011 seconds remain under that original envelope, subject to actual provider charges and the required900-second shutdown/export reserve. Do not silently give the next run a fresh3600seconds or reuse expired deployment deadlines. The proposed entire-phase12h/CNY120 ceiling also does not reset across sessions or guarantee sufficient funds.

No GPU preflight reservation exists, so there are no reusable32 Base-dev outputs or64 profile annotation forwards. Entire planned counts remain unrun: eight nonformal updates maximum,512 formal updates,8192 mask sequence forwards and31203 generations. Main admission is false, not merely waiting for a successful script exit.

## Disconnection-safe execution when ready

Use an immutable, newly extracted archive tied to a published full Git commit. Verify the archive SHA and independently supplied source-inventory SHA; use `source_guard.py` to bind all namespace Python source and the input SHA. Never reuse an execution directory with stale bytecode. Launch the finite worker via a server-side detached `nohup`/`setsid` session with an absolute deadline and `timeout`, a shared persistent physical reservation ledger, complete stdout/stderr, and a process start/exit receipt. A provider timer must enforce the whole-instance limit with a900-second preservation/shutdown reserve.

After a client network interruption, inspect the server PID/receipts/ledger and verified latest checkpoint before starting anything. A disconnected client is not evidence the job stopped. Do not repeat logical benchmark outputs or reset physical budgets. Count infrastructure failures as unresolved rather than incorrect and retain the original evidence.

## Storage/closeout

Respect both filesystem quotas separately, reserving2GiB on each. Final FP32 model files may serve both inference and recovery; do not duplicate them unnecessarily. Final optimizer data can be pruned only after a complete independent local backup with SHA/byte verification and ACK. Step64 weights may be temporary only after all required midpoint outputs are durable and the checkpoint policy permits removal. Engineering-only smoke state is explicitly disposable only after its roundtrip receipt is durable; never generalize that exemption to scientific checkpoints.

Current stopped-instance free space was 28,869,136,384B system and40,179,052,544B data. No old scientific record or unique weights were deleted. E015 independent full-weight recovery remains incomplete: never release the instance or delete that historical unique state. No automatic restart, recurring job or optional experiment is queued.
