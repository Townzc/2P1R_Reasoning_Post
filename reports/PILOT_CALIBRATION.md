# Pilot v1 calibration — 2026-09-08

The frozen Repeat calibration completed all 1024 updates and passed its
prespecified development feasibility gate. This run is not a scientific Repeat
arm and is not reused for the four-arm comparison.

| Check | Correct | Parse failures | Truncated |
|---|---:|---:|---:|
| Matched dev, update 256 | 11/64 | 6/64 | 0/64 |
| Matched dev, update 512 | 16/64 | 0/64 | 0/64 |
| Matched dev, final update 1024 | 14/64 | 5/64 | 0/64 |
| Broader dev, final | 2/64 | 1/64 | 0/64 |
| Unique train sample, final | 12/16 | 0/16 | 0/16 |

The gate requires >=4/64 matched-dev successes, <=10% parse failures and <=5%
truncation at the full frozen dose. The final matched score decreased from
update 512; no checkpoint selection or early stopping was performed. The broader
slice remains weak. Neither development slice establishes a general arithmetic
claim, and the pilot has only one paired seed.

Before training, the first 16 matched-dev prompts produced zero successes and
100% parse failures/truncation at both the 192-token and 384-token prefixes of
the same greedy continuations. Extending the cap alone did not solve the base
model's output-format problem. This 16-prompt diagnostic is not a full 64-prompt
baseline. Full matched-dev reference NLL decreased from 0.639281 to 0.342810.

Training processed exactly 267456 supervised response tokens including EOS,
472832 nonpadding tokens and 4096 presentations, matching the frozen plan.
The measured 100-update window after 10 warmup updates achieved 683.08 response
tokens/s; peak allocated memory was 26836.94 MiB and peak reserved memory
28988 MiB. The bounded process completed in 545.48 seconds and charged 546
seconds. The cumulative ledger is now 1719/7200 seconds, leaving 5481 seconds.

All nine pinned model files, frozen data and source hashes passed verification.
All 50 Linux tests passed with no skips. A CPU rescore of the saved final and
intermediate predictions agrees with the recorded metrics and gate; full-dose
history and planned/actual exposure accounting agree. See
`a800_pilot_preflight_20260908_r1/` and `pilot_calibration_output_integrity.json`.
Raw predictions, budget records, logs and manifests are retained under
`runs/pilot_v1_calibration_seed17_r1`. Training source commit:
`423c94f6d109315913111318ca7e266ba254eb25`.

The owner-provided replacement A800 retained the verified environment and base
cache. External SSH stalled before authentication, so authenticated Jupyter
terminal/file access and a published Git bundle were used. No credentials or
instance endpoints are included in the repository. No calibration checkpoint
was requested; all required calibration records and the latest private ledger
have independent local copies.

## Next authorized phase

Run four independent seed-17 arms from the pinned base, each at the same 1024
updates and 267456 response tokens. The complete phase reserves 4260 seconds
(4 x 1050-second caps plus guards), within the remaining 5481 seconds. Calibration
measured about 390 seconds for training and 59 seconds for final greedy scoring;
sampled scoring and checkpoint saving add costs, so the 1050-second cap remains
unchanged. The run filesystem has about 41 GiB free, above the 30 GiB requirement.
Retain all outcomes and back up all four weights before discarding the instance.
No holdout, additional seed, protocol change or main grid is authorized here.
