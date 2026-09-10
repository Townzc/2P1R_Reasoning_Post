# C020: separate task completion from capability preservation

2026-09-10 UTC. Local CPU/tokenizer work only. All160 saved E013/E016 generation
streams were reverified from published source
`cf6525b40f36fd714bebbada254af3235fba85c1`. Historical scores and both failed
E016 screens are unchanged. No server contact, model call, new reservation,
unused development text or official-test evaluation occurred.

## The termination failure is mostly continuation into another question

| Saved endpoint | Original clean correct | Truncated originally | Truncated after an earlier new-question header | Correct saved prefix under the candidate completion contract |
|---|---:|---:|---:|---:|
| E013 base,16 observed parents | 10/16 | 2 | 1 | 12/16 |
| E013 tuned,same16 parents | 0/16 | 5 | 0 | 0/16 |
| E016 base,64 observed parents | 26/64 | 14 | 13 | 39/64 |
| E015,same64 E016 parents | 0/64 | 2 | 0 | 0/64 |

For the E016 base, the candidate first-stop events are47 native EOS,16
new-question boundaries and1 length cap. Thirteen of its14 historical
truncations occur after it has already started another question. Of the16
boundary cases,13 have a correct marked answer for the original question.
Simply raising the output cap would spend more on continuation without
addressing the principal observed termination issue.

The candidate retains9,960 of19,391 generated tokens, including delimiter
trigger tokens:9,431 tokens (48.64%) are later tails in these saved streams.
The sum of batch-maximum lengths decreases from5,313 to2,601. These are exact
saved-trace counts, **not measured GPU speedups**. E015's10,086 tokens and zero
correct answers are unchanged, so boundary stopping alone does not repair it.
[All counts](real_math_c020_completion_r1/summary.json).

This rule was designed after inspecting E016. Its39/64 candidate count is not
a new model evaluation, a replacement benchmark score, unbiased confirmation,
or proof validation. Runtime stopping may change batch numerics; future outputs
must be measured. The14 missing marked answers remain format failures under the
frozen extractor, including some correct unmarked prose. No last-number or
gold-guided extraction is introduced.

## Concrete proposed evaluation contract

Retain the original Problem/Solution prompt and the existing gold-blind marked
extractor. Stop a row at native EOS or the first complete, line-anchored
Problem/Question/Q header or bracketed Problem/Question header already recognized
by that extractor. Do not stop on an answer candidate: later contradictory
claims within the same task must still be visible.

Store the exact generated token prefix including the stop trigger, the rendered
answer segment before the new question, and a separate stop reason. A boundary
stop is **not native EOS**. Candidate task-answer success requires an agreed
correct marked answer before a valid stop; a header by itself, conflicting
claims, invalid special tokens, an incomplete stream or a length cap never
becomes success. Continue reporting native EOS and historical metrics separately.

The CPU reference is not a production GPU stopper. Ten boundary-specific fixtures
and six existing extractor tests pass. An independent verifier checks all160
streams, all18 minimal token-prefix boundary triggers and506 proposed training
presentations without calling the new stopping function. It also checks exact
dose and adapter-size arithmetic. [Independent evidence](real_math_c020_completion_r1/independent_verification.json),
[tests](real_math_c020_completion_r1/focused_tests.log),
[registration](../docs/experiments/C020_completion_contract_audit.md).

## Capability-preservation preparation

The review-only training inventory broadens the nominal pool from32 to256
parents, with253 retained single-response parents and3 unavailable parents.
Two epochs, batch8/microbatch1, give64 updates,506 presentations,77,192 supervised
tokens and109,434 nonpadding processed tokens. Each retained response appears
twice; each epoch's last batch has5 rows. These totals use existing accepted
metadata. Raw response reconstruction, exact token/mask checks and a response
quality review still precede any training release. Acceptance does not certify
every reasoning step. [Full schedule](real_math_c020_completion_r1/proposed_training_dose.json).

For a rank16/alpha32 LoRA candidate on the original28-layer Qwen model, applying
adapters to q/k/v/o/gate/up/down projections while freezing all base parameters
gives a shape estimate of18,464,768 trainable parameters. FP32 adapter tensors
alone occupy73,859,072 bytes (70.44MiB), compared with E015's6.19GB full checkpoint.
Actual library parameter scope and serialized bytes require verification; this
does not establish training speed or adequate transfer throughput.

LoRA is a proposed new adaptation method, not a silent change to an existing
arm. The reduced repetition and adaptation change together make the next
calibration a recipe feasibility check, not an isolated causal test of LoRA.
No trained candidate exists yet. [Finite evaluation and training proposal](../docs/experiments/P006_evaluation_and_capability_preservation.md),
[paper-to-decision review](LITERATURE_CAPABILITY_PRESERVATION_20260910.md).
The [proposal consistency record](real_math_p006_proposal_checks.json) verifies
the 64 LR values, two fixed sample lists and all three stage budgets. All 96
historical runtime dependencies, the ledger, accounting and registry are unchanged.

The ledger remains20 receipts,6,921/7,200 seconds used,279 left and no
reservation. Last verified provider state is off; it was not rechecked by
contacting the server in this phase. E015 independent weights recovery remains
open, and that retained instance must not be disposed of.

Reproduce into new paths:

```sh
python -m analyses.c020_completion_audit --tokenizer-dir PINNED_TOKENIZER --out-dir NEW_DIRECTORY
python -m analyses.verify_c020_completion --tokenizer-dir PINNED_TOKENIZER --folder NEW_DIRECTORY --out NEW_VERIFICATION_JSON
```
