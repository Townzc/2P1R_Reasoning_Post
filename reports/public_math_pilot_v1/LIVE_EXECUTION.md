# Latest direction and live evidence — 2026-09-18 03:30 UTC

The owner now targets longer-term ACL/ICML research and plans to move to the
existing `codex/icml-acl-2027` branch after the current round. Read the
[stage review and transition requirements](LONG_TERM_TRANSITION_20260918_ZH.md)
and [bounded read-only evidence](LONG_TERM_TRANSITION_PROGRESS_20260918.json).
The finite queue, scientific settings and tonight’s shutdown deadlines are
unchanged; the ICLR abstract rush is no longer a reason to add compute.

Saved coverage is13,363/31,203 (GSM6,595, MATH6,256, Base-dev512);18/54 runs
are scored. Both original GPU workers, coordinator and CPU scorer remain alive
with no new failure. Four final128-step checkpoints remain committed;12 retained
scientific files match their prior fully hashed identities and sizes. The latest
check did not rehash106GB of binaries. This is not a final output reconciliation.

After full evaluation, publish complete results, resource/failure accounting and
a final handoff supplement, verify normal provider shutdown, pause the heartbeat
and wait for the owner. If tonight is incomplete, preserve exact missing coverage
and stop at the existing boundary; no overnight restart. Do not switch, merge or
edit the other worktree. The older timestamped snapshots below remain historical.

# Public math pilot running on two A800 GPUs

The owner reopened the same instance and authorized immediate use of both cards.
The published abfff696 scheduler started at2026-09-18 00:39:53UTC under detached
tmux. Both workers have one visible CUDA UUID, complete disjoint run assignments,
and independent hard timeouts. The unchanged CPU scorer reuses its saved scores
while evaluating newly completed runs. Source, contract and GNU-timeout lock checks
passed on Linux; all10 parallel tests passed. See [resume evidence](DUAL_GPU_RESUME.json).

At01:49:28UTC,9363 of31203 logical outputs are saved;21840 remain. All five
GSM8K states are complete and scored. Four complete MATH draws plus256 additional
MATH outputs are saved; both original workers and the scorer remain active.
No new failure or worker restart occurred. The live physical ledger has9991
reservations:9363 saved,128 old failures and500 currently in flight. This is a
non-atomic monitoring snapshot, not a final reservation reconciliation.

Instantaneous GPU utilization was100%/98%. Across206 active telemetry samples,
mean utilization was96.94%/98.00%; memory peaks were80607/80687MiB. Disk remains
about82.43GiB free. Cgroup memory events report zero OOM and zero OOM kills since
the current boot. The unchanged jobs continue in tmux.

All four arms completed their fixed128 updates and verified terminal recoveries.
Final scientific dose is512 updates. The544 physical completed-update records
include32 lost uncommitted TrimSFT updates. Independent on-server verification rehashed all
12 retained scientific files: eight64/128 models and four terminal training states,
106270841556 bytes total. It also checked committed ancestry and all512 update
histories. See [artifact verification](PRE_UPGRADE_ARTIFACT_VERIFICATION.json).

At maintenance pause, saved public outputs were Base-GSM8K1319, SFT-GSM8K1319,
DFT-GSM8K1319 and TrimSFT-GSM8K64. With512 Base-dev outputs,4533 of31203 logical
outputs are saved;26670 remain. The physical generation ledger has4661 entries,
including128 previously failed GSM attempts. The pause added zero failed calls,
zero model calls and zero uncommitted reservations. Every completed batch and
post-batch RNG was verified before terminating the evaluator at a durable boundary.
The5039-second evaluator exit143 and10561-second CPU scorer exit143 are intentional
maintenance stops. Their process durations overlap and are not billed GPU hours.
See [maintenance evidence](MAINTENANCE_PAUSE.json).

| Completed GSM evaluation | Correct /1319 | Accuracy | Generation time |
|---|---:|---:|---:|
| Base | 495 | 37.53% | 53.31 min |
| SFT | 1068 | 80.97% | 19.16 min |
| DFT | 1046 | 79.30% | 7.79 min |
| TrimSFT | 1009 | 76.50% | 15.73 min |
| QDW-v0 | 1080 | 81.88% | 7.84 min |

GSM QDW-minus-DFT is+2.58pp with a97.5% paired question-bootstrap interval
[+0.30,+4.85]pp; QDW-minus-Trim is+5.38pp,[+2.88,+7.88]pp. These GSM intervals
are secondary/descriptive, not the confirmatory MATH family. QDW-minus-SFT is
+0.91pp with a95% interval[-0.99,+2.81]pp. None includes training-seed uncertainty.
All1319 official GSM questions remain in each denominator; unresolved judgments
are zero. Base has many parse/length failures; trained arms have zero parse failures.
See [the immutable GSM snapshot](GSM8K_COMPLETE_PARTIAL_RESULTS.json). Full primary
MATH average@8/pass@8 and trained dev comparisons remain unavailable.

The first nine completed MATH batches take331–778seconds, mean704seconds. With71
batches remaining at the snapshot, a two-device mean/max-observed extrapolation
is6.94–7.67hours for MATH alone, excluding development evaluation, loads, scoring
and closeout, and without deducting progress inside two in-flight batches. It is
an engineering projection, not a runtime confidence interval. The former unmeasured
5–8hour whole-evaluation estimate was optimistic and is superseded by these actual
measurements. Full completion tonight is not expected; preserve exact coverage at
the existing nightly cutoff and resume only after owner startup. No benchmark,
draw, setting or endpoint is reduced to force an overnight finish.

The original evaluation source isc833d732a7e5b7ecf7589a41ea30f2fb7068a6d9.
Activated parallel scheduling is fromabfff696f68cdd8aa9b32dd410330ee5424d5c80;
all98 CPU checks passed before deployment, and10 parallel tests passed on Linux.
Both GPU workers are now active, preserving the original scientific contract. The same-instance
upgrade needs no Mac checkpoint transfer. The source keeps complete sampled
streams on one worker, with one visible CUDA device per process and the original
scientific generator code. Read
[the dual-GPU plan](../../experiments/public_math_pilot_v1/DUAL_GPU_PREPARATION.md).

Preserve the128 failed GSM attempts and the32 lost training updates. The passive
GPU replay comparison remains non-bitwise; cause is not isolated. Keep this and
the one-training-seed limitation in the final report. No additional arm, seed,
model or result-based stopping rule is introduced by the hardware change.

Existing nightly model/hard-GPU/CPU cutoffs are06:35/06:45/06:50UTC. The provider
23:58PDT timer was visibly reconfirmed after the hardware change.
After complete evaluation, report all comparisons and limitations to the owner
and wait for their next-direction decision. No optional experiment follows.
