# Read-only T8 closeout helper preflight — no model admission change

These helpers are prepared/parsed only and have not read actual T8 closeout
records or recovered any actual T8 callback. Three new fully mocked local-I/O
checks pass: two runs share exactly one ledger enumeration and cannot be
recollected; a changed terminal preserves partial/failure evidence; an active
provider is refused before enumeration. Every cloud interface and the already
reviewed supplement validator are mocked in these tests. They do not establish
real model completion or re-test the scientific validator.

`collect_t8_cap_wave.py RUN...` is an optional read-only alternative to the
existing per-run collector, for at most eight named already-completed/stopped
original T8 calls. A create-only wave intent fences its exact run set. One common
full-ledger scan is hard-linked to the independent closeouts, while each run
still receives original Volume mtimes, provider proof, envelope binding and
fresh before/after terminal/supplement verification. No claim is made that
unrelated active rows form an atomic snapshot. Local work is capped at1200s.
Any failure preserves the wave intent and valid pieces: no whole-wave replay or
switching to the old collector for the same partially-collected run. A new wave
must be disjoint. Use one collection route per run; no repeated existing
collector/export/oracle. The required independent full raw/state oracles are
unchanged and run later, once each.

`recover_completed_t8_cap_receipt.py RUN` is a narrower read-only fallback for a
saved local ConnectionError (DNS/reset/client-connection). It requires the
original submitted call, absent canonical result, real completed terminal and
stopped/zero-container provider, then reads four bounded original Volume files.
It binds source/spec, originalclaim, effective9600, supplement and original
artifact hashes before writing a reconstructed original envelope once. The
callback error is retained. No restart, remote mutation, new scientific attempt,
raw scoring or complete bundle export occurs.

Review failure fencing, selected-row immutability, ledger-sharing semantics,
original mtime provenance, callback reconstruction and absence of remote writes.
These new paths require scoped acceptance before use. Pending review does not
block any already admitted T8, or the existing single-run closeout route when
no wave intent/closeout exists. The new helpers must never be used to replay a
finished or unknown scientific call. Final CPU/new numerical admission remains
separate and unchanged.
