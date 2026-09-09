# E008 — First paired four-arm scientific pilot

**Work date:** 2026-09-08. **Status:** completed single-seed development pilot.
**Hypothesis timing:** primary contrast and final dose fixed before comparison outcomes.

## Question and motivation

Does allocating four structural paths within a problem improve final-expression
correctness beyond a globally matched one-path allocation, repetition and surface
variation at the same supervision budget?

## Competing explanations and design

Controls address extra response tokens, updates, problems, and global structure
frequency. Paths versus GCM is primary; Repeat and Surface contextualize it.
All four jobs independently start from pinned Qwen2.5-1.5B base, seed17, common
1024 updates / 267456 supervised tokens, identical optimizer and decoding.
Source: `c4f4038f0d1582dc3586802af9d5f22fbfaa13c2`. No best-checkpoint selection.

## Evidence and result

| Arm | Matched greedy | Broader greedy | Sampled pass@1 | pass@4 | Charged seconds |
|---|---:|---:|---:|---:|---:|
| Repeat | 14/64 | 2/64 | 18.75% | 32.8125% | 496 |
| Surface | 12/64 | 0/64 | 13.671875% | 25% | 500 |
| Paths | 23/64 | 4/64 | 28.125% | 51.5625% | 499 |
| GCM | 18/64 | 1/64 | 27.34375% | 34.375% | 498 |

Paths/GCM matched overlap: **11 both correct, 12 Paths-only, 7 GCM-only, 34 both
wrong**. Total phase charge **1993 seconds**; cumulative **3712**. All raw outputs,
four source-linked run directories and verification reports are linked from
[PILOT_V1_RESULTS](../../reports/PILOT_V1_RESULTS.md) and the
[machine-readable snapshot](../../reports/pilot_after_comparison_r1/results.json).
All four weights were independently backed up and hashed; see
[artifact inventory](../../reports/ARTIFACTS.md).

## Interpretation and next decision

The primary contrast is +5/64 in this one selected development slice. Near-equal
sampled per-draw correctness and different pass@4 motivate examining the spread
of successes. One seed, 16 selected dev blocks and poor broader performance do
not establish a population effect, mechanism or useful generalization boundary.
Audit displayed traces and selected structures after the fact, then freeze a
second pairing without changing the primary endpoint.
