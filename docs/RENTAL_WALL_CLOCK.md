# Account for the whole powered-on rental window

The owner's 2026-09-10 correction is authoritative: the server is billed while
powered on, including idle time, CPU preparation, transfers and human analysis.
GPU-process runtime is a separate scientific guard, not the rental bill.

## What is known and unknown

The current guard remains **6,467 / 7,200 process seconds used, 733 remaining**,
18 receipts and zero reservations. Do not reset it, equate its balance with
cash remaining, or change historical receipts to approximate rental charges.

E014 charged 170 process seconds. Existing private orchestration receipts span
2026-09-10 06:35:27.712431 UTC (first successful inspection record) to
07:09:51.214826 UTC (final publication/server-sync record): **2,063.502395
seconds, or 34.39 minutes**. The process charge is 8.24% of that observed span.
These timestamps are local receipt/orchestration timestamps, not provider
power-on/off events, an invoice, or a measurement of GPU utilization. The span
includes preparation/debugging, transfer and publication work; it does not
identify the duration of each component. The rental could extend beyond it.
Reporting only 170 seconds did not describe this cost exposure.

Hourly rate, billing granularity, actual start/stop events and money limit are
unknown. Once supplied, record them separately. For a continuously billed
instance, compute `compute_charge = rate_per_hour * powered_on_seconds / 3600`;
apply provider-specific rounding/minimums only when verified, and list storage
or other charges separately. For repeated windows, sum every billable window.
Cached teacher creation expense remains a third, separately unknown quantity.

## Operating sequence

1. **Server off:** read papers, decide the finite experiment, implement changes,
   run all transferable CPU tests, hash/check data and tokenizer files, prepare
   an immutable release and tested transfer bundle. Precompute manifests and
   verify the local checkpoint/ledger recovery copies. Do local review and
   publication before asking for startup.
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

## Example planning envelope, not a reservation

For P005's one repair only, a **conditional 20-minute** power-on target could
allocate 2 minutes to startup/staging, 1 to instance checks, 6.25 to the bounded
job, 8 to export/verification, and 2.75 to shutdown/slack. This requires assets
already staged and roughly 13 MiB/s or better for a 6.19 GB checkpoint plus
headroom. Startup variability, verification and provider shutdown may make this
insufficient. Measure/validate these prerequisites before presenting a firm
window; do not silently exceed a reviewed monetary cap.

At hourly rate r the illustrative compute charge is r/3, versus about 0.5732r
for the observed E014 orchestration span, both before rounding or other charges.
Neither number is an actual invoice. The current task creates no reservation,
server contact, shutdown claim or additional allowance.

Store a future rental receipt with provider/instance identifier privately,
power-on and confirmed stop timestamps, rate/currency, rounding rule, planned
and actual duration/cost, source of those facts, and linked process receipts.
Public reports should contain sanitized timings and clearly marked unknowns.
