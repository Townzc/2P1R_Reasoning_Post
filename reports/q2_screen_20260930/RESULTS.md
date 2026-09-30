# Q2 available-state results — September 30, 2026

The executable evaluation queue is complete and the provider is OFF. The intended
scientific comparison is **incomplete**: two training controls failed. Available
measurements show an initial gain followed by little observed change, not evidence
of irreversible damage or a reason to declare the hypothesis false.

## What was measured

Pinned Qwen2.5-Coder-1.5B-Instruct; the existing MBPP+ study split of 250 training
and 128 evaluation tasks. Each state has eight samples per evaluation task,
temperature 1, top-p 1 and a 640-token cap. All 3,072 outputs were generated once,
scored, collected and independently checked; **zero evaluation scores are unknown**.
This observed development split is not a new official benchmark or a decontaminated
test. One paired training replicate is available.

| Available state | Training history | Base pass | Extra-only pass | Base AND extra pass | Observed union pass@8 |
| --- | --- | ---: | ---: | ---: | ---: |
| R | Original weights | 54.88% | 46.97% | **46.48% (476/1,024)** | 75.00% (96/128) |
| W_prefix | 128 updates using base-test rewards | 57.91% | 49.61% | **49.22% (504/1,024)** | 75.78% (97/128) |
| W_future | W_prefix + 128 updates using union rewards | 57.91% | 49.90% | **49.02% (502/1,024)** | 75.00% (96/128) |

The primary metric is task-macro sampled pass@1 under the union, which here equals
the fraction of 1,024 outputs passing both suites. It is not greedy accuracy.
Test-suite success is an operational criterion, not a semantic correctness oracle.

| Descriptive union difference | Percentage points | Conditional question-bootstrap 95% interval |
| --- | ---: | ---: |
| W_prefix − R | +2.73 | [+0.78, +4.79] |
| W_future − W_prefix | −0.20 | [−2.15, +1.66] |
| W_future − R | +2.54 | [+0.20, +4.88] |

Intervals use 5,000 paired task resamples, seed 730, conditional on these particular
model weights. They do **not** quantify training-seed uncertainty. The −0.20-point
change neither demonstrates degradation nor establishes equivalence. Unchanged
pass@8 also does not prove a mechanism such as probability redistribution.

Base-pass/extra-fail outputs number 86, 89 and 91 respectively: 8.40%, 8.69% and
8.89% of all outputs, or 15.30%, 15.01% and 15.35% of base-passing outputs. There
is no obvious descriptive increase; these discrepancies are not all adjudicated
semantic bugs. Completion token totals are 120,068, 99,840 and 100,160; one R
output reaches the cap and neither trained state has a capped output.

The intervention did change training signals: base versus union changes a
nonconstant eight-sample reward vector in 61/256 W_prefix groups and 63/256
W_future groups. This saved-output diagnostic establishes exposure to different
reward signals, not a causal explanation for the evaluation changes.

## What remains unanswered

| Prespecified comparison | Availability | Why it matters |
| --- | --- | --- |
| W_future − R_future | **Missing** | Retain old weights versus return to the original model, with equal future training |
| W_future − C_future | **Missing** | Earlier supervision quality at matched historical update dose |
| C_future − R_future | **Missing** | General effect of additional training with the stronger supervision |

Original R has no future training and cannot substitute for R_future. W_prefix
is not C_future. Thus the table cannot answer the central checkpoint-retention
question or isolate harmful supervision history from a general training plateau.

## Failures and actual dose

| Attempt / phase | Committed updates | Saved training outputs | Outcome |
| --- | ---: | ---: | --- |
| Initial attempt | 5 | 96 | Scoring timeout; original scores preserved |
| W_prefix | 128 | 2,048 | Complete; final export verified |
| C_prefix | 100 | 1,616 | Candidate-initialization scoring failure; no model checkpoint |
| W_future | 128 | 2,048 | Complete; final export and terminal Trainer checkpoint verified |
| R_future | 25 | 416 | Unresolved extra-suite timeout; step-25 checkpoint verified |
| **Total** | **386** | **6,224** | Includes all failed overhead |

There are 6,176 outputs in committed-update batches and 48 in three aborted
batches. No update has an uncertain commit and no generation reservation lacks a
saved backend return. Original failed batches retain 28 non-dual-known scores;
diagnostic rescoring did not overwrite them. Evaluation adds 3,072 outputs,
bringing this round's saved total to **9,296**. The original full 640-update,
16,384-output screen was not completed.

An initialization repair passed its saved-output regression gate. A later suite
watchdog repair **failed** a consistency gate and was never enabled. The first
evaluation startup failed before any generation because the installed Ninja was
absent from PATH; the next source used the existing build tools without installing
or changing the sampling backend. All these failures remain in the record.

Missing sampling log-probabilities and unverified vLLM RNG restoration prevent
an exact R_future continuation claim. C_prefix has no weights to resume. Neither
was replayed; the partial R25 state was not added as another evaluation arm. The
scoring/recovery preparation was insufficient for this full run. This execution
limitation is not evidence against the scientific hypothesis. EvalPlus's inner
FAIL attribution also remains imperfect despite zero outer unknowns in evaluation.

## Decision

Do not scale up or claim a positive finding. Prefer **one bounded completion of
the missing controls**, only after a stable, comparable scoring contract passes
its diagnostic gate. Keep the question neutral: when acceptance-test data are
upgraded, what is the future value of retaining earlier weights?

The nearest natural-verifier study already compares base and extra-only rewards
and reports bounded average effects; a generic weak-versus-strong reward comparison
is therefore not a contribution. Our union-based delayed-upgrade contrast differs,
but its novelty and practical importance still require scrutiny.
([When the Reward Suite Is Leaky](https://arxiv.org/html/2607.11022v1))
Reward changes after proxy training are also studied by
[PRIME, §4.3](https://arxiv.org/html/2606.09711v1), while the distinction between
current performance and subsequent trainability is already explored by
[Overtrained Language Models Are Harder to Fine-Tune](https://arxiv.org/abs/2503.19206).
The matched supervision-history/restart decision must carry the proposed insight.

The [next-screen proposal](NEXT_SCREEN_PROPOSAL.md) is **not launched or authorized**.
Its original priority rule and resource limit prevent searching additional doses
or seeds until a desired result appears. If engineering comparability cannot be
established promptly, or completed controls give no useful decision signal,
deprioritize this project and discuss alternatives. That is a project decision,
not scientific falsification. No alternative has yet passed the separate novelty,
data and compute-readiness audit.

## Preservation and closeout

Execution sources: initial `d33cbbfa`; v2 `9a874bc4`; continuation `d27c6fb9`;
available evaluation `25f3ebfeff8b7748ed8ff9a5c4b8d8d70d40c50e`.
Plan, settings, exact counts, token diagnostics and intervals are in [RESULTS.json](RESULTS.json).
All three evaluation collections contain 1,222 verified compact files each.
The final 37-file closeout includes parent receipts and independently rehashed
W_prefix, W_future and R25 checkpoint file sets. Large weights remain on the
stopped volume; do not release it. Existing failed and diagnostic collections
remain separately preserved.

Normal provider OFF was confirmed by **09:14:30 UTC**; the temporary timer was
cleared afterward. The conservative 05:47–09:14:30 window is 3h27m30s and gives
a **CNY27.60 upper cost proxy** at CNY7.98/hour, excluding storage. It includes
idle/repair time and conservatively includes the earlier interruption; it is not
an invoice. The original 4h/CNY31.92 ceiling was not extended. See [CLOSEOUT.json](CLOSEOUT.json).

Unmodified signed evaluation sample records, including raw text and token IDs,
are retained in `EVALUATION_SAMPLES.jsonl.gz`. To independently reproduce the
reported metrics and task intervals without model calls or program execution:

```sh
python3 reports/q2_screen_20260930/reproduce_available_results.py
```
