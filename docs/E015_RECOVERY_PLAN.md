# Separate E015 weights-recovery window

2026-09-10 UTC. Planning only; no instance startup or network transfer. The
complete 12-file, 6,190,803,414-byte E015 checkpoint remains on the stopped
instance. Independent recovery is incomplete. Preserve that instance and its
volume; no release, deletion or duplicate-cleanup command is authorized here.
Approximate previously displayed retention deadline: 2026-09-25 UTC. Verify the
actual console deadline before recovery; ordinary shutdown is not an indefinite
independent backup. [Provider data-retention documentation](https://www.autodl.com/docs/instance_data/).

Use a **separate no-card mode window**, after confirming its displayed price and
instance identity. Official documentation rechecked on 2026-09-10: CNY0.10/hour, 0.5 CPU, 2GB RAM;
the previous console showed the no-card startup operation. Confirm it again
before acting. No-card mode releases the GPU, so later GPU availability is not
guaranteed. [Provider cost-saving documentation](https://www.autodl.com/docs/save_money/).
Do not start a CNY8/hour GPU merely to transfer weights. The GPU experiment
window contains only compact-record export and does not fulfill this recovery.

## Finite admission and transfer plan

Plan a maximum **two hours**, approximately **CNY0.20** at the displayed
CNY0.10/hour rate, before other fees. This is a new, separately recorded
preservation window, not a reset or continuation of the failed E015 export's
deadline or process allowance. It creates no model-process receipt. Record
actual power-on time, mode and stop confirmation separately from GPU accounting.

1. Within the first ten minutes, verify the exact instance, no-card mode,
   read-only source inventory, complete E015 manifest and current ledger. Rehash
   all 12 source files with streaming tools. No model import or cache download.
   Require local free space for a fresh complete 6.19GB destination plus margin.
   The old partial destination and its failure receipt remain immutable.
2. Make at most **two bounded 64MiB probes**, each at most 120 seconds including
   connection startup: one sequential range reader, then at most two concurrent
   readers if needed. Reuse the import-inert private range adapter with supplied
   authentication; lower concurrency respects the 0.5-CPU no-card instance.
   Record ordered, completely received bytes and end-to-end elapsed time,
   including setup. Verify probe bytes against a source-slice hash. Do not
   report buffered/in-flight bytes as transfer throughput.
3. Admit a full copy only if an actual complete probe achieves at least
   **1.5MiB/s** and at least 6600 seconds remain in the original two-hour window.
   The full checkpoint at that speed is about 3936 seconds; this is a proxy,
   not a guaranteed duration. A failed/slow probe ends the window with provider
   shutdown and a compact failure receipt. Do not repeat the prior eight-worker
   GPU experiment or switch to an undocumented public transfer route.
4. One full copy, no retry: reuse `analyses.e015_export.copy_checkpoint` with
   the verified manifest, a never-used private destination, the successful
   bounded opener and **max_seconds=6000**. Its existing POSIX whole-copy timer
   includes connection, reads and local SHA256 verification; 20-second inactivity
   bounds remain. Reusing five small files is not worth weakening its immutable
   destination protection. No original partial is resumed or overwritten.
5. A complete backup requires exactly the 12 manifest files, matching sizes and
   SHA256 values, and `full_backup_verified=true`. Rehash locally once more and
   retain a compact independent receipt. Then obtain provider-confirmed normal
   shutdown within the remaining ten minutes. On failure, retain partials and
   explicitly keep recovery open; do not label the weights backed up or dispose
   of the stopped instance. No automatic route switch, extension or retry.

The existing public exporter and private adapter already have offline timeout,
partial-file and subprocess fixtures. No test establishes today's network
speed. If both probes fail, keep the GPU off and prepare a different authenticated
route locally before any later attempt. Do not open extra rental machines or
paid storage services without a concrete separately reviewed plan.

E016 can read the retained checkpoint without modifying it. Running that
inference diagnostic does not cure the backup limitation and cannot justify
deleting the only complete checkpoint. Recovery remains a separate open item.
