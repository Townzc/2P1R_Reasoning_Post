# C005 — Initial development pool supplied only 14 exact blocks

**Work date:** 2026-09-08. **Status:** failed CPU preparation.
**Hypothesis timing:** retrospective preparation-feasibility check.

## Question and motivation

Can 1024 development candidate groups produce the required 16 exact shared blocks?

## Competing explanations and design

Require the full fixed-size development construction under unchanged matching
rules. An insufficient selected set must not be silently accepted or filled with
overlapping training problems.

## Evidence and result

[failure.json](../../runs/pilot_v1_20260908_r2/failure.json) records only **14/16**
development blocks from 1024 candidates. **Zero GPU seconds**. The partial
preparation remains separate from later frozen data; no result was selected by
model performance.

## Interpretation and next decision

Increase the development allocation to 2048 raw groups before solving, retaining
the complete matching requirements. Freeze a new artifact in
[C006](C006_frozen_pilot_preparation.md); do not overwrite this failure.
