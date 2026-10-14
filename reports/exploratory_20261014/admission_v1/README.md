# Exploratory follow-up: three original runs, not preregistered

Status: **prepared; exact Claude code/data review pending; zero submissions**.
The owner directly authorized this separate $30 finite follow-up after P008
closed. Original P008 records, failed attempts, primary scores, final handoff and
21:00 PDT material freeze remain immutable. Automation p007 remains paused.

| Slot | Fixed scientific work | Endpoint |
|---|---|---|
| `base_4shot` | Qwen2.5-1.5B base, frozen first four reserved-dev examples | 1,319 greedy, 512-token cap |
| `instruct_0shot` | Official Qwen2.5-1.5B-Instruct, own chat template, no demonstrations | same |
| `wrong_teacher_t1` | One base+LoRA student, 256 updates, 524,287 supervised targets, seed 17 | same |

All endpoints use frozen `marked_answer_v1`, the original task-boundary completion
rule, batch 16, context 2,048, and length caps count as incorrect. No test-outcome
selection, extra seed, calibration model call, checkpoint selection or retries.
The two evaluation-only slots perform zero optimizer updates. The student uses
the original P008 `schedule()` builder, exact published 256-element LR vector,
FP32 base/LoRA parameters and AdamW state, BF16 forward, LoRA r16/alpha32/dropout0,
full answers plus EOS, prompt/padding masking, per-update target normalization,
no packing and no truncation. State256 is preserved before the sole endpoint.

## Frozen inputs and models

The first four rows in the original 500-row reserved-dev order are fixed without
reading evaluation outputs. Original worked references (including `####` final
answers) appear as `Problem: ...\nSolution:\n...` demonstrations. No test example
is used. Dev has prior Phase0 exposure; it is not newly unseen data. All 1,319
4-shot prompt lengths are 771–936 tokens, so 512 new tokens fit without changing
the context limit. Instruct prompts are 51–216 tokens; student prompts 27–192.

Base revision is `8faed761d45a263340a0528343f099c05c9a4323`; official general
Instruct revision is `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. This is **not**
the Math teacher. The exact user-requested system text is:
`Please reason step by step, and put your final answer within \boxed{}.`
Its published example is in the [Qwen Math model card](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct),
while the [general Instruct card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
shows a different helpful-assistant default. This study deliberately combines
the specified general Instruct model/template with the requested mathematical
system instruction. It does not claim that combination is the model card's
default evaluation. Native Instruct EOS IDs 151645 and 151643 are both respected;
base/student native EOS remains 151643. Greedy decoding explicitly sets
repetition_penalty=1; model-card stochastic defaults are not inherited.

D1 selection uses its original frozen parent order followed by attempt number.
There are 864 records with native EOS, no truncation, a parsed but wrong frozen
answer and no earlier exact normalized duplicate. The first 429 are selected,
from 101 distinct questions. Duplicate identity is the existing P008
NFC/whitespace exact **within-parent** definition, including earlier unsuccessful
occurrences. No semantic similarity filter or additional teacher output is used.
Selected source token streams have original native-EOS/raw-file bindings.
The full original teacher text is the training target; the correct reference is
metadata only. Actual selection, prompts, schedule, source hashes and model
weight SHA are included here for independent review.

The positive reference is the already closed independent replacement for
`d1_b1_p0_breadth_t1`: **969/1,319**, 429 answers from 429 questions. The original
failed zero-update parent is still failed. New wrong answers cover 101 questions
and have different lengths/exposures. This is an exploratory corpus comparison,
not an isolated causal manipulation of answer correctness. All three results,
including failures or nulls, will be reported together. No claims about unseen
test performance, reasoning validity, stable winner or independent replication.

## Finite execution and budget

Each new slot is submitted once, with 6,001 seconds from worker entry, a 6,061
second platform timeout, at most 600 seconds startup, 4 CPU/32 GiB/one H100,
zero retry and scale-to-zero. All three share a local dispatch lock and a ceiling
of three, including pending/unknown/unmatched containers. A permanent atomic
RunGuard claim and per-block/per-batch intents precede science. Existing claims,
directories or dispatch receipts reject new submissions. Connection loss does
not authorize re-dispatch. The new namespace cannot reuse original P008 claims.

At the [verified Modal rates](https://modal.com/pricing), each 6,761-second
platform/startup/closing envelope reserves $8.26. Three reserve **$24.78**;
**$5.22** is retained for image build, transfer, storage and other setup. Total
new allowance is **$30**, with no replacement slot. These are ceilings/reservations,
not invoices or predicted actual expense. The original project $450 spend ceiling
and $50 protection remain. The new exact plan ends 2026-10-14 14:00 UTC (07:00 PDT);
every launch still needs its full 6,001+700-second window. A late review leaves
the slot unsubmitted rather than reducing dose or extending the deadline.

The existing base assets and pinned software stack are reused. General Instruct
metadata/tokenizer are frozen locally; its one 3,087,467,144-byte official weight
download and hash check occur inside its original paid worker/time cap, with no
download retry. Its partial files and failure remain if transport fails. No paid
standalone probe, new controller or extra training profile is included. The
measured old T1 runtimes are background evidence, not a guarantee for this new
corpus, prompt or model. Code and exact numeric/input review are mandatory before
the first new upload, image or scientific submission.

## Verification and disclosure

Thirteen new CPU fixtures passed for ordered selection, shortfall, duplicates,
caps/parse rejection, native EOS, exact budget and permanent duplicate claims.
They are not a new GPU or throughput measurement. Input preparation ran once,
with exact target scheduling and complete-context validation before output files.
No old P008 oracle or test suite was rerun. New completed outputs require an
original result, actual app STOPPED/zero owned containers, one immutable
collection/export, and the new local full raw/state/dose oracle. Official weight
readback is separately retained. Original failed/unknown work is never replayed.

The first billing-report CLI used an unsupported range `month` and returned no
report; its stderr and the subsequent local empty-JSON read error are retained.
A separate corrected `this month` GET succeeded. Source preparation also fixed a
local capacity-helper signature before any test or submission. No scientific
attempt arose from these local errors. Fresh Papers remained `ea8befd5`; no new
Pro delivery was inferred. This packet requests review, it does not assert PASS.
