# Public math pilot paused for hardware configuration

Provider off was visibly confirmed by2026-09-18 00:26:11UTC after the owner
requested an in-place change to two A800 GPUs. Full scientific evaluation is
incomplete. The heartbeat is paused pending owner startup. No instance or volume
was deleted, and all large artifacts remain on the server.

All four arms completed their fixed128 updates and verified terminal recoveries.
Final scientific dose512 and physical completed-update records544 include the32
lost uncommitted TrimSFT updates. Independent on-server verification rehashed all
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

These are partial results for the overall experiment. TrimSFT and QDW-v0 GSM,
all MATH draws and all trained dev endpoints are still incomplete. No primary
QDW comparison or overall method claim is available. See the immutable
[partial scoring snapshot](PARTIAL_RESULTS_BEFORE_UPGRADE.json). Different
lengths make the first Base-batch speed unsuitable as a measured whole-round ETA.
Single-GPU8–14h and two-GPU5–8h evaluation windows remain planning estimates;
MATH and actual dual-GPU throughput have not been measured.

The original evaluation source isc833d732a7e5b7ecf7589a41ea30f2fb7068a6d9.
Optional parallel scheduling is prepared atabfff696f68cdd8aa9b32dd410330ee5424d5c80;
all98 CPU checks pass, but it is not deployed or GPU-tested. The same-instance
upgrade needs no Mac checkpoint transfer. The source keeps complete sampled
streams on one worker, with one visible CUDA device per process and the original
scientific generator code. Read
[the dual-GPU plan](../../experiments/public_math_pilot_v1/DUAL_GPU_PREPARATION.md).

Preserve the128 failed GSM attempts and the32 lost training updates. The passive
GPU replay comparison remains non-bitwise; cause is not isolated. Keep this and
the one-training-seed limitation in the final report. No additional arm, seed,
model or result-based stopping rule is introduced by the hardware change.

Existing nightly model/hard-GPU/CPU cutoffs are06:35/06:45/06:50UTC. The provider
23:58PDT timer was left enabled and must be rechecked after hardware changes.
After complete evaluation, report all comparisons and limitations to the owner
and wait for their next-direction decision. No optional experiment follows.
