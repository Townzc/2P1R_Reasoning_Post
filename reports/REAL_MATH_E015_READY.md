# E015 ready for one owner-started A800 window

2026-09-10 UTC. Offline preparation is complete. No server contact, pretrained
model call, GPU reservation or E015 training result occurred in this phase.
Start the existing A800 for the single registered run after reading the finite
handoff below. E012 stays paused; E013/E014 must not be replayed.

## What will run and what it can establish

`gsm8k_terminal_decay_e015_r1` uses the original 32 GSM8K references, fresh pinned
Qwen2.5-1.5B base, seed 17, 256 optimizer calls and the original decoder/gate.
Only the learning-rate schedule changes: 192 constant steps at 5e-5, then 64
cosine-decay steps to zero. There are 255 nonzero-LR updates; summed LR is
0.011175. Dose remains 167,232 supervised / 229,056 processed tokens, with 32
exposures per reference. No new development/test generation or teacher call.

The unchanged gate requires at least 31/32 correct and terminated train answers,
zero truncations, reference NLL below 0.1 and complete dose/profile. This is an
engineering repair, not a generalization or multiple-solution result. A failed
or partial run stops without retry or the old 512-step fallback. A passing run
leads to a separately designed held-out capability/profile check before the
prospective Repeat256x1 / Solutions256x4 / Breadth1024x1 comparison. P005 retains
conditional selection, curriculum and small-student/objective alternatives.

## Published and independently checked

- Implementation commit: `09a00c0a8d2e260f74cfcd02a2967fda0a757d36`.
- Immutable input-release commit: `73b054bf9e7f5bd03d6f96d63dd6a32c51d82e27`.
- Release SHA256: `a88cf1732d13ce00f235dda0eb7d8f3288273987270352de03e0a9551bcc3230`.
- Input manifest SHA256: `b8720bf6c0c836f59a29d876fc0a53c51ff3f9683d04883f8b37a806dca9f6d0`.
- [Focused suite](real_math_e015_local_tests.json): 112 tests, 110 pass and two GNU-timeout integrations deferred to Linux. Includes actual optimizer LR, zero-LR state advancement, partial-dose handling, raw-token/reference audit, mocked worker lifecycle, duplicate cleanup and stalled-export deadlines.
- [Independent inputs](real_math_e015_verification_r1/input_verification.json): all 32 parents, 5,226 reference targets/EOS, original order/dose and the separate LR formula agree.
- [Published default inspection](real_math_e015_verification_r1/published_inspection.json): passes in 4.59 seconds with no model/server calls.
- [Fresh checkout](real_math_e015_verification_r1/fresh_checkout.json): a 140,486-byte incremental release bundle imports from the last server commit `d2ddb6a`; independent inputs and default inspection pass in 6.07 seconds. The final handoff bundle also includes this readiness milestone.

Four further [independent negative checks](real_math_e015_verification_r1/lr_negative_checks.json)
reject NaN, infinity, booleans and wrong LR values even after coherent hash
updates; the isolated inputs are restored byte-identically. Five offline
[transport fixtures](real_math_e015_verification_r1/transport_checks.json) verify
the prepared parallel range adapter, ordered hashes, a real 20 ms deadline,
partials and subprocess cleanup. It matches the historical eight-worker
concurrency with bounded buffers; current SSH throughput is still unmeasured.

CPU fixtures do not prove GPU numerical equivalence or a passed engineering gate.
All original `src/`, `scripts/`, experiment inputs, scores and proposal JSON files
remain unchanged. Installed generation/Qwen2 source hashes are frozen separately.

## Money, preservation and admission

The owner supplied **CNY 8/hour and CNY 3,000 overall ceiling**. The conservative
whole powered-on window targets **40 minutes (~CNY 5.33)**, with a **45-minute
planned ceiling (~CNY 6)** before unverified rounding/storage fees. This ceiling
is not a spending target. Actual historical bills and remaining money are unknown.

The original process ledger stays at 6,467/7,200 seconds used, 733 remaining,
18 receipts and zero reservations. One 360-second process plus 15-second guard
fits, leaving at least 358. Later finite phases can be priced within the monetary
ceiling while preserving history; 733 seconds is not the new financial limit.
Latest ledger SHA256:
`8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9`.

[Fresh preservation checks](real_math_e015_local_preservation.json) verify all
12 independent E013 checkpoint files (6,190,803,414 bytes). On startup, reclaim
only the exact rehashed server duplicate if required. Export a preview receipt
before deletion. Keep the original base, surrounding records and ledger. The
predicted free-space margin above 12 GiB is only 59.6 MiB: stage first and verify
actual disk space; a failed gate ends the window without launching a model.

The prior export took 16.24 minutes, so allow 22 minutes for export/verification.
The new streaming helper has a real whole-transfer deadline and retains partials
on failure. An incomplete copy is not a backup. Preserve the volume on shutdown
if unique weights remain; do not dispose of that instance. An optional
console-verified no-card export route is described in the
[storage/rental plan](../docs/E015_STORAGE_AND_RENTAL.md).

## Startup and closeout

Synchronize the published handoff, verify original base/tokenizer, exact ledger,
idle A800 80 GB, driver 580.126.09, pinned packages and the 12 GiB storage gate.
Run the full 112-test Linux suite (including both timeout integrations) before
reservation. Record actual power-on time and its evidence source. Admission
requires at least 2,040 seconds left within the planned window for the guarded
job, export and shutdown. Notification time may postdate actual startup.

Use the commands in [the registration](../docs/experiments/E015_terminal_decay.md).
Launch only E015. Preserve completed or partial outputs and reconcile the new
process receipt. Export compact outputs/latest ledger first, then stream/hash
all new checkpoint files into an unused independent destination. Stop promptly
after preservation and verify the provider state; a watchdog or lost SSH
connection is not evidence that billing stopped. Complete detailed analysis and
GitHub result publication locally after shutdown.
