# Overnight completion authorization — 2026-09-18 UTC

The owner explicitly requested completion of the current round overnight, durable
records, and shutdown before their morning review. This supersedes the earlier
midnight pause and the old 06:35/06:45/06:50/06:58 UTC deadlines. It does not
reopen the ICLR sprint or authorize additional scientific work.

At 05:58 UTC, all four training arms were complete. The remaining work was
frozen MATH sampling and trained-model dev evaluation, with scoring concurrent.
The remaining wall-time estimate is approximately 6–7 hours on two A80080GB
GPUs, with an 8-hour planning reserve. At the owner's quoted CNY8/card/hour,
this is approximately CNY96–112, or CNY128 for the reserve, excluding other fees.
The provider UI estimated CNY126.61 from about 06:02 UTC to the new timer.
These are prospective estimates, not an invoice. The owner supplied a CNY200
remaining-spend boundary; it is a ceiling, not a spending target.

| Boundary | UTC, 2026-09-18 | America/Los_Angeles, 2026-09-18 |
|---|---|---|
| Model admission deadline | 13:35 | 06:35 |
| Hard GPU deadline | 13:45 | 06:45 |
| CPU scoring deadline | 13:50 | 06:50 |
| Verified provider failsafe shutdown | 13:58 | 06:58 |

Stop the instance earlier as soon as results and essential compact records are
verified. Complete extensive narrative analysis and publication after shutdown.
The timer is a failsafe, not a planned idle period. If the finite ceiling arrives
before completion, retain unfinished coverage and report it honestly; do not
exceed the boundary or restart automatically.

## Operational continuation

The running evaluator's argv contains immutable old deadlines. Request a pause
at the end of each current complete run using its existing pause marker. Preserve
both worker/coordinator receipts and independently reconcile stable saved outputs,
physical reservations, scoring bindings and retained checkpoint identities. Resume
once with the same published scheduler source `abfff696f68cdd8aa9b32dd410330ee5424d5c80`,
identical original scientific and parallel contracts, and the new deadlines.
Consume the pause marker by archival rename only after idle verification. A
requested pause is not an infrastructure fault or an additional retry allowance.
Keep the unchanged scorer single-instance, with a separate new attempt receipt
after its existing deadline exits. Preserve the old telemetry and append a new
bounded observer stream. All model workers remain detached under tmux.

Four arms, 512 committed updates, 544 physical completed training records,
31,203 logical outputs and the 31,331 physical-generation cap are unchanged.
Retain the GSM128 OOM and its 128 lost attempts, TrimSFT cache failure and its
32 lost updates, and the non-bitwise GPU replay limitation. No completed outputs
are regenerated; no new preparation, training, seeds, models or benchmarks run.
Large scientific artifacts remain verified on the server as previously authorized.
No instance or volume is released or deleted.

## Required estimates for later experiments

Before each future experiment, provide the owner a concrete estimate covering
training, answer generation/evaluation, CPU scoring, setup and closeout; wall time
and GPU-hours; the hardware and concurrency plan; cost range and maximum budget;
disk and host/GPU memory; measured throughput versus assumptions; and finite stop
conditions. Use a bounded engineering measurement if throughput is unknown,
subject to that experiment's authorization. Do not substitute training duration
for total rental duration. Reuse outputs only when exact identities permit it.

Future scientific proposals remain proposals until the owner chooses a direction.
After this round, provide the complete four-method comparison, MATH average@8
and pass@8, GSM8K, dev trends, paired uncertainty, limitations, actual resource
use and an ACL/ICML handoff. The other long-term worktree remains unchanged.
