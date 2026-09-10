# Account for the whole powered-on rental window

The owner's 2026-09-10 correction is authoritative: the server is billed while
powered on, including idle time, CPU preparation, transfers and human analysis.
GPU-process runtime is a separate scientific guard, not the rental bill.

## What is known and unknown

The owner has authorized the next E015 step and supplied **CNY 8 per hour**
with an **overall CNY 3,000 spending ceiling**, requesting continued economy.
That ceiling equals 375 nominal powered-on hours before other fees; it is not
a spending target. Historical billed spend and the remaining financial balance
are unknown until reconciled against provider records. Do not report CNY 3,000
as a measured account balance or assert that it covers a particular deadline.

The original process guard remains **6,467 / 7,200 seconds used, 733 remaining**,
18 receipts and zero reservations. E015 uses one 360-second process plus a
15-second guard within that allowance. Preserve its history; do not equate it
with cash or rewrite receipts to approximate rental charges. The 733 seconds
are not a permanent financial limit on later scientifically approved finite
phases. Record any new phase-specific process allowance explicitly, linked to
the historical ledger and the overall money ceiling, before that phase runs.

E014 charged 170 process seconds. Existing private orchestration receipts span
2026-09-10 06:35:27.712431 UTC (first successful inspection record) to
07:09:51.214826 UTC (final publication/server-sync record): **2,063.502395
seconds, or 34.39 minutes**. The process charge is 8.24% of that observed span.
These timestamps are local receipt/orchestration timestamps, not provider
power-on/off events, an invoice, or a measurement of GPU utilization. The span
includes preparation/debugging, transfer and publication work; it does not
identify the duration of each component. The rental could extend beyond it.
Reporting only 170 seconds did not describe this cost exposure.

Billing granularity, actual start/stop events and historical charges remain
unknown. For a continuously billed instance, compute
`compute_charge = rate_per_hour * powered_on_seconds / 3600`; apply provider
rounding/minimums only when verified, and list storage or other charges
separately. For repeated windows or billing modes, sum all charged intervals
at their verified rates. Cached teacher creation expense remains separately
unknown.

## Operating sequence

1. **Server off:** read papers, decide the finite experiment, implement changes,
   run all transferable CPU tests, hash/check data and tokenizer files, prepare
   an immutable release and tested transfer bundle. Precompute manifests and
   verify the local checkpoint/ledger recovery copies. Publish the execution
   source and pass offline CPU checks before notifying the owner that startup
   is needed; the owner has already authorized the next E015 step.
2. **Before startup:** state the exact queue, required assets/storage, process
   allowance, total powered-on window, rate/money cap and exit plan. Confirm who
   will stop the instance in the provider console. No queue may auto-start when
   a clone boots. Include checkpoint transfer at measured/required bandwidth.
3. **After startup:** perform only essential instance-specific identity, ledger,
   disk, environment and GPU checks. Target a short prepared preflight. If it
   blocks, preserve a compact failure receipt and request shutdown promptly;
   investigate locally instead of debugging indefinitely on the rental.
4. **Execute the finite queue:** enforce both the process guard and the reviewed
   power-on deadline. No interactive paper search, unplanned retry or new arm
   while the instance is running. A near-deadline job must leave enough time to
   preserve unique results; do not start a job that cannot safely finish/export.
5. **Exit:** copy/hash-check essential new weights, compact raw outputs, receipts
   and the latest ledger to durable independent storage, then request/perform
   the authorized provider shutdown. Stopping Python, disconnecting SSH or
   halting a container is not evidence that billing stopped. Record provider
   state/time when available; otherwise explicitly say shutdown is unverified.
6. **Server off:** do the full CPU output audit, analysis, figures, report writing
   and final publication locally. The staged release is already published;
   a final GitHub upload need not keep a disposable instance running after all
   unique state has a verified independent copy. Reconcile both ledgers later.

## Current E015 planning envelope

The previous E013 checkpoint export and verification took 16.24 minutes, so
the former illustrative 20-minute whole window is superseded. Plan a
**40-minute target/about CNY 5.33** and a **45-minute planned ceiling/CNY 6.00**
at the owner's rate, before rounding or other fees. The target assigns 360
seconds to startup/staging/checks, 375 to the guarded process, 1,320 to export
and verification, and 345 to shutdown/slack. Before admitting the job, require
at least **2,040 seconds** to the absolute powered-on deadline for the last
three components; do not trade preservation or shutdown time for more work.

Use the [E015 storage and rental plan](E015_STORAGE_AND_RENTAL.md) for the
single duplicate-checkpoint cleanup, unchanged 12 GiB gate, finite queue and
transfer failure exit. That plan also documents an optional lower-cost CPU
export mode, subject to provider-console verification; the conservative
45-minute GPU-mode envelope remains the fallback. Neither plan establishes an
actual invoice, observed current server state or confirmed shutdown.

Store a future rental receipt with provider/instance identifier privately,
power-on and confirmed stop timestamps, rate/currency, rounding rule, planned
and actual duration/cost, source of those facts, and linked process receipts.
Public reports should contain sanitized timings and clearly marked unknowns.
