# E015 results — engineering gate passes; server shut down

The single registered E015 run completed on 2026-09-10 UTC. All **32/32 training
answers are correct and terminated**, with **zero truncations** and reference
NLL **0.001106**. The unchanged engineering gate passes. All eight original
E013 failures are repaired in this endpoint, with no lost successful answers.
No development/test generation or scientific treatment comparison was run.

The provider confirmed normal shutdown after compact results and the current
ledger were downloaded. **Independent checkpoint backup is incomplete** because
the new connection was too slow. The complete 12-file checkpoint remains on the
stopped instance's disk; preserve that instance until a verified recovery copy
exists. Do not interpret partial local files as a backup.

## Fixed dose and verified endpoint

Executed source: `e5083217d40c1f83477d18aa7331d94bac328987`.
Input-release SHA256:
`a88cf1732d13ce00f235dda0eb7d8f3288273987270352de03e0a9551bcc3230`.
Run: `gsm8k_terminal_decay_e015_r1`; original pinned Qwen2.5-1.5B base,
seed 17, FP32 parameters/BF16 autocast/SDPA, TF32 off, fresh AdamW, batch 4,
microbatch 1. The exact 32 references, schedule, masks and scorer remain fixed.
Dose is 256 optimizer calls, 167,232 supervised targets and 229,056 processed
tokens, with 32 exposures per row. The predeclared LR schedule has 192 constant
steps and 64 cosine-decay steps, ending at zero: 255 nonzero-LR calls, summed
LR 0.011175. There was one model job and no retry or 512-step fallback.

| Measure | E013 constant LR | E015 terminal decay |
|---|---:|---:|
| Correct and terminated train answers | 24/32 | **32/32** |
| Truncations | 5/32 | **0/32** |
| Reference-exact outputs | 20/32 | 31/32 |
| Final reference NLL | 0.0142055 | **0.00110594** |
| Reference argmax misses | 17/5,226 (E014 probe) | **1/5,226** |
| Reference-conditioned EOS argmax matches | 32/32 (E014 probe) | 32/32 |
| Generated tokens | 8,652 | 5,244 |
| Original engineering gate | Failed | **Passed** |

The only nonexact E015 output is `gsm8k/train/02775`. Its reference token at
zero-based target position 145 is ` *`, while the full-reference argmax is `6`;
the target-minus-best-other margin is -0.5. Its generated alternative still ends
with the correct numeric answer. Thus perfect reproduction of every reference
token is not necessary for this endpoint. Reference-conditioned EOS remains a
measurement after the correct reference prefix, not after a generated loop.

The official gate remains at least 31 correct/terminated answers, zero
truncations, NLL below 0.1 and complete dose/profile. All 112 Linux tests passed,
including both GNU-timeout integrations. Server and local CPU output audits
check 32 generated streams, all 5,226 reference targets and 256 updates. Server
audit also rehashed all 12 checkpoint files. These are record-consistency and
numeric-endpoint checks, not independently recomputed pretrained logits or
proof-validity verification. [Paired evidence](real_math_e015_execution_r1/paired_comparison.json),
[server audit](../runs/gsm8k_terminal_decay_e015_r1/record_verification.json),
[local audit](real_math_e015_execution_r1/local_record_verification.json).

## Attribution limit: early numerical trajectories differ

The configured training intervention is terminal LR, but the two runs are not a
verified branch from identical optimizer/parameter state at step 192. Their
base reference measurements are exactly equal; the first three logged training
NLLs also agree. Gradient norms first differ at step 3, and training NLL first
differs at step 4, long before LR decay starts at step 193. Across the first
192 steps, the largest absolute NLL difference is 0.160433; at step 192,
E013/E015 log 0.033197/0.086129. The original data/order/dose hashes agree.

Therefore report a successful configuration endpoint, not a clean causal
estimate of how much improvement terminal decay alone caused. The source of
early GPU numerical divergence is unresolved. The tiny CPU equivalence tests
never established GPU bitwise equality. PyTorch documents that controlling
seeds does not eliminate every source of nondeterminism, and offers separate
deterministic-algorithm controls; this is context for a possible future check,
not evidence identifying the cause here.
[PyTorch 2.8 reproducibility documentation](https://docs.pytorch.org/docs/2.8/notes/randomness.html).

Training memorization also does not establish generalization, a benefit of
multiple solutions, or task-wide robustness across seeds. No old score, parent,
reference, cap or checkpoint-selection rule was changed after seeing results.

## Compute, rental and preservation

The bounded process took 218.164 seconds and charged **219 process seconds**.
Training took 166.430 seconds, final train generation 28.816, all-reference
measurement 0.805, and checkpoint save/hash 14.060. Profile throughput is
1,010.04 supervised tokens/second. E013 trained for 167.136 seconds; E015's lower
total process duration also reflects intentionally omitted base/dev generation,
so it is not an isolated training-speed improvement.

All 19 public receipts reconcile to **6,686/7,200 used, 514 remaining, zero
reservations**. The latest independently retained private ledger SHA256 is
`ad45fa615091d9f47d16b5b80b07aa23313f356b5ab96bdcab4fa74ff60891d0`.
The earlier 18-receipt backup is preserved; a clone is not a new allowance.
[Ledger reconciliation](real_math_e015_execution_r1/ledger_verification.json).

The owner-supplied new server was an older snapshot. Published source and the
current ledger were restored before launch. Its original base and pinned
runtime passed verification. Both sides reverified E013's independent backup;
only the exact 12-file server duplicate was reclaimed, leaving 12,945,813,504
bytes free and passing the unchanged 12 GiB gate. Unique state and the original
base were retained. [Preflight/migration](real_math_e015_execution_r1/preflight_and_migration.json).

A provider stop timer was set as a backstop. After computation, compact records
and the updated ledger were exported and verified. The first real checkpoint
export was stopped after 154.59 seconds with 11,703,349 ordered bytes written;
only five small files were fully verified. Two bounded connection-multiplexing
probes, including a warmed connection, did not establish sufficient throughput.
These byte counts exclude data still buffered in parallel ranges and are not
measurements of aggregate network capacity. No second full backup or model
run was started; the original export allowance was not reset.

Normal shutdown was then confirmed in the provider UI, and the now-unneeded
timer was cancelled. The final closeout check was at 08:54:27 UTC, about 23
minutes after the recorded owner notification. At CNY8/hour that observed span
corresponds to about CNY3.07, **not an actual invoice**: notification may postdate
power-on and the final check follows actual stop. The CNY3000 overall ceiling
is not a spending target, and historical billed spend remains unreconciled.
[Shutdown evidence](real_math_e015_execution_r1/shutdown_closeout.json).

The complete new checkpoint contains 12 files / 6,190,803,414 bytes and passed
server hashes before the read-only export. Full independent weights recovery
remains open; the stopped instance must not be released/deleted. Local partials
and failure receipts are retained separately from the complete E013 backup.
Provider retention is finite, so recovery should precede the displayed release
deadline (approximately 2026-09-25 UTC; verify the console before recovery).
A later CPU/no-card transfer can avoid GPU idle billing, but none was started
after the requested shutdown. A late 20-second read-only SSH check timed out;
it provides no additional pre-shutdown evidence. The provider UI, not SSH loss,
confirms the stop. [Export closeout](real_math_e015_execution_r1/checkpoint_export_closeout.json).

## Next decision, with the server off

1. Prepare a separate bounded weights-recovery plan with a measured transfer
   route before any instance disposal. Keep current compact records and the
   19-receipt ledger independent. Do not restart a GPU to do literature work.
2. Use this passing recipe as an engineering candidate. Freeze a distinct
   held-out capability/profile check and its answer-format/denominator rules
   before new generation; the previous strict base 0/16 was format-limited.
   Inspect existing saved outputs on CPU first. No test-set tuning or automatic
   full training grid follows this 32-example success.
3. After a non-floor capability result, price the complete three-arm minimum
   from P005: Repeat256x1, Solutions256x4 and Breadth1024x1, including actual
   selection losses, evaluation and preservation. Keep total supervision and
   optimizer calls matched, and plan paired uncertainty/replication. Treat
   selection/curriculum and a task-matched small student as conditional routes
   if capability or allocation results motivate them. The old 512-step sweep
   is not a default next action.

The new monetary ceiling permits finite future phases while preserving process
history; 514 seconds is not a permanent financial cap. No new phase allowance,
server startup, teacher call, scientific arm or development/test decode was
silently initiated after this run. Post-hoc comparison code is
`analyses/e015_result_comparison.py`; its two reports reproduce byte for byte
from saved outputs and the current ledger.
