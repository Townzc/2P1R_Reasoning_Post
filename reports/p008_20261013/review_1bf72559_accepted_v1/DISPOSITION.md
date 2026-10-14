# Public collection provenance code review accepted

Claude 1bf72559, comment event 2026-10-14 02:47:16 UTC, full report read 02:55:34 UTC, gives PASS for the exact publisher v2 at b4796e6e. This covers collection provenance and the unchanged archive selection/readback code; it is not G3 acceptance of any actual T8 output.

The named-wave route requires the original intent, matching envelope and ledger hashes, and a completed wave. Partial waves fail closed. The single-run route cannot bypass an existing wave intent. Callback recovery requires the saved ConnectionError and four exact original files; no private gates are published. The reviewer could not inspect the untracked local single-run collector. This round uses the separately reviewed named-wave collector instead.

L1 is retained: this publisher is executed only once in the existing checkout, using the stored wave path. No relocation or republication is performed. Live student sources and final CPU sources are unchanged.

At the actual 02:54:56 UTC provider snapshot, three original T8s had completed terminals and zero owned containers. Exact app info at 02:55:50 confirmed STOPPED: D1 B8/p0 breadth, D1 B8/p4 breadth and depth. The other five remained active and had saved all 2048 training updates. These saved acknowledgments and receipts do not replace independent raw/state oracles. One disjoint three-run collection wave was started after those checks; no model was submitted or replayed.
